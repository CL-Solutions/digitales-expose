"""Populate default template content for existing templates

Revision ID: populate_template_content
Revises: 9db411757f96
Create Date: 2025-01-07 22:00:00.000000

"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column
from sqlalchemy import String, JSON
import json

# revision identifiers, used by Alembic.
revision: str = "populate_template_content"
down_revision: Union[str, None] = "9db411757f96"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Populate default content for template fields"""
    
    # Define default content
    default_floor_plan_content = "10 Jahre Erfahrung in der Grundrissoptimierung für maximale Mietertragskraft"
    
    default_modernization_items = [
        {"title": "Vollständige Entrümpelung und Entsorgung alter Einbauten", "description": None},
        {"title": "Modernisierung des Badezimmers", "description": None},
        {"title": "Erneuerung der kompletten Elektrik", "description": None},
        {"title": "Neue Türen und Zargen", "description": None},
        {"title": "Hochwertiger Parkettboden", "description": None},
        {"title": "Fliesenarbeiten in Betonoptik", "description": None},
        {"title": "Grundrissoptimierung", "description": "Anpassung auf optimale Zimmeraufteilung"},
        {"title": "LED Beleuchtung im gesamten Objekt", "description": None},
        {"title": "Maßgefertigte Einbauküche", "description": None},
        {"title": "Komplette Malerarbeiten", "description": None},
        {"title": "Balkon Holzverkleidung", "description": None},
        {"title": "5 Jahre Modernisierungsgarantie", "description": None}
    ]
    
    default_insurance_plans = [
        {
            "name": "Basis",
            "price": 269.10,
            "period": "pro Jahr",
            "features": [
                "Mietausfall bis 10.000€",
                "Sachschäden abgedeckt",
                "Rechtsschutz inklusive"
            ],
            "recommended": False
        },
        {
            "name": "Premium",
            "price": 314.10,
            "period": "pro Jahr",
            "features": [
                "Mietausfall bis 15.000€",
                "Erweiterte Sachschäden",
                "Räumungskosten inklusive"
            ],
            "recommended": True
        },
        {
            "name": "Komplett",
            "price": 359.10,
            "period": "pro Jahr",
            "features": [
                "Mietausfall bis 20.000€",
                "Vollkasko-Schutz",
                "24/7 Notfall-Service"
            ],
            "recommended": False
        }
    ]
    
    default_process_steps = [
        {
            "number": 1,
            "title": "Referenzobjekt besichtigen",
            "description": "Lernen Sie unseren Modernisierungsstandard bei einer Besichtigung kennen.",
            "color_scheme": "amber"
        },
        {
            "number": 2,
            "title": "Business Case erstellen",
            "description": "Wir berechnen Ihren individuellen Investment-Case mit allen Details.",
            "color_scheme": "amber"
        },
        {
            "number": 3,
            "title": "Reservierung unterzeichnen",
            "description": "Sichern Sie sich Ihr Wunschobjekt mit einer verbindlichen Reservierung.",
            "color_scheme": "amber"
        },
        {
            "number": 4,
            "title": "Finanzierung regeln",
            "description": "Unsere Partner unterstützen Sie bei der optimalen Finanzierungslösung.",
            "color_scheme": "blue"
        },
        {
            "number": 5,
            "title": "Kaufvertrag besprechen",
            "description": "Detaillierte Besprechung aller Vertragsbestandteile mit unseren Experten.",
            "color_scheme": "blue"
        },
        {
            "number": 6,
            "title": "Objektbesichtigung & Notartermin",
            "description": "Finale Besichtigung und Beurkundung beim Notar Ihrer Wahl.",
            "color_scheme": "green"
        }
    ]
    
    default_opportunities = [
        {"title": "Langfristige Wertsteigerung", "description": "Attraktive Lage mit hohem Entwicklungspotenzial"},
        {"title": "Stabile Mieteinnahmen", "description": "Durch bewährtes Co-Living Konzept"},
        {"title": "Steuerliche Vorteile", "description": "Optimale Nutzung von Abschreibungsmöglichkeiten"},
        {"title": "Professionelle Verwaltung", "description": "Erfahrenes Management-Team vor Ort"}
    ]
    
    default_risks = [
        {"title": "Marktschwankungen", "description": "Können den Objektwert beeinflussen"},
        {"title": "Mietausfallrisiko", "description": "Trotz umfassender Versicherung möglich"},
        {"title": "Instandhaltungskosten", "description": "Können je nach Objektzustand variieren"},
        {"title": "Zinsänderungsrisiko", "description": "Bei der Anschlussfinanzierung zu beachten"}
    ]
    
    # Update existing templates with default content where fields are NULL
    op.execute(f"""
        UPDATE expose_templates 
        SET floor_plan_content = '{default_floor_plan_content}'
        WHERE floor_plan_content IS NULL
    """)
    
    op.execute(f"""
        UPDATE expose_templates 
        SET modernization_items = '{json.dumps(default_modernization_items)}'::jsonb
        WHERE modernization_items IS NULL
    """)
    
    op.execute(f"""
        UPDATE expose_templates 
        SET insurance_plans = '{json.dumps(default_insurance_plans)}'::jsonb
        WHERE insurance_plans IS NULL
    """)
    
    op.execute(f"""
        UPDATE expose_templates 
        SET process_steps_list = '{json.dumps(default_process_steps)}'::jsonb
        WHERE process_steps_list IS NULL
    """)
    
    op.execute(f"""
        UPDATE expose_templates 
        SET opportunities_list = '{json.dumps(default_opportunities)}'::jsonb
        WHERE opportunities_list IS NULL
    """)
    
    op.execute(f"""
        UPDATE expose_templates 
        SET risks_list = '{json.dumps(default_risks)}'::jsonb
        WHERE risks_list IS NULL
    """)


def downgrade() -> None:
    """Remove default content"""
    # Set all content fields back to NULL
    op.execute("""
        UPDATE expose_templates 
        SET 
            floor_plan_content = NULL,
            modernization_items = NULL,
            insurance_plans = NULL,
            process_steps_list = NULL,
            opportunities_list = NULL,
            risks_list = NULL
    """)