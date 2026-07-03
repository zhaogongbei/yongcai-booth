"""Add missing database indexes for performance

Revision ID: 003_add_missing_indexes
Revises: 002_add_indexes
Create Date: 2026-06-26 12:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers
revision = "003_add_missing_indexes"
down_revision = "002_add_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # analytics_events — previously had ZERO indexes; all queries were full-table scans
    op.create_index("ix_analytics_events_team_id", "analytics_events", ["team_id"])
    op.create_index(
        "ix_analytics_events_team_created", "analytics_events", ["team_id", "created_at"]
    )
    op.create_index("ix_analytics_events_event_id", "analytics_events", ["event_id"])
    op.create_index("ix_analytics_events_event_type", "analytics_events", ["event_type"])

    # templates — missing team_id and is_public indexes
    op.create_index("ix_templates_team_id", "templates", ["team_id"])
    op.create_index("ix_templates_is_public", "templates", ["is_public"])

    # photo_sessions — missing event_id index
    op.create_index("ix_photo_sessions_event_id", "photo_sessions", ["event_id"])

    # shares — missing photo_id and channel indexes
    op.create_index("ix_shares_photo_id", "shares", ["photo_id"])
    op.create_index("ix_shares_channel", "shares", ["channel"])

    # print_jobs — missing created_at for ordered pagination
    op.create_index("ix_print_jobs_created_at", "print_jobs", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_print_jobs_created_at", "print_jobs")
    op.drop_index("ix_shares_channel", "shares")
    op.drop_index("ix_shares_photo_id", "shares")
    op.drop_index("ix_photo_sessions_event_id", "photo_sessions")
    op.drop_index("ix_templates_is_public", "templates")
    op.drop_index("ix_templates_team_id", "templates")
    op.drop_index("ix_analytics_events_event_type", "analytics_events")
    op.drop_index("ix_analytics_events_event_id", "analytics_events")
    op.drop_index("ix_analytics_events_team_created", "analytics_events")
    op.drop_index("ix_analytics_events_team_id", "analytics_events")
