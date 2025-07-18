"""Add contact information fields to tenant model

Revision ID: e62769cc8c35
Revises: 6ffdb74a4890
Create Date: 2025-06-12 22:30:45.068108

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e62769cc8c35"
down_revision: Union[str, None] = "6ffdb74a4890"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "tenants", sa.Column("contact_email", sa.String(length=255), nullable=True)
    )
    op.add_column(
        "tenants", sa.Column("contact_phone", sa.String(length=100), nullable=True)
    )
    op.add_column(
        "tenants", sa.Column("contact_street", sa.String(length=255), nullable=True)
    )
    op.add_column(
        "tenants",
        sa.Column("contact_house_number", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "tenants", sa.Column("contact_city", sa.String(length=100), nullable=True)
    )
    op.add_column(
        "tenants", sa.Column("contact_state", sa.String(length=100), nullable=True)
    )
    op.add_column(
        "tenants", sa.Column("contact_zip_code", sa.String(length=20), nullable=True)
    )
    op.add_column(
        "tenants", sa.Column("contact_country", sa.String(length=100), nullable=True)
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("tenants", "contact_country")
    op.drop_column("tenants", "contact_zip_code")
    op.drop_column("tenants", "contact_state")
    op.drop_column("tenants", "contact_city")
    op.drop_column("tenants", "contact_house_number")
    op.drop_column("tenants", "contact_street")
    op.drop_column("tenants", "contact_phone")
    op.drop_column("tenants", "contact_email")
    # ### end Alembic commands ###
