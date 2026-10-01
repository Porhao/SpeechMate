"""live sessions keep their practice setup (interview plan / deck Q&A plan), the
conversation turns and browser-side metrics

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0006'
down_revision: Union[str, None] = '0005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

JSON = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.add_column('live_sessions', sa.Column('context', JSON, nullable=True))
    op.add_column('live_sessions', sa.Column('turns', JSON, nullable=True))
    op.add_column('live_sessions', sa.Column('client_metrics', JSON, nullable=True))


def downgrade() -> None:
    op.drop_column('live_sessions', 'client_metrics')
    op.drop_column('live_sessions', 'turns')
    op.drop_column('live_sessions', 'context')
