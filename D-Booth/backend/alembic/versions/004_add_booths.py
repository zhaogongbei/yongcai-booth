"""Add booths and related tables (props, surveys, disclaimers, green_screen, etc.)

Revision ID: 004_add_booths
Revises: 003_add_missing_indexes
Create Date: 2026-07-01 12:00:00.000000

"""

import sqlalchemy as sa

from alembic import op
from app.models.types import GUID

# revision identifiers
revision = "004_add_booths"
down_revision = "003_add_missing_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    dialect = op.get_context().dialect.name

    if dialect == "postgresql":
        op.execute(
            "CREATE TYPE propcategory AS ENUM ('节日', '婚礼', '生日', '动物', '眼镜', '帽子', '胡须', '自定义')"
        )
        op.execute("CREATE TYPE boothstatus AS ENUM ('online', 'offline', 'busy', 'error')")
        op.execute(
            "CREATE TYPE triggertype AS ENUM ('session_start', 'countdown_start', 'capture_start', 'file_download', 'processing_start', 'sharing_screen', 'session_end', 'printing')"
        )
        op.execute("CREATE TYPE triggeraction AS ENUM ('http_callback', 'app_execute')")

    # Add event_type to events table if not exists
    if dialect == "postgresql":
        op.execute("ALTER TABLE events ADD COLUMN IF NOT EXISTS event_type VARCHAR(50)")
    else:
        try:
            op.add_column("events", sa.Column("event_type", sa.String(length=50), nullable=True))
        except Exception:
            pass  # Column may already exist (non-PostgreSQL fallback)

    # Create booths table
    op.create_table(
        "booths",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("team_id", GUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("device_id", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=True),
        sa.Column("version", sa.String(length=50), nullable=True),
        sa.Column("last_heartbeat", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ip_address", sa.String(length=50), nullable=True),
        sa.Column("os_info", sa.String(length=255), nullable=True),
        sa.Column("current_event_id", GUID(), nullable=True),
        sa.Column("config_hash", sa.String(length=64), nullable=True),
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
            ["current_event_id"],
            ["events.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_booths_team_id", "booths", ["team_id"])
    op.create_index("ix_booths_device_id", "booths", ["device_id"], unique=True)
    op.create_index("ix_booths_status", "booths", ["status"])

    # Create props table
    op.create_table(
        "props",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("team_id", GUID(), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("image_url", sa.String(length=500), nullable=False),
        sa.Column("thumbnail_url", sa.String(length=500), nullable=False),
        sa.Column("is_public", sa.Boolean(), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True),
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
    op.create_index("ix_props_team_id", "props", ["team_id"])
    op.create_index("ix_props_category", "props", ["category"])
    op.create_index("ix_props_is_public", "props", ["is_public"])

    # Create surveys table
    op.create_table(
        "surveys",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("event_id", GUID(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("questions", sa.JSON(), nullable=True),
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
        sa.UniqueConstraint("event_id"),
    )

    # Create survey_responses table
    op.create_table(
        "survey_responses",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("event_id", GUID(), nullable=False),
        sa.Column("session_id", GUID(), nullable=False),
        sa.Column("answers", sa.JSON(), nullable=True),
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

    # Create disclaimers table
    op.create_table(
        "disclaimers",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("event_id", GUID(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("require_signature", sa.Boolean(), nullable=True),
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
        sa.UniqueConstraint("event_id"),
    )

    # Create disclaimer_acceptances table
    op.create_table(
        "disclaimer_acceptances",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("event_id", GUID(), nullable=False),
        sa.Column("session_id", GUID(), nullable=False),
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

    # Create signatures table
    op.create_table(
        "signatures",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("session_id", GUID(), nullable=False),
        sa.Column("signature_url", sa.String(length=500), nullable=False),
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
            ["session_id"],
            ["photo_sessions.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    dialect = op.get_context().dialect.name

    op.drop_table("signatures")
    op.drop_table("disclaimer_acceptances")
    op.drop_table("disclaimers")
    op.drop_table("survey_responses")
    op.drop_table("surveys")
    op.drop_table("props")
    op.drop_index("ix_booths_status", "booths")
    op.drop_index("ix_booths_device_id", "booths")
    op.drop_index("ix_booths_team_id", "booths")
    op.drop_table("booths")

    if dialect == "postgresql":
        op.execute("DROP TYPE IF EXISTS triggeraction")
        op.execute("DROP TYPE IF EXISTS triggertype")
        op.execute("DROP TYPE IF EXISTS boothstatus")
        op.execute("DROP TYPE IF EXISTS propcategory")
