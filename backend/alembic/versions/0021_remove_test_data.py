"""
Einmalige Bereinigung: Alle von BDD-Tests hinterlassenen Einrichtungen entfernen.

Die Tests haben Einrichtungen mit erkennbaren Namen angelegt, aber der
after_scenario-Cleanup hatte einen FK-Reihenfolge-Bug (inbox vor requests)
und hat context.location_a/b/c_id nicht erfasst. Die Daten blieben in der DB.

Erkannte Test-Namensmuster:
  - 'Einrichtung A (Test)' / 'Einrichtung B (Test)' / 'Einrichtung C (Test)'
  - 'Verlege-Test-XXXXXX'
  - 'Guard-AZR-Loc-XXXXXX'
  - 'Warte-SB-Test'
  - 'Test-Einrichtung'
  - 'Einrichtung Kontingent-N'

Idempotent. Down: kein Rollback.
"""

from alembic import op

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None

# Bedingung für JOIN-Queries (l = Alias für capacity.locations)
_JOIN_COND = """
    l.name LIKE 'Einrichtung %(Test)%'
    OR l.name LIKE 'Verlege-Test-%'
    OR l.name LIKE 'Guard-AZR-Loc-%'
    OR l.name = 'Warte-SB-Test'
    OR l.name = 'Test-Einrichtung'
    OR l.name LIKE 'Einrichtung Kontingent-%'
"""

# Bedingung für einfache DELETE auf capacity.locations direkt
_DIRECT_COND = """
    name LIKE 'Einrichtung %(Test)%'
    OR name LIKE 'Verlege-Test-%'
    OR name LIKE 'Guard-AZR-Loc-%'
    OR name = 'Warte-SB-Test'
    OR name = 'Test-Einrichtung'
    OR name LIKE 'Einrichtung Kontingent-%'
"""

_TEST_IDS_SUBQUERY = f"SELECT id FROM capacity.locations WHERE {_DIRECT_COND}"


def upgrade() -> None:
    # 1. Belegungslabels
    op.execute(f"""
        DELETE FROM persons.occupant_labels ol
        USING persons.occupants o
        JOIN capacity.beds b ON b.id = o.bed_id
        JOIN capacity.rooms r ON r.id = b.room_id
        JOIN capacity.locations l ON l.id = r.location_id
        WHERE ol.occupant_id = o.id
          AND ({_JOIN_COND})
    """)

    # 2. Belegungen
    op.execute(f"""
        DELETE FROM persons.occupants o
        USING capacity.beds b
        JOIN capacity.rooms r ON r.id = b.room_id
        JOIN capacity.locations l ON l.id = r.location_id
        WHERE o.bed_id = b.id
          AND ({_JOIN_COND})
    """)

    # 3. Postkorb — vor Reservierungen (FK: inbox → requests)
    op.execute(f"""
        DELETE FROM tasks.inbox
        WHERE location_id IN ({_TEST_IDS_SUBQUERY})
           OR related_reservation_id IN (
               SELECT id FROM reservations.requests
               WHERE requester_location_id IN ({_TEST_IDS_SUBQUERY})
                  OR target_location_id    IN ({_TEST_IDS_SUBQUERY})
           )
    """)

    # 4. Reservierungen
    op.execute(f"""
        DELETE FROM reservations.requests
        WHERE requester_location_id IN ({_TEST_IDS_SUBQUERY})
           OR target_location_id    IN ({_TEST_IDS_SUBQUERY})
    """)

    # 5. Kontingent-Historie
    op.execute(f"""
        DELETE FROM capacity.kontingent_history
        WHERE location_id IN ({_TEST_IDS_SUBQUERY})
    """)

    # 6. Audit-Einträge
    op.execute(f"""
        DELETE FROM audit.events
        WHERE location_id IN ({_TEST_IDS_SUBQUERY})
    """)

    # 7. Betten (bed_labels via CASCADE)
    op.execute(f"""
        DELETE FROM capacity.beds b
        USING capacity.rooms r
        JOIN capacity.locations l ON l.id = r.location_id
        WHERE b.room_id = r.id
          AND ({_JOIN_COND})
    """)

    # 8. Räume (room_labels via CASCADE)
    op.execute(f"""
        DELETE FROM capacity.rooms r
        USING capacity.locations l
        WHERE r.location_id = l.id
          AND ({_JOIN_COND})
    """)

    # 9. Locations (location_labels via CASCADE)
    op.execute(f"""
        DELETE FROM capacity.locations WHERE {_DIRECT_COND}
    """)


def downgrade() -> None:
    pass
