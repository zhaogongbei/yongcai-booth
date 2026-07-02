from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate, UserUpdate, UserResponse
from app.models.models import User
from app.core.password import PasswordValidator


class UserService:
    """Service for user business logic"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = UserRepository(db)
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return PasswordValidator.verify_password(plain_password, hashed_password)
    
    @staticmethod
    def get_password_hash(password: str) -> str:
        """Hash a password"""
        return PasswordValidator.hash_password(password)
    
    async def get_user(self, user_id: UUID) -> Optional[User]:
        """Get user by ID"""
        return await self.repository.get(user_id)
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        return await self.repository.get_by_email(email)
    
    async def authenticate(self, email: str, password: str) -> Optional[User]:
        """Authenticate user with email and password"""
        user = await self.repository.get_by_email_active(email)
        if not user:
            return None
        if not self.verify_password(password, user.hashed_password):
            return None
        return user
    
    async def create_user(self, user_in: UserCreate) -> User:
        """Create a new user"""
        # Check if email already exists
        if await self.repository.email_exists(user_in.email):
            raise ValueError("Email already registered")
        
        # Validate password strength
        is_valid, error_msg = PasswordValidator.validate(user_in.password)
        if not is_valid:
            raise ValueError(error_msg)
        
        # Hash password
        hashed_password = self.get_password_hash(user_in.password)
        
        # Create user
        user_data = {
            "email": user_in.email,
            "hashed_password": hashed_password,
            "full_name": user_in.full_name,
            "is_active": True,
            "is_verified": False,
        }
        
        return await self.repository.create(user_data)
    
    async def update_user(
        self,
        user_id: UUID,
        user_in: UserUpdate
    ) -> Optional[User]:
        """Update user information"""
        user = await self.repository.get(user_id)
        if not user:
            return None
        
        update_data = user_in.model_dump(exclude_unset=True)
        
        # Check email uniqueness if email is being updated
        if "email" in update_data:
            existing_user = await self.repository.get_by_email(update_data["email"])
            if existing_user and existing_user.id != user_id:
                raise ValueError("Email already registered")
        
        return await self.repository.update(user_id, update_data)
    
    async def delete_user(self, user_id: UUID) -> bool:
        """Delete a user"""
        return await self.repository.delete(user_id)
    
    async def deactivate_user(self, user_id: UUID) -> bool:
        """Deactivate a user account"""
        return await self.repository.deactivate(user_id)
    
    async def verify_email(self, user_id: UUID) -> bool:
        """Mark user email as verified"""
        return await self.repository.verify_email(user_id)
    
    async def change_password(
        self,
        user_id: UUID,
        current_password: str,
        new_password: str
    ) -> bool:
        """Change user password"""
        user = await self.repository.get(user_id)
        if not user:
            return False
        
        # Verify current password
        if not self.verify_password(current_password, user.hashed_password):
            raise ValueError("Current password is incorrect")
        
        # Validate new password strength
        is_valid, error_msg = PasswordValidator.validate(new_password)
        if not is_valid:
            raise ValueError(error_msg)
        
        # Hash new password
        hashed_password = self.get_password_hash(new_password)
        
        # Update password
        await self.repository.update(user_id, {"hashed_password": hashed_password})
        return True
    
    async def reset_password(self, user_id: UUID, new_password: str) -> bool:
        """Reset user password (admin/forgot password flow)"""
        # Validate new password strength
        is_valid, error_msg = PasswordValidator.validate(new_password)
        if not is_valid:
            raise ValueError(error_msg)
        
        hashed_password = self.get_password_hash(new_password)
        await self.repository.update(user_id, {"hashed_password": hashed_password})
        return True
