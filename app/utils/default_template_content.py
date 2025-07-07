"""Default content for expose templates"""

DEFAULT_FLOOR_PLAN_CONTENT = "10 Jahre Erfahrung in der Grundrissoptimierung für maximale Mietertragskraft"

DEFAULT_MODERNIZATION_ITEMS = [
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

DEFAULT_INSURANCE_PLANS = [
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

DEFAULT_PROCESS_STEPS = [
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

DEFAULT_OPPORTUNITIES = [
    {"title": "Langfristige Wertsteigerung", "description": "Attraktive Lage mit hohem Entwicklungspotenzial"},
    {"title": "Stabile Mieteinnahmen", "description": "Durch bewährtes Co-Living Konzept"},
    {"title": "Steuerliche Vorteile", "description": "Optimale Nutzung von Abschreibungsmöglichkeiten"},
    {"title": "Professionelle Verwaltung", "description": "Erfahrenes Management-Team vor Ort"}
]

DEFAULT_RISKS = [
    {"title": "Marktschwankungen", "description": "Können den Objektwert beeinflussen"},
    {"title": "Mietausfallrisiko", "description": "Trotz umfassender Versicherung möglich"},
    {"title": "Instandhaltungskosten", "description": "Können je nach Objektzustand variieren"},
    {"title": "Zinsänderungsrisiko", "description": "Bei der Anschlussfinanzierung zu beachten"}
]

def get_default_template_content():
    """Returns a dictionary with all default template content"""
    return {
        "floor_plan_content": DEFAULT_FLOOR_PLAN_CONTENT,
        "modernization_items": DEFAULT_MODERNIZATION_ITEMS,
        "insurance_plans": DEFAULT_INSURANCE_PLANS,
        "process_steps_list": DEFAULT_PROCESS_STEPS,
        "opportunities_list": DEFAULT_OPPORTUNITIES,
        "risks_list": DEFAULT_RISKS
    }