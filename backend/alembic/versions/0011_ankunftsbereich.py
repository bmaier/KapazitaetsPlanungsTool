"""Add room_type for Ankunftsbereich support

Revision ID: 0011
Revises: 0010
Create Date: 2026-05-28
"""
from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE capacity.rooms "
        "ADD COLUMN IF NOT EXISTS room_type VARCHAR(20) NOT NULL DEFAULT 'STANDARD'"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE capacity.rooms "
        "DROP COLUMN IF EXISTS room_type"
    )
