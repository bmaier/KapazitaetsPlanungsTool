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


def after_scenario(context, scenario):
    # Nur die vom Test angelegten Locations löschen (via context.loc_map).
    # ON DELETE CASCADE entfernt zugehörige Rooms, Beds und Occupants automatisch.
    # Demo-Daten bleiben erhalten.
    test_loc_ids = list(getattr(context, "loc_map", {}).values())
    if not test_loc_ids:
        return
    try:
        conn = _get_db_connection()
        conn.autocommit = True
        with conn.cursor() as cur:
            placeholders = ",".join(["%s"] * len(test_loc_ids))
            # Reservierungen und Tasks zu diesen Locations zuerst löschen
            cur.execute(
                f"DELETE FROM reservations.requests WHERE requester_location_id IN ({placeholders}) "
                f"OR target_location_id IN ({placeholders})",
                test_loc_ids + test_loc_ids,
            )
            cur.execute(
                f"DELETE FROM tasks.inbox WHERE location_id IN ({placeholders})",
                test_loc_ids,
            )
            # Locations löschen — CASCADE entfernt Rooms, Beds, Occupants
            cur.execute(
                f"DELETE FROM capacity.locations WHERE id IN ({placeholders})",
                test_loc_ids,
            )
        conn.close()
    except Exception:
        pass
