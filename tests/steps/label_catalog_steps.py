"""
Behave Step-Definitionen für label_catalog.feature.
Nutzt requests für HTTP-Requests gegen das laufende Backend.
Fixture-Cleanup über psycopg2 direkt gegen die DB.
"""
import os

import psycopg2
import requests
from behave import given, then, when

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://bordercap_app:bordercap_app_dev@localhost:5432/bordercap?gssencmode=disable",
)

# Labels die in Tests angelegt werden — für Cleanup
_TEST_LABEL_NAMES = [
    "Test-Label-BDD",
    "Test-Label-InUse",
    "Test-Label-Unused",
]
_TEST_LOCATION_ID = "aaaaaaaa-bbbb-cccc-dddd-000000000001"
_TEST_ROOM_ID = "aaaaaaaa-bbbb-cccc-dddd-000000000002"


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------


def _headers(context) -> dict:
    h = {"Content-Type": "application/json"}
    if getattr(context, "auth_token", None):
        h["Authorization"] = f"Bearer {context.auth_token}"
    return h


def _post(path: str, body: dict, context=None) -> requests.Response:
    return requests.post(
        f"{BACKEND_URL}{path}", json=body, headers=_headers(context), timeout=15
    )


def _get(path: str, context=None) -> requests.Response:
    return requests.get(
        f"{BACKEND_URL}{path}", headers=_headers(context), timeout=15
    )


def _delete(path: str, context=None) -> requests.Response:
    return requests.delete(
        f"{BACKEND_URL}{path}", headers=_headers(context), timeout=15
    )


def _db_cleanup():
    """Entfernt Test-Labels und Test-Fixtures aus der DB."""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True
        cur = conn.cursor()
        # Junction-Table-Einträge
        cur.execute(
            "DELETE FROM capacity.room_labels WHERE label_name = ANY(%s)",
            (_TEST_LABEL_NAMES,),
        )
        cur.execute(
            "DELETE FROM capacity.location_labels WHERE label_name = ANY(%s)",
            (_TEST_LABEL_NAMES,),
        )
        cur.execute(
            "DELETE FROM capacity.bed_labels WHERE label_name = ANY(%s)",
            (_TEST_LABEL_NAMES,),
        )
        cur.execute(
            "DELETE FROM persons.occupant_labels WHERE label_name = ANY(%s)",
            (_TEST_LABEL_NAMES,),
        )
        # Test-Raum und Fixture-Location entfernen
        cur.execute(
            "DELETE FROM capacity.rooms WHERE id = %s",
            (_TEST_ROOM_ID,),
        )
        cur.execute(
            "DELETE FROM capacity.locations WHERE id = %s",
            (_TEST_LOCATION_ID,),
        )
        # Katalog-Einträge
        cur.execute(
            "DELETE FROM capacity.label_catalog WHERE name = ANY(%s)",
            (_TEST_LABEL_NAMES,),
        )
        cur.close()
        conn.close()
    except Exception:
        pass  # Cleanup-Fehler nicht eskalieren


# ---------------------------------------------------------------------------
# Given-Steps
# ---------------------------------------------------------------------------


@given("der Label-Katalog enthält mindestens einen Eintrag")
def step_catalog_has_entries(context):
    _db_cleanup()
    resp = _get("/api/labels", context)
    assert resp.status_code == 200, f"GET /api/labels fehlgeschlagen: {resp.status_code}"
    data = resp.json()
    assert len(data["items"]) > 0, "Label-Katalog ist leer"


@given("ich bin als system-admin authentifiziert")
def step_auth_system_admin(context):
    """Auth-Token wird aus ENV gelesen oder bleibt leer (für Testumgebungen ohne Auth)."""
    token = os.environ.get("SYSTEM_ADMIN_TOKEN", "")
    context.auth_token = token if token else None


@given("ich bin als writer authentifiziert")
def step_auth_writer(context):
    token = os.environ.get("WRITER_TOKEN", "")
    context.auth_token = token if token else None


@given("ein Raum mit ID aus der Datenbank existiert")
def step_any_room_exists(context):
    """Liest die ID eines beliebigen aktiven Raums für den PATCH-Test."""
    conn = psycopg2.connect(DATABASE_URL)
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM capacity.rooms WHERE is_active = TRUE LIMIT 1")
        row = cur.fetchone()
    conn.close()
    assert row, "Kein aktiver Raum in der DB — PATCH-Test nicht möglich"
    context.test_patch_room_id = str(row[0])


@given('das Label "{label_name}" für entity_type "{entity_type}" existiert bereits im Katalog')
def step_label_exists(context, label_name: str, entity_type: str):
    _post(
        "/api/label-catalog",
        {"name": label_name, "entity_type": entity_type, "category": "Test", "color": "#aabbcc"},
        context,
    )
    resp = _get("/api/labels", context)
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert any(
        i["name"] == label_name and entity_type in i["entity_types"] for i in items
    ), f"Label '{label_name}' nicht im Katalog"


@given('das Label "{label_name}" für entity_type "{entity_type}" ist ein System-Label')
def step_label_is_system(context, label_name: str, entity_type: str):
    resp = _get("/api/labels", context)
    assert resp.status_code == 200
    items = resp.json()["items"]
    entry = next(
        (i for i in items if i["name"] == label_name and entity_type in i["entity_types"]),
        None,
    )
    assert entry is not None, f"Label '{label_name}' nicht im Katalog"
    assert entry.get("is_system") is True, f"Label '{label_name}' ist kein System-Label"


@given('ein Raum hat das Label "{label_name}" gesetzt')
def step_room_has_label(context, label_name: str):
    """Erstellt eine Test-Location + Test-Raum und setzt das Label via junction table direkt."""
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cur = conn.cursor()
    # Test-Location anlegen
    cur.execute("""
        INSERT INTO capacity.locations
            (id, name, adresse, kontingent, notbett_kapazitaet, is_active, created_at, updated_at)
        VALUES (%s, 'BDD-Test-Location', 'Test', 0, 0, TRUE, NOW(), NOW())
        ON CONFLICT (id) DO NOTHING
    """, (_TEST_LOCATION_ID,))
    # Test-Raum anlegen
    cur.execute("""
        INSERT INTO capacity.rooms
            (id, location_id, name, geschlechts_designation, room_type, is_active, created_at, updated_at)
        VALUES (%s, %s, 'BDD-Test-Raum', 'D', 'STANDARD', TRUE, NOW(), NOW())
        ON CONFLICT (id) DO NOTHING
    """, (_TEST_ROOM_ID, _TEST_LOCATION_ID))
    # Label in room_labels eintragen
    cur.execute("""
        INSERT INTO capacity.room_labels (room_id, label_name, label_entity_type)
        VALUES (%s, %s, 'ROOM')
        ON CONFLICT DO NOTHING
    """, (_TEST_ROOM_ID, label_name))
    cur.close()
    conn.close()
    context.test_room_id = _TEST_ROOM_ID


@given('das Label "{label_name}" für entity_type "{entity_type}" existiert im Katalog und ist nicht in Verwendung')
def step_label_exists_unused(context, label_name: str, entity_type: str):
    resp = _post(
        "/api/label-catalog",
        {"name": label_name, "entity_type": entity_type, "category": "Test", "color": "#112233"},
        context,
    )
    assert resp.status_code in (201, 409), f"Unerwarteter Status: {resp.status_code}"


# ---------------------------------------------------------------------------
# When-Steps
# ---------------------------------------------------------------------------


@when("ich POST /api/label-catalog mit {body_json} sende")
def step_post_label_catalog(context, body_json: str):
    import json
    body = json.loads(body_json)
    context.response = _post("/api/label-catalog", body, context)


@when("ich DELETE /api/label-catalog/{entity_type}/{label_name} sende")
def step_delete_label_catalog(context, entity_type: str, label_name: str):
    from urllib.parse import quote
    path = f"/api/label-catalog/{quote(entity_type)}/{quote(label_name)}"
    context.response = _delete(path, context)


@when("ich PATCH /api/rooms/{room_id}/labels mit {labels_json} sende")
def step_patch_room_labels(context, labels_json: str):
    import json
    room_id = context.test_patch_room_id
    labels = json.loads(labels_json)
    context.response = requests.patch(
        f"{BACKEND_URL}/api/rooms/{room_id}/labels",
        json={"labels": labels},
        headers=_headers(context),
        timeout=15,
    )


# ---------------------------------------------------------------------------
# Then-Steps
# ---------------------------------------------------------------------------


@then("der HTTP-Status ist {status_code:d}")
def step_http_status(context, status_code: int):
    actual = context.response.status_code
    assert actual == status_code, (
        f"Erwartet HTTP {status_code}, erhalten {actual}. "
        f"Body: {context.response.text[:300]}"
    )


@then('GET /api/labels enthält ein Label mit name "{label_name}" und entity_type "{entity_type}"')
def step_get_labels_contains(context, label_name: str, entity_type: str):
    resp = _get("/api/labels", context)
    assert resp.status_code == 200
    items = resp.json()["items"]
    found = any(
        i["name"] == label_name and entity_type in i["entity_types"] for i in items
    )
    assert found, (
        f"Label '{label_name}' mit entity_type '{entity_type}' nicht in GET /api/labels gefunden. "
        f"Vorhandene: {[(i['name'], i['entity_types']) for i in items if i['name'] == label_name]}"
    )


@then('GET /api/labels enthält kein Label mit name "{label_name}" und entity_type "{entity_type}"')
def step_get_labels_not_contains(context, label_name: str, entity_type: str):
    resp = _get("/api/labels", context)
    assert resp.status_code == 200
    items = resp.json()["items"]
    found = any(
        i["name"] == label_name and entity_type in i["entity_types"] for i in items
    )
    assert not found, f"Label '{label_name}' mit entity_type '{entity_type}' sollte nicht mehr vorhanden sein"


