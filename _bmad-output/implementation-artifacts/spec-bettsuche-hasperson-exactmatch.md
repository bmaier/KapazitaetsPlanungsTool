---
title: 'Bettsuche hasPerson — handleOpenConfirm Exact-Match + geschlecht-Fallback'
type: 'bugfix'
created: '2026-06-02'
status: 'done'
baseline_commit: '4e08fd5'
context:
  - spec-belegung-vormerken-suche-fix.md   # Vorgänger-Story (9-1) — selbe Komponente
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Im SuggestionWizard werden bei der Bestätigung im `hasPerson`-Pfad die Person-Labels falsch geladen, wenn die API mehrere Treffer zurückgibt. `handleOpenConfirm` nutzt weiterhin `res.find(...) ?? res[0]` — bei keinem exakten Match wird der erste API-Treffer als Fallback genommen und dessen `occ_labels` angezeigt. Das kann Labels einer anderen Person zeigen. Zweites Problem: `person.geschlecht ?? a.geschlecht` fängt leere Strings ("") nicht ab — der Nullish-Coalescing-Operator greift nur bei null/undefined.

**Approach:** (1) `?? res[0]`-Fallback in `handleOpenConfirm` für den Einzelperson-Pfad (Z. 283) und den Gruppen-Pfad (Z. 274) entfernen — `occ_labels` nur setzen wenn exakter AZR-Match vorliegt. (2) `person.geschlecht ?? a.geschlecht` in `searchPersonForBed` (Z. 301) und im Trefferliste-Click-Handler durch `person.geschlecht || a.geschlecht` ersetzen. Kein Backend-Change erforderlich.

## Boundaries & Constraints

**Always:**
- Exact-Match-Vergleich: `r.azr_id === person.azr_id` (case-sensitive, da `person.azr_id` aus URL-Param kommt und API-Rückgabe identisch sein sollte)
- Wenn kein exakter Match gefunden: `occ_labels` = `[]` (leeres Array), kein Fallback auf anderen Treffer — falsche Labels sind schlimmer als keine Labels
- Gruppen-Pfad (`handleOpenConfirm`, Z. 274): gleiches Verhalten — nur exakter Match befüllt `groupPersonLabels[person.azr_id]`
- `|| a.geschlecht`-Fallback gilt für alle Stellen wo `geschlecht` aus einer API-Antwort übernommen wird

**Ask First:**
- Soll bei fehlendem Label-Match ein visueller Hinweis ("Labels nicht abrufbar") erscheinen oder einfach keine Chips? → Standard: **keine Chips, kein Hinweis** — Labels sind optionale Zusatzinfo, ihr Fehlen ist kein Fehler

**Never:**
- Backend-Änderungen
- Änderungen am `!hasPerson`-Pfad (searchPersonForBed, Trefferliste) — Scope von Story 9-1, korrekt
- Neue UI-Zustände oder State-Variablen — nur Logik in bestehenden Funktionen anpassen
- Den Confirm-Dialog blockieren wenn Labels nicht geladen werden können — Dialog muss immer öffnen

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Einzelperson, exakter AZR-Match | URL `?azrId=AZR-2024-001`, API gibt genau diesen zurück | `confirmPersonLabels` = `occ_labels` der Person, Dialog öffnet | — |
| Einzelperson, kein exakter Match | URL `?azrId=AZR-2024-001`, API gibt andere Treffer zurück | `confirmPersonLabels` = `[]`, Dialog öffnet ohne Labels | — |
| Einzelperson, leere API-Antwort | URL `?azrId=AZR-9999`, API gibt `[]` zurück | `confirmPersonLabels` = `[]`, Dialog öffnet | catch → `setConfirmPersonLabels([])` |
| Einzelperson, API-Fehler | Netzwerkfehler | `confirmPersonLabels` = `[]`, Dialog öffnet | catch → `setConfirmPersonLabels([])` |
| Gruppenverlegung, alle exakt gefunden | URL `?group=AZR-1:M,AZR-2:W`, beide exakt in API | `groupPersonLabels` = `{AZR-1: [...], AZR-2: [...]}` | — |
| Gruppenverlegung, eine Person kein Match | URL `?group=AZR-1:M,AZR-2:W`, AZR-2 nur Teiltreffer | `groupPersonLabels` = `{AZR-1: [...]}` — AZR-2 fehlt im Map | per-Person catch → kein Eintrag |
| `geschlecht` als leerer String von API | `exact.geschlecht = ""` | Fallback auf `a.geschlecht` (vorheriger Wert) | — |
| `geschlecht` als `null`/`undefined` | `exact.geschlecht = null` | Fallback auf `a.geschlecht` | — |

</frozen-after-approval>

## Code Map

- `frontend/src/pages/SuggestionWizard.tsx` — Einzige zu ändernde Datei

Relevante Stellen:

- **Zeile 274**: `handleOpenConfirm` Gruppen-Pfad — `res.find(...) ?? res[0]` → nur `res.find(...)`, kein Fallback
- **Zeile 283**: `handleOpenConfirm` Einzelperson-Pfad — `res.find(...) ?? res[0]` → nur `res.find(...)`, kein Fallback
- **Zeile 301**: `searchPersonForBed` — `exact.geschlecht ?? a.geschlecht` → `exact.geschlecht || a.geschlecht`
- **Zeile ~1124**: Trefferliste-Click-Handler — `person.geschlecht ?? a.geschlecht` → `person.geschlecht || a.geschlecht`

## Tasks & Acceptance

**Execution:**

- [x] `frontend/src/pages/SuggestionWizard.tsx` -- `handleOpenConfirm` Einzelperson-Pfad (Z. 283): `?? res[0]`-Fallback entfernen; `found = res.find(r => r.azr_id === currentPerson.azr_id)` ohne Fallback; `setConfirmPersonLabels((found?.occ_labels as string[]) ?? [])` bleibt unverändert -- verhindert falsche Labels bei Teiltreffern

- [x] `frontend/src/pages/SuggestionWizard.tsx` -- `handleOpenConfirm` Gruppen-Pfad (Z. 274): `?? res[0]`-Fallback entfernen; `found = res.find(r => r.azr_id === person.azr_id)` ohne Fallback; `if (found)` Gate bleibt — kein Map-Eintrag für nicht exakt gefundene Person -- konsistentes Verhalten mit Einzelpfad

- [x] `frontend/src/pages/SuggestionWizard.tsx` -- `searchPersonForBed` (Z. 301): `exact.geschlecht ?? a.geschlecht` → `exact.geschlecht || a.geschlecht` -- leerer String wird korrekt als falsy behandelt

- [x] `frontend/src/pages/SuggestionWizard.tsx` -- Trefferliste-Click-Handler (Z. ~1124): `person.geschlecht ?? a.geschlecht` → `person.geschlecht || a.geschlecht` -- gleiche Korrektur für den Click-Pfad

**Acceptance Criteria:**

- Given `?azrId=AZR-2024-001` und API liefert Treffer mit anderen AZR-IDs aber nicht exakt "AZR-2024-001", when Bestätigungs-Dialog geöffnet wird, then werden KEINE Labels angezeigt (nicht die Labels eines anderen Treffers)
- Given `?azrId=AZR-2024-001` und API liefert exakt "AZR-2024-001" mit Labels, when Bestätigungs-Dialog geöffnet wird, then werden diese Labels korrekt angezeigt
- Given Gruppenverlegung mit zwei Personen, eine davon hat keinen exakten API-Match, when Bestätigungs-Dialog geöffnet wird, then hat nur die exakt gefundene Person Labels im Dialog
- Given API-Antwort `geschlecht: ""`, when Person aus Trefferliste gewählt wird, then wird der Fallback-Wert aus `a.geschlecht` verwendet statt leerem String
- Given alle bestehenden Flows (!hasPerson AZR-Suche, Trefferliste, bed_labels-Anzeige), when diese genutzt werden, then funktionieren sie identisch wie vor der Änderung

## Design Notes

**Warum case-sensitive Match in handleOpenConfirm:**
`searchPersonForBed` (Story 9-1) nutzt `toLowerCase()` weil der User frei tippt. In `handleOpenConfirm` kommt `person.azr_id` aus einem URL-Param, der aus einem bekannten Datensatz stammt. API-Rückgabe und URL-Param sollten byte-identisch sein.

**Warum `||` statt `??` für geschlecht:**
`??` greift nur bei null/undefined. `||` greift auch bei `""`. Da `geschlecht` Enum-Werte (M/W/D) hat, ist `""` ungültig und soll verworfen werden.

## Verification

**Commands:**
- `cd frontend && npm run type-check` — expected: 0 TypeScript-Fehler
- `cd frontend && npm run build` — expected: Build erfolgreich

**Manual checks:**
- hasPerson Einzelpfad: URL `?azrId=AZR-TEST-001&geschlecht=M` → Bettsuche → Bestätigen → Labels nur wenn AZR exakt in der DB
- Gruppen-Pfad: URL `?group=AZR-1:M,AZR-2:W` → Labels nur für exakt gematchte Personen
- !hasPerson-Pfad: AZR-Suche → Trefferliste → Person auswählen → geschlecht korrekt (kein leerer String)

## Spec Change Log

## Suggested Review Order

**Bug Fix — handleOpenConfirm Exact-Match**

- Einzelperson-Pfad: `?? res[0]` entfernt
  [`SuggestionWizard.tsx:283`](../../frontend/src/pages/SuggestionWizard.tsx#L283)

- Gruppen-Pfad: `?? res[0]` entfernt, per-Person kein Map-Eintrag bei Mismatch
  [`SuggestionWizard.tsx:274`](../../frontend/src/pages/SuggestionWizard.tsx#L274)

**Bug Fix — geschlecht leerer String**

- searchPersonForBed: `??` → `||`
  [`SuggestionWizard.tsx:301`](../../frontend/src/pages/SuggestionWizard.tsx#L301)

- Trefferliste-Click-Handler: `??` → `||`
  [`SuggestionWizard.tsx:1124`](../../frontend/src/pages/SuggestionWizard.tsx#L1124)
