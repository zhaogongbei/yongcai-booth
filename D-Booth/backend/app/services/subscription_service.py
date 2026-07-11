import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.plans import get_plan, list_plans, normalize_plan_id
from app.models.models import Subscription, SubscriptionStatus
from app.repositories.ai_task_repository import AITaskRepository
from app.repositories.event_repository import EventRepository
from app.repositories.photo_repository import PhotoRepository
from app.repositories.subscription_repository import SubscriptionRepository
from app.schemas.subscription import (
    SubscriptionCreate,
    SubscriptionPlan,
    SubscriptionUpdate,
    SubscriptionUsage,
)
from app.services.base_service import BaseService, BusinessRuleError, ValidationError


class StripeCancellationError(RuntimeError):
    """Raised when Stripe rejects or cannot process a subscription cancellation."""


class SubscriptionService(BaseService[Subscription, SubscriptionCreate, SubscriptionUpdate]):
    """
    Service for subscription business logic.

    Manages team subscription plans, quota enforcement, Stripe integration,
    and usage tracking.
    """

    def __init__(self, db: AsyncSession):
        repository = SubscriptionRepository(db)
        super().__init__(repository, db)

    # ── Validation Hooks ──────────────────────────────────────

    async def validate_create(self, obj_in: SubscriptionCreate) -> None:
        """Validate subscription creation business rules."""
        plan_id = normalize_plan_id(obj_in.plan_name)
        if plan_id != obj_in.plan_name.strip().lower():
            raise ValidationError(f"Unknown subscription plan '{obj_in.plan_name}'")

    async def validate_update(self, existing: Subscription, obj_in: SubscriptionUpdate) -> None:
        """Validate subscription update business rules."""
        update_dict = obj_in.model_dump(exclude_unset=True)
        if "plan_name" in update_dict and update_dict["plan_name"] is not None:
            plan_id = normalize_plan_id(update_dict["plan_name"])
            if plan_id != update_dict["plan_name"].strip().lower():
                raise ValidationError(f"Unknown subscription plan '{update_dict['plan_name']}'")

    # ── Transformation Hooks ──────────────────────────────────

    async def before_create(self, obj_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Transform subscription data before creation."""
        # Normalize and set plan_name
        if "plan_name" in obj_dict:
            obj_dict["plan_name"] = normalize_plan_id(obj_dict["plan_name"])
        obj_dict["status"] = SubscriptionStatus.ACTIVE
        return obj_dict

    async def before_update(
        self, existing: Subscription, obj_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Transform subscription update data."""
        # Normalize plan_name if present
        if "plan_name" in obj_dict and obj_dict["plan_name"] is not None:
            obj_dict["plan_name"] = normalize_plan_id(obj_dict["plan_name"])
        return obj_dict

    # ── Business Logic Methods ────────────────────────────────

    async def get_subscription(self, subscription_id: UUID) -> Optional[Subscription]:
        """Get subscription by ID (alias for route compatibility)."""
        return await self.get(subscription_id)

    async def get_by_stripe_id(self, stripe_subscription_id: str) -> Optional[Subscription]:
        """Get subscription by Stripe subscription ID"""
        return await self.repository.get_by_stripe_subscription_id(stripe_subscription_id)

    def get_plans(self) -> list[SubscriptionPlan]:
        """Return the configured subscription plans."""
        return [SubscriptionPlan(**plan) for plan in list_plans()]

    async def get_team_usage(self, team_id: UUID) -> SubscriptionUsage:
        subscription = await self.repository.get_by_team_id(team_id)
        plan = self._plan_for_subscription(subscription)
        period_start, period_end = self._billing_period(subscription)

        event_repo = EventRepository(self.db)
        photo_repo = PhotoRepository(self.db)
        ai_repo = AITaskRepository(self.db)

        usage = {
            "events": await event_repo.count_by_team(team_id),
            "photos": await photo_repo.count_by_team(team_id),
            "ai_credits_monthly": await ai_repo.count_by_team_between(
                team_id,
                period_start,
                period_end,
            ),
        }
        limits = plan["limits"]
        is_overused = self._limit_exceeded(usage["events"], limits["max_events"])
        is_overused = is_overused or self._limit_exceeded(
            usage["ai_credits_monthly"],
            limits["ai_credits_monthly"],
        )

        return SubscriptionUsage(
            team_id=team_id,
            plan_name=plan["id"],
            current_period_start=period_start,
            current_period_end=period_end,
            usage=usage,
            limits=limits,
            is_overused=is_overused,
        )

    async def ensure_can_create_event(self, team_id: UUID) -> None:
        """Verify team can create another event within plan limits."""
        plan = await self._get_active_team_plan(team_id)
        limit = plan["limits"]["max_events"]
        current = await EventRepository(self.db).count_by_team(team_id)
        if self._limit_exceeded(current, limit):
            raise ValueError(
                f"Event quota exceeded for plan '{plan['id']}' " f"({current}/{limit})"
            )

    async def ensure_can_upload_photo(self, team_id: UUID, event_id: UUID) -> None:
        """Verify event can accept another photo within plan limits."""
        plan = await self._get_active_team_plan(team_id)
        limit = plan["limits"]["photos_per_event"]
        current = await PhotoRepository(self.db).count_by_event(event_id)
        if self._limit_exceeded(current, limit):
            raise ValueError(
                f"Photo quota exceeded for plan '{plan['id']}' "
                f"({current}/{limit} photos per event)"
            )

    async def ensure_can_create_ai_task(self, team_id: UUID) -> None:
        """Verify team has remaining AI credits for this billing period."""
        subscription = await self.repository.get_by_team_id(team_id)
        plan = self._plan_for_subscription(subscription)
        limit = plan["limits"]["ai_credits_monthly"]
        period_start, period_end = self._billing_period(subscription)
        current = await AITaskRepository(self.db).count_by_team_between(
            team_id,
            period_start,
            period_end,
        )
        if self._limit_exceeded(current, limit):
            raise ValueError(
                f"AI credit quota exceeded for plan '{plan['id']}' " f"({current}/{limit})"
            )

    async def create_subscription(self, subscription_in: SubscriptionCreate) -> Subscription:
        """Create a new subscription (alias for route compatibility)."""
        return await self.create(subscription_in)

    async def update_subscription(
        self, subscription_id: UUID, subscription_in: SubscriptionUpdate
    ) -> Optional[Subscription]:
        """Update subscription (alias for route compatibility)."""
        return await self.update(subscription_id, subscription_in)

    async def cancel_subscription(
        self, subscription_id: UUID, immediate: bool = False
    ) -> Optional[Subscription]:
        """Cancel a subscription locally and at Stripe."""
        subscription = await self.repository.get(subscription_id)
        if not subscription:
            return None

        # Notify Stripe if a stripe_subscription_id is linked
        if subscription.stripe_subscription_id:
            import stripe

            stripe.api_key = settings.STRIPE_SECRET_KEY
            try:
                if immediate:
                    await asyncio.to_thread(
                        stripe.Subscription.delete, subscription.stripe_subscription_id
                    )
                else:
                    await asyncio.to_thread(
                        stripe.Subscription.modify,
                        subscription.stripe_subscription_id,
                        cancel_at_period_end=True,
                    )
            except Exception as exc:
                # Fail closed: if Stripe has not accepted the cancellation, keep
                # the local subscription unchanged. Marking it cancelled locally
                # while Stripe keeps billing would silently charge the customer
                # behind a "cancelled" status.
                raise StripeCancellationError(
                    "Stripe subscription cancellation failed; the subscription "
                    "was not cancelled. Please retry later."
                ) from exc

        if immediate:
            return await self.repository.update_status(
                subscription_id, SubscriptionStatus.CANCELLED
            )
        else:
            return await self.repository.cancel_at_period_end(subscription_id)

    async def reactivate_subscription(self, subscription_id: UUID) -> Optional[Subscription]:
        """Reactivate a cancelled subscription"""
        return await self.repository.reactivate(subscription_id)

    async def update_period(
        self, subscription_id: UUID, period_start: datetime, period_end: datetime
    ) -> Optional[Subscription]:
        """Update subscription billing period"""
        return await self.repository.update_period(subscription_id, period_start, period_end)

    async def handle_stripe_webhook(self, event_type: str, data: dict) -> None:
        """Handle Stripe webhook events"""
        if event_type == "customer.subscription.updated":
            await self._handle_subscription_updated(data)
        elif event_type == "customer.subscription.deleted":
            await self._handle_subscription_deleted(data)
        elif event_type == "invoice.payment_succeeded":
            await self._handle_payment_succeeded(data)
        elif event_type == "invoice.payment_failed":
            await self._handle_payment_failed(data)

    async def _handle_subscription_updated(self, data: dict) -> None:
        """Handle subscription update from Stripe"""
        stripe_sub_id = data.get("id")
        subscription = await self.repository.get_by_stripe_subscription_id(stripe_sub_id)
        if subscription:
            status_map = {
                "active": SubscriptionStatus.ACTIVE,
                "canceled": SubscriptionStatus.CANCELLED,
                "past_due": SubscriptionStatus.PAST_DUE,
            }
            status = status_map.get(data.get("status"), SubscriptionStatus.INACTIVE)
            await self.repository.update_status(subscription.id, status)

    async def _handle_subscription_deleted(self, data: dict) -> None:
        """Handle subscription deletion from Stripe"""
        stripe_sub_id = data.get("id")
        subscription = await self.repository.get_by_stripe_subscription_id(stripe_sub_id)
        if subscription:
            await self.repository.update_status(subscription.id, SubscriptionStatus.CANCELLED)

    async def _handle_payment_succeeded(self, data: dict) -> None:
        """Handle successful payment — update billing period and reactivate."""
        # The invoice lines contain period start/end
        stripe_sub_id = data.get("subscription")
        if stripe_sub_id:
            subscription = await self.repository.get_by_stripe_subscription_id(stripe_sub_id)
            if subscription:
                # Extract period from invoice data if available
                period_start = data.get("period_start")
                period_end = data.get("period_end")
                if period_start and period_end:
                    from datetime import datetime as dt

                    ps = (
                        dt.fromtimestamp(period_start)
                        if isinstance(period_start, (int, float))
                        else None
                    )
                    pe = (
                        dt.fromtimestamp(period_end)
                        if isinstance(period_end, (int, float))
                        else None
                    )
                    if ps and pe:
                        await self.repository.update_period(subscription.id, ps, pe)
                # Ensure active status (in case it was past_due)
                await self.repository.update_status(subscription.id, SubscriptionStatus.ACTIVE)

    async def _handle_payment_failed(self, data: dict) -> None:
        """Handle failed payment — mark subscription as past_due."""
        stripe_sub_id = data.get("subscription")
        if stripe_sub_id:
            subscription = await self.repository.get_by_stripe_subscription_id(stripe_sub_id)
            if subscription:
                await self.repository.update_status(subscription.id, SubscriptionStatus.PAST_DUE)

    async def _get_active_team_plan(self, team_id: UUID) -> dict:
        subscription = await self.repository.get_by_team_id(team_id)
        return self._plan_for_subscription(subscription)

    @staticmethod
    def _plan_for_subscription(subscription: Optional[Subscription]) -> dict:
        if subscription and subscription.status == SubscriptionStatus.ACTIVE:
            return get_plan(subscription.plan_name)
        return get_plan(None)

    @staticmethod
    def _limit_exceeded(current: int, limit: Optional[int]) -> bool:
        return limit is not None and current >= limit

    @staticmethod
    def _billing_period(
        subscription: Optional[Subscription],
    ) -> tuple[datetime, datetime]:
        if subscription and subscription.current_period_start and subscription.current_period_end:
            return (
                SubscriptionService._ensure_aware(subscription.current_period_start),
                SubscriptionService._ensure_aware(subscription.current_period_end),
            )

        now = datetime.now(timezone.utc)
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if start.month == 12:
            end = start.replace(year=start.year + 1, month=1)
        else:
            end = start.replace(month=start.month + 1)
        return start, end

    @staticmethod
    def _ensure_aware(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
