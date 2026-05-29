"""rename ANKUNFT→WARTEBEREICH and add WARTEPLATZ bett_typ

Revision ID: 0013
Revises: 0012
Create Date: 2026-05-28
"""
from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Rename room_type value ANKUNFT → WARTEBEREICH
    op.execute("""
        UPDATE capacity.rooms
           SET room_type = 'WARTEBEREICH'
         WHERE room_type = 'ANKUNFT'
    """)

    # 2. Drop the old CHECK constraint on bett_typ and replace it with one
    #    that also allows WARTEPLATZ (added for Wartebereich/Warteplatz spaces).
    #    The constraint name was set in migration 0002.
    op.execute("""
        ALTER TABLE capacity.beds
          DROP CONSTRAINT IF EXISTS beds_bett_typ_check
    """)
    op.execute("""
        ALTER TABLE capacity.beds
          ADD CONSTRAINT beds_bett_typ_check
          CHECK (bett_typ IN ('KONTINGENT', 'NOTBETT', 'DOPPEL', 'WARTEPLATZ'))
    """)


def downgrade() -> None:
    op.execute("""
        UPDATE capacity.rooms
           SET room_type = 'ANKUNFT'
         WHERE room_type = 'WARTEBEREICH'
    """)
    op.execute("""
        ALTER TABLE capacity.beds
          DROP CONSTRAINT IF EXISTS beds_bett_typ_check
    """)
    op.execute("""
        ALTER TABLE capacity.beds
          ADD CONSTRAINT beds_bett_typ_check
          CHECK (bett_typ IN ('KONTINGENT', 'NOTBETT'))
    """)
