"""optimize models: soft delete, indexes, relationships

Revision ID: 006_optimize_models_soft_delete_indexes
Revises: 005_add_triggers_webhooks_and_green_screen
Create Date: 2026-07-02 00:00:00.000000

"""

import sqlalchemy as sa

from alembic import op
from app.models.types import GUID

# revision identifiers
revision = "006_optimize_models_soft_delete_indexes"
down_revision = "005_add_triggers_webhooks_and_green_screen"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ====================================================================
    # PART 1: Add soft delete fields to all tables
    # ====================================================================

    tables_for_soft_delete = [
        "users",
        "teams",
        "team_members",
        "events",
        "templates",
        "photo_sessions",
        "photos",
        "print_jobs",
        "shares",
        "ai_tasks",
        "subscriptions",
        "props",
        "booths",
        "trigger_configs",
        "webhooks",
        "signatures",
        "surveys",
        "survey_responses",
        "disclaimers",
        "disclaimer_acceptances",
    ]

    for table in tables_for_soft_delete:
        op.add_column(
            table, sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false")
        )
        op.add_column(table, sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
        op.add_column(table, sa.Column("deleted_by", GUID(), nullable=True))
        op.create_index(f"ix_{table}_is_deleted", table, ["is_deleted"])

    # ====================================================================
    # PART 2: Add missing indexes
    # ====================================================================

    # Signatures
    op.create_index("ix_signature_session_id", "signatures", ["session_id"])

    # Survey Responses - add survey_id FK and indexes
    op.add_column("survey_responses", sa.Column("survey_id", GUID(), nullable=True))
    op.create_foreign_key(
        "fk_survey_response_survey_id",
        "survey_responses",
        "surveys",
        ["survey_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_survey_response_event_id", "survey_responses", ["event_id"])
    op.create_index("ix_survey_response_session_id", "survey_responses", ["session_id"])
    op.create_index("ix_survey_response_survey_id", "survey_responses", ["survey_id"])
    op.create_unique_constraint(
        "uq_survey_response_event_session", "survey_responses", ["event_id", "session_id"]
    )

    # Disclaimer Acceptances - add disclaimer_id FK and indexes
    op.add_column("disclaimer_acceptances", sa.Column("disclaimer_id", GUID(), nullable=True))
    op.create_foreign_key(
        "fk_disclaimer_acceptance_disclaimer_id",
        "disclaimer_acceptances",
        "disclaimers",
        ["disclaimer_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_disclaimer_acceptance_event_id", "disclaimer_acceptances", ["event_id"])
    op.create_index("ix_disclaimer_acceptance_session_id", "disclaimer_acceptances", ["session_id"])
    op.create_index(
        "ix_disclaimer_acceptance_disclaimer_id", "disclaimer_acceptances", ["disclaimer_id"]
    )
    op.create_unique_constraint(
        "uq_disclaimer_acceptance_event_session",
        "disclaimer_acceptances",
        ["event_id", "session_id"],
    )

    # Events - additional indexes
    op.create_index("ix_event_status", "events", ["status"])
    op.create_index("ix_event_start_date", "events", ["start_date"])
    op.create_index("ix_event_end_date", "events", ["end_date"])
    op.create_index("ix_event_team_dates", "events", ["team_id", "start_date", "end_date"])

    # Templates
    op.create_index("ix_template_team_id", "templates", ["team_id"])
    op.create_index("ix_template_is_public", "templates", ["is_public"])

    # Photo Sessions
    op.create_index("ix_photo_session_event_id", "photo_sessions", ["event_id"])
    op.create_index("ix_photo_session_email", "photo_sessions", ["email"])
    op.create_index("ix_photo_session_event_created", "photo_sessions", ["event_id", "created_at"])

    # Photos
    op.create_index("ix_photo_event_created", "photos", ["event_id", "created_at"])

    # Print Jobs
    op.create_index("ix_print_job_status_created", "print_jobs", ["status", "created_at"])

    # Shares
    op.create_index("ix_share_photo_id", "shares", ["photo_id"])
    op.create_index("ix_share_channel", "shares", ["channel"])
    op.create_index("ix_share_expires_at", "shares", ["expires_at"])
    op.create_index("ix_share_photo_channel", "shares", ["photo_id", "channel"])

    # AI Tasks
    op.create_index("ix_ai_task_team_id", "ai_tasks", ["team_id"])
    op.create_index("ix_ai_task_status", "ai_tasks", ["status"])
    op.create_index("ix_ai_task_workflow", "ai_tasks", ["workflow"])
    op.create_index(
        "ix_ai_task_team_status_created", "ai_tasks", ["team_id", "status", "created_at"]
    )

    # Analytics Events
    op.create_index("ix_analytics_event_team_id", "analytics_events", ["team_id"])
    op.create_index("ix_analytics_event_event_id", "analytics_events", ["event_id"])
    op.create_index("ix_analytics_event_event_type", "analytics_events", ["event_type"])
    op.create_index("ix_analytics_event_created_at", "analytics_events", ["created_at"])
    op.create_index(
        "ix_analytics_event_team_type_created",
        "analytics_events",
        ["team_id", "event_type", "created_at"],
    )

    # Subscriptions
    op.create_index("ix_subscription_status", "subscriptions", ["status"])
    op.create_index("ix_subscription_stripe_customer_id", "subscriptions", ["stripe_customer_id"])


def downgrade() -> None:
    # ====================================================================
    # Remove indexes (reverse order)
    # ====================================================================

    # Subscriptions
    op.drop_index("ix_subscription_stripe_customer_id", "subscriptions")
    op.drop_index("ix_subscription_status", "subscriptions")

    # Analytics Events
    op.drop_index("ix_analytics_event_team_type_created", "analytics_events")
    op.drop_index("ix_analytics_event_created_at", "analytics_events")
    op.drop_index("ix_analytics_event_event_type", "analytics_events")
    op.drop_index("ix_analytics_event_event_id", "analytics_events")
    op.drop_index("ix_analytics_event_team_id", "analytics_events")

    # AI Tasks
    op.drop_index("ix_ai_task_team_status_created", "ai_tasks")
    op.drop_index("ix_ai_task_workflow", "ai_tasks")
    op.drop_index("ix_ai_task_status", "ai_tasks")
    op.drop_index("ix_ai_task_team_id", "ai_tasks")

    # Shares
    op.drop_index("ix_share_photo_channel", "shares")
    op.drop_index("ix_share_expires_at", "shares")
    op.drop_index("ix_share_channel", "shares")
    op.drop_index("ix_share_photo_id", "shares")

    # Print Jobs
    op.drop_index("ix_print_job_status_created", "print_jobs")

    # Photos
    op.drop_index("ix_photo_event_created", "photos")

    # Photo Sessions
    op.drop_index("ix_photo_session_event_created", "photo_sessions")
    op.drop_index("ix_photo_session_email", "photo_sessions")
    op.drop_index("ix_photo_session_event_id", "photo_sessions")

    # Templates
    op.drop_index("ix_template_is_public", "templates")
    op.drop_index("ix_template_team_id", "templates")

    # Events
    op.drop_index("ix_event_team_dates", "events")
    op.drop_index("ix_event_end_date", "events")
    op.drop_index("ix_event_start_date", "events")
    op.drop_index("ix_event_status", "events")

    # Disclaimer Acceptances
    op.drop_constraint("uq_disclaimer_acceptance_event_session", "disclaimer_acceptances")
    op.drop_index("ix_disclaimer_acceptance_disclaimer_id", "disclaimer_acceptances")
    op.drop_index("ix_disclaimer_acceptance_session_id", "disclaimer_acceptances")
    op.drop_index("ix_disclaimer_acceptance_event_id", "disclaimer_acceptances")
    op.drop_constraint("fk_disclaimer_acceptance_disclaimer_id", "disclaimer_acceptances")
    op.drop_column("disclaimer_acceptances", "disclaimer_id")

    # Survey Responses
    op.drop_constraint("uq_survey_response_event_session", "survey_responses")
    op.drop_index("ix_survey_response_survey_id", "survey_responses")
    op.drop_index("ix_survey_response_session_id", "survey_responses")
    op.drop_index("ix_survey_response_event_id", "survey_responses")
    op.drop_constraint("fk_survey_response_survey_id", "survey_responses")
    op.drop_column("survey_responses", "survey_id")

    # Signatures
    op.drop_index("ix_signature_session_id", "signatures")

    # ====================================================================
    # Remove soft delete fields
    # ====================================================================

    tables_for_soft_delete = [
        "users",
        "teams",
        "team_members",
        "events",
        "templates",
        "photo_sessions",
        "photos",
        "print_jobs",
        "shares",
        "ai_tasks",
        "subscriptions",
        "props",
        "booths",
        "trigger_configs",
        "webhooks",
        "signatures",
        "surveys",
        "survey_responses",
        "disclaimers",
        "disclaimer_acceptances",
    ]

    for table in tables_for_soft_delete:
        op.drop_index(f"ix_{table}_is_deleted", table)
        op.drop_column(table, "deleted_by")
        op.drop_column(table, "deleted_at")
        op.drop_column(table, "is_deleted")
