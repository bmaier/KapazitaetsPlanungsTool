"""
Behave Step-Definitionen für intern_verlegen_direktbuchung.feature.
Testet den internen Verlegungsflow (SuggestionWizard-Direktbuchung):
  - POST neue Belegung mit verlegung_grund → 201
  - DELETE alte Belegung → 200
  - Nach POST+DELETE: genau eine aktive Belegung
  - Rollback: neue Belegung löschbar
  - Reservierungsanfrage auf eigene Einrichtung → 422

Wiederverwendete Schritte (NICHT neu definieren):
  - @given("die API läuft auf http://localhost:8000")      — capacity_steps.py
  - @then("ist der HTTP-Status {expected_status:d}")        — capacity_steps.py
"""
import os
from datetime import date, timedelta
from uuid import uuid4

import requests
from behave import given, then, when

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def _auth_headers(context) -> dict:
    t = getattr(context, "auth_token", None)
    return {"Authorization": f"Bearer {t}"} if t else {}


def _loc_headers(context, loc_id: str) -> dict:
    return {**_auth_headers(context), "X-Location-Id": loc_id}


def _today() -> str:
    return date.today().isoformat()


def _in_days(n: int) -> str:
    return (date.today() + timedelta(days=n)).isoformat()


def _post(context, path: str, body: dict, loc_id: str | None = None) -> requests.Response:
    headers = _loc_headers(context, loc_id) if loc_id else _auth_headers(context)
    return requests.post(f"{BACKEND_URL}{path}", json=body, headers=headers, timeout=15)


def _delete(context, path: str, loc_id: str | None = None) -> requests.Response:
    headers = _loc_headers(context, loc_id) if loc_id else _auth_headers(context)
    return requests.delete(f"{BACKEND_URL}{path}", headers=headers, timeout=15)


def _get(context, path: str, loc_id: str | None = None) -> requests.Response:
    headers = _loc_headers(context, loc_id) if loc_id else _auth_headers(context)
    return requests.get(f"{BACKEND_URL}{path}", headers=headers, timeout=15)


def _setup_location_with_rooms(context) -> tuple[str, str, str]:
    """
    Erstellt eine Location mit:
      - Einem WARTEPLATZ-Bett in einem Wartebereich-Raum
      - Einem KONTINGENT-Bett in einem Standard-Raum
    Gibt (loc_id, wartebereich_bed_id, kontingent_bed_id) zurück.
    """
    requests.post(
        f"{BACKEND_URL}/api/system/eu-quota",
        json={"eu_gesamtquote": 9999},
        headers=_auth_headers(context),
        timeout=15,
    )
    loc_name = f"Verlege-Test-{uuid4().hex[:6].upper()}"
    resp = _post(
        context,
        "/api/locations",
        {"name": loc_name, "kontingent": 10, "adresse": ""},
    )
    assert resp.status_code == 201, f"Location create failed: {resp.status_code} — {resp.text}"
    loc_id = resp.json()["id"]

    # Wartebereich-Raum
    resp = _post(
        context,
        f"/api/locations/{loc_id}/rooms",
        {"name": "Wartebereich", "geschlechts_designation": "D"},
    )
    assert resp.status_code == 201, f"Wartebereich-Room create failed: {resp.status_code} — {resp.text}"
    wartebereich_room_id = resp.json()["id"]

    # WARTEPLATZ-Bett
    resp = _post(
        context,
        f"/api/rooms/{wartebereich_room_id}/beds",
        {"bett_nummer": "W-001", "bett_typ": "WARTEPLATZ"},
    )
    assert resp.status_code == 201, f"Warteplatz-Bed create failed: {resp.status_code} — {resp.text}"
    wartebereich_bed_id = resp.json()["id"]

    # Standard-Raum
    resp = _post(
        context,
        f"/api/locations/{loc_id}/rooms",
        {"name": "Standard-Raum", "geschlechts_designation": "M"},
    )
    assert resp.status_code == 201, f"Standard-Room create failed: {resp.status_code} — {resp.text}"
    standard_room_id = resp.json()["id"]

    # KONTINGENT-Bett
    resp = _post(
        context,
        f"/api/rooms/{standard_room_id}/beds",
        {"bett_nummer": "K-001", "bett_typ": "KONTINGENT"},
    )
    assert resp.status_code == 201, f"Kontingent-Bed create failed: {resp.status_code} — {resp.text}"
    kontingent_bed_id = resp.json()["id"]

    return loc_id, wartebereich_bed_id, kontingent_bed_id


# ---------------------------------------------------------------------------
# Given-Schritte
# ---------------------------------------------------------------------------


@given("eine Einrichtung mit Wartebereich und KONTINGENT-Bett für den Verlege-Test existiert")
def step_setup_verlege_location(context):
    """
    Legt eine Einrichtung mit Wartebereich-Bett (WARTEPLATZ) und
    Standard-Bett (KONTINGENT) an.
    Registriert die Location in context.loc_map für Cleanup.
    """
    loc_id, wartebereich_bed_id, kontingent_bed_id = _setup_location_with_rooms(context)

    context.verlege_loc_id = loc_id
    context.verlege_wartebereich_bed_id = wartebereich_bed_id
    context.verlege_kontingent_bed_id = kontingent_bed_id
    context.verlege_azr_id = f"AZR-VERLG-{uuid4().hex[:6].upper()}"

    context.loc_map = getattr(context, "loc_map", {})
    context.loc_map[f"verlege-{loc_id}"] = loc_id


@given("eine Person ist im Wartebereich-Bett belegt")
def step_person_in_wartebereich(context):
    """Bucht die Testperson in das Wartebereich-Bett ein."""
    resp = _post(
        context,
        f"/api/beds/{context.verlege_wartebereich_bed_id}/occupancy",
        {
            "azr_id": context.verlege_azr_id,
            "geschlecht": "M",
            "belegung_start": _today(),
            "belegung_ende": _in_days(30),
        },
        loc_id=context.verlege_loc_id,
    )
    assert resp.status_code == 201, (
        f"Wartebereich-Belegung create failed: {resp.status_code} — {resp.text}"
    )
    context.verlege_wartebereich_occ_id = resp.json()["id"]


# ---------------------------------------------------------------------------
# When-Schritte
# ---------------------------------------------------------------------------


@when("ich die Person mit verlegung_grund in das KONTINGENT-Bett einbuche")
def step_post_new_kontingent_occupancy(context):
    """
    POST neue Belegung mit verlegung_grund in das KONTINGENT-Bett.
    Überbrückt kurze Doppelbelegung während des internen Verlegens.
    """
    context.response = _post(
        context,
        f"/api/beds/{context.verlege_kontingent_bed_id}/occupancy",
        {
            "azr_id": context.verlege_azr_id,
            "geschlecht": "M",
            "belegung_start": _today(),
            "belegung_ende": _in_days(30),
            "verlegung_grund": "Internes Verlegen vom Warteplatz",
        },
        loc_id=context.verlege_loc_id,
    )
    if context.response.status_code == 201:
        context.verlege_kontingent_occ_id = context.response.json()["id"]


@when("ich die alte Wartebereich-Belegung lösche")
def step_delete_old_wartebereich_occupancy(context):
    """
    DELETE die alte Wartebereich-Belegung nach dem internen Verlegen.
    Erwartet 200.
    """
    context.response = _delete(
        context,
        f"/api/beds/{context.verlege_wartebereich_bed_id}/occupancy/{context.verlege_wartebereich_occ_id}",
        loc_id=context.verlege_loc_id,
    )


@when("ich die neue KONTINGENT-Belegung wieder lösche")
def step_delete_new_kontingent_occupancy(context):
    """
    DELETE die neue KONTINGENT-Belegung (Rollback-Szenario).
    Erwartet 200.
    """
    context.response = _delete(
        context,
        f"/api/beds/{context.verlege_kontingent_bed_id}/occupancy/{context.verlege_kontingent_occ_id}",
        loc_id=context.verlege_loc_id,
    )


@when("ich eine Reservierungsanfrage von der eigenen Einrichtung auf sich selbst sende")
def step_self_reservation(context):
    """
    POST /api/reservations mit requester_location_id == target_location_id.
    Der Wizard darf diesen Pfad NICHT verwenden; Backend muss 422 zurückgeben.
    """
    context.response = _post(
        context,
        "/api/reservations",
        {
            "target_location_id": context.verlege_loc_id,
            "azr_id": context.verlege_azr_id,
            "geschlecht": "M",
            "geburtsjahr": 1990,
            "herkunftsland": "DEU",
            "belegung_start": _in_days(1),
            "belegung_ende": _in_days(30),
        },
        loc_id=context.verlege_loc_id,
    )


# ---------------------------------------------------------------------------
# Then-Schritte
# ---------------------------------------------------------------------------


@then("hat die Person genau eine aktive Belegung")
def step_person_has_exactly_one_occupancy(context):
    """
    Prüft via GET /api/occupants?azr_id=... dass die Person
    genau eine aktive Belegung hat.
    """
    resp = _get(
        context,
        f"/api/occupants/search?azr_id={context.verlege_azr_id}",
        loc_id=context.verlege_loc_id,
    )
    assert resp.status_code == 200, (
        f"GET /api/occupants fehlgeschlagen: HTTP {resp.status_code} — {resp.text}"
    )
    try:
        body = resp.json()
    except Exception:
        raise AssertionError(
            f"Antwort ist kein gültiges JSON. Body: {resp.text[:500]}"
        )
    # Filtere auf aktive Belegungen (kein belegung_ende in der Vergangenheit)
    today = date.today().isoformat()
    active = [
        occ for occ in body
        if occ.get("belegung_ende", "9999-12-31") >= today
    ]
    assert len(active) == 1, (
        f"Erwartet genau 1 aktive Belegung für {context.verlege_azr_id}, "
        f"gefunden: {len(active)}. Alle Belegungen: {body}"
    )
