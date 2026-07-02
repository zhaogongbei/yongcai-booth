from typing import Optional, List
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.models import Share, Photo, Event, TeamMember
from app.repositories.base import BaseRepository


class ShareRepository(BaseRepository[Share]):
    """Repository for Share model"""

    def __init__(self, db: AsyncSession):
        super().__init__(Share, db)

    async def get_visible_to_user(
        self,
        user_id: UUID,
        channel: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Share]:
        """Get shares scoped to teams the user belongs to, with optional channel filter."""
        stmt = (
            select(Share)
            .join(Photo, Share.photo_id == Photo.id)
            .join(Event, Photo.event_id == Event.id)
            .join(TeamMember, TeamMember.team_id == Event.team_id)
            .where(TeamMember.user_id == user_id)
        )

        # Add channel filter if provided
        if channel:
            stmt = stmt.where(Share.channel == channel)

        stmt = stmt.order_by(Share.created_at.desc()).offset(skip).limit(limit)

        result = await self.db.execute(stmt)
        return list(result.scalars().unique().all())

    async def get_by_photo(self, photo_id: UUID) -> List[Share]:
        """Get all shares for a photo"""
        result = await self.db.execute(
            select(Share)
            .where(Share.photo_id == photo_id)
            .order_by(Share.created_at.desc())
        )
        return list(result.scalars().all())
    
    async def get_by_short_code(self, short_code: str) -> Optional[Share]:
        """Get share by short code"""
        result = await self.db.execute(
            select(Share).where(Share.short_code == short_code)
        )
        return result.scalar_one_or_none()
    
    async def get_by_channel(
        self,
        channel: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Share]:
        """Get shares by channel"""
        result = await self.db.execute(
            select(Share)
            .where(Share.channel == channel)
            .order_by(Share.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def increment_view_count(self, share_id: UUID) -> Optional[Share]:
        """Increment view count"""
        stmt = select(Share).where(Share.id == share_id)
        result = await self.db.execute(stmt)
        share = result.scalar_one_or_none()
        
        if share:
            share.view_count += 1
            await self.db.commit()
            await self.db.refresh(share)
            return share
        return None
    
    async def is_expired(self, share_id: UUID) -> bool:
        """Check if share is expired"""
        stmt = select(Share).where(Share.id == share_id)
        result = await self.db.execute(stmt)
        share = result.scalar_one_or_none()
        
        if not share:
            return True
        
        if share.expires_at and share.expires_at < datetime.now(timezone.utc):
            return True
        
        return False
    
    async def get_total_views(self, photo_id: UUID) -> int:
        """Get total views for a photo"""
        result = await self.db.execute(
            select(func.sum(Share.view_count)).where(
                Share.photo_id == photo_id
            )
        )
        return result.scalar_one() or 0
    
    async def count_by_channel(self) -> dict:
        """Count shares by channel"""
        result = await self.db.execute(
            select(Share.channel, func.count(Share.id))
            .group_by(Share.channel)
        )
        return {row[0]: row[1] for row in result.all()}

    async def count_by_event(self, event_id: UUID) -> int:
        """Count shares for an event (via photo, single join)."""
        result = await self.db.execute(
            select(func.count())
            .select_from(Share)
            .join(Photo, Share.photo_id == Photo.id)
            .where(Photo.event_id == event_id)
        )
        return result.scalar_one()
