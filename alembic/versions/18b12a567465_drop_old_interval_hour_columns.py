"""Drop old interval hour columns

Revision ID: 18b12a567465
Revises: 58a33c67ea61
Create Date: 2026-03-13 07:19:41.870170

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '18b12a567465'
down_revision: Union[str, None] = '58a33c67ea61'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column('settings', 'min_interval_hours')
    op.drop_column('settings', 'max_interval_hours')


def downgrade() -> None:
    op.add_column('settings', sa.Column('min_interval_hours', sa.Integer(), nullable=True))
    op.add_column('settings', sa.Column('max_interval_hours', sa.Integer(), nullable=True))
