---
title: 'Ziel 6a — Belegungsvorschlag Solver (einfach)'
type: 'feature'
created: '2026-05-24'
status: 'done'
baseline_commit: 'NO_VCS'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Sachbearbeiter müssen manuell freie Betten nach Geschlecht und Kapazität suchen — keine Werkzeug-Unterstützung beim Planen neuer Belegungen. Entscheidungen werden nicht auditierbar dokumentiert.

**Approach:** Neue Route `/suggestions` mit dreistufigem Wizard: (1) Constraints eingeben (Geschlecht, Anzahl, Zeitraum), (2) bis zu drei Bett-Varianten vom Backend angezeigt bekommen, (3) Variante wählen oder mit Begründung ablehnen. Backend-Solver filtert freie Betten der eigenen Einrichtung nach Raumgeschlechtsdesignation + Zeitraum; Entscheidung landet in `audit.events`.

## Boundaries & Constraints

**Always:**
- Solver fragt nur Betten der eigenen Ja ab (via `X-Location-Id`-Header, keine cross-location in 6a)
- Geschlechtsfilter auf `rooms.geschlechts_designation IN (requested_gender, 'D')` — nicht auf Bett-Ebene
- Datum-Überlappungscheck: `NOT EXISTS (... WHERE belegung_start < ende AND belegung_ende > start)`
- Kein Anlegen von `persons.occupants`-Einträgen durch den Solver — er ist rein beratend
- Audit-Logging via `audit.events` (kein neues Schema): `SUGGESTION_CREATED`, `SUGGESTION_ACCEPTED`, `SUGGESTION_REJECTED`
- `suggestion_id` = `audit.events.id` des SUGGESTION_CREATED-Eintrags — wird ans Frontend zurückgegeben und für accept/reject referenziert

**Ask First:**
- Wenn `anzahl > 50` oder der Solver 0 Varianten findet und der SB manuell weiterarbeiten möchte

**Never:**
- Kein Familien-Constraint, kein Alter-Check (→ 6b)
- Keine standortübergreifende Suche (→ 6b)
- Keine automatische Bett-Zuweisung (nur beratende Funktion)

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Genug freie Betten | Geschlecht W, Anzahl 3, gültiger Zeitraum | 1–3 Varianten (Bett-Listen) + suggestion_id | — |
| Nicht genug Betten | Anzahl 10, nur 5 frei | `{ variants: [], message: "Nur 5 Betten verfügbar" }` | Frontend: Hinweis im Wizard anzeigen |
| Ungültiger Zeitraum | belegung_start ≥ belegung_ende | 422 mit Feldmeldung | Inline-Fehler im Formular |
| Akzeptieren | `POST /suggestions/{id}/accept` mit variant_index | 200; audit.events SUGGESTION_ACCEPTED | Snackbar "Vorschlag akzeptiert" |
| Ablehnen | `POST /suggestions/{id}/reject` mit reason | 200; audit.events SUGGESTION_REJECTED | Snackbar "Vorschlag abgelehnt" |
| Unbekannte suggestion_id beim Accept | gefälschte UUID | 404 | Snackbar "Vorschlag nicht gefunden" |

</frozen-after-approval>

## Code Map

- `backend/src/api/suggestions/router.py` — Neu: Solver-Logik + Accept/Reject-Endpunkte
- `backend/src/api/suggestions/schemas.py` — Neu: Pydantic-Schemas für Request/Response
- `backend/src/main.py` — suggestions-Router registrieren
- `frontend/src/pages/SuggestionWizard.tsx` — Neu: 3-stufiger Wizard
- `frontend/src/App.tsx` — Route `/suggestions` ergänzen
- `frontend/src/components/NavBar.tsx` — "Vorschlag"-Link ergänzen

## Tasks & Acceptance

**Execution:**

- [x] `backend/src/api/suggestions/__init__.py` — leere Datei (Package)

- [x] `backend/src/api/suggestions/schemas.py` — Neu. `SuggestionRequest(geschlecht: Literal['M','W','D'], anzahl: int = Field(ge=1, le=50), belegung_start: date, belegung_ende: date, @model_validator: ende > start)`. `BedOption(bed_id: str, bett_nummer: str, room_name: str, bett_typ: str)`. `Variant(beds: list[BedOption])`. `SuggestionResponse(suggestion_id: str, variants: list[Variant], message: str = '')`.

- [x] `backend/src/api/suggestions/router.py` — Neu. `POST /suggestions`: Query freie Betten via `AsyncSessionFactory` (JOIN beds→rooms, Filter: `r.location_id = location_ctx.location_id`, `r.is_active`, `b.is_active`, `r.geschlechts_designation IN (geschlecht, 'D')`, kein überlappendes Occupant). Gruppiere Betten nach Raum. Varianten: (1) einzelner Raum mit genug Betten falls vorhanden, (2) wenigste Räume (greedy), (3) erste `anzahl` Betten alphabetisch. Dedupliziere identische Varianten. Schreibe `audit.events` `{event_type: 'SUGGESTION_CREATED', payload: {location_id, geschlecht, anzahl, belegung_start, belegung_ende, variants_count}}` → gibt `suggestion_id = event.id` zurück. `POST /suggestions/{suggestion_id}/accept`: prüfe `audit.events`-Existenz (404 wenn nicht). Schreibe `SUGGESTION_ACCEPTED {suggestion_id, variant_index}`. `POST /suggestions/{suggestion_id}/reject`: Schreibe `SUGGESTION_REJECTED {suggestion_id, reason}`.

- [x] `backend/src/main.py` — `from src.api.suggestions.router import router as suggestion_router`; `app.include_router(suggestion_router, prefix="/api", dependencies=[Depends(get_current_user)])`.

- [x] `frontend/src/pages/SuggestionWizard.tsx` — Neu. Drei Schritte via `activeStep` (MUI Stepper): **Step 0** Formular (Geschlecht-Select M/W/D, Anzahl NumberField 1–50, Belegung-Von date, Belegung-Bis date, Validierung: Ende > Start); Submit → `POST /api/suggestions`. **Step 1** Varianten (bis zu 3 Cards; jede Card zeigt Raumnamen + Bettnummern + Typ; Radio-Auswahl; bei `variants=[]` zeige `message`-Text + "Abbrechen"-Button). **Step 2** Bestätigung: "Variante X gewählt" + "Bestätigen" → `POST /api/suggestions/{id}/accept {variant_index}`; alternativ "Ablehnen" → Textarea für Grund → `POST /api/suggestions/{id}/reject {reason}`. Snackbar für Erfolg/Fehler. Nach Abschluss: navigate('/').

- [x] `frontend/src/App.tsx` — `import SuggestionWizard from './pages/SuggestionWizard'`; Route `<Route path="/suggestions" element={<SuggestionWizard />} />` ergänzen.

- [x] `frontend/src/components/NavBar.tsx` — "Vorschlag" als vierten Nav-Link ergänzen (path `/suggestions`, kein Badge); ins `NAV_LINKS`-Array einfügen.

**Acceptance Criteria:**
- Given auth. SB, when er `/suggestions` öffnet, then zeigt Schritt 0 das Constraints-Formular
- Given Formular valide ausgefüllt (W, 2, gültige Daten), when SB abschickt, then erscheinen bis zu 3 Varianten in Schritt 1
- Given Variante 2 ausgewählt, when SB auf "Bestätigen" klickt, then ist in `audit.events` ein SUGGESTION_ACCEPTED-Eintrag mit `variant_index=1`
- Given SB klickt "Ablehnen" und gibt Grund "Zu weit vom Eingang", when er bestätigt, then ist SUGGESTION_REJECTED mit `reason` in `audit.events`
- Given Anzahl > verfügbare Betten, when Solver antwortet, then zeigt Step 1 `message` statt Varianten-Cards
- Given belegung_ende ≤ belegung_start, when SB eingibt, then ist Submit-Button disabled

## Spec Change Log

**2026-05-24 — Post-review patches (3 Agenten):**
- **Backend security:** Accept/Reject-Endpunkte prüfen jetzt `location_id` aus SUGGESTION_CREATED-Payload gegen aktuelle Location (403 bei Mismatch). Verhindert Cross-Location-Accept.
- **Backend validation:** Accept-Endpunkt liest `variants_count` aus SUGGESTION_CREATED-Payload und verwirft `variant_index >= variants_count` mit 422.
- **Backend defensive:** `_compute_variants` — greedy-Variante nur anhängen wenn nicht leer (`if greedy:`).
- **Frontend wizard flow:** Accept/Reject-Buttons von Schritt 1 nach Schritt 2 (Bestätigung) verschoben. Schritt 1 hat jetzt nur Varianten-Auswahl + "Weiter"-Button.
- **Frontend UX:** Schritt 2 zeigt "Variante X gewählt" (Alert info) vor Bestätigen/Ablehnen.
- **Frontend bug:** `selectedVariant` wird bei Zurück + Neu-Einreichung auf `null` zurückgesetzt.
- **Frontend NavBar:** "Vorschlag" als vierter Link (nach Postkorb) gerendert, nicht als dritter.
- **Rejected:** Accept/Reject INSERT ohne explizite `id` — `DEFAULT gen_random_uuid()` im Schema vorhanden, kein Handlungsbedarf.

## Design Notes

**Audit-IDs ohne neue Tabelle:** `suggestion_id` ist die `audit.events.id` des SUGGESTION_CREATED-Eintrags. Accept/Reject verifizieren die Existenz via `SELECT id FROM audit.events WHERE id = :sid AND event_type = 'SUGGESTION_CREATED'`. Kein neues Schema, kein neuer Migrations-Schritt nötig.

**Varianten-Deduplizierung:** Wenn alle drei Algorithmen dieselbe Bett-Menge liefern (z.B. nur ein Raum mit genau `anzahl` Betten), nur eine Variante zurückgeben.

**`geschlechts_designation 'D'`:** Räume mit Designation 'D' (Divers/gemischt) akzeptieren alle Geschlechter. Dies ist identisch zum Pattern im Reservierungsworkflow.

## Verification

**Commands:**
- `cd frontend && npm run build` — erwartet: kein TypeScript-Fehler

**Manual checks:**
- `make dev && make seed` → NavBar zeigt "Vorschlag"-Link → Formular ausfüllen → Varianten erscheinen → Bestätigen → in `audit.events` prüfen (`SELECT * FROM audit.events ORDER BY created_at DESC LIMIT 5`)

## Suggested Review Order

**Solver-Kern**

- SQL-Abfrage: Geschlechtsfilter auf rooms, Datumsüberlappung via NOT EXISTS, Location-Scope
  [`router.py:28`](../../backend/src/api/suggestions/router.py#L28)

- Drei Varianten-Algorithmen + Deduplizierung via `_same_beds`; greedy-Guard verhindert leere Variante
  [`router.py:89`](../../backend/src/api/suggestions/router.py#L89)

- Audit-Event SUGGESTION_CREATED; `suggestion_id = event.id` (kein neues Schema)
  [`router.py:69`](../../backend/src/api/suggestions/router.py#L69)

**Sicherheit & Validierung**

- Accept: Location-Ownership-Check + variant_index-Obergrenze via gespeichertem `variants_count`
  [`router.py:131`](../../backend/src/api/suggestions/router.py#L131)

- Reject: gleicher Location-Ownership-Check
  [`router.py:168`](../../backend/src/api/suggestions/router.py#L168)

- Request-Schemas: `geschlecht`, `anzahl ge=1/le=50`, Datum-Validator `ende > start`
  [`schemas.py:6`](../../backend/src/api/suggestions/schemas.py#L6)

**Frontend Wizard-Flow**

- Step 0: Constraints-Formular; Submit-Button disabled wenn `ende <= start`
  [`SuggestionWizard.tsx:124`](../../frontend/src/pages/SuggestionWizard.tsx#L124)

- Step 1: Variant-Cards mit Radio-Auswahl; "Weiter"-Button → Step 2 (kein Accept/Reject hier)
  [`SuggestionWizard.tsx:181`](../../frontend/src/pages/SuggestionWizard.tsx#L181)

- Step 2: "Variante X gewählt" + Bestätigen/Ablehnen; `completed`-Flag zeigt Abschluss-Screen
  [`SuggestionWizard.tsx:239`](../../frontend/src/pages/SuggestionWizard.tsx#L239)

**Peripherie**

- Vorschlag als vierter Link nach Postkorb (nicht in NAV_LINKS-Array)
  [`NavBar.tsx:55`](../../frontend/src/components/NavBar.tsx#L55)

- Route `/suggestions` registriert
  [`App.tsx:45`](../../frontend/src/App.tsx#L45)
