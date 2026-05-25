"""Add labels, coordinates, validity dates to locations; deaktiviert_ab to beds

Revision ID: 0007
Revises: 0006
Create Date: 2026-05-25
"""
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Labels + coordinates + validity dates for locations
    op.execute("ALTER TABLE capacity.locations ADD COLUMN labels TEXT[] DEFAULT '{}' NOT NULL")
    op.execute("ALTER TABLE capacity.locations ADD COLUMN lat DOUBLE PRECISION")
    op.execute("ALTER TABLE capacity.locations ADD COLUMN lon DOUBLE PRECISION")
    op.execute("ALTER TABLE capacity.locations ADD COLUMN valid_from DATE")
    op.execute("ALTER TABLE capacity.locations ADD COLUMN valid_until DATE")

    # Time-based bed deactivation
    op.execute("ALTER TABLE capacity.beds ADD COLUMN deaktiviert_ab DATE")


def downgrade() -> None:
    op.execute("ALTER TABLE capacity.locations DROP COLUMN labels")
    op.execute("ALTER TABLE capacity.locations DROP COLUMN lat")
    op.execute("ALTER TABLE capacity.locations DROP COLUMN lon")
    op.execute("ALTER TABLE capacity.locations DROP COLUMN valid_from")
    op.execute("ALTER TABLE capacity.locations DROP COLUMN valid_until")

    op.execute("ALTER TABLE capacity.beds DROP COLUMN deaktiviert_ab")
