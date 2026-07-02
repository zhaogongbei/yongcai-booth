"""add triggers, webhooks, green_screen tables

Revision ID: 005_add_triggers_webhooks_and_green_screen
Revises: 004_add_booths
Create Date: 2026-07-01 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from app.models.types import GUID

# revision identifiers
revision = '005_add_triggers_webhooks_and_green_screen'
down_revision = '004_add_booths'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. trigger_configs
    op.create_table('trigger_configs',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('team_id', GUID(), nullable=False),
        sa.Column('event_id', GUID(), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('action_type', sa.String(length=50), nullable=False),
        sa.Column('target', sa.String(length=500), nullable=False),
        sa.Column('payload_template', sa.JSON(), nullable=True),
        sa.Column('timeout', sa.Integer(), nullable=True),
        sa.Column('retry', sa.Integer(), nullable=True),
        sa.Column('enabled', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ),
        sa.ForeignKeyConstraint(['event_id'], ['events.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_trigger_configs_team_id', 'trigger_configs', ['team_id'])
    op.create_index('ix_trigger_configs_event_id', 'trigger_configs', ['event_id'])

    # 2. trigger_logs
    op.create_table('trigger_logs',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('trigger_id', GUID(), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('success', sa.Boolean(), nullable=True),
        sa.Column('response_data', sa.JSON(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['trigger_id'], ['trigger_configs.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_trigger_logs_trigger_id', 'trigger_logs', ['trigger_id'])

    # 3. webhooks
    op.create_table('webhooks',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('team_id', GUID(), nullable=False),
        sa.Column('url', sa.String(length=500), nullable=False),
        sa.Column('events', sa.JSON(), nullable=False),
        sa.Column('secret', sa.String(length=255), nullable=True),
        sa.Column('enabled', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_webhooks_team_id', 'webhooks', ['team_id'])

    # 4. webhook_logs
    op.create_table('webhook_logs',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('webhook_id', GUID(), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('url', sa.String(length=500), nullable=False),
        sa.Column('status_code', sa.Integer(), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=True),
        sa.Column('response_body', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['webhook_id'], ['webhooks.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_webhook_logs_webhook_id', 'webhook_logs', ['webhook_id'])

    # 5. green_screen_settings
    op.create_table('green_screen_settings',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('event_id', GUID(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=True),
        sa.Column('mode', sa.String(length=50), nullable=True),
        sa.Column('color_to_remove', sa.String(length=20), nullable=True),
        sa.Column('sensitivity', sa.Float(), nullable=True),
        sa.Column('smoothness', sa.Float(), nullable=True),
        sa.Column('use_flash', sa.Boolean(), nullable=True),
        sa.Column('output_size', sa.String(length=20), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['event_id'], ['events.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('event_id')
    )

    # 6. green_screen_backgrounds
    op.create_table('green_screen_backgrounds',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('settings_id', GUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('background_url', sa.String(length=500), nullable=False),
        sa.Column('overlay_url', sa.String(length=500), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['settings_id'], ['green_screen_settings.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_green_screen_backgrounds_settings_id', 'green_screen_backgrounds', ['settings_id'])


def downgrade() -> None:
    op.drop_index('ix_green_screen_backgrounds_settings_id', 'green_screen_backgrounds')
    op.drop_table('green_screen_backgrounds')
    op.drop_table('green_screen_settings')
    op.drop_index('ix_webhook_logs_webhook_id', 'webhook_logs')
    op.drop_table('webhook_logs')
    op.drop_index('ix_webhooks_team_id', 'webhooks')
    op.drop_table('webhooks')
    op.drop_index('ix_trigger_logs_trigger_id', 'trigger_logs')
    op.drop_table('trigger_logs')
    op.drop_index('ix_trigger_configs_event_id', 'trigger_configs')
    op.drop_index('ix_trigger_configs_team_id', 'trigger_configs')
    op.drop_table('trigger_configs')
