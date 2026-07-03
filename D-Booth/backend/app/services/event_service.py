from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Event, EventStatus, UserRole
from app.repositories.event_repository import EventRepository
from app.schemas.event import EventCreate, EventStatistics, EventUpdate
from app.services.base_service import BaseService, BusinessRuleError, ValidationError


class EventService(BaseService[Event, EventCreate, EventUpdate]):
    """
    Service for event business logic.

    Provides event management operations including:
    - Event CRUD operations
    - Status transitions (draft -> scheduled -> active -> completed)
    - Permission checks (team membership, admin/owner roles)
    - Event statistics and filtering
    """

    def __init__(self, db: AsyncSession):
        repository = EventRepository(db)
        super().__init__(repository, db)
        self._current_user_id: Optional[UUID] = None

    def set_current_user(self, user_id: UUID) -> None:
        """Set current user for permission checks."""
        self._current_user_id = user_id

    async def get_event(self, event_id: UUID) -> Optional[Event]:
        """Get event by ID."""
        return await self.get(event_id)

    async def create_event(
        self,
        event_in: EventCreate,
        creator_id: UUID,
    ) -> Event:
        """Create a new event using the legacy service API."""
        self.set_current_user(creator_id)

        try:
            return await self.create(event_in)
        except ValidationError as exc:
            raise ValueError(str(exc)) from exc
        except BusinessRuleError as exc:
            raise PermissionError(str(exc)) from exc

    async def update_event(
        self,
        event_id: UUID,
        event_in: EventUpdate | dict,
        user_id: Optional[UUID] = None,
    ) -> Optional[Event]:
        """Update an event using the legacy service API."""
        if user_id is not None:
            self.set_current_user(user_id)

        update_in = event_in if isinstance(event_in, EventUpdate) else EventUpdate(**event_in)

        try:
            return await self.update(event_id, update_in)
        except ValidationError as exc:
            raise ValueError(str(exc)) from exc
        except BusinessRuleError as exc:
            raise PermissionError(str(exc)) from exc

    async def delete_event(self, event_id: UUID, user_id: Optional[UUID] = None) -> bool:
        """Delete an event using the legacy service API."""
        if user_id is not None:
            self.set_current_user(user_id)

        try:
            return await self.delete(event_id)
        except BusinessRuleError as exc:
            raise PermissionError(str(exc)) from exc

    # Override BaseService hooks

    async def validate_create(self, obj_in: EventCreate) -> None:
        """Validate business rules before event creation."""
        # Validate dates
        if obj_in.end_date <= obj_in.start_date:
            raise ValidationError("End date must be after start date")

        # Verify team membership (creator must be team member)
        if self._current_user_id:
            from app.repositories.team_repository import TeamRepository

            team_repo = TeamRepository(self.db)
            role = await team_repo.get_member_role(obj_in.team_id, self._current_user_id)
            if role is None:
                raise BusinessRuleError("User is not a member of this team")

        # Check subscription limits
        from app.services.subscription_service import SubscriptionService

        await SubscriptionService(self.db).ensure_can_create_event(obj_in.team_id)

    async def validate_update(self, existing: Event, obj_in: EventUpdate) -> None:
        """Validate business rules before event update."""
        # Permission check: only admin/owner can update
        if self._current_user_id:
            await self._ensure_admin_or_owner(existing.team_id, self._current_user_id)

        # Validate dates if being updated
        update_data = obj_in.model_dump(exclude_unset=True)
        if "start_date" in update_data or "end_date" in update_data:
            start = update_data.get("start_date", existing.start_date)
            end = update_data.get("end_date", existing.end_date)
            if end <= start:
                raise ValidationError("End date must be after start date")

    async def validate_delete(self, existing: Event) -> None:
        """Validate business rules before event deletion."""
        # Permission check: only admin/owner can delete
        if self._current_user_id:
            await self._ensure_admin_or_owner(existing.team_id, self._current_user_id)

    async def before_create(self, obj_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Transform data before event creation."""
        # Set creator_id if current user is set
        if self._current_user_id and "creator_id" not in obj_dict:
            obj_dict["creator_id"] = self._current_user_id

        # Set initial status
        obj_dict.setdefault("status", EventStatus.DRAFT)

        return obj_dict

    async def after_create(self, created: Event) -> None:
        """Handle side effects after event creation."""
        # Could publish EventCreated domain event here
        pass

    # Event-specific methods

    async def _ensure_admin_or_owner(self, team_id: UUID, user_id: UUID) -> None:
        """Ensure user is admin or owner of the team."""
        from app.repositories.team_repository import TeamRepository

        team_repo = TeamRepository(self.db)
        role = await team_repo.get_member_role(team_id, user_id)
        if role not in (UserRole.OWNER, UserRole.ADMIN):
            raise BusinessRuleError("Only team admins or owners can perform this action")

    async def get_events(
        self,
        user_id: Optional[UUID] = None,
        team_id: Optional[UUID] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Event]:
        """
        Get events with optional filters.

        When team_id is given, return events for that team.
        When user_id is given without team_id, return events from all of the user's teams.

        Args:
            user_id: Filter by user (across their teams)
            team_id: Filter by specific team
            status: Filter by status (draft/scheduled/active/completed/cancelled)
            skip: Pagination offset
            limit: Maximum results

        Returns:
            List of events matching filters
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

    async def get_team_events(self, team_id: UUID, skip: int = 0, limit: int = 100) -> List[Event]:
        """Get all events for a team."""
        return await self.repository.get_by_team(team_id, skip, limit)

    async def get_events_by_status(
        self, team_id: UUID, status: EventStatus, skip: int = 0, limit: int = 100
    ) -> List[Event]:
        """Get events by status for a team."""
        return await self.repository.get_by_status(team_id, status, skip, limit)

    async def get_active_events(self, team_id: UUID) -> List[Event]:
        """Get all active events for a team."""
        return await self.repository.get_active_events(team_id)

    async def get_events_by_date_range(
        self,
        team_id: UUID,
        start_from: datetime,
        start_to: datetime,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Event]:
        """Get events within date range for a team."""
        return await self.repository.get_by_date_range(team_id, start_from, start_to, skip, limit)

    # Status transition methods

    async def start_event(self, event_id: UUID) -> Optional[Event]:
        """
        Start an event (transition from scheduled to active).

        Args:
            event_id: Event unique identifier

        Returns:
            Updated event if successful

        Raises:
            BusinessRuleError: If event is not in scheduled status
        """
        event = await self.get(event_id)
        if not event:
            return None

        if event.status != EventStatus.SCHEDULED:
            raise BusinessRuleError("Only scheduled events can be started")

        result = await self.repository.update_status(event_id, EventStatus.ACTIVE)

        # Fire trigger for event start
        await self._fire_trigger(result, "session_start")

        return result

    async def complete_event(self, event_id: UUID) -> Optional[Event]:
        """
        Complete an event (transition from active to completed).

        Args:
            event_id: Event unique identifier

        Returns:
            Updated event if successful

        Raises:
            BusinessRuleError: If event is not in active status
        """
        event = await self.get(event_id)
        if not event:
            return None

        if event.status != EventStatus.ACTIVE:
            raise BusinessRuleError("Only active events can be completed")

        return await self.repository.update_status(event_id, EventStatus.COMPLETED)

    async def cancel_event(self, event_id: UUID) -> Optional[Event]:
        """
        Cancel an event (can be done from any status).

        Args:
            event_id: Event unique identifier

        Returns:
            Updated event if successful
        """
        return await self.repository.update_status(event_id, EventStatus.CANCELLED)

    async def schedule_event(self, event_id: UUID) -> Optional[Event]:
        """
        Schedule an event (transition from draft to scheduled).

        Args:
            event_id: Event unique identifier

        Returns:
            Updated event if successful

        Raises:
            BusinessRuleError: If event is not in draft status
        """
        event = await self.get(event_id)
        if not event:
            return None

        if event.status != EventStatus.DRAFT:
            raise BusinessRuleError("Only draft events can be scheduled")

        return await self.repository.update_status(event_id, EventStatus.SCHEDULED)

    async def update_event_settings(self, event_id: UUID, settings: dict) -> Optional[Event]:
        """
        Update event settings.

        Args:
            event_id: Event unique identifier
            settings: Settings dictionary

        Returns:
            Updated event if found
        """
        event = await self.get(event_id)
        if not event:
            return None

        return await self.repository.update(event_id, {"settings": settings})

    async def get_event_statistics(self, event_id: UUID) -> EventStatistics:
        """
        Get comprehensive event statistics.

        Args:
            event_id: Event unique identifier

        Returns:
            EventStatistics with counts of sessions, photos, prints, shares
        """
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

        total_prints = await print_repo.count_by_event(event_id)
        total_shares = await share_repo.count_by_event(event_id)

        return EventStatistics(
            event_id=event_id,
            total_sessions=total_sessions,
            total_photos=total_photos,
            total_prints=total_prints,
            total_shares=total_shares,
            active_sessions=len(active_sessions),
        )

    async def _fire_trigger(self, event_or_event_id, trigger_type: str):
        """
        Fire a trigger for event lifecycle events.

        Args:
            event_or_event_id: Event instance or event UUID
            trigger_type: Trigger type string (e.g. 'session_start')
        """
        try:
            from app.services.trigger_service import TriggerService, TriggerType

            event_id = (
                event_or_event_id.id if hasattr(event_or_event_id, "id") else event_or_event_id
            )
            trigger_service = TriggerService(self.db)
            context = {"event_id": str(event_id)}
            if hasattr(event_or_event_id, "team_id"):
                context["team_id"] = str(event_or_event_id.team_id)
            await trigger_service.execute_triggers(trigger_type, context)
        except Exception:
            pass  # Never let trigger failures break the main flow
