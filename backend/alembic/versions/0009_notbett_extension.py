"""Add extended_once to occupants for notbett single-extension tracking

Revision ID: 0009
Revises: 0008
Create Date: 2026-05-27
"""
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE persons.occupants ADD COLUMN IF NOT EXISTS "
        "extended_once BOOLEAN NOT NULL DEFAULT FALSE"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE persons.occupants DROP COLUMN IF EXISTS extended_once")
