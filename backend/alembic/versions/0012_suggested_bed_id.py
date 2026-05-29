"""0012 suggested_bed_id on reservations.requests

Revision ID: 0012
Revises: 0011
Create Date: 2026-05-28
"""
from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        ALTER TABLE reservations.requests
          ADD COLUMN IF NOT EXISTS suggested_bed_id UUID
            REFERENCES capacity.beds(id) ON DELETE SET NULL
    """)


def downgrade():
    op.execute("ALTER TABLE reservations.requests DROP COLUMN IF EXISTS suggested_bed_id")
