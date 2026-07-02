from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime


class CameraCapabilities(BaseModel):
    """相机能力模型"""
    iso_range: tuple[int, int] = (100, 6400)
    shutter_speeds: List[str] = ["1/30", "1/60", "1/125", "1/250", "1/500", "1/1000"]
    wb_modes: List[str] = ["自动", "日光", "阴天", "钨丝灯", "荧光灯", "闪光灯", "自定义"]
    focus_modes: List[str] = ["AF-S", "AF-C", "MF"]
    exposure_compensation_range: tuple[float, float] = (-3.0, 3.0)
    supports_live_view: bool = True
    supports_video: bool = False
    model_config = ConfigDict(from_attributes=True)


class CameraSettings(BaseModel):
    """相机设置模型"""
    iso: int = 800
    shutter_speed: str = "1/125"
    aperture: str = "f/4.0"
    white_balance: str = "自动"
    exposure_compensation: float = 0.0
    focus_mode: str = "AF-C"
    model_config = ConfigDict(from_attributes=True)


class CameraStatus(BaseModel):
    """相机状态模型"""
    connected: bool = False
    model: Optional[str] = None
    firmware_version: Optional[str] = None
    battery_level: Optional[int] = None  # 0-100
    storage_remaining: Optional[int] = None  # MB
    controller_type: str = "webcam"  # webcam, gphoto2, canon, nikon
    model_config = ConfigDict(from_attributes=True)


class CameraSettingsUpdate(BaseModel):
    """相机设置更新请求"""
    iso: Optional[int] = None
    shutter_speed: Optional[str] = None
    aperture: Optional[str] = None
    white_balance: Optional[str] = None
    exposure_compensation: Optional[float] = None
    focus_mode: Optional[str] = None


class CameraCapabilitiesResponse(CameraCapabilities):
    pass


class CameraWizardStep(BaseModel):
    """相机向导步骤"""
    step: int
    title: str
    description: str
    options: Optional[Dict[str, Any]] = None


class CameraWizardResult(BaseModel):
    """相机向导结果"""
    success: bool
    settings: CameraSettings
    recommendations: List[str]
    test_photo_url: Optional[str] = None


class ExposureAnalysis(BaseModel):
    """曝光分析结果"""
    brightness: float  # 0-1
    is_underexposed: bool
    is_overexposed: bool
    recommendations: List[str]
    suggested_iso: Optional[int] = None
    suggested_shutter: Optional[str] = None
    suggested_aperture: Optional[str] = None