"""Beds: bett_nummer UNIQUE nur auf aktiven Betten (partieller Index)

Ersetzt den globalen UNIQUE-Constraint (room_id, bett_nummer) durch einen
partiellen UNIQUE INDEX WHERE is_active = true, damit soft-gelöschte Betten
die Nummer nicht dauerhaft blockieren.

Revision ID: 0019
Revises: 0018
Create Date: 2026-06-07
"""
from alembic import op

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE capacity.beds DROP CONSTRAINT uq_room_bett_nummer")
    op.execute("""
        CREATE UNIQUE INDEX uq_room_bett_nummer_active
            ON capacity.beds (room_id, bett_nummer)
            WHERE is_active = true
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS capacity.uq_room_bett_nummer_active")
    op.execute("""
        ALTER TABLE capacity.beds
            ADD CONSTRAINT uq_room_bett_nummer UNIQUE (room_id, bett_nummer)
    """)
