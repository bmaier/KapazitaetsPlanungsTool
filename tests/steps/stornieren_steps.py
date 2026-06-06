"""
Behave Step-Definitionen für stornieren_postkorb_sicht.feature.

Enthält nur den NEUEN Schritt, der in reservation_steps.py noch nicht definiert ist:
  - @when("ich DELETE /api/reservations/{reservation_id} sende als Einrichtung B")

Wiederverwendete Schritte (NICHT neu definieren, in reservation_steps.py vorhanden):
  - @given("zwei aktive Einrichtungen A und B existieren")
  - @given("eine dritte Einrichtung C existiert")
  - @given("eine Reservierung von A nach B im Status PENDING existiert")
  - @when("ich DELETE /api/reservations/{reservation_id} sende als Einrichtung A")
  - @when("ich DELETE /api/reservations/{reservation_id} sende als Einrichtung C")
  - @then("ist der HTTP-Status {expected_status:d}")             — capacity_steps.py
  - @then('die Reservierungsantwort enthält Status "{expected_status}"')
"""
import os
from datetime import date, timedelta

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


def _delete(context, path: str, loc_id: str | None = None) -> requests.Response:
    headers = _loc_headers(context, loc_id) if loc_id else _auth_headers(context)
    return requests.delete(f"{BACKEND_URL}{path}", headers=headers, timeout=15)


# ---------------------------------------------------------------------------
# When-Schritte (neu)
# ---------------------------------------------------------------------------


@when("ich DELETE /api/reservations/{reservation_id} sende als Einrichtung B")
def step_delete_reservation_as_b(context, reservation_id: str):
    """
    Zieleinrichtung B versucht, die Reservierung zu stornieren.
    Erwartet: 403 (nicht berechtigt).
    """
    res_id = (
        context.reservation_id
        if reservation_id == "{reservation_id}"
        else reservation_id
    )
    context.response = _delete(
        context,
        f"/api/reservations/{res_id}",
        loc_id=context.location_b_id,
    )
