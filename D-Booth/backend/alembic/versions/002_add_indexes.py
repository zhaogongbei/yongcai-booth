"""Add database indexes for performance

Revision ID: 002_add_indexes
Revises: 001_initial
Create Date: 2026-06-22 17:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '002_add_indexes'
down_revision = '001_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The following indexes were removed because they already exist in 001_initial:
    #   ix_photos_event_id, ix_photos_session_id, ix_photos_event_created
    #   ix_team_members_team_id, ix_team_members_user_id, ix_team_members_team_user
    #   ix_events_team_id, ix_events_status, ix_events_team_status, ix_events_created_at
    #   ix_shares_expires_at, ix_shares_short_code
    #   ix_ai_tasks_status
    #   ix_print_jobs_photo_id, ix_print_jobs_status

    # Only truly new index not present in 001_initial
    op.create_index('ix_ai_tasks_created_at', 'ai_tasks', ['created_at'])


def downgrade() -> None:
    op.drop_index('ix_ai_tasks_created_at', 'ai_tasks')
