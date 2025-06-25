"""Merge branches

Revision ID: fa8c54dcf550
Revises: 144aaf012717, standardize_state_names
Create Date: 2025-06-11 11:03:21.446133

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "fa8c54dcf550"
down_revision: Union[str, None] = ("144aaf012717", "standardize_state_names")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
