"""
Soft Delete Utilities for D-Booth Backend

This module provides utilities for working with soft-deleted records.
"""

from datetime import datetime
from typing import Optional, Type, TypeVar
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeMeta

from app.models.models import SoftDeleteMixin

T = TypeVar("T", bound=SoftDeleteMixin)


class SoftDeleteManager:
    """Manager for soft delete operations on models."""

    @staticmethod
    async def soft_delete(
        session: AsyncSession, model: Type[T], record_id: UUID, deleted_by: Optional[UUID] = None
    ) -> Optional[T]:
        """
        Soft delete a record by ID.

        Args:
            session: Database session
            model: Model class
            record_id: ID of record to delete
            deleted_by: ID of user performing the deletion

        Returns:
            The soft-deleted record, or None if not found
        """
        stmt = (
            update(model)
            .where(model.id == record_id)
            .where(model.is_deleted == False)
            .values(is_deleted=True, deleted_at=datetime.utcnow(), deleted_by=deleted_by)
            .returning(model)
        )
        result = await session.execute(stmt)
        await session.commit()
        return result.scalar_one_or_none()

    @staticmethod
    async def restore(session: AsyncSession, model: Type[T], record_id: UUID) -> Optional[T]:
        """
        Restore a soft-deleted record.

        Args:
            session: Database session
            model: Model class
            record_id: ID of record to restore

        Returns:
            The restored record, or None if not found
        """
        stmt = (
            update(model)
            .where(model.id == record_id)
            .where(model.is_deleted == True)
            .values(is_deleted=False, deleted_at=None, deleted_by=None)
            .returning(model)
        )
        result = await session.execute(stmt)
        await session.commit()
        return result.scalar_one_or_none()

    @staticmethod
    async def permanently_delete(session: AsyncSession, model: Type[T], record_id: UUID) -> bool:
        """
        Permanently delete a record from the database.

        WARNING: This is irreversible. Only use for data cleanup.

        Args:
            session: Database session
            model: Model class
            record_id: ID of record to permanently delete

        Returns:
            True if deleted, False if not found
        """
        stmt = select(model).where(model.id == record_id)
        result = await session.execute(stmt)
        record = result.scalar_one_or_none()

        if record:
            await session.delete(record)
            await session.commit()
            return True
        return False

    @staticmethod
    def exclude_deleted(query):
        """
        Add filter to exclude soft-deleted records from a query.

        Usage:
            query = select(User).where(User.email == email)
            query = SoftDeleteManager.exclude_deleted(query)

        Args:
            query: SQLAlchemy select query

        Returns:
            Modified query with soft delete filter
        """
        # Get the model from the query
        model = query.column_descriptions[0]["entity"]
        if hasattr(model, "is_deleted"):
            return query.where(model.is_deleted == False)
        return query

    @staticmethod
    def only_deleted(query):
        """
        Add filter to only get soft-deleted records.

        Args:
            query: SQLAlchemy select query

        Returns:
            Modified query to only return deleted records
        """
        model = query.column_descriptions[0]["entity"]
        if hasattr(model, "is_deleted"):
            return query.where(model.is_deleted == True)
        return query

    @staticmethod
    def include_deleted(query):
        """
        Return query as-is (includes both deleted and non-deleted).

        This is a no-op method for API consistency.

        Args:
            query: SQLAlchemy select query

        Returns:
            Unmodified query
        """
        return query


# Convenience functions for direct use


async def soft_delete(
    session: AsyncSession, model: Type[T], record_id: UUID, deleted_by: Optional[UUID] = None
) -> Optional[T]:
    """Convenience function for soft deleting a record."""
    return await SoftDeleteManager.soft_delete(session, model, record_id, deleted_by)


async def restore(session: AsyncSession, model: Type[T], record_id: UUID) -> Optional[T]:
    """Convenience function for restoring a soft-deleted record."""
    return await SoftDeleteManager.restore(session, model, record_id)


async def permanently_delete(session: AsyncSession, model: Type[T], record_id: UUID) -> bool:
    """Convenience function for permanently deleting a record."""
    return await SoftDeleteManager.permanently_delete(session, model, record_id)


def exclude_deleted(query):
    """Convenience function for excluding soft-deleted records."""
    return SoftDeleteManager.exclude_deleted(query)


def only_deleted(query):
    """Convenience function for only getting soft-deleted records."""
    return SoftDeleteManager.only_deleted(query)


def include_deleted(query):
    """Convenience function for including all records (deleted and non-deleted)."""
    return SoftDeleteManager.include_deleted(query)
