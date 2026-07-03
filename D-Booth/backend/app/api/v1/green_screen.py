"""
Green Screen API Endpoints
"""

import json
from pathlib import Path
from typing import List, Optional
from uuid import UUID, uuid4

import numpy as np
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.logging import logger
from app.models.models import Event, GreenScreenBackgroundAsset, GreenScreenSettings
from app.schemas.green_screen import (
    BackgroundAnalysisResult,
    GreenScreenBackground,
    GreenScreenProcessRequest,
    GreenScreenSettingsResponse,
    GreenScreenSettingsUpdate,
)
from app.services.green_screen_service import green_screen_service
from app.services.storage_service import r2_storage

router = APIRouter()

# Try to import OpenCV for image decoding
try:
    import cv2

    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False
    logger.warning("OpenCV not available, green screen API will return original images")


def _save_local_green_screen_file(
    file_data: bytes, filename: str, event_id: UUID, folder: str
) -> str:
    safe_name = Path(filename or "upload").name
    safe_suffix = Path(safe_name).suffix or ".jpg"
    stored_name = f"{uuid4().hex}{safe_suffix}"
    relative_folder = Path("uploads") / "green-screen" / str(event_id) / folder
    relative_folder.mkdir(parents=True, exist_ok=True)
    target = relative_folder / stored_name
    target.write_bytes(file_data)
    return f"/uploads/green-screen/{event_id}/{folder}/{stored_name}"


def _delete_local_green_screen_file(file_url: Optional[str]) -> None:
    if not file_url or not file_url.startswith("/uploads/green-screen/"):
        return

    uploads_root = (Path.cwd() / "uploads").resolve()
    target = (Path.cwd() / file_url.lstrip("/")).resolve()
    if target.is_file() and str(target).startswith(str(uploads_root)):
        target.unlink()


def _background_response(background: GreenScreenBackgroundAsset) -> GreenScreenBackground:
    return GreenScreenBackground(
        id=background.id,
        name=background.name,
        background_url=background.background_url,
        overlay_url=background.overlay_url,
        order=background.sort_order or 0,
        created_at=background.created_at,
    )


def _settings_response(settings: GreenScreenSettings) -> GreenScreenSettingsResponse:
    return GreenScreenSettingsResponse(
        id=settings.id,
        event_id=settings.event_id,
        enabled=bool(settings.enabled),
        mode=settings.mode or "auto",
        color_to_remove=settings.color_to_remove or "#00FF00",
        sensitivity=int(settings.sensitivity or 50),
        smoothness=int(settings.smoothness or 30),
        use_flash=bool(settings.use_flash),
        background_mode=settings.background_mode or "rotate",
        output_size=settings.output_size or "template",
        current_background_index=settings.current_background_index or 0,
        backgrounds=[_background_response(background) for background in settings.backgrounds],
        created_at=settings.created_at,
        updated_at=settings.updated_at,
    )


async def _get_settings_for_event(
    db: AsyncSession,
    event_id: UUID,
) -> Optional[GreenScreenSettings]:
    result = await db.execute(
        select(GreenScreenSettings)
        .options(selectinload(GreenScreenSettings.backgrounds))
        .where(GreenScreenSettings.event_id == event_id)
    )
    return result.scalar_one_or_none()


async def _ensure_event_exists(db: AsyncSession, event_id: UUID) -> None:
    result = await db.execute(select(Event.id).where(Event.id == event_id))
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )


async def _get_or_create_settings_for_event(
    db: AsyncSession,
    event_id: UUID,
) -> GreenScreenSettings:
    await _ensure_event_exists(db, event_id)
    settings = await _get_settings_for_event(db, event_id)
    if settings:
        return settings

    settings = GreenScreenSettings(
        id=uuid4(),
        event_id=event_id,
        enabled=False,
        mode="auto",
        color_to_remove="#00FF00",
        sensitivity=50,
        smoothness=30,
        use_flash=False,
        background_mode="rotate",
        output_size="template",
        current_background_index=0,
    )
    db.add(settings)
    await db.commit()
    created = await _get_settings_for_event(db, event_id)
    if not created:
        raise RuntimeError("Failed to create green screen settings")
    return created


@router.post("/preview", response_class=Response)
async def preview_green_screen(
    settings: str = File(...),
    file: UploadFile = File(...),
    background_file: Optional[UploadFile] = File(None),
):
    """
    Preview green screen processing on a single image
    Accepts multipart form data with image file, settings JSON, and optional background image
    Returns processed image as JPEG
    """
    try:
        # Parse settings
        settings_obj = GreenScreenSettingsUpdate(**json.loads(settings))

        # Read uploaded image
        image_bytes = await file.read()
        if not image_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Image file is empty"
            )

        # Decode image
        if not OPENCV_AVAILABLE:
            logger.warning("OpenCV not available, returning original image")
            return Response(content=image_bytes, media_type="image/jpeg")

        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if image is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid image file"
            )

        # Read background if provided
        background = None
        if background_file:
            bg_bytes = await background_file.read()
            if bg_bytes:
                bg_nparr = np.frombuffer(bg_bytes, np.uint8)
                background = cv2.imdecode(bg_nparr, cv2.IMREAD_COLOR)

        # Process image
        result = green_screen_service.process_image(image, settings_obj, background)

        # Encode result
        _, encoded = cv2.imencode(".jpg", result, [cv2.IMWRITE_JPEG_QUALITY, 95])
        result_bytes = encoded.tobytes()

        return Response(content=result_bytes, media_type="image/jpeg")

    except json.JSONDecodeError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid settings JSON")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Green screen preview failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Processing failed: {str(e)}"
        )


@router.post("/process")
async def process_photos(
    event_id: UUID,
    request: GreenScreenProcessRequest,
    photo_ids: List[UUID],
    db: AsyncSession = Depends(get_db),
):
    """
    Batch process photos with green screen settings
    Returns list of processed photo URLs
    """
    try:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Batch green screen processing is not implemented",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch green screen processing failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch processing failed: {str(e)}",
        )


@router.get("/settings/{event_id}", response_model=GreenScreenSettingsResponse)
async def get_green_screen_settings(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get green screen settings for an event"""
    try:
        settings = await _get_or_create_settings_for_event(db, event_id)
        return _settings_response(settings)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get green screen settings: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get settings: {str(e)}",
        )


@router.put("/settings/{event_id}", response_model=GreenScreenSettingsResponse)
async def update_green_screen_settings(
    event_id: UUID,
    settings: GreenScreenSettingsUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update green screen settings for an event"""
    try:
        settings_model = await _get_or_create_settings_for_event(db, event_id)
        update_data = settings.model_dump()
        for field, value in update_data.items():
            setattr(settings_model, field, value)

        await db.commit()
        updated = await _get_settings_for_event(db, event_id)
        if not updated:
            raise RuntimeError("Failed to load updated green screen settings")
        return _settings_response(updated)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update green screen settings: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update settings: {str(e)}",
        )


@router.post("/backgrounds", response_model=GreenScreenBackground)
async def upload_background(
    event_id: UUID = Form(...),
    name: str = Form(...),
    file: UploadFile = File(...),
    overlay_file: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
):
    """Upload a new background image with optional overlay"""
    try:
        # Read background file
        file_bytes = await file.read()
        if not file_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Background file is empty"
            )

        settings = await _get_or_create_settings_for_event(db, event_id)

        # Upload to storage
        filename = file.filename or f"{uuid4().hex}.jpg"
        if r2_storage.is_available():
            background_url = await r2_storage.upload_file(
                file_data=file_bytes,
                filename=filename,
                content_type=file.content_type or "image/jpeg",
                folder=f"green-screen/{event_id}/backgrounds",
            )
        else:
            background_url = _save_local_green_screen_file(
                file_bytes,
                filename,
                event_id,
                "backgrounds",
            )

        # Upload overlay if provided
        overlay_url = None
        if overlay_file:
            overlay_bytes = await overlay_file.read()
            if overlay_bytes:
                overlay_filename = overlay_file.filename or f"{uuid4().hex}.png"
                if r2_storage.is_available():
                    overlay_url = await r2_storage.upload_file(
                        file_data=overlay_bytes,
                        filename=overlay_filename,
                        content_type=overlay_file.content_type or "image/png",
                        folder=f"green-screen/{event_id}/overlays",
                    )
                else:
                    overlay_url = _save_local_green_screen_file(
                        overlay_bytes,
                        overlay_filename,
                        event_id,
                        "overlays",
                    )

        background = GreenScreenBackgroundAsset(
            id=uuid4(),
            settings_id=settings.id,
            name=name,
            background_url=background_url,
            overlay_url=overlay_url,
            sort_order=len(settings.backgrounds),
        )
        db.add(background)
        await db.commit()
        await db.refresh(background)
        return _background_response(background)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upload background: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload background: {str(e)}",
        )


@router.delete("/backgrounds/{background_id}")
async def delete_background(
    background_id: UUID,
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete a background image"""
    try:
        result = await db.execute(
            select(GreenScreenBackgroundAsset)
            .join(GreenScreenSettings)
            .where(GreenScreenBackgroundAsset.id == background_id)
            .where(GreenScreenSettings.event_id == event_id)
        )
        background = result.scalar_one_or_none()
        if not background:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Green screen background not found",
            )

        if r2_storage.is_available():
            await r2_storage.delete_file(background.background_url)
            if background.overlay_url:
                await r2_storage.delete_file(background.overlay_url)
        else:
            _delete_local_green_screen_file(background.background_url)
            _delete_local_green_screen_file(background.overlay_url)

        await db.delete(background)
        await db.commit()
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete background: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete background: {str(e)}",
        )


@router.post("/test-photo", response_model=BackgroundAnalysisResult)
async def analyze_test_photo(
    file: UploadFile = File(...),
):
    """Analyze test photo and provide recommendations"""
    try:
        # Read uploaded image
        image_bytes = await file.read()
        if not image_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Image file is empty"
            )

        # Decode image
        if not OPENCV_AVAILABLE:
            return BackgroundAnalysisResult(
                complexity_score=0.5,
                recommended_mode="ai_removal",
                is_green_background=False,
                suggested_sensitivity=50,
                suggestions=["OpenCV not available, limited analysis"],
            )

        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if image is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid image file"
            )

        # Analyze photo
        analysis = green_screen_service.analyze_test_photo(image)

        return BackgroundAnalysisResult(**analysis)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Test photo analysis failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Analysis failed: {str(e)}"
        )
