from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Webhook, WebhookLog
from app.repositories.base import BaseRepository


class WebhookRepository(BaseRepository[Webhook]):
    """Repository for Webhook model"""

    def __init__(self, db: AsyncSession):
        super().__init__(Webhook, db)

    async def get_by_team_id(self, team_id: UUID) -> List[Webhook]:
        """Get all webhooks for a team"""
        result = await self.db.execute(
            select(Webhook)
            .where(Webhook.team_id == team_id, Webhook.enabled == True)
            .order_by(Webhook.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_event_type(self, team_id: UUID, event_type: str) -> List[Webhook]:
        """Get webhooks for a team that are subscribed to the event type"""
        result = await self.db.execute(
            select(Webhook).where(
                Webhook.team_id == team_id,
                Webhook.enabled == True,
                Webhook.events.contains([event_type]),
            )
        )
        return list(result.scalars().all())


class WebhookLogRepository(BaseRepository[WebhookLog]):
    """Repository for WebhookLog model"""

    def __init__(self, db: AsyncSession):
        super().__init__(WebhookLog, db)

    async def get_by_webhook_id(
        self, webhook_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[WebhookLog]:
        """Get webhook logs for a specific webhook"""
        result = await self.db.execute(
            select(WebhookLog)
            .where(WebhookLog.webhook_id == webhook_id)
            .order_by(WebhookLog.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
