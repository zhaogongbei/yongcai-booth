"""add optional template reference to print jobs

Revision ID: 009_add_print_job_template_id
Revises: 008_align_green_screen_persistence
Create Date: 2026-07-04 00:00:00.000000

"""

import sqlalchemy as sa

from alembic import op
from app.models.custom_types import GUID

# revision identifiers
revision = "009_add_print_job_template_id"
down_revision = "008_align_green_screen_persistence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("print_jobs", sa.Column("template_id", GUID(), nullable=True))
    op.create_foreign_key(
        "print_jobs_template_id_fkey",
        "print_jobs",
        "templates",
        ["template_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_print_job_template_id", "print_jobs", ["template_id"])


def downgrade() -> None:
    op.drop_index("ix_print_job_template_id", table_name="print_jobs")
    op.drop_constraint("print_jobs_template_id_fkey", "print_jobs", type_="foreignkey")
    op.drop_column("print_jobs", "template_id")
