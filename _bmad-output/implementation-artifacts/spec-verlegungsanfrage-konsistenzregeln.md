---
title: 'Verlegungsanfrage: Konsistenzregeln — Ausbuchen-Block, Ein-Platz-Regel, Verlegen-Grund'
type: 'feature'
created: '2026-06-04'
status: 'done'
baseline_commit: 'ee8684011b6c87248878c91e76c31531d0ffe6d8'
context: ['_bmad-output/project-context.md']
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Eine Person mit aktiver Verlegungsanfrage (PENDING/CONFIRMED) kann aktuell ausgebucht oder an einer anderen Einrichtung neu eingebucht werden — das unterbricht den Verlegungsworkflow und erzeugt inkonsistente Daten. Zusätzlich fehlt beim internen Verlegen ein allgemeines Pflicht-Begründungsfeld; der Ausbuchen-Grund wird zwar an das Backend gesendet, aber nicht im Audit-Event persistiert.

**Approach:** (1) `end_occupancy` (DELETE) prüft via DB-Lookup ob die AZR-ID eine PENDING/CONFIRMED Reservation hat → HTTP 409. (2) `create_occupancy` (POST) prüft: Ein-Platz-Regel (AZR-ID aktiv in anderer Einrichtung) → 409; aktive Reservation + Cross-Location → 409; internem Verlegen (selbe `location_id`) wird beides ausdrücklich erlaubt. (3) `end_occupancy` schreibt `grund` ins `OCCUPANCY_DELETED`-Audit-Payload. (4) Verlegen-Dialog in Drilldown erhält allgemeines Pflicht-Begründungsfeld. (5) Neue BDD-Szenarien für alle Guards.

## Boundaries & Constraints

**Always:**
- Internes Verlegen (POST neues Bett + DELETE altes Bett, gleiche `location_id`) darf weder durch Ein-Platz-Regel noch durch Reservation-Guard blockiert werden.
- `grund` beim Ausbuchen bleibt Query-Parameter (kein Request-Body für DELETE, FastAPI-Konvention).
- Schichtentrennung: neue Domain-Rule-Funktionen nur in `domain/reservations/rules.py` — kein `fastapi`-Import dort.
- Bestehende Klick-Navigation (FREI+pending → navigate, BELEGT+transfer → Dialog) aus `project-context.md` bleibt unverändert.
- Nur `requester_location_id` + `system-admin` darf Reservierungen stornieren (Invariante aus `project-context.md`).
- Kein Alembic-Schema-Change erforderlich.

**Ask First:** — keine offenen Fragen.

**Never:**
- Ein-Platz-Regel blockiert internen Transfer (selbe Location).
- Ziel-Einrichtung kann Stornieren (weder API noch UI).
- Ausbuchen-Grund-Pflicht im Backend erzwingen (bleibt optional — nur Audit-Persistierung).

## I/O & Edge-Case Matrix

| Szenario | Zustand | Erwartetes Verhalten |
|----------|---------|---------------------|
| Ausbuchen bei PENDING Reservation | AZR-ID hat PENDING Reservation | HTTP 409 "Erst Verlegungsanfrage stornieren" |
| Ausbuchen bei CONFIRMED Reservation | AZR-ID hat CONFIRMED Reservation | HTTP 409 |
| Ausbuchen ohne aktive Reservation | keine PENDING/CONFIRMED Reservation | HTTP 200, Audit-Event mit `grund` |
| Cross-Location POST, Person hat PENDING | azr_id hat PENDING, Ziel-Location ≠ Requester-Location | HTTP 409 |
| Internes Verlegen, Person hat PENDING | azr_id hat PENDING, Ziel-Location = aktuelle Location | HTTP 201 (erlaubt) |
| Ein-Platz-Verletzung | azr_id aktiv in anderer Location, kein interner Transfer | HTTP 409 "Person bereits in anderer Einrichtung belegt" |
| Internes Verlegen (Ein-Platz) | azr_id aktiv in selber Location | HTTP 201 (erlaubt) |
| Verlegen-Dialog, Grund leer | Begründungsfeld leer | Verlegen-Button disabled |

</frozen-after-approval>

## Code Map

- `backend/src/domain/reservations/rules.py:29` — neue Exceptions `ActiveReservationBlocksError`, `EinPlatzRuleError`; neue Funktionen `check_no_active_reservation_for_ausbuchen(azr_id, active_res_id)` und `check_no_active_occupancy_elsewhere(azr_id, active_occ_location_id, target_location_id)`
- `backend/src/api/capacity/router.py:1189` — `end_occupancy`: DB-Query auf aktive Reservation + Domain-Rule-Aufruf; `grund` in OCCUPANCY_DELETED Audit-Payload schreiben
- `backend/src/api/capacity/router.py:1056` — `create_occupancy`: Ein-Platz-Query + Reservation-Guard (beide vor bestehenden Checks); `target_location_id` aus DB-Query auf Bett (bereits vorhanden, Z.1083)
- `frontend/src/pages/Drilldown.tsx:866` — `handleVerlegen`: neues State `verlegenGrund: string`; TextField "Begründung *" im Verlegen-Dialog; Button disabled wenn leer; `verlegenGrund` an POST als `Body-Feld geschlecht_mismatch_grund` oder separates Feld übergeben — **nur wenn** kein separates `grund`-Feld in `OccupancyCreate` — sonst neues `verlegung_grund`-Feld
- `backend/src/api/capacity/schemas.py:95` — `OccupancyCreate`: optionales Feld `verlegung_grund: Optional[str] = None` für allgemeines Verlegen-Begründungsfeld; wird in OCCUPANCY_CREATED Audit-Payload aufgenommen
- `tests/features/occupancy_guards.feature` — neue BDD-Feature-Datei mit 6 Szenarien

## Tasks & Acceptance

**Execution:**
- [x] `backend/src/domain/reservations/rules.py` — neue Exception-Klassen `ActiveReservationBlocksError` (für Ausbuchen + externes Verlegen) und `EinPlatzRuleError`; neue Funktion `check_no_active_reservation(active_res_id: Optional[uuid.UUID]) -> None` raises wenn nicht None; neue Funktion `check_single_occupancy(existing_location_id: Optional[uuid.UUID], target_location_id: uuid.UUID) -> None` raises `EinPlatzRuleError` wenn existing_location_id gesetzt und ≠ target_location_id
- [x] `backend/src/api/capacity/router.py` (`end_occupancy`, ~Z.1189) — nach `occ_repo.get_by_id()`: SQL-SELECT auf `reservations.requests WHERE azr_id=:azr AND status IN ('PENDING','CONFIRMED') LIMIT 1`; Aufruf `check_no_active_reservation(result)`; HTTP-409-Mapping via `except ActiveReservationBlocksError`; in `OCCUPANCY_DELETED`-Audit-Payload `grund` hinzufügen; auch `occ_repo.delete()` in `capacity_repo.py` um `grund`-Parameter erweitert
- [x] `backend/src/api/capacity/router.py` (`create_occupancy`, ~Z.1056) — nach Laden des Ziel-Betts (`target_bed`): (a) SQL-SELECT auf `persons.occupants JOIN capacity.beds WHERE azr_id=:azr AND belegung_ende>=CURRENT_DATE AND beds.location_id!=:loc LIMIT 1`; Aufruf `check_single_occupancy(existing_loc_id, target_location_id)`; (b) SQL-SELECT auf `reservations.requests WHERE azr_id=:azr AND status IN ('PENDING','CONFIRMED') LIMIT 1`; wenn Treffer UND `req.requester_location_id != target_location_id`: `check_no_active_reservation(res_id)`; beide `except`-Handler → HTTP 409
- [x] `backend/src/api/capacity/schemas.py` — `OccupancyCreate`: optionales Feld `verlegung_grund: Optional[str] = None` hinzugefügt
- [x] `frontend/src/pages/Drilldown.tsx` — neuer State `verlegenGrund`; im Verlegen-Dialog TextField "Begründung *"; Verlegen-Bestätigen-Button: `disabled={!verlegenGrund.trim()}`; `verlegenGrund` in POST-Body als `verlegung_grund`; Reset nach Verlegen + onClose + Abbrechen
- [x] `tests/features/occupancy_guards.feature` — neue Feature-Datei mit 7 Szenarien; Step-Definitionen in `tests/steps/occupancy_guard_steps.py`; 0 undefined steps (dry-run bestätigt)

**Acceptance Criteria:**
- Given AZR-ID hat PENDING Reservation, when DELETE /api/beds/{id}/occupancy/{occ_id}, then HTTP 409 mit Fehlermeldung "Verlegungsanfrage".
- Given AZR-ID hat CONFIRMED Reservation, when DELETE /api/beds/{id}/occupancy/{occ_id}, then HTTP 409.
- Given AZR-ID ohne aktive Reservation, when DELETE /api/beds/{id}/occupancy/{occ_id} mit `?grund=...`, then HTTP 200 und Audit-Event `OCCUPANCY_DELETED` enthält `grund`-Feld.
- Given AZR-ID aktiv in Einrichtung A, when POST /api/beds/{bed_in_B}/occupancy, then HTTP 409 (Ein-Platz).
- Given AZR-ID aktiv in Einrichtung A (selbe Location wie Ziel-Bett), when POST occupancy, then HTTP 201.
- Given AZR-ID hat PENDING Reservation (A→B), when POST /api/beds/{bed_in_C}/occupancy (C ≠ A), then HTTP 409.
- Given AZR-ID hat PENDING Reservation, when POST /api/beds/{bed_in_A}/occupancy (A = requester), then HTTP 201 (internes Verlegen erlaubt).
- Given Verlegen-Dialog offen, when Begründungsfeld leer, then Verlegen-Button ist disabled.
- Given Verlegen-Dialog, Begründung gefüllt, when Verlegen bestätigen, then POST-Body enthält `verlegung_grund`.

## Spec Change Log

## Design Notes

In `create_occupancy` (POST) ist `target_location_id` bereits in Z.1083 aus der DB geladen (`bed.location_id`). Die Ein-Platz-Query nutzt `beds.location_id != :target_loc` als Filter — liefert nur Treffer bei wirklich fremden Einrichtungen; internes Verlegen (bestehende Belegung selber Location) liefert 0 Treffer → kein Guard ausgelöst.

Reihenfolge der Guards in `create_occupancy`: (1) Ein-Platz-Check → (2) Reservation-Guard → (3) bestehende Checks (`check_bed_available`, `check_notbett_duration`, etc.). Diese Reihenfolge gibt dem SB die sprechendste Fehlermeldung zuerst.

Der `verlegung_grund` im OccupancyCreate-Schema ist `Optional` — das Backend erzwingt keine Pflicht (ermöglicht programmatische Nutzung ohne Grund). Die Pflicht liegt ausschließlich im Frontend-Dialog-Guard.

## Verification

**Commands:**
- `cd /Users/A3694852/KapzitaetsPlanungsTool/frontend && npx tsc --noEmit` — expected: 0 Fehler
- `cd /Users/A3694852/KapzitaetsPlanungsTool && python3 -m pytest backend/tests/ -x -q 2>/dev/null || echo "no pytest"` — expected: alle grün
- `cd /Users/A3694852/KapzitaetsPlanungsTool && python3 -m behave tests/ --dry-run --no-capture 2>&1 | grep "0 undefined"` — expected: 0 undefined steps

## Suggested Review Order

**Domain-Regeln (Kern der Änderung)**

- Zwei neue Exceptions + zwei reine Prüffunktionen ohne I/O; Eintrittspunkt zum Verstehen der Logik.
  [`rules.py:14`](../../backend/src/domain/reservations/rules.py#L14)

**Ausbuchen-Guard (DELETE /occupancy)**

- Guard-Block: SQL-Lookup auf aktive Reservation, dann Domain-Rule, dann Delete — Reihenfolge kritisch.
  [`router.py:1285`](../../backend/src/api/capacity/router.py#L1285)

- `occ_repo.delete()` erhält jetzt `grund`-Parameter — Audit-Payload um optionales Feld erweitert.
  [`capacity_repo.py:357`](../../backend/src/adapters/db/capacity_repo.py#L357)

**Einbuchen-Guards (POST /occupancy)**

- Ein-Platz-Query: `location_id != :loc` filtert cross-location Belegungen; internes Verlegen hat 0 Treffer.
  [`router.py:1106`](../../backend/src/api/capacity/router.py#L1106)

- Reservation-Guard: `requester_location_id != bed_location_id` erlaubt internes Verlegen, blockiert externes.
  [`router.py:1128`](../../backend/src/api/capacity/router.py#L1128)

- `verlegung_grund` Audit-Event nach dem Geschlecht-Mismatch-Block; beide Events optional.
  [`router.py:1167`](../../backend/src/api/capacity/router.py#L1167)

**Schema**

- Optionales `verlegung_grund`-Feld in `OccupancyCreate` — Backend erzwingt keine Pflicht.
  [`schemas.py:105`](../../backend/src/api/capacity/schemas.py#L105)

**Frontend (Verlegen-Dialog)**

- Neuer State + Pflicht-TextField im normalen Verlegen-Pfad; Button disabled wenn leer.
  [`Drilldown.tsx:411`](../../frontend/src/pages/Drilldown.tsx#L411)

- `verlegung_grund` im POST-Body; Reset in allen Close/Cancel-Pfaden.
  [`Drilldown.tsx:893`](../../frontend/src/pages/Drilldown.tsx#L893)

**Tests**

- 7 BDD-Szenarien: Ausbuchen-Block (PENDING/CONFIRMED/frei), Ein-Platz, internes Verlegen, Reservation-Guard.
  [`occupancy_guards.feature:1`](../../tests/features/occupancy_guards.feature#L1)

- Step-Definitionen mit Setup-Helpers für Location/Room/Bed/Occupancy/Reservation.
  [`occupancy_guard_steps.py:1`](../../tests/steps/occupancy_guard_steps.py#L1)
