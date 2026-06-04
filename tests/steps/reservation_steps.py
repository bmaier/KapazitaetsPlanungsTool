"""
Behave Step-Definitionen für reservation_workflow.feature.
Nutzt requests für HTTP-Requests gegen das laufende Backend.
context.reservation_id, context.location_a_id, context.location_b_id, context.location_c_id
werden zwischen Schritten weitergegeben.
"""
import os
import psycopg2
from datetime import date, timedelta

import requests
from behave import given, then, when

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------


def _auth_headers(context) -> dict:
    token = getattr(context, "auth_token", None)
    return {"Authorization": f"Bearer {token}"} if token else {}


def _location_headers(context, location_id) -> dict:
    return {**_auth_headers(context), "X-Location-Id": str(location_id)}


def _post(path: str, body: dict, headers: dict) -> requests.Response:
    return requests.post(f"{BACKEND_URL}{path}", json=body, headers=headers, timeout=15)


def _get(path: str, headers: dict) -> requests.Response:
    return requests.get(f"{BACKEND_URL}{path}", headers=headers, timeout=15)


def _delete(path: str, headers: dict) -> requests.Response:
    return requests.delete(f"{BACKEND_URL}{path}", headers=headers, timeout=15)


def _patch(path: str, body: dict, headers: dict) -> requests.Response:
    return requests.patch(f"{BACKEND_URL}{path}", json=body, headers=headers, timeout=15)


def _today() -> date:
    return date.today()


def _in_days(n: int) -> str:
    return (_today() + timedelta(days=n)).isoformat()


def _create_location(context, name: str) -> str:
    """Legt eine Einrichtung mit EU-Quota-freiem Kontingent 0 an und gibt ID zurück."""
    # Stelle sicher, dass die EU-Quote ausreicht (setze sie hoch wenn nötig)
    headers = _auth_headers(context)
    # Setze EU-Quote auf eine großzügige Zahl um Konflikte zu vermeiden
    requests.post(
        f"{BACKEND_URL}/api/system/eu-quota",
        json={"eu_gesamtquote": 9999},
        headers=headers,
        timeout=15,
    )
    resp = requests.post(
        f"{BACKEND_URL}/api/locations",
        json={"name": name, "kontingent": 0, "adresse": ""},
        headers=headers,
        timeout=15,
    )
    assert resp.status_code == 201, (
        f"Location '{name}' konnte nicht erstellt werden: "
        f"HTTP {resp.status_code} — {resp.text}"
    )
    return resp.json()["id"]


def _create_reservation(context, from_location_id: str, to_location_id: str) -> str:
    """Erstellt eine Reservierungsanfrage und gibt die ID zurück."""
    headers = _location_headers(context, from_location_id)
    resp = _post(
        "/api/reservations",
        {
            "target_location_id": to_location_id,
            "azr_id": "AZR-TEST-001",
            "geschlecht": "M",
            "geburtsjahr": 1990,
            "herkunftsland": "DEU",
            "belegung_start": _in_days(1),
            "belegung_ende": _in_days(8),
        },
        headers=headers,
    )
    assert resp.status_code == 201, (
        f"Reservierung konnte nicht erstellt werden: "
        f"HTTP {resp.status_code} — {resp.text}"
    )
    return resp.json()["id"]


# ---------------------------------------------------------------------------
# Background-Schritte
# ---------------------------------------------------------------------------


@given("zwei aktive Einrichtungen A und B existieren")
def step_two_locations_exist(context):
    """Legt zwei Einrichtungen A und B an."""
    context.location_a_id = _create_location(context, "Einrichtung A (Test)")
    context.location_b_id = _create_location(context, "Einrichtung B (Test)")


@given("eine dritte Einrichtung C existiert")
def step_third_location_exists(context):
    """Legt Einrichtung C an."""
    context.location_c_id = _create_location(context, "Einrichtung C (Test)")


# ---------------------------------------------------------------------------
# When-Schritte: Reservierungsaktionen
# ---------------------------------------------------------------------------


@when("ich POST /api/reservations sende als Einrichtung A mit Ziel B")
def step_post_reservation_a_to_b(context):
    headers = _location_headers(context, context.location_a_id)
    context.response = _post(
        "/api/reservations",
        {
            "target_location_id": context.location_b_id,
            "azr_id": "AZR-TEST-001",
            "geschlecht": "M",
            "geburtsjahr": 1990,
            "herkunftsland": "DEU",
            "belegung_start": _in_days(1),
            "belegung_ende": _in_days(8),
        },
        headers=headers,
    )
    if context.response.status_code == 201:
        context.reservation_id = context.response.json()["id"]


@when("ich POST /api/reservations sende als Einrichtung A mit Ziel A")
def step_post_reservation_a_to_a(context):
    headers = _location_headers(context, context.location_a_id)
    context.response = _post(
        "/api/reservations",
        {
            "target_location_id": context.location_a_id,
            "azr_id": "AZR-SELF-001",
            "geschlecht": "M",
            "geburtsjahr": 1985,
            "herkunftsland": "DEU",
            "belegung_start": _in_days(1),
            "belegung_ende": _in_days(8),
        },
        headers=headers,
    )


@when("ich POST /api/reservations/{reservation_id}/confirm sende als Einrichtung B")
def step_confirm_reservation_as_b(context, reservation_id: str):
    res_id = (
        context.reservation_id
        if reservation_id == "{reservation_id}"
        else reservation_id
    )
    headers = _location_headers(context, context.location_b_id)
    context.response = _post(
        f"/api/reservations/{res_id}/confirm", {}, headers=headers
    )
    if context.response.status_code == 200:
        context.reservation_id = context.response.json()["id"]


@when("ich POST /api/reservations/{reservation_id}/confirm sende als Einrichtung C")
def step_confirm_reservation_as_c(context, reservation_id: str):
    res_id = (
        context.reservation_id
        if reservation_id == "{reservation_id}"
        else reservation_id
    )
    headers = _location_headers(context, context.location_c_id)
    context.response = _post(
        f"/api/reservations/{res_id}/confirm", {}, headers=headers
    )


@when("ich POST /api/reservations/{reservation_id}/reject sende als Einrichtung B")
def step_reject_reservation_as_b(context, reservation_id: str):
    res_id = (
        context.reservation_id
        if reservation_id == "{reservation_id}"
        else reservation_id
    )
    headers = _location_headers(context, context.location_b_id)
    context.response = _post(
        f"/api/reservations/{res_id}/reject", {}, headers=headers
    )


@when("ich DELETE /api/reservations/{reservation_id} sende als Einrichtung A")
def step_delete_reservation_as_a(context, reservation_id: str):
    res_id = (
        context.reservation_id
        if reservation_id == "{reservation_id}"
        else reservation_id
    )
    headers = _location_headers(context, context.location_a_id)
    context.response = _delete(f"/api/reservations/{res_id}", headers=headers)


@when("ich DELETE /api/reservations/{reservation_id} sende als Einrichtung C")
def step_delete_reservation_as_c(context, reservation_id: str):
    res_id = (
        context.reservation_id
        if reservation_id == "{reservation_id}"
        else reservation_id
    )
    headers = _location_headers(context, context.location_c_id)
    context.response = _delete(f"/api/reservations/{res_id}", headers=headers)


@when("ich GET /api/tasks sende als Einrichtung B")
def step_get_tasks_as_b(context):
    headers = _location_headers(context, context.location_b_id)
    context.response = _get("/api/tasks", headers=headers)


@when("ich GET /api/tasks?priority=HIGH sende als Einrichtung B")
def step_get_tasks_high_priority_as_b(context):
    headers = _location_headers(context, context.location_b_id)
    context.response = _get("/api/tasks?priority=HIGH", headers=headers)


# ---------------------------------------------------------------------------
# Given-Schritte: Vorzustand
# ---------------------------------------------------------------------------


@given("eine Reservierung von A nach B im Status PENDING existiert")
def step_reservation_pending(context):
    """Erstellt eine Reservierung A→B (PENDING)."""
    context.reservation_id = _create_reservation(
        context, context.location_a_id, context.location_b_id
    )


@given("eine Reservierung von A nach B im Status TRANSFERRED existiert")
def step_reservation_transferred(context):
    """
    Erstellt eine Reservierung A→B, bestätigt sie und setzt sie auf TRANSFERRED.
    TRANSFERRED ist noch kein direkter API-Endpoint; wir simulieren über confirm + direktes
    update_status via Hilfsmethode. Da es keinen /transfer-Endpoint gibt, testen wir
    den 409-Fall durch manuelles Setzen über confirm (CONFIRMED) und dann den
    TRANSFERRED-Status via confirm-chain ist noch nicht implementiert.

    Workaround: Wir erstellen eine CONFIRMED-Reservation und versuchen dann CANCELLED darauf —
    das ist erlaubt laut VALID_TRANSITIONS. Stattdessen testen wir den 409-Fall realistisch:
    Eine REJECTED-Reservation kann nicht erneut CANCELLED werden, da REJECTED kein gültiger
    Ausgangsstatus für CANCELLED ist.

    Für TRANSFERRED: Der Übergang CONFIRMED → TRANSFERRED gibt es keinen öffentlichen Endpoint.
    Daher setzen wir den Status direkt in der DB über den psycopg2-Weg aus environment.py.
    """
    # Erstelle zuerst eine normale Reservierung
    reservation_id = _create_reservation(
        context, context.location_a_id, context.location_b_id
    )
    context.reservation_id = reservation_id

    # Bestätige sie (CONFIRMED)
    headers = _location_headers(context, context.location_b_id)
    resp = _post(
        f"/api/reservations/{reservation_id}/confirm", {}, headers=headers
    )
    assert resp.status_code == 200, (
        f"Bestätigung fehlgeschlagen: HTTP {resp.status_code} — {resp.text}"
    )

    # Setze Status direkt auf TRANSFERRED in der DB
    conn = psycopg2.connect(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        dbname=os.environ.get("POSTGRES_DB", "bordercap"),
        user=os.environ.get("POSTGRES_USER", "bordercap"),
        password=os.environ.get("POSTGRES_PASSWORD", "bordercap_dev"),
    )
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE reservations.requests SET status = 'TRANSFERRED' WHERE id = %s",
            (reservation_id,),
        )
    conn.close()


# ---------------------------------------------------------------------------
# Then-Schritte: Assertions für Reservierungen
# ---------------------------------------------------------------------------


@then('die Reservierungsantwort enthält Status "{expected_status}"')
def step_reservation_status(context, expected_status: str):
    try:
        body = context.response.json()
    except Exception:
        raise AssertionError(
            f"Antwort ist kein gültiges JSON. Body: {context.response.text[:500]}"
        )
    actual = body.get("status")
    assert actual == expected_status, (
        f"Status: erwartet '{expected_status}', erhalten '{actual}'. "
        f"Vollständige Antwort: {body}"
    )


@then('die Reservierungsantwort enthält ein "id"-Feld')
def step_reservation_has_id(context):
    try:
        body = context.response.json()
    except Exception:
        raise AssertionError(
            f"Antwort ist kein gültiges JSON. Body: {context.response.text[:500]}"
        )
    assert "id" in body, (
        f"Feld 'id' fehlt in der Antwort. Vorhandene Felder: {list(body.keys())}"
    )


@then('GET /api/tasks für Einrichtung B enthält eine neue Task vom Typ "{task_type}"')
def step_tasks_for_b_contain_type(context, task_type: str):
    headers = _location_headers(context, context.location_b_id)
    resp = _get("/api/tasks", headers=headers)
    assert resp.status_code == 200, (
        f"GET /api/tasks fehlgeschlagen: HTTP {resp.status_code} — {resp.text}"
    )
    tasks = resp.json()
    types = [t.get("task_type") for t in tasks]
    assert task_type in types, (
        f"Kein Task vom Typ '{task_type}' gefunden. Vorhandene Typen: {types}"
    )


@then('GET /api/tasks für Einrichtung A enthält eine neue Task vom Typ "{task_type}"')
def step_tasks_for_a_contain_type(context, task_type: str):
    headers = _location_headers(context, context.location_a_id)
    resp = _get("/api/tasks", headers=headers)
    assert resp.status_code == 200, (
        f"GET /api/tasks fehlgeschlagen: HTTP {resp.status_code} — {resp.text}"
    )
    tasks = resp.json()
    types = [t.get("task_type") for t in tasks]
    assert task_type in types, (
        f"Kein Task vom Typ '{task_type}' gefunden. Vorhandene Typen: {types}"
    )


@then("die Antwort ist eine nicht-leere Liste")
def step_response_is_nonempty_list(context):
    try:
        body = context.response.json()
    except Exception:
        raise AssertionError(
            f"Antwort ist kein gültiges JSON. Body: {context.response.text[:500]}"
        )
    assert isinstance(body, list), (
        f"Antwort ist keine Liste. Typ: {type(body)}"
    )
    assert len(body) > 0, "Liste ist leer, es wurden keine Einträge gefunden."


# ---------------------------------------------------------------------------
# Neue Schritte: GET /{id} + POST /{id}/cancel
# ---------------------------------------------------------------------------


def _get_reader_token(context) -> str:
    """Holt einen Token für reader_user (kein writer-Recht)."""
    if hasattr(context, "reader_auth_token"):
        return context.reader_auth_token
    keycloak_url = os.environ.get("KEYCLOAK_URL", "http://localhost:8080")
    realm = os.environ.get("KEYCLOAK_REALM", "bordercapcontrol")
    resp = requests.post(
        f"{keycloak_url}/realms/{realm}/protocol/openid-connect/token",
        data={
            "grant_type": "password",
            "client_id": "bordercapcontrol-test",
            "client_secret": os.environ.get("KEYCLOAK_TEST_CLIENT_SECRET", "bordercapcontrol-test-secret"),
            "username": "reader_user",
            "password": os.environ.get("KEYCLOAK_READER_PASSWORD", "Reader1234!"),
        },
        timeout=15,
    )
    assert resp.status_code == 200, f"Reader-Token konnte nicht geholt werden: {resp.text}"
    context.reader_auth_token = resp.json()["access_token"]
    return context.reader_auth_token


@when("ich GET /api/reservations/{reservation_id} sende als Einrichtung A")
def step_get_reservation_as_a(context, reservation_id: str):
    res_id = context.reservation_id if reservation_id == "{reservation_id}" else reservation_id
    headers = _location_headers(context, context.location_a_id)
    context.response = _get(f"/api/reservations/{res_id}", headers=headers)


@when("ich GET /api/reservations/{reservation_id} sende als Einrichtung B")
def step_get_reservation_as_b(context, reservation_id: str):
    res_id = context.reservation_id if reservation_id == "{reservation_id}" else reservation_id
    headers = _location_headers(context, context.location_b_id)
    context.response = _get(f"/api/reservations/{res_id}", headers=headers)


@when("ich GET /api/reservations/{reservation_id} sende als Einrichtung C")
def step_get_reservation_as_c(context, reservation_id: str):
    res_id = context.reservation_id if reservation_id == "{reservation_id}" else reservation_id
    headers = _location_headers(context, context.location_c_id)
    context.response = _get(f"/api/reservations/{res_id}", headers=headers)


@when('ich POST /api/reservations/{reservation_id}/cancel sende als Einrichtung A mit Grund "{grund}"')
def step_cancel_as_a(context, reservation_id: str, grund: str):
    res_id = context.reservation_id if reservation_id == "{reservation_id}" else reservation_id
    headers = _location_headers(context, context.location_a_id)
    context.response = _post(f"/api/reservations/{res_id}/cancel", {"grund": grund}, headers=headers)


@when('ich POST /api/reservations/{reservation_id}/cancel sende als Einrichtung B mit Grund "{grund}"')
def step_cancel_as_b(context, reservation_id: str, grund: str):
    res_id = context.reservation_id if reservation_id == "{reservation_id}" else reservation_id
    headers = _location_headers(context, context.location_b_id)
    context.response = _post(f"/api/reservations/{res_id}/cancel", {"grund": grund}, headers=headers)


@when('ich POST /api/reservations/{reservation_id}/cancel sende als Einrichtung C mit Grund "{grund}"')
def step_cancel_as_c(context, reservation_id: str, grund: str):
    res_id = context.reservation_id if reservation_id == "{reservation_id}" else reservation_id
    headers = _location_headers(context, context.location_c_id)
    context.response = _post(f"/api/reservations/{res_id}/cancel", {"grund": grund}, headers=headers)


@when('ich POST /api/reservations/{reservation_id}/cancel sende als Reader-User von Einrichtung A mit Grund "{grund}"')
def step_cancel_as_reader(context, reservation_id: str, grund: str):
    res_id = context.reservation_id if reservation_id == "{reservation_id}" else reservation_id
    reader_token = _get_reader_token(context)
    headers = {
        "Authorization": f"Bearer {reader_token}",
        "X-Location-Id": str(context.location_a_id),
    }
    context.response = _post(f"/api/reservations/{res_id}/cancel", {"grund": grund}, headers=headers)


@then('die Antwort enthält Felder "id", "azr_id", "status"')
def step_response_has_required_fields(context):
    try:
        body = context.response.json()
    except Exception:
        raise AssertionError(f"Antwort ist kein JSON. Body: {context.response.text[:500]}")
    for field in ("id", "azr_id", "status"):
        assert field in body, f"Feld '{field}' fehlt. Vorhanden: {list(body.keys())}"


@then('alle Tasks der Reservierung haben Status "DONE" oder "CANCELLED"')
def step_tasks_are_done(context):
    conn = psycopg2.connect(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        dbname=os.environ.get("POSTGRES_DB", "bordercap"),
        user=os.environ.get("POSTGRES_USER", "bordercap"),
        password=os.environ.get("POSTGRES_PASSWORD", "bordercap_dev"),
    )
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            "SELECT status FROM tasks.inbox WHERE related_reservation_id = %s",
            (context.reservation_id,),
        )
        rows = cur.fetchall()
    conn.close()
    assert rows, "Keine Tasks für diese Reservierung gefunden."
    for (status,) in rows:
        assert status in ("DONE", "CANCELLED"), (
            f"Task hat unerwarteten Status '{status}' — erwartet DONE oder CANCELLED."
        )
