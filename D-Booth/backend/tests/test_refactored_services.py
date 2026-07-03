"""
Tests for BaseService and refactored services.

This file contains basic smoke tests to verify the refactored services
can be imported and instantiated correctly.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock
from uuid import uuid4

# Test imports
def test_base_service_import():
    """Test that BaseService can be imported."""
    from app.services.base_service import (
        BaseService,
        BusinessRuleError,
        ResourceNotFoundError,
        DuplicateResourceError,
        ValidationError,
        ServiceError,
    )
    assert BaseService is not None
    assert BusinessRuleError is not None


def test_refactored_services_import():
    """Test that all refactored services can be imported."""
    from app.services.user_service import UserService
    from app.services.event_service import EventService
    from app.services.team_service import TeamService
    from app.services.trigger_service import TriggerService
    from app.services.share_service import ShareService
    from app.services.template_service import TemplateService
    from app.services.photo_service import PhotoService
    from app.services.subscription_service import SubscriptionService
    from app.services.print_service import PrintService

    assert UserService is not None
    assert EventService is not None
    assert TeamService is not None
    assert TriggerService is not None
    assert ShareService is not None
    assert TemplateService is not None
    assert PhotoService is not None
    assert SubscriptionService is not None
    assert PrintService is not None


@pytest.mark.asyncio
async def test_user_service_instantiation():
    """Test that UserService can be instantiated."""
    from app.services.user_service import UserService

    # Mock database session
    mock_db = MagicMock()

    # Instantiate service
    service = UserService(mock_db)

    assert service is not None
    assert service.db == mock_db
    assert service.repository is not None


@pytest.mark.asyncio
async def test_base_service_crud_methods():
    """Test that BaseService CRUD methods exist."""
    from app.services.base_service import BaseService

    # Check that CRUD methods are defined
    assert hasattr(BaseService, 'get')
    assert hasattr(BaseService, 'get_or_404')
    assert hasattr(BaseService, 'get_multi')
    assert hasattr(BaseService, 'create')
    assert hasattr(BaseService, 'update')
    assert hasattr(BaseService, 'delete')
    assert hasattr(BaseService, 'exists')
    assert hasattr(BaseService, 'count')


@pytest.mark.asyncio
async def test_base_service_hooks():
    """Test that BaseService hooks are defined."""
    from app.services.base_service import BaseService

    # Check validation hooks
    assert hasattr(BaseService, 'validate_create')
    assert hasattr(BaseService, 'validate_update')
    assert hasattr(BaseService, 'validate_delete')

    # Check transformation hooks
    assert hasattr(BaseService, 'before_create')
    assert hasattr(BaseService, 'before_update')
    assert hasattr(BaseService, 'before_delete')

    # Check side-effect hooks
    assert hasattr(BaseService, 'after_create')
    assert hasattr(BaseService, 'after_update')
    assert hasattr(BaseService, 'after_delete')


@pytest.mark.asyncio
async def test_user_service_validates_email():
    """Test that UserService validates email uniqueness."""
    from app.services.user_service import UserService
    from app.services.base_service import BusinessRuleError
    from app.schemas.user import UserCreate

    # Mock database and repository
    mock_db = MagicMock()
    service = UserService(mock_db)

    # Mock repository method
    service.repository.email_exists = AsyncMock(return_value=True)

    # Create user data
    user_data = UserCreate(
        email="test@example.com",
        password="ValidPassword123!",
        full_name="Test User"
    )

    # Should raise BusinessRuleError for duplicate email
    with pytest.raises(BusinessRuleError, match="Email already registered"):
        await service.validate_create(user_data)


@pytest.mark.asyncio
async def test_event_service_validates_dates():
    """Test that EventService validates date range."""
    from app.services.event_service import EventService
    from app.services.base_service import ValidationError
    from app.schemas.event import EventCreate
    from datetime import datetime, timedelta

    # Mock database
    mock_db = MagicMock()
    service = EventService(mock_db)

    # Create event with invalid dates (end before start)
    event_data = EventCreate(
        team_id=uuid4(),
        name="Test Event",
        start_date=datetime.now() + timedelta(days=7),
        end_date=datetime.now() + timedelta(days=1),  # Before start
    )

    # Should raise ValidationError
    with pytest.raises(ValidationError, match="End date must be after start date"):
        await service.validate_create(event_data)


@pytest.mark.asyncio
async def test_team_service_generates_slug():
    """Test that TeamService generates slug from name."""
    from app.services.team_service import TeamService
    from app.schemas.team import TeamCreate

    # Mock database
    mock_db = MagicMock()
    service = TeamService(mock_db)
    service.repository.slug_exists = AsyncMock(return_value=False)

    # Create team without slug
    team_data = TeamCreate(
        name="My Awesome Team!",
        description="Test description"
    )

    # Should generate slug
    await service.validate_create(team_data)
    assert team_data.slug == "my-awesome-team"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
