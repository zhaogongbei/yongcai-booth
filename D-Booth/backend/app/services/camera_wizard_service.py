import io
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image, ImageStat

logger = logging.getLogger(__name__)


@dataclass
class ExposureAnalysis:
    """曝光分析结果"""

    brightness: float  # 0-1
    is_underexposed: bool
    is_overexposed: bool
    recommendations: List[str]
    suggested_iso: Optional[int] = None
    suggested_shutter: Optional[str] = None
    suggested_aperture: Optional[str] = None


class CameraWizardService:
    """相机设置向导服务"""

    @staticmethod
    async def detect_camera_model() -> Optional[str]:
        """检测相机型号"""
        from app.services.camera_service import camera_manager

        controller = camera_manager.get_controller()
        status = controller.get_status()
        return status.get("model")

    @staticmethod
    async def get_camera_presets(model: Optional[str] = None) -> Dict[str, Any]:
        """根据相机型号加载预设"""
        presets = {
            "Canon EOS R5": {
                "iso": 400,
                "shutter_speed": "1/125",
                "aperture": "f/5.6",
                "white_balance": "闪光灯",
                "default_flash_power": "1/4",
            },
            "Canon EOS 5D Mark IV": {
                "iso": 800,
                "shutter_speed": "1/125",
                "aperture": "f/5.6",
                "white_balance": "闪光灯",
                "default_flash_power": "1/4",
            },
            "Nikon Z6": {
                "iso": 800,
                "shutter_speed": "1/125",
                "aperture": "f/5.6",
                "white_balance": "闪光灯",
                "default_flash_power": "1/4",
            },
            "Sony A7 III": {
                "iso": 640,
                "shutter_speed": "1/125",
                "aperture": "f/5.6",
                "white_balance": "闪光灯",
                "default_flash_power": "1/4",
            },
        }

        if model and model in presets:
            return presets[model]

        # 通用预设
        return {
            "iso": 800,
            "shutter_speed": "1/125",
            "aperture": "f/5.6",
            "white_balance": "闪光灯",
            "default_flash_power": "1/2",
        }

    @staticmethod
    def analyze_test_photo(image_data: bytes) -> ExposureAnalysis:
        """分析测试照片的曝光情况

        Args:
            image_data: 测试照片的JPEG字节数据

        Returns:
            ExposureAnalysis对象，包含曝光分析和建议
        """
        try:
            image = Image.open(io.BytesIO(image_data)).convert("L")
            stat = ImageStat.Stat(image)

            # 计算平均亮度 (0-255)
            mean_brightness = stat.mean[0]
            brightness = mean_brightness / 255.0

            # 计算直方图
            histogram = image.histogram()

            # 分析暗部和亮部像素比例
            total_pixels = sum(histogram)
            dark_pixels = sum(histogram[:64])  # 0-64 暗部
            bright_pixels = sum(histogram[192:])  # 192-255 亮部

            dark_ratio = dark_pixels / total_pixels if total_pixels > 0 else 0
            bright_ratio = bright_pixels / total_pixels if total_pixels > 0 else 0

            is_underexposed = brightness < 0.3 and dark_ratio > 0.3
            is_overexposed = brightness > 0.75 and bright_ratio > 0.3

            recommendations = []
            suggested_iso = None
            suggested_shutter = None
            suggested_aperture = None

            if is_underexposed:
                recommendations.append("照片偏暗，建议提高ISO或降低快门速度")
                # 根据暗度建议调整
                if brightness < 0.15:
                    suggested_iso = 1600
                    suggested_shutter = "1/60"
                    recommendations.append("严重曝光不足，建议ISO提高到1600，快门降至1/60s")
                elif brightness < 0.25:
                    suggested_iso = 800
                    suggested_shutter = "1/80"
                    recommendations.append(
                        "曝光不足，建议ISO提高到800，快门降至1/80s推荐将光圈开大至f/4.0"
                    )
                else:
                    suggested_iso = 640
                    suggested_shutter = "1/100"
                    recommendations.append("轻微曝光不足，建议ISO提高到640，快门降至1/100s")
            elif is_overexposed:
                recommendations.append("照片偏亮，建议降低ISO或提高快门速度")
                if brightness > 0.9:
                    suggested_iso = 100
                    suggested_shutter = "1/500"
                    recommendations.append("严重曝光过度，建议ISO降至100，快门提高至1/500s")
                elif brightness > 0.8:
                    suggested_iso = 200
                    suggested_shutter = "1/250"
                    recommendations.append("曝光过度，建议ISO降至200，快门提高至1/250s")
                else:
                    suggested_iso = 400
                    suggested_shutter = "1/200"
                    recommendations.append("轻微曝光过度，建议ISO降至400，快门提高至1/200s")
            else:
                recommendations.append("曝光正常，当前设置在合理范围内")

            logger.info(
                f"Photo analysis: brightness={brightness:.2f}, "
                f"underexposed={is_underexposed}, overexposed={is_overexposed}"
            )

            return ExposureAnalysis(
                brightness=brightness,
                is_underexposed=is_underexposed,
                is_overexposed=is_overexposed,
                recommendations=recommendations,
                suggested_iso=suggested_iso,
                suggested_shutter=suggested_shutter,
                suggested_aperture=suggested_aperture,
            )

        except Exception as e:
            logger.error(f"Failed to analyze test photo: {e}")
            return ExposureAnalysis(
                brightness=0.5,
                is_underexposed=False,
                is_overexposed=False,
                recommendations=["无法分析测试照片，请手动调整参数"],
            )

    @staticmethod
    def get_flash_settings(power: Optional[str] = None, use_flash: bool = True) -> Dict[str, Any]:
        """获取闪光灯配置建议

        Args:
            power: 闪光灯功率 (如 "1/1", "1/2", "1/4", "1/8")
            use_flash: 是否使用闪光灯
        """
        if not use_flash:
            return {
                "use_flash": False,
                "recommended_power": None,
                "recommendations": ["不使用闪光灯，建议开启环境光照明"],
            }

        return {
            "use_flash": True,
            "recommended_power": power or "1/2",
            "power_options": ["1/1", "1/2", "1/4", "1/8", "1/16"],
            "recommendations": [
                "使用闪光灯时推荐快门速度不超过1/200s（同步速度限制）",
                "ISO建议设置为400-800以获得合适的闪光曝光",
                "闪光灯功率1/2为大多数场合的推荐起始值",
            ],
        }


# 服务单例
camera_wizard_service = CameraWizardService()
