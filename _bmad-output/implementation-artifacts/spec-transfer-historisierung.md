---
title: 'Transfer-Historisierung — Quell-Belegung bei Check-in schließen statt löschen'
type: 'feature'
created: '2026-06-07'
status: 'done'
baseline_commit: 'ab87386'
context: ['_bmad-output/project-context.md', 'spec-verlegungsanfrage-konsistenzregeln.md']
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Beim Transfer-Check-in (`POST /api/reservations/{id}/transfer`, CONFIRMED → TRANSFERRED) wurde die Quell-Belegung der Person mittels `DELETE` aus der Datenbank entfernt. Damit ist die Unterbringungshistorie der Person lückenhaft: Es gibt Zeiträume in denen die Person keinen Platz hatte, obwohl sie physisch noch in der Quelleinrichtung war. Das verletzt die DSGVO-Nachweispflicht (jede Person muss zu jedem Zeitpunkt einem Platz zuordenbar sein) sowie die Aufbewahrungspflicht für Unterbringungsdaten.

**Approach:** Im `transfer()` in `reservation_repo.py`: statt `session.delete(source_occupant)` wird `source_occupant.belegung_ende = date.today()` gesetzt. Die alte Belegung bleibt erhalten und endet am Tag des Check-ins. Die neue Belegung in der Zieleinrichtung beginnt mit `belegung_start` der Reservierung.

## Boundaries & Constraints

**Always:**
- B-01: Quell-Belegung wird niemals gelöscht — nur `belegung_ende = date.today()` gesetzt.
- B-02: Die neue Belegung in der Zieleinrichtung (`belegung_start` = Reservierungs-Start) kann die alte Belegung zeitlich überlappen — das ist bewusst akzeptiert als Übergangszeitraum (Person ist physisch in der Zieleinrichtung aber noch formal aus der Quelle ausgecheckt).
- B-03: Wenn keine Quell-Belegung gefunden wird (Person wurde nie formal eingebucht oder bereits anderswo ausgebucht), wird dies ignoriert — kein Fehler, nur die neue Belegung wird angelegt.
- B-04: Der Suchalgorithmus für die Quell-Belegung: `azr_id = reservation.azr_id` + Zeitraum-Überschneidung mit Reservierungszeitraum + `bed_id != confirmed_bed_id` (damit nicht die neue Belegung selbst gefunden wird).

**Never:**
- Keine physische Löschung von Belegungen beim Transfer.
- Kein separater API-Endpoint für die Historisierung — läuft inline im `transfer()`-Call.

## Fachliche Begründung (Ein-Platz-Regel)

Jede Person muss gemäß BAMF-Anforderungen zu jedem Zeitpunkt einem Unterbringungsplatz zugeordnet sein. Die Belegungshistorie muss lückenlos und auditierbar bleiben. Die bisherige DELETE-Variante erzeugte Lücken zwischen dem Check-in in der Zieleinrichtung und dem Ende der alten Belegung. Mit `belegung_ende = today` wird die alte Belegung nahtlos abgeschlossen.

## I/O

**Input:** `POST /api/reservations/{reservation_id}/transfer` mit `X-Location-Id: {target_location_id}`

**Ablauf:**
1. Reservierung laden + FOR UPDATE sperren
2. Statusübergang CONFIRMED → TRANSFERRED prüfen
3. Quell-Belegung suchen (Abfrage: `azr_id = res.azr_id`, Zeitraum-Überschneidung, `bed_id != confirmed_bed_id`)
4. Falls gefunden: `source_occupant.belegung_ende = date.today()`
5. Neue Belegung anlegen (`OccupantModel` mit `belegung_start = res.belegung_start`, `belegung_ende = res.belegung_ende`)
6. Status auf `TRANSFERRED` setzen
7. Tasks + Audit-Einträge erzeugen

**Output:** `ReservationResponse` mit `status = "TRANSFERRED"`

</frozen-after-approval>

## Code Map

- `backend/src/adapters/db/reservation_repo.py:transfer()` — Zeile mit `source_occupant.belegung_ende = date.today()` (vorher `session.delete(source_occupant)`)
- `backend/src/adapters/db/reservation_repo.py` — `from datetime import date, datetime, timezone` (date für `date.today()` hinzugefügt)

## Tasks & Acceptance

**Execution:**
- [x] `reservation_repo.py` — `transfer()`: `session.delete(source_occupant)` → `source_occupant.belegung_ende = date.today()`
- [x] `reservation_repo.py` — Import: `date` zu `from datetime import date, datetime, timezone` hinzugefügt

**Acceptance Criteria (durch `transfer_occupancy_history.feature` abgedeckt):**
- Nach `POST .../transfer` existiert die Quell-Belegung noch in der DB (kein DELETE).
- Die Quell-Belegung hat `belegung_ende = date.today()`.
- Die Zieleinrichtung hat eine aktive Belegung (`belegung_ende > today`).
- Die Belegungshistorie enthält keine Lücke (Ende der alten Belegung ≥ Start der neuen).
- Die Reservierung hat Status `TRANSFERRED`.

## BDD-Tests

`tests/features/transfer_occupancy_history.feature` (4 Szenarien):
- Quell-Belegung bleibt erhalten + `belegung_ende = heute`
- Neue Belegung in Zieleinrichtung vorhanden
- Keine Zeitlücke in der Belegungshistorie
- Reservierungsstatus = `TRANSFERRED`
