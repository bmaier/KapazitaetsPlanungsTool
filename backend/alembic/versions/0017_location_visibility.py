"""Add show_on_map to locations

Revision ID: 0017
Revises: 0016
Create Date: 2026-06-05
"""
from alembic import op

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE capacity.locations ADD COLUMN show_on_map BOOLEAN NOT NULL DEFAULT TRUE"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE capacity.locations DROP COLUMN show_on_map")
