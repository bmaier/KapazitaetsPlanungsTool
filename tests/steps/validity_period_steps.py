"""
Step-Definitionen für validity_period_checks.feature.

Testet, dass Betten, Räume und Einrichtungen nur für Zeiträume angeboten
und gebucht werden, in denen sie vollständig verfügbar sind.

Setup nutzt die REST-API wo möglich; direkte DB-Updates (psycopg2) nur für
Gültigkeitsdaten, da hierfür keine separaten Create-Endpoints existieren.
"""
import os
from datetime import date, timedelta

import psycopg2
import requests
from behave import given, then, when

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")


# ─── Zeithelfer ──────────────────────────────────────────────────────────────

def _today() -> str:
    return date.today().isoformat()


def _in_days(n: int) -> str:
    return (date.today() + timedelta(days=n)).isoformat()


# ─── HTTP-Helfer ─────────────────────────────────────────────────────────────

def _auth(context) -> dict:
    token = getattr(context, "auth_token", None)
    return {"Authorization": f"Bearer {token}"} if token else {}


def _loc_auth(context, loc_id: str) -> dict:
    return {**_auth(context), "X-Location-Id": loc_id}


def _post(context, path: str, body: dict, loc_id: str | None = None) -> requests.Response:
    headers = _loc_auth(context, loc_id) if loc_id else _auth(context)
    return requests.post(f"{BACKEND_URL}{path}", json=body, headers=headers, timeout=15)


def _get(context, path: str, loc_id: str | None = None) -> requests.Response:
    headers = _loc_auth(context, loc_id) if loc_id else _auth(context)
    return requests.get(f"{BACKEND_URL}{path}", headers=headers, timeout=15)


def _patch(context, path: str, body: dict, loc_id: str | None = None) -> requests.Response:
    headers = _loc_auth(context, loc_id) if loc_id else _auth(context)
    return requests.patch(f"{BACKEND_URL}{path}", json=body, headers=headers, timeout=15)


# ─── DB-Helfer ───────────────────────────────────────────────────────────────

def _db_conn():
    return psycopg2.connect(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        dbname=os.environ.get("POSTGRES_DB", "bordercap"),
        user=os.environ.get("POSTGRES_USER", "bordercap"),
        password=os.environ.get("POSTGRES_PASSWORD", "bordercap_dev"),
    )


def _reset_bed_validity(bed_id: str):
    """Setzt alle Gültigkeitsfelder eines Betts auf NULL zurück."""
    conn = _db_conn()
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE capacity.beds SET valid_from = NULL, deaktiviert_ab = NULL WHERE id = %s",
            (bed_id,),
        )
    conn.close()


def _reset_room_validity(room_id: str):
    """Setzt alle Gültigkeitsfelder eines Raums auf NULL zurück."""
    conn = _db_conn()
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE capacity.rooms SET valid_from = NULL, valid_until = NULL WHERE id = %s",
            (room_id,),
        )
    conn.close()


def _reset_location_validity(loc_id: str):
    """Reaktiviert eine Einrichtung und setzt Gültigkeitsfelder zurück."""
    conn = _db_conn()
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE capacity.locations SET is_active = TRUE, valid_from = NULL, valid_until = NULL WHERE id = %s",
            (loc_id,),
        )
    conn.close()


# ─── Setup-Hilfsfunktionen ───────────────────────────────────────────────────

def _create_location(context, name: str) -> str:
    resp = _post(context, "/api/system/eu-quota", {"eu_gesamtquote": 9999})
    resp = _post(context, "/api/locations", {"name": name, "kontingent": 5, "adresse": ""})
    assert resp.status_code == 201, f"Location '{name}' fehlgeschlagen: {resp.status_code} — {resp.text}"
    return resp.json()["id"]


def _create_room(context, loc_id: str, name: str = "Testraum", designation: str = "M") -> str:
    resp = _post(context, f"/api/locations/{loc_id}/rooms",
                 {"name": name, "geschlechts_designation": designation})
    assert resp.status_code == 201, f"Room create fehlgeschlagen: {resp.status_code} — {resp.text}"
    return resp.json()["id"]


def _create_bed(context, room_id: str, nummer: str = "001") -> str:
    resp = _post(context, f"/api/rooms/{room_id}/beds",
                 {"bett_nummer": nummer, "bett_typ": "KONTINGENT"})
    assert resp.status_code == 201, f"Bed create fehlgeschlagen: {resp.status_code} — {resp.text}"
    return resp.json()["id"]


# ─── SEARCH PERIOD ───────────────────────────────────────────────────────────
# Alle Tests verwenden denselben 14-Tage-Suchzeitraum: [today+1 … today+15)

def _period_start() -> str:
    return _in_days(1)


def _period_end() -> str:
    return _in_days(15)


# ─── GIVEN ───────────────────────────────────────────────────────────────────

@given("eine Einrichtung mit einem freien Kontingent-Bett für Gültigkeitstests existiert")
def step_setup_location_with_bed(context):
    """Legt Einrichtung + Raum + Bett an. Speichert IDs in context."""
    requests.post(
        f"{BACKEND_URL}/api/system/eu-quota",
        json={"eu_gesamtquote": 9999},
        headers=_auth(context),
        timeout=15,
    )
    loc_id = _create_location(context, "Gültigkeitstest-Einrichtung")
    room_id = _create_room(context, loc_id)
    bed_id = _create_bed(context, room_id)

    context.validity_loc_id = loc_id
    context.validity_room_id = room_id
    context.validity_bed_id = bed_id

    # Für cleanup in after_scenario
    context.loc_map = getattr(context, "loc_map", {})
    context.loc_map["validity_loc"] = loc_id


@given("das Bett wird in der Mitte des Suchzeitraums deaktiviert")
def step_bed_deactivated_mid_period(context):
    mid = _in_days(8)  # Mitte des 14-Tage-Zeitraums
    resp = _patch(context, f"/api/beds/{context.validity_bed_id}/deactivate",
                  {"deaktiviert_ab": mid})
    assert resp.status_code == 200, f"deactivate fehlgeschlagen: {resp.status_code} — {resp.text}"
    context.period_start = _period_start()
    context.period_end = _period_end()


@given("das Bett ist erst nach dem Beginn des Suchzeitraums gültig")
def step_bed_valid_from_after_period_start(context):
    # Bett erst ab Mitte des Zeitraums gültig → liegt nach period_start
    mid = _in_days(8)
    resp = _patch(context, f"/api/beds/{context.validity_bed_id}/validity",
                  {"valid_from": mid})
    assert resp.status_code == 200, f"validity fehlgeschlagen: {resp.status_code} — {resp.text}"
    context.period_start = _period_start()
    context.period_end = _period_end()


@given("der Raum des Betts endet vor dem Ende des Suchzeitraums")
def step_room_valid_until_before_period_end(context):
    # Raum endet in der Mitte → liegt vor period_end
    mid = _in_days(8)
    resp = _patch(context, f"/api/rooms/{context.validity_room_id}/validity",
                  {"valid_until": mid})
    assert resp.status_code == 200, f"room validity fehlgeschlagen: {resp.status_code} — {resp.text}"
    context.period_start = _period_start()
    context.period_end = _period_end()


@given("die Einrichtung ist deaktiviert")
def step_location_deactivated(context):
    resp = _patch(context, f"/api/locations/{context.validity_loc_id}",
                  {"is_active": False})
    assert resp.status_code == 200, f"deactivate location fehlgeschlagen: {resp.status_code} — {resp.text}"
    context.period_start = _period_start()
    context.period_end = _period_end()


@given("das Bett hat keine einschränkenden Gültigkeitsdaten")
def step_bed_no_validity_constraints(context):
    _reset_bed_validity(context.validity_bed_id)
    context.period_start = _period_start()
    context.period_end = _period_end()


@given("die Einrichtung läuft vor dem Ende des gewünschten Belegungszeitraums aus")
def step_location_expires_before_period_end(context):
    mid = _in_days(8)
    resp = _patch(context, f"/api/locations/{context.validity_loc_id}",
                  {"valid_until": mid})
    assert resp.status_code == 200, f"location valid_until fehlgeschlagen: {resp.status_code} — {resp.text}"
    context.occ_start = _in_days(1)
    context.occ_end = _in_days(15)


@given("das Bett ist erst nach dem Beginn des gewünschten Belegungszeitraums gültig")
def step_bed_valid_from_after_occ_start(context):
    future = _in_days(8)
    resp = _patch(context, f"/api/beds/{context.validity_bed_id}/validity",
                  {"valid_from": future})
    assert resp.status_code == 200, f"bed validity fehlgeschlagen: {resp.status_code} — {resp.text}"
    context.occ_start = _in_days(1)
    context.occ_end = _in_days(15)


@given("das Bett wird in der Mitte des gewünschten Belegungszeitraums deaktiviert")
def step_bed_deactivated_mid_occ_period(context):
    mid = _in_days(8)
    resp = _patch(context, f"/api/beds/{context.validity_bed_id}/deactivate",
                  {"deaktiviert_ab": mid})
    assert resp.status_code == 200, f"deactivate fehlgeschlagen: {resp.status_code} — {resp.text}"
    context.occ_start = _in_days(1)
    context.occ_end = _in_days(15)


@given("der Raum des Betts läuft vor dem Ende des gewünschten Belegungszeitraums aus")
def step_room_expires_before_occ_end(context):
    mid = _in_days(8)
    resp = _patch(context, f"/api/rooms/{context.validity_room_id}/validity",
                  {"valid_until": mid})
    assert resp.status_code == 200, f"room valid_until fehlgeschlagen: {resp.status_code} — {resp.text}"
    context.occ_start = _in_days(1)
    context.occ_end = _in_days(15)


@given("eine zweite Einrichtung als Ziel existiert und deaktiviert wurde")
def step_target_location_deactivated(context):
    loc_id = _create_location(context, "Gültigkeitstest-Zieleinrichtung-deaktiviert")
    context.loc_map["validity_target_loc"] = loc_id
    context.validity_target_loc_id = loc_id
    resp = _patch(context, f"/api/locations/{loc_id}", {"is_active": False})
    assert resp.status_code == 200, f"deactivate target fehlgeschlagen: {resp.status_code} — {resp.text}"
    context.res_start = _in_days(1)
    context.res_end = _in_days(15)


@given("eine zweite Einrichtung als Ziel existiert und läuft vor dem Belegungsende aus")
def step_target_location_expires_early(context):
    loc_id = _create_location(context, "Gültigkeitstest-Zieleinrichtung-auslaufend")
    context.loc_map["validity_target_loc"] = loc_id
    context.validity_target_loc_id = loc_id
    mid = _in_days(8)
    resp = _patch(context, f"/api/locations/{loc_id}", {"valid_until": mid})
    assert resp.status_code == 200, f"valid_until auf Ziel fehlgeschlagen: {resp.status_code} — {resp.text}"
    context.res_start = _in_days(1)
    context.res_end = _in_days(15)


# ─── WHEN ────────────────────────────────────────────────────────────────────

@when("ich eine Bettsuche für den gesamten Zeitraum durchführe")
def step_post_suggestions(context):
    payload = {
        "geschlecht": "M",
        "anzahl": 1,
        "belegung_start": context.period_start,
        "belegung_ende": context.period_end,
        "cross_location": False,
    }
    context.response = requests.post(
        f"{BACKEND_URL}/api/suggestions",
        json=payload,
        headers=_loc_auth(context, context.validity_loc_id),
        timeout=15,
    )


@when("ich eine lokale Bettsuche als Mitglied dieser Einrichtung durchführe")
def step_post_suggestions_local(context):
    payload = {
        "geschlecht": "M",
        "anzahl": 1,
        "belegung_start": _period_start(),
        "belegung_ende": _period_end(),
        "cross_location": False,
    }
    # Die deaktivierte Einrichtung im X-Location-Id Header → get_location_context gibt 403
    context.response = requests.post(
        f"{BACKEND_URL}/api/suggestions",
        json=payload,
        headers=_loc_auth(context, context.validity_loc_id),
        timeout=15,
    )


@when("ich versuche eine Belegung für das Bett anzulegen")
def step_post_occupancy_attempt(context):
    context.response = _post(
        context,
        f"/api/beds/{context.validity_bed_id}/occupancy",
        {
            "azr_id": "AZR-VALID-001",
            "geschlecht": "M",
            "belegung_start": _in_days(1),
            "belegung_ende": _in_days(15),
        },
        loc_id=context.validity_loc_id,
    )


@when("ich eine Belegung anlege, die über das Einrichtungsende hinausgeht")
def step_post_occupancy_exceeds_location(context):
    context.response = _post(
        context,
        f"/api/beds/{context.validity_bed_id}/occupancy",
        {
            "azr_id": "AZR-VALID-002",
            "geschlecht": "M",
            "belegung_start": context.occ_start,
            "belegung_ende": context.occ_end,  # > location.valid_until
        },
        loc_id=context.validity_loc_id,
    )


@when("ich eine Belegung anlege, die vor dem Gültigkeitsbeginn des Betts beginnt")
def step_post_occupancy_before_bed_valid_from(context):
    context.response = _post(
        context,
        f"/api/beds/{context.validity_bed_id}/occupancy",
        {
            "azr_id": "AZR-VALID-003",
            "geschlecht": "M",
            "belegung_start": context.occ_start,  # < bed.valid_from
            "belegung_ende": context.occ_end,
        },
        loc_id=context.validity_loc_id,
    )


@when("ich eine Belegung anlege, die über das Deaktivierungsdatum des Betts hinausgeht")
def step_post_occupancy_exceeds_bed_deaktiviert_ab(context):
    context.response = _post(
        context,
        f"/api/beds/{context.validity_bed_id}/occupancy",
        {
            "azr_id": "AZR-VALID-004",
            "geschlecht": "M",
            "belegung_start": context.occ_start,
            "belegung_ende": context.occ_end,  # > bed.deaktiviert_ab
        },
        loc_id=context.validity_loc_id,
    )


@when("ich eine Belegung anlege, die über das Raumende hinausgeht")
def step_post_occupancy_exceeds_room_valid_until(context):
    context.response = _post(
        context,
        f"/api/beds/{context.validity_bed_id}/occupancy",
        {
            "azr_id": "AZR-VALID-005",
            "geschlecht": "M",
            "belegung_start": context.occ_start,
            "belegung_ende": context.occ_end,  # > room.valid_until
        },
        loc_id=context.validity_loc_id,
    )


@when("ich eine Verlegungsanfrage zur deaktivierten Zieleinrichtung stelle")
def step_post_reservation_to_inactive_target(context):
    context.response = _post(
        context,
        "/api/reservations",
        {
            "target_location_id": context.validity_target_loc_id,
            "azr_id": "AZR-RES-001",
            "geschlecht": "M",
            "geburtsjahr": 1990,
            "herkunftsland": "DEU",
            "belegung_start": context.res_start,
            "belegung_ende": context.res_end,
        },
        loc_id=context.validity_loc_id,
    )


@when("ich eine Verlegungsanfrage stelle, deren Ende über die Gültigkeit der Zieleinrichtung hinausgeht")
def step_post_reservation_exceeds_target_validity(context):
    context.response = _post(
        context,
        "/api/reservations",
        {
            "target_location_id": context.validity_target_loc_id,
            "azr_id": "AZR-RES-002",
            "geschlecht": "M",
            "geburtsjahr": 1990,
            "herkunftsland": "DEU",
            "belegung_start": context.res_start,
            "belegung_ende": context.res_end,  # > target_location.valid_until
        },
        loc_id=context.validity_loc_id,
    )


@when("ich GET /api/locations/{id}/bed-status mit dem Suchzeitraum abfrage")
def step_get_bed_status(context, id: str):
    path = (
        f"/api/locations/{context.validity_loc_id}/bed-status"
        f"?date_from={context.period_start}&date_to={context.period_end}"
    )
    context.response = _get(context, path)


# ─── THEN ────────────────────────────────────────────────────────────────────

@then("sind keine Vorschläge für dieses Bett verfügbar")
def step_no_suggestions_for_bed(context):
    assert context.response.status_code == 200, (
        f"Erwartete 200, erhalten {context.response.status_code}: {context.response.text[:300]}"
    )
    body = context.response.json()
    variants = body.get("variants", [])
    all_bed_ids = [b["bed_id"] for v in variants for b in v.get("beds", [])]
    assert context.validity_bed_id not in all_bed_ids, (
        f"Bett {context.validity_bed_id} sollte nicht in den Vorschlägen sein, ist aber vorhanden."
    )


@then("enthält die Antwort mindestens einen Vorschlag")
def step_has_suggestions(context):
    assert context.response.status_code == 200, (
        f"Erwartete 200, erhalten {context.response.status_code}: {context.response.text[:300]}"
    )
    body = context.response.json()
    variants = body.get("variants", [])
    assert len(variants) > 0, (
        f"Keine Vorschläge in der Antwort. message: '{body.get('message')}'"
    )


@then("hat das Bett in der Antwort period_available = false")
def step_bed_period_available_false(context):
    assert context.response.status_code == 200, (
        f"Erwartete 200, erhalten {context.response.status_code}: {context.response.text[:300]}"
    )
    rooms = context.response.json()
    found = False
    for room in rooms:
        for bed in room.get("beds", []):
            if bed["bed_id"] == context.validity_bed_id:
                found = True
                pa = bed.get("period_available")
                assert pa is False, (
                    f"Bett {context.validity_bed_id}: period_available ist '{pa}', erwartet False."
                )
    assert found, f"Bett {context.validity_bed_id} wurde in der Antwort nicht gefunden."


@then("hat das Bett in der Antwort period_available = true")
def step_bed_period_available_true(context):
    assert context.response.status_code == 200, (
        f"Erwartete 200, erhalten {context.response.status_code}: {context.response.text[:300]}"
    )
    rooms = context.response.json()
    found = False
    for room in rooms:
        for bed in room.get("beds", []):
            if bed["bed_id"] == context.validity_bed_id:
                found = True
                pa = bed.get("period_available")
                assert pa is True, (
                    f"Bett {context.validity_bed_id}: period_available ist '{pa}', erwartet True."
                )
    assert found, f"Bett {context.validity_bed_id} wurde in der Antwort nicht gefunden."
