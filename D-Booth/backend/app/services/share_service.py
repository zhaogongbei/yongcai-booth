import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Photo, Share
from app.repositories.share_repository import ShareRepository
from app.schemas.share import ShareCreate
from app.services.base_service import BaseService, BusinessRuleError, ValidationError


class ShareService(BaseService[Share, ShareCreate, ShareCreate]):
    """
    Service for share link business logic.

    Manages photo sharing links with short codes, expiration tracking,
    and view count analytics.
    """

    def __init__(self, db: AsyncSession):
        repository = ShareRepository(db)
        super().__init__(repository, db)

    # ── Validation Hooks ──────────────────────────────────────

    async def validate_create(self, obj_in: ShareCreate) -> None:
        """Validate share creation business rules."""
        # Verify photo exists
        photo = await self.db.get(Photo, obj_in.photo_id)
        if not photo:
            raise ValidationError("Photo not found")

    async def validate_delete(self, existing: Share) -> None:
        """No special deletion constraints for shares."""
        pass

    # ── Transformation Hooks ──────────────────────────────────

    async def before_create(self, obj_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform share data before creation.

        Generates unique short code, full URL, and sets default expiration.
        """
        # Generate unique short code
        short_code = self.generate_short_code()
        while await self.repository.get_by_short_code(short_code):
            short_code = self.generate_short_code()

        # Set base_url from config or default
        base_url = obj_dict.pop("base_url", "https://aibooth.app")
        full_url = f"{base_url}/s/{short_code}"

        # Set default expiration if not provided (7 days)
        if "expires_at" not in obj_dict or obj_dict["expires_at"] is None:
            obj_dict["expires_at"] = datetime.now(timezone.utc) + timedelta(days=7)

        obj_dict.update(
            {
                "short_code": short_code,
                "full_url": full_url,
                "view_count": 0,
            }
        )

        return obj_dict

    # ── Business Logic Methods ────────────────────────────────

    @staticmethod
    def generate_short_code(length: int = 8) -> str:
        """Generate a random short code."""
        return secrets.token_urlsafe(length)[:length]

    async def create_share(
        self, share_in: ShareCreate, base_url: str = "https://aibooth.app"
    ) -> Share:
        """
        Create a new share link.

        Args:
            share_in: Share creation schema
            base_url: Base URL for generating full share link

        Returns:
            Created share instance
        """
        # Inject base_url into creation flow
        share_dict = share_in.model_dump()
        share_dict["base_url"] = base_url

        # Use a temporary schema-like object to pass through create()
        from pydantic import BaseModel

        class ShareCreateWithBase(BaseModel):
            photo_id: UUID
            channel: Optional[str] = None
            expires_at: Optional[datetime] = None
            base_url: str = "https://aibooth.app"

        extended_in = ShareCreateWithBase(**share_dict)
        return await self.create(extended_in)

    async def get_share_by_code(self, short_code: str) -> Optional[Share]:
        """Get share by short code."""
        return await self.repository.get_by_short_code(short_code)

    async def get_shares(
        self,
        photo_id: Optional[UUID] = None,
        channel: Optional[str] = None,
        team_event_ids: Optional[List[UUID]] = None,
        skip: int = 0,
        limit: int = 100,
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
        self, user_id: UUID, channel: Optional[str] = None, skip: int = 0, limit: int = 100
    ) -> List[Share]:
        """Get shares scoped to teams the user belongs to, with optional channel filter."""
        return await self.repository.get_visible_to_user(user_id, channel, skip, limit)

    async def increment_view(self, share_id: UUID) -> Optional[Share]:
        """Increment view count."""
        return await self.repository.increment_view_count(share_id)

    async def increment_view_count(self, share_id: UUID) -> Optional[Share]:
        """Increment view count (alias for route compatibility)."""
        return await self.increment_view(share_id)

    async def is_expired(self, share_id: UUID) -> bool:
        """Check if share is expired."""
        return await self.repository.is_expired(share_id)

    async def delete_share(self, share_id: UUID) -> bool:
        """Delete a share (alias for route compatibility)."""
        return await self.delete(share_id)
