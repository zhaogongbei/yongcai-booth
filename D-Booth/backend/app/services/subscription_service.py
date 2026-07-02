from typing import Optional
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.plans import get_plan, list_plans, normalize_plan_id
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
from app.models.models import Subscription, SubscriptionStatus


class SubscriptionService:
    """Service for subscription business logic"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = SubscriptionRepository(db)
    
    async def get_subscription(self, subscription_id: UUID) -> Optional[Subscription]:
        """Get subscription by ID"""
        return await self.repository.get(subscription_id)
    
    async def get_by_stripe_id(
        self,
        stripe_subscription_id: str
    ) -> Optional[Subscription]:
        """Get subscription by Stripe subscription ID"""
        return await self.repository.get_by_stripe_subscription_id(
            stripe_subscription_id
        )

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
        plan = await self._get_active_team_plan(team_id)
        limit = plan["limits"]["max_events"]
        current = await EventRepository(self.db).count_by_team(team_id)
        if self._limit_exceeded(current, limit):
            raise ValueError(
                f"Event quota exceeded for plan '{plan['id']}' "
                f"({current}/{limit})"
            )

    async def ensure_can_upload_photo(self, team_id: UUID, event_id: UUID) -> None:
        plan = await self._get_active_team_plan(team_id)
        limit = plan["limits"]["photos_per_event"]
        current = await PhotoRepository(self.db).count_by_event(event_id)
        if self._limit_exceeded(current, limit):
            raise ValueError(
                f"Photo quota exceeded for plan '{plan['id']}' "
                f"({current}/{limit} photos per event)"
            )

    async def ensure_can_create_ai_task(self, team_id: UUID) -> None:
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
                f"AI credit quota exceeded for plan '{plan['id']}' "
                f"({current}/{limit})"
            )
    
    async def create_subscription(
        self,
        subscription_in: SubscriptionCreate
    ) -> Subscription:
        """Create a new subscription"""
        plan_id = normalize_plan_id(subscription_in.plan_name)
        if plan_id != subscription_in.plan_name.strip().lower():
            raise ValueError(f"Unknown subscription plan '{subscription_in.plan_name}'")

        subscription_data = {
            **subscription_in.model_dump(),
            "plan_name": plan_id,
            "status": SubscriptionStatus.ACTIVE,
        }
        return await self.repository.create(subscription_data)
    
    async def update_subscription(
        self,
        subscription_id: UUID,
        subscription_in: SubscriptionUpdate
    ) -> Optional[Subscription]:
        """Update subscription"""
        update_data = subscription_in.model_dump(exclude_unset=True)
        if "plan_name" in update_data and update_data["plan_name"] is not None:
            plan_id = normalize_plan_id(update_data["plan_name"])
            if plan_id != update_data["plan_name"].strip().lower():
                raise ValueError(f"Unknown subscription plan '{update_data['plan_name']}'")
            update_data["plan_name"] = plan_id
        return await self.repository.update(subscription_id, update_data)
    
    async def cancel_subscription(
        self,
        subscription_id: UUID,
        immediate: bool = False
    ) -> Optional[Subscription]:
        """Cancel a subscription locally and at Stripe."""
        subscription = await self.repository.get(subscription_id)
        if not subscription:
            return None

        # Notify Stripe if a stripe_subscription_id is linked
        if subscription.stripe_subscription_id:
            try:
                import stripe
                stripe.api_key = settings.STRIPE_SECRET_KEY
                if immediate:
                    stripe.Subscription.delete(subscription.stripe_subscription_id)
                else:
                    stripe.Subscription.modify(
                        subscription.stripe_subscription_id,
                        cancel_at_period_end=True
                    )
            except Exception:
                # Stripe unreachable — still cancel locally; Stripe will
                # sync via webhook when it comes back online.
                pass

        if immediate:
            return await self.repository.update_status(
                subscription_id,
                SubscriptionStatus.CANCELLED
            )
        else:
            return await self.repository.cancel_at_period_end(subscription_id)
    
    async def reactivate_subscription(
        self,
        subscription_id: UUID
    ) -> Optional[Subscription]:
        """Reactivate a cancelled subscription"""
        return await self.repository.reactivate(subscription_id)
    
    async def update_period(
        self,
        subscription_id: UUID,
        period_start: datetime,
        period_end: datetime
    ) -> Optional[Subscription]:
        """Update subscription billing period"""
        return await self.repository.update_period(
            subscription_id,
            period_start,
            period_end
        )
    
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
        subscription = await self.repository.get_by_stripe_subscription_id(
            stripe_sub_id
        )
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
        subscription = await self.repository.get_by_stripe_subscription_id(
            stripe_sub_id
        )
        if subscription:
            await self.repository.update_status(
                subscription.id,
                SubscriptionStatus.CANCELLED
            )
    
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
                    ps = dt.fromtimestamp(period_start) if isinstance(period_start, (int, float)) else None
                    pe = dt.fromtimestamp(period_end) if isinstance(period_end, (int, float)) else None
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
