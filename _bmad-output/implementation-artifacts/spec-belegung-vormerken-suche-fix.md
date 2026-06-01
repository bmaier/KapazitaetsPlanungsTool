---
title: 'Belegung vormerken — AZR-Suche Fix + Trefferliste + Bett-Labels'
type: 'bugfix'
created: '2026-06-01'
status: 'done'
baseline_commit: '60d5cb88b920642d9a586111034a25c9ff7a403d'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Im Dialog "Belegung vormerken" (SuggestionWizard) meldet die AZR-Suche fälschlich "Person gefunden", wenn die Eingabe nur als Teilstring im AZR vorkommt (`?? res[0]` Fallback). Zusätzlich fehlt eine selektierbare Trefferliste bei Teiltreffern, und im Bestätigungs-Dialog werden die Bett-Labels des Zielbetts nicht angezeigt — obwohl die API sie bereits liefert.

**Approach:** (1) `?? res[0]`-Fallback entfernen — "gefunden" nur bei exaktem AZR-Match. (2) Bei Teiltreffern ohne exakten Match eine selektierbare Liste mit Person-Labels und aktuellem Standort rendern. (3) `bed_labels` im `BedOption`-Interface ergänzen und im Bestätigungs-Panel anzeigen. Kein Backend-Change erforderlich.

## Boundaries & Constraints

**Always:**
- Alle bestehenden Code-Pfade (`hasPerson`, Verlegungsanfrage-Modus, Gruppensuche) bleiben **exakt unverändert** — kein Refactoring, kein Umbenennen
- Exact-Match-Vergleich: case-insensitive `azr_id.toLowerCase() === input.toLowerCase()`, kein Trimmen von Sonderzeichen
- Trefferliste zeigt: `azr_id`, `occ_labels` (als Chips/Tags), `location_name` (aktueller Standort der Person)
- `bed_labels` in der Trefferliste der Person-Suche: **nicht** anzeigen — das sind die Labels des aktuellen Betts der Person, nicht des Zielbetts; es würde verwirren
- `bed_labels` des **Zielbetts** (aus `BedOption`) anzeigen — diese sind relevant für den Sachbearbeiter
- Selektieren aus der Trefferliste setzt `foundPerson` und leert `searchResults` (Liste verschwindet)

**Ask First:**
- Soll bei genau einem Teiltreffern (kein exakter Match) die Person automatisch selektiert werden, oder immer die Liste zeigen? → Standard: **immer Liste zeigen**, auch bei einem Treffer — verhindert erneuten Bug durch "auto-select"

**Never:**
- Backend-Änderungen — API liefert alle Daten bereits
- Änderungen an `hasPerson`-Pfad, Verlegungsanfrage-Dialog, Gruppen-Modus
- Neue Abhängigkeiten / Packages hinzufügen
- `?? res[0]` in anderer Form wiederherstellen

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Exakter AZR-Match | Eingabe "AZR-2024-001", API gibt genau diesen zurück | `foundPerson` gesetzt, kein Listenrendering, Bestätigungs-Panel erscheint | — |
| Exakter Match unter mehreren Treffern | Eingabe "AZR-2024-001", API gibt mehrere inkl. exaktem zurück | Exakter Match genommen, Liste **nicht** gezeigt | — |
| Teiltreff(er), kein exakter Match | Eingabe "AZR", API gibt ≥1 Person zurück | Trefferliste gerendert, `foundPerson` leer, kein "gefunden"-Toast | — |
| Kein Treffer | Eingabe "AZR-9999-ZZZ", API gibt leere Liste zurück | "Nicht gefunden" Zustand (bestehend), kein `foundPerson` | — |
| Klick in Trefferliste | User wählt Person aus Liste | `foundPerson` = Gewählte, Liste verschwindet, Bestätigungs-Panel erscheint | — |
| Neue Suche nach Auswahl | User überschreibt AZR-Feld | Bisherige `foundPerson` und `searchResults` leeren | — |

</frozen-after-approval>

## Code Map

- `frontend/src/pages/SuggestionWizard.tsx` — Einzige zu ändernde Datei; enthält AZR-Suchlogik, `BedOption`-Interface, Render-Logik des Dialogs

Relevante Stellen (alle in SuggestionWizard.tsx):
- **Zeile 42–49**: `BedOption`-Interface — `bed_labels: string[]` fehlt
- **Zeile 291–292**: `?? res[0]`-Fallback — Bug-Ursprung
- **Zeile ~300**: State-Variablen für `foundPerson` — hier `searchResults`-State ergänzen
- **Zeile ~700–850**: Render des Bestätigungs-Panels — hier Bett-Label-Anzeige einfügen
- **Zeile ~650**: AZR-Suchfeld und Ergebnisanzeige — hier Trefferliste einfügen

API-Referenz (`GET /api/occupants/search?q=...` response-Shape pro Item):
```json
{ "occupant_id": "...", "azr_id": "...", "occ_labels": ["..."],
  "location_name": "...", "room_name": "...", "bed_number": "...",
  "bed_labels": ["..."], "room_labels": ["..."] }
```

API-Referenz (`GET /api/suggestions/{loc_id}/beds` response-Shape pro Item, bereits in `BedOption`):
```json
{ "bed_id": "...", "room_id": "...", "bed_number": "...", "room_name": "...",
  "room_labels": ["..."], "bed_labels": ["..."] }
```

## Tasks & Acceptance

**Execution:**

- [x] `frontend/src/pages/SuggestionWizard.tsx` -- `BedOption`-Interface: `bed_labels: string[]` ergänzen (analog zu `room_labels`) -- API liefert das Feld bereits; ohne Interface-Erweiterung kein Zugriff im Render

- [x] `frontend/src/pages/SuggestionWizard.tsx` -- `OccupantSearchResult`-Interface definiert + `searchResults: OccupantSearchResult[]` in `BedAssignment` ergänzt; Initialisierung in `handleOpenConfirm` mit `searchResults: []` -- hält Teiltrefferliste pro Bett-Slot zwischen Suche und Auswahl

- [x] `frontend/src/pages/SuggestionWizard.tsx` -- `searchPersonForBed`: `?? res[0]` entfernt; exakter Match → `searchFound: true`; Teiltreffer ohne Match → `searchResults: res, searchFound: false`; kein Treffer → leere Liste -- exakter Match ist die einzige sichere Zuweisung

- [x] `frontend/src/pages/SuggestionWizard.tsx` -- Trefferliste gerendert: `assignment.searchDone && !assignment.searchFound && assignment.searchResults.length > 0` → clickbare Box-Liste mit `azr_id`, `location_name`, `occ_labels`-Chips; Klick setzt Person in `BedAssignment` und leert `searchResults` -- Sachbearbeiter sieht alle Kandidaten auf einen Blick

- [x] `frontend/src/pages/SuggestionWizard.tsx` -- Bestätigungs-Panel (alle 3 Varianten: !hasPerson, hasPerson Einzeln, hasPerson Gruppe): `bed_labels`-Chips direkt nach `room_labels`-Chips eingefügt; nur wenn `bed_labels.length > 0` -- Sachbearbeiter sieht vollständige Bett-Klassifizierung vor der Buchung

- [x] `frontend/src/pages/SuggestionWizard.tsx` -- AZR-Input onChange: `searchResults: []` beim Tippen zurücksetzen -- verhindert inkonsistenten Zustand nach erneuter Eingabe

**Acceptance Criteria:**

- Given das AZR-Feld enthält "A" und der User klickt Suchen, when die API mehrere Treffer zurückgibt ohne exakten Match, then wird KEINE "Person gefunden"-Meldung gezeigt und stattdessen eine Trefferliste gerendert
- Given die Trefferliste ist sichtbar, when der User einen Eintrag anklickt, then wird die Person als `foundPerson` gesetzt und die Liste ausgeblendet
- Given eine exakte AZR wird eingegeben ("AZR-2024-001") und die API liefert diesen Treffer, when der User sucht, then wird direkt "Person gefunden" angezeigt ohne Trefferliste
- Given ein Bestätigungs-Panel für ein Zielbett mit `bed_labels`, when der Dialog geöffnet ist, then sind die Bett-Labels sichtbar
- Given alle bestehenden Tests und Flows (hasPerson, Verlegungsanfrage, Gruppen-Modus), when diese genutzt werden, then funktionieren sie identisch wie vor der Änderung

## Design Notes

**Warum immer Liste, auch bei einem Teiltreffern:**
Ein einziger Teiltreffern wird nicht auto-selektiert, weil das exakt der Bug-Mechanismus war (`?? res[0]`). Nur der User darf entscheiden — auch wenn es nur eine Kandidatin gibt. Die List-Interaktion ist minimal (ein Klick) und stellt sicher, dass der Sachbearbeiter bewusst wählt.

**`OccupantSearchResult` Typ-Definition:**
Da der Typ nur lokal in SuggestionWizard verwendet wird (kein shared types-File), kann er als lokales Interface direkt in der Datei definiert werden:
```typescript
interface OccupantSearchResult {
  occupant_id: string
  azr_id: string
  occ_labels: string[]
  location_name: string
}
```
Felder die nicht gebraucht werden (`room_name`, `bed_number`, etc.) müssen nicht im Interface stehen — TypeScript lässt überzählige Felder aus der API-Response durch.

## Verification

**Commands:**
- `cd frontend && npm run type-check` -- expected: 0 TypeScript-Fehler (kein `tsc`-Error auf `bed_labels` oder neuen State-Variablen)
- `cd frontend && npm run build` -- expected: Build erfolgreich ohne Warnings zu neuen Typen

**Manual checks (if no CLI):**
- AZR-Feld: "A" eingeben → Suchen → Trefferliste erscheint, kein "gefunden"-Toast
- AZR-Feld: exakte AZR eingeben → Suchen → direkt "gefunden", keine Liste
- Bestätigungs-Panel: Bett mit Labels wählen → `bed_labels` sichtbar im Panel
- hasPerson-Pfad unverändert: Seite mit vorhandener Person öffnen → Dialog zeigt Person ohne Suchfeld

## Spec Change Log

## Suggested Review Order

**Bug Fix — Kern-Logik**

- Drei-Zweig-Dispatch: exakter Match, Teiltreffer-Liste, kein Treffer — Bug-Quelle entfernt
  [`SuggestionWizard.tsx:296`](../../frontend/src/pages/SuggestionWizard.tsx#L296)

- API-Response-Typ `OccupantSearchResult` ersetzt lokalen inline-type in `searchPersonForBed`
  [`SuggestionWizard.tsx:51`](../../frontend/src/pages/SuggestionWizard.tsx#L51)

**State-Architektur**

- `searchResults: OccupantSearchResult[]` im `BedAssignment`-Typ — Kandidatenliste pro Bett-Slot
  [`SuggestionWizard.tsx:147`](../../frontend/src/pages/SuggestionWizard.tsx#L147)

**Trefferliste — UI**

- Render-Gate: `searchDone && !searchFound && searchResults.length > 0` — nur bei Teiltreffern
  [`SuggestionWizard.tsx:1110`](../../frontend/src/pages/SuggestionWizard.tsx#L1110)

- Click-Handler: setzt `azr_id`, Labels, `searchFound: true`, leert `searchResults`
  [`SuggestionWizard.tsx:1128`](../../frontend/src/pages/SuggestionWizard.tsx#L1128)

- onChange AZR-Feld: `searchResults: []` — verhindert veraltete Liste bei neuer Eingabe
  [`SuggestionWizard.tsx:1065`](../../frontend/src/pages/SuggestionWizard.tsx#L1065)

**Bett-Labels — Bestätigungs-Dialog**

- `BedOption.bed_labels: string[]` — neues Interface-Feld für Zielbett-Klassifizierung
  [`SuggestionWizard.tsx:49`](../../frontend/src/pages/SuggestionWizard.tsx#L49)

- Gruppen-Panel: `bed_labels`-Chips nach `room_labels` pro Bett/Person-Zeile
  [`SuggestionWizard.tsx:969`](../../frontend/src/pages/SuggestionWizard.tsx#L969)

- Einzelperson-Panel: `bed_labels`-Chips nach `room_labels` pro Zielbett
  [`SuggestionWizard.tsx:1022`](../../frontend/src/pages/SuggestionWizard.tsx#L1022)

- !hasPerson-Panel (Belegung vormerken): `bed_labels`-Chips nach `room_labels`
  [`SuggestionWizard.tsx:1056`](../../frontend/src/pages/SuggestionWizard.tsx#L1056)

