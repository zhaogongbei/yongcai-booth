# Repository Layer Optimization Guide

## Overview

The D-Booth backend repository layer has been optimized with:

1. **Generic BaseRepository** with full CRUD operations
2. **Bulk operations** for batch processing (create, update, delete)
3. **Redis caching layer** with transparent decorators
4. **Unified error handling** with custom exceptions
5. **Query performance logging** for slow query detection
6. **Type safety** with complete type hints
7. **Comprehensive documentation** (Google-style docstrings)

---

## Architecture

```
app/repositories/
├── base.py                    # Generic BaseRepository with bulk operations
├── cache_decorator.py         # Redis cache decorators
├── user_repository.py         # User-specific queries (optimized)
├── event_repository.py        # Event-specific queries (optimized)
├── photo_repository.py        # Photo-specific queries (optimized)
└── __init__.py               # Exports
```

---

## BaseRepository

### Features

- **Generic CRUD**: Create, Read, Update, Delete operations
- **Bulk operations**: Batch create/update/delete with automatic batching
- **Error handling**: Custom exceptions for different failure modes
- **Performance logging**: Automatic slow query detection
- **Transaction support**: Context manager for explicit transactions

### Basic Usage

```python
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories import UserRepository

async def example(db: AsyncSession):
    user_repo = UserRepository(db)
    
    # Create single record
    user = await user_repo.create({
        "email": "user@example.com",
        "hashed_password": "...",
        "full_name": "John Doe"
    })
    
    # Get by ID
    user = await user_repo.get(user_id)
    
    # Update
    updated_user = await user_repo.update(user_id, {
        "full_name": "Jane Doe"
    })
    
    # Delete
    deleted = await user_repo.delete(user_id)
    
    # Pagination
    users = await user_repo.get_multi(skip=0, limit=50)
    
    # Count
    total = await user_repo.count()
```

### Bulk Operations

```python
# Bulk create (automatically batched)
users_data = [
    {"email": f"user{i}@example.com", "hashed_password": "...", "full_name": f"User {i}"}
    for i in range(1000)
]
created_users = await user_repo.bulk_create(users_data, batch_size=500)

# Bulk update
updates = [
    {"id": user1_id, "is_active": False},
    {"id": user2_id, "is_active": False},
    {"id": user3_id, "full_name": "Updated Name"},
]
count = await user_repo.bulk_update(updates)

# Bulk delete
deleted_count = await user_repo.bulk_delete([id1, id2, id3])
```

### Transaction Management

```python
# Explicit transaction control
async with user_repo.transaction():
    user = await user_repo.create(user_data)
    await team_repo.add_member(team_id, user.id)
    # Both operations committed together
```

---

## Caching Layer

### Redis Cache Decorator

The `@cached` decorator provides transparent caching for repository methods:

```python
from app.repositories.cache_decorator import cached, invalidate_cache

class UserRepository(BaseRepository[User]):
    
    @cached(ttl=600, key_builder=lambda self, email: f"user:email:{email}")
    async def get_by_email(self, email: str) -> Optional[User]:
        # Query implementation
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()
```

### Cache Invalidation

```python
class UserRepository(BaseRepository[User]):
    
    @invalidate_cache("user:*")
    async def create(self, obj_in: dict) -> User:
        return await super().create(obj_in)
    
    @invalidate_cache("user:{user_id}")
    async def update(self, user_id: UUID, obj_in: dict) -> User:
        return await super().update(user_id, obj_in)
```

### Cache Key Patterns

Pre-defined patterns in `CACHE_PATTERNS`:

```python
from app.repositories.cache_decorator import CACHE_PATTERNS

# Common patterns
CACHE_PATTERNS = {
    "event_all": "event:*",
    "event_by_id": "event:{event_id}:*",
    "team_events": "team:{team_id}:events:*",
    "photo_by_event": "event:{event_id}:photos:*",
}
```

---

## Error Handling

### Custom Exceptions

```python
from app.repositories import (
    RecordNotFoundError,      # Record doesn't exist
    DuplicateRecordError,     # Unique constraint violation
    ValidationError,          # Invalid input data
    DatabaseOperationError,   # Generic database error
)

try:
    user = await user_repo.create(user_data)
except DuplicateRecordError:
    # Handle duplicate email
    return {"error": "Email already exists"}
except ValidationError as e:
    # Handle validation error
    return {"error": str(e)}
except DatabaseOperationError:
    # Handle database failure
    return {"error": "Database operation failed"}
```

### Validation

The base repository validates input parameters:

```python
# Raises ValidationError
await user_repo.get_multi(skip=-1, limit=10)  # skip must be non-negative
await user_repo.get_multi(skip=0, limit=0)    # limit must be 1-1000
await user_repo.get_multi(skip=0, limit=2000) # limit must be 1-1000
```

---

## Performance Logging

### Automatic Slow Query Detection

The `@log_query_performance` decorator logs queries exceeding threshold:

```python
from app.repositories.base import log_query_performance

class UserRepository(BaseRepository[User]):
    
    @log_query_performance(threshold_ms=50.0)
    async def get_by_email(self, email: str) -> Optional[User]:
        # If this takes > 50ms, a warning is logged
        ...
```

### Log Output Examples

```
# Fast query (debug level)
DEBUG:app.repositories.base:get_by_email completed in 12.45ms

# Slow query (warning level)
WARNING:app.repositories.base:Slow query detected: get_by_email took 156.78ms (threshold: 50.0ms)

# Failed query (error level)
ERROR:app.repositories.base:Query failed: get_by_email after 23.45ms - IntegrityError(...)
```

---

## Repository-Specific Methods

### UserRepository

```python
user_repo = UserRepository(db)

# Find by email (cached for 10 minutes)
user = await user_repo.get_by_email("user@example.com")

# Find active user by email (not cached - always fresh)
user = await user_repo.get_by_email_active("user@example.com")

# Check email existence
exists = await user_repo.email_exists("user@example.com")

# Verify email
verified = await user_repo.verify_email(user_id)

# Deactivate account
deactivated = await user_repo.deactivate(user_id)
```

### EventRepository

```python
event_repo = EventRepository(db)

# Get by team (cached for 5 minutes)
events = await event_repo.get_by_team(team_id, skip=0, limit=50)

# Get by status (cached)
active_events = await event_repo.get_by_status(team_id, EventStatus.ACTIVE)

# Get active events (cached for 1 minute)
active = await event_repo.get_active_events(team_id)

# Get by date range (not cached - dynamic query)
events = await event_repo.get_by_date_range(
    team_id,
    start_from=datetime(2024, 1, 1),
    start_to=datetime(2024, 12, 31)
)

# Update status (invalidates caches)
event = await event_repo.update_status(event_id, EventStatus.COMPLETED)

# Count by team (cached for 10 minutes)
total = await event_repo.count_by_team(team_id)

# Count by status (cached for 5 minutes)
active_count = await event_repo.count_by_status(team_id, EventStatus.ACTIVE)
```

### PhotoRepository

```python
photo_repo = PhotoRepository(db)

# Get by event with eager loading (cached for 5 minutes)
photos = await photo_repo.get_by_event(event_id, skip=0, limit=100)

# Get by session (cached)
photos = await photo_repo.get_by_session(session_id)

# Get visible to user (not cached - complex query)
photos = await photo_repo.get_visible_to_user(user_id)

# Count by event (cached for 10 minutes)
count = await photo_repo.count_by_event(event_id)

# Count by team (cached)
count = await photo_repo.count_by_team(team_id)

# Get total storage usage (cached)
total_bytes = await photo_repo.get_total_file_size(event_id)

# Bulk create with cache invalidation
photos = await photo_repo.bulk_create(photos_data, batch_size=500)
```

### PhotoSessionRepository

```python
session_repo = PhotoSessionRepository(db)

# Get by event (cached for 5 minutes)
sessions = await session_repo.get_by_event(event_id)

# Get with photos eagerly loaded
session = await session_repo.get_with_photos(session_id)

# Get active sessions (cached for 1 minute)
active = await session_repo.get_active_sessions(event_id)

# Complete session (invalidates caches)
session = await session_repo.complete_session(session_id)

# Count by event (cached for 10 minutes)
count = await session_repo.count_by_event(event_id)
```

---

## Testing

### Running Tests

```bash
# Run all repository tests
pytest tests/test_repositories.py -v

# Run specific test class
pytest tests/test_repositories.py::TestBaseRepository -v

# Run with coverage
pytest tests/test_repositories.py --cov=app.repositories --cov-report=html
```

### Test Coverage

- ✅ CRUD operations (create, read, update, delete)
- ✅ Bulk operations (bulk_create, bulk_update, bulk_delete)
- ✅ Error handling (validation, duplicates, not found)
- ✅ Performance logging (slow queries, fast queries)
- ✅ Cache behavior (cache hit, cache miss)
- ✅ Repository-specific methods

---

## Performance Optimization Tips

### 1. Use Bulk Operations for Batch Processing

```python
# ❌ Bad: N database round-trips
for user_data in users_data:
    await user_repo.create(user_data)

# ✅ Good: Single batched operation
await user_repo.bulk_create(users_data, batch_size=500)
```

### 2. Leverage Caching for Read-Heavy Workloads

```python
# Frequently accessed data is automatically cached
user = await user_repo.get_by_email("user@example.com")  # Cache hit on subsequent calls
```

### 3. Use Eager Loading to Prevent N+1 Queries

```python
# PhotoRepository automatically eager loads relationships
photos = await photo_repo.get_by_event(event_id)
for photo in photos:
    print(photo.event.name)       # No additional query
    print(photo.session.email)    # No additional query
```

### 4. Adjust Cache TTL Based on Data Volatility

```python
# Frequently changing data: short TTL
@cached(ttl=60)  # 1 minute
async def get_active_sessions(self, event_id: UUID):
    ...

# Stable data: long TTL
@cached(ttl=3600)  # 1 hour
async def get_by_id(self, id: UUID):
    ...
```

### 5. Monitor Slow Queries

Check logs for slow query warnings and optimize accordingly:

```bash
# Filter slow queries from logs
grep "Slow query detected" logs/app.log
```

---

## Migration Guide

### Updating Existing Repositories

If you have existing repositories, update them to use the new features:

```python
# Before
class MyRepository:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(self, obj_in: dict):
        obj = MyModel(**obj_in)
        self.db.add(obj)
        await self.db.commit()
        return obj

# After
from app.repositories.base import BaseRepository, log_query_performance
from app.repositories.cache_decorator import cached, invalidate_cache

class MyRepository(BaseRepository[MyModel]):
    def __init__(self, db: AsyncSession):
        super().__init__(MyModel, db)
    
    @log_query_performance(threshold_ms=100.0)
    @cached(ttl=300)
    async def get_by_custom_field(self, value: str):
        # Custom query implementation
        ...
    
    @invalidate_cache("mymodel:*")
    async def create(self, obj_in: dict) -> MyModel:
        return await super().create(obj_in)
```

---

## Best Practices

1. **Always inherit from BaseRepository** for consistent behavior
2. **Use type hints** for all method signatures
3. **Add docstrings** (Google style) for public methods
4. **Set appropriate cache TTL** based on data volatility
5. **Invalidate caches** after mutations (create/update/delete)
6. **Log slow queries** with appropriate thresholds
7. **Use bulk operations** for batch processing
8. **Handle exceptions** at the service layer
9. **Test thoroughly** with unit tests
10. **Monitor performance** in production logs

---

## Configuration

### Redis Configuration

Set Redis URL in `.env`:

```bash
REDIS_URL=redis://localhost:6379/0
```

If Redis is unavailable, caching is automatically disabled (graceful fallback).

### Performance Thresholds

Adjust per-repository thresholds based on complexity:

```python
# Simple queries: low threshold
@log_query_performance(threshold_ms=50.0)
async def get(self, id: UUID):
    ...

# Complex queries: higher threshold
@log_query_performance(threshold_ms=300.0)
async def get_with_complex_joins(self, id: UUID):
    ...
```

---

## Troubleshooting

### Cache Not Working

Check Redis connection:

```python
from app.core.cache import RedisCache

client = await RedisCache.get_client()
if client:
    await client.ping()
    print("Redis connected")
else:
    print("Redis unavailable - caching disabled")
```

### Slow Queries

Enable query echo in development:

```python
# app/core/config.py
DEBUG = True  # Enables SQLAlchemy query logging
```

### Memory Issues with Bulk Operations

Reduce batch size:

```python
# If running out of memory
await repo.bulk_create(data, batch_size=100)  # Instead of 500
```

---

## Future Enhancements

Planned improvements:

1. **Distributed locking** for cache invalidation in multi-instance deployments
2. **Query result streaming** for very large result sets
3. **Automatic cache warming** on application startup
4. **Metrics collection** (Prometheus integration)
5. **Read replicas support** for read-heavy workloads
6. **Soft delete support** in BaseRepository

---

## Contributing

When adding new repositories:

1. Inherit from `BaseRepository[YourModel]`
2. Add model-specific query methods
3. Apply `@cached` decorator to read methods
4. Apply `@invalidate_cache` to mutation methods
5. Apply `@log_query_performance` to all methods
6. Write comprehensive docstrings
7. Add unit tests in `tests/test_repositories.py`
8. Update this documentation

---

## Support

For issues or questions:

- Check logs: `logs/app.log`
- Review test examples: `tests/test_repositories.py`
- Consult docstrings in code
- Monitor performance: Check for slow query warnings
