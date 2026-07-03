from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# Base Share Schema
class ShareBase(BaseModel):
    channel: str = Field(..., max_length=50)  # "email", "sms", "qr", "link", "social"
    recipient: Optional[str] = Field(None, max_length=255)
    expires_at: Optional[datetime] = None


# Share Create Schema
class ShareCreate(ShareBase):
    photo_id: UUID


# Share Update Schema
class ShareUpdate(BaseModel):
    view_count: Optional[int] = Field(None, ge=0)


# Share Response Schema
class ShareResponse(ShareBase):
    id: UUID
    photo_id: UUID
    short_code: str
    full_url: str
    view_count: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Share List Query Schema
class ShareListQuery(BaseModel):
    photo_id: Optional[UUID] = None
    channel: Optional[str] = None
    skip: int = Field(0, ge=0)
    limit: int = Field(100, ge=1, le=100)


# Share by Code Response (public)
class SharePublicResponse(BaseModel):
    photo_url: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    is_expired: bool = False


# Share Statistics Schema
class ShareStatistics(BaseModel):
    total_shares: int = 0
    by_channel: dict[str, int] = {}
    total_views: int = 0
