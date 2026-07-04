import asyncio
import io
import logging
import shutil
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from PIL import Image, ImageStat

logger = logging.getLogger(__name__)


@dataclass
class CameraCapabilities:
    """相机能力数据类"""

    iso_range: Tuple[int, int] = (100, 6400)
    shutter_speeds: list[str] = None
    wb_modes: list[str] = None
    focus_modes: list[str] = None
    supports_live_view: bool = True

    def __post_init__(self):
        if self.shutter_speeds is None:
            self.shutter_speeds = ["1/30", "1/60", "1/125", "1/250", "1/500", "1/1000"]
        if self.wb_modes is None:
            self.wb_modes = ["自动", "日光", "阴天", "钨丝灯", "荧光灯", "闪光灯"]
        if self.focus_modes is None:
            self.focus_modes = ["AF-S", "AF-C", "MF"]


class CameraController(ABC):
    """相机控制抽象基类"""

    @abstractmethod
    async def connect(self) -> bool:
        """连接相机，返回是否成功"""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """断开相机连接"""
        pass

    @abstractmethod
    async def capture(self) -> bytes:
        """拍摄并返回JPEG字节"""
        pass

    @abstractmethod
    async def get_live_view(self) -> bytes:
        """返回MJPEG帧字节"""
        pass

    @abstractmethod
    async def get_settings(self) -> Dict[str, Any]:
        """获取当前相机设置
        返回格式: {iso, shutter_speed, aperture, white_balance, exposure_compensation, focus_mode}
        """
        pass

    @abstractmethod
    async def set_setting(self, key: str, value: Any) -> None:
        """设置相机参数"""
        pass

    @abstractmethod
    async def get_capabilities(self) -> CameraCapabilities:
        """获取相机支持的能力范围"""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """返回相机是否已连接"""
        pass

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """获取相机状态
        返回格式: {connected, model, firmware_version, battery_level, storage_remaining}
        """
        pass


class WebcamCameraController(CameraController):
    """Web摄像头控制器 - 作为降级方案使用"""

    def __init__(self):
        self._connected = False
        self._settings = {
            "settings_available": True,
            "source": "webcam",
            "iso": 800,
            "shutter_speed": "1/125",
            "aperture": "f/4.0",
            "white_balance": "自动",
            "exposure_compensation": 0.0,
            "focus_mode": "AF-C",
        }
        self._capabilities = CameraCapabilities(iso_range=(100, 3200), supports_live_view=True)

    async def connect(self) -> bool:
        self._connected = True
        logger.info("Webcam controller connected (fallback mode)")
        return True

    async def disconnect(self) -> None:
        self._connected = False
        logger.info("Webcam controller disconnected")

    async def capture(self) -> bytes:
        """Webcam模式下，拍摄由前端实现，这里仅返回占位"""
        raise NotImplementedError("Webcam capture is handled by frontend")

    async def get_live_view(self) -> bytes:
        """Webcam模式下，实时取景由前端实现"""
        raise NotImplementedError("Webcam live view is handled by frontend")

    async def get_settings(self) -> Dict[str, Any]:
        return self._settings.copy()

    async def set_setting(self, key: str, value: Any) -> None:
        if key in self._settings:
            self._settings[key] = value
            logger.info(f"Webcam setting {key} updated to {value} (simulated)")

    async def get_capabilities(self) -> CameraCapabilities:
        return self._capabilities

    def is_connected(self) -> bool:
        return self._connected

    def get_status(self) -> Dict[str, Any]:
        return {
            "connected": self._connected,
            "model": "Web Camera",
            "firmware_version": "1.0.0",
            "battery_level": 100,
            "storage_remaining": 999999,
            "controller_type": "webcam",
        }


class GPhoto2CameraController(CameraController):
    """GPhoto2相机控制器 - 支持1000+型号DSLR"""

    def __init__(self):
        self._connected = False
        self._gphoto2_path = shutil.which("gphoto2")
        self._model = None
        self._capabilities = CameraCapabilities()

    async def _run_command(self, args: list[str], timeout: int = 30) -> Tuple[bytes, bytes, int]:
        """运行gphoto2命令"""
        if not self._gphoto2_path:
            raise RuntimeError("gphoto2 not found in PATH")

        try:
            proc = await asyncio.create_subprocess_exec(
                self._gphoto2_path, *args, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            return stdout, stderr, proc.returncode
        except Exception as e:
            logger.error(f"GPhoto2 command failed: {e}")
            raise

    def is_available(self) -> bool:
        """检查gphoto2是否可用"""
        return self._gphoto2_path is not None

    async def detect_camera(self) -> Optional[str]:
        """检测连接的相机型号"""
        if not self.is_available():
            return None

        try:
            stdout, stderr, code = await self._run_command(["--auto-detect"])
            if code != 0:
                return None

            output = stdout.decode("utf-8", errors="ignore")
            lines = [line.strip() for line in output.split("\n") if line.strip()]
            if len(lines) < 2:
                return None

            # 格式:  Model                          Port
            #        Canon EOS R5                   usb:001,007
            for line in lines[1:]:
                if line:
                    parts = line.split(maxsplit=1)
                    if len(parts) >= 2 and parts[1].startswith("usb:"):
                        return parts[0]

            return None
        except Exception as e:
            logger.warning(f"Camera detection failed: {e}")
            return None

    async def connect(self) -> bool:
        if not self.is_available():
            logger.warning("GPhoto2 not available, cannot connect")
            return False

        try:
            # 检测相机
            self._model = await self.detect_camera()
            if not self._model:
                logger.warning("No GPhoto2 compatible camera detected")
                return False

            # 测试连接
            _, _, code = await self._run_command(["--summary"])
            if code != 0:
                logger.error("Failed to connect to camera")
                return False

            self._connected = True
            logger.info(f"Connected to camera: {self._model}")
            return True
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            self._connected = False
            return False

    async def disconnect(self) -> None:
        self._connected = False
        logger.info("GPhoto2 camera disconnected")

    async def capture(self) -> bytes:
        if not self._connected:
            raise RuntimeError("Camera not connected")

        # 拍摄并下载到stdout
        stdout, stderr, code = await self._run_command(
            ["--capture-image-and-download", "--stdout"], timeout=60
        )

        if code != 0:
            logger.error(f"Capture failed: {stderr.decode()}")
            raise RuntimeError(f"Capture failed: {stderr.decode()}")

        return stdout

    async def get_live_view(self) -> bytes:
        if not self._connected:
            raise RuntimeError("Camera not connected")

        # 捕获实时取景帧
        stdout, stderr, code = await self._run_command(
            ["--capture-movie", "--stdout", "--frames=1"], timeout=10
        )

        if code != 0:
            logger.error(f"Live view capture failed: {stderr.decode()}")
            raise RuntimeError(f"Live view failed: {stderr.decode()}")

        return stdout

    async def get_settings(self) -> Dict[str, Any]:
        if not self._connected:
            return {}

        return {
            "settings_available": False,
            "source": "gphoto2",
            "message": "真实相机参数读取尚未接入，未返回模拟曝光值",
        }

    async def set_setting(self, key: str, value: Any) -> None:
        if not self._connected:
            raise RuntimeError("Camera not connected")

        config_map = {
            "iso": "iso",
            "shutter_speed": "shutterspeed",
            "aperture": "aperture",
            "white_balance": "whitebalance",
            "exposure_compensation": "exposurecompensation",
            "focus_mode": "focusmode",
        }

        gphoto_key = config_map.get(key)
        if not gphoto_key:
            logger.warning(f"Unknown setting: {key}")
            return

        _, stderr, code = await self._run_command(["--set-config", f"{gphoto_key}={value}"])

        if code != 0:
            logger.error(f"Failed to set {key}={value}: {stderr.decode()}")
            raise RuntimeError(f"Set setting failed: {stderr.decode()}")

        logger.info(f"Camera setting {key} updated to {value}")

    async def get_capabilities(self) -> CameraCapabilities:
        return self._capabilities

    def is_connected(self) -> bool:
        return self._connected

    def get_status(self) -> Dict[str, Any]:
        return {
            "connected": self._connected,
            "model": self._model,
            "firmware_version": "Unknown",
            "battery_level": None,  # TODO: 实现电池状态读取
            "storage_remaining": None,  # TODO: 实现存储读取
            "controller_type": "gphoto2",
        }


class CameraManager:
    """相机管理器单例"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._active_controller: Optional[CameraController] = None
        self._webcam_controller = WebcamCameraController()
        self._gphoto2_controller = GPhoto2CameraController()
        self._initialized = True
        logger.info("CameraManager initialized")

    async def initialize(self) -> None:
        """初始化相机管理器，自动检测并连接相机"""
        # 优先尝试gphoto2
        if self._gphoto2_controller.is_available():
            model = await self._gphoto2_controller.detect_camera()
            if model:
                success = await self._gphoto2_controller.connect()
                if success:
                    self._active_controller = self._gphoto2_controller
                    logger.info(f"Using GPhoto2 controller for {model}")
                    return

        # 降级到webcam
        await self._webcam_controller.connect()
        self._active_controller = self._webcam_controller
        logger.info("Using Webcam controller (fallback)")

    async def connect(self) -> bool:
        """连接相机"""
        if self._active_controller:
            return await self._active_controller.connect()
        return False

    async def disconnect(self) -> None:
        """断开相机连接"""
        if self._active_controller:
            await self._active_controller.disconnect()

    def get_controller(self) -> CameraController:
        """获取当前激活的控制器"""
        if not self._active_controller:
            return self._webcam_controller
        return self._active_controller

    async def switch_to_webcam(self) -> None:
        """切换到Webcam模式"""
        if self._active_controller:
            await self._active_controller.disconnect()
        await self._webcam_controller.connect()
        self._active_controller = self._webcam_controller
        logger.info("Switched to Webcam controller")

    async def switch_to_gphoto2(self) -> bool:
        """尝试切换到GPhoto2模式"""
        if not self._gphoto2_controller.is_available():
            return False

        success = await self._gphoto2_controller.connect()
        if success:
            if self._active_controller:
                await self._active_controller.disconnect()
            self._active_controller = self._gphoto2_controller
            logger.info("Switched to GPhoto2 controller")
            return True
        return False


# 全局单例
camera_manager = CameraManager()
