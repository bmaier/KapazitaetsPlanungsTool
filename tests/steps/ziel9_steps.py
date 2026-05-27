"""
Step-Definitionen für ziel9_guards.feature.
Testet HF-17 (Gültigkeitszeitraum), HF-18 (Deaktivierungsschutz),
HF-19 (Kontingentschutz), HF-22 (Notbett-Verlängerung).
"""
import os
from datetime import date, timedelta

import requests
from behave import given, then, when

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------


def _headers(context, include_location: bool = False) -> dict:
    h = {}
    if getattr(context, "auth_token", None):
        h["Authorization"] = f"Bearer {context.auth_token}"
    if include_location and getattr(context, "location_id", None):
        h["X-Location-Id"] = str(context.location_id)
    return h


def _post(path: str, body: dict, context=None) -> requests.Response:
    return requests.post(
        f"{BACKEND_URL}{path}", json=body, headers=_headers(context), timeout=15
    )


def _patch(path: str, body: dict, context=None) -> requests.Response:
    return requests.patch(
        f"{BACKEND_URL}{path}",
        json=body,
        headers=_headers(context, include_location=True),
        timeout=15,
    )


def _delete(path: str, context=None) -> requests.Response:
    return requests.delete(
        f"{BACKEND_URL}{path}", headers=_headers(context), timeout=15
    )


def _today() -> str:
    return date.today().isoformat()


def _in_days(n: int) -> str:
    return (date.today() + timedelta(days=n)).isoformat()


def _yesterday() -> str:
    return (date.today() - timedelta(days=1)).isoformat()


def _create_location(context, kontingent: int = 10) -> str:
    resp = _post(
        "/api/locations",
        {"name": "Test-Einrichtung", "kontingent": kontingent, "adresse": ""},
        context=context,
    )
    assert resp.status_code == 201, f"Location create failed: {resp.status_code} — {resp.text}"
    loc_id = resp.json()["id"]
    context.location_id = loc_id
    return loc_id


def _create_room(context, loc_id: str) -> str:
    resp = _post(
        f"/api/locations/{loc_id}/rooms",
        {"name": "Test-Raum", "geschlechts_designation": "M"},
        context=context,
    )
    assert resp.status_code == 201, f"Room create failed: {resp.status_code} — {resp.text}"
    room_id = resp.json()["id"]
    context.room_id = room_id
    return room_id


def _create_bed(context, room_id: str, bett_typ: str = "KONTINGENT") -> str:
    resp = _post(
        f"/api/rooms/{room_id}/beds",
        {"bett_nummer": "B-001", "bett_typ": bett_typ},
        context=context,
    )
    assert resp.status_code == 201, f"Bed create failed: {resp.status_code} — {resp.text}"
    bed_id = resp.json()["id"]
    context.bed_id = bed_id
    return bed_id


def _create_occupancy(context, bed_id: str, start: str, ende: str) -> str:
    resp = _post(
        f"/api/beds/{bed_id}/occupancy",
        {
            "azr_id": f"AZR-TEST-{bed_id[:4]}",
            "geschlecht": "M",
            "belegung_start": start,
            "belegung_ende": ende,
        },
        context=context,
    )
    assert resp.status_code == 201, f"Occupancy create failed: {resp.status_code} — {resp.text}"
    occ_id = resp.json()["id"]
    context.occupancy_id = occ_id
    return occ_id


# ---------------------------------------------------------------------------
# Given-Schritte
# ---------------------------------------------------------------------------


@given("ein belegtes Bett in einem Raum existiert")
def step_occupied_bed_in_room(context):
    loc_id = _create_location(context)
    room_id = _create_room(context, loc_id)
    bed_id = _create_bed(context, room_id)
    _create_occupancy(context, bed_id, _today(), _in_days(10))


@given("eine Location mit Kontingent {kontingent:d} und {count:d} aktiven Belegungen existiert")
def step_location_with_kontingent_and_belegungen(context, kontingent: int, count: int):
    loc_id = _create_location(context, kontingent=kontingent)
    room_id = _create_room(context, loc_id)
    for i in range(count):
        bed_id = _create_bed_numbered(context, room_id, i + 1)
        _create_occupancy(context, bed_id, _today(), _in_days(10))
    context.bed_id = bed_id  # letztes Bett für spätere Verwendung


def _create_bed_numbered(context, room_id: str, n: int) -> str:
    resp = _post(
        f"/api/rooms/{room_id}/beds",
        {"bett_nummer": f"B-{n:03d}", "bett_typ": "KONTINGENT"},
        context=context,
    )
    assert resp.status_code == 201, f"Bed #{n} create failed: {resp.status_code} — {resp.text}"
    return resp.json()["id"]


@given("eine Location mit abgelaufenem Gültigkeitszeitraum existiert")
def step_location_with_expired_validity(context):
    loc_id = _create_location(context, kontingent=10)
    # valid_until auf gestern setzen → heute >= gestern → 409 bei Belegung
    resp = _patch(
        f"/api/locations/{loc_id}",
        {"valid_until": _yesterday()},
        context=context,
    )
    assert resp.status_code == 200, (
        f"valid_until konnte nicht gesetzt werden: {resp.status_code} — {resp.text}"
    )
    room_id = _create_room(context, loc_id)
    _create_bed(context, room_id, "KONTINGENT")


@given("eine laufende Notbett-Belegung existiert")
def step_notbett_occupancy_exists(context):
    loc_id = _create_location(context, kontingent=5)
    room_id = _create_room(context, loc_id)
    bed_id = _create_bed(context, room_id, "NOTBETT")
    _create_occupancy(context, bed_id, _today(), _in_days(1))


@given("eine bereits verlängerte Notbett-Belegung existiert")
def step_extended_notbett_occupancy_exists(context):
    step_notbett_occupancy_exists(context)
    resp = _post(f"/api/occupants/{context.occupancy_id}/extend", {}, context=context)
    assert resp.status_code == 200, (
        f"Erste Verlängerung fehlgeschlagen: {resp.status_code} — {resp.text}"
    )


# ---------------------------------------------------------------------------
# When-Schritte
# ---------------------------------------------------------------------------


@when("ich DELETE /api/rooms/{room_id} sende")
def step_delete_room(context, room_id: str):
    r_id = context.room_id if room_id == "{room_id}" else room_id
    context.response = _delete(f"/api/rooms/{r_id}", context=context)


@when("ich PATCH /api/locations/{location_id} mit Kontingent {kontingent:d} sende")
def step_patch_location_kontingent(context, location_id: str, kontingent: int):
    loc_id = context.location_id if location_id == "{location_id}" else location_id
    context.response = _patch(
        f"/api/locations/{loc_id}",
        {"kontingent": kontingent},
        context=context,
    )


@when("ich POST /api/beds/{bed_id}/occupancy mit heutigem Belegungsstart sende")
def step_post_occupancy_today(context, bed_id: str):
    b_id = context.bed_id if bed_id == "{bed_id}" else bed_id
    context.response = _post(
        f"/api/beds/{b_id}/occupancy",
        {
            "azr_id": "AZR-VALIDITY-TEST",
            "geschlecht": "M",
            "belegung_start": _today(),
            "belegung_ende": _in_days(1),
        },
        context=context,
    )


@when("ich POST /api/occupants/{occupancy_id}/extend sende")
def step_post_extend_notbett(context, occupancy_id: str):
    occ_id = context.occupancy_id if occupancy_id == "{occupancy_id}" else occupancy_id
    context.response = _post(f"/api/occupants/{occ_id}/extend", {}, context=context)


# ---------------------------------------------------------------------------
# Then-Schritte
# ---------------------------------------------------------------------------


@then('die Antwort enthält "{field}" mit Wert {bool_value}')
def step_check_field_bool(context, field: str, bool_value: str):
    try:
        body = context.response.json()
    except Exception:
        raise AssertionError(f"Antwort ist kein JSON. Body: {context.response.text[:500]}")
    expected = bool_value.strip().lower() == "true"
    actual = body.get(field)
    assert actual is expected or actual == expected, (
        f"Feld '{field}': erwartet {expected}, erhalten {actual!r}. Antwort: {body}"
    )
