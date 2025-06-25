"""Add performance indexes for properties and projects

Revision ID: 0e4c900b5081
Revises: d8d107001483
Create Date: 2025-06-16 13:59:39.247474

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0e4c900b5081"
down_revision: Union[str, None] = "d8d107001483"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Properties search performance indexes
    op.create_index("idx_properties_active", "properties", ["active"])
    op.create_index("idx_properties_project_id", "properties", ["project_id"])
    op.create_index("idx_properties_city", "properties", ["city"])
    op.create_index("idx_properties_purchase_price", "properties", ["purchase_price"])
    
    # Projects search performance indexes
    op.create_index("idx_projects_city", "projects", ["city"])
    op.create_index("idx_projects_status", "projects", ["status"])
    
    # Additional indexes for recently added features
    op.create_index("idx_properties_visibility", "properties", ["visibility"])
    
    # Index for fast expose link lookups by link_id
    op.create_index("idx_expose_links_link_id", "expose_links", ["link_id"])


def downgrade() -> None:
    """Downgrade schema."""
    # Drop all indexes in reverse order
    op.drop_index("idx_expose_links_link_id", "expose_links")
    op.drop_index("idx_properties_visibility", "properties")
    op.drop_index("idx_projects_status", "projects")
    op.drop_index("idx_projects_city", "projects")
    op.drop_index("idx_properties_purchase_price", "properties")
    op.drop_index("idx_properties_city", "properties")
    op.drop_index("idx_properties_project_id", "properties")
    op.drop_index("idx_properties_active", "properties")
