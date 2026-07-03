from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Team, TeamMember, UserRole
from app.repositories.team_repository import TeamRepository
from app.schemas.team import TeamCreate, TeamInvitation, TeamUpdate
from app.services.base_service import BaseService, BusinessRuleError, ValidationError


class TeamService(BaseService[Team, TeamCreate, TeamUpdate]):
    """
    Service for team business logic.

    Provides team management operations including:
    - Team CRUD operations
    - Member management (add, remove, update roles)
    - Permission checks
    - Slug generation and validation
    """

    def __init__(self, db: AsyncSession):
        repository = TeamRepository(db)
        super().__init__(repository, db)
        self._current_user_id: Optional[UUID] = None

    def set_current_user(self, user_id: UUID) -> None:
        """Set current user for permission checks."""
        self._current_user_id = user_id

    async def create_team(self, team_in: TeamCreate, creator_id: UUID) -> Team:
        """Create a team using the legacy service API."""
        self.set_current_user(creator_id)

        try:
            return await self.create(team_in)
        except (BusinessRuleError, ValidationError) as exc:
            raise ValueError(str(exc)) from exc

    async def update_team(self, team_id: UUID, team_in: TeamUpdate) -> Optional[Team]:
        """Update a team using the legacy service API."""
        try:
            return await self.update(team_id, team_in)
        except (BusinessRuleError, ValidationError) as exc:
            raise ValueError(str(exc)) from exc

    async def delete_team(self, team_id: UUID) -> bool:
        """Delete a team using the legacy service API."""
        return await self.delete(team_id)

    # Override BaseService hooks

    async def validate_create(self, obj_in: TeamCreate) -> None:
        """Validate business rules before team creation."""
        # Generate slug if not provided
        slug = obj_in.slug
        if not slug:
            slug = obj_in.name.lower().replace(" ", "-").replace("_", "-")
            slug = "".join(c for c in slug if c.isalnum() or c == "-")
            obj_in.slug = slug

        # Check slug uniqueness
        if await self.repository.slug_exists(slug):
            raise BusinessRuleError(f"Slug '{slug}' is already taken")

    async def before_create(self, obj_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Transform data before team creation."""
        # Generate slug if still not set
        if not obj_dict.get("slug"):
            slug = obj_dict["name"].lower().replace(" ", "-").replace("_", "-")
            obj_dict["slug"] = "".join(c for c in slug if c.isalnum() or c == "-")

        return obj_dict

    async def after_create(self, created: Team) -> None:
        """Handle side effects after team creation."""
        # Add creator as owner
        if self._current_user_id:
            await self.repository.add_member(created.id, self._current_user_id, UserRole.OWNER)

    # Team-specific methods

    async def get_team_with_members(self, team_id: UUID) -> Optional[Team]:
        """Get team with all members loaded."""
        return await self.repository.get_with_members(team_id)

    async def get_team(self, team_id: UUID) -> Optional[Team]:
        """Get a team by ID using the legacy service API."""
        return await self.get(team_id)

    async def get_user_teams(self, user_id: UUID) -> List[Team]:
        """Get all teams for a user."""
        return await self.repository.get_user_teams(user_id)

    # Member management

    async def add_member(
        self, team_id: UUID, user_id: UUID, role: UserRole = UserRole.MEMBER
    ) -> TeamMember:
        """
        Add a member to team.

        Args:
            team_id: Team unique identifier
            user_id: User to add
            role: Role to assign (default: MEMBER)

        Returns:
            Created TeamMember

        Raises:
            BusinessRuleError: If user is already a member
        """
        if await self.repository.is_member(team_id, user_id):
            raise BusinessRuleError("User is already a team member")

        return await self.repository.add_member(team_id, user_id, role)

    async def remove_member(self, team_id: UUID, user_id: UUID, requester_id: UUID) -> bool:
        """
        Remove a member from team.

        Args:
            team_id: Team unique identifier
            user_id: User to remove
            requester_id: User requesting the removal

        Returns:
            True if removed successfully

        Raises:
            BusinessRuleError: If requester doesn't have permission
        """
        # Check if requester has permission
        requester_role = await self.repository.get_member_role(team_id, requester_id)
        if requester_role not in [UserRole.OWNER, UserRole.ADMIN]:
            raise BusinessRuleError("Only owners and admins can remove members")

        # Don't allow removing yourself if you're the last owner
        if requester_id == user_id:
            member_role = await self.repository.get_member_role(team_id, user_id)
            if member_role == UserRole.OWNER:
                owner_count = await self.repository.count_owners(team_id)
                if owner_count <= 1:
                    raise BusinessRuleError("A team must have at least one owner")

        return await self.repository.remove_member(team_id, user_id)

    async def update_member_role(
        self, team_id: UUID, user_id: UUID, role: UserRole, requester_id: UUID
    ) -> Optional[TeamMember]:
        """
        Update member role.

        Args:
            team_id: Team unique identifier
            user_id: User whose role to update
            role: New role to assign
            requester_id: User requesting the update

        Returns:
            Updated TeamMember if successful

        Raises:
            BusinessRuleError: If requester doesn't have permission
        """
        # Check if requester has permission (only owners can change roles)
        requester_role = await self.repository.get_member_role(team_id, requester_id)
        if requester_role != UserRole.OWNER:
            raise BusinessRuleError("Only owners can update member roles")

        current_role = await self.repository.get_member_role(team_id, user_id)
        if current_role == UserRole.OWNER and role != UserRole.OWNER:
            owner_count = await self.repository.count_owners(team_id)
            if owner_count <= 1:
                raise BusinessRuleError("A team must have at least one owner")

        return await self.repository.update_member_role(team_id, user_id, role)

    # Permission helpers

    async def is_member(self, team_id: UUID, user_id: UUID) -> bool:
        """Check if user is a team member."""
        return await self.repository.is_member(team_id, user_id)

    async def get_member_role(self, team_id: UUID, user_id: UUID) -> Optional[UserRole]:
        """Get user's role in team."""
        return await self.repository.get_member_role(team_id, user_id)

    async def has_permission(self, team_id: UUID, user_id: UUID, required_role: UserRole) -> bool:
        """
        Check if user has required permission level.

        Role hierarchy: OWNER > ADMIN > MEMBER

        Args:
            team_id: Team unique identifier
            user_id: User to check
            required_role: Minimum required role

        Returns:
            True if user has required permission level
        """
        role = await self.repository.get_member_role(team_id, user_id)
        if not role:
            return False

        role_hierarchy = {
            UserRole.OWNER: 3,
            UserRole.ADMIN: 2,
            UserRole.MEMBER: 1,
        }

        return role_hierarchy.get(role, 0) >= role_hierarchy.get(required_role, 0)
