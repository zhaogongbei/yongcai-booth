from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# Base Template Schema
class TemplateBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    size: Optional[str] = Field(None, max_length=50)
    canvas_width: Optional[Decimal] = Field(None, ge=0)
    canvas_height: Optional[Decimal] = Field(None, ge=0)
    layers: Optional[Dict[str, Any]] = None
    thumbnail_url: Optional[str] = Field(None, max_length=500)
    is_public: bool = False


# Template Create Schema
class TemplateCreate(TemplateBase):
    team_id: UUID


# Template Update Schema
class TemplateUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    size: Optional[str] = Field(None, max_length=50)
    canvas_width: Optional[Decimal] = Field(None, ge=0)
    canvas_height: Optional[Decimal] = Field(None, ge=0)
    layers: Optional[Dict[str, Any]] = None
    thumbnail_url: Optional[str] = Field(None, max_length=500)
    is_public: Optional[bool] = None


# Template Response Schema
class TemplateResponse(TemplateBase):
    id: UUID
    team_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Template List Query Schema
class TemplateListQuery(BaseModel):
    team_id: Optional[UUID] = None
    is_public: Optional[bool] = None
    size: Optional[str] = None
    skip: int = Field(0, ge=0)
    limit: int = Field(100, ge=1, le=100)


# Template Layer Schema (for detailed layer structure)
class TemplateLayer(BaseModel):
    id: str
    type: str  # "background", "photo", "text", "sticker", "logo"
    x: float
    y: float
    width: float
    height: float
    rotation: float = 0
    opacity: float = 1.0
    z_index: int = 0
    properties: Optional[Dict[str, Any]] = None


# Template Export Request
class TemplateExportRequest(BaseModel):
    template_id: UUID
    photo_urls: list[str] = []
    format: str = "jpeg"  # "jpeg", "png", "pdf"
    quality: int = Field(95, ge=1, le=100)


# Template Export Response
class TemplateExportResponse(BaseModel):
    export_url: str
    expires_in: int = 3600
