from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# Base AI Task Schema
class AITaskBase(BaseModel):
    workflow: str = Field(..., max_length=50)  # "background_removal", "ai_headshot", etc.
    provider: str = Field(..., max_length=50)  # "openai", "stability", "replicate", etc.
    prompt: str = Field(..., min_length=1, max_length=1200)
    parameters: Optional[Dict[str, Any]] = None


# AI Task Create Schema
class AITaskCreate(AITaskBase):
    team_id: UUID


# AI Task Update Schema
class AITaskUpdate(BaseModel):
    status: Optional[str] = Field(None, max_length=50)
    progress: Optional[Decimal] = Field(None, ge=0, le=100)
    result_url: Optional[str] = Field(None, max_length=500)
    error_message: Optional[str] = None
    actual_cost: Optional[Decimal] = Field(None, ge=0)


# AI Task Response Schema
class AITaskResponse(AITaskBase):
    id: UUID
    team_id: UUID
    status: str
    progress: Decimal
    result_url: Optional[str] = None
    error_message: Optional[str] = None
    estimated_cost: Optional[Decimal] = None
    actual_cost: Optional[Decimal] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# AI Task List Query Schema
class AITaskListQuery(BaseModel):
    team_id: Optional[UUID] = None
    workflow: Optional[str] = None
    provider: Optional[str] = None
    status: Optional[str] = None
    skip: int = Field(0, ge=0)
    limit: int = Field(100, ge=1, le=100)


# AI Task Statistics Schema
class AITaskStatistics(BaseModel):
    total_tasks: int = 0
    by_workflow: Dict[str, int] = {}
    by_status: Dict[str, int] = {}
    total_cost: Decimal = Decimal(0)


# AI Workflow Schemas
class BackgroundRemovalRequest(BaseModel):
    photo_url: str
    team_id: UUID


class AIHeadshotRequest(BaseModel):
    photo_url: str
    style: str = "professional"  # "professional", "casual", "creative"
    team_id: UUID


class AIPosterRequest(BaseModel):
    photo_url: str
    template_id: Optional[UUID] = None
    prompt: str
    team_id: UUID


class AISceneGenerationRequest(BaseModel):
    prompt: str
    style: str = "realistic"
    width: int = Field(1024, ge=512, le=2048)
    height: int = Field(1024, ge=512, le=2048)
    team_id: UUID
