import logging
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class PlayTiming(str, Enum):
    """播放时机枚举"""
    attract_screen = "attract_screen"
    before_countdown = "before_countdown"
    after_capture = "after_capture"
    during_processing = "during_processing"
    after_processing = "after_processing"
    session_end = "session_end"


# 中文提示文本模板
DEFAULT_TEXTS_CN = {
    PlayTiming.attract_screen: "欢迎光临！点击屏幕开始拍照吧！",
    PlayTiming.before_countdown: "准备拍照！请看镜头，微笑！",
    PlayTiming.after_capture: "拍得真棒！点击下一步继续。",
    PlayTiming.during_processing: "照片处理中，请稍候...",
    PlayTiming.after_processing: "照片处理完成！请查看您的照片。",
    PlayTiming.session_end: "感谢您的参与！请取走您的照片。",
}

# 英文提示文本模板
DEFAULT_TEXTS_EN = {
    PlayTiming.attract_screen: "Welcome! Tap the screen to start taking photos!",
    PlayTiming.before_countdown: "Get ready! Look at the camera and smile!",
    PlayTiming.after_capture: "Great shot! Tap Next to continue.",
    PlayTiming.during_processing: "Processing your photo, please wait...",
    PlayTiming.after_processing: "Photo processing complete! Please check your photo.",
    PlayTiming.session_end: "Thank you for participating! Please take your photo.",
}


class PlaylistItem(BaseModel):
    """播放列表项"""
    timing: PlayTiming = Field(..., description="播放时机")
    enabled: bool = Field(default=True, description="是否启用")
    text: str = Field(..., description="提示文本")
    language: str = Field(default="zh-CN", description="语言")
    voice: str = Field(default="female", description="语音类型")


class Playlist(BaseModel):
    """播放列表"""
    event_id: str
    items: List[PlaylistItem] = Field(default_factory=list)


# 内存存储播放列表配置
_playlist_storage: dict[str, List[PlaylistItem]] = {}


class VirtualAttendantService:
    """虚拟助手语音引导服务"""

    @staticmethod
    def _get_default_playlist(event_id: str) -> List[PlaylistItem]:
        """获取默认播放列表（中文女声）"""
        items = []
        for timing in PlayTiming:
            items.append(PlaylistItem(
                timing=timing,
                enabled=True,
                text=DEFAULT_TEXTS_CN[timing],
                language="zh-CN",
                voice="female"
            ))
        return items

    @staticmethod
    def get_playlist(event_id: str) -> List[PlaylistItem]:
        """获取播放列表，如果没有配置则返回默认值"""
        if event_id not in _playlist_storage:
            return VirtualAttendantService._get_default_playlist(event_id)
        return _playlist_storage[event_id]

    @staticmethod
    def update_playlist(event_id: str, items: List[PlaylistItem]) -> List[PlaylistItem]:
        """更新播放列表"""
        _playlist_storage[event_id] = items
        logger.info(f"播放列表已更新: event_id={event_id}, items_count={len(items)}")
        return items
