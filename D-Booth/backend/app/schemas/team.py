from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from app.models.models import UserRole


# Base Team Schema
class TeamBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None


# Team Create Schema
class TeamCreate(TeamBase):
    slug: Optional[str] = Field(None, max_length=255, pattern="^[a-z0-9-]+$")


# Team Update Schema
class TeamUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None


# Team Response Schema
class TeamResponse(TeamBase):
    id: UUID
    slug: str
    subscription_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# Team Member Base Schema
class TeamMemberBase(BaseModel):
    user_id: UUID
    role: UserRole = UserRole.MEMBER


# Team Member Create Schema
class TeamMemberCreate(TeamMemberBase):
    pass


# Team Member Update Schema
class TeamMemberUpdate(BaseModel):
    role: Optional[UserRole] = None


# Team Member Response Schema
class TeamMemberResponse(BaseModel):
    id: UUID
    team_id: UUID
    user_id: UUID
    role: UserRole
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# Team with Members Response
class TeamWithMembers(TeamResponse):
    members: List[TeamMemberResponse] = []


# Team Invitation Schema
class TeamInvitation(BaseModel):
    email: str
    role: UserRole = UserRole.MEMBER
