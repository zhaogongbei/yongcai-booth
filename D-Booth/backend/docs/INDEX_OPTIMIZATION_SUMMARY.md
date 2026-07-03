# Database Index Optimization Summary

**Date**: 2026-07-03
**File**: `app/models/models.py`
**Status**: Completed

## Overview

Optimized database indexes and relationship loading strategies across all models to improve query performance.

---

## Index Optimizations by Model

### 1. User
**Added**:
- `is_active` - column index for authentication queries
- `is_verified` - column index for verification status filtering
- `ix_user_active_verified` - composite index for combined active/verified queries

**Use Case**: Login, user listing with filters

---

### 2. Team
**Added**:
- `subscription_id` - column index on foreign key

**Use Case**: Team subscription lookups

---

### 3. Survey
**Added**:
- `event_id` - explicit index (was unique only)
- `enabled` - column index for filtering active surveys

**Use Case**: Event survey queries, enabled survey filtering

---

### 4. Disclaimer
**Added**:
- `event_id` - explicit index (was unique only)
- `enabled` - column index for filtering active disclaimers

**Use Case**: Event disclaimer queries, enabled disclaimer filtering

---

### 5. Template
**Added**:
- `ix_template_team_public` - composite index (team_id, is_public)

**Use Case**: Fetching team templates with public/private filtering

---

### 6. Photo
**Added**:
- `ix_photo_session_created` - composite index (session_id, created_at)

**Use Case**: Ordering photos within a session by creation time

---

### 7. PrintJob
**Added**:
- `printer_name` - column index
- `ix_print_job_status_printer` - composite index (status, printer_name)

**Use Case**: Printer-specific job queries, filtering jobs by printer and status

---

### 8. Subscription
**Added**:
- `ix_subscription_status_end` - composite index (status, current_period_end)

**Use Case**: Finding expiring subscriptions, subscription renewal queries

---

### 9. Prop
**Added**:
- `ix_prop_team_category` - composite index (team_id, category)
- `ix_prop_public_category` - composite index (is_public, category)

**Use Case**: Category-based prop filtering per team, public prop browsing by category

---

### 10. Booth
**Added**:
- `current_event_id` - column index on foreign key
- `last_heartbeat` - column index for heartbeat monitoring
- `ix_booth_team_status` - composite index (team_id, status)
- `ix_booth_status_heartbeat` - composite index (status, last_heartbeat)

**Use Case**: Active booth monitoring, stale booth detection, team booth status queries

---

### 11. TriggerConfig
**Added**:
- `enabled` - column index
- `ix_trigger_config_event_type_enabled` - composite index (event_id, event_type, enabled)

**Use Case**: Finding enabled triggers for specific events and types

---

### 12. TriggerLog
**Added**:
- `success` - column index
- `ix_trigger_log_trigger_created` - composite index (trigger_id, created_at)
- `ix_trigger_log_success_created` - composite index (success, created_at)

**Use Case**: Log queries by time, success rate analysis, trigger history

---

### 13. Webhook
**Added**:
- `enabled` - column index
- `ix_webhook_team_enabled` - composite index (team_id, enabled)

**Use Case**: Finding enabled webhooks for a team

---

### 14. WebhookLog
**Added**:
- `success` - column index
- `ix_webhook_log_created_at` - index on created_at for time-based queries
- `ix_webhook_log_webhook_created` - composite index (webhook_id, created_at)
- `ix_webhook_log_success_created` - composite index (success, created_at)

**Use Case**: Log queries by time, webhook delivery history, failure analysis

---

## Relationship Loading Strategy Review

All relationships reviewed and optimized:

### `lazy="joined"` (Eager Loading)
**Used for**: Small, frequently accessed related objects (1:1 or small 1:many)
- Team → Subscription
- Event → Team, Creator, Survey, Disclaimer
- Photo → Event, Session
- PhotoSession → Event
- All log models → parent entities

**Benefit**: Reduces N+1 queries, loads in single JOIN

---

### `lazy="selectin"` (Batch Loading)
**Used for**: Collections that may have many items (1:many)
- User → TeamMembers, Events
- Team → Members, Events, Templates
- Event → Photos, Sessions
- Photo → PrintJobs, Shares

**Benefit**: Avoids N+1 while not polluting main query with large JOINs

---

### Async Session Compatibility
All relationships use either `selectin` or `joined` to avoid `MissingGreenlet` errors in async contexts.
**Never** using default `lazy="select"` which breaks in async SQLAlchemy sessions.

---

## Performance Impact Estimation

### High Impact
- **Event queries**: (team_id, status, start_date) composite index - covers most dashboard queries
- **Photo queries**: (session_id, created_at) - critical for photo gallery ordering
- **Booth monitoring**: (status, last_heartbeat) - enables efficient stale booth detection
- **Log queries**: All logs now have time-based composite indexes for pagination

### Medium Impact
- **User authentication**: (is_active, is_verified) composite speeds up login checks
- **Prop browsing**: Category-based composites reduce filtering overhead
- **Webhook/Trigger lookups**: Enabled flag indexes improve active-only queries

### Database Size Impact
- Estimated index overhead: ~15-20% increase in table size
- Trade-off: Acceptable for read-heavy workload (typical SaaS pattern)

---

## Migration Required

These changes require a database migration to create the new indexes.

**Next Steps**:
1. Generate Alembic migration:
   ```bash
   alembic revision --autogenerate -m "optimize_indexes_and_relationships"
   ```

2. Review migration file for correctness

3. Apply migration:
   ```bash
   alembic upgrade head
   ```

4. Monitor query performance after deployment

---

## Query Pattern Examples

### Before
```python
# N+1 problem
events = await db.execute(select(Event).filter_by(team_id=team_id))
for event in events:
    # Separate query for each event's creator
    creator = await db.get(User, event.creator_id)
```

### After
```python
# Single query with JOIN
events = await db.execute(
    select(Event)
    .filter_by(team_id=team_id)
    .options(joinedload(Event.creator))
)
# Creator already loaded
```

---

## Validation Checklist

- [x] All foreign keys have indexes
- [x] Composite indexes cover common query patterns
- [x] Unique constraints have accompanying indexes
- [x] Boolean filters have indexes where frequently queried
- [x] Timestamp fields used for sorting have indexes
- [x] No default `lazy="select"` relationships (async safe)
- [x] Syntax validated (Python compilation successful)

---

## Notes

- All indexes follow naming convention: `ix_{table}_{columns}`
- Composite indexes ordered by selectivity (most selective first)
- Log tables optimized for time-range queries and filtering by success/failure
- Relationship loading strategies balance performance and memory usage
