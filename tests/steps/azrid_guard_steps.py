"""
Behave Step-Definitionen für azrid_einzel_belegung.feature.
Testet den Backend-Guard, der doppelte aktive Belegungen pro azr_id verhindert.

Wiederverwendete Schritte (NICHT neu definieren):
  - @given("die API läuft auf http://localhost:8000")      — capacity_steps.py
  - @then("ist der HTTP-Status {expected_status:d}")        — capacity_steps.py
  - @then('die Fehlermeldung enthält "{text}"')             — capacity_steps.py
"""
import os
from datetime import date, timedelta
from uuid import uuid4

import requests
from behave import given, when

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


def _yesterday() -> str:
    return (date.today() - timedelta(days=1)).isoformat()


def _post(context, path: str, body: dict, loc_id: str | None = None) -> requests.Response:
    headers = _loc_headers(context, loc_id) if loc_id else _auth_headers(context)
    return requests.post(f"{BACKEND_URL}{path}", json=body, headers=headers, timeout=15)


def _delete(context, path: str, loc_id: str | None = None) -> requests.Response:
    headers = _loc_headers(context, loc_id) if loc_id else _auth_headers(context)
    return requests.delete(f"{BACKEND_URL}{path}", headers=headers, timeout=15)


def _setup_location(context) -> str:
    """Erstellt eine Location mit erhöhter EU-Quote und gibt die ID zurück."""
    requests.post(
        f"{BACKEND_URL}/api/system/eu-quota",
        json={"eu_gesamtquote": 9999},
        headers=_auth_headers(context),
        timeout=15,
    )
    resp = _post(
        context,
        "/api/locations",
        {"name": f"Guard-AZR-Loc-{uuid4().hex[:6].upper()}", "kontingent": 5, "adresse": ""},
    )
    assert resp.status_code == 201, f"Location create failed: {resp.status_code} — {resp.text}"
    return resp.json()["id"]


def _setup_room(context, loc_id: str) -> str:
    resp = _post(
        context,
        f"/api/locations/{loc_id}/rooms",
        {"name": "Testraum", "geschlechts_designation": "M"},
    )
    assert resp.status_code == 201, f"Room create failed: {resp.status_code} — {resp.text}"
    return resp.json()["id"]


def _setup_bed(context, room_id: str, nummer: str) -> str:
    resp = _post(
        context,
        f"/api/rooms/{room_id}/beds",
        {"bett_nummer": nummer, "bett_typ": "KONTINGENT"},
    )
    assert resp.status_code == 201, f"Bed create failed: {resp.status_code} — {resp.text}"
    return resp.json()["id"]


def _setup_occupancy(
    context,
    bed_id: str,
    azr_id: str,
    loc_id: str,
    start: str,
    ende: str,
) -> str:
    resp = _post(
        context,
        f"/api/beds/{bed_id}/occupancy",
        {
            "azr_id": azr_id,
            "geschlecht": "M",
            "belegung_start": start,
            "belegung_ende": ende,
        },
        loc_id=loc_id,
    )
    assert resp.status_code == 201, f"Occupancy create failed: {resp.status_code} — {resp.text}"
    return resp.json()["id"]


# ---------------------------------------------------------------------------
# Given-Schritte
# ---------------------------------------------------------------------------


@given("eine Einrichtung mit zwei Betten für den Guard-Test existiert")
def step_setup_guard_location(context):
    """
    Legt eine Location mit einem Raum und zwei KONTINGENT-Betten an.
    Speichert IDs in context für nachfolgende Schritte.
    Registriert die Location in context.loc_map für Cleanup.
    """
    loc_id = _setup_location(context)
    room_id = _setup_room(context, loc_id)
    bed1_id = _setup_bed(context, room_id, "B-001")
    bed2_id = _setup_bed(context, room_id, "B-002")

    # Eindeutiger AZR-Präfix pro Test-Run
    azr_prefix = f"AZR-DUP-{uuid4().hex[:6].upper()}"

    context.guard_loc_id = loc_id
    context.guard_bed1_id = bed1_id
    context.guard_bed2_id = bed2_id
    context.guard_azr_id = azr_prefix

    # Cleanup-Registrierung
    context.loc_map = getattr(context, "loc_map", {})
    context.loc_map[f"guard-azr-{loc_id}"] = loc_id


@given("eine Person ist in Bett 1 aktiv belegt")
def step_person_active_in_bed1(context):
    """Bucht die Testperson in Bett 1 für heute bis in 10 Tagen ein."""
    occ_id = _setup_occupancy(
        context,
        context.guard_bed1_id,
        context.guard_azr_id,
        context.guard_loc_id,
        _today(),
        _in_days(10),
    )
    context.guard_occ1_id = occ_id


@given("eine Person hat nur eine historische Belegung in Bett 1 (Ende gestern)")
def step_person_historical_in_bed1(context):
    """Legt eine Belegung an, die gestern endete (historisch, nicht mehr aktiv)."""
    occ_id = _setup_occupancy(
        context,
        context.guard_bed1_id,
        context.guard_azr_id,
        context.guard_loc_id,
        _in_days(-10),
        _yesterday(),
    )
    context.guard_occ1_id = occ_id


# ---------------------------------------------------------------------------
# When-Schritte
# ---------------------------------------------------------------------------


@when("ich versuche dieselbe Person ohne verlegung_grund in Bett 2 einzubuchen")
def step_try_duplicate_without_grund(context):
    """
    Versucht die Person (gleiche azr_id) ohne verlegung_grund in Bett 2 einzubuchen.
    Erwartet: Backend-Guard greift → 409.
    """
    context.response = _post(
        context,
        f"/api/beds/{context.guard_bed2_id}/occupancy",
        {
            "azr_id": context.guard_azr_id,
            "geschlecht": "M",
            "belegung_start": _today(),
            "belegung_ende": _in_days(10),
        },
        loc_id=context.guard_loc_id,
    )


@when("ich dieselbe Person mit verlegung_grund in Bett 2 einbuche")
def step_book_with_verlegung_grund(context):
    """
    Bucht die Person mit gesetztem verlegung_grund in Bett 2.
    Erwartet: Guard wird übersprungen → 201.
    """
    context.response = _post(
        context,
        f"/api/beds/{context.guard_bed2_id}/occupancy",
        {
            "azr_id": context.guard_azr_id,
            "geschlecht": "M",
            "belegung_start": _today(),
            "belegung_ende": _in_days(10),
            "verlegung_grund": "Internes Verlegen",
        },
        loc_id=context.guard_loc_id,
    )


@when("ich dieselbe Person ohne verlegung_grund in Bett 2 für einen nicht-überlappenden Zeitraum einbuche")
def step_book_non_overlapping(context):
    """
    Bucht die Person in Bett 2 für einen Zeitraum, der sich NICHT mit der
    bestehenden Belegung (heute bis +10 Tage) überschneidet (ab +15 Tagen).
    Erwartet: Kein Guard → 201.
    """
    context.response = _post(
        context,
        f"/api/beds/{context.guard_bed2_id}/occupancy",
        {
            "azr_id": context.guard_azr_id,
            "geschlecht": "M",
            "belegung_start": _in_days(15),
            "belegung_ende": _in_days(25),
        },
        loc_id=context.guard_loc_id,
    )


@when("ich dieselbe Person ohne verlegung_grund in Bett 2 einbuche")
def step_book_after_historical(context):
    """
    Bucht die Person (nach historischer Belegung) ohne verlegung_grund in Bett 2.
    Da die einzige Belegung bereits beendet ist, greift der Guard nicht → 201.
    """
    context.response = _post(
        context,
        f"/api/beds/{context.guard_bed2_id}/occupancy",
        {
            "azr_id": context.guard_azr_id,
            "geschlecht": "M",
            "belegung_start": _today(),
            "belegung_ende": _in_days(10),
        },
        loc_id=context.guard_loc_id,
    )
