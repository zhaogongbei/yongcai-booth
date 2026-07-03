from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.base import BaseSchema


class SurveyQuestionSchema(BaseSchema):
    id: str
    type: str = Field(description="问题类型: text_short, text_long, multiple_choice, rating")
    text: str
    required: bool = True
    options: List[str] = []
    order: int = 0


class SurveyBase(BaseSchema):
    enabled: bool = True
    title: str = "问卷调查"
    questions: List[SurveyQuestionSchema] = []


class SurveyCreate(SurveyBase):
    event_id: UUID


class SurveyUpdate(SurveyBase):
    pass


class SurveyResponseSchema(SurveyBase):
    id: UUID
    event_id: UUID
    created_at: datetime
    updated_at: datetime


class SurveyAnswerSubmit(BaseSchema):
    event_id: UUID
    session_id: UUID
    answers: dict


class SurveyAnswerResponse(BaseSchema):
    id: UUID
    event_id: UUID
    session_id: UUID
    answers: dict
    created_at: datetime
    updated_at: datetime
