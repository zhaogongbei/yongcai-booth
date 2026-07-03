from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user, get_db
from app.models.models import User
from app.schemas.team import (
    TeamCreate,
    TeamMemberCreate,
    TeamMemberResponse,
    TeamMemberUpdate,
    TeamResponse,
    TeamUpdate,
    TeamWithMembers,
)
from app.services.base_service import BusinessRuleError
from app.services.team_service import TeamService

router = APIRouter()


def _team_business_rule_status(exc: BusinessRuleError) -> int:
    if str(exc).startswith("Only "):
        return status.HTTP_403_FORBIDDEN
    return status.HTTP_400_BAD_REQUEST


@router.get("", response_model=List[TeamResponse])
async def get_my_teams(
    current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db)
):
    """Get all teams for current user"""
    team_service = TeamService(db)
    teams = await team_service.get_user_teams(current_user.id)
    return teams


@router.post("", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
async def create_team(
    team_in: TeamCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new team"""
    team_service = TeamService(db)

    try:
        team = await team_service.create_team(team_in, current_user.id)
        return team
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{team_id}", response_model=TeamWithMembers)
async def get_team(
    team_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get team by ID"""
    team_service = TeamService(db)

    team = await team_service.get_team_with_members(team_id)
    if not team:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")

    # Check if user is a member
    if not await team_service.is_member(team_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="You are not a member of this team"
        )

    return team


@router.put("/{team_id}", response_model=TeamResponse)
async def update_team(
    team_id: UUID,
    team_in: TeamUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update team"""
    from app.models.models import UserRole

    team_service = TeamService(db)

    # Check if user has permission
    if not await team_service.has_permission(team_id, current_user.id, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin permission required"
        )

    team = await team_service.update_team(team_id, team_in)
    if not team:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")

    return team


@router.delete("/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_team(
    team_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete team"""
    from app.models.models import UserRole

    team_service = TeamService(db)

    # Check if user is owner
    if not await team_service.has_permission(team_id, current_user.id, UserRole.OWNER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Owner permission required"
        )

    success = await team_service.delete_team(team_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")


@router.post(
    "/{team_id}/members", response_model=TeamMemberResponse, status_code=status.HTTP_201_CREATED
)
async def add_team_member(
    team_id: UUID,
    member_in: TeamMemberCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a member to team"""
    from app.models.models import UserRole

    team_service = TeamService(db)

    # Check if user has permission
    if not await team_service.has_permission(team_id, current_user.id, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin permission required"
        )

    try:
        member = await team_service.add_member(team_id, member_in.user_id, member_in.role)
        return member
    except BusinessRuleError as e:
        raise HTTPException(status_code=_team_business_rule_status(e), detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{team_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_team_member(
    team_id: UUID,
    user_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a member from team"""
    team_service = TeamService(db)

    try:
        await team_service.remove_member(team_id, user_id, current_user.id)
    except BusinessRuleError as e:
        raise HTTPException(status_code=_team_business_rule_status(e), detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.patch("/{team_id}/members/{user_id}", response_model=TeamMemberResponse)
async def update_team_member_role(
    team_id: UUID,
    user_id: UUID,
    member_in: TeamMemberUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update member role"""
    team_service = TeamService(db)

    try:
        member = await team_service.update_member_role(
            team_id, user_id, member_in.role, current_user.id
        )
        if not member:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
        return member
    except BusinessRuleError as e:
        raise HTTPException(status_code=_team_business_rule_status(e), detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
