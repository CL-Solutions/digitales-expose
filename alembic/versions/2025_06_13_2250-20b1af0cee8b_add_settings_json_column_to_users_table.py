"""Add settings JSON column to users table

Revision ID: 20b1af0cee8b
Revises: f0e38007a1ea
Create Date: 2025-06-13 22:50:32.730510

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20b1af0cee8b"
down_revision: Union[str, None] = "f0e38007a1ea"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    # First add the column as nullable
    op.add_column(
        "users",
        sa.Column("settings", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    
    # Set default value for existing rows
    op.execute("UPDATE users SET settings = '{}' WHERE settings IS NULL")
    
    # Make the column not nullable
    op.alter_column("users", "settings", nullable=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("users", "settings")
    # ### end Alembic commands ###
