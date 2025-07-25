"""Replace opportunities and risks lists with sections

Revision ID: f0b6f636ab1f
Revises: populate_template_content
Create Date: 2025-07-07 23:31:01.952309

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "f0b6f636ab1f"
down_revision: Union[str, None] = "populate_template_content"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "expose_templates",
        sa.Column("opportunities_risks_sections", sa.JSON(), nullable=True),
    )
    op.drop_column("expose_templates", "risks_list")
    op.drop_column("expose_templates", "opportunities_list")
    # ### end Alembic commands ###
    
    # Add default content for opportunities and risks
    default_sections = [
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
    
    import json
    
    op.execute(f"""
        UPDATE expose_templates 
        SET opportunities_risks_sections = '{json.dumps(default_sections)}'::jsonb
        WHERE opportunities_risks_sections IS NULL
    """)


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "expose_templates",
        sa.Column(
            "opportunities_list",
            postgresql.JSON(astext_type=sa.Text()),
            autoincrement=False,
            nullable=True,
        ),
    )
    op.add_column(
        "expose_templates",
        sa.Column(
            "risks_list",
            postgresql.JSON(astext_type=sa.Text()),
            autoincrement=False,
            nullable=True,
        ),
    )
    op.drop_column("expose_templates", "opportunities_risks_sections")
    # ### end Alembic commands ###
