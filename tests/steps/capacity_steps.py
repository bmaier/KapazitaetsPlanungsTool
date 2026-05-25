"""
Behave Step-Definitionen für capacity_crud.feature.
Nutzt requests für HTTP-Requests gegen das laufende Backend.
Entity-IDs werden im context gespeichert: context.location_id, context.room_id, context.bed_id.
"""
import os
from datetime import date, timedelta

import requests
from behave import given, then, when

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------


def _post(path: str, body: dict, context=None) -> requests.Response:
    headers = {}
    if context is not None and getattr(context, "auth_token", None):
        headers["Authorization"] = f"Bearer {context.auth_token}"
    return requests.post(f"{BACKEND_URL}{path}", json=body, headers=headers, timeout=15)


def _get(path: str, context=None) -> requests.Response:
    headers = {}
    if context is not None and getattr(context, "auth_token", None):
        headers["Authorization"] = f"Bearer {context.auth_token}"
    return requests.get(f"{BACKEND_URL}{path}", headers=headers, timeout=15)


def _delete(path: str, context=None) -> requests.Response:
    headers = {}
    if context is not None and getattr(context, "auth_token", None):
        headers["Authorization"] = f"Bearer {context.auth_token}"
    return requests.delete(f"{BACKEND_URL}{path}", headers=headers, timeout=15)


@when("ich GET /api/locations ohne Authentifizierung sende")
def step_get_locations_without_auth(context):
    context.response = requests.get(f"{BACKEND_URL}/api/locations", timeout=15)


@when("ich GET /health ohne Authentifizierung sende")
def step_get_health_without_auth(context):
    context.response = requests.get(f"{BACKEND_URL}/health", timeout=15)


@then("ist der HTTP-Status nicht 401")
def step_status_not_401(context):
    actual = context.response.status_code
    assert actual != 401, (
        f"Erwartet Status != 401, erhalten {actual}. Body: {context.response.text[:500]}"
    )


def _today() -> date:
    return date.today()


def _in_days(n: int) -> str:
    return (_today() + timedelta(days=n)).isoformat()


def _today_str() -> str:
    return _today().isoformat()


# ---------------------------------------------------------------------------
# Background
# ---------------------------------------------------------------------------


@given("die API läuft auf http://localhost:8000")
def step_api_running(context):
    """Prüft, dass das Backend erreichbar ist."""
    try:
        resp = requests.get(f"{BACKEND_URL}/health", timeout=10)
        assert resp.status_code in (200, 503), (
            f"Backend nicht erreichbar: HTTP {resp.status_code}"
        )
    except requests.exceptions.ConnectionError as exc:
        raise AssertionError(
            f"Backend unter {BACKEND_URL} nicht erreichbar. Bitte 'make dev' ausführen."
        ) from exc


@given("die EU-Gesamtquote ist auf {quota:d} gesetzt")
def step_set_eu_quota(context, quota: int):
    """Setzt die EU-Gesamtquote über POST /api/system/eu-quota."""
    resp = _post("/api/system/eu-quota", {"eu_gesamtquote": quota}, context=context)
    assert resp.status_code == 200, (
        f"EU-Quota konnte nicht gesetzt werden: HTTP {resp.status_code} — {resp.text}"
    )
    context.eu_gesamtquote = quota


# ---------------------------------------------------------------------------
# Given-Schritte: Entitäten voranlegen
# ---------------------------------------------------------------------------


@given("eine Location existiert")
def step_location_exists(context):
    """Legt eine Test-Location mit Kontingent 10 an und speichert die ID."""
    resp = _post(
        "/api/locations",
        {"name": "Test-Einrichtung", "kontingent": 10, "adresse": ""},
        context=context,
    )
    assert resp.status_code == 201, (
        f"Location konnte nicht erstellt werden: HTTP {resp.status_code} — {resp.text}"
    )
    context.location_id = resp.json()["id"]


@given("eine Location mit Kontingent {kontingent:d} existiert")
def step_location_with_kontingent_exists(context, kontingent: int):
    """Legt eine Location mit spezifischem Kontingent an."""
    resp = _post(
        "/api/locations",
        {
            "name": f"Einrichtung Kontingent-{kontingent}",
            "kontingent": kontingent,
            "adresse": "",
        },
        context=context,
    )
    assert resp.status_code == 201, (
        f"Location konnte nicht erstellt werden: HTTP {resp.status_code} — {resp.text}"
    )
    context.location_id = resp.json()["id"]


@given("ein Raum existiert")
def step_room_exists(context):
    """Legt eine Location und einen Raum an, speichert beide IDs."""
    step_location_exists(context)
    resp = _post(
        f"/api/locations/{context.location_id}/rooms",
        {"name": "Test-Raum", "geschlechts_designation": "M"},
        context=context,
    )
    assert resp.status_code == 201, (
        f"Raum konnte nicht erstellt werden: HTTP {resp.status_code} — {resp.text}"
    )
    context.room_id = resp.json()["id"]


@given("ein Bett vom Typ {bed_type} existiert")
def step_bed_of_type_exists(context, bed_type: str):
    """Legt Location, Raum und Bett des angegebenen Typs an."""
    step_room_exists(context)
    resp = _post(
        f"/api/rooms/{context.room_id}/beds",
        {"bett_nummer": "B-001", "bett_typ": bed_type.strip()},
        context=context,
    )
    assert resp.status_code == 201, (
        f"Bett konnte nicht erstellt werden: HTTP {resp.status_code} — {resp.text}"
    )
    context.bed_id = resp.json()["id"]
    context.bed_type = bed_type.strip()


@given("ein belegtes Bett existiert")
def step_occupied_bed_exists(context):
    """Legt ein KONTINGENT-Bett an und belegt es sofort."""
    step_bed_of_type_exists(context, "KONTINGENT")
    resp = _post(
        f"/api/beds/{context.bed_id}/occupancy",
        {
            "azr_id": "AZR-SETUP",
            "geschlecht": "M",
            "belegung_start": _today_str(),
            "belegung_ende": _in_days(10),
        },
        context=context,
    )
    assert resp.status_code == 201, (
        f"Belegung konnte nicht erstellt werden: HTTP {resp.status_code} — {resp.text}"
    )
    context.occupancy_id = resp.json()["id"]


# ---------------------------------------------------------------------------
# When-Schritte: Aktionen
# ---------------------------------------------------------------------------


@when('ich POST /api/locations sende mit Name "{name}" und Kontingent {kontingent:d}')
def step_post_location_with_name_and_kontingent(context, name: str, kontingent: int):
    context.response = _post(
        "/api/locations",
        {"name": name, "kontingent": kontingent, "adresse": ""},
        context=context,
    )


@when("ich POST /api/locations sende mit Kontingent {kontingent:d}")
def step_post_location_with_kontingent(context, kontingent: int):
    context.response = _post(
        "/api/locations",
        {"name": "Weitere Einrichtung", "kontingent": kontingent, "adresse": ""},
        context=context,
    )


@when(
    "ich POST /api/locations/{location_id}/rooms sende mit Name"
    ' "{name}" und Geschlechtsdesignation "{designation}"'
)
def step_post_room(context, location_id: str, name: str, designation: str):
    loc_id = context.location_id if location_id == "{location_id}" else location_id
    context.response = _post(
        f"/api/locations/{loc_id}/rooms",
        {"name": name, "geschlechts_designation": designation},
        context=context,
    )


@when(
    'ich POST /api/rooms/{room_id}/beds sende mit Nummer "{nummer}" und Typ "{bed_type}"'
)
def step_post_bed(context, room_id: str, nummer: str, bed_type: str):
    r_id = context.room_id if room_id == "{room_id}" else room_id
    context.response = _post(
        f"/api/rooms/{r_id}/beds",
        {"bett_nummer": nummer, "bett_typ": bed_type},
        context=context,
    )


@when(
    'ich POST /api/beds/{bed_id}/occupancy sende mit AZR-ID "{azr_id}"'
    " und Belegungsende in {days:d} Tagen"
)
def step_post_occupancy_with_azr_id_and_days(
    context, bed_id: str, azr_id: str, days: int
):
    b_id = context.bed_id if bed_id == "{bed_id}" else bed_id
    context.response = _post(
        f"/api/beds/{b_id}/occupancy",
        {
            "azr_id": azr_id,
            "geschlecht": "M",
            "belegung_start": _today_str(),
            "belegung_ende": _in_days(days),
        },
        context=context,
    )


@when("ich POST /api/beds/{bed_id}/occupancy sende mit Belegungsende in {days:d} Tagen")
def step_post_occupancy_with_days(context, bed_id: str, days: int):
    b_id = context.bed_id if bed_id == "{bed_id}" else bed_id
    context.response = _post(
        f"/api/beds/{b_id}/occupancy",
        {
            "azr_id": "AZR-TEST",
            "geschlecht": "M",
            "belegung_start": _today_str(),
            "belegung_ende": _in_days(days),
        },
        context=context,
    )


@when("ich erneut POST /api/beds/{bed_id}/occupancy sende")
def step_post_occupancy_again(context, bed_id: str):
    b_id = context.bed_id if bed_id == "{bed_id}" else bed_id
    context.response = _post(
        f"/api/beds/{b_id}/occupancy",
        {
            "azr_id": "AZR-DUPLICATE",
            "geschlecht": "M",
            "belegung_start": _today_str(),
            "belegung_ende": _in_days(5),
        },
        context=context,
    )


@when("ich DELETE /api/locations/{location_id} sende")
def step_delete_location(context, location_id: str):
    loc_id = context.location_id if location_id == "{location_id}" else location_id
    context.response = _delete(f"/api/locations/{loc_id}", context=context)


@when("ich DELETE /api/beds/{bed_id}/occupancy/{occupancy_id} sende")
def step_delete_occupancy(context, bed_id: str, occupancy_id: str):
    b_id = context.bed_id if bed_id == "{bed_id}" else bed_id
    o_id = context.occupancy_id if occupancy_id == "{occupancy_id}" else occupancy_id
    context.response = _delete(f"/api/beds/{b_id}/occupancy/{o_id}", context=context)


# ---------------------------------------------------------------------------
# Then-Schritte: Assertions
# ---------------------------------------------------------------------------


@then("ist der HTTP-Status {expected_status:d}")
def step_check_http_status(context, expected_status: int):
    actual = context.response.status_code
    assert actual == expected_status, (
        f"Erwartet HTTP {expected_status}, erhalten {actual}. "
        f"Body: {context.response.text[:500]}"
    )


@then('die Antwort enthält ein "{field}"-Feld')
def step_check_field_exists(context, field: str):
    try:
        body = context.response.json()
    except Exception:
        raise AssertionError(
            f"Antwort ist kein gültiges JSON. Body: {context.response.text[:500]}"
        )
    assert field in body, (
        f"Feld '{field}' fehlt in der Antwort. Vorhandene Felder: {list(body.keys())}"
    )


@then('die Antwort enthält "{field}" mit Wert "{value}"')
def step_check_field_value(context, field: str, value: str):
    try:
        body = context.response.json()
    except Exception:
        raise AssertionError(
            f"Antwort ist kein gültiges JSON. Body: {context.response.text[:500]}"
        )
    actual = body.get(field)
    assert str(actual) == value, (
        f"Feld '{field}': erwartet '{value}', erhalten '{actual}'. "
        f"Vollständige Antwort: {body}"
    )


@then('die Fehlermeldung enthält "{text}"')
def step_check_error_message(context, text: str):
    try:
        body = context.response.json()
    except Exception:
        raise AssertionError(
            f"Antwort ist kein gültiges JSON. Body: {context.response.text[:500]}"
        )
    detail = body.get("detail", "")
    assert text in detail, (
        f"Fehlermeldung enthält '{text}' nicht. Tatsächliche Meldung: '{detail}'"
    )


@then('der Response-Header "{header}" hat Wert "{value}"')
def step_check_response_header(context, header: str, value: str):
    actual = context.response.headers.get(header)
    assert actual == value, (
        f"Response-Header '{header}': erwartet '{value}', erhalten '{actual}'. "
        f"Alle Headers: {dict(context.response.headers)}"
    )


@then("GET /api/locations gibt die Location nicht zurück")
def step_location_not_in_list(context):
    resp = _get("/api/locations", context=context)
    assert resp.status_code == 200, (
        f"GET /api/locations fehlgeschlagen: HTTP {resp.status_code}"
    )
    locations = resp.json()
    ids = [loc["id"] for loc in locations]
    assert str(context.location_id) not in ids, (
        f"Location {context.location_id} ist noch in der aktiven Liste. "
        f"IDs: {ids}"
    )


@then("GET /api/locations/{location_id} zeigt is_active als false")
def step_location_is_inactive(context, location_id: str):
    loc_id = context.location_id if location_id == "{location_id}" else location_id
    resp = _get(f"/api/locations/{loc_id}", context=context)
    assert resp.status_code == 200, (
        f"GET /api/locations/{loc_id} fehlgeschlagen: HTTP {resp.status_code}"
    )
    body = resp.json()
    assert body.get("is_active") is False, (
        f"Location {loc_id} hat is_active={body.get('is_active')}, erwartet False"
    )
