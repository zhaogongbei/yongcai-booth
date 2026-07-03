from typing import Optional, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate, UserUpdate, UserResponse
from app.models.models import User
from app.core.password import PasswordValidator
from app.services.base_service import (
    BaseService,
    BusinessRuleError,
    ValidationError,
)


class UserService(BaseService[User, UserCreate, UserUpdate]):
    """
    Service for user business logic.

    Provides user management operations including:
    - User CRUD operations
    - Authentication and password management
    - Email verification
    - Account activation/deactivation
    """

    def __init__(self, db: AsyncSession):
        repository = UserRepository(db)
        super().__init__(repository, db)

    # Override BaseService hooks for business rule validation

    async def validate_create(self, obj_in: UserCreate) -> None:
        """Validate business rules before user creation."""
        # Check if email already exists
        if await self.repository.email_exists(obj_in.email):
            raise BusinessRuleError("Email already registered")

        # Validate password strength
        is_valid, error_msg = PasswordValidator.validate(obj_in.password)
        if not is_valid:
            raise ValidationError(error_msg)

    async def validate_update(self, existing: User, obj_in: UserUpdate) -> None:
        """Validate business rules before user update."""
        update_data = obj_in.model_dump(exclude_unset=True)

        # Check email uniqueness if email is being updated
        if "email" in update_data:
            existing_user = await self.repository.get_by_email(update_data["email"])
            if existing_user and existing_user.id != existing.id:
                raise BusinessRuleError("Email already registered")

    async def before_create(self, obj_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Transform data before user creation."""
        # Hash password
        if "password" in obj_dict:
            obj_dict["hashed_password"] = self._hash_password(obj_dict.pop("password"))

        # Set default values
        obj_dict.setdefault("is_active", True)
        obj_dict.setdefault("is_verified", False)

        return obj_dict

    # User-specific methods

    async def create_user(self, user_in: UserCreate) -> User:
        """Create a user using the legacy service API."""
        try:
            return await self.create(user_in)
        except (BusinessRuleError, ValidationError) as exc:
            raise ValueError(str(exc)) from exc

    async def get_user(self, user_id: UUID) -> Optional[User]:
        """Get a user by ID using the legacy service API."""
        return await self.get(user_id)

    @staticmethod
    def _verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash."""
        return PasswordValidator.verify_password(plain_password, hashed_password)

    @staticmethod
    def _hash_password(password: str) -> str:
        """Hash a password."""
        return PasswordValidator.hash_password(password)

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email address.

        Args:
            email: User's email address

        Returns:
            User instance if found, None otherwise
        """
        return await self.repository.get_by_email(email)

    async def authenticate(self, email: str, password: str) -> Optional[User]:
        """
        Authenticate user with email and password.

        Args:
            email: User's email address
            password: Plain text password

        Returns:
            User instance if authentication successful, None otherwise
        """
        user = await self.repository.get_by_email_active(email)
        if not user:
            return None
        if not self._verify_password(password, user.hashed_password):
            return None
        return user

    async def deactivate_user(self, user_id: UUID) -> bool:
        """
        Deactivate a user account.

        Args:
            user_id: User's unique identifier

        Returns:
            True if deactivated, False if not found
        """
        return await self.repository.deactivate(user_id)


    async def verify_email(self, user_id: UUID) -> bool:
        """
        Mark user email as verified.

        Args:
            user_id: User's unique identifier

        Returns:
            True if verified, False if not found
        """
        return await self.repository.verify_email(user_id)

    async def change_password(
        self,
        user_id: UUID,
        current_password: str,
        new_password: str
    ) -> bool:
        """
        Change user password after verifying current password.

        Args:
            user_id: User's unique identifier
            current_password: Current password for verification
            new_password: New password to set

        Returns:
            True if password changed successfully

        Raises:
            BusinessRuleError: If current password is incorrect
            ValidationError: If new password doesn't meet requirements
        """
        user = await self.get(user_id)
        if not user:
            return False

        # Verify current password
        if not self._verify_password(current_password, user.hashed_password):
            raise BusinessRuleError("Current password is incorrect")

        # Validate new password strength
        is_valid, error_msg = PasswordValidator.validate(new_password)
        if not is_valid:
            raise ValidationError(error_msg)

        # Hash and update password
        hashed_password = self._hash_password(new_password)
        await self.repository.update(user_id, {"hashed_password": hashed_password})
        return True

    async def reset_password(self, user_id: UUID, new_password: str) -> bool:
        """
        Reset user password (admin/forgot password flow).

        This method bypasses current password verification and should only
        be used in trusted contexts (password reset tokens, admin operations).

        Args:
            user_id: User's unique identifier
            new_password: New password to set

        Returns:
            True if password reset successfully

        Raises:
            ValidationError: If new password doesn't meet requirements
        """
        # Validate new password strength
        is_valid, error_msg = PasswordValidator.validate(new_password)
        if not is_valid:
            raise ValidationError(error_msg)

        # Hash and update password
        hashed_password = self._hash_password(new_password)
        await self.repository.update(user_id, {"hashed_password": hashed_password})
        return True
