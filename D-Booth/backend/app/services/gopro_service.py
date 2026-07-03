import asyncio
from typing import List, Optional

import httpx
from pydantic import BaseModel, Field

from app.core.logging import logger


class GoProDevice(BaseModel):
    name: str
    ip_address: str
    model: str
    connected: bool = False


class GoProStatus(BaseModel):
    battery_level: int = 0
    sd_card_remaining: int = 0
    wifi_signal: int = 0
    recording: bool = False


class _GoProController:
    """Internal GoPro controller using GoPro HTTP API.

    This is a singleton-like class that manages a single active GoPro connection.
    GoPro HTTP API reference: https://github.com/KonradIT/gopro-py-api

    Graceful degradation: if no GoPro is available on the network, all operations
    log a warning and return empty/default values rather than crashing.
    """

    def __init__(self):
        self._device: Optional[GoProDevice] = None
        self._http_client: Optional[httpx.AsyncClient] = None
        self._connected = False

    async def discover(self) -> List[GoProDevice]:
        """Scan the network for GoPro cameras.

        GoPro cameras on WiFi typically have a fixed IP range and hostname.
        This tries to find them via multiple strategies.
        """
        discovered = []
        # Common GoPro IP ranges
        candidates = [
            "10.5.5.9",  # Standard GoPro WiFi IP (HERO5+ AP mode)
            "172.20.100.51",  # Alternative
            "172.26.122.51",  # Alternative
            "172.28.228.51",  # Alternative
        ]

        async def try_device(ip: str) -> Optional[GoProDevice]:
            try:
                async with httpx.AsyncClient(timeout=2) as client:
                    # Try to reach GoPro info endpoint
                    response = await client.get(f"http://{ip}/gp/gpControl/info", timeout=2)
                    if response.status_code == 200:
                        info = response.json()
                        model = info.get("ap_ssid", "GoPro")
                        return GoProDevice(name=model, ip_address=ip, model=model)
            except Exception:
                pass
            return None

        tasks = [try_device(ip) for ip in candidates]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, GoProDevice):
                discovered.append(result)

        if not discovered:
            logger.info("No GoPro devices discovered on the network")

        return discovered

    async def connect(self, device: GoProDevice) -> bool:
        """Connect to a specific GoPro device"""
        try:
            self._http_client = httpx.AsyncClient(
                base_url=f"http://{device.ip_address}", timeout=5.0
            )
            # Verify connectivity
            response = await self._http_client.get("/gp/gpControl/info")
            if response.status_code == 200:
                self._device = device
                self._device.connected = True
                self._connected = True
                logger.info(f"Connected to GoPro at {device.ip_address}")
                return True
        except Exception as e:
            logger.warning(f"Failed to connect to GoPro at {device.ip_address}: {e}")
            self._connected = False
            if self._http_client:
                await self._http_client.aclose()
                self._http_client = None
        return False

    async def disconnect(self):
        """Disconnect from the GoPro"""
        self._connected = False
        self._device = None
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
        logger.info("Disconnected from GoPro")

    async def get_status(self) -> GoProStatus:
        """Get battery/SD card/WiFi status from the connected GoPro"""
        if not self._connected or not self._http_client:
            logger.warning("GoPro not connected, returning empty status")
            return GoProStatus()

        try:
            response = await self._http_client.get("/gp/gpControl/status")
            if response.status_code == 200:
                data = response.json()
                status = data.get("status", {})
                return GoProStatus(
                    battery_level=status.get("1", 0),  # Internal battery level
                    sd_card_remaining=status.get("54", 0),  # Remaining photos/videos
                    wifi_signal=status.get("48", 0),  # WiFi signal
                    recording=bool(status.get("8", 0)),  # Recording status
                )
        except Exception as e:
            logger.warning(f"Failed to get GoPro status: {e}")

        return GoProStatus()

    async def take_photo(self) -> Optional[bytes]:
        """Take a photo and download it.

        Returns:
            Photo bytes if successful, None otherwise
        """
        if not self._connected or not self._http_client:
            logger.warning("GoPro not connected, cannot take photo")
            return None

        try:
            # Trigger shutter - mode 1 = photo
            resp = await self._http_client.get("/gp/gpControl/command/shutter", params={"p": "1"})
            if resp.status_code != 200:
                logger.warning(f"Failed to trigger shutter, status: {resp.status_code}")
                return None

            # Wait for the photo to be captured and saved
            await asyncio.sleep(2)

            # Get media list to find the latest photo
            media_resp = await self._http_client.get("/gp/gpMediaList")
            if media_resp.status_code != 200:
                logger.warning(f"Failed to get media list, status: {media_resp.status_code}")
                return None

            media_data = media_resp.json()
            media_list = media_data.get("media", [])
            if not media_list:
                logger.warning("No media found on GoPro")
                return None

            # Get the latest directory and file
            latest_dir = media_list[-1]
            dir_name = latest_dir.get("d", "")
            files = latest_dir.get("fs", [])
            if not files:
                return None

            latest_file = files[-1]
            file_name = latest_file.get("n", "")

            # Download the photo
            download_url = f"/videos/DCIM/{dir_name}/{file_name}"
            download_resp = await self._http_client.get(download_url)
            if download_resp.status_code == 200:
                logger.info(f"Photo downloaded from GoPro: {file_name}")
                return download_resp.content
            else:
                logger.warning(f"Failed to download photo, status: {download_resp.status_code}")
        except Exception as e:
            logger.warning(f"Failed to take photo from GoPro: {e}")

        return None

    async def start_recording(self) -> bool:
        """Start video recording"""
        if not self._connected or not self._http_client:
            logger.warning("GoPro not connected, cannot start recording")
            return False

        try:
            resp = await self._http_client.get("/gp/gpControl/command/shutter", params={"p": "1"})
            if resp.status_code == 200:
                logger.info("GoPro recording started")
                return True
            logger.warning(f"Failed to start recording, status: {resp.status_code}")
        except Exception as e:
            logger.warning(f"Failed to start GoPro recording: {e}")

        return False

    async def stop_recording(self) -> Optional[bytes]:
        """Stop recording and download the video"""
        if not self._connected or not self._http_client:
            logger.warning("GoPro not connected, cannot stop recording")
            return None

        try:
            # Stop recording
            resp = await self._http_client.get("/gp/gpControl/command/shutter", params={"p": "0"})
            if resp.status_code != 200:
                logger.warning(f"Failed to stop recording, status: {resp.status_code}")
                return None

            await asyncio.sleep(2)

            # Get the latest video file
            media_resp = await self._http_client.get("/gp/gpMediaList")
            if media_resp.status_code != 200:
                return None

            media_data = media_resp.json()
            media_list = media_data.get("media", [])
            if not media_list:
                return None

            latest_dir = media_list[-1]
            dir_name = latest_dir.get("d", "")
            files = latest_dir.get("fs", [])
            if not files:
                return None

            latest_file = files[-1]
            file_name = latest_file.get("n", "")

            download_url = f"/videos/DCIM/{dir_name}/{file_name}"
            download_resp = await self._http_client.get(download_url)
            if download_resp.status_code == 200:
                logger.info(f"Video downloaded from GoPro: {file_name}")
                return download_resp.content
        except Exception as e:
            logger.warning(f"Failed to stop recording / download video from GoPro: {e}")

        return None

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def device(self) -> Optional[GoProDevice]:
        return self._device


# Singleton instance
gopro_controller = _GoProController()
