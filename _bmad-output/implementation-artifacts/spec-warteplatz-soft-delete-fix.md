---
title: 'Warteplatz anlegen nach Löschen — Soft-Delete-Kollision Fix'
type: 'bugfix'
created: '2026-06-07'
status: 'done'
baseline_commit: 'aktuell'
context: ['_bmad-output/project-context.md']
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Nach dem Deaktivieren (Soft-Delete) eines Warteplatz-Betts schlägt das Anlegen eines neuen Warteplatz-Betts mit HTTP 500 "Internal Server Error" fehl.

**Root Cause:**
1. `handleDeleteWarteplatz` ruft `DELETE /api/beds/{id}` → `repo.deactivate()` → setzt `is_active = false` (Soft-Delete). Die Zeile bleibt in der DB mit `bett_nummer = "1"`.
2. `GET /api/locations/{id}/bed-status` gibt nur aktive Betten zurück (`AND b.is_active = true`). Das deaktivierte Bett ist im Frontend nicht sichtbar.
3. `handleAddWarteplatz` berechnet `maxNum` aus `warteRooms.flatMap(r => r.beds)` — das sind nur aktive Betten. Nach Soft-Delete: `maxNum = 0`, neues `bett_nummer = "1"`.
4. `POST /api/rooms/{room_id}/beds` mit `bett_nummer = "1"` kollidiert mit dem Soft-Deleted-Record → DB-Fehler.

**Approach:** In `handleAddWarteplatz`: statt `maxNum` aus dem lokalen State zu berechnen, wird `GET /api/rooms/{firstRoom.room_id}/beds?include_inactive=true` aufgerufen um alle Betten einschließlich Soft-Deleted-Zeilen zu laden. `maxNum` wird aus dem vollständigen Set berechnet → `maxNum + 1` ist garantiert kollisionsfrei.

## Boundaries & Constraints

**Always:**
- B-01: `GET /api/rooms/{room_id}/beds?include_inactive=true` vor jedem Warteplatz-Anlegen aufrufen.
- B-02: `maxNum` aus ALLEN Betten berechnen (aktiv + inaktiv) um `bett_nummer`-Kollisionen zu vermeiden.
- B-03: Der existing Endpoint `?include_inactive=true` ist bereits im Backend implementiert — kein neuer Endpoint notwendig.

**Never:**
- Keine physische Löschung von Bett-Zeilen (Soft-Delete bleibt als Architektur-Entscheidung erhalten).
- Keine Änderung am Backend — rein Frontend-Fix.

## Defense-in-Depth: Zwei Fix-Ebenen

Die Lösung besteht aus zwei unabhängig wirkenden Fixes — beide gemeinsam sind am sichersten:

| Ebene | Fix | Wirkung |
|-------|-----|---------|
| DB (Migration 0019) | Partieller UNIQUE INDEX `WHERE is_active = true` | DB erlaubt Nummern-Wiederverwendung wenn bisheriger Träger inaktiv ist |
| Frontend | `include_inactive=true` für `maxNum`-Berechnung | UI vergibt nie eine Nummer die schon existiert (aktiv ODER inaktiv) |

Ohne Migration 0019 schlägt die Erstellung fehl (DB-Constraint). Ohne Frontend-Fix wird immer Nummer 1 wiederverwendet (riskant ohne 0019). Mit beiden Fixes: absolut kollisionssicher.

## Technischer Hintergrund — Soft-Delete-Architektur

Betten werden niemals physisch gelöscht. `DELETE /api/beds/{id}` ruft `repo.deactivate()` auf → `is_active = false`. Die Zeile bleibt in `capacity.beds`. Dieses Pattern ist notwendig weil:
- `persons.occupants` referenziert `bed_id` (Foreign Key)
- Historische Belegungsdaten müssen erhalten bleiben (Audit-Pflicht)
- Physisches Löschen würde Foreign-Key-Constraint verletzen

</frozen-after-approval>

## Code Map

- `frontend/src/pages/Drilldown.tsx:handleAddWarteplatz` — ersetzt lokale `allBeds`-Berechnung durch `await get<...>('/api/rooms/{firstRoom.room_id}/beds?include_inactive=true')`
- `backend/src/api/capacity/router.py:list_beds` — `?include_inactive=true` Query-Parameter (bereits vorhanden)
- `backend/src/adapters/db/capacity_repo.py:deactivate` — setzt `is_active = false` (unverändert)

## Tasks & Acceptance

**Execution:**
- [x] `Drilldown.tsx:handleAddWarteplatz` — `allBeds` Berechnung ersetzt durch API-Call `GET .../beds?include_inactive=true`

**Acceptance Criteria:**
- Nach Deaktivieren eines Warteplatz-Betts kann sofort ein neues angelegt werden — kein HTTP 500.
- Neues Bett erhält `bett_nummer = maxNum + 1` (wobei `maxNum` alle inkl. inaktive Betten umfasst).
- Das deaktivierte Bett bleibt in der DB erhalten (Soft-Delete ist permanent).
