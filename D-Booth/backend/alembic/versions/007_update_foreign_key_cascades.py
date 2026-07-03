"""update foreign key constraints with cascade rules

Revision ID: 007_update_foreign_key_cascades
Revises: 006_optimize_models_soft_delete_indexes
Create Date: 2026-07-02 00:01:00.000000

"""
from alembic import op
import sqlalchemy as sa
from app.models.types import GUID

# revision identifiers
revision = '007_update_foreign_key_cascades'
down_revision = '006_optimize_models_soft_delete_indexes'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Update foreign key constraints to add proper CASCADE or SET NULL rules.

    Pattern:
    - Parent-child relationship where child makes no sense without parent: CASCADE
    - Optional relationship where orphan is acceptable: SET NULL
    """

    # Teams - subscription can be removed
    op.drop_constraint('teams_subscription_id_fkey', 'teams', type_='foreignkey')
    op.create_foreign_key('teams_subscription_id_fkey', 'teams', 'subscriptions', ['subscription_id'], ['id'], ondelete='SET NULL')

    # Team Members - cascade delete when team or user deleted
    op.drop_constraint('team_members_team_id_fkey', 'team_members', type_='foreignkey')
    op.drop_constraint('team_members_user_id_fkey', 'team_members', type_='foreignkey')
    op.create_foreign_key('team_members_team_id_fkey', 'team_members', 'teams', ['team_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('team_members_user_id_fkey', 'team_members', 'users', ['user_id'], ['id'], ondelete='CASCADE')

    # Signatures - cascade delete when session deleted
    op.drop_constraint('signatures_session_id_fkey', 'signatures', type_='foreignkey')
    op.create_foreign_key('signatures_session_id_fkey', 'signatures', 'photo_sessions', ['session_id'], ['id'], ondelete='CASCADE')

    # Surveys - cascade delete when event deleted
    op.drop_constraint('surveys_event_id_fkey', 'surveys', type_='foreignkey')
    op.create_foreign_key('surveys_event_id_fkey', 'surveys', 'events', ['event_id'], ['id'], ondelete='CASCADE')

    # Survey Responses - cascade delete when event or session deleted
    op.drop_constraint('survey_responses_event_id_fkey', 'survey_responses', type_='foreignkey')
    op.drop_constraint('survey_responses_session_id_fkey', 'survey_responses', type_='foreignkey')
    op.create_foreign_key('survey_responses_event_id_fkey', 'survey_responses', 'events', ['event_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('survey_responses_session_id_fkey', 'survey_responses', 'photo_sessions', ['session_id'], ['id'], ondelete='CASCADE')

    # Disclaimers - cascade delete when event deleted
    op.drop_constraint('disclaimers_event_id_fkey', 'disclaimers', type_='foreignkey')
    op.create_foreign_key('disclaimers_event_id_fkey', 'disclaimers', 'events', ['event_id'], ['id'], ondelete='CASCADE')

    # Disclaimer Acceptances - cascade delete
    op.drop_constraint('disclaimer_acceptances_event_id_fkey', 'disclaimer_acceptances', type_='foreignkey')
    op.drop_constraint('disclaimer_acceptances_session_id_fkey', 'disclaimer_acceptances', type_='foreignkey')
    op.create_foreign_key('disclaimer_acceptances_event_id_fkey', 'disclaimer_acceptances', 'events', ['event_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('disclaimer_acceptances_session_id_fkey', 'disclaimer_acceptances', 'photo_sessions', ['session_id'], ['id'], ondelete='CASCADE')

    # Events - cascade on team, SET NULL on creator
    op.drop_constraint('events_team_id_fkey', 'events', type_='foreignkey')
    op.drop_constraint('events_creator_id_fkey', 'events', type_='foreignkey')
    op.create_foreign_key('events_team_id_fkey', 'events', 'teams', ['team_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('events_creator_id_fkey', 'events', 'users', ['creator_id'], ['id'], ondelete='SET NULL')

    # Templates - cascade when team deleted
    op.drop_constraint('templates_team_id_fkey', 'templates', type_='foreignkey')
    op.create_foreign_key('templates_team_id_fkey', 'templates', 'teams', ['team_id'], ['id'], ondelete='CASCADE')

    # Photo Sessions - cascade when event deleted
    op.drop_constraint('photo_sessions_event_id_fkey', 'photo_sessions', type_='foreignkey')
    op.create_foreign_key('photo_sessions_event_id_fkey', 'photo_sessions', 'events', ['event_id'], ['id'], ondelete='CASCADE')

    # Photos - cascade on event, SET NULL on session
    op.drop_constraint('photos_event_id_fkey', 'photos', type_='foreignkey')
    op.drop_constraint('photos_session_id_fkey', 'photos', type_='foreignkey')
    op.create_foreign_key('photos_event_id_fkey', 'photos', 'events', ['event_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('photos_session_id_fkey', 'photos', 'photo_sessions', ['session_id'], ['id'], ondelete='SET NULL')

    # Print Jobs - cascade when photo deleted
    op.drop_constraint('print_jobs_photo_id_fkey', 'print_jobs', type_='foreignkey')
    op.create_foreign_key('print_jobs_photo_id_fkey', 'print_jobs', 'photos', ['photo_id'], ['id'], ondelete='CASCADE')

    # Shares - cascade when photo deleted
    op.drop_constraint('shares_photo_id_fkey', 'shares', type_='foreignkey')
    op.create_foreign_key('shares_photo_id_fkey', 'shares', 'photos', ['photo_id'], ['id'], ondelete='CASCADE')

    # AI Tasks - cascade when team deleted
    op.drop_constraint('ai_tasks_team_id_fkey', 'ai_tasks', type_='foreignkey')
    op.create_foreign_key('ai_tasks_team_id_fkey', 'ai_tasks', 'teams', ['team_id'], ['id'], ondelete='CASCADE')

    # Analytics Events - cascade when team or event deleted
    op.drop_constraint('analytics_events_team_id_fkey', 'analytics_events', type_='foreignkey')
    op.drop_constraint('analytics_events_event_id_fkey', 'analytics_events', type_='foreignkey')
    op.create_foreign_key('analytics_events_team_id_fkey', 'analytics_events', 'teams', ['team_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('analytics_events_event_id_fkey', 'analytics_events', 'events', ['event_id'], ['id'], ondelete='CASCADE')

    # Props - cascade when team deleted (nullable team_id allows public props)
    op.drop_constraint('props_team_id_fkey', 'props', type_='foreignkey')
    op.create_foreign_key('props_team_id_fkey', 'props', 'teams', ['team_id'], ['id'], ondelete='CASCADE')

    # Booths - cascade on team, SET NULL on current_event
    op.drop_constraint('booths_team_id_fkey', 'booths', type_='foreignkey')
    op.drop_constraint('booths_current_event_id_fkey', 'booths', type_='foreignkey')
    op.create_foreign_key('booths_team_id_fkey', 'booths', 'teams', ['team_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('booths_current_event_id_fkey', 'booths', 'events', ['current_event_id'], ['id'], ondelete='SET NULL')

    # Trigger Configs - cascade when event deleted
    op.drop_constraint('trigger_configs_event_id_fkey', 'trigger_configs', type_='foreignkey')
    op.create_foreign_key('trigger_configs_event_id_fkey', 'trigger_configs', 'events', ['event_id'], ['id'], ondelete='CASCADE')

    # Trigger Logs - cascade when trigger or event deleted
    op.drop_constraint('trigger_logs_trigger_id_fkey', 'trigger_logs', type_='foreignkey')
    op.drop_constraint('trigger_logs_event_id_fkey', 'trigger_logs', type_='foreignkey')
    op.create_foreign_key('trigger_logs_trigger_id_fkey', 'trigger_logs', 'trigger_configs', ['trigger_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('trigger_logs_event_id_fkey', 'trigger_logs', 'events', ['event_id'], ['id'], ondelete='CASCADE')

    # Webhooks - cascade when team deleted
    op.drop_constraint('webhooks_team_id_fkey', 'webhooks', type_='foreignkey')
    op.create_foreign_key('webhooks_team_id_fkey', 'webhooks', 'teams', ['team_id'], ['id'], ondelete='CASCADE')

    # Webhook Logs - cascade when webhook deleted
    op.drop_constraint('webhook_logs_webhook_id_fkey', 'webhook_logs', type_='foreignkey')
    op.create_foreign_key('webhook_logs_webhook_id_fkey', 'webhook_logs', 'webhooks', ['webhook_id'], ['id'], ondelete='CASCADE')


def downgrade() -> None:
    """
    Revert foreign key constraints to their original state (no explicit cascade rules).
    """

    # Reverse all changes - drop CASCADE/SET NULL and recreate without ondelete

    # Webhook Logs
    op.drop_constraint('webhook_logs_webhook_id_fkey', 'webhook_logs', type_='foreignkey')
    op.create_foreign_key('webhook_logs_webhook_id_fkey', 'webhook_logs', 'webhooks', ['webhook_id'], ['id'])

    # Webhooks
    op.drop_constraint('webhooks_team_id_fkey', 'webhooks', type_='foreignkey')
    op.create_foreign_key('webhooks_team_id_fkey', 'webhooks', 'teams', ['team_id'], ['id'])

    # Trigger Logs
    op.drop_constraint('trigger_logs_event_id_fkey', 'trigger_logs', type_='foreignkey')
    op.drop_constraint('trigger_logs_trigger_id_fkey', 'trigger_logs', type_='foreignkey')
    op.create_foreign_key('trigger_logs_event_id_fkey', 'trigger_logs', 'events', ['event_id'], ['id'])
    op.create_foreign_key('trigger_logs_trigger_id_fkey', 'trigger_logs', 'trigger_configs', ['trigger_id'], ['id'])

    # Trigger Configs
    op.drop_constraint('trigger_configs_event_id_fkey', 'trigger_configs', type_='foreignkey')
    op.create_foreign_key('trigger_configs_event_id_fkey', 'trigger_configs', 'events', ['event_id'], ['id'])

    # Booths
    op.drop_constraint('booths_current_event_id_fkey', 'booths', type_='foreignkey')
    op.drop_constraint('booths_team_id_fkey', 'booths', type_='foreignkey')
    op.create_foreign_key('booths_current_event_id_fkey', 'booths', 'events', ['current_event_id'], ['id'])
    op.create_foreign_key('booths_team_id_fkey', 'booths', 'teams', ['team_id'], ['id'])

    # Props
    op.drop_constraint('props_team_id_fkey', 'props', type_='foreignkey')
    op.create_foreign_key('props_team_id_fkey', 'props', 'teams', ['team_id'], ['id'])

    # Analytics Events
    op.drop_constraint('analytics_events_event_id_fkey', 'analytics_events', type_='foreignkey')
    op.drop_constraint('analytics_events_team_id_fkey', 'analytics_events', type_='foreignkey')
    op.create_foreign_key('analytics_events_event_id_fkey', 'analytics_events', 'events', ['event_id'], ['id'])
    op.create_foreign_key('analytics_events_team_id_fkey', 'analytics_events', 'teams', ['team_id'], ['id'])

    # AI Tasks
    op.drop_constraint('ai_tasks_team_id_fkey', 'ai_tasks', type_='foreignkey')
    op.create_foreign_key('ai_tasks_team_id_fkey', 'ai_tasks', 'teams', ['team_id'], ['id'])

    # Shares
    op.drop_constraint('shares_photo_id_fkey', 'shares', type_='foreignkey')
    op.create_foreign_key('shares_photo_id_fkey', 'shares', 'photos', ['photo_id'], ['id'])

    # Print Jobs
    op.drop_constraint('print_jobs_photo_id_fkey', 'print_jobs', type_='foreignkey')
    op.create_foreign_key('print_jobs_photo_id_fkey', 'print_jobs', 'photos', ['photo_id'], ['id'])

    # Photos
    op.drop_constraint('photos_session_id_fkey', 'photos', type_='foreignkey')
    op.drop_constraint('photos_event_id_fkey', 'photos', type_='foreignkey')
    op.create_foreign_key('photos_session_id_fkey', 'photos', 'photo_sessions', ['session_id'], ['id'])
    op.create_foreign_key('photos_event_id_fkey', 'photos', 'events', ['event_id'], ['id'])

    # Photo Sessions
    op.drop_constraint('photo_sessions_event_id_fkey', 'photo_sessions', type_='foreignkey')
    op.create_foreign_key('photo_sessions_event_id_fkey', 'photo_sessions', 'events', ['event_id'], ['id'])

    # Templates
    op.drop_constraint('templates_team_id_fkey', 'templates', type_='foreignkey')
    op.create_foreign_key('templates_team_id_fkey', 'templates', 'teams', ['team_id'], ['id'])

    # Events
    op.drop_constraint('events_creator_id_fkey', 'events', type_='foreignkey')
    op.drop_constraint('events_team_id_fkey', 'events', type_='foreignkey')
    op.create_foreign_key('events_creator_id_fkey', 'events', 'users', ['creator_id'], ['id'])
    op.create_foreign_key('events_team_id_fkey', 'events', 'teams', ['team_id'], ['id'])

    # Disclaimer Acceptances
    op.drop_constraint('disclaimer_acceptances_session_id_fkey', 'disclaimer_acceptances', type_='foreignkey')
    op.drop_constraint('disclaimer_acceptances_event_id_fkey', 'disclaimer_acceptances', type_='foreignkey')
    op.create_foreign_key('disclaimer_acceptances_session_id_fkey', 'disclaimer_acceptances', 'photo_sessions', ['session_id'], ['id'])
    op.create_foreign_key('disclaimer_acceptances_event_id_fkey', 'disclaimer_acceptances', 'events', ['event_id'], ['id'])

    # Disclaimers
    op.drop_constraint('disclaimers_event_id_fkey', 'disclaimers', type_='foreignkey')
    op.create_foreign_key('disclaimers_event_id_fkey', 'disclaimers', 'events', ['event_id'], ['id'])

    # Survey Responses
    op.drop_constraint('survey_responses_session_id_fkey', 'survey_responses', type_='foreignkey')
    op.drop_constraint('survey_responses_event_id_fkey', 'survey_responses', type_='foreignkey')
    op.create_foreign_key('survey_responses_session_id_fkey', 'survey_responses', 'photo_sessions', ['session_id'], ['id'])
    op.create_foreign_key('survey_responses_event_id_fkey', 'survey_responses', 'events', ['event_id'], ['id'])

    # Surveys
    op.drop_constraint('surveys_event_id_fkey', 'surveys', type_='foreignkey')
    op.create_foreign_key('surveys_event_id_fkey', 'surveys', 'events', ['event_id'], ['id'])

    # Signatures
    op.drop_constraint('signatures_session_id_fkey', 'signatures', type_='foreignkey')
    op.create_foreign_key('signatures_session_id_fkey', 'signatures', 'photo_sessions', ['session_id'], ['id'])

    # Team Members
    op.drop_constraint('team_members_user_id_fkey', 'team_members', type_='foreignkey')
    op.drop_constraint('team_members_team_id_fkey', 'team_members', type_='foreignkey')
    op.create_foreign_key('team_members_user_id_fkey', 'team_members', 'users', ['user_id'], ['id'])
    op.create_foreign_key('team_members_team_id_fkey', 'team_members', 'teams', ['team_id'], ['id'])

    # Teams
    op.drop_constraint('teams_subscription_id_fkey', 'teams', type_='foreignkey')
    op.create_foreign_key('teams_subscription_id_fkey', 'teams', 'subscriptions', ['subscription_id'], ['id'])
