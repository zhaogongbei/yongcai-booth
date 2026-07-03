from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import check_team_member, get_current_active_user, get_db
from app.core.config import settings
from app.models.models import User
from app.schemas.subscription import (
    CheckoutSessionRequest,
    CheckoutSessionResponse,
    SubscriptionCreate,
    SubscriptionPlan,
    SubscriptionResponse,
    SubscriptionUpdate,
    SubscriptionUsage,
)
from app.services.subscription_service import SubscriptionService

router = APIRouter()


@router.get("", response_model=List[SubscriptionResponse])
async def get_subscriptions(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get subscriptions for the current user's teams"""
    from app.services.team_service import TeamService

    team_service = TeamService(db)
    user_teams = await team_service.get_user_teams(current_user.id)
    if not user_teams:
        return []

    subscription_service = SubscriptionService(db)

    # Only return subscriptions for teams the user belongs to
    all_subscriptions = []
    for team in user_teams:
        if team.subscription_id:
            sub = await subscription_service.get_subscription(team.subscription_id)
            if sub:
                all_subscriptions.append(sub)
    return all_subscriptions[skip : skip + limit]


@router.get("/plans", response_model=List[SubscriptionPlan])
async def get_subscription_plans(db: AsyncSession = Depends(get_db)):
    """Get available subscription plans."""
    return SubscriptionService(db).get_plans()


@router.get("/teams/{team_id}/usage", response_model=SubscriptionUsage)
async def get_subscription_usage(
    team_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get subscription usage for a team."""
    await check_team_member(team_id, current_user, db)
    return await SubscriptionService(db).get_team_usage(team_id)


@router.post("", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_subscription(
    subscription_in: SubscriptionCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new subscription (restricted to Stripe webhook flow)

    IMPORTANT: Direct subscription creation is disabled to prevent data inconsistency.
    Use POST /api/v1/subscriptions/checkout to initiate subscription via Stripe.
    This endpoint is reserved for internal/webhook use only.
    """
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Direct subscription creation is not allowed. Use /api/v1/subscriptions/checkout to subscribe via Stripe.",
    )


@router.post("/checkout", response_model=CheckoutSessionResponse)
async def create_checkout_session(
    checkout_in: CheckoutSessionRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a Stripe Checkout Session for subscribing to a plan.

    Requires the caller to be an owner of the team.
    """
    from app.models.models import UserRole
    from app.services.team_service import TeamService

    team_service = TeamService(db)
    if not await team_service.has_permission(checkout_in.team_id, current_user.id, UserRole.OWNER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only team owners can start a subscription checkout",
        )

    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe is not configured on this server",
        )

    import stripe

    stripe.api_key = settings.STRIPE_SECRET_KEY

    try:
        session = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{"price": checkout_in.plan_id, "quantity": 1}],
            success_url=checkout_in.success_url,
            cancel_url=checkout_in.cancel_url,
            metadata={"team_id": str(checkout_in.team_id)},
        )
        return CheckoutSessionResponse(session_id=session.id, checkout_url=session.url)
    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Stripe error: {str(e)}"
        )


@router.get("/{subscription_id}", response_model=SubscriptionResponse)
async def get_subscription(
    subscription_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get subscription by ID"""
    subscription_service = SubscriptionService(db)

    subscription = await subscription_service.get_subscription(subscription_id)
    if not subscription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")

    if subscription.team:
        await check_team_member(subscription.team.id, current_user, db)

    return subscription


@router.put("/{subscription_id}", response_model=SubscriptionResponse)
async def update_subscription(
    subscription_id: UUID,
    subscription_in: SubscriptionUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update subscription (restricted to team owners)"""
    from app.models.models import UserRole

    subscription_service = SubscriptionService(db)

    subscription = await subscription_service.get_subscription(subscription_id)
    if not subscription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")

    if subscription.team:
        from app.services.team_service import TeamService

        team_service = TeamService(db)
        # Only team owners can modify subscriptions
        if not await team_service.has_permission(
            subscription.team.id, current_user.id, UserRole.OWNER
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only team owners can update subscriptions",
            )

    subscription = await subscription_service.update_subscription(subscription_id, subscription_in)
    return subscription


@router.post("/{subscription_id}/cancel", response_model=SubscriptionResponse)
async def cancel_subscription(
    subscription_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel a subscription (restricted to team owners)"""
    from app.models.models import UserRole

    subscription_service = SubscriptionService(db)

    subscription = await subscription_service.get_subscription(subscription_id)
    if not subscription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")

    if subscription.team:
        from app.services.team_service import TeamService

        team_service = TeamService(db)
        # Only team owners can cancel subscriptions
        if not await team_service.has_permission(
            subscription.team.id, current_user.id, UserRole.OWNER
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only team owners can cancel subscriptions",
            )

    try:
        subscription = await subscription_service.cancel_subscription(subscription_id)
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found"
            )
        return subscription
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/webhooks/stripe", status_code=status.HTTP_200_OK)
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Handle Stripe webhook events"""
    import stripe

    stripe.api_key = settings.STRIPE_SECRET_KEY

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    if not sig_header:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Missing stripe-signature header"
        )

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")

    subscription_service = SubscriptionService(db)

    try:
        await subscription_service.handle_stripe_webhook(
            event_type=event["type"], data=event["data"]["object"]
        )
        return {"status": "success"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
