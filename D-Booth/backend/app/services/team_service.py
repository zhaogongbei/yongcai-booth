from typing import Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.team_repository import TeamRepository
from app.schemas.team import TeamCreate, TeamUpdate, TeamInvitation
from app.models.models import Team, TeamMember, UserRole


class TeamService:
    """Service for team business logic"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = TeamRepository(db)
    
    async def get_team(self, team_id: UUID) -> Optional[Team]:
        """Get team by ID"""
        return await self.repository.get(team_id)
    
    async def get_team_with_members(self, team_id: UUID) -> Optional[Team]:
        """Get team with all members"""
        return await self.repository.get_with_members(team_id)
    
    async def get_user_teams(self, user_id: UUID) -> List[Team]:
        """Get all teams for a user"""
        return await self.repository.get_user_teams(user_id)
    
    async def create_team(
        self,
        team_in: TeamCreate,
        creator_id: UUID
    ) -> Team:
        """Create a new team"""
        # Generate slug if not provided
        slug = team_in.slug
        if not slug:
            slug = team_in.name.lower().replace(" ", "-").replace("_", "-")
            # Remove special characters
            slug = "".join(c for c in slug if c.isalnum() or c == "-")
        
        # Check slug uniqueness
        if await self.repository.slug_exists(slug):
            raise ValueError(f"Slug '{slug}' is already taken")
        
        # Create team
        team_data = {
            "name": team_in.name,
            "slug": slug,
            "description": team_in.description,
        }
        
        team = await self.repository.create(team_data)
        
        # Add creator as owner
        await self.repository.add_member(team.id, creator_id, UserRole.OWNER)
        
        return team
    
    async def update_team(
        self,
        team_id: UUID,
        team_in: TeamUpdate
    ) -> Optional[Team]:
        """Update team information"""
        update_data = team_in.model_dump(exclude_unset=True)
        return await self.repository.update(team_id, update_data)
    
    async def delete_team(self, team_id: UUID) -> bool:
        """Delete a team"""
        return await self.repository.delete(team_id)
    
    async def add_member(
        self,
        team_id: UUID,
        user_id: UUID,
        role: UserRole = UserRole.MEMBER
    ) -> TeamMember:
        """Add a member to team"""
        # Check if already a member
        if await self.repository.is_member(team_id, user_id):
            raise ValueError("User is already a team member")
        
        return await self.repository.add_member(team_id, user_id, role)
    
    async def remove_member(
        self,
        team_id: UUID,
        user_id: UUID,
        requester_id: UUID
    ) -> bool:
        """Remove a member from team"""
        # Check if requester has permission
        requester_role = await self.repository.get_member_role(team_id, requester_id)
        if requester_role not in [UserRole.OWNER, UserRole.ADMIN]:
            raise PermissionError("Only owners and admins can remove members")
        
        # Don't allow removing yourself if you're the last owner
        if requester_id == user_id:
            member_role = await self.repository.get_member_role(team_id, user_id)
            if member_role == UserRole.OWNER:
                # TODO: Check if there are other owners
                pass
        
        return await self.repository.remove_member(team_id, user_id)
    
    async def update_member_role(
        self,
        team_id: UUID,
        user_id: UUID,
        role: UserRole,
        requester_id: UUID
    ) -> Optional[TeamMember]:
        """Update member role"""
        # Check if requester has permission
        requester_role = await self.repository.get_member_role(team_id, requester_id)
        if requester_role != UserRole.OWNER:
            raise PermissionError("Only owners can update member roles")
        
        return await self.repository.update_member_role(team_id, user_id, role)
    
    async def is_member(self, team_id: UUID, user_id: UUID) -> bool:
        """Check if user is a team member"""
        return await self.repository.is_member(team_id, user_id)
    
    async def get_member_role(
        self,
        team_id: UUID,
        user_id: UUID
    ) -> Optional[UserRole]:
        """Get user's role in team"""
        return await self.repository.get_member_role(team_id, user_id)
    
    async def has_permission(
        self,
        team_id: UUID,
        user_id: UUID,
        required_role: UserRole
    ) -> bool:
        """Check if user has required permission level"""
        role = await self.repository.get_member_role(team_id, user_id)
        if not role:
            return False
        
        # Role hierarchy: OWNER > ADMIN > MEMBER
        role_hierarchy = {
            UserRole.OWNER: 3,
            UserRole.ADMIN: 2,
            UserRole.MEMBER: 1,
        }
        
        return role_hierarchy.get(role, 0) >= role_hierarchy.get(required_role, 0)
