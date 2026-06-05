---
title: 'Location Sichtbarkeit & Deaktivierung'
type: 'feature'
created: '2026-06-05'
status: 'done'
baseline_commit: '1e3f88c'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Einrichtungen können nicht deaktiviert (Soft-Delete) oder von der Karte ausgeblendet werden. Admins brauchen (1) einen `is_active`-Toggle, um eine Einrichtung aus dem operativen Betrieb herauszunehmen, und (2) einen `show_on_map`-Toggle, um Einrichtungen selektiv aus der Kartenansicht auszublenden — unabhängig von ihrer Aktivität.

**Approach:** Neues DB-Feld `show_on_map BOOLEAN NOT NULL DEFAULT TRUE` via Alembic-Migration; `LocationUpdateRequest` erhält `is_active` und `show_on_map`; PATCH-Endpoint schreibt beide; Drilldown-Edit-Dialog (Tab 0, nur Admin) zeigt zwei MUI-Switches; MapView filtert nach `show_on_map !== false`; Dashboard-Grid zeigt weiterhin nur is_active=true-Locations (bestehende Summary-Query unverändert).

## Boundaries & Constraints

**Always:**
- `show_on_map` Default = `true` — bestehende Einrichtungen bleiben nach der Migration automatisch kartensichtbar.
- `GET /api/locations/{id}` filtert nicht nach `is_active` — Admin kann deaktivierte Einrichtung per Direktlink aufrufen und reaktivieren.
- Beide Switches sind nur für `isAdmin` (system-admin oder location-admin) im Edit-Dialog sichtbar.
- MapView filtert: `l.is_active && l.show_on_map !== false` — inaktive Locations verschwinden aus der Karte genauso wie show_on_map=false.
- Bestehende Räume, Betten und Belegungen werden nicht verändert.

**Ask First:**
- Sollen deaktivierte Locations im Dashboard-Grid für Admins weiterhin sichtbar sein (ausgegraut, mit Reaktivierungs-Button)? → Nur dann nötig, wenn Admins nicht den Direktlink nutzen wollen. Für Ziel 2 nein — Direktnavigation reicht.

**Never:**
- Physisches Löschen von Locations (kein DELETE-Endpoint, kein CASCADE auf Räume/Betten).
- `show_on_map` im Dashboard-Grid-View auswerten (nur für die Karte relevant).
- Bestehende `kontingent`-Schutzlogik im PATCH-Endpoint anfassen.

## I/O & Edge-Case Matrix

| Szenario | Input / State | Erwartetes Verhalten | Fehlerbehandlung |
|----------|--------------|----------------------|-----------------|
| Einrichtung deaktivieren | Admin setzt is_active=false → Speichern | Location verschwindet aus Dashboard-Grid und Karte beim nächsten Laden | — |
| Reaktivierung via Direktlink | Admin navigiert zu /locations/{id}, setzt is_active=true | Location erscheint wieder in Grid und Karte | — |
| show_on_map=false | Admin setzt show_on_map=false → Speichern | Location bleibt im Grid, verschwindet von der Karte | — |
| Neues Feld nach Migration | Bestehende Locations in DB | show_on_map = true (DEFAULT) — keine Karte-Änderung | — |
| show_on_map undefined im Frontend | API gibt show_on_map nicht zurück (alter Client) | `show_on_map !== false` → true — bleibt sichtbar | — |

</frozen-after-approval>

## Code Map

- `backend/alembic/versions/0017_location_visibility.py` — neue Migration: ADD COLUMN show_on_map
- `backend/src/api/capacity/schemas.py:159` — `LocationUpdateRequest`: is_active + show_on_map ergänzen; `LocationResponse:27` + `LocationSummaryResponse:191`: show_on_map feld
- `backend/src/api/capacity/router.py:203` — list_locations SELECT + Konstruktor; `:238` summary SELECT+GROUP BY+Konstruktor; `:299` get_location SELECT+Konstruktor; `:332` update_location SET+RETURNING+updates-Dict
- `frontend/src/pages/Drilldown.tsx:52` — Location interface: show_on_map; `:367` neue States editShowOnMap + editIsActive; `:525` openEdit() init; `:557` saveEdit() PATCH-Body; `:1587` Dialog Tab 0: zwei Switch-Zeilen
- `frontend/src/components/MapView.tsx:18` — LocationSummary interface: show_on_map; `:104` active-Filter
- `frontend/src/pages/Dashboard.tsx:38` — LocationSummary interface: show_on_map

## Tasks & Acceptance

**Execution:**
- [x] `backend/alembic/versions/0017_location_visibility.py` — neue Migration anlegen: `ALTER TABLE capacity.locations ADD COLUMN show_on_map BOOLEAN NOT NULL DEFAULT TRUE`; downgrade entfernt die Spalte
- [x] `backend/src/api/capacity/schemas.py` — `LocationResponse` + `LocationSummaryResponse`: Feld `show_on_map: bool = True` ergänzen; `LocationUpdateRequest`: `is_active: Optional[bool] = None` und `show_on_map: Optional[bool] = None` ergänzen
- [x] `backend/src/api/capacity/router.py` — in allen vier SQL-Statements `show_on_map` in SELECT/RETURNING/GROUP BY ergänzen; `is_active` und `show_on_map` in updates-Dict des PATCH-Endpoints aufnehmen; alle `LocationResponse`- und `LocationSummaryResponse`-Konstruktoren um `show_on_map=row["show_on_map"]` erweitern
- [x] `frontend/src/pages/Drilldown.tsx` — `Location` interface: `show_on_map?: boolean` ergänzen; States `editShowOnMap: boolean` (init: true) und `editIsActive: boolean` (init: true); `openEdit()` initialisiert beide aus `location`; `saveEdit()` sendet `is_active: editIsActive` und `show_on_map: editShowOnMap` im PATCH-Body; Dialog Tab 0: zwei `FormControlLabel + Switch`-Zeilen (nur wenn `isAdmin`): "Einrichtung aktiv" und "Auf Karte anzeigen"
- [x] `frontend/src/components/MapView.tsx` — `LocationSummary` interface: `show_on_map?: boolean | null` ergänzen; `active`-Filter: `locations.filter(l => l.is_active && l.show_on_map !== false)`
- [x] `frontend/src/pages/Dashboard.tsx` — `LocationSummary` interface: `show_on_map?: boolean | null` ergänzen (kein Logik-Change, nur Typ-Vollständigkeit)

**Acceptance Criteria:**
- Given Einrichtung aktiv und show_on_map=false, when Karte geladen, then kein Marker für diese Einrichtung.
- Given is_active=false via Edit-Dialog gesetzt und gespeichert, when Dashboard neu geladen, then Einrichtung weder im Grid noch auf der Karte.
- Given deaktivierte Einrichtung, when Admin navigiert direkt zu /locations/{id}, then Drilldown lädt; Edit-Dialog zeigt is_active=false; Admin kann reaktivieren.
- Given bestehende DB-Einrichtung nach Migration, then show_on_map=true — Karte unverändert.
- Given kein Admin (location-writer Rolle), when Edit-Dialog geöffnet, then keine Switch-Zeilen für is_active/show_on_map sichtbar.

## Design Notes

`editIsActive` und `editShowOnMap` sind lokale Boolean-States (kein neues State-Management nötig). Der PATCH-Body sendet immer beide Felder — bei boolean ist kein "leer lassen" nötig.

Der `active`-Filter in MapView war bisher `locations.filter(l => l.is_active)`. Mit `show_on_map` wird er zu `locations.filter(l => l.is_active && l.show_on_map !== false)` — `!== false` statt `=== true`, damit undefined-Werte (alter API-Cache) sicher als "sichtbar" behandelt werden.

## Verification

**Commands:**
- `cd /Users/A3694852/KapzitaetsPlanungsTool/frontend && npx tsc --noEmit` — expected: 0 Fehler
- `cd /Users/A3694852/KapzitaetsPlanungsTool && python3 -m pytest backend/tests/ -x -q 2>/dev/null` — expected: alle grün
