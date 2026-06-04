---
title: 'Stammdaten Bugfixes: Doppelte Einrichtungen + GEO-Code-Fehler'
type: 'bugfix'
created: '2026-06-04'
status: 'done'
baseline_commit: '3505371'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** (1) Im "Neue Einrichtung"-Dialog (Dashboard) wird der Formularinhalt beim Schließen ohne Speichern nicht zurückgesetzt — der nächste Dialog-Öffnen startet mit den alten Werten, wodurch unbeabsichtigt Einrichtungen mit dem alten Namen angelegt werden können. Das erklärt die doppelten Datensätze für Frankfurt und München. (2) Ein ungültiger GEO-Code (Lat/Lon-Eingabe die kein gültiges Dezimalformat hat, z.B. "abc") wird als `NaN` ans Backend gesendet, was einen unkontrollierten Fehler auslöst; zusätzlich würde `NaN` in `MapView.getCoords()` Leaflet zum Absturz bringen.

**Approach:** (1) `onClose` des Create-Dialogs und "Abbrechen"-Button setzen alle Formularfelder zurück. Doppelte Einrichtungen im System sind Datenproblem — kein Schema-Change, aber Backend-Deduplizierungs-Endpoint als "Ask First". (2) Frontend-Validierung in `saveEdit()` vor dem PATCH-Aufruf: ungültige Floats → Inline-Fehlermeldung, kein API-Aufruf. Backend-Schema: Pydantic-Validator für lat/lon-Ranges. `getCoords()` in MapView: NaN-sicherer Guard.

## Boundaries & Constraints

**Always:**
- Formularfelder `newName`, `newAdresse`, `newKontingent`, `newNotbett` werden beim Schließen des Create-Dialogs immer auf Defaultwerte (`''`, `''`, `'10'`, `'0'`) zurückgesetzt — egal ob via `onClose`, "Abbrechen" oder nach erfolgreicher Speicherung.
- GEO-Validierung: `lat` muss in [-90, 90], `lon` in [-180, 180]; beide müssen endliche Zahlen sein (`isFinite`). Leere Felder → kein Senden (bleibt `null` in DB).
- Backend-Validator: `math.isfinite(v)` + Range-Check in Pydantic `field_validator` für `lat` und `lon` in `LocationUpdateRequest`.
- Bestehende Einrichtungen, Räume, Betten und Belegungen werden nicht angefasst.

**Ask First:**
- Sollen die doppelten DB-Einträge (Frankfurt/München) bereinigt werden? → Falls ja: manuelles SQL oder Seed-Reset empfehlen, kein automatisches Merge-Script.

**Never:**
- Unique-Constraint auf `capacity.locations.name` (bestehende Demo-Daten könnten Kollisionen haben, Schema-Change nicht erforderlich für den Fix).
- Leaflet/MapView-Logik ändern außer dem NaN-Guard in `getCoords()`.

## I/O & Edge-Case Matrix

| Szenario | Input | Erwartetes Verhalten | Fehlerbehandlung |
|----------|-------|---------------------|-----------------|
| Dialog ohne Speichern schließen | Felder ausgefüllt, dann Escape/Backdrop/Abbrechen | Alle Felder auf Default zurückgesetzt | — |
| Dialog nach Speichern nochmals öffnen | Vorherige Felder leer | Leeres Formular | — |
| GEO: gültiger Wert | `lat = "48.137"` | `parseFloat` → `48.137`, PATCH-Body enthält `lat: 48.137` | — |
| GEO: nicht-numerisch | `lat = "abc"` | Inline-Error unter Feld, kein API-Aufruf | "Ungültiger Wert" |
| GEO: außerhalb Bereich | `lat = "91"` | Inline-Error, kein API-Aufruf | "Breitengrad muss zwischen -90 und 90 liegen" |
| GEO: leer gelassen | `lat = ""` | Feld wird nicht im PATCH-Body gesendet | — |
| Backend: NaN im Body | `lat: NaN` (JS-Bug-Bypass) | HTTP 422 mit sprechendem Detail | Pydantic ValidationError |
| MapView: loc.lat ist NaN | Einrichtung hat `lat: NaN` in DB | Fallback-Koordinaten werden genutzt | kein Crash |

</frozen-after-approval>

## Code Map

- `frontend/src/pages/Dashboard.tsx:287` — "Neue Einrichtung"-Dialog: `onClose` und "Abbrechen"-Button ohne State-Reset (Bug-Quelle)
- `frontend/src/pages/Dashboard.tsx:135` — `handleCreateLocation`: State-Reset nach Speicherung bereits korrekt
- `frontend/src/pages/Drilldown.tsx:556` — `saveEdit()`: `parseFloat(editLat/Lon)` ohne NaN/Range-Prüfung
- `frontend/src/pages/Drilldown.tsx:1587` — GEO-Eingabefelder (Breitengrad / Längengrad TextFields)
- `frontend/src/components/MapView.tsx:42` — `getCoords()`: `loc.lat != null` fängt kein NaN ab
- `backend/src/api/capacity/schemas.py:158` — `LocationUpdateRequest`: `lat`/`lon` ohne Validierung

## Tasks & Acceptance

**Execution:**
- [x] `frontend/src/pages/Dashboard.tsx` — `onClose` des Create-Dialogs (Z.287): State-Reset für alle vier Felder + `setNewLocSaving(false)` ergänzen; gleiches Reset in "Abbrechen"-Button (Z.309)
- [x] `frontend/src/pages/Drilldown.tsx` — `saveEdit()` (Z.556): vor dem PATCH-Aufruf `editLat`/`editLon` validieren — `isFinite(parseFloat(v))` + Range-Check; ungültig → `setGeoError('...')` setzen, kein API-Aufruf; State `geoError: string` hinzufügen
- [x] `frontend/src/pages/Drilldown.tsx` — GEO-Felder (Z.~1587): `helperText` + `error` auf den Lat/Lon-TextFields; `geoError` auf `''` zurücksetzen wenn Felder geändert werden
- [x] `frontend/src/components/MapView.tsx` — `getCoords()` (Z.42): `isFinite`-Guard ergänzt
- [x] `backend/src/api/capacity/schemas.py` — `LocationUpdateRequest`: `field_validator` für `lat` (−90…90) und `lon` (−180…180) mit `math.isfinite`-Check

**Acceptance Criteria:**
- Given "Neue Einrichtung"-Dialog geöffnet, Felder ausgefüllt, when Escape oder "Abbrechen" geklickt, then alle Felder leer / auf Default beim nächsten Öffnen.
- Given Einrichtung bearbeiten, `lat = "abc"`, when "Speichern" geklickt, then Inline-Fehler sichtbar, kein API-Aufruf, kein NaN in der DB.
- Given `lat = "91"`, when "Speichern" geklickt, then Fehler "Breitengrad muss zwischen -90 und 90 liegen".
- Given leeres GEO-Feld, when Speichern, then kein `lat`-Feld im PATCH-Body (bestehender Wert bleibt).
- Given Backend-PATCH mit `lat: NaN` (direkt via API), then HTTP 422.
- Given Location in DB hat `lat: NaN`, when Dashboard-Karte geladen, then Fallback-Koordinaten, kein Leaflet-Crash.

## Design Notes

`geoError` als lokaler State reicht — kein separates State-Management nötig. Validierung beim Speichern ist ausreichend; Echtzeit-Validierung würde unnötig stören (User tippt noch).

Der Pydantic-Validator benötigt `import math` innerhalb der Methode (oder als Modul-Level-Import in schemas.py) und einen `field_name`-Parameter via `info.field_name` für die unterschiedliche Range-Prüfung von lat vs. lon.

## Verification

**Commands:**
- `cd /Users/A3694852/KapzitaetsPlanungsTool/frontend && npx tsc --noEmit` — expected: 0 Fehler
- `cd /Users/A3694852/KapzitaetsPlanungsTool && python3 -m pytest backend/tests/ -x -q 2>/dev/null` — expected: alle grün
