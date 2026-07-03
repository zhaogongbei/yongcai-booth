from datetime import datetime
from typing import Optional
from uuid import UUID

from app.schemas.base import BaseSchema


class SignatureCreate(BaseSchema):
    session_id: UUID


class SignatureResponse(BaseSchema):
    id: UUID
    session_id: UUID
    signature_url: str
    created_at: datetime
    updated_at: datetime
