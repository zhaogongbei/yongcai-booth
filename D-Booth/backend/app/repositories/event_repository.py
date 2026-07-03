from typing import Optional, List
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import noload
from app.models.models import Event, EventStatus
from app.repositories.base import BaseRepository, log_query_performance
from app.repositories.cache_decorator import cached, invalidate_cache


class EventRepository(BaseRepository[Event]):
    """
    Repository for Event model with caching and performance optimizations.

    Provides methods for:
    - Querying events by team, status, or date range
    - Status management
    - Aggregate queries (counting by team/status)
    - Cached queries for frequently accessed data
    """

    def __init__(self, db: AsyncSession):
        super().__init__(Event, db)
    @log_query_performance(threshold_ms=50.0)
    @cached(ttl=300, key_builder=lambda self, id: f"event:{id}")
    async def get(self, id: UUID) -> Optional[Event]:
        """
        Get an event by ID without preloading relationship graphs.

        Results are cached for 5 minutes.

        Args:
            id: Event identifier

        Returns:
            Event instance if found, None otherwise
        """
        result = await self.db.execute(
            select(Event).options(noload("*")).where(Event.id == id)
        )
        return result.scalar_one_or_none()

    @log_query_performance(threshold_ms=150.0)
    @cached(ttl=300, key_builder=lambda self, team_id, skip, limit: f"team:{team_id}:events:{skip}:{limit}")
    async def get_by_team(
        self,
        team_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[Event]:
        """
        Get all events for a team.

        Results are cached for 5 minutes.

        Args:
            team_id: Team identifier
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of Event instances ordered by start date (newest first)
        """
        result = await self.db.execute(
            select(Event)
            .where(Event.team_id == team_id)
            .order_by(Event.start_date.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    @log_query_performance(threshold_ms=150.0)
    @cached(ttl=300, key_builder=lambda self, team_id, status, skip, limit: f"team:{team_id}:events:status:{status}:{skip}:{limit}")
    async def get_by_status(
        self,
        team_id: UUID,
        status: EventStatus,
        skip: int = 0,
        limit: int = 100
    ) -> List[Event]:
        """
        Get events by status for a team.

        Args:
            team_id: Team identifier
            status: Event status filter
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of Event instances matching the status
        """
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

    @log_query_performance(threshold_ms=100.0)
    @cached(ttl=60, key_builder=lambda self, team_id: f"team:{team_id}:active_events")
    async def get_active_events(self, team_id: UUID) -> List[Event]:
        """
        Get all active events for a team.

        Cached for 1 minute since active status changes frequently.

        Args:
            team_id: Team identifier

        Returns:
            List of active Event instances
        """
        result = await self.db.execute(
            select(Event).where(
                Event.team_id == team_id,
                Event.status == EventStatus.ACTIVE
            )
        )
        return list(result.scalars().all())

    @log_query_performance(threshold_ms=150.0)
    async def get_by_date_range(
        self,
        team_id: UUID,
        start_from: datetime,
        start_to: datetime,
        skip: int = 0,
        limit: int = 100
    ) -> List[Event]:
        """
        Get events within a date range for a team.

        Not cached due to dynamic date range queries.

        Args:
            team_id: Team identifier
            start_from: Start of date range (inclusive)
            start_to: End of date range (inclusive)
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of Event instances within the date range
        """
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

    @log_query_performance(threshold_ms=100.0)
    @invalidate_cache("event:*")
    @invalidate_cache("team:*:events:*")
    @invalidate_cache("team:*:active_events")
    async def update_status(
        self,
        event_id: UUID,
        status: EventStatus
    ) -> Optional[Event]:
        """
        Update event status and invalidate related caches.

        Args:
            event_id: Event identifier
            status: New status

        Returns:
            Updated Event instance, or None if not found
        """
        stmt = select(Event).options(noload("*")).where(Event.id == event_id)
        result = await self.db.execute(stmt)
        event = result.scalar_one_or_none()

        if event:
            event.status = status
            await self.db.commit()
            await self.db.refresh(event)
            return event
        return None

    @log_query_performance(threshold_ms=50.0)
    @cached(ttl=600, key_builder=lambda self, team_id: f"team:{team_id}:event_count")
    async def count_by_team(self, team_id: UUID) -> int:
        """
        Count events for a team.

        Args:
            team_id: Team identifier

        Returns:
            Total number of events for the team
        """
        result = await self.db.execute(
            select(func.count()).select_from(Event).where(
                Event.team_id == team_id
            )
        )
        return result.scalar_one()

    @log_query_performance(threshold_ms=50.0)
    @cached(ttl=300, key_builder=lambda self, team_id, status: f"team:{team_id}:event_count:status:{status}")
    async def count_by_status(
        self,
        team_id: UUID,
        status: EventStatus
    ) -> int:
        """
        Count events by status for a team.

        Args:
            team_id: Team identifier
            status: Event status filter

        Returns:
            Number of events matching the status
        """
        result = await self.db.execute(
            select(func.count()).select_from(Event).where(
                Event.team_id == team_id,
                Event.status == status
            )
        )
        return result.scalar_one()

    @invalidate_cache("event:*")
    @invalidate_cache("team:*:events:*")
    @invalidate_cache("team:*:active_events")
    async def create(self, obj_in: dict) -> Event:
        """
        Create a new event and invalidate related caches.

        Args:
            obj_in: Event data dictionary

        Returns:
            Created Event instance
        """
        return await super().create(obj_in)

    @invalidate_cache("event:*")
    @invalidate_cache("team:*:events:*")
    @invalidate_cache("team:*:active_events")
    async def update(self, id: UUID, obj_in: dict) -> Optional[Event]:
        """
        Update event and invalidate related caches.

        Args:
            id: Event identifier
            obj_in: Fields to update

        Returns:
            Updated Event instance, or None if not found
        """
        return await super().update(id, obj_in)

    @invalidate_cache("event:*")
    @invalidate_cache("team:*:events:*")
    @invalidate_cache("team:*:active_events")
    async def bulk_create(
        self,
        objects_in: List[dict],
        batch_size: int = 500
    ) -> List[Event]:
        """
        Bulk create events with cache invalidation.

        Args:
            objects_in: List of event data dictionaries
            batch_size: Number of events to insert per batch

        Returns:
            List of created Event instances
        """
        return await super().bulk_create(objects_in, batch_size)

