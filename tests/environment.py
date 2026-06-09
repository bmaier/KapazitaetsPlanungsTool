"""
Behave environment hooks for test isolation.
after_scenario deletes all test data so scenarios don't bleed into each other.
"""
import os

import psycopg2
import requests as _req

KEYCLOAK_URL = os.environ.get("KEYCLOAK_URL", "http://localhost:8080")
KEYCLOAK_REALM = os.environ.get("KEYCLOAK_REALM", "bordercapcontrol")
KEYCLOAK_TEST_CLIENT_ID = "bordercapcontrol-test"
KEYCLOAK_TEST_CLIENT_SECRET = os.environ.get(
    "KEYCLOAK_TEST_CLIENT_SECRET", "bordercapcontrol-test-secret"
)
KEYCLOAK_TEST_USER = os.environ.get("KEYCLOAK_TEST_USER", "writer_user")
KEYCLOAK_TEST_PASSWORD = os.environ.get("KEYCLOAK_TEST_PASSWORD", "Writer1234!")


def _get_auth_headers(context) -> dict:
    """Gibt den Authorization-Header für HTTP-Requests zurück."""
    token = getattr(context, "auth_token", None)
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def before_all(context):
    """Holt einmalig einen Keycloak-Token für writer_user vor allen Scenarios."""
    token_url = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/token"
    try:
        resp = _req.post(
            token_url,
            data={
                "grant_type": "password",
                "client_id": KEYCLOAK_TEST_CLIENT_ID,
                "client_secret": KEYCLOAK_TEST_CLIENT_SECRET,
                "username": KEYCLOAK_TEST_USER,
                "password": KEYCLOAK_TEST_PASSWORD,
            },
            timeout=15,
        )
        resp.raise_for_status()
        context.auth_token = resp.json()["access_token"]
        context._keycloak_error = None
    except Exception as exc:
        context.auth_token = None
        context._keycloak_error = exc


def before_feature(context, feature):
    """Bricht bei Keycloak-Fehler ab, außer bei @agent-Features (standalone)."""
    if "agent" not in feature.tags and context._keycloak_error is not None:
        raise AssertionError(
            f"Keycloak-Token konnte nicht geholt werden: {context._keycloak_error}\n"
            f"Bitte 'make dev' ausführen und Keycloak unter {KEYCLOAK_URL} erreichbar machen."
        ) from context._keycloak_error


def _get_db_connection():
    return psycopg2.connect(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        dbname=os.environ.get("POSTGRES_DB", "bordercap"),
        user=os.environ.get("POSTGRES_USER", "bordercap"),
        password=os.environ.get("POSTGRES_PASSWORD", "bordercap_dev"),
    )


def _collect_test_location_ids(context) -> list[str]:
    """
    Sammelt alle im Szenario angelegten Location-IDs aus allen bekannten
    context-Attributen. loc_map-Werte können UUID-Strings oder Dicts mit
    "uuid"-Key sein (suggestion_steps verwendet Dicts).
    """
    ids: set[str] = set()

    # loc_map: Werte sind entweder UUID-Strings oder {"uuid": ..., "name": ...}
    for val in getattr(context, "loc_map", {}).values():
        if isinstance(val, dict):
            uid = val.get("uuid")
        else:
            uid = val
        if uid:
            ids.add(str(uid))

    # Direkte Attribute (reservation_steps, capacity_steps, ziel9_steps etc.)
    for attr in ("location_id", "location_a_id", "location_b_id", "location_c_id"):
        uid = getattr(context, attr, None)
        if uid:
            ids.add(str(uid))

    return list(ids)


def after_scenario(context, scenario):
    """
    Löscht alle vom Test angelegten Locations und alle abhängigen Daten.
    Reihenfolge entspricht den FK-Abhängigkeiten (NO ACTION überall außer *_labels).
    """
    loc_ids = _collect_test_location_ids(context)
    if not loc_ids:
        return

    conn = _get_db_connection()
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            ph = ",".join(["%s"] * len(loc_ids))

            # 1. Belegungslabels
            cur.execute(f"""
                DELETE FROM persons.occupant_labels ol
                USING persons.occupants o
                JOIN capacity.beds b ON b.id = o.bed_id
                JOIN capacity.rooms r ON r.id = b.room_id
                WHERE ol.occupant_id = o.id
                  AND r.location_id IN ({ph})
            """, loc_ids)

            # 2. Belegungen
            cur.execute(f"""
                DELETE FROM persons.occupants o
                USING capacity.beds b
                JOIN capacity.rooms r ON r.id = b.room_id
                WHERE o.bed_id = b.id
                  AND r.location_id IN ({ph})
            """, loc_ids)

            # 3. Postkorb — vor Reservierungen (FK: inbox → requests)
            cur.execute(f"""
                DELETE FROM tasks.inbox
                WHERE location_id IN ({ph})
                   OR related_reservation_id IN (
                       SELECT id FROM reservations.requests
                       WHERE requester_location_id IN ({ph})
                          OR target_location_id    IN ({ph})
                   )
            """, loc_ids + loc_ids + loc_ids)

            # 4. Reservierungen
            cur.execute(f"""
                DELETE FROM reservations.requests
                WHERE requester_location_id IN ({ph})
                   OR target_location_id    IN ({ph})
            """, loc_ids + loc_ids)

            # 5. Kontingent-Historie
            cur.execute(f"DELETE FROM capacity.kontingent_history WHERE location_id IN ({ph})", loc_ids)

            # 6. Audit-Einträge (bordercap-User hat DELETE auf audit.events)
            cur.execute(f"DELETE FROM audit.events WHERE location_id IN ({ph})", loc_ids)

            # 7. Betten (bed_labels via CASCADE)
            cur.execute(f"""
                DELETE FROM capacity.beds b
                USING capacity.rooms r
                WHERE b.room_id = r.id
                  AND r.location_id IN ({ph})
            """, loc_ids)

            # 8. Räume (room_labels via CASCADE)
            cur.execute(f"DELETE FROM capacity.rooms WHERE location_id IN ({ph})", loc_ids)

            # 9. Locations (location_labels via CASCADE)
            cur.execute(f"DELETE FROM capacity.locations WHERE id IN ({ph})", loc_ids)

    except Exception as exc:
        print(f"\n[after_scenario] Cleanup-Fehler (Szenario: {scenario.name}): {exc}")
    finally:
        conn.close()
