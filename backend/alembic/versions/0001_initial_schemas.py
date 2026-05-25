"""Initial schemas

Revision ID: 0001
Revises:
Create Date: 2026-05-23

Schemas created by init.sql (PostgreSQL init-Skript beim ersten Container-Start).
Diese Migration dokumentiert den initialen Zustand und ist idempotent.
"""
from alembic import op

# Revision-Identifikatoren
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Schemata werden bereits durch infra/postgres/init.sql erstellt.
    Diese Migration registriert den Zustand in der Alembic-Versionstabelle
    und fügt einen Idempotenz-Kommentar hinzu.
    """
    # Schemata idempotent erstellen (falls Migration ohne init.sql läuft, z.B. in Tests)
    op.execute("CREATE SCHEMA IF NOT EXISTS capacity")
    op.execute("CREATE SCHEMA IF NOT EXISTS reservations")
    op.execute("CREATE SCHEMA IF NOT EXISTS persons")
    op.execute("CREATE SCHEMA IF NOT EXISTS audit")
    op.execute("CREATE SCHEMA IF NOT EXISTS tasks")
    op.execute("CREATE SCHEMA IF NOT EXISTS reference_data")

    # Placeholder-Tabellen idempotent erstellen
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS capacity.locations (
            id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            created_at TIMESTAMPTZ NOT NULL    DEFAULT NOW()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS persons.occupants (
            id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            created_at TIMESTAMPTZ NOT NULL    DEFAULT NOW()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS audit.events (
            id         UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
            event_type VARCHAR(100) NOT NULL,
            payload    JSONB,
            created_at TIMESTAMPTZ  NOT NULL    DEFAULT NOW()
        )
        """
    )


def downgrade() -> None:
    """
    Downgrade entfernt nur die Placeholder-Tabellen, nicht die Schemata selbst,
    da diese möglicherweise durch andere Prozesse befüllt wurden.
    """
    op.execute("DROP TABLE IF EXISTS audit.events")
    op.execute("DROP TABLE IF EXISTS persons.occupants")
    op.execute("DROP TABLE IF EXISTS capacity.locations")
