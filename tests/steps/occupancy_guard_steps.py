"""
Step-Definitionen für occupancy_guards.feature.
Testet Konsistenzregeln für aktive Verlegungsanfragen:
- Ausbuchen blockiert bei PENDING/CONFIRMED Reservation
- Ein-Platz-Regel blockiert Cross-Location-Einbuchung
- Cross-Location-Einbuchung bei PENDING blockiert
- Internes Verlegen immer erlaubt
"""
import os
import json
import psycopg2
from datetime import date, timedelta

import requests
from behave import given, then, when

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")


def _today() -> str:
    return date.today().isoformat()


def _in_days(n: int) -> str:
    return (date.today() + timedelta(days=n)).isoformat()


def _auth_headers(context) -> dict:
    token = getattr(context, "auth_token", None)
    return {"Authorization": f"Bearer {token}"} if token else {}


def _loc_headers(context, loc_id: str) -> dict:
    return {**_auth_headers(context), "X-Location-Id": loc_id}


def _post(context, path: str, body: dict, loc_id: str | None = None) -> requests.Response:
    headers = _loc_headers(context, loc_id) if loc_id else _auth_headers(context)
    return requests.post(f"{BACKEND_URL}{path}", json=body, headers=headers, timeout=15)


def _delete(context, path: str, loc_id: str | None = None, params: dict | None = None) -> requests.Response:
    headers = _loc_headers(context, loc_id) if loc_id else _auth_headers(context)
    return requests.delete(f"{BACKEND_URL}{path}", headers=headers, params=params, timeout=15)


def _setup_location(context) -> str:
    requests.post(
        f"{BACKEND_URL}/api/system/eu-quota",
        json={"eu_gesamtquote": 9999},
        headers=_auth_headers(context),
        timeout=15,
    )
    resp = _post(context, "/api/locations", {"name": f"Guard-Test-Loc-{id(object())}", "kontingent": 5, "adresse": ""})
    assert resp.status_code == 201, f"Location create failed: {resp.status_code} — {resp.text}"
    return resp.json()["id"]


def _setup_room(context, loc_id: str) -> str:
    resp = _post(context, f"/api/locations/{loc_id}/rooms", {"name": "Raum-1", "geschlechts_designation": "M"})
    assert resp.status_code == 201, f"Room create failed: {resp.status_code} — {resp.text}"
    return resp.json()["id"]


def _setup_bed(context, room_id: str, nummer: str = "B-001") -> str:
    resp = _post(context, f"/api/rooms/{room_id}/beds", {"bett_nummer": nummer, "bett_typ": "KONTINGENT"})
    assert resp.status_code == 201, f"Bed create failed: {resp.status_code} — {resp.text}"
    return resp.json()["id"]


def _setup_occupancy(context, bed_id: str, azr_id: str, loc_id: str) -> str:
    resp = _post(context, f"/api/beds/{bed_id}/occupancy", {
        "azr_id": azr_id,
        "geschlecht": "M",
        "belegung_start": _today(),
        "belegung_ende": _in_days(10),
    }, loc_id=loc_id)
    assert resp.status_code == 201, f"Occupancy create failed: {resp.status_code} — {resp.text}"
    return resp.json()["id"]


def _create_reservation(context, from_loc_id: str, to_loc_id: str, azr_id: str) -> str:
    resp = _post(context, "/api/reservations", {
        "target_location_id": to_loc_id,
        "azr_id": azr_id,
        "geschlecht": "M",
        "geburtsjahr": 1990,
        "herkunftsland": "DEU",
        "belegung_start": _in_days(1),
        "belegung_ende": _in_days(8),
    }, loc_id=from_loc_id)
    assert resp.status_code == 201, f"Reservation create failed: {resp.status_code} — {resp.text}"
    return resp.json()["id"]


def _confirm_reservation(context, res_id: str, loc_id: str) -> None:
    resp = _post(context, f"/api/reservations/{res_id}/confirm", {}, loc_id=loc_id)
    assert resp.status_code == 200, f"Confirm failed: {resp.status_code} — {resp.text}"


# ---------------------------------------------------------------------------
# Given-Schritte
# ---------------------------------------------------------------------------

@given("eine Person mit PENDING-Reservation ist aktiv belegt")
def step_person_with_pending_reservation(context):
    loc_a = _setup_location(context)
    loc_b = _setup_location(context)
    room_a = _setup_room(context, loc_a)
    bed_a = _setup_bed(context, room_a)
    azr_id = f"AZR-GUARD-PEND-{loc_a[:4]}"
    occ_id = _setup_occupancy(context, bed_a, azr_id, loc_a)
    _create_reservation(context, loc_a, loc_b, azr_id)
    context.guard_bed_id = bed_a
    context.guard_occ_id = occ_id
    context.guard_loc_id = loc_a


@given("eine Person mit CONFIRMED-Reservation ist aktiv belegt")
def step_person_with_confirmed_reservation(context):
    loc_a = _setup_location(context)
    loc_b = _setup_location(context)
    room_a = _setup_room(context, loc_a)
    room_b = _setup_room(context, loc_b)
    bed_a = _setup_bed(context, room_a)
    bed_b = _setup_bed(context, room_b)
    azr_id = f"AZR-GUARD-CONF-{loc_a[:4]}"
    occ_id = _setup_occupancy(context, bed_a, azr_id, loc_a)
    res_id = _create_reservation(context, loc_a, loc_b, azr_id)
    _confirm_reservation(context, res_id, loc_b)
    context.guard_bed_id = bed_a
    context.guard_occ_id = occ_id
    context.guard_loc_id = loc_a


@given("eine Person ohne aktive Reservation ist aktiv belegt")
def step_person_without_reservation(context):
    loc_a = _setup_location(context)
    room_a = _setup_room(context, loc_a)
    bed_a = _setup_bed(context, room_a)
    azr_id = f"AZR-GUARD-FREE-{loc_a[:4]}"
    occ_id = _setup_occupancy(context, bed_a, azr_id, loc_a)
    context.guard_bed_id = bed_a
    context.guard_occ_id = occ_id
    context.guard_loc_id = loc_a
    context.guard_azr_id = azr_id


@given("eine Person ist aktiv in Einrichtung Alpha belegt")
def step_person_active_in_alpha(context):
    loc_alpha = _setup_location(context)
    loc_beta = _setup_location(context)
    room_alpha = _setup_room(context, loc_alpha)
    room_alpha2 = _setup_room(context, loc_alpha)
    room_beta = _setup_room(context, loc_beta)
    bed_alpha = _setup_bed(context, room_alpha)
    bed_alpha2 = _setup_bed(context, room_alpha2)
    bed_beta = _setup_bed(context, room_beta)
    azr_id = f"AZR-EINPLATZ-{loc_alpha[:4]}"
    occ_id = _setup_occupancy(context, bed_alpha, azr_id, loc_alpha)
    context.guard_loc_alpha = loc_alpha
    context.guard_loc_beta = loc_beta
    context.guard_bed_alpha = bed_alpha
    context.guard_bed_alpha2 = bed_alpha2
    context.guard_bed_beta = bed_beta
    context.guard_occ_id = occ_id
    context.guard_azr_id = azr_id


@given("eine Person hat eine PENDING-Reservation von Alpha nach Beta")
def step_person_with_pending_from_alpha_to_beta(context):
    loc_alpha = _setup_location(context)
    loc_beta = _setup_location(context)
    loc_gamma = _setup_location(context)
    room_alpha = _setup_room(context, loc_alpha)
    room_alpha2 = _setup_room(context, loc_alpha)
    room_gamma = _setup_room(context, loc_gamma)
    bed_alpha = _setup_bed(context, room_alpha)
    bed_alpha2 = _setup_bed(context, room_alpha2)
    bed_gamma = _setup_bed(context, room_gamma)
    azr_id = f"AZR-RESGUARD-{loc_alpha[:4]}"
    occ_id = _setup_occupancy(context, bed_alpha, azr_id, loc_alpha)
    _create_reservation(context, loc_alpha, loc_beta, azr_id)
    context.guard_loc_alpha = loc_alpha
    context.guard_loc_gamma = loc_gamma
    context.guard_bed_alpha = bed_alpha
    context.guard_bed_alpha2 = bed_alpha2
    context.guard_bed_gamma = bed_gamma
    context.guard_occ_id = occ_id
    context.guard_azr_id = azr_id


# ---------------------------------------------------------------------------
# When-Schritte
# ---------------------------------------------------------------------------

@when("ich die Belegung per DELETE beende")
def step_delete_occupancy(context):
    context.response = _delete(
        context,
        f"/api/beds/{context.guard_bed_id}/occupancy/{context.guard_occ_id}",
        loc_id=context.guard_loc_id,
    )


@when('ich die Belegung per DELETE mit Grund "{grund}" beende')
def step_delete_occupancy_with_grund(context, grund: str):
    context.guard_grund = grund
    context.response = _delete(
        context,
        f"/api/beds/{context.guard_bed_id}/occupancy/{context.guard_occ_id}",
        loc_id=context.guard_loc_id,
        params={"grund": grund},
    )


@when("ich versuche dieselbe Person in Einrichtung Beta einzubuchen")
def step_try_create_occupancy_in_beta(context):
    context.response = _post(context, f"/api/beds/{context.guard_bed_beta}/occupancy", {
        "azr_id": context.guard_azr_id,
        "geschlecht": "M",
        "belegung_start": _today(),
        "belegung_ende": _in_days(10),
    }, loc_id=context.guard_loc_beta)


@when("ich dieselbe Person in ein anderes Bett in Einrichtung Alpha einbuche")
def step_create_occupancy_in_alpha2(context):
    context.response = _post(context, f"/api/beds/{context.guard_bed_alpha2}/occupancy", {
        "azr_id": context.guard_azr_id,
        "geschlecht": "M",
        "belegung_start": _today(),
        "belegung_ende": _in_days(10),
    }, loc_id=context.guard_loc_alpha)


@when("ich versuche dieselbe Person in Einrichtung Gamma einzubuchen")
def step_try_create_occupancy_in_gamma(context):
    context.response = _post(context, f"/api/beds/{context.guard_bed_gamma}/occupancy", {
        "azr_id": context.guard_azr_id,
        "geschlecht": "M",
        "belegung_start": _today(),
        "belegung_ende": _in_days(10),
    }, loc_id=context.guard_loc_gamma)


# ---------------------------------------------------------------------------
# Then-Schritte
# ---------------------------------------------------------------------------

@then("ist der HTTP-Status {expected_status:d}")
def step_check_http_status_guard(context, expected_status: int):
    actual = context.response.status_code
    assert actual == expected_status, (
        f"Erwartet HTTP {expected_status}, erhalten {actual} — Body: {context.response.text}"
    )


@then('das Audit-Event OCCUPANCY_DELETED enthält den Grund "{expected_grund}"')
def step_check_audit_grund(context, expected_grund: str):
    conn = psycopg2.connect(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        dbname=os.environ.get("POSTGRES_DB", "bordercap"),
        user=os.environ.get("POSTGRES_USER", "bordercap"),
        password=os.environ.get("POSTGRES_PASSWORD", "bordercap_dev"),
    )
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT payload FROM audit.events WHERE event_type = 'OCCUPANCY_DELETED' "
            "AND payload->>'azr_id' = %s ORDER BY created_at DESC LIMIT 1",
            (context.guard_azr_id,),
        )
        row = cur.fetchone()
        assert row is not None, "Kein OCCUPANCY_DELETED Audit-Event gefunden"
        payload = row[0] if isinstance(row[0], dict) else json.loads(row[0])
        assert payload.get("grund") == expected_grund, (
            f"Audit-Event grund='{payload.get('grund')}' ≠ erwartet '{expected_grund}'"
        )
    finally:
        conn.close()
