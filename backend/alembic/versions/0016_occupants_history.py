"""0016_occupants_history

Entfernt UNIQUE(bed_id) auf persons.occupants, um mehrere historische
Belegungsdatensätze pro Bett zu erlauben (Zeitreihendarstellung).
Die Einzigartigkeit aktiver Belegungen wird auf App-Ebene sichergestellt.

Revision ID: 0016
Revises: 0015
Create Date: 2026-05-31
"""
from alembic import op

revision = '0016'
down_revision = '0015'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE persons.occupants DROP CONSTRAINT IF EXISTS occupants_bed_id_key")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS persons.uix_occupants_bed_active")
    op.execute("ALTER TABLE persons.occupants ADD CONSTRAINT occupants_bed_id_key UNIQUE (bed_id)")
