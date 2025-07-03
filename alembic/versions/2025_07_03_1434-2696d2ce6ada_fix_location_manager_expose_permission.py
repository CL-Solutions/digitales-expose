"""Fix location_manager expose permission

Revision ID: 2696d2ce6ada
Revises: f11d8e36e142
Create Date: 2025-07-03 14:34:48.921139

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "2696d2ce6ada"
down_revision: Union[str, None] = "f11d8e36e142"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Fix location_manager roles that have incorrect expose:read permission
    # First, get the permission IDs
    op.execute("""
        -- Update role_permissions to replace expose:read with expose:view for location_manager roles
        UPDATE role_permissions
        SET permission_id = (
            SELECT id FROM permissions 
            WHERE resource = 'expose' AND action = 'view'
        )
        WHERE role_id IN (
            SELECT id FROM roles 
            WHERE name = 'location_manager'
        )
        AND permission_id = (
            SELECT id FROM permissions 
            WHERE resource = 'expose' AND action = 'read'
        );
    """)


def downgrade() -> None:
    """Downgrade schema."""
    # Revert location_manager roles back to incorrect expose:read permission
    op.execute("""
        -- Note: This assumes expose:read permission exists, which it doesn't
        -- This downgrade is provided for completeness but shouldn't be used
        -- as expose:read is not a valid permission
        SELECT 1; -- No-op
    """)
