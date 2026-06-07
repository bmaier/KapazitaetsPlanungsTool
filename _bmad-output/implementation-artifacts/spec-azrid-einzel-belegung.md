---
title: 'AZR-ID Einzel-Belegung — Invariante: genau eine aktive Belegung pro Person'
type: 'bugfix'
created: '2026-06-06'
status: 'done'
baseline_commit: 'ab8738662c6c76f319721ea66da56367f42562f5'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Eine Person (azr_id) kann aktuell gleichzeitig mehrere aktive Belegungen besitzen — entweder durch versehentliches doppeltes Buchen oder durch einen fehlgeschlagenen DELETE beim internen Verlegen. Es gibt weder einen Backend-Guard noch eine atomare Fehlerbehandlung im Frontend.

**Approach:** (1) Backend-Guard in `create_occupancy`: Prüfe ob azr_id bereits eine überlappende aktive Belegung hat — wenn ja 409 mit Einrichtungs-/Raum-/Bett-Info. Exception: wenn `verlegung_grund` gesetzt ist (explizites Verlegen — alte Belegung wird unmittelbar danach gelöscht). (2) Frontend-Rollback in `handleVerlegen` / `handleBatchIntern`: DELETE neue Belegung wenn der darauffolgende DELETE alte Belegung fehlschlägt. (3) Pre-Check in `handleAutoWarteplatz` (SuggestionWizard): Suche Person erst in aktiven Belegungen — wenn gefunden, Fehler mit aktuellem Standort zeigen statt doppelt buchen.

## Boundaries & Constraints

**Always:**
- Backend-Check überspringen wenn `verlegung_grund` im Request-Body gesetzt ist (markiert absichtliches Verlegen — Kurzzeitfenster mit 2 Belegungen ist unvermeidbar und by design)
- 409-Detail als lesbarer String: `"Person {azr_id} bereits aktiv belegt: {location_name}, {room_name}, Bett {bett_nummer} ({start} – {ende})"`
- Rollback (DELETE neue Belegung) ist Best-Effort — scheitert er, Snackbar mit explizitem Hinweis "Manuelle Korrektur erforderlich"
- `transfer()` in `reservation_repo.py` löscht Warteplatz bereits korrekt — dort keine Änderung
- Keine DB-Migration — kein neuer Unique-Constraint (laufende Verlege-Operationen würden ihn verletzen)

**Ask First:**
- Soll der Backend-Check auch für `handleBelegen` mit gesetztem `verlegung_grund = null` grifen, wenn eine Person eine historische (abgelaufene) Belegung hat? (Vermutlich ja, aber bitte bestätigen falls unklar)

**Never:**
- Kein DB-Unique-Constraint auf `(azr_id, belegung_start, belegung_ende)`
- Keine Änderung an `reservation_repo.transfer()` — bereits korrekt
- Kein neuer API-Endpoint — bestehende Endpunkte erweitern

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Doppelbuchung verhindert | POST `create_occupancy` für azr_id X, azr_id X bereits in Raum B Bett 3 (gleicher Zeitraum), kein `verlegung_grund` | 409 mit Detail "Person X bereits aktiv belegt: Einrichtung Y, Raum B, Bett 3 (…)" | Frontend zeigt Snackbar mit vollem Detail-String |
| Verlegen erlaubt | POST `create_occupancy` für azr_id X, `verlegung_grund` gesetzt, X schon in Bett A | 201 Created (Guard übersprungen) | — |
| Rollback bei DELETE-Fehler | `handleVerlegen`: POST neue Belegung OK, DELETE alte Belegung → Netzwerkfehler | DELETE neue Belegung (Best-Effort), Snackbar "Verlegen fehlgeschlagen — bitte manuell prüfen" | Falls Rollback-DELETE auch scheitert: Snackbar "Manuelle Korrektur erforderlich: Person in 2 Betten" |
| SuggestionWizard Pre-Check — Person bereits belegt | `handleAutoWarteplatz` für azr_id X, X hat aktive Belegung in Bett 7 (belegung_ende >= today) | Snackbar "Person X bereits belegt in {Einrichtung}, {Raum}, Bett 7 — kein Warteplatz angelegt" | Kein POST, kein neues Bett |
| SuggestionWizard — neue Person | `handleAutoWarteplatz` für azr_id Y (unbekannt, nicht in Occupants), freier Warteplatz vorhanden | Belegung auf freiem Warteplatz anlegen — normaler Ablauf | — |
| SuggestionWizard — neue Person, alle Warteplätze voll | `handleAutoWarteplatz` für azr_id Y (unbekannt), alle Warteplätze BELEGT | Neuen WARTEPLATZ-Bed auto-anlegen (sequenzielle Nummer) + Belegung anlegen | — |
| SuggestionWizard — nur historische Belegungen | `handleAutoWarteplatz` für azr_id Z, Z hatte früher Belegung (belegung_ende < today) | Behandeln wie neue Person — Warteplatz anlegen | — |

</frozen-after-approval>

## Code Map

- `backend/src/api/capacity/router.py:1154ff` — `create_occupancy`: Hier Backend-Guard einfügen (nach `check_bed_available`, vor `Occupancy(...)`)
- `backend/src/api/capacity/router.py:1338ff` — `end_occupancy`: Rollback-Ziel für Frontend; keine Änderung nötig
- `frontend/src/pages/Drilldown.tsx:handleVerlegen` — POST dann DELETE; Rollback ergänzen
- `frontend/src/pages/Drilldown.tsx:handleBatchIntern` — gleiche Rollback-Logik pro Person
- `frontend/src/pages/SuggestionWizard.tsx:handleAutoWarteplatz` — Pre-Check via `/api/occupants/search?azr_id=…` vor Warteplatz-POST

## Tasks & Acceptance

**Execution:**

- [x] `backend/src/api/capacity/router.py` — In `create_occupancy` nach `check_bed_available(existing)`: SQL-Query auf `persons.occupants` für `azr_id = body.azr_id AND belegung_start < body.belegung_ende AND belegung_ende > body.belegung_start`. Wenn Treffer und `not body.verlegung_grund`: JOIN auf `capacity.beds b` und `capacity.rooms r` und `capacity.locations l` für Einrichtungs-/Raum-/Bett-Info → `raise HTTPException(409, detail=f"Person {body.azr_id} bereits aktiv belegt: {l.name}, {r.name}, Bett {b.bett_nummer} ({occ.belegung_start} – {occ.belegung_ende})")`.

- [x] `frontend/src/pages/Drilldown.tsx` — `handleVerlegen`: Neue Belegung-ID aus POST-Response speichern. In `catch`/`finally` nach fehlgeschlagenem DELETE der alten Belegung: Best-Effort-DELETE der neuen Belegung via `del('/api/beds/{verlegenTargetBed}/occupancy/{newOccId}')`. Snackbar-Text je nach Rollback-Erfolg anpassen.

- [x] `frontend/src/pages/Drilldown.tsx` — `handleBatchIntern`: Pro Person (Schleife) gleiche Rollback-Logik: `newOccId` aus POST-Response merken, bei DELETE-Fehler Rollback-DELETE der neuen Belegung, Snackbar "Verlegen teilweise fehlgeschlagen — {n} Personen nicht verlegt, bitte prüfen".

- [x] `frontend/src/pages/SuggestionWizard.tsx` — `handleAutoWarteplatz`: Vor dem Warteplatz-POST: `GET /api/occupants/search?azr_id={a.azr_id.trim()}`. Auswertung: Wenn Ergebnis Einträge enthält **und** mind. ein Eintrag hat `belegung_ende >= today` (aktive Belegung) → `setSnackbar(...)` mit Standort-Info aus diesem Eintrag, `setBedAssignments(...)` zurücksetzen, return — kein Warteplatz anlegen. In allen anderen Fällen (keine Treffer, oder nur historische Belegungen mit `belegung_ende < today`) → normaler Ablauf: freien Warteplatz verwenden oder neuen anlegen (sequenzielle Nummer wie bisher).

**Acceptance Criteria:**

- Given Person X bereits in Bett A belegt, when POST `create_occupancy` ohne `verlegung_grund`, then 409 mit lesbarem Standort-Hinweis
- Given `verlegung_grund` gesetzt, when POST `create_occupancy` obwohl Person schon belegt, then 201 (Guard übersprungen)
- Given `handleVerlegen` und DELETE alte Belegung schlägt fehl, when Rollback, then neue Belegung wird ebenfalls gelöscht und Snackbar erklärt Zustand
- Given `handleAutoWarteplatz` für azr_id mit bestehender **aktiver** Belegung (belegung_ende >= today), when Aufruf, then kein neuer Warteplatz, Snackbar mit aktuellem Standort
- Given `handleAutoWarteplatz` für **unbekannte** azr_id (nie belegt oder nur historisch), when alle Warteplätze belegt, then neuer WARTEPLATZ-Bed wird auto-angelegt und Person eingebucht

## Design Notes

**Warum kein DB-Constraint:** Intern-Verlegen erzeugt absichtlich ein Kurzzeitfenster mit 2 Belegungen (POST neu → DELETE alt). Ein Unique-Constraint würde jeden Verlege-Vorgang blockieren. Daher nur App-Level-Guard mit `verlegung_grund`-Bypass.

**Rollback-Pattern in handleVerlegen:**
```typescript
const newOcc = await post<{id: string}>(`/api/beds/${verlegenTargetBed}/occupancy`, { ... })
try {
  await del(`/api/beds/${src.bed_id}/occupancy/${src.occupancy_id}`)
} catch (delErr) {
  try { await del(`/api/beds/${verlegenTargetBed}/occupancy/${newOcc.id`) } catch {}
  throw delErr  // re-throw → Snackbar
}
```

## Verification

**Commands:**
- `cd frontend && npx tsc --noEmit` — expected: 0 errors

**Manual checks:**
- Zwei Belegungen gleicher azr_id anlegen (ohne verlegung_grund): Backend muss 409 zurückgeben
- Intern verlegen: POST neue Belegung, dann DELETE alte → beide im DB prüfen dass korrekt
