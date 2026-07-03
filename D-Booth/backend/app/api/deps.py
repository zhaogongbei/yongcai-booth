from typing import Generator, Optional
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_maker
from app.core.security import verify_token
from app.models.models import Team, User
from app.services.team_service import TeamService
from app.services.user_service import UserService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


# Database dependency (imported from core.database to avoid duplication)
from app.core.database import get_db


# Current user dependency
async def get_current_user(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
) -> User:
    """Get current authenticated user"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # verify_token validates both signature and type=="access"; a refresh
    # token presented here is rejected.
    user_id = verify_token(token, expected_type="access")
    if user_id is None:
        raise credentials_exception

    user_service = UserService(db)
    user = await user_service.get_user(user_id)

    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive"
        )

    return user


# Active user dependency
async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current active user"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive"
        )
    return current_user


# Team membership check
async def check_team_member(
    team_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Check if current user is a team member"""
    team_service = TeamService(db)

    if not await team_service.is_member(team_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="You are not a member of this team"
        )

    return current_user


# Team admin check
async def check_team_admin(
    team_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Check if current user is a team admin or owner"""
    from app.models.models import UserRole

    team_service = TeamService(db)

    if not await team_service.has_permission(team_id, current_user.id, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin permission required"
        )

    return current_user


async def get_current_team(
    x_team_id: Optional[UUID] = Header(None, alias="X-Team-Id"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Team:
    """Resolve the active team for routes that operate on team-scoped resources."""
    team_service = TeamService(db)

    if x_team_id:
        if not await team_service.is_member(x_team_id, current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="You are not a member of this team"
            )
        team = await team_service.get_team(x_team_id)
        if not team:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")
        return team

    teams = await team_service.get_user_teams(current_user.id)
    if not teams:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No team found for current user"
        )
    return teams[0]
