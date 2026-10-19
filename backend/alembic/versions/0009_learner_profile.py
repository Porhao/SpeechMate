"""learner profile: study level, field of study or work, preferred feedback style

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-20

The AI pitches its questions, vocabulary and feedback at these (services/learner.py).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '0009'
down_revision: Union[str, None] = '0008'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('users') as t:
        t.add_column(sa.Column('study_level', sa.String(length=50), nullable=True))
        t.add_column(sa.Column('field_of_study', sa.String(length=100), nullable=True))
        t.add_column(sa.Column('feedback_style', sa.String(length=20), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('users') as t:
        t.drop_column('feedback_style')
        t.drop_column('field_of_study')
        t.drop_column('study_level')
