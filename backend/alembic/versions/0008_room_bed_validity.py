"""Add valid_from/valid_until to rooms; valid_from to beds; labels to rooms

Revision ID: 0008
Revises: 0007
Create Date: 2026-05-26
"""
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Room validity date range
    op.execute("ALTER TABLE capacity.rooms ADD COLUMN IF NOT EXISTS valid_from DATE")
    op.execute("ALTER TABLE capacity.rooms ADD COLUMN IF NOT EXISTS valid_until DATE")

    # Bed valid_from (planned availability start)
    op.execute("ALTER TABLE capacity.beds ADD COLUMN IF NOT EXISTS valid_from DATE")

    # Ensure rooms have labels column (may already exist from 0006)
    op.execute("ALTER TABLE capacity.rooms ADD COLUMN IF NOT EXISTS labels TEXT[] DEFAULT '{}' NOT NULL")


def downgrade() -> None:
    op.execute("ALTER TABLE capacity.rooms DROP COLUMN IF EXISTS valid_from")
    op.execute("ALTER TABLE capacity.rooms DROP COLUMN IF EXISTS valid_until")
    op.execute("ALTER TABLE capacity.beds DROP COLUMN IF EXISTS valid_from")
