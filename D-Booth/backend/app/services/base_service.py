"""
Base service module providing common business logic patterns.

This module implements a generic service layer pattern with:
- Transaction management
- Error handling and logging
- Common CRUD operations delegation
- Business rule validation
- Event publishing support
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, List, Optional, TypeVar
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.base import (
    BaseRepository,
    DuplicateRecordError,
    RecordNotFoundError,
    RepositoryError,
)
from app.repositories.base import ValidationError as RepoValidationError

logger = logging.getLogger(__name__)

ModelType = TypeVar("ModelType")
CreateSchemaType = TypeVar("CreateSchemaType")
UpdateSchemaType = TypeVar("UpdateSchemaType")


class ServiceError(Exception):
    """Base exception for service layer errors."""

    pass


class BusinessRuleError(ServiceError):
    """Raised when a business rule validation fails."""

    pass


class ResourceNotFoundError(ServiceError):
    """Raised when a requested resource does not exist."""

    pass


class DuplicateResourceError(ServiceError):
    """Raised when attempting to create a duplicate resource."""

    pass


class ValidationError(ServiceError):
    """Raised when input validation fails."""

    pass


class BaseService(Generic[ModelType, CreateSchemaType, UpdateSchemaType], ABC):
    """
    Base service providing common business logic operations.

    This service layer sits between the API layer and the repository layer,
    implementing business rules, validation, and transaction management.

    Type Parameters:
        ModelType: SQLAlchemy model type
        CreateSchemaType: Pydantic schema for creating records
        UpdateSchemaType: Pydantic schema for updating records

    Attributes:
        repository: Repository instance for data access
        db: Database session for transaction management

    Example:
        class UserService(BaseService[User, UserCreate, UserUpdate]):
            def __init__(self, db: AsyncSession):
                repo = UserRepository(db)
                super().__init__(repo, db)

            async def get_by_email(self, email: str) -> Optional[User]:
                # Business logic specific to users
                user = await self.repository.get_by_email(email)
                return user
    """

    def __init__(self, repository: BaseRepository[ModelType], db: AsyncSession):
        """
        Initialize the service.

        Args:
            repository: Repository instance for data access
            db: Async database session
        """
        self.repository = repository
        self.db = db
        self._model_name = repository.model.__name__

    async def get(self, id: UUID) -> Optional[ModelType]:
        """
        Get a single resource by ID.

        Args:
            id: Unique identifier

        Returns:
            Model instance if found, None otherwise

        Raises:
            ServiceError: If retrieval fails

        Example:
            user = await user_service.get(user_id)
        """
        try:
            return await self.repository.get(id)
        except RepositoryError as e:
            logger.error(f"Failed to get {self._model_name} {id}: {e}")
            raise ServiceError(f"Failed to retrieve {self._model_name}") from e

    async def get_or_404(self, id: UUID) -> ModelType:
        """
        Get a resource by ID or raise ResourceNotFoundError.

        Args:
            id: Unique identifier

        Returns:
            Model instance

        Raises:
            ResourceNotFoundError: If resource not found
            ServiceError: If retrieval fails

        Example:
            user = await user_service.get_or_404(user_id)
        """
        obj = await self.get(id)
        if not obj:
            raise ResourceNotFoundError(f"{self._model_name} not found")
        return obj

    async def get_multi(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """
        Get multiple resources with pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records

        Returns:
            List of model instances

        Raises:
            ValidationError: If pagination parameters are invalid
            ServiceError: If retrieval fails

        Example:
            users = await user_service.get_multi(skip=0, limit=50)
        """
        try:
            return await self.repository.get_multi(skip=skip, limit=limit)
        except RepoValidationError as e:
            raise ValidationError(str(e)) from e
        except RepositoryError as e:
            logger.error(f"Failed to get multiple {self._model_name}: {e}")
            raise ServiceError(f"Failed to retrieve {self._model_name} list") from e

    async def create(self, obj_in: CreateSchemaType) -> ModelType:
        """
        Create a new resource.

        Validates business rules before creating the resource.

        Args:
            obj_in: Pydantic schema with creation data

        Returns:
            Created model instance

        Raises:
            BusinessRuleError: If business rules are violated
            DuplicateResourceError: If resource already exists
            ValidationError: If input validation fails
            ServiceError: If creation fails

        Example:
            user_data = UserCreate(email="test@example.com", password="...")
            user = await user_service.create(user_data)
        """
        try:
            # Validate business rules before creation
            await self.validate_create(obj_in)

            # Convert Pydantic model to dict
            obj_dict = obj_in.model_dump() if hasattr(obj_in, "model_dump") else obj_in.dict()

            # Perform any necessary transformations
            obj_dict = await self.before_create(obj_dict)

            # Create the resource
            created_obj = await self.repository.create(obj_dict)

            # Publish domain events or trigger side effects
            await self.after_create(created_obj)

            logger.info(f"Created {self._model_name} with id {created_obj.id}")
            return created_obj

        except DuplicateRecordError as e:
            raise DuplicateResourceError(f"{self._model_name} already exists") from e
        except RepoValidationError as e:
            raise ValidationError(str(e)) from e
        except RepositoryError as e:
            logger.error(f"Failed to create {self._model_name}: {e}")
            raise ServiceError(f"Failed to create {self._model_name}") from e

    async def update(self, id: UUID, obj_in: UpdateSchemaType) -> Optional[ModelType]:
        """
        Update an existing resource.

        Validates business rules before updating.

        Args:
            id: Unique identifier of the resource
            obj_in: Pydantic schema with update data

        Returns:
            Updated model instance if found, None otherwise

        Raises:
            BusinessRuleError: If business rules are violated
            DuplicateResourceError: If update creates duplicate
            ValidationError: If input validation fails
            ServiceError: If update fails

        Example:
            update_data = UserUpdate(full_name="Jane Doe")
            user = await user_service.update(user_id, update_data)
        """
        try:
            # Check if resource exists
            existing = await self.get(id)
            if not existing:
                return None

            # Validate business rules
            await self.validate_update(existing, obj_in)

            # Convert Pydantic model to dict, excluding unset fields
            obj_dict = (
                obj_in.model_dump(exclude_unset=True)
                if hasattr(obj_in, "model_dump")
                else obj_in.dict(exclude_unset=True)
            )

            # Perform any necessary transformations
            obj_dict = await self.before_update(existing, obj_dict)

            # Update the resource
            updated_obj = await self.repository.update(id, obj_dict)

            # Publish domain events or trigger side effects
            if updated_obj:
                await self.after_update(updated_obj)

            logger.info(f"Updated {self._model_name} with id {id}")
            return updated_obj

        except DuplicateRecordError as e:
            raise DuplicateResourceError(f"Update creates duplicate {self._model_name}") from e
        except RepoValidationError as e:
            raise ValidationError(str(e)) from e
        except RepositoryError as e:
            logger.error(f"Failed to update {self._model_name} {id}: {e}")
            raise ServiceError(f"Failed to update {self._model_name}") from e

    async def delete(self, id: UUID) -> bool:
        """
        Delete a resource by ID.

        Validates business rules before deletion.

        Args:
            id: Unique identifier

        Returns:
            True if deleted, False if not found

        Raises:
            BusinessRuleError: If business rules prevent deletion
            ServiceError: If deletion fails

        Example:
            was_deleted = await user_service.delete(user_id)
        """
        try:
            # Check if resource exists
            existing = await self.get(id)
            if not existing:
                return False

            # Validate business rules
            await self.validate_delete(existing)

            # Perform pre-deletion cleanup
            await self.before_delete(existing)

            # Delete the resource
            deleted = await self.repository.delete(id)

            # Publish domain events or trigger side effects
            if deleted:
                await self.after_delete(id)

            logger.info(f"Deleted {self._model_name} with id {id}")
            return deleted

        except RepositoryError as e:
            logger.error(f"Failed to delete {self._model_name} {id}: {e}")
            raise ServiceError(f"Failed to delete {self._model_name}") from e

    async def exists(self, id: UUID) -> bool:
        """
        Check if a resource exists.

        Args:
            id: Unique identifier

        Returns:
            True if exists, False otherwise

        Example:
            if await user_service.exists(user_id):
                print("User exists")
        """
        try:
            return await self.repository.exists(id)
        except RepositoryError as e:
            logger.error(f"Failed to check {self._model_name} existence: {e}")
            raise ServiceError(f"Failed to check existence") from e

    async def count(self) -> int:
        """
        Count total number of resources.

        Returns:
            Total count

        Example:
            total = await user_service.count()
        """
        try:
            return await self.repository.count()
        except RepositoryError as e:
            logger.error(f"Failed to count {self._model_name}: {e}")
            raise ServiceError(f"Failed to count {self._model_name}") from e

    # Hooks for subclasses to override

    async def validate_create(self, obj_in: CreateSchemaType) -> None:
        """
        Validate business rules before creation.

        Override this method to implement custom validation logic.

        Args:
            obj_in: Input data for creation

        Raises:
            BusinessRuleError: If validation fails

        Example:
            async def validate_create(self, obj_in: UserCreate):
                if "@" not in obj_in.email:
                    raise BusinessRuleError("Invalid email format")
        """
        pass

    async def validate_update(self, existing: ModelType, obj_in: UpdateSchemaType) -> None:
        """
        Validate business rules before update.

        Override this method to implement custom validation logic.

        Args:
            existing: Current state of the resource
            obj_in: Input data for update

        Raises:
            BusinessRuleError: If validation fails

        Example:
            async def validate_update(self, existing: User, obj_in: UserUpdate):
                if obj_in.role == "admin" and not existing.is_verified:
                    raise BusinessRuleError("Cannot promote unverified user")
        """
        pass

    async def validate_delete(self, existing: ModelType) -> None:
        """
        Validate business rules before deletion.

        Override this method to implement custom validation logic.

        Args:
            existing: Resource to be deleted

        Raises:
            BusinessRuleError: If deletion is not allowed

        Example:
            async def validate_delete(self, existing: User):
                if existing.is_owner:
                    raise BusinessRuleError("Cannot delete team owner")
        """
        pass

    async def before_create(self, obj_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform data before creation.

        Override this method to perform data transformations.

        Args:
            obj_dict: Dictionary of field values

        Returns:
            Transformed dictionary

        Example:
            async def before_create(self, obj_dict: Dict):
                obj_dict["created_by_ip"] = get_client_ip()
                return obj_dict
        """
        return obj_dict

    async def before_update(self, existing: ModelType, obj_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform data before update.

        Override this method to perform data transformations.

        Args:
            existing: Current state of the resource
            obj_dict: Dictionary of fields to update

        Returns:
            Transformed dictionary

        Example:
            async def before_update(self, existing: User, obj_dict: Dict):
                obj_dict["updated_by"] = get_current_user_id()
                return obj_dict
        """
        return obj_dict

    async def before_delete(self, existing: ModelType) -> None:
        """
        Perform cleanup before deletion.

        Override this method to handle cascading deletes or cleanup.

        Args:
            existing: Resource to be deleted

        Example:
            async def before_delete(self, existing: User):
                # Delete user's sessions
                await session_service.delete_by_user(existing.id)
        """
        pass

    async def after_create(self, created: ModelType) -> None:
        """
        Handle side effects after creation.

        Override this method to publish events or trigger workflows.

        Args:
            created: Newly created resource

        Example:
            async def after_create(self, created: User):
                await event_publisher.publish(UserCreatedEvent(user_id=created.id))
                await email_service.send_welcome_email(created.email)
        """
        pass

    async def after_update(self, updated: ModelType) -> None:
        """
        Handle side effects after update.

        Override this method to publish events or trigger workflows.

        Args:
            updated: Updated resource

        Example:
            async def after_update(self, updated: User):
                await event_publisher.publish(UserUpdatedEvent(user_id=updated.id))
        """
        pass

    async def after_delete(self, id: UUID) -> None:
        """
        Handle side effects after deletion.

        Override this method to publish events or trigger workflows.

        Args:
            id: ID of deleted resource

        Example:
            async def after_delete(self, id: UUID):
                await event_publisher.publish(UserDeletedEvent(user_id=id))
        """
        pass
