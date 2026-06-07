---
title: 'Bettsuche — Zeitraum-Vorbelegung aus Verlegungskontext'
type: 'feature'
created: '2026-06-07'
status: 'done'
baseline_commit: 'ab87386'
context: ['_bmad-output/project-context.md', 'spec-belegung-vormerken-ziel-b.md']
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Wenn ein Sachbearbeiter die Bettsuche aus dem Verlegungskontext heraus öffnet (Klick auf "Verlegen" bei einer belegten Person), werden Startdatum und Enddatum nicht automatisch befüllt. Der SB muss sie manuell eingeben, obwohl beide Werte bereits bekannt sind: Start = morgen (Transfertermin frühestens ab morgen) und Ende = das bestehende `belegung_ende` der Person.

**Approach:** In `SuggestionWizard.tsx`: URL-Parameter `&ende={belegung_ende}` wird von `Drilldown.tsx` beim Öffnen der Bettsuche angehängt. Im Wizard wird `preEnde` aus den URL-Parametern gelesen. Wenn eine Person (`azrId`) im URL angegeben ist, wird `initStart = tomorrow` gesetzt. `initEnde = preEnde` wenn `preEnde > initStart`, sonst `in30` (30 Tage ab heute). Die bestehende `handleStartChange`-Funktion verhindert, dass Ende ≤ Start ist.

## Boundaries & Constraints

**Always:**
- B-01: Wenn `azrId`-URL-Parameter vorhanden: `start = tomorrow` (ISO-Datum des Folgetags) — nicht heute.
- B-02: `ende = preEnde` wenn `preEnde > initStart`; sonst `ende = in30` (Fallback).
- B-03: `ende` muss immer mindestens 1 Tag nach `start` liegen — `handleStartChange` erzwingt dies automatisch.
- B-04: Einzelperson-Verlegung: `Drilldown.tsx openVerlegung()` hängt `&ende={bed.belegung_ende}` an wenn `belegung_ende > tomorrow`.
- B-05: Gruppen-Verlegung: `Drilldown.tsx openGruppenVerlegung()` berechnet das Minimum-`belegung_ende` aller ausgewählten Betten und hängt `&ende={minEnde}` an wenn `minEnde > tomorrow`.
- B-06: Start-Feld-Min: `inputProps={{ min: hasPerson ? tomorrow : today }}` — SB kann nicht in der Vergangenheit starten wenn Person angegeben.

**Never:**
- Kein automatisches Setzen von Endedatum vor Startdatum.
- Kein Überschreiben manueller Eingaben nach dem ersten Render.

## I/O

**URL-Parameter die SuggestionWizard liest:**
- `azrId` — AZR-ID der Person (optional, setzt `hasPerson = true`)
- `geschlecht` — vorausgefülltes Geschlecht
- `cross=1` — Cross-Location-Suche vorgewählt
- `ende` — vorausgefülltes Enddatum (aus `belegung_ende` der Quell-Belegung)
- `group` — Gruppen-Verlegung (komma-getrennte `azrId:geschlecht`-Paare)

**Startdatum-Logik:**
```
hasPerson ? tomorrow : today
```

**Enddatum-Logik:**
```
preEnde && preEnde > initStart ? preEnde : in30
```

</frozen-after-approval>

## Code Map

- `frontend/src/pages/SuggestionWizard.tsx` — `preEnde = searchParams.get('ende') ?? ''`
- `frontend/src/pages/SuggestionWizard.tsx` — `const tomorrow`, `initStart`, `initEnde` Berechnungslogik
- `frontend/src/pages/SuggestionWizard.tsx` — `useState(initStart)` für Start, `useState(initEnde)` für Ende
- `frontend/src/pages/SuggestionWizard.tsx:handleStartChange` — verhindert Ende ≤ Start
- `frontend/src/pages/SuggestionWizard.tsx` — Start-Feld `inputProps={{ min: hasPerson ? tomorrow : today }}`
- `frontend/src/pages/Drilldown.tsx:openVerlegung` — hängt `&ende=${bed.belegung_ende}` an (wenn > tomorrow)
- `frontend/src/pages/Drilldown.tsx:openGruppenVerlegung` — berechnet `minEnde` aus allen ausgewählten Betten + hängt `&ende=${minEnde}` an

## Tasks & Acceptance

**Execution:**
- [x] `SuggestionWizard.tsx` — `preEnde` aus URL-Parametern lesen
- [x] `SuggestionWizard.tsx` — `initStart`/`initEnde` korrekt berechnen (hasPerson → tomorrow; preEnde als Fallback)
- [x] `SuggestionWizard.tsx` — `handleStartChange`: nur Ende verschieben wenn es ≤ Start wird (kein aggressives Reset)
- [x] `SuggestionWizard.tsx` — Start-Feld `min`-Attribut je nach `hasPerson`
- [x] `Drilldown.tsx` — `openVerlegung`: `&ende=` Parameter anhängen
- [x] `Drilldown.tsx` — `openGruppenVerlegung`: `minEnde` berechnen + `&ende=` anhängen

**Acceptance Criteria:**
- Öffnen von Bettsuche per Klick auf "Verlegen" (mit `azrId`): Start = morgen, Ende = `belegung_ende` der Person.
- Öffnen ohne Person (Cross-Location ohne azrId): Start = heute, Ende = in 30 Tagen.
- Manuelle Änderung des Startdatums: Ende wird nur dann auto-korrigiert wenn es ≤ Start liegt.
- Gruppen-Verlegung: Ende = Minimum-`belegung_ende` aller ausgewählten Personen.
- Enddatum kann nie vor Startdatum liegen.
