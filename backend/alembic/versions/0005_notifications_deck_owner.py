"""notifications; presentation decks owned by the user who uploaded them

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '0005'
down_revision: Union[str, None] = '0004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('notifications',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('kind', sa.String(length=50), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('body', sa.Text(), nullable=False),
    sa.Column('link', sa.String(length=300), nullable=True),
    sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_notifications_user_id', 'notifications', ['user_id'])
    # Decks uploaded while signed in belong to that user (older/anonymous decks stay unowned)
    op.add_column('sessions', sa.Column('user_id', sa.Uuid(), nullable=True))
    op.create_foreign_key('fk_sessions_user_id', 'sessions', 'users', ['user_id'], ['id'], ondelete='SET NULL')
    op.create_index('ix_sessions_user_id', 'sessions', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_sessions_user_id', table_name='sessions')
    op.drop_constraint('fk_sessions_user_id', 'sessions', type_='foreignkey')
    op.drop_column('sessions', 'user_id')
    op.drop_index('ix_notifications_user_id', table_name='notifications')
    op.drop_table('notifications')
