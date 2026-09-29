"""users, live sessions, progress records and reports

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-30

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0002'
down_revision: Union[str, None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

JSONType = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql')


def upgrade() -> None:
    op.create_table('users',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('full_name', sa.String(length=255), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('password_hash', sa.Text(), nullable=False),
    sa.Column('role', sa.String(length=50), nullable=False),
    sa.Column('language', sa.String(length=50), nullable=False),
    sa.Column('age_group', sa.String(length=50), nullable=True),
    sa.Column('communication_goal', sa.String(length=100), nullable=True),
    sa.Column('skill_level', sa.String(length=50), nullable=False),
    sa.Column('challenges', JSONType, nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    op.create_table('live_sessions',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('session_type', sa.String(length=50), nullable=False),
    sa.Column('duration_sec', sa.Integer(), nullable=False),
    sa.Column('recording_storage_path', sa.Text(), nullable=True),
    sa.Column('status', sa.String(length=50), nullable=False),
    sa.Column('error_detail', sa.Text(), nullable=True),
    sa.Column('warnings', JSONType, nullable=True),
    sa.Column('analysis', JSONType, nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_live_sessions_user_id', 'live_sessions', ['user_id'])

    op.create_table('progress_records',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('live_session_id', sa.Uuid(), nullable=False),
    sa.Column('metric_name', sa.String(length=100), nullable=False),
    sa.Column('metric_value', sa.Float(), nullable=False),
    sa.Column('recorded_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['live_session_id'], ['live_sessions.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_progress_records_user_id', 'progress_records', ['user_id'])

    op.create_table('reports',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('report_type', sa.String(length=50), nullable=False),
    sa.Column('content', JSONType, nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_reports_user_id', 'reports', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_reports_user_id', table_name='reports')
    op.drop_table('reports')
    op.drop_index('ix_progress_records_user_id', table_name='progress_records')
    op.drop_table('progress_records')
    op.drop_index('ix_live_sessions_user_id', table_name='live_sessions')
    op.drop_table('live_sessions')
    op.drop_index('ix_users_email', table_name='users')
    op.drop_table('users')
