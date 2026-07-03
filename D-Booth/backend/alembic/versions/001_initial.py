"""Initial schema with all tables and indexes

Revision ID: 001_initial
Revises:
Create Date: 2026-06-22 18:30:00.000000

"""

import sqlalchemy as sa

from alembic import op
from app.models.types import GUID

# revision identifiers
revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    dialect = op.get_context().dialect.name

    if dialect == "postgresql":
        op.execute("CREATE TYPE userrole AS ENUM ('admin', 'owner', 'member')")
        op.execute(
            "CREATE TYPE eventstatus AS ENUM ('draft', 'scheduled', 'active', 'completed', 'cancelled')"
        )
        op.execute(
            "CREATE TYPE printjobstatus AS ENUM ('pending', 'queued', 'printing', 'completed', 'failed', 'cancelled')"
        )
        op.execute(
            "CREATE TYPE subscriptionstatus AS ENUM ('active', 'inactive', 'cancelled', 'past_due')"
        )

    # Create subscriptions table
    op.create_table(
        "subscriptions",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("plan_name", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=True),
        sa.Column("stripe_subscription_id", sa.String(length=255), nullable=True),
        sa.Column("stripe_customer_id", sa.String(length=255), nullable=True),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_at_period_end", sa.Boolean(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stripe_subscription_id"),
    )

    # Create users table
    op.create_table(
        "users",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("is_verified", sa.Boolean(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    # Create teams table
    op.create_table(
        "teams",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("subscription_id", GUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["subscription_id"],
            ["subscriptions.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_teams_slug"), "teams", ["slug"], unique=True)

    # Create team_members table
    op.create_table(
        "team_members",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("team_id", GUID(), nullable=False),
        sa.Column("user_id", GUID(), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["team_id"],
            ["teams.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_team_members_team_id", "team_members", ["team_id"])
    op.create_index("ix_team_members_user_id", "team_members", ["user_id"])
    op.create_index(
        "ix_team_members_team_user", "team_members", ["team_id", "user_id"], unique=True
    )

    # Create events table
    op.create_table(
        "events",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("team_id", GUID(), nullable=False),
        sa.Column("creator_id", GUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=True),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("venue_name", sa.String(length=255), nullable=True),
        sa.Column("venue_address", sa.Text(), nullable=True),
        sa.Column("settings", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["creator_id"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["team_id"],
            ["teams.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_events_team_id", "events", ["team_id"])
    op.create_index("ix_events_creator_id", "events", ["creator_id"])
    op.create_index("ix_events_status", "events", ["status"])
    op.create_index("ix_events_team_status", "events", ["team_id", "status"])
    op.create_index("ix_events_created_at", "events", ["created_at"])

    # Create templates table
    op.create_table(
        "templates",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("team_id", GUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("size", sa.String(length=50), nullable=True),
        sa.Column("canvas_width", sa.Numeric(), nullable=True),
        sa.Column("canvas_height", sa.Numeric(), nullable=True),
        sa.Column("layers", sa.JSON(), nullable=True),
        sa.Column("thumbnail_url", sa.String(length=500), nullable=True),
        sa.Column("is_public", sa.Boolean(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["team_id"],
            ["teams.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create photo_sessions table
    op.create_table(
        "photo_sessions",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("event_id", GUID(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column(
            "started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["events.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create photos table
    op.create_table(
        "photos",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("event_id", GUID(), nullable=False),
        sa.Column("session_id", GUID(), nullable=True),
        sa.Column("original_url", sa.String(length=500), nullable=False),
        sa.Column("processed_url", sa.String(length=500), nullable=True),
        sa.Column("thumbnail_url", sa.String(length=500), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["events.id"],
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["photo_sessions.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_photos_event_id", "photos", ["event_id"])
    op.create_index("ix_photos_session_id", "photos", ["session_id"])
    op.create_index("ix_photos_event_created", "photos", ["event_id", "created_at"])

    # Create print_jobs table
    op.create_table(
        "print_jobs",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("photo_id", GUID(), nullable=False),
        sa.Column("printer_name", sa.String(length=255), nullable=True),
        sa.Column("copies", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("printed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["photo_id"],
            ["photos.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_print_jobs_photo_id", "print_jobs", ["photo_id"])
    op.create_index("ix_print_jobs_status", "print_jobs", ["status"])

    # Create shares table
    op.create_table(
        "shares",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("photo_id", GUID(), nullable=False),
        sa.Column("channel", sa.String(length=50), nullable=False),
        sa.Column("recipient", sa.String(length=255), nullable=True),
        sa.Column("short_code", sa.String(length=20), unique=True, index=True),
        sa.Column("full_url", sa.String(length=500), nullable=True),
        sa.Column("view_count", sa.Integer(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["photo_id"],
            ["photos.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_shares_short_code", "shares", ["short_code"], unique=True)
    op.create_index("ix_shares_expires_at", "shares", ["expires_at"])

    # Create ai_tasks table
    op.create_table(
        "ai_tasks",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("team_id", GUID(), nullable=False),
        sa.Column("workflow", sa.String(length=50), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("parameters", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=True),
        sa.Column("progress", sa.Numeric(), nullable=True),
        sa.Column("result_url", sa.String(length=500), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("estimated_cost", sa.Numeric(), nullable=True),
        sa.Column("actual_cost", sa.Numeric(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["team_id"],
            ["teams.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_tasks_team_id", "ai_tasks", ["team_id"])
    op.create_index("ix_ai_tasks_status", "ai_tasks", ["status"])

    # Create analytics_events table
    op.create_table(
        "analytics_events",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("team_id", GUID(), nullable=False),
        sa.Column("event_id", GUID(), nullable=True),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("properties", sa.JSON(), nullable=True),
        sa.Column("user_id", GUID(), nullable=True),
        sa.Column("session_id", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["events.id"],
        ),
        sa.ForeignKeyConstraint(
            ["team_id"],
            ["teams.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    dialect = op.get_context().dialect.name

    # Drop tables
    op.drop_table("analytics_events")
    op.drop_table("ai_tasks")
    op.drop_index("ix_shares_expires_at", "shares")
    op.drop_index("ix_shares_short_code", "shares")
    op.drop_table("shares")
    op.drop_index("ix_print_jobs_status", "print_jobs")
    op.drop_index("ix_print_jobs_photo_id", "print_jobs")
    op.drop_table("print_jobs")
    op.drop_index("ix_photos_event_created", "photos")
    op.drop_index("ix_photos_session_id", "photos")
    op.drop_index("ix_photos_event_id", "photos")
    op.drop_table("photos")
    op.drop_table("photo_sessions")
    op.drop_table("templates")
    op.drop_index("ix_events_created_at", "events")
    op.drop_index("ix_events_team_status", "events")
    op.drop_index("ix_events_status", "events")
    op.drop_index("ix_events_creator_id", "events")
    op.drop_index("ix_events_team_id", "events")
    op.drop_table("events")
    op.drop_index("ix_team_members_team_user", "team_members")
    op.drop_index("ix_team_members_user_id", "team_members")
    op.drop_index("ix_team_members_team_id", "team_members")
    op.drop_table("team_members")
    op.drop_index(op.f("ix_teams_slug"), "teams")
    op.drop_table("teams")
    op.drop_index(op.f("ix_users_email"), "users")
    op.drop_table("users")
    op.drop_table("subscriptions")

    if dialect == "postgresql":
        op.execute("DROP TYPE IF EXISTS subscriptionstatus")
        op.execute("DROP TYPE IF EXISTS printjobstatus")
        op.execute("DROP TYPE IF EXISTS eventstatus")
        op.execute("DROP TYPE IF EXISTS userrole")
