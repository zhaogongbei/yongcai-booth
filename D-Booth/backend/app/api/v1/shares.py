from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_active_user, check_team_member
from app.services.share_service import ShareService
from app.services.photo_service import PhotoService
from app.services.event_service import EventService
from app.schemas.share import ShareCreate, ShareResponse
from app.models.models import User

router = APIRouter()


async def _verify_photo_team_access(photo_id: Optional[UUID], current_user: User, db: AsyncSession):
    """Helper: verify photo's event team membership."""
    if not photo_id:
        return
    photo_service = PhotoService(db)
    photo = await photo_service.get_photo(photo_id)
    if not photo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Photo not found"
        )
    event_service = EventService(db)
    event = await event_service.get_event(photo.event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found for photo"
        )
    await check_team_member(event.team_id, current_user, db)


@router.get("", response_model=List[ShareResponse])
async def get_shares(
    photo_id: Optional[UUID] = Query(None),
    channel: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get shares with optional filters"""
    share_service = ShareService(db)

    if photo_id:
        await _verify_photo_team_access(photo_id, current_user, db)
        return await share_service.get_shares(photo_id=photo_id, skip=skip, limit=limit)

    # IMPORTANT: Always scope to user's teams (no global queries by channel alone)
    # Prevents cross-team data leakage
    return await share_service.get_shares_visible_to_user(
        user_id=current_user.id, channel=channel, skip=skip, limit=limit
    )


@router.post("", response_model=ShareResponse, status_code=status.HTTP_201_CREATED)
async def create_share(
    share_in: ShareCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new share link"""
    # IDOR guard: verify the photo belongs to user's team
    await _verify_photo_team_access(share_in.photo_id, current_user, db)

    share_service = ShareService(db)
    
    try:
        share = await share_service.create_share(share_in)
        return share
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/code/{short_code}", response_model=ShareResponse)
async def get_share_by_code(
    short_code: str,
    db: AsyncSession = Depends(get_db)
):
    """Get share by short code (public endpoint)"""
    share_service = ShareService(db)
    
    share = await share_service.get_share_by_code(short_code)
    if not share:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share not found or expired"
        )
    
    await share_service.increment_view_count(share.id)
    return share


@router.get("/{share_id}", response_model=ShareResponse)
async def get_share(
    share_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get share by ID"""
    share_service = ShareService(db)

    share = await share_service.get_share(share_id)
    if not share:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share not found"
        )

    # Verify team membership via photo -> event -> team
    await _verify_photo_team_access(share.photo_id, current_user, db)

    return share


@router.delete("/{share_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_share(
    share_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete share"""
    share_service = ShareService(db)

    share = await share_service.get_share(share_id)
    if not share:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share not found"
        )

    # Verify team membership via photo -> event -> team
    await _verify_photo_team_access(share.photo_id, current_user, db)

    success = await share_service.delete_share(share_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share not found"
        )
