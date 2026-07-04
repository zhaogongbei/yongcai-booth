from pathlib import Path
from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.api.deps import get_current_active_user
from app.models.models import User
from app.services.gopro_service import GoProDevice, GoProStatus, gopro_controller

router = APIRouter()

GOPRO_UPLOAD_DIR = Path("uploads") / "gopro"


def _save_gopro_media(media_bytes: bytes, extension: str) -> str:
    GOPRO_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"gopro_{uuid4().hex}.{extension.lstrip('.')}"
    file_path = GOPRO_UPLOAD_DIR / filename
    file_path.write_bytes(media_bytes)
    return f"/api/v1/media/gopro/{filename}"


class GoProConnectRequest(BaseModel):
    ip_address: str
    name: Optional[str] = None
    model: Optional[str] = None


@router.get("/discover", response_model=List[dict])
async def discover_gopros(current_user: User = Depends(get_current_active_user)):
    """Discover available GoPro devices on the network"""
    devices = await gopro_controller.discover()
    return [
        {
            "name": d.name,
            "ip_address": d.ip_address,
            "model": d.model,
            "connected": d.connected,
        }
        for d in devices
    ]


@router.post("/connect", response_model=dict)
async def connect_gopro(
    request: GoProConnectRequest, current_user: User = Depends(get_current_active_user)
):
    """Connect to a GoPro device"""
    device = GoProDevice(
        name=request.name or "GoPro",
        ip_address=request.ip_address,
        model=request.model or "Unknown",
    )
    success = await gopro_controller.connect(device)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to connect to GoPro. Check IP and ensure device is in WiFi mode.",
        )
    return {
        "success": True,
        "device": {
            "name": gopro_controller.device.name if gopro_controller.device else "GoPro",
            "ip_address": request.ip_address,
            "connected": True,
        },
    }


@router.get("/status", response_model=dict)
async def get_gopro_status(current_user: User = Depends(get_current_active_user)):
    """Get status of connected GoPro"""
    if not gopro_controller.is_connected:
        return {
            "connected": False,
            "status": None,
        }

    status = await gopro_controller.get_status()
    return {
        "connected": True,
        "device": (
            {
                "name": gopro_controller.device.name,
                "ip_address": gopro_controller.device.ip_address,
                "model": gopro_controller.device.model,
            }
            if gopro_controller.device
            else None
        ),
        "status": {
            "battery_level": status.battery_level,
            "sd_card_remaining": status.sd_card_remaining,
            "wifi_signal": status.wifi_signal,
            "recording": status.recording,
        },
    }


@router.post("/photo", response_model=dict)
async def take_gopro_photo(current_user: User = Depends(get_current_active_user)):
    """Take a photo with the connected GoPro and return download URL"""
    if not gopro_controller.is_connected:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No GoPro connected")

    photo_bytes = await gopro_controller.take_photo()
    if not photo_bytes:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to take photo from GoPro",
        )

    media_url = _save_gopro_media(photo_bytes, "jpg")
    return {"success": True, "temp_url": media_url, "size": len(photo_bytes)}


@router.post("/record/start", response_model=dict)
async def start_recording(current_user: User = Depends(get_current_active_user)):
    """Start video recording on GoPro"""
    if not gopro_controller.is_connected:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No GoPro connected")

    success = await gopro_controller.start_recording()
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to start recording"
        )

    return {"success": True}


@router.post("/record/stop", response_model=dict)
async def stop_recording(current_user: User = Depends(get_current_active_user)):
    """Stop recording on GoPro and return the video URL"""
    if not gopro_controller.is_connected:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No GoPro connected")

    video_bytes = await gopro_controller.stop_recording()
    if not video_bytes:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to stop recording or download video",
        )

    media_url = _save_gopro_media(video_bytes, "mp4")
    return {"success": True, "temp_url": media_url, "size": len(video_bytes)}


@router.post("/disconnect", response_model=dict)
async def disconnect_gopro(current_user: User = Depends(get_current_active_user)):
    """Disconnect from GoPro"""
    await gopro_controller.disconnect()
    return {"success": True}
