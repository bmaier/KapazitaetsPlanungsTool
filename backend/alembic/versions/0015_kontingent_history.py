"""0015_kontingent_history

Revision ID: 0015
Revises: 0014
Create Date: 2026-05-31
"""
from alembic import op

revision = '0015'
down_revision = '0014'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE capacity.kontingent_history (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            location_id UUID NOT NULL REFERENCES capacity.locations(id),
            kontingent_value INTEGER NOT NULL,
            valid_from TIMESTAMPTZ NOT NULL DEFAULT now(),
            actor_id TEXT
        )
    """)
    op.execute("""
        CREATE INDEX ix_kontingent_history_location_valid_from
        ON capacity.kontingent_history (location_id, valid_from DESC)
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS capacity.kontingent_history")
