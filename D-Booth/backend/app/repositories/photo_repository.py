from typing import Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from app.models.models import Event, Photo, PhotoSession, TeamMember
from app.repositories.base import BaseRepository


class PhotoRepository(BaseRepository[Photo]):
    """Repository for Photo model"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(Photo, db)
    
    async def get_by_event(
        self,
        event_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[Photo]:
        """
        Get all photos for an event with preloaded relationships.
        Prevents N+1 queries by eager loading event, session, and ai_tasks.
        """
        result = await self.db.execute(
            select(Photo)
            .where(Photo.event_id == event_id)
            .options(
                selectinload(Photo.event),
                selectinload(Photo.session),
                selectinload(Photo.ai_tasks)
            )
            .order_by(Photo.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_session(
        self,
        session_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[Photo]:
        """
        Get all photos for a session with preloaded relationships.
        """
        result = await self.db.execute(
            select(Photo)
            .where(Photo.session_id == session_id)
            .options(
                selectinload(Photo.event),
                selectinload(Photo.session),
                selectinload(Photo.ai_tasks)
            )
            .order_by(Photo.created_at)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_visible_to_user(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[Photo]:
        """
        Get photos from events owned by teams the user belongs to.
        Preloads relationships to prevent N+1 queries.
        """
        result = await self.db.execute(
            select(Photo)
            .join(Event, Photo.event_id == Event.id)
            .join(TeamMember, TeamMember.team_id == Event.team_id)
            .where(TeamMember.user_id == user_id)
            .options(
                selectinload(Photo.event),
                selectinload(Photo.session),
                selectinload(Photo.ai_tasks)
            )
            .order_by(Photo.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().unique().all())
    
    async def count_by_event(self, event_id: UUID) -> int:
        """Count photos for an event"""
        result = await self.db.execute(
            select(func.count()).select_from(Photo).where(
                Photo.event_id == event_id
            )
        )
        return result.scalar_one()

    async def count_by_team(self, team_id: UUID) -> int:
        """Count photos across all events for a team."""
        result = await self.db.execute(
            select(func.count())
            .select_from(Photo)
            .join(Event, Photo.event_id == Event.id)
            .where(Event.team_id == team_id)
        )
        return result.scalar_one()
    
    async def count_by_session(self, session_id: UUID) -> int:
        """Count photos for a session"""
        result = await self.db.execute(
            select(func.count()).select_from(Photo).where(
                Photo.session_id == session_id
            )
        )
        return result.scalar_one()
    
    async def get_total_file_size(self, event_id: UUID) -> int:
        """Get total file size for event photos"""
        result = await self.db.execute(
            select(func.sum(Photo.file_size)).where(
                Photo.event_id == event_id
            )
        )
        return result.scalar_one() or 0


class PhotoSessionRepository(BaseRepository[PhotoSession]):
    """Repository for PhotoSession model"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(PhotoSession, db)
    
    async def get_by_event(
        self,
        event_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[PhotoSession]:
        """Get all sessions for an event"""
        result = await self.db.execute(
            select(PhotoSession)
            .where(PhotoSession.event_id == event_id)
            .order_by(PhotoSession.started_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_with_photos(self, session_id: UUID) -> Optional[PhotoSession]:
        """Get session with all photos"""
        result = await self.db.execute(
            select(PhotoSession)
            .where(PhotoSession.id == session_id)
            .options(selectinload(PhotoSession.photos))
        )
        return result.scalar_one_or_none()
    
    async def get_active_sessions(self, event_id: UUID) -> List[PhotoSession]:
        """Get active sessions (not completed)"""
        result = await self.db.execute(
            select(PhotoSession).where(
                PhotoSession.event_id == event_id,
                PhotoSession.completed_at.is_(None)
            )
        )
        return list(result.scalars().all())
    
    async def complete_session(self, session_id: UUID) -> Optional[PhotoSession]:
        """Mark session as completed"""
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
    
    async def count_by_event(self, event_id: UUID) -> int:
        """Count sessions for an event"""
        result = await self.db.execute(
            select(func.count()).select_from(PhotoSession).where(
                PhotoSession.event_id == event_id
            )
        )
        return result.scalar_one()
