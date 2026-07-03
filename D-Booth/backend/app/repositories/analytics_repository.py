from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import AnalyticsEvent
from app.repositories.base import BaseRepository


class AnalyticsRepository(BaseRepository[AnalyticsEvent]):
    """Repository for AnalyticsEvent model"""

    def __init__(self, db: AsyncSession):
        super().__init__(AnalyticsEvent, db)

    async def get_by_team(
        self, team_id: UUID, skip: int = 0, limit: int = 1000
    ) -> List[AnalyticsEvent]:
        """Get all analytics events for a team"""
        result = await self.db.execute(
            select(AnalyticsEvent)
            .where(AnalyticsEvent.team_id == team_id)
            .order_by(AnalyticsEvent.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_event(
        self, event_id: UUID, skip: int = 0, limit: int = 1000
    ) -> List[AnalyticsEvent]:
        """Get analytics for a specific event"""
        result = await self.db.execute(
            select(AnalyticsEvent)
            .where(AnalyticsEvent.event_id == event_id)
            .order_by(AnalyticsEvent.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_type(
        self, team_id: UUID, event_type: str, skip: int = 0, limit: int = 1000
    ) -> List[AnalyticsEvent]:
        """Get analytics by event type"""
        result = await self.db.execute(
            select(AnalyticsEvent)
            .where(AnalyticsEvent.team_id == team_id, AnalyticsEvent.event_type == event_type)
            .order_by(AnalyticsEvent.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_date_range(
        self, team_id: UUID, start_date: datetime, end_date: datetime
    ) -> List[AnalyticsEvent]:
        """Get analytics within date range"""
        result = await self.db.execute(
            select(AnalyticsEvent)
            .where(
                AnalyticsEvent.team_id == team_id,
                AnalyticsEvent.created_at >= start_date,
                AnalyticsEvent.created_at <= end_date,
            )
            .order_by(AnalyticsEvent.created_at)
        )
        return list(result.scalars().all())

    async def count_by_type(self, team_id: UUID) -> dict:
        """Count events by type"""
        result = await self.db.execute(
            select(AnalyticsEvent.event_type, func.count(AnalyticsEvent.id))
            .where(AnalyticsEvent.team_id == team_id)
            .group_by(AnalyticsEvent.event_type)
        )
        return {row[0]: row[1] for row in result.all()}

    async def count_unique_users(self, team_id: UUID) -> int:
        """Count unique users"""
        result = await self.db.execute(
            select(func.count(distinct(AnalyticsEvent.user_id))).where(
                AnalyticsEvent.team_id == team_id
            )
        )
        return result.scalar_one()

    async def count_unique_sessions(self, team_id: UUID) -> int:
        """Count unique sessions"""
        result = await self.db.execute(
            select(func.count(distinct(AnalyticsEvent.session_id))).where(
                AnalyticsEvent.team_id == team_id
            )
        )
        return result.scalar_one()

    async def track_event(
        self,
        team_id: UUID,
        event_type: str,
        properties: Optional[Dict[str, Any]] = None,
        event_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
        session_id: Optional[str] = None,
    ) -> AnalyticsEvent:
        """Track a new analytics event"""
        event = AnalyticsEvent(
            team_id=team_id,
            event_type=event_type,
            properties=properties,
            event_id=event_id,
            user_id=user_id,
            session_id=session_id,
        )
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(event)
        return event
