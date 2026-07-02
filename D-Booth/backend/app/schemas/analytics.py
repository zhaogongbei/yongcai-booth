from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime


# Base Analytics Event Schema
class AnalyticsEventBase(BaseModel):
    event_type: str = Field(..., max_length=50)
    properties: Optional[Dict[str, Any]] = None
    user_id: Optional[UUID] = None
    session_id: Optional[str] = Field(None, max_length=255)


# Analytics Event Create Schema
class AnalyticsEventCreate(AnalyticsEventBase):
    team_id: UUID
    event_id: Optional[UUID] = None


# Analytics Event Response Schema
class AnalyticsEventResponse(AnalyticsEventBase):
    id: UUID
    team_id: UUID
    event_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# Analytics Query Schema
class AnalyticsQuery(BaseModel):
    team_id: Optional[UUID] = None
    event_id: Optional[UUID] = None
    event_type: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    skip: int = Field(0, ge=0)
    limit: int = Field(1000, ge=1, le=10000)


# Analytics Summary Schema
class AnalyticsSummary(BaseModel):
    total_events: int = 0
    unique_users: int = 0
    unique_sessions: int = 0
    events_by_type: Dict[str, int] = {}
    date_range: Optional[Dict[str, datetime]] = None


# Event Analytics Schema (for specific event)
class EventAnalytics(BaseModel):
    event_id: UUID
    total_sessions: int = 0
    total_photos: int = 0
    total_prints: int = 0
    total_shares: int = 0
    average_session_duration: Optional[float] = None  # in seconds
    popular_templates: list[Dict[str, Any]] = []
    share_channels: Dict[str, int] = {}
    hourly_activity: Dict[str, int] = {}


# Team Analytics Schema
class TeamAnalytics(BaseModel):
    team_id: UUID
    total_events: int = 0
    active_events: int = 0
    total_photos: int = 0
    total_prints: int = 0
    total_shares: int = 0
    storage_used: int = 0  # in bytes
    ai_tasks_count: int = 0
    ai_tasks_cost: float = 0
