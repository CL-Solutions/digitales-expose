"""Add Investagon status flags: active, pre_sale, draft

Revision ID: 1298d8141aca
Revises: 391a02dec3bb
Create Date: 2025-06-05 09:55:06.093887

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "1298d8141aca"
down_revision: Union[str, None] = "391a02dec3bb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("properties", sa.Column("active", sa.Integer(), nullable=True))
    op.add_column("properties", sa.Column("pre_sale", sa.Integer(), nullable=True))
    op.add_column("properties", sa.Column("draft", sa.Integer(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("properties", "draft")
    op.drop_column("properties", "pre_sale")
    op.drop_column("properties", "active")
    # ### end Alembic commands ###
