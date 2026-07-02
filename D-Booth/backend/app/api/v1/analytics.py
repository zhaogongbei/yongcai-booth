from typing import Dict, Any
from uuid import UUID
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_active_user, check_team_member
from app.services.analytics_service import AnalyticsService
from app.services.event_service import EventService
from app.schemas.analytics import AnalyticsEventCreate
from app.models.models import User

router = APIRouter()


@router.post("/events", status_code=status.HTTP_201_CREATED)
async def track_event(
    event_in: AnalyticsEventCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Track an analytics event"""
    # Verify team membership before tracking
    await check_team_member(event_in.team_id, current_user, db)

    analytics_service = AnalyticsService(db)

    try:
        await analytics_service.track_event(event_in)
        return {"status": "ok"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/overview", response_model=Dict[str, Any])
async def get_analytics_overview(
    team_id: UUID = Query(...),
    start_date: datetime = Query(None),
    end_date: datetime = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get analytics overview for a team"""
    # Verify the user is a member of the requested team
    await check_team_member(team_id, current_user, db)

    analytics_service = AnalyticsService(db)

    if not start_date:
        start_date = datetime.now(timezone.utc) - timedelta(days=30)
    if not end_date:
        end_date = datetime.now(timezone.utc)

    overview = await analytics_service.get_overview(team_id, start_date, end_date)
    return overview


@router.get("/events/stats", response_model=Dict[str, Any])
async def get_event_stats(
    event_id: UUID = Query(...),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get statistics for a specific event"""
    # Trace event -> team for permission check
    event_service = EventService(db)
    event = await event_service.get_event(event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    await check_team_member(event.team_id, current_user, db)

    analytics_service = AnalyticsService(db)

    stats = await analytics_service.get_event_stats(event_id)
    return stats


@router.get("/photos/stats", response_model=Dict[str, Any])
async def get_photo_stats(
    team_id: UUID = Query(...),
    start_date: datetime = Query(None),
    end_date: datetime = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get photo statistics"""
    # Verify the user is a member of the requested team
    await check_team_member(team_id, current_user, db)

    analytics_service = AnalyticsService(db)

    if not start_date:
        start_date = datetime.now(timezone.utc) - timedelta(days=30)
    if not end_date:
        end_date = datetime.now(timezone.utc)

    stats = await analytics_service.get_photo_stats(team_id, start_date, end_date)
    return stats
