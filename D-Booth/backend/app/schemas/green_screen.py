"""
Green Screen Processing Schemas
"""

from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl


class GreenScreenBackground(BaseModel):
    """Background image with optional overlay"""

    id: UUID
    name: str
    background_url: str
    overlay_url: Optional[str] = None
    order: int
    created_at: datetime

    model_config = {"from_attributes": True}


class GreenScreenSettingsBase(BaseModel):
    """Base green screen settings schema"""

    enabled: bool = False
    mode: Literal["chroma_key", "ai_removal", "auto"] = "auto"
    color_to_remove: str = "#00FF00"  # Hex color
    sensitivity: int = Field(default=50, ge=0, le=100)
    smoothness: int = Field(default=30, ge=0, le=100)
    use_flash: bool = False
    background_mode: Literal["rotate", "manual"] = "rotate"
    output_size: Literal["template", "1800x1200", "max"] = "template"
    current_background_index: int = 0


class GreenScreenSettingsCreate(GreenScreenSettingsBase):
    """Create green screen settings"""

    event_id: UUID


class GreenScreenSettingsUpdate(GreenScreenSettingsBase):
    """Update green screen settings"""

    pass


class GreenScreenSettingsResponse(GreenScreenSettingsBase):
    """Green screen settings response"""

    id: UUID
    event_id: UUID
    backgrounds: List[GreenScreenBackground] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class GreenScreenProcessRequest(BaseModel):
    """Request schema for green screen processing"""

    settings: GreenScreenSettingsBase
    background_id: Optional[UUID] = None
    apply_to_all: bool = False


class BackgroundAnalysisResult(BaseModel):
    """Result of background complexity analysis"""

    complexity_score: float  # 0 = complex, 1 = simple solid color
    recommended_mode: Literal["chroma_key", "ai_removal"]
    is_green_background: bool
    suggested_sensitivity: int
    suggestions: List[str]
