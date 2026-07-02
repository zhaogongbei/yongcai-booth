from typing import Optional, List
from uuid import UUID
import secrets
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.share_repository import ShareRepository
from app.schemas.share import ShareCreate
from app.models.models import Share, Photo


class ShareService:
    """Service for share business logic"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = ShareRepository(db)

    @staticmethod
    def generate_short_code(length: int = 8) -> str:
        """Generate a random short code"""
        return secrets.token_urlsafe(length)[:length]

    async def create_share(
        self,
        share_in: ShareCreate,
        base_url: str = "https://aibooth.app"
    ) -> Share:
        """Create a new share link"""
        # Generate unique short code
        short_code = self.generate_short_code()

        # Ensure uniqueness
        while await self.repository.get_by_short_code(short_code):
            short_code = self.generate_short_code()

        # Generate full URL
        full_url = f"{base_url}/s/{short_code}"

        # Set default expiration if not provided (7 days)
        expires_at = share_in.expires_at
        if not expires_at:
            expires_at = datetime.now(timezone.utc) + timedelta(days=7)

        share_data = {
            **share_in.model_dump(exclude={"expires_at"}),
            "short_code": short_code,
            "full_url": full_url,
            "expires_at": expires_at,
            "view_count": 0,
        }

        return await self.repository.create(share_data)

    async def get_share_by_code(self, short_code: str) -> Optional[Share]:
        """Get share by short code"""
        return await self.repository.get_by_short_code(short_code)

    async def get_share(self, share_id: UUID) -> Optional[Share]:
        """Get share by ID"""
        return await self.repository.get(share_id)

    async def get_shares(
        self,
        photo_id: Optional[UUID] = None,
        channel: Optional[str] = None,
        team_event_ids: Optional[List[UUID]] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Share]:
        """Get shares with optional filters.

        When ``photo_id`` is given, return shares for that photo.
        Otherwise scope to events in ``team_event_ids`` (IDOR guard).
        """
        if photo_id:
            return await self.repository.get_by_photo(photo_id)

        if channel:
            return await self.repository.get_by_channel(channel, skip, limit)

        # Fallback: scope via team_event_ids if available
        if team_event_ids:
            stmt = (
                select(Share)
                .join(Photo, Share.photo_id == Photo.id)
                .where(Photo.event_id.in_(team_event_ids))
                .order_by(Share.created_at.desc())
                .offset(skip)
                .limit(limit)
            )
            result = await self.db.execute(stmt)
            return list(result.scalars().all())

        return await self.repository.get_multi(skip, limit)

    async def get_shares_visible_to_user(
        self,
        user_id: UUID,
        channel: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Share]:
        """Get shares scoped to teams the user belongs to, with optional channel filter."""
        return await self.repository.get_visible_to_user(user_id, channel, skip, limit)

    async def increment_view(self, share_id: UUID) -> Optional[Share]:
        """Increment view count"""
        return await self.repository.increment_view_count(share_id)

    # Alias to match route layer naming convention
    async def increment_view_count(self, share_id: UUID) -> Optional[Share]:
        """Increment view count (alias)"""
        return await self.increment_view(share_id)

    async def is_expired(self, share_id: UUID) -> bool:
        """Check if share is expired"""
        return await self.repository.is_expired(share_id)

    async def delete_share(self, share_id: UUID) -> bool:
        """Delete a share"""
        return await self.repository.delete(share_id)
