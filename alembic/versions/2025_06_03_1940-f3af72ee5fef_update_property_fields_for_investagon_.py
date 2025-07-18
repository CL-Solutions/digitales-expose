"""Update property fields for Investagon sync

Revision ID: f3af72ee5fef
Revises: dcb69066ad8b
Create Date: 2025-06-03 19:40:25.929930

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f3af72ee5fef"
down_revision: Union[str, None] = "dcb69066ad8b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "properties", sa.Column("street", sa.String(length=255), nullable=True)
    )
    op.add_column(
        "properties", sa.Column("house_number", sa.String(length=50), nullable=True)
    )
    op.add_column(
        "properties",
        sa.Column("apartment_number", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "properties", sa.Column("country", sa.String(length=100), nullable=True)
    )
    op.add_column(
        "properties", sa.Column("renovation_year", sa.Integer(), nullable=True)
    )
    op.add_column(
        "properties",
        sa.Column(
            "purchase_price_parking", sa.Numeric(precision=10, scale=2), nullable=True
        ),
    )
    op.add_column(
        "properties",
        sa.Column(
            "purchase_price_furniture", sa.Numeric(precision=10, scale=2), nullable=True
        ),
    )
    op.add_column(
        "properties",
        sa.Column(
            "rent_parking_month", sa.Numeric(precision=10, scale=2), nullable=True
        ),
    )
    op.add_column(
        "properties",
        sa.Column(
            "transaction_broker_rate", sa.Numeric(precision=5, scale=2), nullable=True
        ),
    )
    op.add_column(
        "properties",
        sa.Column(
            "transaction_tax_rate", sa.Numeric(precision=5, scale=2), nullable=True
        ),
    )
    op.add_column(
        "properties",
        sa.Column(
            "transaction_notary_rate", sa.Numeric(precision=5, scale=2), nullable=True
        ),
    )
    op.add_column(
        "properties",
        sa.Column(
            "transaction_register_rate", sa.Numeric(precision=5, scale=2), nullable=True
        ),
    )
    op.add_column(
        "properties",
        sa.Column(
            "operation_cost_landlord", sa.Numeric(precision=10, scale=2), nullable=True
        ),
    )
    op.add_column(
        "properties",
        sa.Column(
            "operation_cost_tenant", sa.Numeric(precision=10, scale=2), nullable=True
        ),
    )
    op.add_column(
        "properties",
        sa.Column(
            "operation_cost_reserve", sa.Numeric(precision=10, scale=2), nullable=True
        ),
    )
    op.drop_column("properties", "address")
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "properties",
        sa.Column(
            "address", sa.VARCHAR(length=500), autoincrement=False, nullable=False
        ),
    )
    op.drop_column("properties", "operation_cost_reserve")
    op.drop_column("properties", "operation_cost_tenant")
    op.drop_column("properties", "operation_cost_landlord")
    op.drop_column("properties", "transaction_register_rate")
    op.drop_column("properties", "transaction_notary_rate")
    op.drop_column("properties", "transaction_tax_rate")
    op.drop_column("properties", "transaction_broker_rate")
    op.drop_column("properties", "rent_parking_month")
    op.drop_column("properties", "purchase_price_furniture")
    op.drop_column("properties", "purchase_price_parking")
    op.drop_column("properties", "renovation_year")
    op.drop_column("properties", "country")
    op.drop_column("properties", "apartment_number")
    op.drop_column("properties", "house_number")
    op.drop_column("properties", "street")
    # ### end Alembic commands ###
