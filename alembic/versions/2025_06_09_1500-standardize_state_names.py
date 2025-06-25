"""Standardize state names to German

Revision ID: standardize_state_names
Revises: 430449afd390
Create Date: 2025-06-09 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'standardize_state_names'
down_revision: Union[str, None] = '430449afd390'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Map English state names to German
    state_mapping = {
        'Bavaria': 'Bayern',
        'Baden-Württemberg': 'Baden-Württemberg',
        'Berlin': 'Berlin',
        'Brandenburg': 'Brandenburg',
        'Bremen': 'Bremen',
        'Hamburg': 'Hamburg',
        'Hesse': 'Hessen',
        'Lower Saxony': 'Niedersachsen',
        'Mecklenburg-Vorpommern': 'Mecklenburg-Vorpommern',
        'North Rhine-Westphalia': 'Nordrhein-Westfalen',
        'Rhineland-Palatinate': 'Rheinland-Pfalz',
        'Saarland': 'Saarland',
        'Saxony': 'Sachsen',
        'Saxony-Anhalt': 'Sachsen-Anhalt',
        'Schleswig-Holstein': 'Schleswig-Holstein',
        'Thuringia': 'Thüringen'
    }
    
    # Update properties table
    for english_name, german_name in state_mapping.items():
        op.execute(
            f"UPDATE properties SET state = '{german_name}' WHERE state = '{english_name}'"
        )
    
    # Update projects table
    for english_name, german_name in state_mapping.items():
        op.execute(
            f"UPDATE projects SET state = '{german_name}' WHERE state = '{english_name}'"
        )
    
    # Update cities table
    for english_name, german_name in state_mapping.items():
        op.execute(
            f"UPDATE cities SET state = '{german_name}' WHERE state = '{english_name}'"
        )


def downgrade() -> None:
    # Map German state names back to English
    state_mapping = {
        'Bayern': 'Bavaria',
        'Hessen': 'Hesse',
        'Niedersachsen': 'Lower Saxony',
        'Nordrhein-Westfalen': 'North Rhine-Westphalia',
        'Rheinland-Pfalz': 'Rhineland-Palatinate',
        'Sachsen': 'Saxony',
        'Sachsen-Anhalt': 'Saxony-Anhalt',
        'Thüringen': 'Thuringia'
    }
    
    # Update properties table
    for german_name, english_name in state_mapping.items():
        op.execute(
            f"UPDATE properties SET state = '{english_name}' WHERE state = '{german_name}'"
        )
    
    # Update projects table
    for german_name, english_name in state_mapping.items():
        op.execute(
            f"UPDATE projects SET state = '{english_name}' WHERE state = '{german_name}'"
        )
    
    # Update cities table
    for german_name, english_name in state_mapping.items():
        op.execute(
            f"UPDATE cities SET state = '{english_name}' WHERE state = '{german_name}'"
        )