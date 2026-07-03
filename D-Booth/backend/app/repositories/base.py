"""
Base repository module providing common CRUD operations with performance optimization.

This module implements a generic repository pattern with:
- Async SQLAlchemy 2.0 support
- Bulk operations (create, update, delete)
- Query performance logging
- Comprehensive error handling
- Type safety with generics
"""

import logging
import time
from typing import Generic, TypeVar, Type, Optional, List, Sequence, Any, Dict
from uuid import UUID
from functools import wraps
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, inspect
from sqlalchemy.orm import DeclarativeMeta
from sqlalchemy.exc import (
    SQLAlchemyError,
    IntegrityError,
    DataError,
    DatabaseError,
)

logger = logging.getLogger(__name__)

ModelType = TypeVar("ModelType", bound=DeclarativeMeta)


# Custom Exceptions
class RepositoryError(Exception):
    """Base exception for repository operations."""
    pass


class RecordNotFoundError(RepositoryError):
    """Raised when a requested record does not exist."""
    pass


class DuplicateRecordError(RepositoryError):
    """Raised when attempting to create a duplicate record."""
    pass


class ValidationError(RepositoryError):
    """Raised when data validation fails."""
    pass


class DatabaseOperationError(RepositoryError):
    """Raised when a database operation fails."""
    pass


def log_query_performance(threshold_ms: float = 100.0):
    """
    Decorator to log slow queries that exceed the threshold.

    Args:
        threshold_ms: Log warning if query takes longer than this (milliseconds).

    Example:
        @log_query_performance(threshold_ms=50.0)
        async def get_by_email(self, email: str):
            # Query implementation
            pass
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.perf_counter() - start_time) * 1000

                if duration_ms > threshold_ms:
                    logger.warning(
                        f"Slow query detected: {func.__name__} took {duration_ms:.2f}ms "
                        f"(threshold: {threshold_ms}ms)"
                    )
                else:
                    logger.debug(f"{func.__name__} completed in {duration_ms:.2f}ms")

                return result
            except Exception as e:
                duration_ms = (time.perf_counter() - start_time) * 1000
                logger.error(
                    f"Query failed: {func.__name__} after {duration_ms:.2f}ms - {str(e)}"
                )
                raise
        return wrapper
    return decorator


class BaseRepository(Generic[ModelType]):
    """
    Base repository with common CRUD operations and bulk support.

    Provides:
        - Standard CRUD operations (create, read, update, delete)
        - Bulk operations for batch processing
        - Query performance logging
        - Comprehensive error handling
        - Type-safe generic interface

    Type Parameters:
        ModelType: SQLAlchemy ORM model class

    Attributes:
        model: The SQLAlchemy model class this repository manages
        db: AsyncSession for database operations

    Example:
        class UserRepository(BaseRepository[User]):
            def __init__(self, db: AsyncSession):
                super().__init__(User, db)

            async def get_by_email(self, email: str) -> Optional[User]:
                result = await self.db.execute(
                    select(User).where(User.email == email)
                )
                return result.scalar_one_or_none()
    """

    def __init__(self, model: Type[ModelType], db: AsyncSession):
        """
        Initialize the repository.

        Args:
            model: SQLAlchemy model class
            db: Async database session
        """
        self.model = model
        self.db = db
        self._model_name = model.__name__

    @log_query_performance(threshold_ms=100.0)
    async def get(self, id: UUID) -> Optional[ModelType]:
        """
        Get a single record by ID.

        Args:
            id: Unique identifier of the record

        Returns:
            Model instance if found, None otherwise

        Raises:
            DatabaseOperationError: If database operation fails

        Example:
            user = await user_repo.get(user_id)
            if user:
                print(f"Found user: {user.email}")
        """
        try:
            result = await self.db.execute(
                select(self.model).where(self.model.id == id)
            )
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Failed to get {self._model_name} with id {id}: {e}")
            raise DatabaseOperationError(
                f"Failed to retrieve {self._model_name}"
            ) from e

    @log_query_performance(threshold_ms=200.0)
    async def get_multi(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> List[ModelType]:
        """
        Get multiple records with pagination.

        Args:
            skip: Number of records to skip (offset)
            limit: Maximum number of records to return

        Returns:
            List of model instances

        Raises:
            DatabaseOperationError: If database operation fails
            ValidationError: If pagination parameters are invalid

        Example:
            # Get first 50 users
            users = await user_repo.get_multi(skip=0, limit=50)

            # Get next 50 users
            users = await user_repo.get_multi(skip=50, limit=50)
        """
        if skip < 0:
            raise ValidationError("skip must be non-negative")
        if limit < 1 or limit > 1000:
            raise ValidationError("limit must be between 1 and 1000")

        try:
            result = await self.db.execute(
                select(self.model).offset(skip).limit(limit)
            )
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Failed to get multiple {self._model_name}: {e}")
            raise DatabaseOperationError(
                f"Failed to retrieve {self._model_name} records"
            ) from e

    @log_query_performance(threshold_ms=100.0)
    async def create(self, obj_in: dict) -> ModelType:
        """
        Create a new record.

        Args:
            obj_in: Dictionary of field values for the new record

        Returns:
            Created model instance with database-generated fields populated

        Raises:
            DuplicateRecordError: If record violates unique constraint
            ValidationError: If input data is invalid
            DatabaseOperationError: If database operation fails

        Example:
            user_data = {
                "email": "user@example.com",
                "hashed_password": "...",
                "full_name": "John Doe"
            }
            user = await user_repo.create(user_data)
        """
        try:
            db_obj = self.model(**obj_in)
            self.db.add(db_obj)
            await self.db.commit()
            await self.db.refresh(db_obj)
            logger.debug(f"Created {self._model_name} with id {db_obj.id}")
            return db_obj
        except IntegrityError as e:
            await self.db.rollback()
            logger.warning(f"Integrity error creating {self._model_name}: {e}")
            raise DuplicateRecordError(
                f"Record violates unique constraint"
            ) from e
        except (DataError, TypeError) as e:
            await self.db.rollback()
            logger.warning(f"Validation error creating {self._model_name}: {e}")
            raise ValidationError(f"Invalid data for {self._model_name}") from e
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Failed to create {self._model_name}: {e}")
            raise DatabaseOperationError(
                f"Failed to create {self._model_name}"
            ) from e

    @log_query_performance(threshold_ms=500.0)
    async def bulk_create(
        self,
        objects_in: List[dict],
        batch_size: int = 500
    ) -> List[ModelType]:
        """
        Create multiple records in bulk with automatic batching.

        This method processes records in batches to avoid memory issues
        and transaction timeouts with large datasets.

        Args:
            objects_in: List of dictionaries containing field values
            batch_size: Number of records to insert per batch (default: 500)

        Returns:
            List of created model instances

        Raises:
            ValidationError: If input data is invalid
            DuplicateRecordError: If any record violates unique constraint
            DatabaseOperationError: If database operation fails

        Example:
            user_data = [
                {"email": "user1@example.com", "full_name": "User 1"},
                {"email": "user2@example.com", "full_name": "User 2"},
                # ... more users
            ]
            users = await user_repo.bulk_create(user_data, batch_size=100)
            print(f"Created {len(users)} users")
        """
        if not objects_in:
            return []

        if batch_size < 1:
            raise ValidationError("batch_size must be positive")

        created_objects = []

        try:
            # Process in batches
            for i in range(0, len(objects_in), batch_size):
                batch = objects_in[i:i + batch_size]
                db_objects = [self.model(**obj_data) for obj_data in batch]
                self.db.add_all(db_objects)
                await self.db.flush()
                created_objects.extend(db_objects)

            await self.db.commit()

            # Refresh all objects to get DB-generated values
            for obj in created_objects:
                await self.db.refresh(obj)

            logger.info(
                f"Bulk created {len(created_objects)} {self._model_name} records "
                f"in {(len(objects_in) + batch_size - 1) // batch_size} batches"
            )
            return created_objects

        except IntegrityError as e:
            await self.db.rollback()
            logger.warning(f"Integrity error in bulk create {self._model_name}: {e}")
            raise DuplicateRecordError(
                f"One or more records violate unique constraint"
            ) from e
        except (DataError, TypeError) as e:
            await self.db.rollback()
            logger.warning(f"Validation error in bulk create {self._model_name}: {e}")
            raise ValidationError(f"Invalid data in bulk create") from e
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Failed to bulk create {self._model_name}: {e}")
            raise DatabaseOperationError(
                f"Failed to bulk create {self._model_name}"
            ) from e

    @log_query_performance(threshold_ms=150.0)
    async def update(self, id: UUID, obj_in: dict) -> Optional[ModelType]:
        """
        Update an existing record and return the refreshed ORM object.

        Uses a select-then-mutate pattern instead of Core update()…
        returning() because the latter returns plain column tuples, not
        ORM instances — relationship access would fail silently.

        Args:
            id: Unique identifier of the record to update
            obj_in: Dictionary of fields to update

        Returns:
            Updated model instance if found, None otherwise

        Raises:
            ValidationError: If input data is invalid
            DuplicateRecordError: If update violates unique constraint
            DatabaseOperationError: If database operation fails

        Example:
            updated_user = await user_repo.update(
                user_id,
                {"full_name": "Jane Doe", "is_active": True}
            )
        """
        try:
            obj = await self.get(id)
            if not obj:
                return None

            for key, value in obj_in.items():
                if hasattr(obj, key):
                    setattr(obj, key, value)

            await self.db.commit()
            await self.db.refresh(obj)
            logger.debug(f"Updated {self._model_name} with id {id}")
            return obj

        except IntegrityError as e:
            await self.db.rollback()
            logger.warning(f"Integrity error updating {self._model_name}: {e}")
            raise DuplicateRecordError(
                f"Update violates unique constraint"
            ) from e
        except (DataError, TypeError) as e:
            await self.db.rollback()
            logger.warning(f"Validation error updating {self._model_name}: {e}")
            raise ValidationError(f"Invalid data for {self._model_name}") from e
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Failed to update {self._model_name} with id {id}: {e}")
            raise DatabaseOperationError(
                f"Failed to update {self._model_name}"
            ) from e

    @log_query_performance(threshold_ms=500.0)
    async def bulk_update(
        self,
        updates: List[Dict[str, Any]],
        id_field: str = "id"
    ) -> int:
        """
        Update multiple records in a single database round-trip.

        Each update dict must contain the id_field to identify which record
        to update. Uses SQLAlchemy Core for efficiency.

        Args:
            updates: List of dicts, each containing id_field and fields to update
            id_field: Name of the field containing the record identifier

        Returns:
            Number of records updated

        Raises:
            ValidationError: If input data is invalid
            DatabaseOperationError: If database operation fails

        Example:
            updates = [
                {"id": uuid1, "is_active": False},
                {"id": uuid2, "is_active": False},
                {"id": uuid3, "is_active": True},
            ]
            count = await user_repo.bulk_update(updates)
            print(f"Updated {count} users")
        """
        if not updates:
            return 0

        # Validate all updates have id_field
        for upd in updates:
            if id_field not in upd:
                raise ValidationError(
                    f"Each update must contain '{id_field}' field"
                )

        try:
            count = 0
            for upd in updates:
                record_id = upd.pop(id_field)
                if upd:  # Only update if there are fields besides id
                    stmt = (
                        update(self.model)
                        .where(getattr(self.model, id_field) == record_id)
                        .values(**upd)
                    )
                    result = await self.db.execute(stmt)
                    count += result.rowcount

            await self.db.commit()
            logger.info(f"Bulk updated {count} {self._model_name} records")
            return count

        except (DataError, TypeError) as e:
            await self.db.rollback()
            logger.warning(f"Validation error in bulk update {self._model_name}: {e}")
            raise ValidationError(f"Invalid data in bulk update") from e
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Failed to bulk update {self._model_name}: {e}")
            raise DatabaseOperationError(
                f"Failed to bulk update {self._model_name}"
            ) from e

    @log_query_performance(threshold_ms=100.0)
    async def delete(self, id: UUID) -> bool:
        """
        Delete a record by ID.

        Args:
            id: Unique identifier of the record to delete

        Returns:
            True if record was deleted, False if not found

        Raises:
            DatabaseOperationError: If database operation fails

        Example:
            was_deleted = await user_repo.delete(user_id)
            if was_deleted:
                print("User deleted successfully")
        """
        try:
            stmt = delete(self.model).where(self.model.id == id)
            result = await self.db.execute(stmt)
            await self.db.commit()

            deleted = result.rowcount > 0
            if deleted:
                logger.debug(f"Deleted {self._model_name} with id {id}")
            return deleted

        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Failed to delete {self._model_name} with id {id}: {e}")
            raise DatabaseOperationError(
                f"Failed to delete {self._model_name}"
            ) from e

    @log_query_performance(threshold_ms=300.0)
    async def bulk_delete(self, ids: List[UUID]) -> int:
        """
        Delete multiple records by their IDs.

        Args:
            ids: List of record identifiers to delete

        Returns:
            Number of records deleted

        Raises:
            DatabaseOperationError: If database operation fails

        Example:
            deleted_count = await user_repo.bulk_delete([uuid1, uuid2, uuid3])
            print(f"Deleted {deleted_count} users")
        """
        if not ids:
            return 0

        try:
            stmt = delete(self.model).where(self.model.id.in_(ids))
            result = await self.db.execute(stmt)
            await self.db.commit()

            count = result.rowcount
            logger.info(f"Bulk deleted {count} {self._model_name} records")
            return count

        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Failed to bulk delete {self._model_name}: {e}")
            raise DatabaseOperationError(
                f"Failed to bulk delete {self._model_name}"
            ) from e

    async def exists(self, id: UUID) -> bool:
        """
        Check if a record exists by ID.

        Args:
            id: Unique identifier to check

        Returns:
            True if record exists, False otherwise

        Raises:
            DatabaseOperationError: If database operation fails

        Example:
            if await user_repo.exists(user_id):
                print("User exists")
        """
        try:
            result = await self.db.execute(
                select(self.model.id).where(self.model.id == id)
            )
            return result.scalar_one_or_none() is not None
        except SQLAlchemyError as e:
            logger.error(f"Failed to check existence of {self._model_name}: {e}")
            raise DatabaseOperationError(
                f"Failed to check {self._model_name} existence"
            ) from e

    @log_query_performance(threshold_ms=100.0)
    async def count(self) -> int:
        """
        Count total number of records.

        Returns:
            Total record count

        Raises:
            DatabaseOperationError: If database operation fails

        Example:
            total_users = await user_repo.count()
            print(f"Total users: {total_users}")
        """
        try:
            result = await self.db.execute(
                select(func.count()).select_from(self.model)
            )
            return result.scalar_one()
        except SQLAlchemyError as e:
            logger.error(f"Failed to count {self._model_name}: {e}")
            raise DatabaseOperationError(
                f"Failed to count {self._model_name} records"
            ) from e

    @asynccontextmanager
    async def transaction(self):
        """
        Context manager for explicit transaction control.

        Yields control to the caller and commits on success,
        rolls back on exception.

        Yields:
            None

        Raises:
            DatabaseOperationError: If transaction fails

        Example:
            async with user_repo.transaction():
                await user_repo.create(user_data)
                await team_repo.add_member(team_id, user_id)
                # Both operations committed together
        """
        try:
            yield
            await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Transaction failed for {self._model_name}: {e}")
            raise DatabaseOperationError(
                f"Transaction failed: {str(e)}"
            ) from e
