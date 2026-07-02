from datetime import datetime
from uuid import UUID
from typing import Optional
from app.schemas.base import BaseSchema


class DisclaimerBase(BaseSchema):
    enabled: bool = True
    title: str = "免责声明"
    text: str = ""
    require_signature: bool = False


class DisclaimerCreate(DisclaimerBase):
    event_id: UUID


class DisclaimerUpdate(DisclaimerBase):
    pass


class DisclaimerResponse(DisclaimerBase):
    id: UUID
    event_id: UUID
    created_at: datetime
    updated_at: datetime


class DisclaimerAcceptanceCreate(BaseSchema):
    event_id: UUID
    session_id: UUID


class DisclaimerAcceptanceResponse(BaseSchema):
    id: UUID
    event_id: UUID
    session_id: UUID
    created_at: datetime