"""
Booth repository for data access operations.
"""

from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Booth, BoothStatus
from app.repositories.base import BaseRepository


class BoothRepository(BaseRepository[Booth]):
    """Repository for Booth data access."""

    def __init__(self, db: AsyncSession):
        super().__init__(Booth, db)

    async def get_by_device_id(self, device_id: str) -> Optional[Booth]:
        """Get booth by device ID."""
        result = await self.db.execute(select(Booth).where(Booth.device_id == device_id))
        return result.scalar_one_or_none()

    async def get_by_team(self, team_id: UUID, skip: int = 0, limit: int = 100) -> List[Booth]:
        """Get booths by team ID."""
        result = await self.db.execute(
            select(Booth)
            .where(Booth.team_id == team_id)
            .order_by(Booth.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def update_heartbeat(self, booth_id: UUID) -> Optional[Booth]:
        """Update booth heartbeat timestamp."""
        booth = await self.get(booth_id)
        if not booth:
            return None

        booth.last_heartbeat = datetime.now(timezone.utc)
        booth.status = BoothStatus.ONLINE
        await self.db.commit()
        await self.db.refresh(booth)
        return booth

    async def mark_offline_booths(self, timeout_seconds: int = 60) -> int:
        """Mark booths as offline if no heartbeat within timeout."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(seconds=timeout_seconds)
        result = await self.db.execute(
            update(Booth)
            .where(Booth.last_heartbeat < cutoff_time)
            .where(Booth.status != BoothStatus.OFFLINE)
            .values(status=BoothStatus.OFFLINE)
        )
        await self.db.commit()
        return result.rowcount

    async def update_config_hash(self, booth_id: UUID, config_hash: str) -> Optional[Booth]:
        """Update booth configuration hash."""
        booth = await self.get(booth_id)
        if not booth:
            return None

        booth.config_hash = config_hash
        await self.db.commit()
        await self.db.refresh(booth)
        return booth
