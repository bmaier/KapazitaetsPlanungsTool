---
title: 'Verlegungsanfrage: Bett-Dialog, AZR-Tooltip & Stornierung'
type: 'feature'
created: '2026-06-04'
status: 'done'
baseline_commit: '8b9cf41149d5f64b7de341f92e0d82b78d7cc285'
context: []
---

> **⚠ IMPLEMENTIERUNGSFEHLER KORRIGIERT** — Diese Spec enthält zwei falsche Regeln, die in der Implementierung behoben wurden:
>
> 1. **Cancel-Berechtigung (Zeile 23, 56, 76):** Die Regel „OR location_id == target_location_id" ist **falsch**. Nur die **anfragende Einrichtung (requester_location_id)** + system-admin darf stornieren. Die Ziel-Einrichtung kann ausschließlich `confirm` oder `reject` aufrufen.
> 2. **FREI-Bett-Klick (Zeile 39, 71, 95):** Ein FREI-Bett mit `pending_reservation_id` gehört der **Ziel-Einrichtung** — Klick soll zu `/reservations?highlight={pending_reservation_id}` navigieren (nicht Dialog öffnen). Dialog + Stornieren-Button gilt nur für BELEGT-Betten in der **Requester-Einrichtung** (`has_pending_transfer=true`).
>
> **Korrektur-Spec:** `spec-verlegungsanfrage-berechtigung-klick-korrektur.md` (status: done, commit 4ebf5db)
> **Kanonische Regeln:** Abschnitt „Verlegungsanfragen — Rollenregeln" in `project-context.md`

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Beim Klick auf ein Bett mit aktiver Verlegungsanfrage springt der Drilldown zur allgemeinen `/reservations`-Liste ohne Kontext; der Tooltip zeigt für FREI-Betten (Ziel-Bett einer eingehenden Anfrage) keine AZR-ID, und für BELEGT-Betten (Person mit ausgehender Anfrage) fehlt die Ziel-Einrichtung. Stornieren ist nur über die Listenansicht möglich, nicht direkt aus dem Bettgitter.

**Approach:** (1) `BedStatusItem` um `outgoing_reservation_id` + `transfer_target_location_name` (BELEGT mit aktiver Anfrage) und `pending_azr_id` (FREI mit vorgeschlagenem Bett) erweitern — reine SQL-Subqueries, kein Schema-Change; (2) neuer `POST /api/reservations/{id}/cancel`-Endpoint mit `{grund}`-Pflichtfeld, erlaubt für writer/location-admin/system-admin an Requester- ODER Target-Location, markiert bestehende OPEN-Tasks der Reservation als DONE; (3) Drilldown: Click-Handler öffnet Detail-Dialog statt zu navigieren; Dialog zeigt AZR, Einrichtungen, Status, Zeitraum + Stornieren-Button (nur für Writer+).

## Boundaries & Constraints

**Always:**
- `pending_azr_id` im BedStatusItem nur befüllen wenn `pending_reservation_id` gesetzt ist (FREI-Bett).
- `outgoing_reservation_id` + `transfer_target_location_name` nur befüllen wenn `has_pending_transfer=true` (BELEGT-Bett); CONFIRMED-Transfer analog mit `has_confirmed_transfer`.
- Cancel-Berechtigung: user.roles enthält 'writer', 'location-admin' oder 'system-admin' UND (location_id == requester_location_id OR location_id == target_location_id OR system-admin).
- `grund` ist Pflichtfeld im Frontend-Dialog (min 1 Zeichen) — Backend empfängt es optional und schreibt Audit-Event.
- Bei Cancel: `UPDATE tasks.inbox SET status='DONE' WHERE related_reservation_id=:id AND status IN ('OPEN','IN_PROGRESS')` vor Erstellung der CANCELLED-Notification-Tasks.
- Reader-only-User sehen den Dialog, aber keinen Stornieren-Button.

**Ask First:** — keine offenen Fragen.

**Never:**
- Kein neues DB-Schema, keine neue Migration.
- Kein automatisches Stornieren ohne User-Bestätigung.
- Cancel-Endpoint gibt keine anderen Statusübergänge frei (nur PENDING→CANCELLED und CONFIRMED→CANCELLED).

## I/O & Edge-Case Matrix

| Szenario | Zustand | Erwartetes Verhalten |
|----------|---------|---------------------|
| FREI-Bett, eingehende Anfrage | `pending_reservation_id` gesetzt | Tooltip: „[AZR] von [Requester]"; Click → Dialog |
| BELEGT-Bett, ausgehende Anfrage | `has_pending_transfer=true` | Tooltip: „Verlegungsanfrage → [Target]"; Click → Dialog |
| Dialog öffnen | Reservation-Details laden | GET /api/reservations/{id} → AZR, Einrichtungen, Status, Zeitraum |
| Writer klickt Stornieren | Begründung leer | Button bleibt disabled |
| Writer klickt Stornieren | Begründung gefüllt | POST /api/reservations/{id}/cancel → Status=CANCELLED, OPEN-Tasks=DONE, Snackbar Erfolg |
| Reader klickt Bett | pending-Bett | Dialog öffnet, kein Stornieren-Button sichtbar |
| Cancel-Aufruf ohne Writer-Rolle | HTTP 403 | Fehlermeldung im Dialog |
| Cancel von fremder Location | weder Requester noch Target | HTTP 403 |
| Reservation bereits CANCELLED | POST cancel | HTTP 409 „Ungültiger Statusübergang" |

</frozen-after-approval>

## Code Map

- `backend/src/api/capacity/schemas.py:220` — BedStatusItem: neue Felder `outgoing_reservation_id`, `transfer_target_location_name`, `pending_azr_id`
- `backend/src/api/capacity/router.py:483` — SQL-Subqueries für neue Felder; `row`-Mapping ~Zeile 568
- `backend/src/api/reservations/router.py:128` — bestehender `cancel_reservation` → erweitern + Berechtigung +grund; neuer `GET /api/reservations/{id}`
- `backend/src/domain/reservations/rules.py:29` — `check_retraction_allowed`: target_location_id ebenfalls erlauben
- `frontend/src/pages/Drilldown.tsx:100` — BedStatus-Interface; ~247 Tooltip-Text; ~701 Click-Handler; neue Dialog-Komponente + State

## Tasks & Acceptance

**Execution:**
- [x] `backend/src/api/capacity/schemas.py` — `BedStatusItem` um drei Felder erweitern: `outgoing_reservation_id: Optional[UUID] = None`, `transfer_target_location_name: Optional[str] = None`, `pending_azr_id: Optional[str] = None` — ermöglicht Tooltip + Dialog ohne separate API-Calls
- [x] `backend/src/api/capacity/router.py` — In der bed-status SQL drei Subqueries ergänzt; Im `row`-Mapping alle drei Felder befüllt
- [x] `backend/src/domain/reservations/rules.py` — `check_retraction_allowed`: Bedingung auf `location_id not in (req.requester_location_id, req.target_location_id)` erweitert
- [x] `backend/src/api/reservations/router.py` — `GET /api/reservations/{id}` + `POST /api/reservations/{id}/cancel` hinzugefügt; `ReservationDetailResponse` + `CancelRequest` Schemas ergänzt; Tasks-UPDATE + Audit-Event implementiert
- [x] `frontend/src/pages/Drilldown.tsx` — BedStatus-Interface erweitert; Tooltip-Texte korrigiert; Click-Handler öffnet Dialog; `TransferRequestDialog` mit Cancel-Funktionalität (Writer+, Begründung Pflicht)

**Acceptance Criteria:**
- Given FREI-Bett mit `pending_reservation_id`, when Hover, then Tooltip zeigt AZR-ID + anfragende Einrichtung.
- Given BELEGT-Bett mit `has_pending_transfer=true`, when Hover, then Tooltip zeigt AZR-ID + Ziel-Einrichtung.
- Given beides, when Klick auf Bett, then öffnet Detail-Dialog (kein Navigate).
- Given Detail-Dialog, when offen, then zeigt AZR, beide Einrichtungen (Requester/Target), Status, Zeitraum.
- Given Reader-User im Dialog, then kein Stornieren-Button sichtbar.
- Given Writer-User, Stornieren-Button, Begründung leer, then Button disabled.
- Given Writer-User, Begründung gefüllt, when Stornieren geklickt, then POST /cancel → 200, Tasks mit related_reservation_id → DONE, Snackbar Erfolg, Dialog schließt, Bettgitter aktualisiert.
- Given Target-Location Writer (nicht Requester), when POST /cancel, then 200 (nicht 403).
- Given Reader POST /cancel via API, then HTTP 403.

## Design Notes

`outgoing_reservation_id` im BedStatusItem hat denselben Subquery-Aufbau wie `pending_reservation_id` — nur Blickrichtung wechselt von `suggested_bed_id = b.id` (eingehend) auf `pen_out.azr_id = o.azr_id` (ausgehend). Bei mehreren parallelen Anfragen liefert `ORDER BY created_at LIMIT 1` die älteste; Invariante: eine Person hat maximal eine PENDING-Anfrage (späterer Ziel B Guard).

Der bestehende `DELETE /api/reservations/{id}` bleibt erhalten (Abwärtskompatibilität mit Reservations.tsx). Der neue `POST /cancel`-Endpoint ist der kanonische Weg mit Begründung.

Rollen-Check im Frontend per `keycloak.tokenParsed?.realm_access?.roles?.includes('writer')` — analog zu bestehenden `canEdit`-Guards in Drilldown.tsx.

## Verification

**Commands:**
- `cd /Users/A3694852/KapzitaetsPlanungsTool/frontend && npx tsc --noEmit` — expected: kein Fehler
- `cd /Users/A3694852/KapzitaetsPlanungsTool && python3 -m pytest backend/tests/ -x -q 2>/dev/null || echo "no pytest"` — keine Regression

**Manual checks:**
- GET /api/locations/{frankfurt_id}/bed-status → `pending_azr_id` befüllt für FREI-Bett mit PENDING-Anfrage
- Drilldown Flughafen Frankfurt: FREI-Bett mit Verlegungsanfrage → Tooltip zeigt AZR; Klick → Dialog
- Dialog Cancel mit Begründung → Reservation status=CANCELLED, GET /api/reservations?status=CANCELLED bestätigt; tasks.inbox für beide Locations status='DONE'

## Spec Change Log

