"""
Step-Definitionen für transfer_occupancy_history.feature.

Testet, dass beim Check-in (CONFIRMED → TRANSFERRED) die alte Belegung
nicht gelöscht, sondern auf belegung_ende = heute gesetzt wird.
"""
import os
from datetime import date, timedelta

import psycopg2
import requests
from behave import given, then, when

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")

AZR_TRANSFER_TEST = "AZR-TRANSFER-HIST-001"


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


# ─── DB-Helfer ───────────────────────────────────────────────────────────────

def _db_conn():
    return psycopg2.connect(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        dbname=os.environ.get("POSTGRES_DB", "bordercap"),
        user=os.environ.get("POSTGRES_USER", "bordercap"),
        password=os.environ.get("POSTGRES_PASSWORD", "bordercap_dev"),
    )


def _get_occupancies(azr_id: str) -> list[dict]:
    """Gibt alle Belegungen einer AZR-ID sortiert nach belegung_start zurück."""
    conn = _db_conn()
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT o.id, o.bed_id, o.belegung_start, o.belegung_ende,
                   r.location_id
            FROM persons.occupants o
            JOIN capacity.beds b ON b.id = o.bed_id
            JOIN capacity.rooms r ON r.id = b.room_id
            WHERE o.azr_id = %s
            ORDER BY o.belegung_start ASC
            """,
            (azr_id,),
        )
        rows = cur.fetchall()
    conn.close()
    return [
        {
            "id": str(row[0]),
            "bed_id": str(row[1]),
            "belegung_start": row[2],
            "belegung_ende": row[3],
            "location_id": str(row[4]),
        }
        for row in rows
    ]


# ─── Setup-Hilfsfunktionen ───────────────────────────────────────────────────

def _create_location(context, name: str) -> str:
    requests.post(
        f"{BACKEND_URL}/api/system/eu-quota",
        json={"eu_gesamtquote": 9999},
        headers=_auth(context),
        timeout=15,
    )
    resp = _post(context, "/api/locations", {"name": name, "kontingent": 5, "adresse": ""})
    assert resp.status_code == 201, f"Location '{name}': {resp.status_code} — {resp.text}"
    return resp.json()["id"]


def _create_room(context, loc_id: str, name: str = "Testraum") -> str:
    resp = _post(context, f"/api/locations/{loc_id}/rooms",
                 {"name": name, "geschlechts_designation": "M"})
    assert resp.status_code == 201, f"Room create: {resp.status_code} — {resp.text}"
    return resp.json()["id"]


def _create_bed(context, room_id: str, nummer: str = "001") -> str:
    resp = _post(context, f"/api/rooms/{room_id}/beds",
                 {"bett_nummer": nummer, "bett_typ": "KONTINGENT"})
    assert resp.status_code == 201, f"Bed create: {resp.status_code} — {resp.text}"
    return resp.json()["id"]


def _create_occupancy(context, bed_id: str, loc_id: str, azr_id: str) -> str:
    resp = _post(
        context,
        f"/api/beds/{bed_id}/occupancy",
        {
            "azr_id": azr_id,
            "geschlecht": "M",
            "belegung_start": _today(),
            "belegung_ende": _in_days(30),
        },
        loc_id=loc_id,
    )
    assert resp.status_code == 201, f"Occupancy create: {resp.status_code} — {resp.text}"
    return resp.json()["id"]


def _create_reservation(context, from_loc: str, to_loc: str, azr_id: str,
                        start: str, end: str) -> str:
    resp = _post(
        context,
        "/api/reservations",
        {
            "target_location_id": to_loc,
            "azr_id": azr_id,
            "geschlecht": "M",
            "geburtsjahr": 1990,
            "herkunftsland": "DEU",
            "belegung_start": start,
            "belegung_ende": end,
        },
        loc_id=from_loc,
    )
    assert resp.status_code == 201, f"Reservation create: {resp.status_code} — {resp.text}"
    return resp.json()["id"]


def _confirm_reservation(context, res_id: str, bed_id: str, loc_id: str) -> None:
    resp = _post(
        context,
        f"/api/reservations/{res_id}/confirm",
        {"confirmed_bed_id": bed_id},
        loc_id=loc_id,
    )
    assert resp.status_code == 200, f"Confirm: {resp.status_code} — {resp.text}"


# ─── GIVEN ───────────────────────────────────────────────────────────────────

@given("zwei aktive Einrichtungen Alpha und Beta für Transfertests existieren")
def step_two_locations_for_transfer(context):
    alpha_id = _create_location(context, "Transfer-Alpha")
    beta_id = _create_location(context, "Transfer-Beta")
    context.alpha_id = alpha_id
    context.beta_id = beta_id
    context.loc_map = getattr(context, "loc_map", {})
    context.loc_map["transfer_alpha"] = alpha_id
    context.loc_map["transfer_beta"] = beta_id


@given("ein freies Bett in Einrichtung Alpha und ein freies Bett in Einrichtung Beta existieren")
def step_beds_in_alpha_and_beta(context):
    alpha_room = _create_room(context, context.alpha_id, "Alpha-Raum")
    beta_room = _create_room(context, context.beta_id, "Beta-Raum")
    context.alpha_bed_id = _create_bed(context, alpha_room, "A-001")
    context.beta_bed_id = _create_bed(context, beta_room, "B-001")


@given("die Testperson ist aktiv in Transfer-Einrichtung Alpha eingebucht")
def step_transfer_person_active_in_alpha(context):
    context.transfer_azr_id = AZR_TRANSFER_TEST
    context.alpha_occ_id = _create_occupancy(
        context, context.alpha_bed_id, context.alpha_id, context.transfer_azr_id
    )


@given("eine bestätigte Verlegungsanfrage nach Beta für diese Person existiert")
def step_confirmed_reservation_to_beta(context):
    res_start = _in_days(1)
    res_end = _in_days(15)
    res_id = _create_reservation(
        context,
        context.alpha_id,
        context.beta_id,
        context.transfer_azr_id,
        res_start,
        res_end,
    )
    context.transfer_res_id = res_id
    context.transfer_res_start = res_start
    context.transfer_res_end = res_end
    _confirm_reservation(context, res_id, context.beta_bed_id, context.beta_id)


# ─── WHEN ────────────────────────────────────────────────────────────────────

@when("Einrichtung Beta den Transfer durchführt")
def step_beta_transfers(context):
    context.response = _post(
        context,
        f"/api/reservations/{context.transfer_res_id}/transfer",
        {},
        loc_id=context.beta_id,
    )


# ─── THEN ────────────────────────────────────────────────────────────────────

@then("die alte Belegung der Person in Alpha existiert noch in der Datenbank")
def step_old_occupancy_still_exists(context):
    occs = _get_occupancies(context.transfer_azr_id)
    alpha_occs = [o for o in occs if o["location_id"] == context.alpha_id]
    assert len(alpha_occs) >= 1, (
        f"Keine Belegung der Person in Alpha gefunden. Alle Belegungen: {occs}"
    )


@then("die alte Belegung hat belegung_ende = heute")
def step_old_occupancy_ends_today(context):
    occs = _get_occupancies(context.transfer_azr_id)
    alpha_occs = [o for o in occs if o["location_id"] == context.alpha_id]
    assert len(alpha_occs) >= 1, "Keine Alpha-Belegung gefunden."
    old_occ = alpha_occs[0]
    expected = date.today()
    actual = old_occ["belegung_ende"]
    assert actual == expected, (
        f"belegung_ende der alten Belegung: erwartet {expected}, erhalten {actual}."
    )


@then("eine aktive Belegung der Person in Einrichtung Beta existiert")
def step_new_occupancy_in_beta(context):
    occs = _get_occupancies(context.transfer_azr_id)
    beta_occs = [o for o in occs if o["location_id"] == context.beta_id]
    assert len(beta_occs) >= 1, (
        f"Keine Belegung der Person in Beta gefunden. Alle Belegungen: {occs}"
    )
    today = date.today()
    active = [o for o in beta_occs if o["belegung_ende"] > today]
    assert len(active) >= 1, (
        f"Keine aktive (belegung_ende > heute) Belegung in Beta. Beta-Belegungen: {beta_occs}"
    )


@then("die Belegungshistorie der Person enthält keine Zeitlücke")
def step_no_gap_in_history(context):
    occs = _get_occupancies(context.transfer_azr_id)
    assert len(occs) >= 2, f"Weniger als 2 Belegungen — History unvollständig: {occs}"
    # Sortiert nach belegung_start; prüfe dass jedes Ende das nächste Start abdeckt
    for i in range(len(occs) - 1):
        curr_end = occs[i]["belegung_ende"]
        next_start = occs[i + 1]["belegung_start"]
        assert curr_end >= next_start, (
            f"Lücke in der Belegungshistorie: Belegung {i} endet {curr_end}, "
            f"Belegung {i+1} beginnt {next_start}."
        )


@then('die Reservierung hat Status "{expected_status}"')
def step_reservation_status_transferred(context, expected_status: str):
    body = context.response.json()
    actual = body.get("status")
    assert actual == expected_status, (
        f"Reservierungsstatus: erwartet '{expected_status}', erhalten '{actual}'. "
        f"Vollständige Antwort: {body}"
    )
