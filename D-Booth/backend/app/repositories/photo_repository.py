from typing import List, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.models import Event, Photo, PhotoSession, TeamMember
from app.repositories.base import BaseRepository, log_query_performance
from app.repositories.cache_decorator import cached, invalidate_cache


class PhotoRepository(BaseRepository[Photo]):
    """
    Repository for Photo model with caching support.

    Provides methods for:
    - Querying photos by event, session, or user access
    - Counting photos and calculating storage usage
    - Bulk photo operations
    - Performance-optimized queries with eager loading
    """

    def __init__(self, db: AsyncSession):
        super().__init__(Photo, db)

    @log_query_performance(threshold_ms=200.0)
    @cached(
        ttl=300,
        key_builder=lambda self, event_id, skip, limit: f"event:{event_id}:photos:{skip}:{limit}",
    )
    async def get_by_event(self, event_id: UUID, skip: int = 0, limit: int = 100) -> List[Photo]:
        """
        Get all photos for an event with preloaded relationships.

        Prevents N+1 queries by eager loading event, session, and ai_tasks.
        Results are cached for 5 minutes.

        Args:
            event_id: Event identifier
            skip: Number of records to skip (pagination offset)
            limit: Maximum number of records to return

        Returns:
            List of Photo instances with preloaded relationships

        Example:
            photos = await photo_repo.get_by_event(event_id, skip=0, limit=50)
        """
        result = await self.db.execute(
            select(Photo)
            .where(Photo.event_id == event_id)
            .options(
                selectinload(Photo.event), selectinload(Photo.session), selectinload(Photo.ai_tasks)
            )
            .order_by(Photo.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    @log_query_performance(threshold_ms=200.0)
    @cached(
        ttl=300,
        key_builder=lambda self, session_id, skip, limit: f"session:{session_id}:photos:{skip}:{limit}",
    )
    async def get_by_session(
        self, session_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[Photo]:
        """
        Get all photos for a session with preloaded relationships.

        Args:
            session_id: PhotoSession identifier
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of Photo instances ordered by creation time
        """
        result = await self.db.execute(
            select(Photo)
            .where(Photo.session_id == session_id)
            .options(
                selectinload(Photo.event), selectinload(Photo.session), selectinload(Photo.ai_tasks)
            )
            .order_by(Photo.created_at)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    @log_query_performance(threshold_ms=300.0)
    async def get_visible_to_user(
        self, user_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[Photo]:
        """
        Get photos from events owned by teams the user belongs to.

        Preloads relationships to prevent N+1 queries.

        Args:
            user_id: User identifier
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of Photo instances the user has access to
        """
        result = await self.db.execute(
            select(Photo)
            .join(Event, Photo.event_id == Event.id)
            .join(TeamMember, TeamMember.team_id == Event.team_id)
            .where(TeamMember.user_id == user_id)
            .options(
                selectinload(Photo.event), selectinload(Photo.session), selectinload(Photo.ai_tasks)
            )
            .order_by(Photo.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().unique().all())

    @log_query_performance(threshold_ms=100.0)
    @cached(ttl=600, key_builder=lambda self, event_id: f"event:{event_id}:photo_count")
    async def count_by_event(self, event_id: UUID) -> int:
        """
        Count photos for an event.

        Cached for 10 minutes since counts change infrequently.

        Args:
            event_id: Event identifier

        Returns:
            Total number of photos for the event
        """
        result = await self.db.execute(
            select(func.count()).select_from(Photo).where(Photo.event_id == event_id)
        )
        return result.scalar_one()

    @log_query_performance(threshold_ms=150.0)
    @cached(ttl=600, key_builder=lambda self, team_id: f"team:{team_id}:photo_count")
    async def count_by_team(self, team_id: UUID) -> int:
        """
        Count photos across all events for a team.

        Args:
            team_id: Team identifier

        Returns:
            Total number of photos across all team events
        """
        result = await self.db.execute(
            select(func.count())
            .select_from(Photo)
            .join(Event, Photo.event_id == Event.id)
            .where(Event.team_id == team_id)
        )
        return result.scalar_one()

    @log_query_performance(threshold_ms=100.0)
    @cached(ttl=300, key_builder=lambda self, session_id: f"session:{session_id}:photo_count")
    async def count_by_session(self, session_id: UUID) -> int:
        """
        Count photos for a session.

        Args:
            session_id: PhotoSession identifier

        Returns:
            Total number of photos in the session
        """
        result = await self.db.execute(
            select(func.count()).select_from(Photo).where(Photo.session_id == session_id)
        )
        return result.scalar_one()

    @log_query_performance(threshold_ms=100.0)
    @cached(ttl=600, key_builder=lambda self, event_id: f"event:{event_id}:total_size")
    async def get_total_file_size(self, event_id: UUID) -> int:
        """
        Get total file size for event photos in bytes.

        Args:
            event_id: Event identifier

        Returns:
            Total file size in bytes (0 if no photos)
        """
        result = await self.db.execute(
            select(func.sum(Photo.file_size)).where(Photo.event_id == event_id)
        )
        return result.scalar_one() or 0

    @invalidate_cache("event:*:photos:*")
    @invalidate_cache("session:*:photos:*")
    async def create(self, obj_in: dict) -> Photo:
        """
        Create a new photo and invalidate related caches.

        Args:
            obj_in: Photo data dictionary

        Returns:
            Created Photo instance
        """
        return await super().create(obj_in)

    @invalidate_cache("event:*:photos:*")
    @invalidate_cache("session:*:photos:*")
    async def bulk_create(self, objects_in: List[dict], batch_size: int = 500) -> List[Photo]:
        """
        Bulk create photos with cache invalidation.

        Args:
            objects_in: List of photo data dictionaries
            batch_size: Number of photos to insert per batch

        Returns:
            List of created Photo instances
        """
        return await super().bulk_create(objects_in, batch_size)


class PhotoSessionRepository(BaseRepository[PhotoSession]):
    """
    Repository for PhotoSession model with performance optimizations.

    Provides methods for:
    - Querying sessions by event
    - Managing session lifecycle (active/completed)
    - Eager loading photos to prevent N+1 queries
    """

    def __init__(self, db: AsyncSession):
        super().__init__(PhotoSession, db)

    @log_query_performance(threshold_ms=150.0)
    @cached(
        ttl=300,
        key_builder=lambda self, event_id, skip, limit: f"event:{event_id}:sessions:{skip}:{limit}",
    )
    async def get_by_event(
        self, event_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[PhotoSession]:
        """
        Get all sessions for an event.

        Args:
            event_id: Event identifier
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of PhotoSession instances ordered by start time (newest first)
        """
        result = await self.db.execute(
            select(PhotoSession)
            .where(PhotoSession.event_id == event_id)
            .order_by(PhotoSession.started_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    @log_query_performance(threshold_ms=150.0)
    async def get_with_photos(self, session_id: UUID) -> Optional[PhotoSession]:
        """
        Get session with all photos eagerly loaded.

        Args:
            session_id: PhotoSession identifier

        Returns:
            PhotoSession with photos relationship loaded, or None if not found
        """
        result = await self.db.execute(
            select(PhotoSession)
            .where(PhotoSession.id == session_id)
            .options(selectinload(PhotoSession.photos))
        )
        return result.scalar_one_or_none()

    @log_query_performance(threshold_ms=150.0)
    @cached(ttl=60, key_builder=lambda self, event_id: f"event:{event_id}:active_sessions")
    async def get_active_sessions(self, event_id: UUID) -> List[PhotoSession]:
        """
        Get active sessions (not completed) for an event.

        Cached for 1 minute since active status changes frequently.

        Args:
            event_id: Event identifier

        Returns:
            List of active PhotoSession instances
        """
        result = await self.db.execute(
            select(PhotoSession).where(
                PhotoSession.event_id == event_id, PhotoSession.completed_at.is_(None)
            )
        )
        return list(result.scalars().all())

    @log_query_performance(threshold_ms=100.0)
    @invalidate_cache("event:*:sessions:*")
    @invalidate_cache("event:*:active_sessions")
    async def complete_session(self, session_id: UUID) -> Optional[PhotoSession]:
        """
        Mark session as completed and invalidate related caches.

        Args:
            session_id: PhotoSession identifier

        Returns:
            Updated PhotoSession instance, or None if not found
        """
        from datetime import datetime, timezone

        stmt = select(PhotoSession).where(PhotoSession.id == session_id)
        result = await self.db.execute(stmt)
        session = result.scalar_one_or_none()

        if session:
            session.completed_at = datetime.now(timezone.utc)
            await self.db.commit()
            await self.db.refresh(session)
            return session
        return None

    @log_query_performance(threshold_ms=100.0)
    @cached(ttl=600, key_builder=lambda self, event_id: f"event:{event_id}:session_count")
    async def count_by_event(self, event_id: UUID) -> int:
        """
        Count sessions for an event.

        Args:
            event_id: Event identifier

        Returns:
            Total number of sessions for the event
        """
        result = await self.db.execute(
            select(func.count()).select_from(PhotoSession).where(PhotoSession.event_id == event_id)
        )
        return result.scalar_one()

    @invalidate_cache("event:*:sessions:*")
    @invalidate_cache("event:*:active_sessions")
    async def create(self, obj_in: dict) -> PhotoSession:
        """
        Create a new session and invalidate related caches.

        Args:
            obj_in: PhotoSession data dictionary

        Returns:
            Created PhotoSession instance
        """
        return await super().create(obj_in)

    @invalidate_cache("event:*:sessions:*")
    @invalidate_cache("event:*:active_sessions")
    async def bulk_create(
        self, objects_in: List[dict], batch_size: int = 500
    ) -> List[PhotoSession]:
        """
        Bulk create photo sessions with cache invalidation.

        Args:
            objects_in: List of session data dictionaries
            batch_size: Number of sessions to insert per batch

        Returns:
            List of created PhotoSession instances
        """
        return await super().bulk_create(objects_in, batch_size)
