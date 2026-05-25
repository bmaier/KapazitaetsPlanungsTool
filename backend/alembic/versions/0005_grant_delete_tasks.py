"""Grant DELETE on tasks.inbox to bordercap_app

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-24
"""
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("GRANT DELETE ON tasks.inbox TO bordercap_app")


def downgrade() -> None:
    op.execute("REVOKE DELETE ON tasks.inbox FROM bordercap_app")
