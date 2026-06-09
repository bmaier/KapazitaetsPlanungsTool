"""
Einmalige Bereinigung: Alle Demo-Standorte und zugehörige Daten entfernen.

Die 5 Demo-Standorte (Frankfurt, München, Passau, Hamburg, Kiefersfelden)
haben feste UUIDs nach dem Muster a1b2c3d4-00xx-… und wurden nur für
Entwicklung und Demos angelegt. Diese Migration entfernt sie und alle
abhängigen Zeilen in der korrekten FK-Reihenfolge.

Idempotent: wirkt sich nicht aus wenn bereits gelöscht.
Down: absichtlich kein Rollback (Demo-Daten sollen nicht wiederhergestellt werden).
"""

from alembic import op

DEMO_LOCATION_IDS = [
    "a1b2c3d4-0001-0001-0001-000000000001",
    "a1b2c3d4-0002-0002-0002-000000000002",
    "a1b2c3d4-0003-0003-0003-000000000003",
    "a1b2c3d4-0004-0004-0004-000000000004",
    "a1b2c3d4-0005-0005-0005-000000000005",
]

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    ids = "{" + ",".join(DEMO_LOCATION_IDS) + "}"

    # 1. Belegungslabels (keine FK — direkt über occupant JOIN)
    op.execute(f"""
        DELETE FROM persons.occupant_labels ol
        USING persons.occupants o
        JOIN capacity.beds b ON b.id = o.bed_id
        JOIN capacity.rooms r ON r.id = b.room_id
        WHERE ol.occupant_id = o.id
          AND r.location_id = ANY('{ids}'::uuid[])
    """)

    # 2. Belegungen
    op.execute(f"""
        DELETE FROM persons.occupants o
        USING capacity.beds b
        JOIN capacity.rooms r ON r.id = b.room_id
        WHERE o.bed_id = b.id
          AND r.location_id = ANY('{ids}'::uuid[])
    """)

    # 3. Postkorb-Aufgaben — vor Reservierungen löschen (FK: inbox → requests)
    op.execute(f"""
        DELETE FROM tasks.inbox
        WHERE location_id = ANY('{ids}'::uuid[])
           OR related_reservation_id IN (
               SELECT id FROM reservations.requests
               WHERE requester_location_id = ANY('{ids}'::uuid[])
                  OR target_location_id    = ANY('{ids}'::uuid[])
           )
    """)

    # 4. Reservierungen
    op.execute(f"""
        DELETE FROM reservations.requests
        WHERE requester_location_id = ANY('{ids}'::uuid[])
           OR target_location_id    = ANY('{ids}'::uuid[])
    """)

    # 5. Kontingent-Historie
    op.execute(f"""
        DELETE FROM capacity.kontingent_history
        WHERE location_id = ANY('{ids}'::uuid[])
    """)

    # 6. Audit-Einträge mit Demo-Location-Referenz
    op.execute(f"""
        DELETE FROM audit.events
        WHERE location_id = ANY('{ids}'::uuid[])
    """)

    # 7. Bett-Labels (keine FK — direkt via Joins)
    op.execute(f"""
        DELETE FROM capacity.bed_labels bl
        USING capacity.beds b
        JOIN capacity.rooms r ON r.id = b.room_id
        WHERE bl.bed_id = b.id
          AND r.location_id = ANY('{ids}'::uuid[])
    """)

    # 8. Betten
    op.execute(f"""
        DELETE FROM capacity.beds b
        USING capacity.rooms r
        WHERE b.room_id = r.id
          AND r.location_id = ANY('{ids}'::uuid[])
    """)

    # 9. Raum-Labels
    op.execute(f"""
        DELETE FROM capacity.room_labels rl
        USING capacity.rooms r
        WHERE rl.room_id = r.id
          AND r.location_id = ANY('{ids}'::uuid[])
    """)

    # 10. Räume
    op.execute(f"""
        DELETE FROM capacity.rooms
        WHERE location_id = ANY('{ids}'::uuid[])
    """)

    # 11. Einrichtungs-Labels
    op.execute(f"""
        DELETE FROM capacity.location_labels
        WHERE location_id = ANY('{ids}'::uuid[])
    """)

    # 12. Standorte selbst
    op.execute(f"""
        DELETE FROM capacity.locations
        WHERE id = ANY('{ids}'::uuid[])
    """)


def downgrade() -> None:
    # Demo-Daten werden nicht wiederhergestellt.
    pass
