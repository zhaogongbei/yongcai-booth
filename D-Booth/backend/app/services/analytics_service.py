from typing import Dict, Any, Optional, List
from uuid import UUID
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.analytics_repository import AnalyticsRepository
from app.repositories.photo_repository import PhotoRepository
from app.repositories.print_job_repository import PrintJobRepository
from app.repositories.share_repository import ShareRepository
from app.schemas.analytics import AnalyticsEventCreate, AnalyticsSummary
from app.models.models import AnalyticsEvent, Event, EventStatus, Photo, PrintJob, Share, Booth, BoothStatus


class AnalyticsService:
    """Service for analytics business logic"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = AnalyticsRepository(db)

    async def track_event(
        self,
        event_in_or_team_id,
        event_type: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
        event_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
        session_id: Optional[str] = None
    ) -> AnalyticsEvent:
        """Track a new analytics event.

        Accepts both a dict/AnalyticsEventCreate object (from the route
        layer) and individual keyword args (from internal callers).
        """
        if isinstance(event_in_or_team_id, AnalyticsEventCreate):
            obj = event_in_or_team_id
            return await self.repository.track_event(
                team_id=obj.team_id,
                event_type=obj.event_type,
                properties=obj.properties,
                event_id=obj.event_id,
                user_id=obj.user_id,
                session_id=obj.session_id
            )
        return await self.repository.track_event(
            team_id=event_in_or_team_id,
            event_type=event_type,
            properties=properties,
            event_id=event_id,
            user_id=user_id,
            session_id=session_id
        )

    async def get_team_summary(
        self,
        team_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> AnalyticsSummary:
        """Get analytics summary for a team"""
        # Get events in date range if provided
        if start_date and end_date:
            events = await self.repository.get_by_date_range(
                team_id, start_date, end_date
            )
        else:
            events = await self.repository.get_by_team(team_id, limit=10000)

        # Calculate summary
        event_types = await self.repository.count_by_type(team_id)
        unique_users = await self.repository.count_unique_users(team_id)
        unique_sessions = await self.repository.count_unique_sessions(team_id)

        return AnalyticsSummary(
            total_events=len(events),
            unique_users=unique_users,
            unique_sessions=unique_sessions,
            events_by_type=event_types,
            date_range={"start": start_date, "end": end_date} if start_date and end_date else None
        )

    async def get_event_analytics(
        self,
        event_id: UUID,
        skip: int = 0,
        limit: int = 1000
    ) -> List[AnalyticsEvent]:
        """Get analytics for a specific event"""
        return await self.repository.get_by_event(event_id, skip, limit)

    # ── Convenience methods used by the analytics route layer ──────────

    async def get_overview(
        self,
        team_id: UUID,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get analytics overview for a team (aggregated summary)."""
        summary = await self.get_team_summary(team_id, start_date, end_date)
        business_metrics = await self._get_business_overview(team_id)
        return {
            "total_events": summary.total_events,
            "unique_users": summary.unique_users,
            "unique_sessions": summary.unique_sessions,
            "events_by_type": summary.events_by_type,
            "date_range": summary.date_range,
            **business_metrics,
        }

    async def get_event_stats(self, event_id: UUID) -> Dict[str, Any]:
        """Get statistics for a specific event."""
        photo_repo = PhotoRepository(self.db)
        print_repo = PrintJobRepository(self.db)
        share_repo = ShareRepository(self.db)

        total_photos = await photo_repo.count_by_event(event_id)
        total_prints = await print_repo.count_by_event(event_id)
        total_shares = await share_repo.count_by_event(event_id)

        return {
            "event_id": str(event_id),
            "total_photos": total_photos,
            "total_prints": total_prints,
            "total_shares": total_shares,
        }

    async def get_photo_stats(
        self,
        team_id: UUID,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get photo statistics for a team (single-query aggregation, no N+1)."""
        # 单次聚合查询替代循环
        result = await self.db.execute(
            select(
                func.count(Photo.id).label("total_photos"),
                func.coalesce(func.sum(Photo.file_size), 0).label("total_size")
            )
            .select_from(Photo)
            .join(Event, Photo.event_id == Event.id)
            .where(Event.team_id == team_id)
        )
        row = result.one()

        from app.repositories.event_repository import EventRepository
        event_repo = EventRepository(self.db)
        total_events = await event_repo.count_by_team(team_id)

        return {
            "team_id": str(team_id),
            "total_photos": row.total_photos,
            "total_size_bytes": row.total_size,
            "total_events": total_events,
        }

    async def _get_business_overview(self, team_id: UUID) -> Dict[str, Any]:
        """Aggregate business counters for dashboard overview."""
        photo_result = await self.db.execute(
            select(
                func.count(Photo.id).label("total_photos"),
                func.coalesce(func.sum(Photo.file_size), 0).label("storage_used"),
            )
            .select_from(Photo)
            .join(Event, Photo.event_id == Event.id)
            .where(Event.team_id == team_id)
        )
        photo_row = photo_result.one()

        print_result = await self.db.execute(
            select(func.count(PrintJob.id))
            .select_from(PrintJob)
            .join(Photo, PrintJob.photo_id == Photo.id)
            .join(Event, Photo.event_id == Event.id)
            .where(Event.team_id == team_id)
        )

        share_result = await self.db.execute(
            select(func.count(Share.id))
            .select_from(Share)
            .join(Photo, Share.photo_id == Photo.id)
            .join(Event, Photo.event_id == Event.id)
            .where(Event.team_id == team_id)
        )

        active_event_result = await self.db.execute(
            select(func.count(Event.id))
            .select_from(Event)
            .where(Event.team_id == team_id, Event.status == EventStatus.ACTIVE)
        )

        return {
            "total_photos": photo_row.total_photos,
            "total_prints": print_result.scalar_one(),
            "total_shares": share_result.scalar_one(),
            "active_events": active_event_result.scalar_one(),
            "storage_used": photo_row.storage_used,
            "estimated_revenue": 0,
            "revenue": 0,
        }

    async def get_multi_booth_stats(self, team_id: UUID) -> Dict[str, Any]:
        """获取多展位聚合统计数据"""
        # 获取团队所有展位
        booths_result = await self.db.execute(
            select(Booth).where(Booth.team_id == team_id)
        )
        booths = booths_result.scalars().all()

        # 活跃展位（最近30分钟有心跳）
        cutoff_time = datetime.utcnow() - timedelta(minutes=30)
        active_booths = [b for b in booths if b.last_heartbeat and b.last_heartbeat >= cutoff_time]

        total_sessions = 0
        total_photos = 0
        total_prints = 0
        total_shares = 0

        by_booth = []
        for booth in booths:
            booth_stats = {
                "booth_id": str(booth.id),
                "name": booth.name,
                "status": booth.status.value if booth.status else "offline",
                "last_heartbeat": str(booth.last_heartbeat) if booth.last_heartbeat else None,
                "sessions": 0,
                "photos": 0,
                "prints": 0,
                "shares": 0
            }

            # 如果有关联的活动，统计该活动的数据
            if booth.current_event_id:
                # 统计活动会话数 - 使用子查询替代关系对象
                from app.models.models import PhotoSession
                sessions_result = await self.db.execute(
                    select(func.count(PhotoSession.id))
                    .where(PhotoSession.event_id == booth.current_event_id)
                )
                sessions = sessions_result.scalar_one_or_none() or 0
                booth_stats["sessions"] = sessions
                total_sessions += sessions

                # 统计照片数
                photo_repo = PhotoRepository(self.db)
                photos = await photo_repo.count_by_event(booth.current_event_id)
                booth_stats["photos"] = photos
                total_photos += photos

                # 统计打印数
                print_repo = PrintJobRepository(self.db)
                prints = await print_repo.count_by_event(booth.current_event_id)
                booth_stats["prints"] = prints
                total_prints += prints

                # 统计分享数
                share_repo = ShareRepository(self.db)
                shares = await share_repo.count_by_event(booth.current_event_id)
                booth_stats["shares"] = shares
                total_shares += shares

            by_booth.append(booth_stats)

        return {
            "team_id": str(team_id),
            "total_booths": len(booths),
            "active_booths": len(active_booths),
            "total_sessions": total_sessions,
            "total_photos": total_photos,
            "total_prints": total_prints,
            "total_shares": total_shares,
            "by_booth": by_booth
        }
