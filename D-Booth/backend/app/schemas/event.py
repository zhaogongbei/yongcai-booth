from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.models import EventStatus


# Base Event Schema
class EventBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    event_type: Optional[str] = Field(None, max_length=50)
    start_date: datetime
    end_date: datetime
    venue_name: Optional[str] = Field(None, max_length=255)
    venue_address: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None


# Event Create Schema
class EventCreate(EventBase):
    team_id: UUID


# Event Update Schema
class EventUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    event_type: Optional[str] = Field(None, max_length=50)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    venue_name: Optional[str] = Field(None, max_length=255)
    venue_address: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None
    status: Optional[EventStatus] = None


# Event Response Schema
class EventResponse(EventBase):
    id: UUID
    team_id: UUID
    creator_id: UUID
    status: EventStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Event Status Update Schema
class EventStatusUpdate(BaseModel):
    status: EventStatus


# Event Statistics Schema
class EventStatistics(BaseModel):
    event_id: UUID
    total_sessions: int = 0
    total_photos: int = 0
    total_prints: int = 0
    total_shares: int = 0
    active_sessions: int = 0


# Event List Query Schema
class EventListQuery(BaseModel):
    team_id: Optional[UUID] = None
    status: Optional[EventStatus] = None
    start_date_from: Optional[datetime] = None
    start_date_to: Optional[datetime] = None
    skip: int = Field(0, ge=0)
    limit: int = Field(100, ge=1, le=100)
