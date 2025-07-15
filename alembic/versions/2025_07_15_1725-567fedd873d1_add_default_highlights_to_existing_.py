"""Add default highlights to existing expose templates

Revision ID: 567fedd873d1
Revises: 3a3f6adc7ad6
Create Date: 2025-07-15 17:25:39.190701

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text
import json


# revision identifiers, used by Alembic.
revision: str = "567fedd873d1"
down_revision: Union[str, None] = "3a3f6adc7ad6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Default highlights from default_template_content.py
DEFAULT_HIGHLIGHTS = [
    {
        "label": "Mietrendite",
        "value": "{{gross_rental_yield}}%",
        "icon": "percent",
        "color": "green",
        "enabled": True,
        "order": 1,
        "condition": "gross_rental_yield > 4"
    },
    {
        "label": "Positiver Cashflow",
        "value": "{{monthly_net_income}}",
        "icon": "trending-up",
        "color": "blue",
        "enabled": False,
        "order": 2,
        "condition": "monthly_net_income > 0"
    },
    {
        "label": "Balkon / Terrasse",
        "value": "{{size_sqm}} m²",
        "icon": "home",
        "color": "amber",
        "enabled": False,
        "order": 3,
        "condition": "has_balcony = true"
    },
    {
        "label": "Hinterlandsbebauung",
        "value": None,
        "icon": "building",
        "color": "gray",
        "enabled": False,
        "order": 4,
        "condition": "backyard_development = true"
    },
    {
        "label": "Erhaltungsaufwand",
        "value": "{{initial_maintenance_expenses_formatted}}",
        "icon": "wrench",
        "color": "blue",
        "enabled": False,
        "order": 5,
        "condition": "initial_maintenance_expenses > 0"
    },
    {
        "label": "Übernahme SEV im 1. Jahr",
        "value": None,
        "icon": "shield-check",
        "color": "green",
        "enabled": False,
        "order": 6,
        "condition": "sev_takeover_one_year = true"
    },
    {
        "label": "Energieeffizienz",
        "value": "Klasse {{energy_class}}",
        "icon": "zap",
        "color": "green",
        "enabled": False,
        "order": 7,
        "condition": "energy_class <= D"
    },
    {
        "label": "Erstvermietungsgarantie",
        "value": None,
        "icon": "check-circle",
        "color": "blue",
        "enabled": False,
        "order": 8,
        "condition": None
    },
    {
        "label": "Gewährleistung",
        "value": "5 Jahre",
        "icon": "shield",
        "color": "amber",
        "enabled": False,
        "order": 9,
        "condition": None
    },
    {
        "label": "Garage / Stellplatz",
        "value": "{{purchase_price_parking}}",
        "icon": "car",
        "color": "gray",
        "enabled": False,
        "order": 10,
        "condition": "has_parking = true"
    },
    {
        "label": "Baujahr",
        "value": "{{construction_year}}",
        "icon": "calendar",
        "color": "blue",
        "enabled": False,
        "order": 11,
        "condition": "construction_year > 2020"
    },
    {
        "label": "Übernahme Sonderumlagen",
        "value": "{{takeover_special_charges_amount}} für {{takeover_special_charges_years}} Jahre",
        "icon": "receipt",
        "color": "green",
        "enabled": False,
        "order": 12,
        "condition": "takeover_special_charges_years > 0 OR takeover_special_charges_amount > 0"
    }
]


def upgrade() -> None:
    """Upgrade schema."""
    # Update the specific template with default highlights
    connection = op.get_bind()
    
    template_id = "8f284269-1905-45ce-8bf3-c1362b601686"
    
    print(f"Updating template {template_id} with default highlights...")
    
    connection.execute(
        text(
            "UPDATE expose_templates SET highlights = :highlights WHERE id = :id"
        ),
        {"highlights": json.dumps(DEFAULT_HIGHLIGHTS), "id": template_id}
    )
    
    print(f"Updated template ID: {template_id}")


def downgrade() -> None:
    """Downgrade schema."""
    # We don't remove highlights on downgrade as they might have been customized
    pass
