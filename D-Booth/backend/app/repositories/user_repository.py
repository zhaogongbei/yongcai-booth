from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import noload
from app.models.models import User
from app.repositories.base import BaseRepository, log_query_performance
from app.repositories.cache_decorator import cached, invalidate_cache


class UserRepository(BaseRepository[User]):
    """
    Repository for User model with caching and performance optimizations.

    Provides methods for:
    - User lookup by ID, email, or active status
    - Email existence checks
    - Account verification and deactivation
    - Cached queries for frequently accessed users
    """

    def __init__(self, db: AsyncSession):
        super().__init__(User, db)

    @log_query_performance(threshold_ms=50.0)
    @cached(ttl=300, key_builder=lambda self, id: f"user:{id}")
    async def get(self, id: UUID) -> Optional[User]:
        """
        Get a user by ID without preloading relationship graphs.

        Results are cached for 5 minutes.

        Args:
            id: User identifier

        Returns:
            User instance if found, None otherwise
        """
        result = await self.db.execute(
            select(User).options(noload("*")).where(User.id == id)
        )
        return result.scalar_one_or_none()

    @log_query_performance(threshold_ms=50.0)
    @cached(ttl=600, key_builder=lambda self, email: f"user:email:{email}")
    async def get_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email address.

        Results are cached for 10 minutes.

        Args:
            email: User email address

        Returns:
            User instance if found, None otherwise
        """
        result = await self.db.execute(
            select(User).options(noload("*")).where(User.email == email)
        )
        return result.scalar_one_or_none()

    @log_query_performance(threshold_ms=50.0)
    async def get_by_email_active(self, email: str) -> Optional[User]:
        """
        Get active user by email address.

        Not cached since login checks should always be fresh.

        Args:
            email: User email address

        Returns:
            User instance if found and active, None otherwise
        """
        result = await self.db.execute(
            select(User).options(noload("*")).where(
                User.email == email,
                User.is_active == True
            )
        )
        return result.scalar_one_or_none()

    @log_query_performance(threshold_ms=50.0)
    async def email_exists(self, email: str) -> bool:
        """
        Check if email already exists in the system.

        Args:
            email: Email address to check

        Returns:
            True if email exists, False otherwise
        """
        result = await self.db.execute(
            select(User.id).where(User.email == email)
        )
        return result.scalar_one_or_none() is not None

    @log_query_performance(threshold_ms=100.0)
    @invalidate_cache("user:{user_id}")
    @invalidate_cache("user:email:*")
    async def verify_email(self, user_id: UUID) -> bool:
        """
        Mark user email as verified and invalidate caches.

        Args:
            user_id: User identifier

        Returns:
            True if user was found and verified, False otherwise
        """
        stmt = select(User).options(noload("*")).where(User.id == user_id)
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()

        if user:
            user.is_verified = True
            await self.db.commit()
            return True
        return False

    @log_query_performance(threshold_ms=100.0)
    @invalidate_cache("user:{user_id}")
    @invalidate_cache("user:email:*")
    async def deactivate(self, user_id: UUID) -> bool:
        """
        Deactivate a user account and invalidate caches.

        Args:
            user_id: User identifier

        Returns:
            True if user was found and deactivated, False otherwise
        """
        stmt = select(User).options(noload("*")).where(User.id == user_id)
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()

        if user:
            user.is_active = False
            await self.db.commit()
            return True
        return False

    @invalidate_cache("user:*")
    async def create(self, obj_in: dict) -> User:
        """
        Create a new user and invalidate all user caches.

        Args:
            obj_in: User data dictionary

        Returns:
            Created User instance
        """
        return await super().create(obj_in)

    @invalidate_cache("user:*")
    async def update(self, id: UUID, obj_in: dict) -> Optional[User]:
        """
        Update user and invalidate caches.

        Args:
            id: User identifier
            obj_in: Fields to update

        Returns:
            Updated User instance, or None if not found
        """
        return await super().update(id, obj_in)

