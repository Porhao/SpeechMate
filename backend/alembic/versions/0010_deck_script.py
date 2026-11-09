"""deck practice script

Revision ID: 0010
Revises: 0009
Create Date: 2026-10-20

The script written for a deck at a chosen talk length (services/script_writer.py).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0010'
down_revision: Union[str, None] = '0009'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('sessions') as t:
        t.add_column(sa.Column('script', sa.JSON().with_variant(postgresql.JSONB(), 'postgresql'), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('sessions') as t:
        t.drop_column('script')
