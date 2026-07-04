from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import check_team_member, get_current_active_user, get_db
from app.core.logging import logger
from app.models.models import User
from app.schemas.camera import (
    CameraCapabilitiesResponse,
    CameraSettings,
    CameraSettingsUpdate,
    CameraStatus,
    CameraWizardResult,
)
from app.services.camera_service import CameraController, camera_manager
from app.services.camera_wizard_service import camera_wizard_service

router = APIRouter()


def _get_controller() -> CameraController:
    """获取当前相机控制器"""
    return camera_manager.get_controller()


# ─── 状态 ──────────────────────────────────────────────────────────────────────


@router.get("/status", response_model=CameraStatus)
async def get_camera_status(
    current_user: User = Depends(get_current_active_user),
):
    """获取相机连接状态、型号等"""
    controller = _get_controller()
    status_dict = controller.get_status()
    return CameraStatus(
        connected=status_dict.get("connected", False),
        model=status_dict.get("model"),
        firmware_version=status_dict.get("firmware_version"),
        battery_level=status_dict.get("battery_level"),
        storage_remaining=status_dict.get("storage_remaining"),
        controller_type=status_dict.get("controller_type", "webcam"),
    )


@router.post("/connect")
async def connect_camera(
    current_user: User = Depends(get_current_active_user),
):
    """连接相机"""
    try:
        # 初始化时自动检测
        await camera_manager.initialize()
        controller = _get_controller()
        if controller.is_connected():
            status = controller.get_status()
            return {
                "status": "ok",
                "message": f"已连接到 {status.get('model', '相机')}",
                "connected": True,
            }
        else:
            return {
                "status": "warning",
                "message": "相机连接失败，使用Web摄像头模式",
                "connected": False,
            }
    except Exception as e:
        logger.error(f"Camera connect error: {e}")
        # 降级到webcam
        await camera_manager.switch_to_webcam()
        return {"status": "degraded", "message": "已降级为Web摄像头模式", "connected": True}


@router.post("/disconnect")
async def disconnect_camera(
    current_user: User = Depends(get_current_active_user),
):
    """断开相机"""
    await camera_manager.disconnect()
    return {"status": "ok", "message": "相机已断开"}


# ─── 设置 ──────────────────────────────────────────────────────────────────────


@router.get("/settings")
async def get_camera_settings(
    current_user: User = Depends(get_current_active_user),
):
    """获取当前曝光参数"""
    controller = _get_controller()
    settings = await controller.get_settings()
    return settings


@router.put("/settings")
async def update_camera_settings(
    settings_in: CameraSettingsUpdate,
    current_user: User = Depends(get_current_active_user),
):
    """修改曝光参数"""
    controller = _get_controller()
    updates = settings_in.model_dump(exclude_unset=True)

    for key, value in updates.items():
        if value is not None:
            try:
                await controller.set_setting(key, value)
            except Exception as e:
                logger.error(f"Failed to set {key}={value}: {e}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail=f"设置 {key} 失败: {str(e)}"
                )

    return {"status": "ok", "message": "设置已更新"}


# ─── 拍摄 ──────────────────────────────────────────────────────────────────────


@router.post("/capture")
async def capture_photo(
    event_id: Optional[UUID] = Query(None),
    session_id: Optional[UUID] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """远程触发拍摄，下载原片并存储

    在webcam模式下，拍摄由前端Canvas捕获实现，此端点返回指示前端进行拍摄。
    在DSLR模式下，触发相机物理拍摄。
    """
    import uuid

    from app.services.event_service import EventService
    from app.services.photo_service import PhotoService
    from app.services.subscription_service import SubscriptionService

    controller = _get_controller()
    status = controller.get_status()
    controller_type = status.get("controller_type", "webcam")

    if controller_type == "webcam":
        # Webcam模式: 前端处理拍摄，这里返回指示
        return {
            "status": "ok",
            "message": "Webcam模式，请使用前端Canvas捕获",
            "capture_method": "webcam",
            "settings": await controller.get_settings(),
        }

    # DSLR模式: 触发拍摄
    try:
        image_data = await controller.capture()

        if not image_data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="相机拍摄失败，未获取到图像数据",
            )

        # 保存到本地临时目录
        import os
        from pathlib import Path

        upload_dir = Path("uploads") / "camera_captures"
        upload_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{uuid.uuid4().hex}.jpg"
        filepath = upload_dir / filename
        filepath.write_bytes(image_data)

        photo = None
        if event_id:
            event_service = EventService(db)
            event = await event_service.get_event(event_id)
            if not event:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
            await check_team_member(event.team_id, current_user, db)
            await SubscriptionService(db).ensure_can_upload_photo(event.team_id, event.id)
            photo = await PhotoService(db).upload_photo_bytes(
                file_data=image_data,
                filename=filename,
                content_type="image/jpeg",
                event_id=event_id,
                session_id=session_id,
            )

        return {
            "status": "ok",
            "message": "拍摄成功",
            "capture_method": "dslr",
            "local_path": str(filepath),
            "file_size": len(image_data),
            "photo": photo,
            "settings": await controller.get_settings(),
        }

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"DSLR capture failed: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="拍摄失败")


# ─── 能力 ──────────────────────────────────────────────────────────────────────


@router.get("/capabilities", response_model=CameraCapabilitiesResponse)
async def get_camera_capabilities(
    current_user: User = Depends(get_current_active_user),
):
    """获取相机能力范围"""
    controller = _get_controller()
    capabilities = await controller.get_capabilities()
    return CameraCapabilitiesResponse(
        iso_range=capabilities.iso_range,
        shutter_speeds=capabilities.shutter_speeds,
        wb_modes=capabilities.wb_modes,
        focus_modes=capabilities.focus_modes,
        supports_live_view=capabilities.supports_live_view,
    )


# ─── 实时取景 ──────────────────────────────────────────────────────────────────


@router.get("/live-view")
async def get_live_view_status(
    current_user: User = Depends(get_current_active_user),
):
    """获取实时取景状态"""
    controller = _get_controller()
    is_connected = controller.is_connected()
    controller_type = controller.get_status().get("controller_type", "webcam")

    return {
        "available": is_connected,
        "source": controller_type,
        "format": "mjpeg" if controller_type == "gphoto2" else "webrtc",
        "fps": 30 if controller_type == "gphoto2" else None,
    }


# ─── 向导 ──────────────────────────────────────────────────────────────────────


@router.get("/wizard/step1")
async def wizard_step1_detect(
    current_user: User = Depends(get_current_active_user),
):
    """向导步骤1: 检测相机型号，加载预设"""
    model = await camera_wizard_service.detect_camera_model()
    presets = await camera_wizard_service.get_camera_presets(model)

    return {
        "step": 1,
        "title": "检测相机型号",
        "description": "检测连接的相机型号并加载推荐预设",
        "model": model,
        "presets": presets,
        "recommendations": [
            "请确保相机已通过USB连接并开启",
            "相机切换到M档（手动模式）以获得最佳控制",
        ],
    }


@router.post("/wizard/step2")
async def wizard_step2_flash(
    current_user: User = Depends(get_current_active_user),
):
    """向导步骤2: 闪光灯配置"""
    flash_settings = camera_wizard_service.get_flash_settings(use_flash=True)

    return {
        "step": 2,
        "title": "闪光灯配置",
        "description": "设置是否使用闪光灯及功率",
        "flash_settings": flash_settings,
    }


@router.post("/wizard/step3")
async def wizard_step3_test_photo(
    current_user: User = Depends(get_current_active_user),
):
    """向导步骤3: 拍摄测试照片并分析曝光"""
    controller = _get_controller()
    controller_type = controller.get_status().get("controller_type", "webcam")

    if controller_type == "webcam":
        return {
            "step": 3,
            "title": "测试照片分析",
            "description": "请先拍摄一张测试照片后再进行分析",
            "status": "awaiting_test_photo",
            "analysis": None,
        }

    # DSLR模式下尝试拍摄测试照片
    try:
        image_data = await controller.capture()
        analysis = camera_wizard_service.analyze_test_photo(image_data)

        import base64

        photo_base64 = base64.b64encode(image_data).decode("utf-8")

        return {
            "step": 3,
            "title": "测试照片分析",
            "description": "拍摄测试照片并分析曝光",
            "test_photo": f"data:image/jpeg;base64,{photo_base64}",
            "analysis": {
                "brightness": analysis.brightness,
                "is_underexposed": analysis.is_underexposed,
                "is_overexposed": analysis.is_overexposed,
                "recommendations": analysis.recommendations,
                "suggested_iso": analysis.suggested_iso,
                "suggested_shutter": analysis.suggested_shutter,
                "suggested_aperture": analysis.suggested_aperture,
            },
        }
    except Exception as e:
        logger.error(f"Test photo capture failed: {e}")
        return {
            "step": 3,
            "title": "测试照片分析",
            "description": "未能拍摄测试照片",
            "error": str(e),
        }


@router.post("/wizard/analyze-test-photo")
async def wizard_analyze_test_photo(
    current_user: User = Depends(get_current_active_user),
):
    """分析上传的测试照片 (用于webcam模式下前端上传)"""
    return {"status": "ok", "message": "请使用multipart/form-data上传测试照片到本端点"}


@router.post("/wizard/step4")
async def wizard_step4_flash_power(
    current_user: User = Depends(get_current_active_user),
):
    """向导步骤4: 闪光灯功率微调"""
    flash_settings = camera_wizard_service.get_flash_settings(power="1/2")

    return {
        "step": 4,
        "title": "闪光灯功率配置",
        "description": "微调闪光灯输出功率",
        "flash_settings": flash_settings,
    }


@router.post("/wizard/step5")
async def wizard_step5_confirm(
    current_user: User = Depends(get_current_active_user),
):
    """向导步骤5: 最终确认"""
    controller = _get_controller()
    settings = await controller.get_settings()

    return {
        "step": 5,
        "title": "最终确认",
        "description": "确认所有设置，开始拍照",
        "final_settings": settings,
        "tips": ["拍摄时保持相机稳定", "及时检查照片效果", "可根据实际效果微调参数"],
    }
