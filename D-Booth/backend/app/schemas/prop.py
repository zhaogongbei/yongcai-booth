from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from uuid import UUID
from app.models.models import PropCategory


class PropBase(BaseModel):
    name: str
    category: PropCategory
    tags: Optional[List[str]] = Field(default_factory=list)


class PropCreate(PropBase):
    pass


class PropResponse(PropBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    team_id: Optional[UUID]
    image_url: str
    thumbnail_url: str
    is_public: bool
    is_default: bool


class AppliedPropRequest(BaseModel):
    prop_id: UUID
    x: float = Field(ge=0.0, le=1.0, description="X position ratio (0-1)")
    y: float = Field(ge=0.0, le=1.0, description="Y position ratio (0-1)")
    scale: float = Field(default=1.0, ge=0.1, le=3.0, description="Scale factor (0.1-3.0)")
    rotation: float = Field(default=0.0, ge=0.0, le=360.0, description="Rotation angle (0-360 degrees)")
    flip_h: bool = Field(default=False, description="Horizontal flip")
    flip_v: bool = Field(default=False, description="Vertical flip")
    opacity: float = Field(default=1.0, ge=0.0, le=1.0, description="Opacity (0-1)")


class ApplyPropsRequest(BaseModel):
    image_url: str
    applied_props: List[AppliedPropRequest]
