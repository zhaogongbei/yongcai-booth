from pydantic import BaseModel, Field, ConfigDict, HttpUrl
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime


# Base Photo Schema
class PhotoBase(BaseModel):
    original_url: str = Field(..., max_length=500)
    processed_url: Optional[str] = Field(None, max_length=500)
    thumbnail_url: Optional[str] = Field(None, max_length=500)
    file_size: Optional[int] = Field(None, ge=0)
    width: Optional[int] = Field(None, ge=0)
    height: Optional[int] = Field(None, ge=0)
    metadata: Optional[Dict[str, Any]] = Field(None, validation_alias="metadata_")


# Photo Create Schema
class PhotoCreate(BaseModel):
    event_id: UUID
    session_id: Optional[UUID] = None
    original_url: str = Field(..., max_length=500)
    processed_url: Optional[str] = Field(None, max_length=500)
    thumbnail_url: Optional[str] = Field(None, max_length=500)
    file_size: Optional[int] = Field(None, ge=0)
    width: Optional[int] = Field(None, ge=0)
    height: Optional[int] = Field(None, ge=0)
    metadata: Optional[Dict[str, Any]] = None


# Photo Update Schema
class PhotoUpdate(BaseModel):
    processed_url: Optional[str] = Field(None, max_length=500)
    thumbnail_url: Optional[str] = Field(None, max_length=500)
    metadata: Optional[Dict[str, Any]] = None


# Photo Response Schema
class PhotoResponse(PhotoBase):
    id: UUID
    event_id: UUID
    session_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# Photo Upload Request Schema
class PhotoUploadRequest(BaseModel):
    event_id: UUID
    session_id: Optional[UUID] = None
    filename: str
    content_type: str = "image/jpeg"


# Photo Upload URL Response
class PhotoUploadResponse(BaseModel):
    upload_url: str
    photo_id: UUID
    expires_in: int = 3600


# Photo Session Base Schema
class PhotoSessionBase(BaseModel):
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)


# Photo Session Create Schema
class PhotoSessionCreate(PhotoSessionBase):
    event_id: UUID


# Photo Session Update Schema
class PhotoSessionUpdate(BaseModel):
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    completed_at: Optional[datetime] = None


# Photo Session Response Schema
class PhotoSessionResponse(PhotoSessionBase):
    id: UUID
    event_id: UUID
    started_at: datetime
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# Photo Session with Photos Response
class PhotoSessionWithPhotos(PhotoSessionResponse):
    photos: list[PhotoResponse] = []


# Photo List Query Schema
class PhotoListQuery(BaseModel):
    event_id: Optional[UUID] = None
    session_id: Optional[UUID] = None
    skip: int = Field(0, ge=0)
    limit: int = Field(100, ge=1, le=100)
