from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.models import PrintJobStatus


# Base Print Job Schema
class PrintJobBase(BaseModel):
    printer_name: Optional[str] = Field(None, max_length=255)
    copies: int = Field(1, ge=1, le=10)
    template_id: Optional[UUID] = None


# Print Job Create Schema
class PrintJobCreate(PrintJobBase):
    photo_id: UUID


# Print Job Update Schema
class PrintJobUpdate(BaseModel):
    status: Optional[PrintJobStatus] = None
    error_message: Optional[str] = None
    printed_at: Optional[datetime] = None


# Print Job Response Schema
class PrintJobResponse(PrintJobBase):
    id: UUID
    photo_id: UUID
    status: PrintJobStatus
    error_message: Optional[str] = None
    printed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Print Job List Query Schema
class PrintJobListQuery(BaseModel):
    photo_id: Optional[UUID] = None
    status: Optional[PrintJobStatus] = None
    skip: int = Field(0, ge=0)
    limit: int = Field(100, ge=1, le=100)


# Print Job Statistics Schema
class PrintJobStatistics(BaseModel):
    total: int = 0
    pending: int = 0
    queued: int = 0
    printing: int = 0
    completed: int = 0
    failed: int = 0
    cancelled: int = 0


# Batch Print Request
class BatchPrintRequest(BaseModel):
    photo_ids: list[UUID] = Field(..., min_length=1, max_length=50)
    printer_name: Optional[str] = Field(None, max_length=255)
    copies: int = Field(1, ge=1, le=10)


# Batch Print Response
class BatchPrintResponse(BaseModel):
    job_ids: list[UUID]
    total_jobs: int
