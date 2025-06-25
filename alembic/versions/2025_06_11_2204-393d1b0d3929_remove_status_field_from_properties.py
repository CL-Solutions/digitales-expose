"""remove_status_field_from_properties

Revision ID: 393d1b0d3929
Revises: a46b4c95dc98
Create Date: 2025-06-11 22:04:58.256888

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "393d1b0d3929"
down_revision: Union[str, None] = "a46b4c95dc98"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Drop the status column from properties table
    op.drop_column('properties', 'status')


def downgrade() -> None:
    """Downgrade schema."""
    # Re-add the status column with default value
    op.add_column('properties', sa.Column('status', sa.String(50), nullable=False, server_default='available'))
