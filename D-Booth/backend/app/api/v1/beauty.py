"""
Beauty Processing API endpoints
POST /api/v1/beauty/preview     - Process photo with beauty params, return image
POST /api/v1/beauty/apply       - Async beauty via Celery (for photo sessions)
POST /api/v1/beauty/detect-face - Detect faces and return key points
GET  /api/v1/beauty/presets     - Return beauty preset parameter sets
GET  /api/v1/beauty/status      - Check if beauty engine is available
"""

from typing import List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import Response
from pydantic import BaseModel

from app.services.beauty_service import BeautyParams, beauty_processor

router = APIRouter()

_BEAUTY_PRESETS = [
    {
        "name": "原图",
        "params": {
            "smooth": 0,
            "whiten": 0,
            "thinFace": 0,
            "bigEye": 0,
            "eyeLight": 0,
            "acne": 0,
            "nasolabial": 0,
            "teethWhiten": 0,
            "lipColor": 0,
        },
    },
    {
        "name": "自然",
        "params": {
            "smooth": 60,
            "whiten": 40,
            "thinFace": 30,
            "bigEye": 20,
            "eyeLight": 30,
            "acne": 20,
            "nasolabial": 25,
            "teethWhiten": 30,
            "lipColor": 15,
        },
    },
    {
        "name": "清新",
        "params": {
            "smooth": 55,
            "whiten": 55,
            "thinFace": 35,
            "bigEye": 30,
            "eyeLight": 40,
            "acne": 25,
            "nasolabial": 30,
            "teethWhiten": 40,
            "lipColor": 20,
        },
    },
    {
        "name": "白皙",
        "params": {
            "smooth": 70,
            "whiten": 85,
            "thinFace": 40,
            "bigEye": 35,
            "eyeLight": 45,
            "acne": 30,
            "nasolabial": 35,
            "teethWhiten": 50,
            "lipColor": 10,
        },
    },
    {
        "name": "元气",
        "params": {
            "smooth": 50,
            "whiten": 35,
            "thinFace": 50,
            "bigEye": 55,
            "eyeLight": 60,
            "acne": 15,
            "nasolabial": 20,
            "teethWhiten": 35,
            "lipColor": 55,
        },
    },
    {
        "name": "高级",
        "params": {
            "smooth": 65,
            "whiten": 30,
            "thinFace": 45,
            "bigEye": 25,
            "eyeLight": 35,
            "acne": 40,
            "nasolabial": 45,
            "teethWhiten": 25,
            "lipColor": 25,
        },
    },
    {
        "name": "胶片",
        "params": {
            "smooth": 45,
            "whiten": 20,
            "thinFace": 25,
            "bigEye": 15,
            "eyeLight": 20,
            "acne": 10,
            "nasolabial": 10,
            "teethWhiten": 15,
            "lipColor": 20,
        },
    },
    {
        "name": "奶油",
        "params": {
            "smooth": 85,
            "whiten": 60,
            "thinFace": 30,
            "bigEye": 40,
            "eyeLight": 50,
            "acne": 35,
            "nasolabial": 40,
            "teethWhiten": 45,
            "lipColor": 35,
        },
    },
    {
        "name": "韩系",
        "params": {
            "smooth": 75,
            "whiten": 70,
            "thinFace": 65,
            "bigEye": 60,
            "eyeLight": 55,
            "acne": 45,
            "nasolabial": 50,
            "teethWhiten": 55,
            "lipColor": 45,
        },
    },
    {
        "name": "日系",
        "params": {
            "smooth": 60,
            "whiten": 50,
            "thinFace": 40,
            "bigEye": 50,
            "eyeLight": 45,
            "acne": 30,
            "nasolabial": 35,
            "teethWhiten": 40,
            "lipColor": 50,
        },
    },
]


@router.get("/status")
async def status_check():
    """Return engine availability so frontend can decide UI behaviour."""
    from app.services.beauty_service import MEDIAPIPE_AVAILABLE, OPENCV_AVAILABLE

    return {
        "opencv_available": OPENCV_AVAILABLE,
        "mediapipe_available": MEDIAPIPE_AVAILABLE,
        "beauty_ready": OPENCV_AVAILABLE and MEDIAPIPE_AVAILABLE,
        "presets_count": len(_BEAUTY_PRESETS),
    }


@router.get("/presets")
async def get_presets():
    return _BEAUTY_PRESETS


@router.post("/preview")
async def preview_beauty(
    smooth: int = Form(default=0, ge=0, le=100),
    whiten: int = Form(default=0, ge=0, le=100),
    thinFace: int = Form(default=0, ge=0, le=100),
    bigEye: int = Form(default=0, ge=0, le=100),
    eyeLight: int = Form(default=0, ge=0, le=100),
    acne: int = Form(default=0, ge=0, le=100),
    nasolabial: int = Form(default=0, ge=0, le=100),
    teethWhiten: int = Form(default=0, ge=0, le=100),
    lipColor: int = Form(default=0, ge=0, le=100),
    quality: str = Form(default="full"),
    file: UploadFile = File(...),
):
    """Apply beauty params and return the JPEG result directly.
    ``quality``: "lite" (LiveView, <50ms) or "full" (print/preview, higher quality).
    """
    try:
        image_bytes = await file.read()
    except Exception as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Read error: {e}")
    if not image_bytes:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Empty file")

    params = BeautyParams(
        smooth=smooth,
        whiten=whiten,
        thinFace=thinFace,
        bigEye=bigEye,
        eyeLight=eyeLight,
        acne=acne,
        nasolabial=nasolabial,
        teethWhiten=teethWhiten,
        lipColor=lipColor,
    )
    result = beauty_processor.process_image(image_bytes, params, quality=quality)
    return Response(content=result, media_type="image/jpeg")


@router.post("/detect-face")
async def detect_face(file: UploadFile = File(...)):
    try:
        image_bytes = await file.read()
    except Exception as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Read error: {e}")
    if not image_bytes:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Empty file")

    faces = beauty_processor.detect_faces(image_bytes, quality="full")
    return {
        "face_count": len(faces),
        "faces": [
            {
                "x": f.x,
                "y": f.y,
                "width": f.width,
                "height": f.height,
                "confidence": f.confidence,
                "landmark_count": len(f.landmarks) if f.landmarks else 0,
            }
            for f in faces
        ],
    }


class ApplyRequest(BaseModel):
    photo_id: str
    image_url: str
    params: dict = {}
    quality: str = "full"


@router.post("/apply", status_code=status.HTTP_202_ACCEPTED)
async def apply_beauty_async(req: ApplyRequest):
    """Submit beauty processing as a Celery background task.
    Returns immediately with 202 Accepted; the caller polls the photo record.
    """
    try:
        from app.tasks.beauty_tasks import apply_beauty_task

        task = apply_beauty_task.delay(
            photo_id=req.photo_id,
            image_url=req.image_url,
            params=req.params,
            quality=req.quality,
        )
        return {"status": "accepted", "task_id": task.id, "photo_id": req.photo_id}
    except Exception as e:
        # Celery unavailable → fall back to sync processing
        from app.services.beauty_service import BeautyProcessor

        result = beauty_processor.process_image(b"", BeautyParams(), quality=req.quality)
        return {"status": "sync_fallback", "photo_id": req.photo_id}
