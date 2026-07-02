from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from uuid import UUID
from datetime import datetime
from app.models.models import BoothStatus


class BoothCreate(BaseModel):
    """展位注册请求"""
    team_id: UUID
    name: str = Field(..., min_length=1, max_length=255, description="展位名称，如'主舞台拍照亭'")
    device_id: str = Field(..., min_length=1, max_length=255, description="设备唯一标识")
    version: Optional[str] = Field(None, max_length=50, description="软件版本")
    ip_address: Optional[str] = Field(None, max_length=50, description="设备IP地址")
    os_info: Optional[str] = Field(None, max_length=255, description="操作系统信息")
    current_event_id: Optional[UUID] = Field(None, description="当前关联的活动ID")


class BoothUpdate(BaseModel):
    """展位信息更新请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    status: Optional[BoothStatus] = None
    version: Optional[str] = Field(None, max_length=50)
    ip_address: Optional[str] = Field(None, max_length=50)
    os_info: Optional[str] = Field(None, max_length=255)
    current_event_id: Optional[UUID] = None


class BoothResponse(BaseModel):
    """展位响应"""
    id: UUID
    team_id: UUID
    name: str
    device_id: str
    status: BoothStatus
    version: Optional[str] = None
    last_heartbeat: Optional[datetime] = None
    ip_address: Optional[str] = None
    os_info: Optional[str] = None
    current_event_id: Optional[UUID] = None
    config_hash: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class HeartbeatResponse(BaseModel):
    """心跳响应"""
    booth_id: UUID
    status: BoothStatus
    last_heartbeat: datetime
    message: str = "心跳已接收"


class SyncStateResponse(BaseModel):
    """同步状态响应"""
    booth_id: str
    team_id: str
    templates_hash: str
    settings_hash: str
    props_hash: str
    cloud_hash: str
    booth_config_hash: Optional[str] = None
    need_sync_templates: int = 0
    need_sync_settings: int = 0
    need_sync_props: int = 0
    total_templates: int = 0
    total_events: int = 0
    total_props: int = 0
    is_synced: bool = False


class SyncPushResponse(BaseModel):
    """推送配置响应"""
    booth_id: str
    config_hash: str
    pushed: dict


class SyncPullResponse(BaseModel):
    """拉取配置响应"""
    booth_id: str
    name: str
    status: str
    version: Optional[str] = None
    config_hash: Optional[str] = None
    last_heartbeat: Optional[str] = None
    ip_address: Optional[str] = None
    os_info: Optional[str] = None
    current_event_id: Optional[str] = None


class SyncLogResponse(BaseModel):
    """同步日志响应"""
    team_id: str
    booths: list
    total: int
