---
title: 'Geschlechts-Mismatch-Check + Batch-Intern-Verlegen + Dialog-Cleanup'
type: 'bugfix'
created: '2026-06-06'
status: 'done'
baseline_commit: 'ab8738662c6c76f319721ea66da56367f42562f5'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Bett-Zuweisung (`handleBelegen`) prüft Geschlechts-Abweichung gar nicht; `handleVerlegen` prüft korrekt, aber ohne Notbett/Warteplatz-Ausnahme; der Reservierungs-Bestätigungsdialog fehlt ganz. Multi-Select-Intern-Verlegen (Wartebereich → Standardraum) existiert nicht. Der „Neue Verlegungsanfrage"-Dialog (`ReservationCreateDialog`) zeigt keine Betten-Verfügbarkeit, validiert AZR nicht und dupliziert den SuggestionWizard nutzlos.

**Approach:** Mismatch-Check konsistent in allen drei Pfaden (Belegen, Intern-Verlegen, Reservation-Confirm) mit einheitlichem zweistufigem Muster (Info-Alert → Pflicht-Begründung, Ausnahme Notbett/Wartebereich). Batch-intern-Dialog für Multi-Select. `ReservationCreateDialog` durch `navigate('/suggestions')` ersetzen.

## Boundaries & Constraints

**Always:**
- Mismatch-Ausnahme gilt ausschließlich für `is_notbett === true` und `room_type === 'WARTEBEREICH'` / `bett_typ === 'WARTEPLATZ'`
- Zweistufig: erster Versuch → Warnung anzeigen + return; zweiter Versuch mit `mismatch===true` → Grund-Pflichtfeld sichtbar, Button disabled bis `trim().length > 0`; erst dann Speichern
- `OccupancyCreate.geschlecht_mismatch_grund` ist bereits im Backend — darauf aufbauen, nicht neu bauen
- Backend-Änderung nur für Reservation-Confirm: `Optional[str]` hinzufügen + in Audit-Payload — kein neues DB-Feld, keine Migration
- Batch-Intern-Verlegen: Ziel-Betten aus bestehender `freiBeds`-Berechnung (inkl. Geschlechts-Chip); bereits im Dialog beanspruchte Betten aus dem Pool entfernen

**Ask First:**
- Falls der Batch-Intern-Dialog bei partiellen Fehlern (3 Personen, 1 POST schlägt fehl) abbricht oder partial-commit erlaubt — Standard: Abbruch bei erstem Fehler, Fehler-Snackbar, bereits gebuchte rückgängig machen ist zu komplex → nur abbrechen und user informieren

**Never:**
- Kein neues DB-Feld auf `reservations`-Tabelle; kein `alembic revision`
- `ReservationCreateDialog` nicht refaktorieren — entfernen
- Kein Geschlechts-Check bei `room_type === 'WARTEBEREICH'`-Räumen als Ziel (dort gilt er nie)
- `handleBelegen` weiterhin mit direktem `fetch()` lassen (Refactor ist out-of-scope)

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output | Error Handling |
|----------|--------------|----------------|----------------|
| Belegen: gleiche Designation | belegGeschlecht M, Raum M | Direkt speichern | N/A |
| Belegen: Mismatch | belegGeschlecht W, Raum M | Warning + Grund-Feld, Button disabled | N/A |
| Belegen: Notbett-Ausnahme | belegGeschlecht W, `is_notbett=true` | Kein Warning | N/A |
| Belegen: Wartebereich-Ausnahme | belegGeschlecht M, `room_type=WARTEBEREICH` | Kein Warning | N/A |
| Verlegen intern: Warteplatz | Person W, Ziel `bett_typ=WARTEPLATZ` | Kein Warning | N/A |
| Verlegen intern: Mismatch | Person W, Ziel-Raum M | Bestehendes Warning greift (fix exception) | N/A |
| Reservation Confirm: Mismatch | `confirmRes.geschlecht M`, `FreeBed.geschlechts_designation W` | Alert + Grund-Feld, Button disabled | N/A |
| Reservation Confirm: is_notbett | Bett mit `is_notbett=true` gewählt | Kein Warning | N/A |
| Batch-Intern: 3 Personen | Multi-Select + "Intern verlegen" | Dialog mit 3 Zeilen, freie STANDARD-Betten als Auswahl | N/A |
| Batch-Intern: POST schlägt fehl | 2/3 Betten schon belegt | Snackbar-Fehler, kein partial commit, Dialog bleibt offen | N/A |
| Neue Verlegungsanfrage | Klick auf Button in Reservations.tsx | `navigate('/suggestions')`, kein Dialog | N/A |

</frozen-after-approval>

## Code Map

- `frontend/src/pages/Drilldown.tsx` — `handleBelegen` (Mismatch hinzufügen), `handleVerlegen` (Ausnahme fixen), Batch-Intern-State + Dialog + Button
- `frontend/src/pages/Reservations.tsx` — Confirm-Dialog: Mismatch-Alert + Grund-Feld; „Neue Anfrage"-Button → navigate
- `frontend/src/components/ReservationCreateDialog.tsx` — nicht mehr importiert, Datei kann bleiben
- `backend/src/api/reservations/schemas.py` — `geschlecht_mismatch_grund: Optional[str] = None` in `ReservationConfirmRequest`
- `backend/src/api/reservations/router.py` — `body.geschlecht_mismatch_grund` an `repo.confirm()` weitergeben
- `backend/src/adapters/db/reservation_repo.py` — Param in `confirm()`-Signatur + Audit-Payload

## Tasks & Acceptance

**Execution:**

- [x] `frontend/src/pages/Drilldown.tsx` — **Belegen-Mismatch:** `belegMismatch: boolean` + `belegMismatchGrund: string` State. In `handleBelegen` nach Guard: `if (!belegMismatch && deriveRoomGender(belegBed.room) !== 'D' && deriveRoomGender(belegBed.room) !== belegGeschlecht && !belegBed.bed.is_notbett && belegBed.room.room_type !== 'WARTEBEREICH') { setBelegMismatch(true); setBelegSaving(false); return }`. Beim POST `geschlecht_mismatch_grund` mitsenden wenn gesetzt. Im Belegung-Dialog unter allen Feldern, wenn `belegMismatch===true`: `<Alert severity="warning">` + `<TextField label="Begründung *" value={belegMismatchGrund}…/>`. Bestätigen-Button disabled wenn `belegMismatch && !belegMismatchGrund.trim()`. Reset in `setBelegBed(null)`.

- [x] `frontend/src/pages/Drilldown.tsx` — **Verlegen-Ausnahme:** Zeile ~910 condition erweitern um `&& !targetBedInfo?.is_notbett && targetBedInfo?.bett_typ !== 'WARTEPLATZ'`.

- [x] `frontend/src/pages/Drilldown.tsx` — **Batch-Intern-Verlegen:** State: `batchInternOpen: boolean`, `batchAssignments: Record<string, string>` (bed_id → targetBedId), `batchMismatchGrunds: Record<string, string>` (bed_id → grund). Im multi-select-Mode zweiter Button „Intern verlegen" (neben bestehendem „Extern verlegen"). Dialog: pro `selectedAnkunftBeds`-Eintrag eine Zeile mit AZR-ID + Geschlechts-Chip + Dropdown der verfügbaren freiBeds (bett_typ ≠ WARTEPLATZ, bereits beanspruchte ausblenden). Bei Mismatch pro Zeile: Warning-Icon + Grund-TextField inline. Confirm-Button nur aktiv wenn alle Personen ein Bett zugewiesen haben. `handleBatchIntern()`: sequenziell POST `/api/beds/{targetBedId}/occupancy` + DELETE `/api/beds/{sourceBedId}/occupancy/{occupancyId}` pro Person, bei Fehler Snackbar + abort + reload.

- [x] `frontend/src/pages/Reservations.tsx` — **Confirm-Mismatch:** `FreeBed` Interface: `is_notbett?: boolean` hinzufügen; in `openConfirmDialog` aus `BedItem` mappen. `genderMismatch: boolean` als derived/memo: `selectedBedId && confirmRes` gesetzt → prüfe ob Bed's `geschlechts_designation !== 'D'` und `geschlechts_designation !== confirmRes.geschlecht` und `!bed.is_notbett`. Im Confirm-Dialog wenn `genderMismatch===true`: `<Alert severity="warning">` vor dem Bett-Picker + `<TextField label="Begründung *" value={genderMismatchGrund}/>`. Bestätigen-Button disabled wenn `genderMismatch && !genderMismatchGrund.trim()`. `handleConfirmWithBed` sendet `geschlecht_mismatch_grund` wenn gesetzt.

- [x] `frontend/src/pages/Reservations.tsx` — **Dialog-Cleanup:** `dialogOpen` State entfernen, `ReservationCreateDialog` Import entfernen, Button `onClick={() => navigate('/suggestions')}` anpassen.

- [x] `backend/src/api/reservations/schemas.py` — `geschlecht_mismatch_grund: Optional[str] = None` in `ReservationConfirmRequest`.

- [x] `backend/src/api/reservations/router.py` — `body.geschlecht_mismatch_grund` an `repo.confirm(…, mismatch_grund=body.geschlecht_mismatch_grund)` übergeben.

- [x] `backend/src/adapters/db/reservation_repo.py` — `confirm()`-Signatur: `mismatch_grund: Optional[str] = None`. Wenn gesetzt, in `extra_payload` des Audit-Eintrags aufnehmen: `{"mismatch_grund": mismatch_grund}`.

**Acceptance Criteria:**

- Given Bett-Zuweisen mit Geschlechts-Mismatch (nicht Notbett/Wartebereich), when Speichern (1. Versuch), then Alert erscheint, Begründungsfeld sichtbar, Button disabled — erst nach Eingabe speicherbar
- Given Bett-Zuweisen auf Notbett oder Wartebereich-Raum mit abweichendem Geschlecht, when Speichern, then kein Mismatch-Alert, direktes Speichern
- Given Interne Verlegung auf Warteplatz (`bett_typ=WARTEPLATZ`), when Verlegen, then keine Mismatch-Warnung
- Given Reservierungs-Bestätigungsdialog, Bett mit Mismatch ausgewählt und kein Grund, when Bestätigen, then Button disabled
- Given Multi-Select 3+ Personen in Wartebereich, when „Intern verlegen" geklickt, then Batch-Dialog mit allen Personen und freien Betten (kein Warteplatz als Ziel) öffnet sich
- Given „Neue Verlegungsanfrage" Button in Reservations, when geklickt, then Navigation zu `/suggestions`, kein Dialog

## Design Notes

Mismatch-Pattern für `handleBelegen` (identisch zum bestehenden `handleVerlegen`-Muster):
```
1. Aufruf: setXxxMismatch(true); setXxxSaving(false); return
2. Aufruf (mismatch===true): proceed + include grund in payload
Reset: bei Dialog-Close alle Mismatch-States auf false/"" zurücksetzen
```

Batch-Intern: `batchAssignments` ist Record\<sourceBedId, targetBedId\>. Ein Bett das in der Map erscheint, wird aus den Dropdown-Optionen aller anderen Personen gefiltert.

## Verification

**Commands:**
- `cd /Users/A3694852/KapzitaetsPlanungsTool/frontend && npx tsc --noEmit` -- erwartet: 0 Fehler
- `cd /Users/A3694852/KapzitaetsPlanungsTool/frontend && npx eslint src/pages/Drilldown.tsx src/pages/Reservations.tsx --max-warnings 0` -- erwartet: keine neuen Warnungen

## Spec Change Log

