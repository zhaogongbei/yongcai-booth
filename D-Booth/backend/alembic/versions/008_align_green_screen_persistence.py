"""align green screen persistence tables with API schema

Revision ID: 008_align_green_screen_persistence
Revises: 007_update_foreign_key_cascades
Create Date: 2026-07-03 00:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers
revision = "008_align_green_screen_persistence"
down_revision = "007_update_foreign_key_cascades"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "green_screen_settings",
        sa.Column("background_mode", sa.String(length=20), nullable=True, server_default="rotate"),
    )
    op.add_column(
        "green_screen_settings",
        sa.Column("current_background_index", sa.Integer(), nullable=True, server_default="0"),
    )
    op.add_column(
        "green_screen_backgrounds",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.add_column(
        "green_screen_backgrounds",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("green_screen_backgrounds", "updated_at")
    op.drop_column("green_screen_backgrounds", "created_at")
    op.drop_column("green_screen_settings", "current_background_index")
    op.drop_column("green_screen_settings", "background_mode")
