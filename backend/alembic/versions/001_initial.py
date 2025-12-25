"""Initial migration - Create all tables

Revision ID: 001
Create Date: 2025-12-24
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('device_locale', sa.String(10), nullable=True),
        sa.Column('ui_language_override', sa.String(10), nullable=True),
        sa.Column('auto_post_enabled', sa.Boolean(), nullable=False, default=False),
        sa.Column('daily_post_limit', sa.Integer(), nullable=False, default=10),
    )
    op.create_index('ix_users_id', 'users', ['id'])

    # Create x_accounts table
    op.create_table(
        'x_accounts',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('oauth_state', sa.String(255), nullable=True),
        sa.Column('access_token_encrypted', sa.Text(), nullable=True),
        sa.Column('refresh_token_encrypted', sa.Text(), nullable=True),
        sa.Column('token_expires_at', sa.DateTime(), nullable=True),
        sa.Column('x_user_id', sa.String(255), nullable=True),
        sa.Column('x_username', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_x_accounts_user_id', 'x_accounts', ['user_id'])

    # Create campaigns table
    op.create_table(
        'campaigns',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('language', sa.String(10), nullable=False, default='tr'),
        sa.Column('hashtags_json', sa.Text(), nullable=True, default='[]'),
        sa.Column('tone', sa.String(50), nullable=True),
        sa.Column('call_to_action', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_campaigns_user_id', 'campaigns', ['user_id'])
    op.create_index('ix_campaigns_created_at', 'campaigns', ['created_at'])

    # Create media_assets table
    op.create_table(
        'media_assets',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('campaign_id', sa.String(36), sa.ForeignKey('campaigns.id'), nullable=False),
        sa.Column('type', sa.String(10), nullable=False),
        sa.Column('path', sa.Text(), nullable=False),
        sa.Column('original_name', sa.String(255), nullable=False),
        sa.Column('alt_text', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_media_assets_campaign_id', 'media_assets', ['campaign_id'])

    # Create schedules table
    op.create_table(
        'schedules',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('campaign_id', sa.String(36), sa.ForeignKey('campaigns.id'), nullable=False),
        sa.Column('timezone', sa.String(50), nullable=False, default='Europe/Istanbul'),
        sa.Column('times_json', sa.Text(), nullable=True, default='[]'),
        sa.Column('recurrence', sa.String(20), nullable=False, default='daily'),
        sa.Column('start_date', sa.DateTime(), nullable=False),
        sa.Column('end_date', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('auto_post', sa.Boolean(), nullable=False, default=False),
        sa.Column('daily_limit', sa.Integer(), nullable=False, default=10),
        sa.Column('selected_variant_index', sa.Integer(), nullable=False, default=0),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_schedules_campaign_id', 'schedules', ['campaign_id'])
    op.create_index('ix_schedules_is_active', 'schedules', ['is_active'])

    # Create drafts table
    op.create_table(
        'drafts',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('campaign_id', sa.String(36), sa.ForeignKey('campaigns.id'), nullable=False),
        sa.Column('schedule_id', sa.String(36), sa.ForeignKey('schedules.id'), nullable=True),
        sa.Column('scheduled_for', sa.DateTime(), nullable=True),
        sa.Column('variant_index', sa.Integer(), nullable=False, default=0),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('char_count', sa.Integer(), nullable=False),
        sa.Column('hashtags_used_json', sa.Text(), nullable=True, default='[]'),
        sa.Column('status', sa.String(20), nullable=False, default='pending'),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('x_post_id', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('posted_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_drafts_campaign_id', 'drafts', ['campaign_id'])
    op.create_index('ix_drafts_status', 'drafts', ['status'])
    op.create_index('ix_drafts_scheduled_for', 'drafts', ['scheduled_for'])

    # Create post_logs table
    op.create_table(
        'post_logs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('campaign_id', sa.String(36), sa.ForeignKey('campaigns.id'), nullable=False),
        sa.Column('draft_id', sa.String(36), sa.ForeignKey('drafts.id'), nullable=True),
        sa.Column('run_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('action', sa.String(20), nullable=False),
        sa.Column('details', sa.JSON(), nullable=True),
    )
    op.create_index('ix_post_logs_campaign_id', 'post_logs', ['campaign_id'])
    op.create_index('ix_post_logs_run_at', 'post_logs', ['run_at'])


def downgrade() -> None:
    op.drop_table('post_logs')
    op.drop_table('drafts')
    op.drop_table('schedules')
    op.drop_table('media_assets')
    op.drop_table('campaigns')
    op.drop_table('x_accounts')
    op.drop_table('users')
