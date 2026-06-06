"""
Behave Step-Definitionen für wartebereich_sb.feature.
Testet: Schnelleinbuchen auf Warteplatz (mit/ohne freies Bett) + freies Bett löschen.
"""
import os
import uuid
from datetime import date, timedelta

import psycopg2
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


def _db_connect():
    return psycopg2.connect(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        dbname=os.environ.get("POSTGRES_DB", "bordercap"),
        user=os.environ.get("POSTGRES_USER", "bordercap"),
        password=os.environ.get("POSTGRES_PASSWORD", "bordercap_dev"),
    )


def _loc_uuid(name: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"wartebereich-sb-test::{name}"))


def _room_uuid(loc_id: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{loc_id}::warte-room"))


def _bed_uuid(room_id: str, nr: int) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{room_id}::bed::{nr}"))


def _occ_uuid(bed_id: str, azr: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"warte-occ::{bed_id}::{azr}"))


# ─── cleanup helper ─────────────────────────────────────────────────────────

def _cleanup(loc_id: str, room_id: str):
    conn = _db_connect()
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM persons.occupants WHERE bed_id IN "
            "(SELECT id FROM capacity.beds WHERE room_id = %s)",
            (room_id,),
        )
        cur.execute("DELETE FROM capacity.beds WHERE room_id = %s", (room_id,))
        cur.execute("DELETE FROM capacity.rooms WHERE id = %s", (room_id,))
        cur.execute("DELETE FROM capacity.locations WHERE id = %s", (loc_id,))
    conn.close()


# ─── Given ──────────────────────────────────────────────────────────────────

@given('eine Einrichtung "{loc_name}" mit Wartebereich existiert')
def step_create_einrichtung(context, loc_name):
    loc_id = _loc_uuid(loc_name)
    room_id = _room_uuid(loc_id)
    context.sb_loc_id = loc_id
    context.sb_room_id = room_id
    context.sb_beds_before = 0

    # Cleanup any leftover data from previous runs
    _cleanup(loc_id, room_id)

    conn = _db_connect()
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO capacity.locations
                (id, name, adresse, kontingent, notbett_kapazitaet,
                 labels, lat, lon, is_active, created_at, updated_at)
            VALUES (%s, 'Warte-SB-Test', 'Teststr. 1', 0, 0, %s, 0, 0, TRUE, NOW(), NOW())
            ON CONFLICT (id) DO NOTHING
            """,
            (loc_id, []),
        )
        cur.execute(
            """
            INSERT INTO capacity.rooms
                (id, location_id, name, geschlechts_designation,
                 labels, room_type, is_active, created_at, updated_at)
            VALUES (%s, %s, 'Wartebereich', 'D', %s, 'WARTEBEREICH', TRUE, NOW(), NOW())
            ON CONFLICT (id) DO NOTHING
            """,
            (room_id, loc_id, []),
        )
    conn.close()


@given('der Wartebereich hat {count:d} freien Platz')
def step_add_free_beds(context, count):
    room_id = context.sb_room_id
    conn = _db_connect()
    conn.autocommit = True
    with conn.cursor() as cur:
        for nr in range(1, count + 1):
            bed_id = _bed_uuid(room_id, nr)
            cur.execute(
                """
                INSERT INTO capacity.beds
                    (id, room_id, bett_nummer, bett_typ,
                     labels, is_active, created_at, updated_at)
                VALUES (%s, %s, %s, 'WARTEPLATZ', %s, TRUE, NOW(), NOW())
                ON CONFLICT (id) DO NOTHING
                """,
                (bed_id, room_id, str(nr), []),
            )
            context.sb_free_bed_id = bed_id
    conn.close()
    context.sb_beds_before = count


@given('alle Wartebereich-Plätze in "Warte-SB-Test" sind belegt')
def step_all_beds_occupied(context):
    room_id = context.sb_room_id
    bed_id = _bed_uuid(room_id, 1)
    occ_id = _occ_uuid(bed_id, "AZR-BELEGT-FILL")
    conn = _db_connect()
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO capacity.beds
                (id, room_id, bett_nummer, bett_typ, labels, is_active, created_at, updated_at)
            VALUES (%s, %s, '1', 'WARTEPLATZ', %s, TRUE, NOW(), NOW())
            ON CONFLICT (id) DO NOTHING
            """,
            (bed_id, room_id, []),
        )
        cur.execute(
            """
            INSERT INTO persons.occupants
                (id, bed_id, azr_id, alias_id, geschlecht,
                 belegung_start, belegung_ende, labels, created_at)
            VALUES (%s, %s, 'AZR-BELEGT-FILL', NULL, 'M', %s, %s, %s, NOW())
            ON CONFLICT (id) DO NOTHING
            """,
            (occ_id, bed_id, _today(), _in_days(30), []),
        )
    conn.close()
    context.sb_beds_before = 1


@given('Person "{azr}" belegt den Warteplatz')
def step_person_belegt_warteplatz(context, azr):
    bed_id = context.sb_free_bed_id
    occ_id = _occ_uuid(bed_id, azr)
    conn = _db_connect()
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO persons.occupants
                (id, bed_id, azr_id, alias_id, geschlecht,
                 belegung_start, belegung_ende, labels, created_at)
            VALUES (%s, %s, %s, NULL, 'M', %s, %s, %s, NOW())
            ON CONFLICT (id) DO NOTHING
            """,
            (occ_id, bed_id, azr, _today(), _in_days(30), []),
        )
    conn.close()


# ─── When ───────────────────────────────────────────────────────────────────

@when('SB legt über die API einen neuen Warteplatz an')
def step_sb_add_warteplatz(context):
    room_id = context.sb_room_id
    resp = requests.get(
        f"{BACKEND_URL}/api/locations/{context.sb_loc_id}/bed-status",
        headers=_loc_headers(context, context.sb_loc_id),
    )
    assert resp.status_code == 200, f"bed-status failed: {resp.text}"
    rooms_data = resp.json()
    warte_rooms = [r for r in rooms_data if r["room_type"] == "WARTEBEREICH"]
    assert warte_rooms, "Kein WARTEBEREICH-Raum gefunden"
    all_beds = [b for r in warte_rooms for b in r["beds"]]
    max_num = max(
        (int("".join(c for c in b["bett_nummer"] if c.isdigit()) or "0") for b in all_beds),
        default=0,
    )
    new_resp = requests.post(
        f"{BACKEND_URL}/api/rooms/{warte_rooms[0]['room_id']}/beds",
        json={"bett_nummer": str(max_num + 1), "bett_typ": "WARTEPLATZ"},
        headers=_auth_headers(context),
    )
    assert new_resp.status_code == 201, f"Bett anlegen fehlgeschlagen: {new_resp.text}"
    context.sb_add_resp = new_resp
    context.sb_beds_after_add = len(all_beds) + 1


@when('SB löscht den freien Warteplatz über die API')
def step_sb_delete_free(context):
    bed_id = context.sb_free_bed_id
    resp = requests.delete(
        f"{BACKEND_URL}/api/beds/{bed_id}",
        headers=_auth_headers(context),
    )
    context.sb_delete_resp = resp
    context.sb_deleted_bed_id = bed_id


@when('SB versucht den belegten Warteplatz zu löschen')
def step_sb_delete_occupied(context):
    bed_id = context.sb_free_bed_id
    resp = requests.delete(
        f"{BACKEND_URL}/api/beds/{bed_id}",
        headers=_auth_headers(context),
    )
    context.sb_delete_resp = resp


# ─── Then ───────────────────────────────────────────────────────────────────

@then('existiert ein zusätzlicher Warteplatz im Wartebereich')
def step_neues_bett_vorhanden(context):
    new_bed_id = context.sb_add_resp.json()["id"]
    conn = _db_connect()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT bett_typ, is_active FROM capacity.beds WHERE id = %s",
            (new_bed_id,),
        )
        row = cur.fetchone()
    conn.close()
    assert row, "Neues Bett nicht in DB gefunden"
    assert row[0] == "WARTEPLATZ", f"Falscher bett_typ: {row[0]}"
    assert row[1] is True, "Neues Bett ist nicht aktiv"


@then('ist der Warteplatz nicht mehr aktiv')
def step_warteplatz_not_active(context):
    resp = context.sb_delete_resp
    assert resp.status_code == 200, f"Löschen fehlgeschlagen: {resp.text}"
    conn = _db_connect()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT is_active FROM capacity.beds WHERE id = %s",
            (context.sb_deleted_bed_id,),
        )
        row = cur.fetchone()
    conn.close()
    assert row and row[0] is False, "Bett ist noch aktiv nach Delete"


@then('antwortet der Server mit Status {status:d}')
def step_response_status(context, status):
    resp = context.sb_delete_resp
    assert resp.status_code == status, f"Erwartet {status}, erhalten {resp.status_code}: {resp.text}"


# ─── after_scenario cleanup ─────────────────────────────────────────────────

def after_scenario(context, scenario):
    loc_id = getattr(context, "sb_loc_id", None)
    room_id = getattr(context, "sb_room_id", None)
    if loc_id and room_id:
        try:
            _cleanup(loc_id, room_id)
        except Exception:
            pass
