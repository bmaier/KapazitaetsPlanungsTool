---
title: 'Verlegungsanfrage: Berechtigung + Klick-Verhalten korrigieren'
type: 'bugfix'
created: '2026-06-04'
status: 'done'
baseline_commit: '8b9cf41149d5f64b7de341f92e0d82b78d7cc285'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Ziel A (spec-verlegungsanfrage-dialog-stornierung.md) hat zwei Rollenlogik-Fehler eingebaut: (1) `check_retraction_allowed` erlaubt jetzt fälschlicherweise auch der Ziel-Einrichtung das Stornieren — nur die anfragende Einrichtung (Requester) darf stornieren; die Ziel-Einrichtung darf ausschließlich bestätigen oder ablehnen. (2) Klick auf ein FREI-Bett mit `pending_reservation_id` (= eingehende Anfrage in der Ziel-Einrichtung) öffnet jetzt einen Dialog mit Stornieren-Button statt zur Reservierungsliste zu navigieren — das unterbricht den Bestätigungs-/Ablehnungs-Workflow des Ziel-SB.

**Approach:** (1) `check_retraction_allowed` zurück auf ausschließlich `requester_location_id` (+ system-admin). (2) FREI-Bett + `pending_reservation_id` → `navigate('/reservations?highlight={id}')` — dasselbe Verhalten wie VORGEMERKT-Bett, nur mit der Pending-Reservierungs-ID. (3) Betroffenes BDD-Szenario von 200 auf 403 korrigieren.

## Boundaries & Constraints

**Always:**
- Nur Requester-Location (anfragende Einrichtung) + system-admin dürfen stornieren (POST /cancel + DELETE).
- Ziel-Einrichtung darf FREI-Bett mit pending_reservation_id klicken → Navigation zur Reservierungsliste mit Highlight, kein Dialog.
- BELEGT-Bett mit `has_pending_transfer` (outgoing, Requester-Sicht) → Dialog mit Stornieren-Button bleibt unverändert.
- VORGEMERKT-Bett → navigate mit `reservation_id` bleibt unverändert.
- GET /api/reservations/{id} (lesend) bleibt für beide Locations erlaubt.

**Ask First:** — keine offenen Fragen.

**Never:**
- Dialog mit Stornieren-Button für FREI-Betten (Ziel-Einrichtungs-Sicht).
- Ziel-Einrichtung kann weder per API noch per UI stornieren.

## I/O & Edge-Case Matrix

| Szenario | Zustand | Erwartetes Verhalten |
|----------|---------|---------------------|
| Ziel-SB klickt FREI-Bett mit pending | `pending_reservation_id` gesetzt, `status=FREI` | Navigate zu `/reservations?highlight={pending_reservation_id}` |
| Requester-SB klickt BELEGT-Bett mit Anfrage | `has_pending_transfer=true`, `outgoing_reservation_id` gesetzt | Dialog öffnet (unverändert) |
| Ziel-Einrichtung POST /cancel | location_id == target_location_id | HTTP 403 |
| Requester POST /cancel | location_id == requester_location_id | HTTP 200, Status CANCELLED |
| system-admin POST /cancel | kein X-Location-Id | HTTP 200 |

</frozen-after-approval>

## Code Map

- `backend/src/domain/reservations/rules.py:41` — `check_retraction_allowed`: Zeile mit `not in (req.requester_location_id, req.target_location_id)` zurück auf `!= req.requester_location_id`
- `frontend/src/pages/Drilldown.tsx:764` — `handleBedClick`: FREI+pending Block (Zeilen 765–769) → navigate statt setTransferDialogBed
- `tests/features/reservation_workflow.feature:100` — Szenario "Ziel-Einrichtung darf ebenfalls…" → erwartet jetzt HTTP 403

## Tasks & Acceptance

**Execution:**
- [x] `backend/src/domain/reservations/rules.py` — `check_retraction_allowed` Zeile 41: `location_id not in (req.requester_location_id, req.target_location_id)` → `location_id is None or location_id != req.requester_location_id`; Docstring anpassen: "Sonst: nur requester_location_id"
- [x] `frontend/src/pages/Drilldown.tsx` — `handleBedClick` FREI+pending Block: statt `setTransferDialogBed(bed)` → `navigate(\`/reservations?highlight=\${bed.pending_reservation_id}\`)`
- [x] `tests/features/reservation_workflow.feature` — Szenario "Ziel-Einrichtung darf POST /cancel NICHT aufrufen" erwartet jetzt HTTP 403

**Acceptance Criteria:**
- Given Ziel-SB im Drilldown, FREI-Bett mit pending_reservation_id, when Klick, then Browser navigiert zu `/reservations?highlight={id}` — kein Dialog öffnet sich.
- Given Requester-SB im Drilldown, BELEGT-Bett mit has_pending_transfer, when Klick, then Dialog öffnet sich mit Stornieren-Button (unverändert).
- Given VORGEMERKT-Bett in Ziel-Einrichtung, when Klick, then navigiert zu `/reservations?highlight={reservation_id}` (unverändert).
- Given Ziel-Einrichtung-Writer, when POST /api/reservations/{id}/cancel, then HTTP 403.
- Given Requester-Einrichtung-Writer, when POST /api/reservations/{id}/cancel mit grund, then HTTP 200 + Status CANCELLED.
- Given system-admin ohne X-Location-Id, when POST /cancel, then HTTP 200.

## Verification

**Commands:**
- `cd /Users/A3694852/KapzitaetsPlanungsTool/frontend && npx tsc --noEmit` — expected: kein Fehler
- `cd /Users/A3694852/KapzitaetsPlanungsTool && python3 -m pytest backend/tests/ -x -q 2>/dev/null || echo "no pytest"` — expected: alle Tests grün

## Suggested Review Order

1. `backend/src/domain/reservations/rules.py:41` — Kernkorrektur: `check_retraction_allowed` lässt nur noch `requester_location_id` (+ system-admin) zu.
2. `tests/features/reservation_workflow.feature:100` — Szenario "Ziel-Einrichtung darf POST /cancel NICHT aufrufen" erwartet jetzt HTTP 403.
3. `frontend/src/pages/Drilldown.tsx` (TransferReservationDetail Interface, ~Zeile 76) — `requester_location_id` Feld hinzugefügt für UI-Guard.
4. `frontend/src/pages/Drilldown.tsx:handleBedClick` (~Zeile 765) — FREI+pending Block: navigate statt setTransferDialogBed.
5. `frontend/src/pages/Drilldown.tsx` (Dialog JSX, Stornieren-Button) — Guard `transferDialogDetail?.requester_location_id === id` schützt Button + Begründungsfeld.

## Design Notes

FREI-Bett+pending verhält sich nach der Korrektur identisch zu VORGEMERKT-Bett — beide navigieren zur Reservierungsliste mit Highlight-Parameter. Der Unterschied: FREI nutzt `bed.pending_reservation_id`, VORGEMERKT nutzt `bed.reservation_id`. Der `useEffect` im TransferRequestDialog-Block wird dadurch nur noch für BELEGT-Betten (outgoing) ausgelöst; der `?? bed.pending_reservation_id`-Fallback in Zeile 720 ist nach dieser Änderung nicht mehr erreichbar, bleibt aber harmlos.
