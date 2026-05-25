"""Capacity core tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-23
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Placeholder-Tabellen entfernen (aus Migration 0001)
    op.execute("DROP TABLE IF EXISTS capacity.locations CASCADE")
    op.execute("DROP TABLE IF EXISTS persons.occupants CASCADE")

    # capacity.locations
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS capacity.locations (
            id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            name                VARCHAR(255) NOT NULL,
            adresse             TEXT        NOT NULL DEFAULT '',
            kontingent          INTEGER     NOT NULL DEFAULT 0,
            notbett_kapazitaet  INTEGER     NOT NULL DEFAULT 0,
            is_active           BOOLEAN     NOT NULL DEFAULT TRUE,
            created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )

    # capacity.rooms
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS capacity.rooms (
            id                      UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            location_id             UUID        NOT NULL REFERENCES capacity.locations(id),
            name                    VARCHAR(255) NOT NULL,
            geschlechts_designation VARCHAR(10) NOT NULL,
            is_active               BOOLEAN     NOT NULL DEFAULT TRUE,
            created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )

    # capacity.beds
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS capacity.beds (
            id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            room_id     UUID        NOT NULL REFERENCES capacity.rooms(id),
            bett_nummer VARCHAR(50) NOT NULL,
            bett_typ    VARCHAR(20) NOT NULL CHECK (bett_typ IN ('KONTINGENT', 'NOTBETT')),
            is_active   BOOLEAN     NOT NULL DEFAULT TRUE,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_room_bett_nummer UNIQUE (room_id, bett_nummer)
        )
        """
    )

    # persons.occupants (DSGVO: kein Name, kein Foto)
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS persons.occupants (
            id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            bed_id          UUID        NOT NULL REFERENCES capacity.beds(id) UNIQUE,
            azr_id          VARCHAR(50) NOT NULL,
            alias_id        VARCHAR(100),
            geschlecht      VARCHAR(10) NOT NULL,
            belegung_start  DATE        NOT NULL,
            belegung_ende   DATE        NOT NULL,
            CONSTRAINT ck_dates CHECK (belegung_ende > belegung_start),
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )

    # capacity.system_settings (Singleton: id=1)
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS capacity.system_settings (
            id              INTEGER PRIMARY KEY DEFAULT 1,
            eu_gesamtquote  INTEGER NOT NULL DEFAULT 0,
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT single_row CHECK (id = 1)
        )
        """
    )
    # Standard-Eintrag einfügen
    op.execute(
        "INSERT INTO capacity.system_settings (eu_gesamtquote, updated_at) "
        "VALUES (0, NOW()) ON CONFLICT DO NOTHING"
    )

    # Indexes für häufige Queries
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_locations_is_active "
        "ON capacity.locations (is_active)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_rooms_location_id "
        "ON capacity.rooms (location_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_rooms_is_active "
        "ON capacity.rooms (is_active)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_beds_room_id "
        "ON capacity.beds (room_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_beds_is_active "
        "ON capacity.beds (is_active)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_occupants_bed_id "
        "ON persons.occupants (bed_id)"
    )

    # Grants für app_role auf neue Tabellen
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON capacity.locations TO app_role"
    )
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON capacity.rooms TO app_role"
    )
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON capacity.beds TO app_role"
    )
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON persons.occupants TO app_role"
    )
    op.execute(
        "GRANT SELECT, INSERT, UPDATE ON capacity.system_settings TO app_role"
    )
    op.execute("GRANT INSERT ON audit.events TO app_role")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS persons.occupants CASCADE")
    op.execute("DROP TABLE IF EXISTS capacity.system_settings CASCADE")
    op.execute("DROP TABLE IF EXISTS capacity.beds CASCADE")
    op.execute("DROP TABLE IF EXISTS capacity.rooms CASCADE")
    op.execute("DROP TABLE IF EXISTS capacity.locations CASCADE")
