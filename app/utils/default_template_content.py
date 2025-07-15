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

DEFAULT_OPPORTUNITIES_RISKS_SECTIONS = [
    {
        "headline": "Chancen und Risiken beim Erwerb von Immobilien zur Kapitalanlage",
        "content": "Jede Investition enthält Chancen und Risiken. Auch bei dem vorliegenden Angebot besteht die Möglichkeit einer wirtschaftlichen Verschlechterung - sei es aus rechtlichen, wirtschaftlichen oder steuerlichen Gründen. Nachstehend sollen für einen Erwerber die Chancen, aber auch die Risiken einer möglichen Investition in ein Immobilienangebot dargestellt werden, um die individuelle Anlageentscheidung zu unterstützen.",
        "is_expanded_by_default": True
    },
    {
        "headline": "Standort",
        "content": "Der Kauf einer Immobilie kann eine sehr rentable Investitionsentscheidung sein, wenn sich der Standort auf Dauer bewährt. Dafür sind insbesondere Lage, Verkehrsanbindung, örtliche und regionale Wirtschaftskraft sowie Zukunftspotentiale, Wirtschaftsstruktur usw. entscheidend. Werden diese Faktoren bei der Beurteilung einer Investition nicht berücksichtigt bzw. entwickelt sich der gewählte Standort langfristig nicht positiv, kann dies dazu führen, dass die Immobilieninvestition für den Käufer keine gewinnbringende Investition darstellt. Deshalb wird grundsätzlich empfohlen, vor der endgültigen Kaufentscheidung eine persönliche Besichtigung des Standorts vorzunehmen, auch bei entfernten Immobilienangeboten.",
        "is_expanded_by_default": False
    },
    {
        "headline": "Fertigstellung",
        "content": "Nach dem Bauträgervertrag wird ein fester Erwerbpreis und ein Fertigstellungstermin vereinbart. Das Risiko von Kostensteigerungen, Bauzeit sowie der Fertigstellung übernimmt der Bauträger. Allerdings kann auch dieser, beispielsweise durch gravierende Baumängel oder durch den Ausfall bzw. die Insolvenz seiner Vertragspartner (Handwerkern, Lieferanten usw.) leistungsunfähig werden. Dann können Herstellungs-, Gewährleistungs- oder Schadensansprüche nur bedingt oder gar nicht gegenüber dem Bauträger durchgesetzt werden.",
        "is_expanded_by_default": False
    },
    {
        "headline": "Wertentwicklung",
        "content": "Eine Immobilie stellt eine langfristige Anlageform dar. Dennoch ist der Verkauf der Immobilie rechtlich jederzeit möglich. Den Verkaufspreis bestimmen die zum Veräußerungszeitpunkt herrschenden Marktverhältnisse. Es besteht das Risiko, dass bei einem Verkauf zu einem ungünstigen Zeitpunkt Verluste entstehen oder die Käufersuche längere Zeit andauert. Der Wert der Immobilie kann daher eventuell nicht kurzfristig in Barmittel umgesetzt werden. Zusätzlich kann ein Verkaufsdruck zu erheblichen Preisreduzierungen führen. Allerdings hat eine Immobilie als langfristige Anlageform grundsätzlich eine positive Wertentwicklung. Wird bei einem späteren Verkauf ein Gewinn erzielt, ist die Spekulationsfrist für private Veräußerungsgeschäfte (zur Zeit 10 Jahre) zu beachten.",
        "is_expanded_by_default": False
    },
    {
        "headline": "Mieteinnahmen",
        "content": "Wie sich die Mieten zukünftig entwickeln, hängt von einer Reihe unterschiedlichster Faktoren ab und kann daher nicht garantiert werden. Über die Dauer des Investitionszeitraumes sind die Mietsteigerungen schwer abzuschätzen. Unvorhersehbare Entwicklungen, wie z. B. gesetzliche Änderungen, gewandelte Ansprüche der Mieter oder strukturelle Veränderungen eines Wirtschaftsraumes, können die Mieteinnahmen positiv oder negativ beeinflussen.",
        "is_expanded_by_default": False
    },
    {
        "headline": "Mietgarantie",
        "content": "Die Werthaltigkeit einer Mietgarantie hängt stets von der Bonität des Mietgarantiegebers ab, die ggf. vor dem Immobilienerwerb gesondert geprüft werden muss. Die tatsächlich erzielte Miete nach Ablauf der Garantiefrist wird vom Markt bestimmt. Sie kann deshalb höher oder niedriger als die Garantiemiete sein.",
        "is_expanded_by_default": False
    },
    {
        "headline": "Instandhaltung",
        "content": "Zur Abdeckung von Renovierungs- oder Instandhaltungsmaßnahmen usw. wird in der Regel eine Instandhaltungsrücklage gebildet. Die Höhe der Instandhaltungsrücklage kann aber gegebenenfalls nicht ausreichen, um die erfahrungsgemäß nach 10 bis 20 Jahren anfallenden höheren Instandhaltungskosten zu bezahlen. Dadurch können zusätzliche Umlagen der Eigentümergemeinschaft erforderlich sein. Beim Erwerb einer Eigentumswohnung aus zweiter Hand sind neben einer intensiven Besichtigung der Wohnung und der Gemeinschaftsanlagen auch die Protokolle der letzten Eigentümerversammlungen zu prüfen, aus denen die beschlossenen oder bevorstehenden Maßnahmen ersichtlich sind.",
        "is_expanded_by_default": False
    },
    {
        "headline": "Steuerliche Grundlagen",
        "content": "Zur Berechnung der individuellen steuerlichen Auswirkung wird vor einer Kaufentscheidung die Hinzuziehung eines Steuerberaters empfohlen. Auf das mögliche Risiko einer Steuergesetzesänderung wird hingewiesen.",
        "is_expanded_by_default": False
    },
    {
        "headline": "Zusatzinformationen für Management-/Betreiberimmobilien",
        "content": "Management-/Betreiberimmobilien wie beispielsweise Gewerbeimmobilien, Pflegeheime, Studentenwohnheime, Boardinghäuser, usw. weisen gegenüber den allgemeinen Wohnimmobilien einige Besonderheiten auf - so insbesondere in der Bauweise, im Nutzerkreis, in nutzungsspezifischen Vertragskonzeptionen sowie der Drittverwendungsmöglichkeit usw. Der Erwerb ist deshalb mit weiteren Chancen und Risiken verbunden, auf die nachfolgend hingewiesen wird.",
        "is_expanded_by_default": False
    },
    {
        "headline": "Fertigstellung bei Spezialimmobilien",
        "content": "Sollte sich die Fertigstellung des kompletten Gebäudes verzögern - egal ob durch oder ohne Verschulden des Bauträgers oder der von ihm beauftragten Unternehmen bzw. durch unbekannte Einflüsse von außen - kann dies, falls sich die Fertigstellung solange verzögert und so die vereinbarte Frist zur Übergabe der Spezialimmobilie an den Mieter nicht eingehalten werden kann, dazu führen, dass der Mieter vom Mietvertrag zurücktritt und/oder Schadenersatzansprüche geltend macht. Im Falle eines Vertragsrücktritts ist es erforderlich, einen neuen Betreiber zu finden. Gelingt dies nicht, würden die Mieteinnahmen komplett ausfallen. Darüber hinaus führt die Verzögerung der Fertigstellung zu einer Verschiebung der Mietzahlungspflicht und damit zu erhöhten Finanzierungskosten.",
        "is_expanded_by_default": False
    },
    {
        "headline": "Wertentwicklung bei Management-/Betreiberimmobilien",
        "content": "Die Wertentwicklung einer Management-/Betreiberimmobilie hängt neben den zuvor genannten Bedingungen von dem Bedarf an Immobilien konkret dieser Art und den Nutzungsmöglichkeiten ab und ist stark geprägt von dem durch die Immobilie erzielbaren Ertrag, also den Miet-/Pachteinnahmen. Dies kann dazu führen, dass der Wert der Immobilie sich negativ entwickelt und auch erheblich unter dem Einstandspreis liegen kann. Daneben ist die Wertentwicklung auch von dem Angebot vergleichbarer Immobilien abhängig. Werden solche insbesondere im näheren Einzugsbereich des Objektes errichtet, kann sich damit die Nachfrage, die erzielbare Miete und letztlich auch der Wert der Immobilie selbst verringern.",
        "is_expanded_by_default": False
    },
    {
        "headline": "Weiterveräußerung",
        "content": "Bei einem Verkauf zu einem ungünstigen Zeitpunkt kann die Käufersuche für eine Management- / Betreiberimmobilie längere Zeit, auch über ein Jahr hinweg dauern. Der potenzielle Erwerber ist über die Teilungserklärung/Gemeinschaftsverordnung und Verträge verpflichtet, in die bestehenden Verträge einzutreten.",
        "is_expanded_by_default": False
    }
]

DEFAULT_LIABILITY_DISCLAIMER = """Alle Angaben, Berechnungen und Zahlenbeispiele dieser Unterlagen entsprechen dem augenblicklichen Planungsstand. Änderungen der Bauausführung und der Material- bzw. Baustoffauswahl bleiben soweit sie erforderlich, gleichwertig und dem Erwerber zumutbar sind, vorbehalten.

Maßliche Differenzen, statische und bauliche Maßnahmen, die sich aus architektonischen, bau- oder genehmigungstechnischen Gründen ergeben, jedoch keinen Einfluss auf die Qualität und Nutzung des Gebäudes haben, bleiben ebenso vorbehalten. Einrichtungsgegenstände, die in den Planunterlagen eingezeichnet sind, dienen ausschließlich dem besseren Vorstellungsvermögen und sind, falls nicht ausdrücklich im Leistungsbedarf beschrieben, nicht Teil. Die aufgeführten Bilder sind als Werbebeispiele anzusehen.

Haftung
Für umfassende oder unvollständige Angaben oder für die Verletzung eventuell bestehender Aufklärungsoder Hinweispflichten haftet die Invenio GmbH nur bei Vorsatz oder grober Fahrlässigkeit. Eine Haftung für Schäden aus der Verletzung des Lebens, des Körpers oder der Gesundheit ist weder ausgeschlossen, noch begrenzt. Eine Haftung für den Eintritt insbesondere eines angegebenen Steuervortells oder Progression oder für die Abweichung insbesondere durch zukünftige wirtschaftliche Entwicklungen, durch Gesetzesänderung oder Änderung der Rechtsprechung kann nicht übernommen werden. Es kann von der Invenio GmbH keine Garantie oder Gewähr über mit der Investition verfolgten wirtschaftlichen, steuerlichen oder sonstigen Ziele übernommen werden."""

DEFAULT_ONSITE_MANAGEMENT_SERVICES = [
    {"service": "Neuvermietung bei Mieterschäden inkl. Bonitätsprüfung", "description": None},
    {"service": "Mietvertragsstellung nach aktueller Rechtsprechung", "description": None},
    {"service": "Protokollierte Wohnungsübergaben inkl. anschließender Mietraumauflung", "description": None},
    {"service": "Jährliche Betriebskostenabrechnung", "description": None},
    {"service": "Kaufmännerverwaltung- und Abrechnung bei Auszug", "description": None},
    {"service": "Mieterstützung und Kommunikation", "description": None},
    {"service": "Koordination von Instandhaltungs- und Instandsetzungsmaßnahmen/Modernisierungen", "description": None},
    {"service": "Durchsetzen von Mieterhöhungsverlangen nach aktueller Rechtsprechung", "description": None},
    {"service": "Regelmäßige Wirtschaftlichkeitsberechnung mit Prüfung von Renditeerhöhungspotential und Entwicklungschancen", "description": None},
    {"service": "***Finanzmanagement", "description": None},
    {"service": "Reporting", "description": None}
]

DEFAULT_ONSITE_MANAGEMENT_PACKAGE = {
    "name": "ANGEBOT 360°+",
    "price": 142.80,
    "unit": "€ brutto monatlich pro Wohnung (WG-Konzept mit 4 Zimmern)"
}

DEFAULT_COLIVING_CONTENT = """Kapital schafft Verantwortung!
Doch welche Investments schaffen gesellschaftlichen Mehrwert bei guter Rendite?

Das Investment in Co-Living ist eine Win-Win-Situation für Investor und Mieter. Mit dem Investment in Co-Living Konzepte ermöglichst du einem Young Professional ein schönes und trotzdem leistbares Zuhause und sicherst dein Kapital gegen die Inflation.

Co-Living ist mehr als nur geteilter Wohnraum. Es ist eine moderne Lebensform, die auf Gemeinschaft, Nachhaltigkeit und Flexibilität setzt. In unseren sorgfältig gestalteten Co-Living-Spaces finden junge Berufstätige nicht nur ein Zuhause, sondern eine Community. Die voll möblierten Zimmer, gemeinsamen Arbeitsbereiche und durchdachten Gemeinschaftsflächen schaffen ein Umfeld, in dem sich persönliche Entwicklung und soziale Interaktion ideal ergänzen."""

DEFAULT_SPECIAL_FEATURES = [
    {
        "title": "Möblierung (Bett, Schrank, Schreibtisch, Stuhl, Spiegel, Lampe, Vorhänklung)",
        "description": None
    },
    {
        "title": "Mietausfsallrisko verteilt auf 4 Mieter",
        "description": None
    },
    {
        "title": "Erstausmietungsgarantie in voller Höhe (im Kaufvertrag festgehalten)",
        "description": None
    },
    {
        "title": "Gewährleistung der Modernisierung für 5 Jahre (im Kaufvertrag festgehalten)",
        "description": None
    },
    {
        "title": "Schutz vor Mietpiegel durch 3 Faktoren:\n- Modernisierung der Wohnungen auf Neubaustandard\n- Einzelzimmervermietung\n- Teilmöblierte Vermietung",
        "description": None
    },
    {
        "title": "Geringer Zeitaufwand:\nÜbergabe der Mieter in die Sondereigentumsverwaltung (siehe Angebot)",
        "description": None
    }
]

DEFAULT_HIGHLIGHTS = [
    {
        "label": "Mietrendite",
        "value": "{{gross_rental_yield}}%",
        "icon": "percent",
        "color": "green",
        "enabled": True,
        "order": 1,
        "condition": "gross_rental_yield > 4"  # Only show if rental yield is above 4%
    },
    {
        "label": "Positiver Cashflow",
        "value": "{{monthly_net_income}}",  # Added dynamic value
        "icon": "trending-up",
        "color": "blue",
        "enabled": False,
        "order": 2,
        "condition": "monthly_net_income > 0"  # Show only if cashflow is positive
    },
    {
        "label": "Balkon / Terrasse",
        "value": "{{size_sqm}} m²",  # Show balcony size if available
        "icon": "home",
        "color": "amber",
        "enabled": False,
        "order": 3,
        "condition": "has_balcony = true"  # Only show if property has balcony
    },
    {
        "label": "Hinterlandsbebauung",
        "value": None,
        "icon": "building",
        "color": "gray",
        "enabled": False,
        "order": 4,
        "condition": "backyard_development = true"  # Check project-level field
    },
    {
        "label": "Erhaltungsaufwand",
        "value": "{{initial_maintenance_expenses_formatted}}",
        "icon": "wrench",
        "color": "blue",
        "enabled": False,
        "order": 5,
        "condition": "initial_maintenance_expenses > 0"  # Only show if there are maintenance expenses
    },
    {
        "label": "Übernahme SEV im 1. Jahr",
        "value": None,
        "icon": "shield-check",
        "color": "green",
        "enabled": False,
        "order": 6,
        "condition": "sev_takeover_one_year = true"  # Check project-level field
    },
    {
        "label": "Energieeffizienz",
        "value": "Klasse {{energy_class}}",  # Added "Klasse" prefix
        "icon": "zap",
        "color": "green",
        "enabled": False,
        "order": 7,
        "condition": "energy_class <= D"  # Only show for energy class D or better
    },
    {
        "label": "Erstvermietungsgarantie",
        "value": None,
        "icon": "check-circle",
        "color": "blue",
        "enabled": False,
        "order": 8,
        "condition": None  # Manual configuration needed
    },
    {
        "label": "Gewährleistung",
        "value": "5 Jahre",  # Default warranty period
        "icon": "shield",
        "color": "amber",
        "enabled": False,
        "order": 9,
        "condition": None  # Manual configuration needed
    },
    {
        "label": "{{parking_type}}",  # Dynamic label showing the parking type
        "value": "{{purchase_price_parking}}",  # Show parking price if available
        "icon": "car",
        "color": "gray",
        "enabled": False,
        "order": 10,
        "condition": "has_parking = true"  # Only show if property has parking
    },
    {
        "label": "Baujahr",
        "value": "{{construction_year}}",
        "icon": "calendar",
        "color": "blue",
        "enabled": False,
        "order": 11,
        "condition": "construction_year > 2020"  # Only show for newer buildings
    },
    {
        "label": "Übernahme Sonderumlagen",
        "value": "{{takeover_special_charges_amount}} für {{takeover_special_charges_years}} Jahre",
        "icon": "receipt",
        "color": "green",
        "enabled": False,
        "order": 12,
        "condition": "takeover_special_charges_years > 0 OR takeover_special_charges_amount > 0"  # Show if either field is set
    }
]

def get_default_template_content():
    """Returns a dictionary with all default template content"""
    return {
        "floor_plan_content": DEFAULT_FLOOR_PLAN_CONTENT,
        "modernization_items": DEFAULT_MODERNIZATION_ITEMS,
        "insurance_plans": DEFAULT_INSURANCE_PLANS,
        "process_steps_list": DEFAULT_PROCESS_STEPS,
        "opportunities_risks_sections": DEFAULT_OPPORTUNITIES_RISKS_SECTIONS,
        "liability_disclaimer_content": DEFAULT_LIABILITY_DISCLAIMER,
        "onsite_management_services": DEFAULT_ONSITE_MANAGEMENT_SERVICES,
        "onsite_management_package": DEFAULT_ONSITE_MANAGEMENT_PACKAGE,
        "coliving_content": DEFAULT_COLIVING_CONTENT,
        "special_features_items": DEFAULT_SPECIAL_FEATURES,
        "highlights": DEFAULT_HIGHLIGHTS
    }