"""Update existing expose templates with new default values

Revision ID: 39cbc853c254
Revises: f27fb601e979
Create Date: 2025-07-09 11:41:02.537636

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import json


# revision identifiers, used by Alembic.
revision: str = "39cbc853c254"
down_revision: Union[str, None] = "f27fb601e979"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Import default values
    from app.utils.default_template_content import (
        DEFAULT_LIABILITY_DISCLAIMER,
        DEFAULT_ONSITE_MANAGEMENT_SERVICES,
        DEFAULT_ONSITE_MANAGEMENT_PACKAGE,
        DEFAULT_COLIVING_CONTENT,
        DEFAULT_SPECIAL_FEATURES
    )
    
    # Update all existing expose templates with the new default values
    op.execute(f"""
        UPDATE expose_templates 
        SET 
            liability_disclaimer_content = '{DEFAULT_LIABILITY_DISCLAIMER.replace("'", "''")}',
            onsite_management_services = '{json.dumps(DEFAULT_ONSITE_MANAGEMENT_SERVICES)}',
            onsite_management_package = '{json.dumps(DEFAULT_ONSITE_MANAGEMENT_PACKAGE)}',
            coliving_content = '{DEFAULT_COLIVING_CONTENT.replace("'", "''")}',
            special_features_items = '{json.dumps(DEFAULT_SPECIAL_FEATURES)}'
        WHERE 
            liability_disclaimer_content IS NULL 
            OR onsite_management_services IS NULL
            OR onsite_management_package IS NULL
            OR coliving_content IS NULL
            OR special_features_items IS NULL
    """)
    
    # Also update the enabled_sections to include the new sections
    op.execute("""
        UPDATE expose_templates 
        SET enabled_sections = jsonb_set(
            jsonb_set(
                jsonb_set(
                    jsonb_set(
                        COALESCE(enabled_sections, '{}')::jsonb,
                        '{liability_disclaimer}',
                        'true'::jsonb
                    ),
                    '{onsite_management}',
                    'true'::jsonb
                ),
                '{coliving}',
                'true'::jsonb
            ),
            '{special_features}',
            'true'::jsonb
        )
        WHERE enabled_sections IS NOT NULL
    """)


def downgrade() -> None:
    """Downgrade schema."""
    # Remove the new sections from enabled_sections
    op.execute("""
        UPDATE expose_templates 
        SET enabled_sections = enabled_sections::jsonb 
            - 'liability_disclaimer' 
            - 'onsite_management' 
            - 'coliving' 
            - 'special_features'
        WHERE enabled_sections IS NOT NULL
    """)
    
    # Clear the new fields
    op.execute("""
        UPDATE expose_templates 
        SET 
            liability_disclaimer_content = NULL,
            onsite_management_services = NULL,
            onsite_management_package = NULL,
            coliving_content = NULL,
            special_features_items = NULL
    """)
