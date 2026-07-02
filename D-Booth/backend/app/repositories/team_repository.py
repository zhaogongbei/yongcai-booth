from typing import Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models.models import Team, TeamMember, UserRole
from app.repositories.base import BaseRepository


class TeamRepository(BaseRepository[Team]):
    """Repository for Team model"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(Team, db)
    
    async def get_by_slug(self, slug: str) -> Optional[Team]:
        """Get team by slug"""
        result = await self.db.execute(
            select(Team).where(Team.slug == slug)
        )
        return result.scalar_one_or_none()
    
    async def slug_exists(self, slug: str) -> bool:
        """Check if slug already exists"""
        result = await self.db.execute(
            select(Team.id).where(Team.slug == slug)
        )
        return result.scalar_one_or_none() is not None
    
    async def get_with_members(self, team_id: UUID) -> Optional[Team]:
        """Get team with all members"""
        result = await self.db.execute(
            select(Team)
            .where(Team.id == team_id)
            .options(selectinload(Team.members))
        )
        return result.scalar_one_or_none()
    
    async def get_user_teams(self, user_id: UUID) -> List[Team]:
        """Get all teams for a user"""
        result = await self.db.execute(
            select(Team)
            .join(TeamMember)
            .where(TeamMember.user_id == user_id)
        )
        return list(result.scalars().all())
    
    async def add_member(
        self,
        team_id: UUID,
        user_id: UUID,
        role: UserRole = UserRole.MEMBER
    ) -> TeamMember:
        """Add a member to team"""
        member = TeamMember(
            team_id=team_id,
            user_id=user_id,
            role=role
        )
        self.db.add(member)
        await self.db.commit()
        await self.db.refresh(member)
        return member
    
    async def remove_member(self, team_id: UUID, user_id: UUID) -> bool:
        """Remove a member from team"""
        from sqlalchemy import delete
        stmt = delete(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == user_id
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount > 0
    
    async def update_member_role(
        self,
        team_id: UUID,
        user_id: UUID,
        role: UserRole
    ) -> Optional[TeamMember]:
        """Update member role"""
        stmt = select(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == user_id
        )
        result = await self.db.execute(stmt)
        member = result.scalar_one_or_none()
        
        if member:
            member.role = role
            await self.db.commit()
            await self.db.refresh(member)
            return member
        return None
    
    async def is_member(self, team_id: UUID, user_id: UUID) -> bool:
        """Check if user is a team member"""
        result = await self.db.execute(
            select(TeamMember.id).where(
                TeamMember.team_id == team_id,
                TeamMember.user_id == user_id
            )
        )
        return result.scalar_one_or_none() is not None
    
    async def get_member_role(
        self,
        team_id: UUID,
        user_id: UUID
    ) -> Optional[UserRole]:
        """Get user's role in team"""
        result = await self.db.execute(
            select(TeamMember.role).where(
                TeamMember.team_id == team_id,
                TeamMember.user_id == user_id
            )
        )
        return result.scalar_one_or_none()
