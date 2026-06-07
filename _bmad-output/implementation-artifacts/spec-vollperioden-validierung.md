---
title: 'Vollperioden-Validierung — Kaskade Einrichtung → Raum → Bett + period_available Flag'
type: 'feature'
created: '2026-06-07'
status: 'done'
baseline_commit: 'ab87386'
supersedes: 'spec-ziel9c-validity-enforcement.md'
context: ['_bmad-output/project-context.md']
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** `spec-ziel9c-validity-enforcement.md` deckte nur `valid_from`/`valid_until` auf Einrichtungsebene und nur gegen `belegung_start` ab. In Wirklichkeit muss das gesamte Belegungsintervall `[belegung_start, belegung_ende)` auf allen drei Ebenen (Einrichtung → Raum → Bett) gültig sein. Zudem muss die Bettsuche Vorschläge ausfiltern, deren Gültigkeitsfenster kürzer ist als der angefragte Zeitraum — egal ob das Ablaufdatum auf Bett-, Raum- oder Einrichtungsebene liegt.

**Approach:** (1) Backend-Validierung in `create_occupancy` und `create_reservation` auf vollständige Periodenkaskade erweitert: Einrichtung `is_active` + `valid_from`/`valid_until`, Raum `valid_from`/`valid_until`, Bett `valid_from`/`deaktiviert_ab`. Jede Stufe prüft gegen `belegung_ende`, nicht nur `belegung_start`. (2) SQL-Queries in `suggestions/router.py` erweitert, sodass `deaktiviert_ab >= period_end` und `valid_until >= period_end` für alle Ebenen gelten. (3) Neues Feld `period_available: Optional[bool]` in `BedStatusItem` (server-seitig berechnet) — ermöglicht dem Frontend Betten mit zu kurzem Gültigkeitsfenster aus Auswahllisten auszublenden.

## Boundaries & Constraints

**Always:**
- B-01: Vollständige Periode `[start, end)` prüfen — `belegung_ende` muss im Gültigkeitsfenster liegen, nicht nur `belegung_start`.
- B-02: Kaskade zwingend in dieser Reihenfolge: Einrichtung → Raum → Bett (erster Fehler bricht ab mit HTTP 409).
- B-03: `valid_from` / `valid_until` / `deaktiviert_ab` sind alle optional (NULL = unbefristet) — kein Fehler wenn alle NULL.
- B-04: `period_available` in `BedStatusItem` ist `null` wenn `date_to` im Query-Parameter fehlt; `true`/`false` wenn angegeben.
- B-05: Bei Reservierungen wird die **Ziel-Einrichtung** (`target_location_id`) geprüft, nicht die anfragende.
- B-06: `l.is_active = true` im Basis-SQL der Bettsuche — deaktivierte Einrichtungen liefern keine Vorschläge.
- B-07: Fehlermeldungen (Belegung): `"Einrichtung ist deaktiviert"`, `"Belegungsende überschreitet die Verfügbarkeit der Einrichtung (bis {date})"`, `"Belegungsende überschreitet die Verfügbarkeit des Raums (bis {date})"`, `"Bett ist erst ab {date} verfügbar"`, `"Belegungsende überschreitet die Verfügbarkeit des Betts (bis {date})"`.
- B-08: Fehlermeldungen (Reservierung): `"Ziel-Einrichtung ist deaktiviert"`, `"Belegungsende überschreitet die Verfügbarkeit der Ziel-Einrichtung (bis {date})"`.

**Never:**
- Keine Änderung der `valid_from`/`valid_until`-Edit-Flows in Drilldown.tsx `saveEdit`.
- Kein neuer Endpoint für Validierungsabfragen — Validierung läuft inline in den bestehenden POST-Handlern.

## Abweichung von spec-ziel9c

`spec-ziel9c` hatte als Constraint: `"B-01: Prüfung auf belegung_start (nicht belegung_ende)"`. Diese Einschränkung wurde bewusst **nicht** eingehalten — die Vollperioden-Prüfung war fachlich korrekt und wurde implementiert. `spec-ziel9c` bleibt als historischer Kontext erhalten, gilt aber als durch diese Spec vollständig ersetzt.

## I/O & Edge-Case Matrix

| Szenario | Ebene | Prüfung | HTTP |
|----------|-------|---------|------|
| Einrichtung `is_active = false` | Location | immer | 409 |
| `belegung_start < location.valid_from` | Location | wenn nicht NULL | 409 |
| `belegung_ende > location.valid_until` | Location | wenn nicht NULL | 409 |
| `belegung_start < room.valid_from` | Room | wenn nicht NULL | 409 |
| `belegung_ende > room.valid_until` | Room | wenn nicht NULL | 409 |
| `belegung_start < bed.valid_from` | Bed | wenn nicht NULL | 409 |
| `belegung_ende > bed.deaktiviert_ab` | Bed | wenn nicht NULL | 409 |
| Alle NULL | Alle | — | kein Fehler |
| Bettsuche: `deaktiviert_ab < period_end` | Bed | SQL-Filter | Bett nicht in Vorschlägen |
| Bettsuche: `valid_until < period_end` | Room/Location | SQL-Filter | Bett nicht in Vorschlägen |
| `bed-status` ohne `date_to`-Parameter | — | `period_available = null` | 200 |
| `bed-status` mit `date_to` | alle | cascade check | `period_available true/false` |

</frozen-after-approval>

## Code Map

- `backend/src/api/capacity/router.py:create_occupancy` — Vollständige Kaskaden-Validierung; erweiterte JOIN-Query für `l.is_active`, `r.valid_from`, `r.valid_until`, `l.valid_from`, `l.valid_until`
- `backend/src/api/capacity/router.py:get_bed_status` — `period_available`-Berechnungs-SELECT (JOIN auf locations, rooms; CASCADE-Check per SQL)
- `backend/src/api/capacity/schemas.py:BedStatusItem` — `period_available: Optional[bool] = None`
- `backend/src/api/reservations/router.py:create_reservation` — Zieleinrichtungs-Validierung: `is_active`, `valid_from`, `valid_until` gegen `belegung_start`/`belegung_ende`
- `backend/src/api/suggestions/router.py:_BED_SELECT` — SQL WHERE-Klausel mit `l.is_active = true`, vollständige Periodenprüfung auf allen drei Ebenen
- `frontend/src/pages/Drilldown.tsx:bedIsActive` — prüft `period_available === false` wenn `refDateTo` angegeben
- `frontend/src/pages/Drilldown.tsx:BedGrid` — übergibt `refDateTo={dateTo}` an `bedIsActive`
- `frontend/src/pages/Reservations.tsx` — Bett-Filter `.filter(b => b.period_available !== false)`
- `frontend/src/components/ReservationCreateDialog.tsx` — Bett-Filter `.filter(b => b.period_available !== false)`

## Tasks & Acceptance

**Execution:**
- [x] `backend/src/api/capacity/router.py` — `create_occupancy`: JOIN auf `capacity.locations` + `capacity.rooms`; Kaskaden-Checks für alle 6 Validierungsfälle
- [x] `backend/src/api/capacity/router.py` — `get_bed_status`: `period_available`-Column berechnet via SQL-CASE-Ausdruck; `date_to`-Query-Parameter übergeben
- [x] `backend/src/api/capacity/schemas.py` — `BedStatusItem.period_available: Optional[bool] = None`
- [x] `backend/src/api/reservations/router.py` — `create_reservation`: target-location-Prüfung auf `is_active`, `valid_from`, `valid_until`, `belegung_ende`
- [x] `backend/src/api/suggestions/router.py` — `_BED_SELECT`/`_BED_SELECT_NO_GENDER`: `l.is_active = true` + vollständige Periodenprüfung auf allen Ebenen
- [x] `frontend/src/pages/Drilldown.tsx` — `bedIsActive()`: `period_available === false` wenn `refDateTo` angegeben; `BedGrid` erhält `refDateTo`
- [x] `frontend/src/pages/Reservations.tsx` — Bett-Dropdown-Filter für `period_available !== false`
- [x] `frontend/src/components/ReservationCreateDialog.tsx` — Bett-Filter + `inputProps.min` auf Datumsfeldern

**Acceptance Criteria (alle durch `validity_period_checks.feature` abgedeckt):**
- Bettsuche gibt kein Bett zurück dessen `deaktiviert_ab` vor `period_end` liegt.
- Bettsuche gibt kein Bett zurück dessen Raum-`valid_until` vor `period_end` liegt.
- Bettsuche gibt kein Bett zurück wenn Einrichtung `is_active = false` (→ 403 bei scoped Suche).
- `create_occupancy` liefert HTTP 409 bei jedem der 6 Kaskaden-Verstöße.
- `create_reservation` liefert HTTP 409 wenn Zieleinrichtung deaktiviert oder `valid_until` überschritten.
- `GET /api/locations/{id}/bed-status?date_from=…&date_to=…` gibt `period_available: false` für Betten mit zu kurzem Fenster.

## BDD-Tests

`tests/features/validity_period_checks.feature` (14 Szenarien) — alle Ebenen und alle Operationen abgedeckt.
