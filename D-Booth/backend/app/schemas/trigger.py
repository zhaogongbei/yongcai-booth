from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.models import TriggerAction, TriggerType


class TriggerConfigBase(BaseModel):
    event_type: TriggerType
    enabled: bool = False
    action_type: TriggerAction
    target: str = Field(..., min_length=1, max_length=500)
    payload_template: Dict[str, Any] = Field(default_factory=dict)
    timeout: int = Field(10, gt=0)
    retry: int = Field(3, ge=1)


class TriggerConfigCreate(TriggerConfigBase):
    event_id: UUID


class TriggerConfigUpdate(BaseModel):
    event_type: Optional[TriggerType] = None
    enabled: Optional[bool] = None
    action_type: Optional[TriggerAction] = None
    target: Optional[str] = Field(None, min_length=1, max_length=500)
    payload_template: Optional[Dict[str, Any]] = None
    timeout: Optional[int] = Field(None, gt=0)
    retry: Optional[int] = Field(None, ge=1)


class TriggerConfigResponse(TriggerConfigBase):
    id: UUID
    event_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TriggerLogResponse(BaseModel):
    id: UUID
    trigger_id: UUID
    event_id: UUID
    event_type: TriggerType
    success: bool
    response_status: Optional[int] = None
    response_data: Optional[str] = None
    duration_ms: Optional[int] = None
    attempt_count: int = 1
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
