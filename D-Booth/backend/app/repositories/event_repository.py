from typing import Optional, List
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import noload
from app.models.models import Event, EventStatus
from app.repositories.base import BaseRepository


class EventRepository(BaseRepository[Event]):
    """Repository for Event model"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(Event, db)

    async def get(self, id: UUID) -> Optional[Event]:
        """Get an event by ID without preloading relationship graphs."""
        result = await self.db.execute(
            select(Event).options(noload("*")).where(Event.id == id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_team(
        self,
        team_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[Event]:
        """Get all events for a team"""
        result = await self.db.execute(
            select(Event)
            .where(Event.team_id == team_id)
            .order_by(Event.start_date.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_by_status(
        self,
        team_id: UUID,
        status: EventStatus,
        skip: int = 0,
        limit: int = 100
    ) -> List[Event]:
        """Get events by status"""
        result = await self.db.execute(
            select(Event)
            .where(
                Event.team_id == team_id,
                Event.status == status
            )
            .order_by(Event.start_date.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_active_events(self, team_id: UUID) -> List[Event]:
        """Get all active events"""
        result = await self.db.execute(
            select(Event).where(
                Event.team_id == team_id,
                Event.status == EventStatus.ACTIVE
            )
        )
        return list(result.scalars().all())
    
    async def get_by_date_range(
        self,
        team_id: UUID,
        start_from: datetime,
        start_to: datetime,
        skip: int = 0,
        limit: int = 100
    ) -> List[Event]:
        """Get events within date range"""
        result = await self.db.execute(
            select(Event)
            .where(
                Event.team_id == team_id,
                Event.start_date >= start_from,
                Event.start_date <= start_to
            )
            .order_by(Event.start_date)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def update_status(
        self,
        event_id: UUID,
        status: EventStatus
    ) -> Optional[Event]:
        """Update event status"""
        stmt = select(Event).options(noload("*")).where(Event.id == event_id)
        result = await self.db.execute(stmt)
        event = result.scalar_one_or_none()
        
        if event:
            event.status = status
            await self.db.commit()
            await self.db.refresh(event)
            return event
        return None
    
    async def count_by_team(self, team_id: UUID) -> int:
        """Count events for a team"""
        result = await self.db.execute(
            select(func.count()).select_from(Event).where(
                Event.team_id == team_id
            )
        )
        return result.scalar_one()
    
    async def count_by_status(
        self,
        team_id: UUID,
        status: EventStatus
    ) -> int:
        """Count events by status"""
        result = await self.db.execute(
            select(func.count()).select_from(Event).where(
                Event.team_id == team_id,
                Event.status == status
            )
        )
        return result.scalar_one()
