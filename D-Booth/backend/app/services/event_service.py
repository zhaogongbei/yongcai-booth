from typing import Optional, List
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.event_repository import EventRepository
from app.schemas.event import EventCreate, EventUpdate, EventStatistics
from app.models.models import Event, EventStatus


class EventService:
    """Service for event business logic"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = EventRepository(db)
    
    async def get_event(self, event_id: UUID) -> Optional[Event]:
        """Get event by ID"""
        return await self.repository.get(event_id)

    async def get_events(
        self,
        user_id: Optional[UUID] = None,
        team_id: Optional[UUID] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Event]:
        """Get events with optional filters.

        When ``team_id`` is given, return events for that team.
        When ``user_id`` is given without ``team_id``, return events from
        all of the user's teams.
        """
        if team_id:
            if status:
                try:
                    enum_status = EventStatus(status)
                    return await self.repository.get_by_status(team_id, enum_status, skip, limit)
                except ValueError:
                    pass
            return await self.repository.get_by_team(team_id, skip, limit)

        if user_id:
            from app.repositories.team_repository import TeamRepository
            team_repo = TeamRepository(self.db)
            user_teams = await team_repo.get_user_teams(user_id)
            all_events: List[Event] = []
            for t in user_teams:
                all_events.extend(await self.repository.get_by_team(t.id, 0, limit))
            all_events.sort(key=lambda e: e.start_date, reverse=True)
            return all_events[:limit]

        return await self.repository.get_multi(skip, limit)

    async def get_team_events(
        self,
        team_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[Event]:
        """Get all events for a team"""
        return await self.repository.get_by_team(team_id, skip, limit)
    
    async def get_events_by_status(
        self,
        team_id: UUID,
        status: EventStatus,
        skip: int = 0,
        limit: int = 100
    ) -> List[Event]:
        """Get events by status"""
        return await self.repository.get_by_status(team_id, status, skip, limit)
    
    async def get_active_events(self, team_id: UUID) -> List[Event]:
        """Get all active events"""
        return await self.repository.get_active_events(team_id)
    
    async def get_events_by_date_range(
        self,
        team_id: UUID,
        start_from: datetime,
        start_to: datetime,
        skip: int = 0,
        limit: int = 100
    ) -> List[Event]:
        """Get events within date range"""
        return await self.repository.get_by_date_range(
            team_id, start_from, start_to, skip, limit
        )
    
    async def create_event(
        self,
        event_in: EventCreate,
        creator_id: UUID
    ) -> Event:
        """Create a new event"""
        # Validate dates
        if event_in.end_date <= event_in.start_date:
            raise ValueError("End date must be after start date")

        # Verify creator belongs to the team (prevent cross-team event creation)
        from app.repositories.team_repository import TeamRepository
        team_repo = TeamRepository(self.db)
        role = await team_repo.get_member_role(event_in.team_id, creator_id)
        if role is None:
            raise PermissionError("User is not a member of this team")

        from app.services.subscription_service import SubscriptionService
        await SubscriptionService(self.db).ensure_can_create_event(event_in.team_id)

        event_data = {
            **event_in.model_dump(),
            "creator_id": creator_id,
            "status": EventStatus.DRAFT,
        }

        return await self.repository.create(event_data)
    
    async def update_event(
        self,
        event_id: UUID,
        event_in: EventUpdate,
        user_id: Optional[UUID] = None
    ) -> Optional[Event]:
        """Update event information.

        If ``user_id`` is provided, the caller must be a team admin/owner.
        """
        event = await self.repository.get(event_id)
        if not event:
            return None

        # Permission guard: only admin/owner can update
        if user_id is not None:
            from app.repositories.team_repository import TeamRepository
            from app.models.models import UserRole
            team_repo = TeamRepository(self.db)
            role = await team_repo.get_member_role(event.team_id, user_id)
            if role not in (UserRole.OWNER, UserRole.ADMIN):
                raise PermissionError("Only team admins or owners can update events")
        
        update_data = event_in.model_dump(exclude_unset=True)
        
        # Validate dates if being updated
        if "start_date" in update_data or "end_date" in update_data:
            start = update_data.get("start_date", event.start_date)
            end = update_data.get("end_date", event.end_date)
            if end <= start:
                raise ValueError("End date must be after start date")
        
        return await self.repository.update(event_id, update_data)
    
    async def delete_event(self, event_id: UUID, user_id: Optional[UUID] = None) -> bool:
        """Delete an event.

        If ``user_id`` is provided, the caller must be a team admin/owner.
        """
        if user_id is not None:
            event = await self.repository.get(event_id)
            if not event:
                return False
            from app.repositories.team_repository import TeamRepository
            from app.models.models import UserRole
            team_repo = TeamRepository(self.db)
            role = await team_repo.get_member_role(event.team_id, user_id)
            if role not in (UserRole.OWNER, UserRole.ADMIN):
                raise PermissionError("Only team admins or owners can delete events")

        return await self.repository.delete(event_id)
    
    async def start_event(self, event_id: UUID) -> Optional[Event]:
        """Start an event (change status to active)"""
        event = await self.repository.get(event_id)
        if not event:
            return None
        
        if event.status != EventStatus.SCHEDULED:
            raise ValueError("Only scheduled events can be started")
        
        result = await self.repository.update_status(event_id, EventStatus.ACTIVE)

        # Trigger SESSION_START
        await self._fire_trigger(result, "session_start")

        return result

    async def complete_event(self, event_id: UUID) -> Optional[Event]:
        """Complete an event"""
        event = await self.repository.get(event_id)
        if not event:
            return None
        
        if event.status != EventStatus.ACTIVE:
            raise ValueError("Only active events can be completed")
        
        return await self.repository.update_status(event_id, EventStatus.COMPLETED)
    
    async def cancel_event(self, event_id: UUID) -> Optional[Event]:
        """Cancel an event"""
        return await self.repository.update_status(event_id, EventStatus.CANCELLED)

    async def schedule_event(self, event_id: UUID) -> Optional[Event]:
        """Schedule an event (change from draft to scheduled)"""
        event = await self.repository.get(event_id)
        if not event:
            return None

        if event.status != EventStatus.DRAFT:
            raise ValueError("Only draft events can be scheduled")

        return await self.repository.update_status(event_id, EventStatus.SCHEDULED)

    async def update_event_settings(self, event_id: UUID, settings: dict) -> Optional[Event]:
        """Update event settings"""
        event = await self.repository.get(event_id)
        if not event:
            return None

        return await self.repository.update(event_id, {"settings": settings})
    
    async def get_event_statistics(self, event_id: UUID) -> EventStatistics:
        """Get event statistics"""
        # Import here to avoid circular dependency
        from app.repositories.photo_repository import PhotoRepository, PhotoSessionRepository
        from app.repositories.print_job_repository import PrintJobRepository
        from app.repositories.share_repository import ShareRepository
        
        photo_repo = PhotoRepository(self.db)
        session_repo = PhotoSessionRepository(self.db)
        print_repo = PrintJobRepository(self.db)
        share_repo = ShareRepository(self.db)
        
        # Get counts
        total_sessions = await session_repo.count_by_event(event_id)
        total_photos = await photo_repo.count_by_event(event_id)
        
        # Get active sessions
        active_sessions = await session_repo.get_active_sessions(event_id)
        
        # TODO: Get print and share counts for this event
        
        return EventStatistics(
            event_id=event_id,
            total_sessions=total_sessions,
            total_photos=total_photos,
            total_prints=0,  # TODO
            total_shares=0,  # TODO
            active_sessions=len(active_sessions),
        )

    async def _fire_trigger(self, event_or_event_id, trigger_type: str):
        """Fire a trigger for event lifecycle events.

        Args:
            event_or_event_id: Event instance or event UUID
            trigger_type: Trigger type string (e.g. 'session_start')
        """
        try:
            from app.services.trigger_service import TriggerService, TriggerType
            event_id = event_or_event_id.id if hasattr(event_or_event_id, "id") else event_or_event_id
            trigger_service = TriggerService(self.db)
            context = {"event_id": str(event_id)}
            if hasattr(event_or_event_id, "team_id"):
                context["team_id"] = str(event_or_event_id.team_id)
            await trigger_service.execute_triggers(trigger_type, context)
        except Exception:
            pass  # Never let trigger failures break the main flow
