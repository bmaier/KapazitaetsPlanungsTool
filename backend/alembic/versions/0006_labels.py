"""Add labels TEXT[] column to rooms, beds, and occupants

Revision ID: 0006
Revises: 0005
Create Date: 2026-05-25
"""
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE capacity.rooms ADD COLUMN labels TEXT[] DEFAULT '{}' NOT NULL")
    op.execute("ALTER TABLE capacity.beds ADD COLUMN labels TEXT[] DEFAULT '{}' NOT NULL")
    op.execute("ALTER TABLE persons.occupants ADD COLUMN labels TEXT[] DEFAULT '{}' NOT NULL")


def downgrade() -> None:
    op.execute("ALTER TABLE capacity.rooms DROP COLUMN labels")
    op.execute("ALTER TABLE capacity.beds DROP COLUMN labels")
    op.execute("ALTER TABLE persons.occupants DROP COLUMN labels")
