"""Add virtual_tour section to expose templates

Revision ID: b3713fe9b17f
Revises: cff140843de7
Create Date: 2025-07-12 11:30:39.871892

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b3713fe9b17f"
down_revision: Union[str, None] = "cff140843de7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Update existing expose templates to include virtual_tour in enabled_sections
    # Cast to jsonb for the operation, then back to json
    op.execute("""
        UPDATE expose_templates
        SET enabled_sections = (
            jsonb_set(
                enabled_sections::jsonb,
                '{virtual_tour}',
                'true'
            )
        )::json
        WHERE enabled_sections IS NOT NULL
        AND NOT (enabled_sections::jsonb ? 'virtual_tour')
    """)


def downgrade() -> None:
    """Downgrade schema."""
    pass
