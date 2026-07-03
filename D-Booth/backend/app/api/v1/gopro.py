from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.api.deps import get_current_active_user
from app.models.models import User
from app.services.gopro_service import GoProDevice, GoProStatus, gopro_controller

router = APIRouter()


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

    # Save photo to temporary storage
    import os
    import tempfile
    from uuid import uuid4

    from app.core.config import settings

    temp_dir = tempfile.gettempdir()
    filename = f"gopro_photo_{uuid4().hex}.jpg"
    file_path = os.path.join(temp_dir, filename)

    with open(file_path, "wb") as f:
        f.write(photo_bytes)

    # Return local temp URL (frontend should upload this to R2)
    base_url = f"http://{settings.HOST}:{settings.PORT}" if settings.DEBUG else ""
    return {"success": True, "temp_url": f"{base_url}/temp/{filename}", "size": len(photo_bytes)}


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

    import os
    import tempfile
    from uuid import uuid4

    from app.core.config import settings

    temp_dir = tempfile.gettempdir()
    filename = f"gopro_video_{uuid4().hex}.mp4"
    file_path = os.path.join(temp_dir, filename)

    with open(file_path, "wb") as f:
        f.write(video_bytes)

    base_url = f"http://{settings.HOST}:{settings.PORT}" if settings.DEBUG else ""
    return {"success": True, "temp_url": f"{base_url}/temp/{filename}", "size": len(video_bytes)}


@router.post("/disconnect", response_model=dict)
async def disconnect_gopro(current_user: User = Depends(get_current_active_user)):
    """Disconnect from GoPro"""
    await gopro_controller.disconnect()
    return {"success": True}
