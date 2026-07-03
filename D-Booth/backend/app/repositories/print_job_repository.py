from typing import List, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Event, Photo, PrintJob, PrintJobStatus, TeamMember
from app.repositories.base import BaseRepository


class PrintJobRepository(BaseRepository[PrintJob]):
    """Repository for PrintJob model"""

    def __init__(self, db: AsyncSession):
        super().__init__(PrintJob, db)

    async def get_visible_to_user(
        self, user_id: UUID, status: Optional[str] = None, skip: int = 0, limit: int = 100
    ) -> List[PrintJob]:
        """Get print jobs scoped to teams the user belongs to, with optional status filter."""
        from app.models.models import PrintJobStatus

        stmt = (
            select(PrintJob)
            .join(Photo, PrintJob.photo_id == Photo.id)
            .join(Event, Photo.event_id == Event.id)
            .join(TeamMember, TeamMember.team_id == Event.team_id)
            .where(TeamMember.user_id == user_id)
        )

        # Add status filter if provided
        if status:
            try:
                enum_status = PrintJobStatus(status)
                stmt = stmt.where(PrintJob.status == enum_status)
            except ValueError:
                # Invalid status value - return empty list
                return []

        stmt = stmt.order_by(PrintJob.created_at.desc()).offset(skip).limit(limit)

        result = await self.db.execute(stmt)
        return list(result.scalars().unique().all())

    async def get_by_photo(self, photo_id: UUID) -> List[PrintJob]:
        """Get all print jobs for a photo"""
        result = await self.db.execute(
            select(PrintJob)
            .where(PrintJob.photo_id == photo_id)
            .order_by(PrintJob.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_status(
        self, status: PrintJobStatus, skip: int = 0, limit: int = 100
    ) -> List[PrintJob]:
        """Get print jobs by status"""
        result = await self.db.execute(
            select(PrintJob)
            .where(PrintJob.status == status)
            .order_by(PrintJob.created_at)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_pending_jobs(self, limit: int = 50) -> List[PrintJob]:
        """Get pending print jobs"""
        result = await self.db.execute(
            select(PrintJob)
            .where(PrintJob.status == PrintJobStatus.PENDING)
            .order_by(PrintJob.created_at)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def update_status(
        self, job_id: UUID, status: PrintJobStatus, error_message: Optional[str] = None
    ) -> Optional[PrintJob]:
        """Update print job status"""
        from datetime import datetime, timezone

        stmt = select(PrintJob).where(PrintJob.id == job_id)
        result = await self.db.execute(stmt)
        job = result.scalar_one_or_none()

        if job:
            job.status = status
            if error_message:
                job.error_message = error_message
            if status == PrintJobStatus.COMPLETED:
                job.printed_at = datetime.now(timezone.utc)
            await self.db.commit()
            await self.db.refresh(job)
            return job
        return None

    async def count_by_event(self, event_id: UUID) -> int:
        """Count print jobs for an event (join through Photo, single query)."""
        result = await self.db.execute(
            select(func.count())
            .select_from(PrintJob)
            .join(Photo, PrintJob.photo_id == Photo.id)
            .where(Photo.event_id == event_id)
        )
        return result.scalar_one()

    async def count_by_status(self, status: PrintJobStatus) -> int:
        """Count print jobs by status"""
        result = await self.db.execute(
            select(func.count()).select_from(PrintJob).where(PrintJob.status == status)
        )
        return result.scalar_one()

    async def count_by_event(self, event_id: UUID) -> int:
        """Count print jobs for an event (via photo, single join)."""
        result = await self.db.execute(
            select(func.count())
            .select_from(PrintJob)
            .join(Photo, PrintJob.photo_id == Photo.id)
            .where(Photo.event_id == event_id)
        )
        return result.scalar_one()

    async def get_statistics(self) -> dict:
        """Get print job statistics"""
        stats = {}
        for status in PrintJobStatus:
            count = await self.count_by_status(status)
            stats[status.value] = count
        return stats
