from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from app.api.deps import get_db, get_current_active_user, check_team_member
from app.services.watermark_service import WatermarkService, WatermarkSettings
from app.services.storage_service import r2_storage
from app.models.models import User, Event, Photo
from app.services.photo_service import PhotoService

router = APIRouter()


@router.put("/settings/watermark/{event_id}", response_model=WatermarkSettings)
async def update_watermark_settings(
    event_id: UUID,
    settings: WatermarkSettings,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update watermark settings for an event"""
    from app.services.event_service import EventService
    event_service = EventService(db)

    event = await event_service.get_event(event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )

    # Verify team membership
    await check_team_member(event.team_id, current_user, db)

    # Update event settings
    event_settings = event.settings or {}
    event_settings["watermark"] = settings.model_dump()
    await event_service.update_event_settings(event_id, event_settings)

    return settings


@router.get("/settings/watermark/{event_id}", response_model=WatermarkSettings)
async def get_watermark_settings(
    event_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get watermark settings for an event"""
    from app.services.event_service import EventService
    event_service = EventService(db)

    event = await event_service.get_event(event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )

    # Verify team membership
    await check_team_member(event.team_id, current_user, db)

    event_settings = event.settings or {}
    return WatermarkSettings(**event_settings.get("watermark", {}))


@router.post("/watermark/upload")
async def upload_watermark(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user)
):
    """Upload a watermark PNG file"""
    if not file.content_type or not file.content_type.startswith("image/png"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PNG files are allowed for watermarks"
        )

    # Read file content
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:  # 5MB limit
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Watermark file size must be less than 5MB"
        )

    # Upload to storage
    try:
        url = await r2_storage.upload_file(
            file_data=content,
            filename=file.filename or "watermark.png",
            folder="uploads/watermarks"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload watermark: {str(e)}"
        )

    return {"url": url}


@router.post("/watermark/preview/{photo_id}")
async def preview_watermark(
    photo_id: UUID,
    settings: WatermarkSettings,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Preview watermark effect on a photo"""
    if not settings.enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Watermark is not enabled"
        )

    if not settings.watermark_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No watermark image provided"
        )

    # Get photo
    photo_service = PhotoService(db)
    photo = await photo_service.get_photo(photo_id)
    if not photo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Photo not found"
        )

    # Verify team membership
    await check_team_member(photo.event.team_id, current_user, db)

    try:
        # Download original image
        async with httpx.AsyncClient() as client:
            response = await client.get(photo.original_url)
            response.raise_for_status()
            image_bytes = response.content

        # Download watermark
        async with httpx.AsyncClient() as client:
            response = await client.get(settings.watermark_url)
            response.raise_for_status()
            watermark_bytes = response.content

        # Apply watermark
        result_bytes = WatermarkService.apply_watermark(
            image_bytes=image_bytes,
            watermark_bytes=watermark_bytes,
            position=settings.position,
            opacity=settings.opacity,
            scale=settings.scale,
            tile=settings.tile
        )

        return Response(content=result_bytes, media_type="image/jpeg")

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate preview: {str(e)}"
        )