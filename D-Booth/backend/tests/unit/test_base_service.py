"""
Unit tests for BaseService.

Tests all CRUD methods, hooks, and exception handling.
"""

from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from app.repositories.base import (
    BaseRepository,
    DuplicateRecordError,
    RecordNotFoundError,
    RepositoryError,
)
from app.repositories.base import ValidationError as RepoValidationError
from app.services.base_service import (
    BaseService,
    BusinessRuleError,
    DuplicateResourceError,
    ResourceNotFoundError,
    ServiceError,
    ValidationError,
)


# Mock Model
class MockModel:
    def __init__(self, id: UUID, name: str):
        self.id = id
        self.name = name


# Mock Schemas
class MockCreate:
    name: str

    def __init__(self, name: str):
        self.name = name

    def model_dump(self):
        return {"name": self.name}


class MockUpdate:
    name: Optional[str] = None

    def __init__(self, name: Optional[str] = None):
        self.name = name

    def model_dump(self, exclude_unset=False):
        data = {}
        if self.name is not None:
            data["name"] = self.name
        return data


# Concrete Service for Testing
class MockService(BaseService[MockModel, MockCreate, MockUpdate]):
    def __init__(self, repository, db):
        super().__init__(repository, db)
        self.validate_create_called = False
        self.validate_update_called = False
        self.validate_delete_called = False
        self.before_create_called = False
        self.before_update_called = False
        self.before_delete_called = False
        self.after_create_called = False
        self.after_update_called = False
        self.after_delete_called = False

    async def validate_create(self, obj_in: MockCreate) -> None:
        self.validate_create_called = True
        if obj_in.name == "forbidden":
            raise BusinessRuleError("Name is forbidden")

    async def validate_update(self, existing: MockModel, obj_in: MockUpdate) -> None:
        self.validate_update_called = True
        if obj_in.name == "forbidden":
            raise BusinessRuleError("Name is forbidden")

    async def validate_delete(self, existing: MockModel) -> None:
        self.validate_delete_called = True
        if existing.name == "protected":
            raise BusinessRuleError("Cannot delete protected resource")

    async def before_create(self, obj_dict: Dict[str, Any]) -> Dict[str, Any]:
        self.before_create_called = True
        obj_dict["transformed"] = True
        return obj_dict

    async def before_update(self, existing: MockModel, obj_dict: Dict[str, Any]) -> Dict[str, Any]:
        self.before_update_called = True
        obj_dict["updated"] = True
        return obj_dict

    async def before_delete(self, existing: MockModel) -> None:
        self.before_delete_called = True

    async def after_create(self, created: MockModel) -> None:
        self.after_create_called = True

    async def after_update(self, updated: MockModel) -> None:
        self.after_update_called = True

    async def after_delete(self, id: UUID) -> None:
        self.after_delete_called = True


@pytest.fixture
def mock_repository():
    """Create a mock repository."""
    repo = AsyncMock(spec=BaseRepository)
    repo.model = MagicMock(__name__="MockModel")
    return repo


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return AsyncMock()


@pytest.fixture
def service(mock_repository, mock_db):
    """Create a test service instance."""
    return MockService(mock_repository, mock_db)


class TestBaseServiceGet:
    """Test get operations."""

    @pytest.mark.anyio
    async def test_get_success(self, service, mock_repository):
        """Test successful get operation."""
        test_id = uuid4()
        expected_obj = MockModel(test_id, "test")
        mock_repository.get.return_value = expected_obj

        result = await service.get(test_id)

        assert result == expected_obj
        mock_repository.get.assert_called_once_with(test_id)

    @pytest.mark.anyio
    async def test_get_not_found(self, service, mock_repository):
        """Test get when resource not found."""
        test_id = uuid4()
        mock_repository.get.return_value = None

        result = await service.get(test_id)

        assert result is None

    @pytest.mark.anyio
    async def test_get_repository_error(self, service, mock_repository):
        """Test get when repository raises error."""
        test_id = uuid4()
        mock_repository.get.side_effect = RepositoryError("Database error")

        with pytest.raises(ServiceError, match="Failed to retrieve"):
            await service.get(test_id)

    @pytest.mark.anyio
    async def test_get_or_404_success(self, service, mock_repository):
        """Test get_or_404 success."""
        test_id = uuid4()
        expected_obj = MockModel(test_id, "test")
        mock_repository.get.return_value = expected_obj

        result = await service.get_or_404(test_id)

        assert result == expected_obj

    @pytest.mark.anyio
    async def test_get_or_404_not_found(self, service, mock_repository):
        """Test get_or_404 raises ResourceNotFoundError."""
        test_id = uuid4()
        mock_repository.get.return_value = None

        with pytest.raises(ResourceNotFoundError, match="not found"):
            await service.get_or_404(test_id)

    @pytest.mark.anyio
    async def test_get_multi_success(self, service, mock_repository):
        """Test get_multi operation."""
        expected_objs = [
            MockModel(uuid4(), "test1"),
            MockModel(uuid4(), "test2"),
        ]
        mock_repository.get_multi.return_value = expected_objs

        result = await service.get_multi(skip=0, limit=100)

        assert result == expected_objs
        mock_repository.get_multi.assert_called_once_with(skip=0, limit=100)

    @pytest.mark.anyio
    async def test_get_multi_validation_error(self, service, mock_repository):
        """Test get_multi with invalid parameters."""
        mock_repository.get_multi.side_effect = RepoValidationError("Invalid limit")

        with pytest.raises(ValidationError, match="Invalid limit"):
            await service.get_multi(skip=0, limit=10000)


class TestBaseServiceCreate:
    """Test create operations."""

    @pytest.mark.anyio
    async def test_create_success(self, service, mock_repository):
        """Test successful create operation."""
        test_id = uuid4()
        create_data = MockCreate(name="test")
        created_obj = MockModel(test_id, "test")
        mock_repository.create.return_value = created_obj

        result = await service.create(create_data)

        assert result == created_obj
        assert service.validate_create_called
        assert service.before_create_called
        assert service.after_create_called

        # Verify repository called with transformed data
        call_args = mock_repository.create.call_args[0][0]
        assert call_args["name"] == "test"
        assert call_args["transformed"] is True

    @pytest.mark.anyio
    async def test_create_validation_error(self, service, mock_repository):
        """Test create with business rule validation failure."""
        create_data = MockCreate(name="forbidden")

        with pytest.raises(BusinessRuleError, match="forbidden"):
            await service.create(create_data)

        assert service.validate_create_called
        assert not service.before_create_called
        mock_repository.create.assert_not_called()

    @pytest.mark.anyio
    async def test_create_duplicate_error(self, service, mock_repository):
        """Test create with duplicate resource."""
        create_data = MockCreate(name="test")
        mock_repository.create.side_effect = DuplicateRecordError("Duplicate")

        with pytest.raises(DuplicateResourceError, match="already exists"):
            await service.create(create_data)

        assert service.validate_create_called
        assert service.before_create_called
        assert not service.after_create_called

    @pytest.mark.anyio
    async def test_create_repository_validation_error(self, service, mock_repository):
        """Test create with repository validation error."""
        create_data = MockCreate(name="test")
        mock_repository.create.side_effect = RepoValidationError("Invalid data")

        with pytest.raises(ValidationError, match="Invalid data"):
            await service.create(create_data)

    @pytest.mark.anyio
    async def test_create_repository_error(self, service, mock_repository):
        """Test create with generic repository error."""
        create_data = MockCreate(name="test")
        mock_repository.create.side_effect = RepositoryError("Database error")

        with pytest.raises(ServiceError, match="Failed to create"):
            await service.create(create_data)


class TestBaseServiceUpdate:
    """Test update operations."""

    @pytest.mark.anyio
    async def test_update_success(self, service, mock_repository):
        """Test successful update operation."""
        test_id = uuid4()
        existing_obj = MockModel(test_id, "old_name")
        updated_obj = MockModel(test_id, "new_name")
        update_data = MockUpdate(name="new_name")

        mock_repository.get.return_value = existing_obj
        mock_repository.update.return_value = updated_obj

        result = await service.update(test_id, update_data)

        assert result == updated_obj
        assert service.validate_update_called
        assert service.before_update_called
        assert service.after_update_called

        # Verify repository called with transformed data
        call_args = mock_repository.update.call_args[0]
        assert call_args[0] == test_id
        assert call_args[1]["name"] == "new_name"
        assert call_args[1]["updated"] is True

    @pytest.mark.anyio
    async def test_update_not_found(self, service, mock_repository):
        """Test update when resource not found."""
        test_id = uuid4()
        update_data = MockUpdate(name="new_name")
        mock_repository.get.return_value = None

        result = await service.update(test_id, update_data)

        assert result is None
        assert not service.validate_update_called
        mock_repository.update.assert_not_called()

    @pytest.mark.anyio
    async def test_update_validation_error(self, service, mock_repository):
        """Test update with business rule validation failure."""
        test_id = uuid4()
        existing_obj = MockModel(test_id, "old_name")
        update_data = MockUpdate(name="forbidden")
        mock_repository.get.return_value = existing_obj

        with pytest.raises(BusinessRuleError, match="forbidden"):
            await service.update(test_id, update_data)

        assert service.validate_update_called
        assert not service.before_update_called
        mock_repository.update.assert_not_called()

    @pytest.mark.anyio
    async def test_update_duplicate_error(self, service, mock_repository):
        """Test update creating duplicate."""
        test_id = uuid4()
        existing_obj = MockModel(test_id, "old_name")
        update_data = MockUpdate(name="duplicate")
        mock_repository.get.return_value = existing_obj
        mock_repository.update.side_effect = DuplicateRecordError("Duplicate")

        with pytest.raises(DuplicateResourceError, match="duplicate"):
            await service.update(test_id, update_data)


class TestBaseServiceDelete:
    """Test delete operations."""

    @pytest.mark.anyio
    async def test_delete_success(self, service, mock_repository):
        """Test successful delete operation."""
        test_id = uuid4()
        existing_obj = MockModel(test_id, "test")
        mock_repository.get.return_value = existing_obj
        mock_repository.delete.return_value = True

        result = await service.delete(test_id)

        assert result is True
        assert service.validate_delete_called
        assert service.before_delete_called
        assert service.after_delete_called
        mock_repository.delete.assert_called_once_with(test_id)

    @pytest.mark.anyio
    async def test_delete_not_found(self, service, mock_repository):
        """Test delete when resource not found."""
        test_id = uuid4()
        mock_repository.get.return_value = None

        result = await service.delete(test_id)

        assert result is False
        assert not service.validate_delete_called
        mock_repository.delete.assert_not_called()

    @pytest.mark.anyio
    async def test_delete_validation_error(self, service, mock_repository):
        """Test delete with business rule preventing deletion."""
        test_id = uuid4()
        existing_obj = MockModel(test_id, "protected")
        mock_repository.get.return_value = existing_obj

        with pytest.raises(BusinessRuleError, match="protected"):
            await service.delete(test_id)

        assert service.validate_delete_called
        assert not service.before_delete_called
        mock_repository.delete.assert_not_called()

    @pytest.mark.anyio
    async def test_delete_repository_error(self, service, mock_repository):
        """Test delete with repository error."""
        test_id = uuid4()
        existing_obj = MockModel(test_id, "test")
        mock_repository.get.return_value = existing_obj
        mock_repository.delete.side_effect = RepositoryError("Database error")

        with pytest.raises(ServiceError, match="Failed to delete"):
            await service.delete(test_id)


class TestBaseServiceUtilities:
    """Test utility methods."""

    @pytest.mark.anyio
    async def test_exists_true(self, service, mock_repository):
        """Test exists returns True."""
        test_id = uuid4()
        mock_repository.exists.return_value = True

        result = await service.exists(test_id)

        assert result is True
        mock_repository.exists.assert_called_once_with(test_id)

    @pytest.mark.anyio
    async def test_exists_false(self, service, mock_repository):
        """Test exists returns False."""
        test_id = uuid4()
        mock_repository.exists.return_value = False

        result = await service.exists(test_id)

        assert result is False

    @pytest.mark.anyio
    async def test_exists_error(self, service, mock_repository):
        """Test exists with repository error."""
        test_id = uuid4()
        mock_repository.exists.side_effect = RepositoryError("Database error")

        with pytest.raises(ServiceError, match="Failed to check existence"):
            await service.exists(test_id)

    @pytest.mark.anyio
    async def test_count_success(self, service, mock_repository):
        """Test count operation."""
        mock_repository.count.return_value = 42

        result = await service.count()

        assert result == 42
        mock_repository.count.assert_called_once()

    @pytest.mark.anyio
    async def test_count_error(self, service, mock_repository):
        """Test count with repository error."""
        mock_repository.count.side_effect = RepositoryError("Database error")

        with pytest.raises(ServiceError, match="Failed to count"):
            await service.count()


class TestBaseServiceHooks:
    """Test that hooks are properly called and can be overridden."""

    @pytest.mark.anyio
    async def test_all_create_hooks_called(self, service, mock_repository):
        """Test that all create hooks are called in correct order."""
        test_id = uuid4()
        create_data = MockCreate(name="test")
        created_obj = MockModel(test_id, "test")
        mock_repository.create.return_value = created_obj

        await service.create(create_data)

        assert service.validate_create_called
        assert service.before_create_called
        assert service.after_create_called

    @pytest.mark.anyio
    async def test_all_update_hooks_called(self, service, mock_repository):
        """Test that all update hooks are called in correct order."""
        test_id = uuid4()
        existing_obj = MockModel(test_id, "old")
        updated_obj = MockModel(test_id, "new")
        update_data = MockUpdate(name="new")

        mock_repository.get.return_value = existing_obj
        mock_repository.update.return_value = updated_obj

        await service.update(test_id, update_data)

        assert service.validate_update_called
        assert service.before_update_called
        assert service.after_update_called

    @pytest.mark.anyio
    async def test_all_delete_hooks_called(self, service, mock_repository):
        """Test that all delete hooks are called in correct order."""
        test_id = uuid4()
        existing_obj = MockModel(test_id, "test")
        mock_repository.get.return_value = existing_obj
        mock_repository.delete.return_value = True

        await service.delete(test_id)

        assert service.validate_delete_called
        assert service.before_delete_called
        assert service.after_delete_called

    @pytest.mark.anyio
    async def test_hooks_not_called_on_early_failure(self, service, mock_repository):
        """Test that later hooks are not called if early hook fails."""
        create_data = MockCreate(name="forbidden")

        with pytest.raises(BusinessRuleError):
            await service.create(create_data)

        assert service.validate_create_called
        assert not service.before_create_called
        assert not service.after_create_called


class TestBaseServiceExceptionHandling:
    """Test exception handling and error conversions."""

    @pytest.mark.anyio
    async def test_repository_error_converted_to_service_error(self, service, mock_repository):
        """Test that RepositoryError is converted to ServiceError."""
        test_id = uuid4()
        mock_repository.get.side_effect = RepositoryError("Low-level error")

        with pytest.raises(ServiceError):
            await service.get(test_id)

    @pytest.mark.anyio
    async def test_duplicate_record_error_converted(self, service, mock_repository):
        """Test that DuplicateRecordError is converted to DuplicateResourceError."""
        create_data = MockCreate(name="test")
        mock_repository.create.side_effect = DuplicateRecordError("Duplicate")

        with pytest.raises(DuplicateResourceError):
            await service.create(create_data)

    @pytest.mark.anyio
    async def test_repo_validation_error_converted(self, service, mock_repository):
        """Test that repo ValidationError is converted to service ValidationError."""
        create_data = MockCreate(name="test")
        mock_repository.create.side_effect = RepoValidationError("Invalid")

        with pytest.raises(ValidationError):
            await service.create(create_data)
