"""Add total_units to projects table

Revision ID: b7831082344d
Revises: fix_percentages_2025
Create Date: 2025-06-25 19:56:28.186053

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b7831082344d"
down_revision: Union[str, None] = "fix_percentages_2025"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add total_units column to projects table
    op.add_column('projects', sa.Column('total_units', sa.Integer(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove total_units column from projects table
    op.drop_column('projects', 'total_units')
