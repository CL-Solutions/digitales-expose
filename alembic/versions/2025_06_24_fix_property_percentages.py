"""Fix property percentage values from Investagon

Revision ID: fix_percentages_2025
Revises: 0e4c900b5081
Create Date: 2025-06-24 14:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "fix_percentages_2025"
down_revision: Union[str, None] = "0e4c900b5081"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Convert percentage values (e.g., 3 for 3%) to decimal values (0.03)"""
    
    # Fix object_share_owner values > 1
    op.execute("""
        UPDATE properties 
        SET object_share_owner = object_share_owner / 100.0,
            updated_at = NOW()
        WHERE object_share_owner > 1
    """)
    
    # Fix share_land values > 1
    op.execute("""
        UPDATE properties 
        SET share_land = share_land / 100.0,
            updated_at = NOW()
        WHERE share_land > 1
    """)
    
    print("Fixed property percentage values")


def downgrade() -> None:
    """Convert decimal values back to percentage values"""
    
    # Convert object_share_owner back to percentage
    op.execute("""
        UPDATE properties 
        SET object_share_owner = object_share_owner * 100.0,
            updated_at = NOW()
        WHERE object_share_owner IS NOT NULL AND object_share_owner <= 1
    """)
    
    # Convert share_land back to percentage
    op.execute("""
        UPDATE properties 
        SET share_land = share_land * 100.0,
            updated_at = NOW()
        WHERE share_land IS NOT NULL AND share_land <= 1
    """)