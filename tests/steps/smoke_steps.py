"""
Behave Step-Definitionen für Infrastruktur Smoke Tests.
Nutzt requests für HTTP-Checks und psycopg2 für direkte DB-Queries.
"""
import os
import requests
import psycopg2
from psycopg2 import sql as psql
from behave import given, when, then

# Verbindungsparameter aus Umgebungsvariablen (mit Dev-Defaults)
DB_HOST = os.environ.get("POSTGRES_HOST", "localhost")
DB_PORT = int(os.environ.get("POSTGRES_PORT", "5432"))
DB_NAME = os.environ.get("POSTGRES_DB", "bordercap")
DB_USER = os.environ.get("POSTGRES_USER", "bordercap")
DB_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "bordercap_dev")

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
SKOS_URL = os.environ.get("SKOS_URL", "http://localhost:8001")


# ---------------------------------------------------------------------------
# Background
# ---------------------------------------------------------------------------

@given("die Docker-Compose-Umgebung läuft")
def step_docker_compose_running(context):
    """Prüft, dass der Backend-Service erreichbar ist."""
    try:
        resp = requests.get(f"{BACKEND_URL}/health", timeout=10)
        assert resp.status_code in (200, 503), (
            f"Backend nicht erreichbar: HTTP {resp.status_code}"
        )
    except requests.exceptions.ConnectionError as exc:
        raise AssertionError(
            f"Backend unter {BACKEND_URL} nicht erreichbar. "
            "Bitte 'make dev' ausführen."
        ) from exc


# ---------------------------------------------------------------------------
# HTTP GET Schritt
# ---------------------------------------------------------------------------

@when("ich GET {url} aufrufe")
def step_get_url(context, url):
    """Führt einen HTTP-GET-Request aus und speichert Response in context."""
    context.response = requests.get(url.strip(), timeout=15)
    context.response_json = None
    try:
        context.response_json = context.response.json()
    except ValueError:
        pass


# ---------------------------------------------------------------------------
# HTTP-Status-Assertions
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# JSON-Body-Assertions
# ---------------------------------------------------------------------------

@then('die Antwort enthält das Feld "{field}"')
def step_check_json_field_exists(context, field):
    assert context.response_json is not None, "Antwort ist kein JSON"
    assert field in context.response_json, (
        f"Feld '{field}' fehlt in der Antwort. "
        f"Vorhandene Felder: {list(context.response_json.keys())}"
    )


@then('die Antwort enthält einen Code "{code}" mit Label "{label}"')
def step_check_code_label(context, code, label):
    assert context.response_json is not None, "Antwort ist kein JSON"
    concepts = context.response_json.get("concepts", [])
    assert isinstance(concepts, list), f"'concepts' ist keine Liste: {concepts}"
    matching = [c for c in concepts if c.get("code") == code]
    assert matching, (
        f"Code '{code}' nicht in Codeliste gefunden. "
        f"Verfügbare Codes: {[c.get('code') for c in concepts]}"
    )
    actual_label = matching[0].get("label")
    assert actual_label == label, (
        f"Code '{code}': erwartet Label '{label}', erhalten '{actual_label}'"
    )


# ---------------------------------------------------------------------------
# PostgreSQL-Schema-Checks
# ---------------------------------------------------------------------------

def _get_db_connection(user=DB_USER, password=DB_PASSWORD):
    """Erstellt eine psycopg2-Verbindung."""
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=user,
        password=password,
    )


def _get_app_db_connection():
    """
    Verbindet als bordercap_app — NON-Superuser mit nur app_role.
    Nötig für Privilege-Tests: ein PostgreSQL-Superuser umgeht alle GRANT-Checks.
    """
    app_user = os.environ.get("POSTGRES_APP_USER", "bordercap_app")
    app_password = os.environ.get("POSTGRES_APP_PASSWORD", "bordercap_app_dev")
    return _get_db_connection(user=app_user, password=app_password)


@when("ich die PostgreSQL-Schemata abfrage")
def step_query_schemas(context):
    """Lädt alle Schema-Namen aus information_schema."""
    conn = _get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT schema_name
                FROM information_schema.schemata
                WHERE schema_name NOT IN (
                    'information_schema', 'pg_catalog', 'pg_toast',
                    'pg_temp_1', 'pg_toast_temp_1'
                )
                ORDER BY schema_name
                """
            )
            rows = cur.fetchall()
            context.existing_schemas = {row[0] for row in rows}
    finally:
        conn.close()


@then('existiert das Schema "{schema_name}"')
def step_schema_exists(context, schema_name):
    assert schema_name in context.existing_schemas, (
        f"Schema '{schema_name}' fehlt. "
        f"Vorhandene Schemata: {sorted(context.existing_schemas)}"
    )


# ---------------------------------------------------------------------------
# Audit-Manipulationsschutz
# ---------------------------------------------------------------------------

@when("ich versuche, einen Audit-Eintrag zu löschen")
def step_try_delete_audit(context):
    """
    Versucht als bordercap_app (NON-Superuser, nur app_role), einen Audit-Eintrag zu löschen.
    WICHTIG: Verbindung als NON-Superuser — PostgreSQL-Superuser umgehen alle Privilege-Checks.
    """
    context.delete_error = None
    context.delete_succeeded = False
    conn = _get_app_db_connection()
    try:
        conn.autocommit = False
        with conn.cursor() as cur:
            cur.execute("DELETE FROM audit.events WHERE id = gen_random_uuid()")
        conn.commit()
        context.delete_succeeded = True
    except psycopg2.errors.InsufficientPrivilege as exc:
        context.delete_error = exc
        conn.rollback()
    except Exception as exc:
        context.delete_error = exc
        conn.rollback()
    finally:
        conn.close()


@when("ich versuche, Audit-Einträge zu lesen")
def step_try_select_audit(context):
    """
    Versucht als bordercap_app (NON-Superuser), audit.events zu lesen.
    app_role hat nur INSERT — kein SELECT auf Audit-Tabellen.
    """
    context.select_error = None
    context.select_succeeded = False
    conn = _get_app_db_connection()
    try:
        conn.autocommit = False
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM audit.events LIMIT 1")
        conn.commit()
        context.select_succeeded = True
    except psycopg2.errors.InsufficientPrivilege as exc:
        context.select_error = exc
        conn.rollback()
    except Exception as exc:
        context.select_error = exc
        conn.rollback()
    finally:
        conn.close()


@then("schlägt die Operation mit einem Berechtigungsfehler fehl")
def step_check_permission_error(context):
    assert not context.delete_succeeded, (
        "DELETE auf audit.events hat unerwartet funktioniert! "
        "Die app_role darf keine DELETE-Rechte auf Audit-Tabellen haben."
    )
    assert context.delete_error is not None, (
        "Es wurde kein Fehler geworfen, aber DELETE sollte fehlschlagen."
    )
    # pgcode 42501 = insufficient_privilege
    pgcode = getattr(context.delete_error, "pgcode", None)
    assert pgcode == "42501", (
        f"Erwartet PostgreSQL-Fehlercode 42501 (insufficient_privilege), "
        f"erhalten: {pgcode}. Fehler: {context.delete_error}"
    )


@then("schlägt auch SELECT mit einem Berechtigungsfehler fehl")
def step_check_select_permission_error(context):
    assert not context.select_succeeded, (
        "SELECT auf audit.events hat unerwartet funktioniert! "
        "Die app_role darf kein SELECT auf Audit-Tabellen haben."
    )
    assert context.select_error is not None, (
        "SELECT auf audit.events hat keinen Fehler ausgelöst."
    )
    pgcode = getattr(context.select_error, "pgcode", None)
    assert pgcode == "42501", (
        f"Erwartet PostgreSQL-Fehlercode 42501 (insufficient_privilege), "
        f"erhalten: {pgcode}. Fehler: {context.select_error}"
    )
