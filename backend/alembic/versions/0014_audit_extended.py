"""audit.events erweitern: actor_id, actor_role, location_id, entity_type, entity_id + Indexes

Revision ID: 0014
Revises: 0013
Create Date: 2026-05-29
"""
from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE audit.events
          ADD COLUMN IF NOT EXISTS actor_id    VARCHAR(255),
          ADD COLUMN IF NOT EXISTS actor_role  VARCHAR(50),
          ADD COLUMN IF NOT EXISTS location_id UUID,
          ADD COLUMN IF NOT EXISTS entity_type VARCHAR(50),
          ADD COLUMN IF NOT EXISTS entity_id   VARCHAR(255)
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_events_created_at  ON audit.events (created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_events_entity_id   ON audit.events (entity_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_events_location_id ON audit.events (location_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_events_actor_id    ON audit.events (actor_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_audit_events_actor_id")
    op.execute("DROP INDEX IF EXISTS ix_audit_events_location_id")
    op.execute("DROP INDEX IF EXISTS ix_audit_events_entity_id")
    op.execute("DROP INDEX IF EXISTS ix_audit_events_created_at")
    op.execute("""
        ALTER TABLE audit.events
          DROP COLUMN IF EXISTS actor_id,
          DROP COLUMN IF EXISTS actor_role,
          DROP COLUMN IF EXISTS location_id,
          DROP COLUMN IF EXISTS entity_type,
          DROP COLUMN IF EXISTS entity_id
    """)
