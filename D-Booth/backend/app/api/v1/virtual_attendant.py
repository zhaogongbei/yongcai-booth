from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import check_team_member, get_current_active_user, get_db
from app.models.models import Event, User
from app.services.tts_service import TTSService
from app.services.virtual_attendant_service import PlaylistItem, PlayTiming, VirtualAttendantService

router = APIRouter()


class UpdatePlaylistRequest(BaseModel):
    """更新播放列表请求"""

    items: List[PlaylistItem] = Field(..., description="播放列表项")


class PreviewTTSRequest(BaseModel):
    """预览TTS请求"""

    text: str = Field(..., description="要合成的文本")
    language: str = Field(default="zh-CN", description="语言")
    voice: str = Field(default="female", description="语音类型")


async def _ensure_event_access(db: AsyncSession, event_id: UUID, current_user: User) -> None:
    result = await db.execute(select(Event.team_id).where(Event.id == event_id))
    team_id = result.scalar_one_or_none()
    if team_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    await check_team_member(team_id, current_user, db)


@router.get("/playlist/{event_id}", response_model=List[PlaylistItem])
async def get_playlist(event_id: str):
    """获取事件的播放列表"""
    try:
        playlist = VirtualAttendantService.get_playlist(event_id)
        return playlist
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="获取播放列表失败"
        )


@router.put("/playlist/{event_id}", response_model=List[PlaylistItem])
async def update_playlist(
    event_id: UUID,
    request: UpdatePlaylistRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """更新事件的播放列表"""
    try:
        await _ensure_event_access(db, event_id, current_user)
        playlist = VirtualAttendantService.update_playlist(str(event_id), request.items)
        return playlist
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="更新播放列表失败"
        )


@router.post("/preview", response_class=Response)
async def preview_tts(
    request: PreviewTTSRequest,
    current_user: User = Depends(get_current_active_user),
):
    """预览TTS语音，返回MP3音频"""
    try:
        audio_data = await TTSService.synthesize(
            text=request.text, language=request.language, voice=request.voice
        )

        if not audio_data:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="TTS服务当前不可用"
            )

        return Response(
            content=audio_data,
            media_type="audio/mpeg",
            headers={"Content-Disposition": f"attachment; filename=preview.mp3"},
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="TTS合成失败")


@router.get("/tts/{timing}", response_class=Response)
async def get_tts_by_timing(
    timing: str, event_id: str, language: str = "zh-CN", voice: str = "female"
):
    """获取指定时机的已合成TTS音频"""
    try:
        # 验证timing参数
        try:
            play_timing = PlayTiming(timing)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=f"无效的播放时机: {timing}"
            )

        # 获取播放列表
        playlist = VirtualAttendantService.get_playlist(event_id)

        # 查找对应的播放项
        item = next((i for i in playlist if i.timing == play_timing), None)
        if not item or not item.enabled:
            # 如果没有找到或未启用，返回空音频
            return Response(content=b"", media_type="audio/mpeg")

        # 合成语音
        audio_data = await TTSService.synthesize(
            text=item.text, language=item.language, voice=item.voice
        )

        return Response(
            content=audio_data,
            media_type="audio/mpeg",
            headers={"Cache-Control": "public, max-age=86400"},  # 缓存1天
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="获取TTS失败")
