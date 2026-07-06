from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import check_team_member, get_current_active_user, get_db, verify_event_access
from app.models.models import User
from app.schemas.photo import (
    PhotoCreate,
    PhotoResponse,
    PhotoSessionCreate,
    PhotoSessionResponse,
    PhotoUpdate,
)
from app.services.beauty_service import BeautyParams
from app.services.photo_service import PhotoService
from app.services.subscription_service import SubscriptionService

router = APIRouter()


@router.get("", response_model=List[PhotoResponse])
async def get_photos(
    event_id: Optional[UUID] = Query(None),
    session_id: Optional[UUID] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get photos with optional filters"""
    photo_service = PhotoService(db)

    if event_id:
        # Verify the event belongs to the user's team (single joined query)
        await verify_event_access(event_id, current_user, db)
    elif session_id:
        # Trace session -> event -> team for permission check
        session = await photo_service.get_session(session_id)
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
        await verify_event_access(session.event_id, current_user, db)
    else:
        return await photo_service.photo_repo.get_visible_to_user(
            current_user.id, skip=skip, limit=limit
        )

    photos = await photo_service.get_photos(
        event_id=event_id, session_id=session_id, skip=skip, limit=limit
    )
    return photos


@router.post("", response_model=PhotoResponse, status_code=status.HTTP_201_CREATED)
async def create_photo(
    photo_in: PhotoCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new photo record"""
    # Verify event belongs to user's team (single joined query)
    event = await verify_event_access(photo_in.event_id, current_user, db)

    photo_service = PhotoService(db)
    subscription_service = SubscriptionService(db)

    try:
        await subscription_service.ensure_can_upload_photo(event.team_id, event.id)
        photo = await photo_service.create_photo(photo_in)
        return photo
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/sessions", response_model=PhotoSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_photo_session(
    session_in: PhotoSessionCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a photo session for an event."""
    await verify_event_access(session_in.event_id, current_user, db)

    photo_service = PhotoService(db)
    return await photo_service.create_session(session_in)


@router.get("/sessions", response_model=List[PhotoSessionResponse])
async def get_photo_sessions(
    event_id: UUID = Query(...),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get photo sessions for an event."""
    await verify_event_access(event_id, current_user, db)

    photo_service = PhotoService(db)
    return await photo_service.get_sessions(event_id, skip, limit)


@router.post("/sessions/{session_id}/complete", response_model=PhotoSessionResponse)
async def complete_photo_session(
    session_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark a photo session as completed."""
    photo_service = PhotoService(db)
    session = await photo_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    await verify_event_access(session.event_id, current_user, db)

    completed = await photo_service.complete_session(session_id)
    if not completed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return completed


@router.post("/upload", response_model=PhotoResponse, status_code=status.HTTP_201_CREATED)
async def upload_photo(
    event_id: UUID,
    session_id: Optional[UUID] = None,
    file: UploadFile = File(...),
    beauty_smooth: int = Form(default=0, ge=0, le=100),
    beauty_whiten: int = Form(default=0, ge=0, le=100),
    beauty_thinFace: int = Form(default=0, ge=0, le=100),
    beauty_bigEye: int = Form(default=0, ge=0, le=100),
    beauty_eyeLight: int = Form(default=0, ge=0, le=100),
    beauty_acne: int = Form(default=0, ge=0, le=100),
    beauty_nasolabial: int = Form(default=0, ge=0, le=100),
    beauty_teethWhiten: int = Form(default=0, ge=0, le=100),
    beauty_lipColor: int = Form(default=0, ge=0, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a photo file with optional built-in AI beauty processing."""
    # Verify event belongs to user's team (single joined query)
    event = await verify_event_access(event_id, current_user, db)

    photo_service = PhotoService(db)
    subscription_service = SubscriptionService(db)

    # Build beauty params if any slider is non-zero
    bp = BeautyParams(
        smooth=beauty_smooth,
        whiten=beauty_whiten,
        thinFace=beauty_thinFace,
        bigEye=beauty_bigEye,
        eyeLight=beauty_eyeLight,
        acne=beauty_acne,
        nasolabial=beauty_nasolabial,
        teethWhiten=beauty_teethWhiten,
        lipColor=beauty_lipColor,
    )
    if all(getattr(bp, f, 0) == 0 for f in BeautyParams.model_fields):
        bp = None  # no beauty → skip processing for speed

    try:
        await subscription_service.ensure_can_upload_photo(event.team_id, event.id)
        photo = await photo_service.upload_photo(file, event_id, session_id, beauty_params=bp)
        return photo
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{photo_id}", response_model=PhotoResponse)
async def get_photo(
    photo_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get photo by ID"""
    photo_service = PhotoService(db)

    photo = await photo_service.get_photo(photo_id)
    if not photo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo not found")

    await check_team_member(photo.event.team_id, current_user, db)

    return photo


@router.put("/{photo_id}", response_model=PhotoResponse)
async def update_photo(
    photo_id: UUID,
    photo_in: PhotoUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update photo metadata"""
    photo_service = PhotoService(db)

    photo = await photo_service.get_photo(photo_id)
    if not photo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo not found")

    await check_team_member(photo.event.team_id, current_user, db)

    photo = await photo_service.update_photo(photo_id, photo_in)
    return photo


@router.delete("/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_photo(
    photo_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete photo"""
    photo_service = PhotoService(db)

    photo = await photo_service.get_photo(photo_id)
    if not photo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo not found")

    await check_team_member(photo.event.team_id, current_user, db)

    success = await photo_service.delete_photo(photo_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo not found")
