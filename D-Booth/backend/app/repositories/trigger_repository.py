from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import TriggerConfig, TriggerLog, TriggerType
from app.repositories.base import BaseRepository


class TriggerConfigRepository(BaseRepository[TriggerConfig]):
    """Repository for TriggerConfig model"""

    def __init__(self, db: AsyncSession):
        super().__init__(TriggerConfig, db)

    async def get_by_event_id(self, event_id: UUID) -> List[TriggerConfig]:
        """Get all trigger configs for an event"""
        result = await self.db.execute(
            select(TriggerConfig)
            .where(TriggerConfig.event_id == event_id)
            .order_by(TriggerConfig.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_event_and_type(
        self, event_id: UUID, event_type: TriggerType
    ) -> List[TriggerConfig]:
        """Get enabled trigger configs for an event and type"""
        result = await self.db.execute(
            select(TriggerConfig).where(
                TriggerConfig.event_id == event_id,
                TriggerConfig.event_type == event_type,
                TriggerConfig.enabled == True,
            )
        )
        return list(result.scalars().all())


class TriggerLogRepository(BaseRepository[TriggerLog]):
    """Repository for TriggerLog model"""

    def __init__(self, db: AsyncSession):
        super().__init__(TriggerLog, db)

    async def get_by_event_id(
        self, event_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[TriggerLog]:
        """Get trigger logs for an event"""
        result = await self.db.execute(
            select(TriggerLog)
            .where(TriggerLog.event_id == event_id)
            .order_by(TriggerLog.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_trigger_id(
        self, trigger_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[TriggerLog]:
        """Get trigger logs for a specific trigger"""
        result = await self.db.execute(
            select(TriggerLog)
            .where(TriggerLog.trigger_id == trigger_id)
            .order_by(TriggerLog.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
