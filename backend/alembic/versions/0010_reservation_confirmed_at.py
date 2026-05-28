"""Add confirmed_at to reservations.requests

Revision ID: 0010
Revises: 0009
Create Date: 2026-05-28
"""
from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE reservations.requests "
        "ADD COLUMN IF NOT EXISTS confirmed_at TIMESTAMPTZ"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE reservations.requests "
        "DROP COLUMN IF EXISTS confirmed_at"
    )
