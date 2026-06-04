---
title: 'Belegung-vormerken: Neue Person anlegen + Pflicht-Warteplatz vor Anfrage'
type: 'feature'
created: '2026-06-04'
status: 'done'
baseline_commit: '06401b4'
context: ['_bmad-output/project-context.md']
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Wenn im Belegung-vormerken-Dialog eine AZR-Suche keinen Treffer liefert (Person noch nicht im System), gibt es keinen geführten Einbuchungsweg. Zudem werden `geburtsjahr` / `herkunftsland` in Verlegungsanfragen als Hardcode-Platzhalter gesendet, was die Datenqualität mindert.

**Approach:**
Im "Keine Treffer"-Block wird ein Formular (Geschlecht, Geburtsjahr, Herkunftsland) eingeblendet. Der SB klickt "Im Wartebereich einbuchen" — das System sucht automatisch einen freien WARTEPLATZ in einem WARTEBEREICH-Zimmer der eigenen Location. Wenn kein freies Bett vorhanden → automatisch ein neues WARTEPLATZ-Bett im ersten WARTEBEREICH-Zimmer anlegen (POST `/api/rooms/{room_id}/beds`). Wenn kein WARTEBEREICH-Zimmer existiert → Meldung an den SB ("Admin muss Wartebereich in Stammdaten anlegen"), Aktion blockiert. Erst nach erfolgreicher Warteplatz-Belegung ist "Bestätigen" (Verlegungsanfrage / lokale Vormerkung) freigegeben. Geburtsjahr / Herkunftsland fließen aus dem Formular in den `POST /api/reservations`-Body.

## Boundaries & Constraints

**Always:**
- Warteplatz-Belegung ist **Voraussetzung** für den "Bestätigen"-Schritt bei neuer Person — kein Bypass.
- Kein WARTEBEREICH-Zimmer an der Location → Fehlermeldung "Kein Wartebereich vorhanden — bitte Administrator kontaktieren." + kein Weitermachen.
- Auto-Create-Bett: `bett_typ = 'WARTEPLATZ'`, `bett_nummer` = `'W-AUTO-{timestamp}'`; wird im ersten WARTEBEREICH-Zimmer der Location angelegt.
- `GET /api/locations/{id}/bed-status` Antwort muss `room_id` pro Raum enthalten (TypeScript-Typ erweitern).
- Geburtsjahr/Herkunftsland: Fallback wenn leer → `new Date().getFullYear() - 30` / `'UNK'`.
- Rollen: Writer der Location + Admins dürfen Warteplatz anlegen — bestehende Berechtigungslogik greift automatisch (kein neuer Guard).
- Bestehende manuelle Warteplatz-Form (`handleOpenWarteplatz`) bleibt unverändert; neuer Pfad ist der "Keine Treffer"-Block.

**Ask First:** — keine offenen Fragen.

**Never:**
- Verlegungsanfrage vor erfolgreicher Warteplatz-Belegung zulassen.
- `geburtsjahr`/`herkunftsland` an `POST /api/beds/{id}/occupancy` senden (OccupancyCreate kennt diese Felder nicht).
- Warteplatz-Auto-Create wenn WARTEBEREICH-Zimmer komplett fehlt — stattdessen blockieren.

## I/O & Edge-Case Matrix

| Szenario | Zustand | Erwartetes Verhalten |
|----------|---------|---------------------|
| Keine Treffer, neues Formular | `searchDone && !searchFound && searchResults.length===0 && azr_id.trim()` | Formular (Geschlecht/Geburtsjahr/Herkunftsland) + Button "Im Wartebereich einbuchen" sichtbar |
| Freier Warteplatz vorhanden | `handleAutoWarteplatz` findet WARTEBEREICH-Bett mit status='FREI' | POST occupancy → `warteplatzCreated=true` → Bestätigen-Button aktiv |
| Kein freies Bett, Zimmer vorhanden | WARTEBEREICH-Zimmer vorhanden, alle Betten belegt | POST neues WARTEPLATZ-Bett → POST occupancy → `warteplatzCreated=true` |
| Kein WARTEBEREICH-Zimmer | Location hat kein WARTEBEREICH-Zimmer | Snackbar "Kein Wartebereich vorhanden — Administrator kontaktieren" + keine weitere Aktion |
| Warteplatz-Belegung 409 (Ein-Platz) | Person bereits anderswo aktiv belegt | Snackbar "Person bereits in anderer Einrichtung aktiv belegt (Ein-Platz-Regel)" |
| Bestätigen ohne Warteplatz | `warteplatzCreated=false` bei neuer Person | Bestätigen-Button disabled |
| Reservation mit Geburtsjahr/Herkunftsland | `a.neuePersonGeburtsjahr` gesetzt | POST /reservations enthält eingegebene Werte statt Hardcode |
| Geburtsjahr/Herkunftsland leer | Felder nicht ausgefüllt | Fallback: Jahr-30, 'UNK' |

</frozen-after-approval>

## Code Map

- `frontend/src/pages/SuggestionWizard.tsx:205` — `BedAssignment` Interface: neue Felder `neuePersonGeschlecht`, `neuePersonGeburtsjahr`, `neuePersonHerkunftsland`
- `frontend/src/pages/SuggestionWizard.tsx:341` — `handleOpenConfirm`: neue Felder mit Defaults initialisieren
- `frontend/src/pages/SuggestionWizard.tsx:405` — `BedStatusRoom` Typ: `room_id` und `room_name` ergänzen
- `frontend/src/pages/SuggestionWizard.tsx:460` — neue Funktion `handleAutoWarteplatz(idx)` nach `handleSubmitWarteplatz`
- `frontend/src/pages/SuggestionWizard.tsx:574` — `handleAccept` warteplatzCreated-Pfad: Geburtsjahr/Herkunftsland aus State
- `frontend/src/pages/SuggestionWizard.tsx:588` — `handleAccept` Auto-Warteplatz-Block (searchDone+!searchFound+isCross): durch `warteplatzCreated`-Prüfung ersetzen (Warteplatz muss vorher via handleAutoWarteplatz erstellt worden sein)
- `frontend/src/pages/SuggestionWizard.tsx:1362` — "Keine Treffer"-Block: Formular + "Im Wartebereich einbuchen"-Button; Bestätigen-Button-Disable-Logik
- `backend/src/api/capacity/router.py` — `end_occupancy` DELETE: internes-Verlegen-Fix bereits implementiert (2026-06-04)

## Tasks & Acceptance

**Execution:**
- [x] `frontend/src/pages/SuggestionWizard.tsx` — `BedAssignment` Interface (Z.205): `neuePersonGeschlecht: string`, `neuePersonGeburtsjahr: string`, `neuePersonHerkunftsland: string` hinzufügen
- [x] `frontend/src/pages/SuggestionWizard.tsx` — `BedStatusRoom` lokalen Typ: `room_id: string` ergänzen (alle Vorkommen via replace_all)
- [x] `frontend/src/pages/SuggestionWizard.tsx` — `handleOpenConfirm` (Z.341): Defaults `neuePersonGeschlecht: 'M', neuePersonGeburtsjahr: '', neuePersonHerkunftsland: ''` in `setBedAssignments`-Initialisierung
- [x] `frontend/src/pages/SuggestionWizard.tsx` — neue Funktion `handleAutoWarteplatz(idx)`: (1) GET bed-status → WARTEBEREICH+FREI suchen; (2) wenn keins → erstes WARTEBEREICH-Zimmer suchen; (3) wenn kein Zimmer → Snackbar "Kein Wartebereich vorhanden — Administrator kontaktieren" + return; (4) wenn Zimmer vorhanden aber kein freies Bett → POST `/api/rooms/{room_id}/beds` `{bett_nummer:'W-AUTO-{Date.now()}', bett_typ:'WARTEPLATZ'}`; (5) POST `/api/beds/{bed_id}/occupancy`; (6) bei 409 → Snackbar Ein-Platz-Meldung; (7) bei 201 → `warteplatzCreated:true, searchFound:true, geschlecht:neuePersonGeschlecht, foundLocationId:locationId`
- [x] `frontend/src/pages/SuggestionWizard.tsx` — `handleAccept` warteplatzCreated-Pfad: `geburtsjahr: a.neuePersonGeburtsjahr ? parseInt(a.neuePersonGeburtsjahr) : new Date().getFullYear()-30, herkunftsland: a.neuePersonHerkunftsland || 'UNK'`
- [x] `frontend/src/pages/SuggestionWizard.tsx` — `handleAccept` Auto-Warteplatz-Block: bestehenden Block entfernt; neue Person ohne warteplatzCreated → Snackbar "Bitte zuerst im Wartebereich einbuchen" + return (Guard)
- [x] `frontend/src/pages/SuggestionWizard.tsx` — "Keine Treffer"-Block: Formular eingeblendet (Geschlecht-Select, Geburtsjahr-TextField, Herkunftsland-TextField); "Im Wartebereich einbuchen"-Button; "AZR korrigieren"-Button

**Acceptance Criteria:**
- Given Person nicht im System, when "Keine Treffer" angezeigt, then Formular (Geschlecht/Geburtsjahr/Herkunftsland) + "Im Wartebereich einbuchen"-Button sichtbar.
- Given freier WARTEPLATZ vorhanden, when "Im Wartebereich einbuchen" geklickt, then POST occupancy + `warteplatzCreated=true` + Bestätigen-Button aktiv.
- Given keine freien Warteplätze aber WARTEBEREICH-Zimmer vorhanden, when Button geklickt, then neues WARTEPLATZ-Bett auto-erstellt + Person eingebucht + `warteplatzCreated=true`.
- Given kein WARTEBEREICH-Zimmer an Location, when Button geklickt, then Snackbar "Kein Wartebereich vorhanden — Administrator kontaktieren" + kein weiterer Schritt.
- Given Person bereits anderswo belegt, when POST occupancy → 409, then Snackbar Ein-Platz-Meldung.
- Given neue Person + `warteplatzCreated=false`, when Bestätigen versucht, then return mit Hinweis (Guard).
- Given Geburtsjahr/Herkunftsland eingegeben, when Reservation gesendet, then POST /reservations enthält eingegebene Werte.
- Given internes Verlegen (DELETE altes Bett, Person hat PENDING Reservation), when DELETE aufgerufen, then HTTP 200 (kein Block), Reservation-Status unverändert. *(Backend-Fix bereits implementiert)*

## Design Notes

`handleAutoWarteplatz` ist eine Sofort-Aktion (wie `handleSubmitWarteplatz`). Nach Erfolg ist die Person im System → `handleAccept` nimmt den `warteplatzCreated`-Pfad und schickt bei Cross-Location eine Reservation.

Der bestehende `else if (a.searchDone && !a.searchFound && isCrossLocation …)` Block in `handleAccept` (Z.588) wird zu einem Guard umgebaut: neue Person ohne `warteplatzCreated` → return mit Fehlermeldung. Das stellt sicher, dass `handleAutoWarteplatz` immer zuerst durchläuft.

`BedStatusRoom.room_id` wird benötigt damit der Auto-Create-Schritt das richtige Zimmer anspricht. Der Backend-Endpunkt `GET /api/locations/{id}/bed-status` gibt `room_id` bereits zurück — nur der TypeScript-Typ muss erweitert werden.
