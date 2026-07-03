"""
Unit tests for repository layer with bulk operations and caching.

Tests cover:
- BaseRepository CRUD operations
- Bulk create/update/delete
- Error handling
- Performance logging
- Cache behavior (mocked)
"""

import uuid
from datetime import datetime, timezone
from typing import List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.models import Event, EventStatus, Photo, User
from app.repositories.base import (
    DatabaseOperationError,
    DuplicateRecordError,
    RecordNotFoundError,
    ValidationError,
)
from app.repositories.event_repository import EventRepository
from app.repositories.photo_repository import PhotoRepository
from app.repositories.user_repository import UserRepository

# Test database setup
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def async_engine():
    """Create async test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        future=True,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def async_session(async_engine):
    """Create async test database session."""
    async_session_maker = sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_maker() as session:
        yield session


@pytest.fixture
def user_repo(async_session):
    """Create UserRepository instance."""
    return UserRepository(async_session)


@pytest.fixture
def event_repo(async_session):
    """Create EventRepository instance."""
    return EventRepository(async_session)


@pytest.fixture
def photo_repo(async_session):
    """Create PhotoRepository instance."""
    return PhotoRepository(async_session)


class TestBaseRepository:
    """Test BaseRepository CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_user(self, user_repo):
        """Test creating a single user."""
        user_data = {
            "email": "test@example.com",
            "hashed_password": "hashed_password_123",
            "full_name": "Test User",
            "is_active": True,
        }

        user = await user_repo.create(user_data)

        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.full_name == "Test User"
        assert user.is_active is True

    @pytest.mark.asyncio
    async def test_get_user_by_id(self, user_repo):
        """Test retrieving user by ID."""
        user_data = {
            "email": "test@example.com",
            "hashed_password": "hashed_password_123",
            "full_name": "Test User",
        }
        created_user = await user_repo.create(user_data)

        retrieved_user = await user_repo.get(created_user.id)

        assert retrieved_user is not None
        assert retrieved_user.id == created_user.id
        assert retrieved_user.email == created_user.email

    @pytest.mark.asyncio
    async def test_get_nonexistent_user(self, user_repo):
        """Test retrieving non-existent user returns None."""
        non_existent_id = uuid.uuid4()
        user = await user_repo.get(non_existent_id)

        assert user is None

    @pytest.mark.asyncio
    async def test_get_multi_users(self, user_repo):
        """Test retrieving multiple users with pagination."""
        # Create 5 users
        for i in range(5):
            await user_repo.create(
                {
                    "email": f"user{i}@example.com",
                    "hashed_password": "password",
                    "full_name": f"User {i}",
                }
            )

        # Get first 3 users
        users = await user_repo.get_multi(skip=0, limit=3)
        assert len(users) == 3

        # Get next 2 users
        users = await user_repo.get_multi(skip=3, limit=3)
        assert len(users) == 2

    @pytest.mark.asyncio
    async def test_update_user(self, user_repo):
        """Test updating user fields."""
        user_data = {
            "email": "test@example.com",
            "hashed_password": "password",
            "full_name": "Test User",
        }
        user = await user_repo.create(user_data)

        updated_user = await user_repo.update(
            user.id, {"full_name": "Updated Name", "is_active": False}
        )

        assert updated_user is not None
        assert updated_user.full_name == "Updated Name"
        assert updated_user.is_active is False

    @pytest.mark.asyncio
    async def test_update_nonexistent_user(self, user_repo):
        """Test updating non-existent user returns None."""
        non_existent_id = uuid.uuid4()
        result = await user_repo.update(non_existent_id, {"full_name": "Test"})

        assert result is None

    @pytest.mark.asyncio
    async def test_delete_user(self, user_repo):
        """Test deleting a user."""
        user_data = {
            "email": "test@example.com",
            "hashed_password": "password",
            "full_name": "Test User",
        }
        user = await user_repo.create(user_data)

        deleted = await user_repo.delete(user.id)
        assert deleted is True

        # Verify user is deleted
        retrieved = await user_repo.get(user.id)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_user(self, user_repo):
        """Test deleting non-existent user returns False."""
        non_existent_id = uuid.uuid4()
        deleted = await user_repo.delete(non_existent_id)

        assert deleted is False

    @pytest.mark.asyncio
    async def test_exists(self, user_repo):
        """Test checking if user exists."""
        user_data = {
            "email": "test@example.com",
            "hashed_password": "password",
            "full_name": "Test User",
        }
        user = await user_repo.create(user_data)

        exists = await user_repo.exists(user.id)
        assert exists is True

        non_existent_id = uuid.uuid4()
        exists = await user_repo.exists(non_existent_id)
        assert exists is False

    @pytest.mark.asyncio
    async def test_count(self, user_repo):
        """Test counting total users."""
        initial_count = await user_repo.count()

        # Create 3 users
        for i in range(3):
            await user_repo.create(
                {
                    "email": f"user{i}@example.com",
                    "hashed_password": "password",
                    "full_name": f"User {i}",
                }
            )

        final_count = await user_repo.count()
        assert final_count == initial_count + 3


class TestBulkOperations:
    """Test bulk create/update/delete operations."""

    @pytest.mark.asyncio
    async def test_bulk_create_users(self, user_repo):
        """Test creating multiple users in bulk."""
        users_data = [
            {
                "email": f"user{i}@example.com",
                "hashed_password": "password",
                "full_name": f"User {i}",
            }
            for i in range(10)
        ]

        created_users = await user_repo.bulk_create(users_data, batch_size=5)

        assert len(created_users) == 10
        assert all(user.id is not None for user in created_users)
        assert created_users[0].email == "user0@example.com"
        assert created_users[9].email == "user9@example.com"

    @pytest.mark.asyncio
    async def test_bulk_create_empty_list(self, user_repo):
        """Test bulk create with empty list returns empty list."""
        result = await user_repo.bulk_create([])
        assert result == []

    @pytest.mark.asyncio
    async def test_bulk_update_users(self, user_repo):
        """Test updating multiple users in bulk."""
        # Create 3 users
        users = []
        for i in range(3):
            user = await user_repo.create(
                {
                    "email": f"user{i}@example.com",
                    "hashed_password": "password",
                    "full_name": f"User {i}",
                    "is_active": True,
                }
            )
            users.append(user)

        # Bulk update
        updates = [
            {"id": users[0].id, "is_active": False},
            {"id": users[1].id, "is_active": False},
            {"id": users[2].id, "full_name": "Updated User 2"},
        ]

        count = await user_repo.bulk_update(updates)
        assert count == 3

        # Verify updates
        user0 = await user_repo.get(users[0].id)
        assert user0.is_active is False

        user2 = await user_repo.get(users[2].id)
        assert user2.full_name == "Updated User 2"

    @pytest.mark.asyncio
    async def test_bulk_update_empty_list(self, user_repo):
        """Test bulk update with empty list."""
        count = await user_repo.bulk_update([])
        assert count == 0

    @pytest.mark.asyncio
    async def test_bulk_delete_users(self, user_repo):
        """Test deleting multiple users in bulk."""
        # Create 3 users
        user_ids = []
        for i in range(3):
            user = await user_repo.create(
                {
                    "email": f"user{i}@example.com",
                    "hashed_password": "password",
                    "full_name": f"User {i}",
                }
            )
            user_ids.append(user.id)

        # Bulk delete
        count = await user_repo.bulk_delete(user_ids)
        assert count == 3

        # Verify all deleted
        for user_id in user_ids:
            user = await user_repo.get(user_id)
            assert user is None

    @pytest.mark.asyncio
    async def test_bulk_delete_empty_list(self, user_repo):
        """Test bulk delete with empty list."""
        count = await user_repo.bulk_delete([])
        assert count == 0


class TestErrorHandling:
    """Test error handling and validation."""

    @pytest.mark.asyncio
    async def test_validation_error_negative_skip(self, user_repo):
        """Test validation error for negative skip parameter."""
        with pytest.raises(ValidationError) as exc_info:
            await user_repo.get_multi(skip=-1, limit=10)

        assert "skip must be non-negative" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validation_error_invalid_limit(self, user_repo):
        """Test validation error for invalid limit parameter."""
        with pytest.raises(ValidationError) as exc_info:
            await user_repo.get_multi(skip=0, limit=0)

        assert "limit must be between 1 and 1000" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validation_error_limit_too_large(self, user_repo):
        """Test validation error for limit exceeding maximum."""
        with pytest.raises(ValidationError) as exc_info:
            await user_repo.get_multi(skip=0, limit=2000)

        assert "limit must be between 1 and 1000" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_duplicate_email_error(self, user_repo):
        """Test duplicate record error for unique constraint violation."""
        user_data = {
            "email": "duplicate@example.com",
            "hashed_password": "password",
            "full_name": "User 1",
        }

        await user_repo.create(user_data)

        # Try to create another user with same email
        with pytest.raises(DuplicateRecordError):
            await user_repo.create(user_data)


class TestUserRepository:
    """Test UserRepository specific methods."""

    @pytest.mark.asyncio
    async def test_get_by_email(self, user_repo):
        """Test finding user by email."""
        user_data = {
            "email": "test@example.com",
            "hashed_password": "password",
            "full_name": "Test User",
        }
        await user_repo.create(user_data)

        user = await user_repo.get_by_email("test@example.com")

        assert user is not None
        assert user.email == "test@example.com"

    @pytest.mark.asyncio
    async def test_get_by_email_not_found(self, user_repo):
        """Test get by email returns None when not found."""
        user = await user_repo.get_by_email("nonexistent@example.com")
        assert user is None

    @pytest.mark.asyncio
    async def test_get_by_email_active(self, user_repo):
        """Test finding active user by email."""
        # Create active user
        await user_repo.create(
            {
                "email": "active@example.com",
                "hashed_password": "password",
                "full_name": "Active User",
                "is_active": True,
            }
        )

        # Create inactive user
        await user_repo.create(
            {
                "email": "inactive@example.com",
                "hashed_password": "password",
                "full_name": "Inactive User",
                "is_active": False,
            }
        )

        active_user = await user_repo.get_by_email_active("active@example.com")
        assert active_user is not None

        inactive_user = await user_repo.get_by_email_active("inactive@example.com")
        assert inactive_user is None

    @pytest.mark.asyncio
    async def test_email_exists(self, user_repo):
        """Test checking if email exists."""
        await user_repo.create(
            {
                "email": "exists@example.com",
                "hashed_password": "password",
                "full_name": "User",
            }
        )

        exists = await user_repo.email_exists("exists@example.com")
        assert exists is True

        exists = await user_repo.email_exists("notexists@example.com")
        assert exists is False

    @pytest.mark.asyncio
    async def test_verify_email(self, user_repo):
        """Test email verification."""
        user = await user_repo.create(
            {
                "email": "test@example.com",
                "hashed_password": "password",
                "full_name": "User",
                "is_verified": False,
            }
        )

        result = await user_repo.verify_email(user.id)
        assert result is True

        verified_user = await user_repo.get(user.id)
        assert verified_user.is_verified is True

    @pytest.mark.asyncio
    async def test_deactivate_user(self, user_repo):
        """Test deactivating a user."""
        user = await user_repo.create(
            {
                "email": "test@example.com",
                "hashed_password": "password",
                "full_name": "User",
                "is_active": True,
            }
        )

        result = await user_repo.deactivate(user.id)
        assert result is True

        deactivated_user = await user_repo.get(user.id)
        assert deactivated_user.is_active is False


class TestPerformanceLogging:
    """Test query performance logging."""

    @pytest.mark.asyncio
    @patch("app.repositories.base.logger")
    async def test_slow_query_warning(self, mock_logger, user_repo):
        """Test that slow queries are logged as warnings."""
        # Mock a slow operation by patching time.perf_counter
        with patch("app.repositories.base.time.perf_counter") as mock_time:
            # First call returns start time, second returns end time
            mock_time.side_effect = [0.0, 0.2]  # 200ms duration

            await user_repo.get_multi(skip=0, limit=10)

            # Check that warning was logged for slow query
            mock_logger.warning.assert_called()
            warning_call = mock_logger.warning.call_args[0][0]
            assert "Slow query detected" in warning_call
            assert "get_multi" in warning_call

    @pytest.mark.asyncio
    @patch("app.repositories.base.logger")
    async def test_fast_query_debug(self, mock_logger, user_repo):
        """Test that fast queries are logged as debug."""
        with patch("app.repositories.base.time.perf_counter") as mock_time:
            # Simulate fast query (10ms)
            mock_time.side_effect = [0.0, 0.01]

            await user_repo.count()

            # Check that debug was logged for fast query
            mock_logger.debug.assert_called()
            debug_call = mock_logger.debug.call_args[0][0]
            assert "completed in" in debug_call


class TestCacheDecorator:
    """Test cache decorator behavior (mocked)."""

    @pytest.mark.asyncio
    @patch("app.repositories.cache_decorator.RedisCache.get")
    @patch("app.repositories.cache_decorator.RedisCache.set")
    async def test_cache_hit(self, mock_set, mock_get, user_repo):
        """Test that cached results are returned on cache hit."""
        # Mock cache hit
        mock_get.return_value = {
            "id": str(uuid.uuid4()),
            "email": "cached@example.com",
            "full_name": "Cached User",
        }

        # This should return cached result
        user = await user_repo.get_by_email("cached@example.com")

        # Verify cache was checked
        mock_get.assert_called()
        # Verify cache set was not called (already cached)
        assert mock_set.call_count == 0

    @pytest.mark.asyncio
    @patch("app.repositories.cache_decorator.RedisCache.get")
    @patch("app.repositories.cache_decorator.RedisCache.set")
    async def test_cache_miss(self, mock_set, mock_get, user_repo):
        """Test that DB is queried on cache miss and result is cached."""
        # Mock cache miss
        mock_get.return_value = None

        # Create actual user in DB
        await user_repo.create(
            {
                "email": "test@example.com",
                "hashed_password": "password",
                "full_name": "Test User",
            }
        )

        # This should query DB and cache the result
        user = await user_repo.get_by_email("test@example.com")

        # Verify cache was checked
        mock_get.assert_called()
        # Verify result was cached
        mock_set.assert_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
