"""drop what removed features left behind: the example narration's columns, the old
upload-a-rehearsal coach (practice_sessions, chat_messages) and the progress copies / reports

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-20

Nothing reads or writes these any more (see docs/project/Database.md). progress_records held a copy
of scores already in live_sessions.analysis. Downgrade brings the tables and columns back empty.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0008'
down_revision: Union[str, None] = '0007'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

JSONType = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql')
SESSION_COLUMNS = ('voice_sample_storage_path', 'narrator_voice', 'voice_cloning_used', 'video_storage_path')
SLIDE_COLUMNS = ('script_text', 'script_word_count', 'script_source', 'audio_storage_path',
                 'audio_duration_sec', 'audio_source', 'status', 'error_detail')


def upgrade() -> None:
    op.drop_table('chat_messages')
    op.drop_table('practice_sessions')
    op.drop_index('ix_reports_user_id', table_name='reports')
    op.drop_table('reports')
    op.drop_index('ix_progress_records_user_id', table_name='progress_records')
    op.drop_table('progress_records')
    with op.batch_alter_table('sessions') as t:
        for c in SESSION_COLUMNS:
            t.drop_column(c)
    with op.batch_alter_table('slides') as t:
        for c in SLIDE_COLUMNS:
            t.drop_column(c)


def downgrade() -> None:
    with op.batch_alter_table('slides') as t:
        t.add_column(sa.Column('script_text', sa.Text(), nullable=True))
        t.add_column(sa.Column('script_word_count', sa.Integer(), nullable=True))
        t.add_column(sa.Column('script_source', sa.String(length=50), nullable=True))
        t.add_column(sa.Column('audio_storage_path', sa.Text(), nullable=True))
        t.add_column(sa.Column('audio_duration_sec', sa.Float(), nullable=True))
        t.add_column(sa.Column('audio_source', sa.String(length=50), nullable=True))
        t.add_column(sa.Column('status', sa.String(length=50), nullable=False, server_default='rendered'))
        t.add_column(sa.Column('error_detail', sa.Text(), nullable=True))
    with op.batch_alter_table('sessions') as t:
        t.add_column(sa.Column('voice_sample_storage_path', sa.Text(), nullable=True))
        t.add_column(sa.Column('narrator_voice', sa.String(length=50), nullable=True))
        t.add_column(sa.Column('voice_cloning_used', sa.Boolean(), nullable=True))
        t.add_column(sa.Column('video_storage_path', sa.Text(), nullable=True))

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
    op.create_table('practice_sessions',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('session_id', sa.Uuid(), nullable=False),
    sa.Column('audio_storage_path', sa.Text(), nullable=False),
    sa.Column('recording_granularity', sa.String(length=50), nullable=False),
    sa.Column('slide_index', sa.Integer(), nullable=True),
    sa.Column('status', sa.String(length=50), nullable=False),
    sa.Column('error_detail', sa.Text(), nullable=True),
    sa.Column('warnings', JSONType, nullable=True),
    sa.Column('transcript', sa.Text(), nullable=True),
    sa.Column('metrics', JSONType, nullable=True),
    sa.Column('feedback', JSONType, nullable=True),
    sa.Column('audience_feedback', JSONType, nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('chat_messages',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('practice_session_id', sa.Uuid(), nullable=False),
    sa.Column('role', sa.String(length=20), nullable=False),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['practice_session_id'], ['practice_sessions.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
