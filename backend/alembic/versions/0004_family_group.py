"""Add family_group_id to persons.occupants

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-24
"""
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE persons.occupants ADD COLUMN family_group_id UUID")


def downgrade() -> None:
    op.execute("ALTER TABLE persons.occupants DROP COLUMN family_group_id")
