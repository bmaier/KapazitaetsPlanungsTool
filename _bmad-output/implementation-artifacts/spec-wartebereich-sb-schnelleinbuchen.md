---
title: 'Wartebereich SB-Erweiterung — Schnelleinbuchen + Bett löschen'
type: 'feature'
created: '2026-06-06'
status: 'done'
baseline_commit: 'e8f2d3c9565b7365cff89cc42c4bd5b1c7b3ac8e'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Sachbearbeiter (writer-Rolle) können im Wartebereich nur neue Personen einbuchen, wenn ein freier Warteplatz sichtbar ist (Klick-auf-freies-Bett-Flow). Sind alle Plätze belegt, gibt es keinen direkten Weg — der SB muss erst Stammdaten öffnen, ein neues Bett anlegen, dann zurückkehren. Zusätzlich können freie, unbenötigte Warteplätze nicht direkt aus dem Wartebereich gelöscht werden.

**Approach:** (A) Prominenter „Person auf Warteplatz"-Button im Wartebereich-Header öffnet eine schlanke Schnell-Einbuchen-Maske (AZR-ID, Geschlecht, Belegung von/bis). Das Frontend sucht automatisch ein freies WARTEBEREICH-Bett; existiert keines, wird ein neues WARTEPLATZ-Bett im ersten WARTEBEREICH-Raum angelegt — alles in einem Schritt ohne Stammdaten-Öffnen. (B) Delete-Icon auf freien (unbelegten) Warteplatz-Cards im Wartebereich: Backend-seitig wird vor dem Soft-Delete geprüft, dass kein Occupant und keine aktive Reservierung an diesem Bett hängt.

## Boundaries & Constraints

**Always:**
- Nur `canEdit`-Rollen (writer, location-admin, system-admin) sehen Button und Delete-Icon
- Kein neues Backend-Endpoint für Feature A — bestehende `POST /rooms/{id}/beds` + `POST /beds/{id}/occupancy` reichen
- Backend `DELETE /beds/{bed_id}` bekommt Auth-Guard (derzeit fehlt er) + Belegungscheck + Reservierungscheck → 409 wenn blockiert
- Reload via `loadBedStatus()` nach jedem erfolgreichem Schreibvorgang
- Bestehender Klick-auf-freies-Bett-Flow (handleBedClick → setBelegBed) bleibt unverändert
- Geburtsjahr und Herkunftsland sind **nicht** Teil der Schnelleinbuchen-Maske (nur Occupancy-Felder: AZR-ID, Geschlecht, Start, Ende)

**Ask First:** — keine offenen Fragen.

**Never:**
- Kein Löschen belegter Betten über diesen Flow
- Kein Löschen von Betten, die eine PENDING/CONFIRMED-Reservierung als `suggested_bed_id` oder `confirmed_bed_id` haben
- Keine Änderung an der Batch-Verlegen- oder Extern-Verlegen-Logik

## I/O & Edge-Case Matrix

| Szenario | Zustand | Erwartetes Verhalten | Fehlerbehandlung |
|---|---|---|---|
| Schnelleinbuchen, freier Platz vorhanden | mind. 1 WARTEBEREICH-Bett FREI | POST occupancy auf das erste freie Bett | — |
| Schnelleinbuchen, alle Plätze belegt | alle WARTEBEREICH-Betten BELEGT | POST neues WARTEPLATZ-Bett, dann POST occupancy | 404 wenn kein WARTEBEREICH-Raum: Snackbar-Fehler |
| Schnelleinbuchen, kein WARTEBEREICH-Raum | keine WARTEBEREICH-Räume | Snackbar: „Kein Wartebereich vorhanden" | frühes Return, kein API-Call |
| Person bereits aktiv belegt | azr_id hat belegung_ende ≥ heute | 409 vom Backend → Snackbar-Fehler | |
| Delete freier Warteplatz | status=FREI, kein Occupant, keine Reservierung | Soft-Delete, Bett verschwindet aus Liste | — |
| Delete, Bett belegt | aktiver Occupant | Backend 409 → Snackbar „Platz ist belegt" | Button gar nicht gerendert (status≠FREI) |
| Delete, aktive Reservierung | PENDING/CONFIRMED-Reservierung auf Bett | Backend 409 → Snackbar „Aktive Reservierung vorhanden" | |

</frozen-after-approval>

## Code Map

- `backend/src/api/capacity/router.py:1052` — `DELETE /beds/{bed_id}`: Auth-Guard + Belegungs- + Reservierungscheck ergänzen
- `frontend/src/pages/Drilldown.tsx:527` — `canEdit`-Berechnung (writer ✓)
- `frontend/src/pages/Drilldown.tsx:560` — bestehende `belegBed`-State-Variablen (Vorbild für neuen Schnelleinbuchen-State)
- `frontend/src/pages/Drilldown.tsx:1002` — `handleBedClick`: freies Bett → setBelegBed (unverändert lassen)
- `frontend/src/pages/Drilldown.tsx:1354` — `ankunftRooms = rooms.filter(r => r.room_type === 'WARTEBEREICH')` — hier hängt der neue Button
- `frontend/src/pages/Drilldown.tsx:1370` — Wartebereich-Header-Button-Zeile (Gruppe auswählen): hier neuen Button daneben einfügen
- `frontend/src/pages/Drilldown.tsx:1404` — Warteplatz-Bed-Card Rendering-Block: hier Delete-Icon ergänzen
- `frontend/src/pages/SuggestionWizard.tsx:403` — `handleAutoWarteplatz`: Referenzimplementierung der Bett-Such/Anlege-Logik (nicht ändern, nur als Muster)
- `tests/features/wartebereich_sb.feature` — neue BDD-Szenarien (neu anlegen)
- `tests/steps/wartebereich_sb_steps.py` — Step-Definitionen (neu anlegen)

## Tasks & Acceptance

**Execution:**

- [x] `backend/src/api/capacity/router.py` — `DELETE /beds/{bed_id}` (Z. 1052): `user: UserContext = Depends(get_current_user)` ergänzen; vor `repo.deactivate()` prüfen: (1) aktiver Occupant via `SELECT id FROM persons.occupants WHERE bed_id=:bid AND belegung_ende >= CURRENT_DATE LIMIT 1` → 409 „Bett ist aktuell belegt"; (2) aktive Reservierung via `SELECT id FROM reservations.requests WHERE (suggested_bed_id=:bid OR confirmed_bed_id=:bid) AND status IN ('PENDING','CONFIRMED') LIMIT 1` → 409 „Bett hat eine aktive Reservierung"

- [x] `frontend/src/pages/Drilldown.tsx` — Schnelleinbuchen-State ergänzen (nach bestehenden `belegBed`-States ~Z. 568): `wpOpen: boolean`, `wpAzrId: string`, `wpGeschlecht: string` (default 'M'), `wpStart: string` (default heute), `wpEnde: string` (default heute+30 Tage), `wpSaving: boolean`

- [x] `frontend/src/pages/Drilldown.tsx` — Schnelleinbuchen-Submit-Handler `handleWpSave` implementieren: (a) `ankunftRooms` aus aktuellem `rooms`-State filtern; (b) erstes FREI-Bett suchen; (c) wenn keines: `POST /api/rooms/{firstRoom.room_id}/beds` mit `{bett_nummer: String(maxNum+1), bett_typ:'WARTEPLATZ'}`; (d) `POST /api/beds/{targetBedId}/occupancy` mit `{azr_id, geschlecht: wpGeschlecht, belegung_start: wpStart, belegung_ende: wpEnde}`; (e) `wpOpen=false`, `loadBedStatus()`, Snackbar Erfolg; 409/400 → Snackbar-Fehler

- [x] `frontend/src/pages/Drilldown.tsx` — „Person auf Warteplatz"-Button im Wartebereich-Header (Z. ~1370, neben dem „Gruppe auswählen"-Button): `{canEdit && (<Button size="small" variant="outlined" color="warning" startIcon={<PersonAddIcon/>} onClick={()=>setWpOpen(true)}>Person auf Warteplatz</Button>)}`; `PersonAddIcon` aus `@mui/icons-material/PersonAdd` importieren

- [x] `frontend/src/pages/Drilldown.tsx` — Schnelleinbuchen-Dialog rendern (am Ende der JSX, vor den bestehenden Dialogen): MUI `Dialog` mit `DialogTitle="Person auf Warteplatz einbuchen"`, drei Pflichtfelder: TextField AZR-ID (label „AZR-ID"), Select Geschlecht (label „Geschlecht", Optionen M/F/D mit deutschen Labels), TextField Belegung von (type date), TextField Belegung bis (type date); Submit-Button „Einbuchen" ruft `handleWpSave` auf, disabled wenn wpSaving oder AZR-ID leer

- [x] `frontend/src/pages/Drilldown.tsx` — Delete-Icon auf freien WARTEBEREICH-Bed-Cards (Z. ~1404, im Warteplatz-Card-Block): wenn `!isBelegt && canEdit` → kleines `IconButton` mit `DeleteIcon` in absoluter Positionierung (top-right des Cards); Klick öffnet Confirm-Snackbar oder inline-Confirm; nach Bestätigung `DELETE /api/beds/{bed.bed_id}`, dann `loadBedStatus()`; DeleteIcon aus `@mui/icons-media/Delete` importieren (sofern noch nicht importiert)

- [x] `tests/features/wartebereich_sb.feature` — BDD-Feature-Datei anlegen mit 4 Szenarien: (1) Schnelleinbuchen wenn freier Platz da; (2) Schnelleinbuchen wenn alle belegt (auto-Bett-Anlage); (3) Kein Wartebereich-Raum vorhanden; (4) Freien Warteplatz löschen

- [x] `tests/steps/wartebereich_sb_steps.py` — Step-Definitionen für alle Szenarien via `requests`-HTTP-Client gegen `localhost:8000`; Fixtures: Writer-Token + Location-ID aus Keycloak; nach jedem Test: aufgeräumte Betten/Occupancies (DELETE via API)

**Acceptance Criteria:**

- Given SB hat writer-Rolle und alle Warteplätze sind belegt, when SB klickt „Person auf Warteplatz" und trägt AZR-ID + Geschlecht + Datum ein und speichert, then erscheint die Person im Wartebereich und ein neuer Warteplatz-Eintrag ist angelegt
- Given SB hat writer-Rolle und ein freier Warteplatz existiert, when SB klickt „Person auf Warteplatz" und speichert, then wird kein neues Bett angelegt und die Person belegt den vorhandenen freien Platz
- Given ein Warteplatz ist frei (kein Occupant, keine Reservierung), when SB klickt Delete-Icon und bestätigt, then ist der Platz aus dem Wartebereich verschwunden
- Given ein Warteplatz ist belegt, then ist kein Delete-Icon sichtbar
- Given viewer-Rolle (kein writer), then sind weder „Person auf Warteplatz"-Button noch Delete-Icon sichtbar
- Given Delete-Icon-Klick auf Bett mit aktiver Reservierung, when Backend antwortet 409, then zeigt Snackbar „Aktive Reservierung vorhanden"

## Design Notes

**Schnelleinbuchen-Logik** ist analog zu `SuggestionWizard.tsx::handleAutoWarteplatz` (Z. 403–468). Der einzige Unterschied: kein Pre-Check auf bestehende Belegung — das Backend gibt 409 zurück, die Snackbar zeigt die Fehlermeldung. Kein doppelter Pre-Check im Frontend.

**Delete-Confirm:** Kein separater Dialog nötig. Ein `window.confirm` oder ein inline `Popover` reicht. Empfohlen: der `wpOpen`-Pattern mit einem kleinen `deleteConfirmBedId: string|null`-State — rendert einen winzigen Confirm-Snackbar/Alert unter dem Card.

**Geschlecht-Select-Optionen:**
```tsx
[{ value: 'M', label: 'Männlich' }, { value: 'F', label: 'Weiblich' }, { value: 'D', label: 'Divers' }]
```

## Verification

**Commands:**
- `cd /Users/A3694852/KapzitaetsPlanungsTool/frontend && npx tsc --noEmit` — expected: 0 errors
- `cd /Users/A3694852/KapzitaetsPlanungsTool && python -m behave tests/features/wartebereich_sb.feature` — expected: alle Szenarien grün

**Manual checks:**
- Drilldown einer Einrichtung mit vollem Wartebereich: Button „Person auf Warteplatz" sichtbar, Dialog öffnet sich, Einbuchen klappt, neuer Platz erscheint
- Drilldown einer Einrichtung mit freiem Warteplatz: Button einbucht auf freies Bett ohne neues anzulegen
- Delete-Icon auf freiem Warteplatz sichtbar, auf belegtem nicht
- viewer-User: kein Button, kein Delete-Icon
