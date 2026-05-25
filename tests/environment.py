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
    except Exception as exc:
        raise AssertionError(
            f"Keycloak-Token konnte nicht geholt werden: {exc}\n"
            f"Bitte 'make dev' ausführen und Keycloak unter {KEYCLOAK_URL} erreichbar machen."
        ) from exc


def _get_db_connection():
    return psycopg2.connect(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        dbname=os.environ.get("POSTGRES_DB", "bordercap"),
        user=os.environ.get("POSTGRES_USER", "bordercap"),
        password=os.environ.get("POSTGRES_PASSWORD", "bordercap_dev"),
    )


def after_scenario(context, scenario):
    try:
        conn = _get_db_connection()
        conn.autocommit = True
        with conn.cursor() as cur:
            # Tasks und Reservierungen zuerst löschen (FK-Abhängigkeiten)
            cur.execute("DELETE FROM tasks.inbox")
            cur.execute("DELETE FROM reservations.requests")
            cur.execute("DELETE FROM persons.occupants")
            cur.execute("DELETE FROM capacity.beds")
            cur.execute("DELETE FROM capacity.rooms")
            cur.execute("DELETE FROM capacity.locations")
            cur.execute("DELETE FROM audit.events")
            cur.execute(
                "UPDATE capacity.system_settings SET eu_gesamtquote = 0 WHERE id = 1"
            )
        conn.close()
    except Exception:
        pass
