"""Reservation and tasks tables

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-23
"""
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # reservations.requests
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS reservations.requests (
            id                   UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
            requester_location_id UUID        NOT NULL REFERENCES capacity.locations(id),
            target_location_id   UUID         NOT NULL REFERENCES capacity.locations(id),
            azr_id               VARCHAR(50)  NOT NULL,
            geschlecht           VARCHAR(10)  NOT NULL,
            geburtsjahr          SMALLINT     NOT NULL CHECK(geburtsjahr > 1900),
            herkunftsland        CHAR(3)      NOT NULL,
            belegung_start       DATE         NOT NULL,
            belegung_ende        DATE         NOT NULL CHECK(belegung_ende > belegung_start),
            status               VARCHAR(20)  NOT NULL
                CHECK(status IN ('PENDING','CONFIRMED','REJECTED','CANCELLED','TRANSFERRED'))
                DEFAULT 'PENDING',
            confirmed_bed_id     UUID         REFERENCES capacity.beds(id),
            created_at           TIMESTAMPTZ  NOT NULL DEFAULT now(),
            updated_at           TIMESTAMPTZ  NOT NULL DEFAULT now()
        )
        """
    )

    # tasks.inbox
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS tasks.inbox (
            id                      UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
            location_id             UUID         NOT NULL REFERENCES capacity.locations(id),
            related_reservation_id  UUID         REFERENCES reservations.requests(id),
            task_type               VARCHAR(50)  NOT NULL,
            priority                VARCHAR(10)  NOT NULL CHECK(priority IN ('LOW','MEDIUM','HIGH')),
            status                  VARCHAR(20)  NOT NULL
                CHECK(status IN ('OPEN','IN_PROGRESS','DONE','DISMISSED'))
                DEFAULT 'OPEN',
            title                   VARCHAR(255) NOT NULL,
            body                    TEXT         NOT NULL DEFAULT '',
            created_at              TIMESTAMPTZ  NOT NULL DEFAULT now(),
            updated_at              TIMESTAMPTZ  NOT NULL DEFAULT now()
        )
        """
    )

    # Indexes
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_requests_status_location "
        "ON reservations.requests (status, requester_location_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_requests_target_status "
        "ON reservations.requests (target_location_id, status)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_tasks_status_location "
        "ON tasks.inbox (status, location_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_tasks_location_created "
        "ON tasks.inbox (location_id, created_at)"
    )

    # Grants
    op.execute(
        "GRANT INSERT, SELECT, UPDATE ON reservations.requests TO bordercap_app"
    )
    op.execute(
        "GRANT INSERT, SELECT, UPDATE ON tasks.inbox TO bordercap_app"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS tasks.inbox CASCADE")
    op.execute("DROP TABLE IF EXISTS reservations.requests CASCADE")
