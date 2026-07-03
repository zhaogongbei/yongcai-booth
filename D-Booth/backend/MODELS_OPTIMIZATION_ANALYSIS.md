# D-Booth Backend Models Optimization Analysis

## Executive Summary

This document outlines the required optimizations for all SQLAlchemy models in the D-Booth backend.

---

## 1. Missing Database Indexes

### High Priority (Query Performance Critical)

| Table | Column(s) | Reason | Impact |
|-------|-----------|--------|--------|
| `signatures` | `session_id` | Foreign key, frequently joined | High |
| `survey_responses` | `event_id` | Foreign key, frequently filtered | High |
| `survey_responses` | `session_id` | Foreign key, frequently joined | High |
| `disclaimer_acceptances` | `event_id` | Foreign key, frequently filtered | High |
| `disclaimer_acceptances` | `session_id` | Foreign key, frequently joined | High |
| `events` | `start_date`, `end_date` | Range queries for active events | High |
| `events` | `status` | Status-based filtering | Medium |
| `templates` | `team_id` | Foreign key, list by team | High |
| `templates` | `is_public` | Public template discovery | Medium |
| `photo_sessions` | `email` | User lookup by email | Medium |
| `photo_sessions` | `event_id` | Foreign key (already indexed via __table_args__) | ✓ Exists |
| `shares` | `channel` | Filter by sharing channel | Medium |
| `shares` | `expires_at` | Cleanup expired shares | Medium |
| `ai_tasks` | `team_id` | Foreign key, list by team | High |
| `ai_tasks` | `status` | Filter by task status | High |
| `ai_tasks` | `workflow` | Filter by workflow type | Medium |
| `analytics_events` | `team_id` | Foreign key, analytics by team | High |
| `analytics_events` | `event_id` | Foreign key, analytics by event | High |
| `analytics_events` | `event_type` | Filter by event type | Medium |
| `analytics_events` | `created_at` | Time-series queries | High |
| `subscriptions` | `status` | Filter active subscriptions | Medium |
| `subscriptions` | `stripe_customer_id` | Webhook lookups | High |

### Composite Indexes Needed

| Table | Columns | Use Case |
|-------|---------|----------|
| `photo_sessions` | `event_id, created_at` | Event sessions timeline |
| `photos` | `event_id, created_at` | Event photos timeline |
| `print_jobs` | `status, created_at` | Queue management |
| `analytics_events` | `team_id, event_type, created_at` | Team analytics reports |
| `shares` | `photo_id, channel` | Photo sharing by channel |
| `ai_tasks` | `team_id, status, created_at` | Task queue by team |

---

## 2. Relationship Optimization Issues

### Models with Missing Relationships

| Model | Missing Relationship | Should Link To |
|-------|---------------------|----------------|
| `Signature` | No inverse from PhotoSession | PhotoSession needs `signatures` |
| `Survey` | No inverse relationships | SurveyResponse should link back |
| `SurveyResponse` | No relationship to Survey | Should have `survey` relationship |
| `SurveyResponse` | No relationship to PhotoSession | Should have `session` relationship |
| `Disclaimer` | No inverse relationships | DisclaimerAcceptance should link |
| `DisclaimerAcceptance` | No relationship to Disclaimer | Should have `disclaimer` relationship |
| `DisclaimerAcceptance` | No relationship to PhotoSession | Should have `session` relationship |
| `AITask` | No relationship to Team | Should have `team` relationship |
| `AnalyticsEvent` | No relationships | Should link to Team, Event |

### Lazy Loading Issues

**Current State**: Most relationships use `lazy="selectin"` or `lazy="joined"` ✓

**Potential Issues**:
- Event model has many `lazy="selectin"` child collections (photos, sessions) - could cause N+1 on large events
- Consider `lazy="noload"` for rarely-accessed collections with explicit loading when needed

**Recommended Pattern**:
- `lazy="joined"` - For single objects (1:1), small parent lookups
- `lazy="selectin"` - For small collections, frequently accessed
- `lazy="noload"` - For large collections, load explicitly with `selectinload()` in queries
- `lazy="raise"` - For development to catch accidental lazy loads

---

## 3. Soft Delete Support

### Models Requiring Soft Delete

All models should support soft deletes for:
- Data recovery
- Audit trails
- Referential integrity

**Fields to Add**:
```python
class SoftDeleteMixin:
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    deleted_by = Column(GUID(), ForeignKey("users.id"), nullable=True)
```

**Models Priority**:
- **Critical**: User, Team, Event, Photo, PhotoSession, Template
- **High**: PrintJob, Share, Subscription, Booth
- **Medium**: All others

**Implementation**:
- Add mixin to all models
- Create `is_deleted` index on each table
- Update queries to filter `is_deleted=False` by default
- Create manager methods: `soft_delete()`, `restore()`, `permanently_delete()`

---

## 4. Timestamp Consistency

### Current Status

✓ **Good**: `TimestampMixin` provides `created_at` and `updated_at` for most models

**Missing Timestamps**:
- All models using `TimestampMixin` have both fields ✓

**Inconsistencies**:
- `PhotoSession` has `started_at` and `completed_at` (domain-specific, acceptable)
- `PrintJob` has `printed_at` (domain-specific, acceptable)
- `Booth` has `last_heartbeat` (domain-specific, acceptable)

**Recommendation**: Current timestamp implementation is consistent ✓

---

## 5. Database Constraints Missing

### Unique Constraints Needed

| Table | Columns | Constraint |
|-------|---------|------------|
| `surveys` | `event_id` | Already has `unique=True` ✓ |
| `disclaimers` | `event_id` | Already has `unique=True` ✓ |
| `survey_responses` | `event_id, session_id` | One response per session per event |
| `disclaimer_acceptances` | `event_id, session_id` | One acceptance per session per event |

### Check Constraints Needed

| Table | Column | Constraint | Reason |
|-------|--------|------------|--------|
| `events` | `start_date, end_date` | `end_date > start_date` | Data integrity |
| `print_jobs` | `copies` | `copies > 0` | Cannot print 0 copies |
| `shares` | `view_count` | `view_count >= 0` | Cannot be negative |
| `ai_tasks` | `progress` | `progress >= 0 AND progress <= 100` | Percentage validation |
| `ai_tasks` | `estimated_cost, actual_cost` | `>= 0` | Cannot be negative |
| `templates` | `canvas_width, canvas_height` | `> 0` | Must have dimensions |
| `subscriptions` | `current_period_end` | `> current_period_start` | Period validation |
| `trigger_config` | `timeout, retry` | `>= 0` | Cannot be negative |

### Foreign Key Constraints Check

**Status**: All foreign keys properly defined ✓

**Missing `ondelete` Cascade Rules**:
- Most FKs should have explicit `ondelete="CASCADE"` or `ondelete="SET NULL"`
- Current: No explicit cascade rules (defaults to RESTRICT)

**Recommended**:
```python
# Parent deleted → children deleted
team_id = Column(GUID(), ForeignKey("teams.id", ondelete="CASCADE"))

# Parent deleted → orphan allowed
session_id = Column(GUID(), ForeignKey("photo_sessions.id", ondelete="SET NULL"))
```

---

## 6. Additional Recommendations

### Performance
1. Add database-level `DEFAULT` values where appropriate
2. Consider partial indexes for common filtered queries
3. Add GIN indexes for JSON columns if using PostgreSQL

### Data Integrity
1. Add email validation at database level (CHECK constraint)
2. Add URL format validation for `*_url` columns
3. Consider ENUM types for status fields at database level

### Maintainability
1. Create base mixins for common patterns
2. Document relationship loading strategies
3. Add model-level validation methods

---

## Next Steps

1. Create Alembic migration for missing indexes
2. Create Alembic migration for soft delete fields
3. Create Alembic migration for check constraints
4. Update model definitions with new fields and constraints
5. Create query helper utilities for soft delete filtering
6. Update existing queries to use optimized loading strategies
7. Run database performance tests
8. Document breaking changes (if any)

