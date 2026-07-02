from typing import Optional
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.models import Subscription, SubscriptionStatus, Team
from app.repositories.base import BaseRepository


class SubscriptionRepository(BaseRepository[Subscription]):
    """Repository for Subscription model"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(Subscription, db)
    
    async def get_by_stripe_subscription_id(
        self,
        stripe_subscription_id: str
    ) -> Optional[Subscription]:
        """Get subscription by Stripe subscription ID"""
        result = await self.db.execute(
            select(Subscription).where(
                Subscription.stripe_subscription_id == stripe_subscription_id
            )
        )
        return result.scalar_one_or_none()
    
    async def get_by_stripe_customer_id(
        self,
        stripe_customer_id: str
    ) -> Optional[Subscription]:
        """Get subscription by Stripe customer ID"""
        result = await self.db.execute(
            select(Subscription).where(
                Subscription.stripe_customer_id == stripe_customer_id
            )
        )
        return result.scalar_one_or_none()

    async def get_by_team_id(self, team_id: UUID) -> Optional[Subscription]:
        """Get the subscription linked to a team."""
        result = await self.db.execute(
            select(Subscription)
            .join(Team, Team.subscription_id == Subscription.id)
            .where(Team.id == team_id)
        )
        return result.scalar_one_or_none()
    
    async def get_active_subscriptions(self) -> list[Subscription]:
        """Get all active subscriptions"""
        result = await self.db.execute(
            select(Subscription).where(
                Subscription.status == SubscriptionStatus.ACTIVE
            )
        )
        return list(result.scalars().all())
    
    async def update_status(
        self,
        subscription_id: UUID,
        status: SubscriptionStatus
    ) -> Optional[Subscription]:
        """Update subscription status"""
        stmt = select(Subscription).where(Subscription.id == subscription_id)
        result = await self.db.execute(stmt)
        subscription = result.scalar_one_or_none()
        
        if subscription:
            subscription.status = status
            await self.db.commit()
            await self.db.refresh(subscription)
            return subscription
        return None
    
    async def update_period(
        self,
        subscription_id: UUID,
        period_start: datetime,
        period_end: datetime
    ) -> Optional[Subscription]:
        """Update subscription period"""
        stmt = select(Subscription).where(Subscription.id == subscription_id)
        result = await self.db.execute(stmt)
        subscription = result.scalar_one_or_none()
        
        if subscription:
            subscription.current_period_start = period_start
            subscription.current_period_end = period_end
            await self.db.commit()
            await self.db.refresh(subscription)
            return subscription
        return None
    
    async def cancel_at_period_end(
        self,
        subscription_id: UUID
    ) -> Optional[Subscription]:
        """Mark subscription to cancel at period end"""
        stmt = select(Subscription).where(Subscription.id == subscription_id)
        result = await self.db.execute(stmt)
        subscription = result.scalar_one_or_none()
        
        if subscription:
            subscription.cancel_at_period_end = True
            await self.db.commit()
            await self.db.refresh(subscription)
            return subscription
        return None
    
    async def reactivate(
        self,
        subscription_id: UUID
    ) -> Optional[Subscription]:
        """Reactivate a cancelled subscription"""
        stmt = select(Subscription).where(Subscription.id == subscription_id)
        result = await self.db.execute(stmt)
        subscription = result.scalar_one_or_none()
        
        if subscription:
            subscription.cancel_at_period_end = False
            subscription.status = SubscriptionStatus.ACTIVE
            await self.db.commit()
            await self.db.refresh(subscription)
            return subscription
        return None
