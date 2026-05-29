"""Behave steps für den SuggestionWizard (Bettsuche / Verlegungsvorschlag)."""
import uuid
from datetime import date, timedelta

import requests
from behave import given, then, when

BASE_URL = "http://localhost:8000"
TODAY = date.today()
IN_30 = TODAY + timedelta(days=30)


# ─── Hilfsfunktionen ────────────────────────────────────────────────────────

def _loc_id(short: str) -> str:
    """Deterministischer UUID aus einem kurzen Kürzel."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"test-loc::{short}"))


def _room_id(loc_id: str, room_name: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{loc_id}::{room_name}"))


def _bed_id(room_id: str, nr: int) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{room_id}::{nr}"))


def _create_location(context, name: str, loc_uuid: str):
    import psycopg2

    conn = psycopg2.connect(
        host="localhost", port=5432, dbname="bordercap",
        user="bordercap", password="bordercap_dev",
    )
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO capacity.locations
                (id, name, adresse, kontingent, notbett_kapazitaet,
                 labels, lat, lon, is_active, created_at, updated_at)
            VALUES (%s, %s, %s, 50, 0, %s, 0, 0, TRUE, NOW(), NOW())
            ON CONFLICT (id) DO NOTHING
        """, (loc_uuid, name, f"Teststraße 1, Teststadt", []))
    conn.close()


def _create_free_beds(context, loc_uuid: str, count: int, geschlecht: str):
    """Legt einen Raum mit `count` freien Betten für das Geschlecht an."""
    import psycopg2

    label = {"M": "Männer", "W": "Frauen", "D": "Familie"}.get(geschlecht, "Männer")
    room_name = f"Testraum-{geschlecht}"
    room_uuid = _room_id(loc_uuid, room_name)

    conn = psycopg2.connect(
        host="localhost", port=5432, dbname="bordercap",
        user="bordercap", password="bordercap_dev",
    )
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO capacity.rooms
                (id, location_id, name, geschlechts_designation,
                 labels, room_type, is_active, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, 'STANDARD', TRUE, NOW(), NOW())
            ON CONFLICT (id) DO NOTHING
        """, (room_uuid, loc_uuid, room_name, geschlecht, [label]))
        for nr in range(1, count + 1):
            bed_uuid = _bed_id(room_uuid, nr)
            cur.execute("""
                INSERT INTO capacity.beds
                    (id, room_id, bett_nummer, bett_typ,
                     labels, is_active, created_at, updated_at)
                VALUES (%s, %s, %s, 'KONTINGENT', %s, TRUE, NOW(), NOW())
                ON CONFLICT (id) DO NOTHING
            """, (bed_uuid, room_uuid, str(nr), []))
    conn.close()


def _get_token_for(context, loc_short: str) -> tuple[str, str]:
    """Gibt (token, loc_uuid) zurück. Nutzt den writer_user mit X-Location-Id-Header."""
    return context.auth_token, _loc_id(loc_short)


# ─── Given ──────────────────────────────────────────────────────────────────

@given('die Datenbank ist leer (Suggestion-Test-Isolation)')
def step_db_clean(context):
    """Löscht alle Kapazitäts- und Reservierungsdaten für saubere Testisolation."""
    import psycopg2
    conn = psycopg2.connect(
        host="localhost", port=5432, dbname="bordercap",
        user="bordercap", password="bordercap_dev",
    )
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("DELETE FROM tasks.inbox")
        cur.execute("DELETE FROM reservations.requests")
        cur.execute("DELETE FROM persons.occupants")
        cur.execute("DELETE FROM capacity.beds")
        cur.execute("DELETE FROM capacity.rooms")
        cur.execute("DELETE FROM capacity.locations")
        cur.execute("DELETE FROM audit.events")
    conn.close()
    context.loc_map = {}


@given('eine Einrichtung "{name}" mit ID "{short}" existiert mit 0 freien Betten')
def step_loc_no_free_beds(context, name, short):
    loc_uuid = _loc_id(short)
    _create_location(context, name, loc_uuid)
    # Kein Raum, keine Betten → 0 freie Plätze
    context.loc_map = getattr(context, "loc_map", {})
    context.loc_map[short] = {"uuid": loc_uuid, "name": name}
    context.loc_map[name] = {"uuid": loc_uuid, "name": name}


@given('eine Einrichtung "{name}" mit ID "{short}" existiert mit {count:d} freien Männerbetten')
def step_loc_free_male_beds(context, name, short, count):
    loc_uuid = _loc_id(short)
    _create_location(context, name, loc_uuid)
    _create_free_beds(context, loc_uuid, count, "M")
    context.loc_map = getattr(context, "loc_map", {})
    context.loc_map[short] = {"uuid": loc_uuid, "name": name}
    context.loc_map[name] = {"uuid": loc_uuid, "name": name}


@given('eine Einrichtung "{name}" mit ID "{short}" existiert mit {count:d} freien Frauenbetten')
def step_loc_free_female_beds(context, name, short, count):
    loc_uuid = _loc_id(short)
    _create_location(context, name, loc_uuid)
    _create_free_beds(context, loc_uuid, count, "W")
    context.loc_map = getattr(context, "loc_map", {})
    context.loc_map[short] = {"uuid": loc_uuid, "name": name}
    context.loc_map[name] = {"uuid": loc_uuid, "name": name}


# ─── When ───────────────────────────────────────────────────────────────────

@when(
    'ich POST /api/suggestions sende als Einrichtung "{loc_short}" '
    'mit anzahl={anzahl:d} geschlecht={geschlecht} cross_location={cross}'
)
def step_post_suggestions(context, loc_short, anzahl, geschlecht, cross):
    token, loc_uuid = _get_token_for(context, loc_short)
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Location-Id": loc_uuid,
        "Content-Type": "application/json",
    }
    payload = {
        "geschlecht": geschlecht,
        "anzahl": anzahl,
        "belegung_start": str(TODAY),
        "belegung_ende": str(IN_30),
        "cross_location": cross.lower() == "true",
    }
    resp = requests.post(f"{BASE_URL}/api/suggestions", json=payload, headers=headers, timeout=10)
    context.response = resp
    context.response_json = resp.json() if resp.ok else {}
    context.variants = context.response_json.get("variants", [])


# ─── Then ───────────────────────────────────────────────────────────────────

@then('ist der HTTP-Status {expected:d}')
def step_check_status(context, expected):
    actual = context.response.status_code
    assert actual == expected, (
        f"Erwartet HTTP {expected}, bekommen {actual}. Body: {context.response.text[:300]}"
    )


@then('die Antwort enthält genau {count:d} Varianten')
def step_variant_count(context, count):
    actual = len(context.variants)
    assert actual == count, (
        f"Erwartet {count} Varianten, bekommen {actual}.\n"
        f"Varianten: {[v['location_name'] for v in context.variants]}"
    )


@then('jede Variante enthält genau {count:d} Bett')
def step_each_variant_beds(context, count):
    wrong = [v for v in context.variants if len(v.get("beds", [])) != count]
    assert not wrong, (
        f"{len(wrong)} Varianten haben nicht genau {count} Bett(en):\n"
        + "\n".join(f"  {v['location_name']}: {len(v['beds'])} Betten" for v in wrong[:5])
    )


@then('die Einrichtung "{name}" ist in {count:d} Varianten vertreten')
def step_location_variant_count(context, name, count):
    loc_info = getattr(context, "loc_map", {}).get(name, {})
    loc_name = loc_info.get("name", name)
    matching = [v for v in context.variants if v.get("location_name") == loc_name]
    actual = len(matching)
    assert actual == count, (
        f'Einrichtung "{loc_name}" sollte in {count} Varianten stehen, '
        f"ist aber in {actual}.\n"
        f"Alle Einrichtungen: {sorted(set(v['location_name'] for v in context.variants))}"
    )


@then('die Einrichtung "{name}" erscheint nicht in den Varianten')
def step_location_absent(context, name):
    loc_info = getattr(context, "loc_map", {}).get(name, {})
    loc_name = loc_info.get("name", name)
    matching = [v for v in context.variants if v.get("location_name") == loc_name]
    assert not matching, (
        f'Einrichtung "{loc_name}" sollte nicht in Varianten erscheinen, '
        f"taucht aber {len(matching)}× auf."
    )


@then('alle Varianten gehören zu Frauenräumen')
def step_all_female_rooms(context, ):
    wrong = []
    for v in context.variants:
        for bed in v.get("beds", []):
            labels = bed.get("room_labels", [])
            if "Männer" in labels:
                wrong.append(bed)
    assert not wrong, (
        f"{len(wrong)} Betten in Männerräumen bei Frauen-Suche:\n"
        + "\n".join(f"  {b['room_name']}" for b in wrong[:5])
    )


@then('alle Varianten gehören zur Einrichtung "{name}"')
def step_all_variants_own_loc(context, name):
    loc_info = getattr(context, "loc_map", {}).get(name, {})
    loc_name = loc_info.get("name", name)
    wrong = [v for v in context.variants if v.get("location_name") != loc_name]
    assert not wrong, (
        f"{len(wrong)} Varianten gehören nicht zu '{loc_name}':\n"
        + "\n".join(f"  {v['location_name']}" for v in wrong[:5])
    )


@then('die Einrichtung "{name}" ist in maximal {count:d} Varianten vertreten')
def step_location_max_variant_count(context, name, count):
    loc_info = getattr(context, "loc_map", {}).get(name, {})
    loc_name = loc_info.get("name", name)
    matching = [v for v in context.variants if v.get("location_name") == loc_name]
    actual = len(matching)
    assert actual <= count, (
        f'Einrichtung "{loc_name}" hat {actual} Varianten — maximal {count} erwartet.'
    )


@then('jede Variante enthält genau {count:d} Betten')
def step_each_variant_beds_plural(context, count):
    wrong = [v for v in context.variants if len(v.get("beds", [])) != count]
    assert not wrong, (
        f"{len(wrong)} Varianten haben nicht genau {count} Bett(en):\n"
        + "\n".join(f"  {v['location_name']}: {len(v['beds'])} Betten" for v in wrong[:5])
    )
