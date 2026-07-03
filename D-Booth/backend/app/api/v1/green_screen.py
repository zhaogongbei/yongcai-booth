"""
Green Screen API Endpoints
"""

import io
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
from uuid import UUID, uuid4

import numpy as np
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import logger
from app.repositories.event_repository import EventRepository
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
        # TODO: Implement actual database retrieval
        # For now return default settings
        return GreenScreenSettingsResponse(
            id=UUID(int=0),
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
            backgrounds=[],
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
        )
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
        # TODO: Implement actual database update
        # For now return the updated settings
        return GreenScreenSettingsResponse(
            id=UUID(int=0),
            event_id=event_id,
            **settings.model_dump(),
            backgrounds=[],
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
        )
    except Exception as e:
        logger.error(f"Failed to update green screen settings: {str(e)}")
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

        # TODO: Save to database
        return GreenScreenBackground(
            id=uuid4(),
            name=name,
            background_url=background_url,
            overlay_url=overlay_url,
            order=0,
            created_at=datetime.now(timezone.utc),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upload background: {str(e)}")
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
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Green screen background deletion is not implemented",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete background: {str(e)}")
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

    except Exception as e:
        logger.error(f"Test photo analysis failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Analysis failed: {str(e)}"
        )
