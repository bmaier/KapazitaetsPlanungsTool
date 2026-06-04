"""
Behave Step-Definitionen für warteplatz_auto_flow.feature.
Testet den API-Flow: freies Wartebereich-Bett finden → Person einbuchen → Verlegungsanfrage senden.
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
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"warteplatz-test::{name}"))


def _room_uuid(loc_id: str, suffix: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{loc_id}::room::{suffix}"))


def _bed_uuid(room_id: str, nr: int) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{room_id}::bed::{nr}"))


def _insert_location(cur, loc_id: str, name: str):
    cur.execute(
        """
        INSERT INTO capacity.locations
            (id, name, adresse, kontingent, notbett_kapazitaet,
             labels, lat, lon, is_active, created_at, updated_at)
        VALUES (%s, %s, 'Teststraße 1', 0, 0, %s, 0, 0, TRUE, NOW(), NOW())
        ON CONFLICT (id) DO NOTHING
        """,
        (loc_id, name, []),
    )


def _insert_room(cur, room_id: str, loc_id: str, name: str, room_type: str, geschlecht: str):
    label = {"M": "Männer", "W": "Frauen", "D": "Wartebereich"}.get(geschlecht, geschlecht)
    cur.execute(
        """
        INSERT INTO capacity.rooms
            (id, location_id, name, geschlechts_designation,
             labels, room_type, is_active, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, TRUE, NOW(), NOW())
        ON CONFLICT (id) DO NOTHING
        """,
        (room_id, loc_id, name, geschlecht, [label], room_type),
    )


def _insert_beds(cur, room_id: str, count: int):
    for nr in range(1, count + 1):
        bed_id = _bed_uuid(room_id, nr)
        cur.execute(
            """
            INSERT INTO capacity.beds
                (id, room_id, bett_nummer, bett_typ,
                 labels, is_active, created_at, updated_at)
            VALUES (%s, %s, %s, 'KONTINGENT', %s, TRUE, NOW(), NOW())
            ON CONFLICT (id) DO NOTHING
            """,
            (bed_id, room_id, str(nr), []),
        )


# ─── Given ──────────────────────────────────────────────────────────────────

@given('eine Quell-Einrichtung "{name}" mit Wartebereich ({count:d} freie Plätze) existiert')
def step_create_source_with_wartebereich(context, name, count):
    loc_id = _loc_uuid(name)
    room_id = _room_uuid(loc_id, "WARTEBEREICH")
    conn = _db_connect()
    conn.autocommit = True
    with conn.cursor() as cur:
        _insert_location(cur, loc_id, name)
        _insert_room(cur, room_id, loc_id, "Wartebereich", "WARTEBEREICH", "D")
        _insert_beds(cur, room_id, count)
    conn.close()
    context.loc_map = getattr(context, "loc_map", {})
    context.loc_map[name] = loc_id
    context.source_location_id = loc_id


@given('eine Ziel-Einrichtung "{name}" mit {count:d} freien Männerbetten existiert')
def step_create_target_with_standard_beds(context, name, count):
    loc_id = _loc_uuid(name)
    room_id = _room_uuid(loc_id, "STANDARD-M")
    conn = _db_connect()
    conn.autocommit = True
    with conn.cursor() as cur:
        _insert_location(cur, loc_id, name)
        _insert_room(cur, room_id, loc_id, "Männerraum", "STANDARD", "M")
        _insert_beds(cur, room_id, count)
    conn.close()
    context.loc_map = getattr(context, "loc_map", {})
    context.loc_map[name] = loc_id
    context.target_location_id = loc_id


@given('alle Wartebereich-Betten in "{name}" sind belegt')
def step_all_wartebereich_beds_occupied(context, name):
    loc_id = context.loc_map.get(name)
    assert loc_id, f"Einrichtung '{name}' nicht in loc_map"
    room_id = _room_uuid(loc_id, "WARTEBEREICH")
    conn = _db_connect()
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM capacity.beds WHERE room_id = %s AND is_active = TRUE",
            (room_id,),
        )
        beds = cur.fetchall()
        today = _today()
        in_30 = _in_days(30)
        for idx, (bed_id,) in enumerate(beds):
            occ_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"occ-belegt::{bed_id}"))
            cur.execute(
                """
                INSERT INTO persons.occupants
                    (id, bed_id, azr_id, alias_id, geschlecht,
                     belegung_start, belegung_ende, labels, created_at)
                VALUES (%s, %s, %s, NULL, 'M', %s, %s, %s, NOW())
                ON CONFLICT (id) DO NOTHING
                """,
                (occ_id, bed_id, f"AZR-BELEGT-{idx + 1:03d}", today, in_30, []),
            )
    conn.close()


# ─── When ───────────────────────────────────────────────────────────────────

@when('ich das erste freie Wartebereich-Bett in "{name}" abfrage')
def step_query_free_wartebereich_bed(context, name):
    loc_id = context.loc_map.get(name)
    assert loc_id, f"Einrichtung '{name}' nicht in loc_map"
    today = _today()
    in_30 = _in_days(30)
    headers = _loc_headers(context, loc_id)
    resp = requests.get(
        f"{BACKEND_URL}/api/locations/{loc_id}/bed-status"
        f"?date_from={today}&date_to={in_30}",
        headers=headers,
        timeout=10,
    )
    assert resp.status_code == 200, (
        f"bed-status fehlgeschlagen: HTTP {resp.status_code} — {resp.text[:300]}"
    )
    rooms = resp.json()
    free_beds = [
        b
        for r in rooms
        if r.get("room_type") == "WARTEBEREICH"
        for b in r.get("beds", [])
        if b.get("status") == "FREI"
    ]
    free_beds.sort(key=lambda b: b.get("bett_nummer", ""))
    context.free_wartebereich_beds = free_beds
    context.first_free_wartebereich_bed = free_beds[0] if free_beds else None


@when('ich "{azr_id}" (Geschlecht {geschlecht}) in das erste freie Wartebereich-Bett von "{name}" einbuche')
def step_book_person_into_wartebereich(context, azr_id, geschlecht, name):
    loc_id = context.loc_map.get(name)
    assert loc_id, f"Einrichtung '{name}' nicht in loc_map"
    bed = context.first_free_wartebereich_bed
    assert bed, "Kein freies Wartebereich-Bett — vorherigen Schritt prüfen"
    context.test_azr_id = azr_id
    context.wartebereich_bed_id = bed["bed_id"]
    today = _today()
    in_30 = _in_days(30)
    headers = _loc_headers(context, loc_id)
    resp = requests.post(
        f"{BACKEND_URL}/api/beds/{bed['bed_id']}/occupancy",
        json={
            "azr_id": azr_id,
            "geschlecht": geschlecht,
            "belegung_start": today,
            "belegung_ende": in_30,
        },
        headers=headers,
        timeout=10,
    )
    context.response = resp
    if resp.status_code == 201:
        context.occupancy_id = resp.json().get("id")


@when('ich eine Verlegungsanfrage von "{src}" nach "{dst}" für "{azr_id}" sende')
def step_send_verlegungsanfrage(context, src, dst, azr_id):
    src_id = context.loc_map.get(src)
    dst_id = context.loc_map.get(dst)
    assert src_id, f"Einrichtung '{src}' nicht in loc_map"
    assert dst_id, f"Einrichtung '{dst}' nicht in loc_map"
    in_30 = _in_days(30)
    in_60 = _in_days(60)
    headers = _loc_headers(context, src_id)
    resp = requests.post(
        f"{BACKEND_URL}/api/reservations",
        json={
            "target_location_id": dst_id,
            "azr_id": azr_id,
            "geschlecht": "M",
            "geburtsjahr": 1996,
            "herkunftsland": "UNK",
            "belegung_start": in_30,
            "belegung_ende": in_60,
        },
        headers=headers,
        timeout=10,
    )
    context.response = resp
    if resp.status_code == 201:
        context.reservation_id = resp.json().get("id")


@when('ich eine Verlegungsanfrage ohne Location-Header nach "{dst}" sende')
def step_send_reservation_no_location_header(context, dst):
    dst_id = context.loc_map.get(dst)
    assert dst_id, f"Einrichtung '{dst}' nicht in loc_map"
    in_30 = _in_days(30)
    in_60 = _in_days(60)
    resp = requests.post(
        f"{BACKEND_URL}/api/reservations",
        json={
            "target_location_id": dst_id,
            "azr_id": "AZR-NO-HEADER",
            "geschlecht": "M",
            "geburtsjahr": 1996,
            "herkunftsland": "UNK",
            "belegung_start": in_30,
            "belegung_ende": in_60,
        },
        headers=_auth_headers(context),  # kein X-Location-Id
        timeout=10,
    )
    context.response = resp


# ─── Then ───────────────────────────────────────────────────────────────────

@then('gibt es mindestens {count:d} freies Wartebereich-Bett')
def step_assert_min_free_wartebereich(context, count):
    actual = len(context.free_wartebereich_beds)
    assert actual >= count, (
        f"Erwartet mindestens {count} freies Wartebereich-Bett, gefunden: {actual}"
    )


@then('gibt es kein freies Wartebereich-Bett')
def step_assert_no_free_wartebereich(context):
    actual = len(context.free_wartebereich_beds)
    assert actual == 0, (
        f"Erwartet 0 freie Wartebereich-Betten, gefunden: {actual}. "
        f"Bett-Nummern: {[b['bett_nummer'] for b in context.free_wartebereich_beds]}"
    )


@then('die Person "{azr_id}" belegt ein Wartebereich-Bett in "{name}"')
def step_assert_person_in_wartebereich(context, azr_id, name):
    loc_id = context.loc_map.get(name)
    assert loc_id, f"Einrichtung '{name}' nicht in loc_map"
    today = _today()
    in_30 = _in_days(30)
    headers = _loc_headers(context, loc_id)
    resp = requests.get(
        f"{BACKEND_URL}/api/locations/{loc_id}/bed-status"
        f"?date_from={today}&date_to={in_30}",
        headers=headers,
        timeout=10,
    )
    assert resp.status_code == 200
    rooms = resp.json()
    occupied_in_wartebereich = [
        b.get("azr_id")
        for r in rooms
        if r.get("room_type") == "WARTEBEREICH"
        for b in r.get("beds", [])
        if b.get("status") == "BELEGT"
    ]
    assert azr_id in occupied_in_wartebereich, (
        f"Person '{azr_id}' nicht im Wartebereich von '{name}' gefunden. "
        f"Belegte Wartebereich-AZR-IDs: {occupied_in_wartebereich}"
    )
