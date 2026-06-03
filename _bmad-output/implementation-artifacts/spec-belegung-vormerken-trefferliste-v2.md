---
title: 'Belegung vormerken — Gruppierte Trefferliste, Kontextwarnungen & Auto-Warteplatz'
type: 'feature'
created: '2026-06-02'
status: 'done'
context:
  - spec-belegung-vormerken-suche-fix.md
  - spec-bettsuche-hasperson-exactmatch.md
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Im „Belegung vormerken"-Dialog (Überschrift: „Bettsuche") zeigt die Trefferliste mehrere Suchergebnisse ohne Gruppierung oder Kontext: Nutzer erkennen nicht, ob eine Person in der eigenen Einrichtung (Wartebereich), bei einer Fremdeinrichtung oder gar nirgends eingebucht ist. Außerdem können Verlegungsanfragen für komplett unregistrierte Personen abgeschickt werden — was zu hängenden Anfragen ohne Ausgangsbett führt.

**Approach:** (1) Trefferliste in drei Gruppen aufteilen: eigene Einrichtung Wartebereich → eigene Einrichtung (andere Räume) → Fremdeinrichtungen; pro Treffer Geschlecht, Labels, Raumname und Belegungsende anzeigen. (2) Warnung wenn für diese Person bereits eine aktive (PENDING) Anfrage der eigenen Einrichtung läuft. (3) Info-Banner wenn Fremdperson ausgewählt (muss abgestimmt sein, nicht blockierend). (4) „Option bestätigen" blockieren wenn Person nicht gefunden → Inline-Flow „Warteplatz anlegen": freies Wartebereich-Bett suchen, Labels vergeben, Belegung anlegen. Kein neuer Backend-Endpoint nötig.

## Boundaries & Constraints

**Always:**
- Eigene Einrichtung bestimmt durch `locationId` aus `useKeycloak()` verglichen mit `location_id` aus `OccupantSearchResult`
- Wartebereich-Erkennung: `room_type === 'WARTEBEREICH'` im Suchergebnis
- Wartebereich-Gruppe erscheint nur wenn ≥1 eigener Wartebereich-Treffer vorhanden
- Aktive-Anfrage-Check: `GET /api/reservations?status=PENDING` beim Öffnen des „Belegung vormerken" Abschnitts laden (einmalig); lokale Map `azr_id → true`; nur eigene ausgehende Anfragen geprüft
- Aktive-Anfrage-Hinweis: Gelbes Warning-Chip im Treffer + gelbes Banner bei Auswahl — nicht blockierend
- Fremdpersonen-Hinweis: blaues Info-Banner bei Auswahl einer Person mit `location_id !== locationId` — nicht blockierend, Nutzer kann trotzdem bestätigen
- Warteplatz-Datum: `belegung_start = heute`, `belegung_ende = heute + 30 Tage` (vorausgefüllt, editierbar)
- Freie Wartebereich-Betten: `GET /api/locations/{locationId}/bed-status` → Betten mit `room_type='WARTEBEREICH'` und `status='FREI'`, aufsteigend nach Bettnummer → erstes nehmen
- Warteplatz-Anlage: `POST /api/beds/{bed_id}/occupancy`; danach bei ausgewählten Labels: `PATCH /api/occupancy/{occ_id}/labels`; kein neues Backend-Endpoint
- Nachdem Warteplatz angelegt: `bedAssignment[idx]` mit `azr_id`, `geschlecht`, `searchFound=true` befüllen → Anfrage-Flow läuft normal weiter

**Ask First:**
- Wenn kein freies Wartebereich-Bett gefunden: Fehlermeldung „Kein freier Warteplatz verfügbar — Person bitte manuell einbuchen" und Flow abbrechen. Soll alternativ ein Notbett angeboten werden? → **Standard: Fehlermeldung, kein Notbett-Fallback**

**Never:**
- Bestehende `hasPerson`-Pfade (Verlegungsanfrage-Wizard) ändern
- Neuen Backend-Endpoint hinzufügen
- Die eigentliche Anfrage blockieren wegen aktivem-Anfrage-Hinweis oder Fremdpersonen-Hinweis (nur warnen)
- Den Bestätigungs-Dialog blockieren wenn Labels nicht gesetzt wurden (Labels optional)

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Treffer: eigene Einrichtung Wartebereich | `location_id === locationId`, `room_type === 'WARTEBEREICH'` | Gruppe „Wartebereich — eigene Einrichtung" zuerst, grüner Linker Rand, Raumname sichtbar | — |
| Treffer: eigene Einrichtung anderer Raum | `location_id === locationId`, `room_type !== 'WARTEBEREICH'` | Gruppe „Eigene Einrichtung" zweite, blauer Rand | — |
| Treffer: Fremdeinrichtung | `location_id !== locationId` | Gruppe „Andere Einrichtungen" letzte, grauer Rand | — |
| Person hat aktive PENDING-Anfrage | `azr_id` in `pendingReservationAzrIds` | Gelbes `⚠ Anfrage läuft`-Chip im Treffer; bei Auswahl: gelbes Banner | — |
| Fremdperson ausgewählt | `foundLocationId !== locationId` | Blaues Info-Banner unter Suchfeld: „Person ist in Fremdeinrichtung — Verlegung muss abgestimmt sein" | — |
| Suche liefert kein Ergebnis | `searchResults = []` nach Suche | Button „Warteplatz anlegen" statt Ergebnisliste; „Option bestätigen" disabled | — |
| Warteplatz anlegen: freies Bett vorhanden | `bed-status` hat FREI WARTEBEREICH-Bett | Inline-Form mit vorausgefüllter AZR-ID, Geschlecht-Picker, Label-Picker, Datum | — |
| Warteplatz anlegen: kein freies Bett | Alle WARTEBEREICH-Betten BELEGT | Fehlermeldung „Kein freier Warteplatz" — Form nicht geöffnet | — |
| Warteplatz-POST fehlschlägt | 409/422 vom Backend | Fehlermeldung anzeigen, Form bleibt offen | catch → Snackbar |
| Mehrfach-Belegungen: selbe AZR zweimal | Duplikat-Treffer in `searchResults` | Composite-Key `azr_id-pi`, beide sichtbar, `room_name` unterschiedlich | — |

</frozen-after-approval>

## Code Map

- `frontend/src/pages/SuggestionWizard.tsx` — Einzige zu ändernde Datei; enthält Trefferliste (Z. ~1100–1150), Suche (Z. ~290–325), bestätigen-Button (Z. ~870–880), bedAssignments-State (Z. ~142–149)
- `frontend/src/auth/KeycloakProvider.tsx` — liefert `locationId`; read-only (kein `locationName` verfügbar)

Relevante Backend-Endpoints (keine Änderungen):
- `GET /api/occupants/search?q=...` — gibt bereits `location_id`, `room_type`, `room_name`, `bed_id` zurück (TS-Interface lückenhaft)
- `GET /api/reservations?status=PENDING` — eigene PENDING-Anfragen der Einrichtung
- `GET /api/locations/{locationId}/bed-status` — Bett-Status inkl. `room_type`; `FREI`/`BELEGT`/`VORGEMERKT`
- `POST /api/beds/{bed_id}/occupancy` — Belegung anlegen
- `PATCH /api/occupancy/{occupancy_id}/labels` — Labels nachträglich setzen

## Tasks & Acceptance

**Execution:**

- [x] `frontend/src/pages/SuggestionWizard.tsx` -- `OccupantSearchResult`-Interface erweitern: `location_id: string`, `room_type: string`, `room_name: string` hinzufügen (Backend gibt diese bereits zurück) -- verhindert TypeScript-Fehler in allen nachfolgenden Tasks

- [x] `frontend/src/pages/SuggestionWizard.tsx` -- `bedAssignments`-State-Typ: `foundLocationId?: string` hinzufügen -- wird für Fremdpersonen-Check nach Auswahl benötigt

- [x] `frontend/src/pages/SuggestionWizard.tsx` -- State `pendingReservationAzrIds: Set<string>` anlegen; `useEffect` beim Mount: `GET /api/reservations?status=PENDING` laden, `new Set(res.map(r => r.azr_id))` daraus bauen -- einmaliger Load, keine On-Demand-Abfrage

- [x] `frontend/src/pages/SuggestionWizard.tsx` -- Trefferliste-Render (Z. ~1113ff): `searchResults` in 3 Gruppen aufteilen: `ownWartebereich` (location_id===locationId && room_type==='WARTEBEREICH'), `ownOther` (location_id===locationId && rest), `external` (rest); jede Gruppe mit Abschnittsüberschrift (`Typography variant="caption"`) und farbigem linkem Rand (grün / blau / grau); jede Zeile: Geschlecht-Chip, Labels-Chips, `room_name`, `belegung_ende`-Datum (DE-Locale); `⚠ Anfrage läuft`-Chip (warning-Farbe) wenn `pendingReservationAzrIds.has(person.azr_id)` -- Gruppen nur rendern wenn Einträge vorhanden

- [x] `frontend/src/pages/SuggestionWizard.tsx` -- Trefferliste-Click-Handler: `foundLocationId: person.location_id` in `bedAssignments`-Update aufnehmen -- wird für Fremdpersonen-Banner benötigt

- [x] `frontend/src/pages/SuggestionWizard.tsx` -- Nach Trefferliste-Auswahl: wenn `a.foundLocationId && a.foundLocationId !== locationId` → blaues Info-Banner unter dem Suchfeld für dieses Bett anzeigen: „ℹ Diese Person ist in einer Fremdeinrichtung eingebucht — eine Verlegung muss vorab abgestimmt sein."; wenn `pendingReservationAzrIds.has(a.azr_id)` → zusätzlich gelbes Warning-Banner: „⚠ Für diese Person läuft bereits eine Anfrage" -- beide Banner dismissbar, kein Blockieren

- [x] `frontend/src/pages/SuggestionWizard.tsx` -- Wenn `searchDone && !searchFound && searchResults.length === 0`: Statt Trefferliste Button `Warteplatz anlegen für AZR {azr_id}` anzeigen; `Option bestätigen` bleibt disabled bis Warteplatz angelegt oder manuell Person gesucht; beim Button-Klick: `GET /api/locations/{locationId}/bed-status` abrufen, erstes FREI WARTEBEREICH-Bett suchen; kein Treffer → Snackbar „Kein freier Warteplatz verfügbar"; Treffer → Warteplatz-Inline-Form aufklappen (Accordion o.ä.) -- keine neue Route/Dialog-Komponente

- [x] `frontend/src/pages/SuggestionWizard.tsx` -- Warteplatz-Inline-Form: Felder `geschlecht` (Select M/W/D, Pflicht), Labels (MultiSelect aus Labelkatalog, optional), `belegung_start` (Date, default heute, read-only), `belegung_ende` (Date, default heute+30, editierbar); Button „Warteplatz bestätigen"; beim Klick: `POST /api/beds/{freeBedId}/occupancy` mit `azr_id`, `geschlecht`, `belegung_start`, `belegung_ende`; bei Erfolg + Labels: `PATCH /api/occupancy/{occ_id}/labels`; danach `bedAssignments[idx]` aktualisieren: `azr_id`, `geschlecht`, `searchFound=true`, `searchDone=true`, `foundLocation=locationName aus bed-status` -- bei POST-Fehler: Snackbar, Form bleibt offen

**Acceptance Criteria:**

- Given Suche liefert Treffer aus eigener Einrichtung und Fremdeinrichtung, when Trefferliste angezeigt, then eigene Einrichtung erscheint vor Fremdeinrichtungen, Wartebereich-Treffer ganz oben
- Given Person hat aktive PENDING-Anfrage, when in Trefferliste angezeigt, then `⚠ Anfrage läuft`-Chip sichtbar und bei Auswahl gelbes Banner
- Given Person aus Fremdeinrichtung ausgewählt, when bedAssignment aktualisiert, then blaues Info-Banner erscheint unterhalb des Suchfeldes, „Option bestätigen" nicht blockiert
- Given Suche liefert kein Ergebnis, when `searchDone`, then „Warteplatz anlegen"-Button sichtbar, „Option bestätigen" disabled
- Given Freies WARTEBEREICH-Bett vorhanden und Warteplatz-Form ausgefüllt, when „Warteplatz bestätigen" geklickt, then Belegung angelegt, Inline-Form verschwindet, Suchfeld zeigt AZR-ID, „Option bestätigen" enabled
- Given Kein freies WARTEBEREICH-Bett, when „Warteplatz anlegen" geklickt, then Snackbar „Kein freier Warteplatz verfügbar", keine Form
- Given `!hasPerson`-Pfad mit gefundener Person, when „Option bestätigen" geklickt, then Verlegungsanfrage gesendet wie bisher (kein Regressions-Fehler)

## Design Notes

**Gruppen-Rendering:**
Statt einer flachen Liste drei MUI-`Box`-Abschnitte mit `<Divider>`-Trenner. Jede Gruppe hat eine `Typography variant="overline"` Überschrift (z.B. „Wartebereich — eigene Einrichtung", „Eigene Einrichtung", „Andere Einrichtungen"). Gruppe nur rendern wenn ≥1 Treffer. Farbiger `borderLeft: '3px solid'` als visuelles Muster (grün #2e7d32, blau #1565c0, grau #757575).

**Warteplatz-Inline-Form:**
Kein Modal-Dialog — mit MUI `Collapse` oder `Box` unterhalb des Suchfeldes des jeweiligen Betts aufklappen. Hält den Kontext des Bett-Assignments sichtbar. Geschlecht-Pflichtfeld weil für OccupancyCreate erforderlich.

**locationName im Warteplatz:**
`useKeycloak()` gibt keinen `locationName` zurück. Den Namen aus der `bed-status`-Antwort lesen (`room.location_name` falls vorhanden) oder weglassen — kein neuer API-Call nur für den Namen.

## Verification

**Commands:**
- `cd frontend && npx tsc --noEmit` — expected: 0 TypeScript-Fehler

**Manual checks:**
- Suche mit bekannter AZR aus eigenem Wartebereich → Gruppe 1, grüner Rand, Labels sichtbar
- Suche mit bekannter AZR aus Fremdeinrichtung → Gruppe 3, blauer Info-Banner bei Auswahl
- Suche mit AZR einer Person mit aktiver PENDING-Anfrage → gelber Chip + Banner
- Suche mit unbekannter AZR (keine Treffer) → „Warteplatz anlegen"-Button, Form aufklappbar
- Warteplatz anlegen: Geschlecht wählen, Labels auswählen, bestätigen → Snackbar-Erfolg, `Option bestätigen` aktiv
- Gesamter `!hasPerson`-Flow (Bettvorschlag → Person suchen → bestätigen) funktioniert wie bisher

## Suggested Review Order

**Feature — Gruppierte Trefferliste, Kontextwarnungen & Auto-Warteplatz**

1. Interface extension: `OccupantSearchResult` + `BedAssignment`
   [`SuggestionWizard.tsx` — OccupantSearchResult & BedAssignment types]

2. State: `pendingReservationAzrIds` useEffect (mount, !hasPerson only)
   [`SuggestionWizard.tsx` — pendingReservationAzrIds state + useEffect]

3. Grouped Trefferliste render (ownWb / ownOther / external, locationId-null guard)
   [`SuggestionWizard.tsx:1197–1253`]

4. Banners: Fremdpersonen (blue) + aktive Anfrage (yellow) — both with locationId guard + trim
   [`SuggestionWizard.tsx:1185–1194`]

5. No-results section: „Warteplatz anlegen"-Button + Inline-Form (fields disabled when loading)
   [`SuggestionWizard.tsx:1256–1325`]

6. handleOpenWarteplatz — bed-status fetch, first FREI WARTEBEREICH bed
   [`SuggestionWizard.tsx` — handleOpenWarteplatz]

7. handleSubmitWarteplatz — POST occupancy + PATCH labels + bedAssignment update
   [`SuggestionWizard.tsx` — handleSubmitWarteplatz]

8. Submit-Button disabled guard: `searchDone && !searchFound`
   [`SuggestionWizard.tsx` — confirm Button disabled prop]

## Spec Change Log
