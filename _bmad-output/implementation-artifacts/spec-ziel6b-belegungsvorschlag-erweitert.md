---
title: 'Ziel 6b — Belegungsvorschlag Solver (erweitert)'
type: 'feature'
created: '2026-05-24'
status: 'done'
baseline_commit: 'NO_VCS'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Der Solver (6a) kennt weder Familienzugehörigkeit — Minderjährige müssen mit Sorgeberechtigten zusammenbleiben — noch Betten außerhalb der eigenen Einrichtung, beides Lücken bei der praktischen Belegungsplanung.

**Approach:** (1) Neues `cross_location`-Flag erweitert die Solver-Abfrage auf alle aktiven Einrichtungen; Varianten-Cards zeigen Einrichtungsname. (2) Neues `familien_modus`-Flag mit `minderjaehrige`-Anzahl steuert Hard-Block: Bei Minderjährigen nur Einzelraumvarianten erlaubt. Migration 0004 legt `family_group_id` auf `persons.occupants` an (Setup für künftige Belegungserfassung).

## Boundaries & Constraints

**Always:**
- `cross_location=False` ist Standard; bestehende Location-Scoping-Logik und Accept/Reject-Ownership-Check bleiben unverändert
- Hard-Block: `familien_modus=True AND minderjaehrige > 0` → Solver liefert maximal Variante 1 (Einzelraum mit ≥ anzahl freien Betten); kein Greedy, kein Alphabetisch
- Wenn kein Einzelraum groß genug: `variants=[], message=f"Kein Raum für {anzahl} Personen zusammen verfügbar"`
- `family_group_id`-Spalte: NULLABLE UUID, kein NOT NULL, kein Index — der Solver liest und schreibt sie nicht
- `SUGGESTION_CREATED`-Payload ergänzt `cross_location: bool` und `familien_modus: bool`
- Kein Join auf `reservations.requests` zur Alters-Prüfung bestehender Occupants (`geburtsjahr` liegt nicht auf `persons.occupants`)

**Ask First:**
- Wenn `minderjaehrige >= anzahl` (keine erwachsene Person dabei — logisch inkonsistent)

**Never:**
- Kein Alters-Lookup auf bestehenden Belegungen (→ Ziel 7)
- Keine Eltern-Kind-Verknüpfung im Solver; `family_group_id` bleibt Setup-only
- Keine automatische Bett-Zuweisung

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Cross-Location, genug Betten | cross_location=true, W, 2 | Varianten aus mehreren Einrichtungen, location_name in Cards | — |
| Familie, Raum groß genug | familien_modus=true, minderjaehrige=1, anzahl=3, Raum ≥3 frei | Genau 1 Variante (Einzelraum) | — |
| Familie, kein Raum groß genug | familien_modus=true, minderjaehrige=1, anzahl=5, max. Raum=4 | `variants=[], message="Kein Raum für 5 Personen zusammen verfügbar"` | Alert im Wizard |
| minderjaehrige ≥ anzahl | minderjaehrige=3, anzahl=3 | 422 Feldmeldung | Inline-Fehler |
| cross_location + familien_modus | beide Flags, minderjaehrige=1 | Alle Locations, nur Einzelraumvariante | — |

</frozen-after-approval>

## Code Map

- `backend/alembic/versions/0004_family_group.py` — Neu: ADD COLUMN family_group_id auf persons.occupants
- `backend/src/api/suggestions/schemas.py` — Erweiterung: cross_location, familien_modus, minderjaehrige; BedOption + location_name
- `backend/src/api/suggestions/router.py` — Erweiterung: cross_location SQL-Branch, Familien-Hard-Block, locations JOIN
- `frontend/src/pages/SuggestionWizard.tsx` — Erweiterung: cross_location-Checkbox, Familien-Toggle + minderjaehrige-Feld, location_name in Cards

## Tasks & Acceptance

**Execution:**

- [x] `backend/alembic/versions/0004_family_group.py` — Neu. `revision='0004'`, `down_revision='0003'`. `upgrade()`: `op.execute("ALTER TABLE persons.occupants ADD COLUMN family_group_id UUID")`. `downgrade()`: `op.execute("ALTER TABLE persons.occupants DROP COLUMN family_group_id")`.

- [x] `backend/src/api/suggestions/schemas.py` — `SuggestionRequest` bekommt: `cross_location: bool = False`, `familien_modus: bool = False`, `minderjaehrige: int = Field(default=0, ge=0)`. `@model_validator(mode='after')` ergänzt: `if self.familien_modus and self.minderjaehrige >= self.anzahl: raise ValueError("mindestens eine erwachsene Person erforderlich")`. `BedOption` bekommt: `location_name: str = ''`.

- [x] `backend/src/api/suggestions/router.py` — Zwei SQL-Strings: `SQL_SCOPED` (mit `r.location_id = :loc_id`, wie bisher) und `SQL_CROSS` (mit `r.location_id IN (SELECT id FROM capacity.locations WHERE is_active=true)`). Beide ergänzen `JOIN capacity.locations l ON l.id = r.location_id` und selektieren `l.name AS location_name`. In `create_suggestion`: Branch auf `body.cross_location` für SQL-Auswahl. Nach `available`-Berechnung: wenn `body.familien_modus AND body.minderjaehrige > 0`: Variante 1 (Einzelraum mit ≥ anzahl Betten) suchen — falls gefunden `variants=[Variant(beds=room_beds[:anzahl])]`, sonst `variants=[], message=f"Kein Raum für {body.anzahl} Personen zusammen verfügbar"` und direkt zu Audit-Write. `SUGGESTION_CREATED`-Payload: `cross_location`, `familien_modus` hinzufügen.

- [x] `frontend/src/pages/SuggestionWizard.tsx` — Step 0: `FormControlLabel(Checkbox)` "Standortübergreifend suchen" → state `crossLocation: bool`. `FormControlLabel(Checkbox)` "Familiengruppe" → state `familienModus: bool`. Wenn `familienModus=true`: `TextField type=number` "Anzahl Minderjähriger" (0..anzahl-1) → state `minderjaehrige: number`. `formValid` ergänzt: `!familienModus || minderjaehrige < anzahl`. `handleSubmit` schickt alle neuen Felder. Step 1: Wenn `crossLocation=true`, zeige `b.location_name` in Card-Zeilen.

**Acceptance Criteria:**
- Given SB aktiviert "Standortübergreifend" und schickt ab, then enthalten alle Varianten-Cards die Einrichtungsbezeichnung
- Given familien_modus=true, minderjaehrige=1, anzahl=3, ein Raum ≥3 freie Betten, then ist genau 1 Variante sichtbar
- Given familien_modus=true, kein Raum ≥ anzahl Betten, then zeigt Step 1 "Kein Raum für N Personen zusammen verfügbar"
- Given minderjaehrige=3, anzahl=3 im Formular, then ist Submit-Button disabled
- Given `alembic upgrade head`, then läuft Migration 0004 fehlerfrei durch

## Spec Change Log

**2026-05-24 — Post-review patches (3 Agenten):**
- **room_name-Kollision (Bug):** `_compute_family_variants` und `_compute_variants` nutzten `room_name` als Schlüssel → bei `cross_location=True` wurden gleichnamige Räume verschiedener Einrichtungen zusammengeführt. Fix: Schlüssel auf `(location_name, room_name)`-Tupel geändert.
- **familien_modus=0-Bypass (Bug):** `familien_modus=True, minderjaehrige=0` fiel in `_compute_variants` durch. Schema-Validator ergänzt: `familien_modus ohne minderjaehrige >= 1` → 422. Frontend: Checkbox-Aktivierung setzt `minderjaehrige` auf 1 als Default; `familyValid` erfordert `minderjaehrige >= 1`.
- **Family-Message-Reihenfolge (Bug):** Family-Check kommt jetzt vor dem `available < anzahl`-Check, damit immer die fachlich korrekte Meldung gezeigt wird.
- **UUID-Validierung:** `suggestion_id`-Pfadparameter in `accept`/`reject` auf Typ `UUID` geändert → FastAPI liefert 422 für ungültige UUIDs, kein 500.
- **OccupantModel-Sync:** `family_group_id: Mapped[Optional[uuid.UUID]]` zu `OccupantModel` in `models.py` ergänzt (migration-sync).
- **Rejected:** TOCTOU/Bett-Persistierung, Datum-Strings, INSERT ohne id — alle by-design (advisory solver).
- **Deferred:** Cross-location Accept/Reject-Ownership (Spec sagt "unverändert"); alphabetische Priorisierung (UX-Gap → Ziel 7).

## Design Notes

**Kein geburtsjahr-JOIN:** `persons.occupants` hat kein `geburtsjahr` — es liegt nur auf `reservations.requests`. Der Hard-Block operiert auf User-Input (`minderjaehrige`). Altersverifizierung bestehender Belegungen → Ziel 7.

**family_group_id Setup-only:** Die Migration legt das Feld an, damit künftige Belegungserfassungsflows Familiengruppen tracken können. Kein Index nötig bis das Feld aktiv genutzt wird.

**Zwei SQL-Strings statt dynamischer WHERE:** `SQL_SCOPED` und `SQL_CROSS` als Modul-Konstanten — lesbarer und testbarer als bedingtes String-Konkatenieren.

## Verification

**Commands:**
- `cd frontend && npm run build` — erwartet: kein TypeScript-Fehler
- `cd backend && alembic upgrade head` — erwartet: 0004 läuft durch, keine Fehler

**Manual checks:**
- `make dev && make seed` → Formular: "Standortübergreifend" aktivieren → Varianten zeigen Einrichtungsname
- `make dev && make seed` → Formular: "Familiengruppe" + 1 Minderjährigen → nur 1 Variante wenn Raum passend
- `SELECT * FROM persons.occupants LIMIT 1` → Spalte `family_group_id` vorhanden (NULL)

## Suggested Review Order

**Migration & ORM-Sync**

- Setup-only NULLABLE UUID; kein NOT NULL, kein Index — intentional
  [`0004_family_group.py:16`](../../backend/alembic/versions/0004_family_group.py#L16)

- ORM-Modell synchronisiert; Spalte ohne Schreib-Logik im Solver
  [`models.py:104`](../../backend/src/adapters/db/models.py#L104)

**SQL & Cross-Location**

- Zwei SQL-Strings mit gemeinsamem _BED_SELECT; JOIN capacity.locations bringt location_name
  [`router.py:19`](../../backend/src/api/suggestions/router.py#L19)

- SQL_SCOPED vs. SQL_CROSS Branch; loc_id-Param nur bei SCOPED
  [`router.py:53`](../../backend/src/api/suggestions/router.py#L53)

**Solver-Logik**

- Reihenfolge: Family-Check vor available-Check → korrekte Fehlermeldung immer
  [`router.py:78`](../../backend/src/api/suggestions/router.py#L78)

- _compute_family_variants: (location_name, room_name)-Tupel verhindert Cross-Location-Kollision
  [`router.py:108`](../../backend/src/api/suggestions/router.py#L108)

- _compute_variants: gleicher Tupel-Schlüssel wie family-Variante; Greedy + Alphabetisch
  [`router.py:121`](../../backend/src/api/suggestions/router.py#L121)

**Validierung**

- Schema: familien_modus ohne minderjaehrige >= 1 → 422; minderjaehrige >= anzahl → 422
  [`schemas.py:15`](../../backend/src/api/suggestions/schemas.py#L15)

- UUID-Typ auf Pfadparametern; FastAPI liefert 422 statt 500 bei ungültiger UUID
  [`router.py:159`](../../backend/src/api/suggestions/router.py#L159)

**Frontend**

- familyValid erfordert minderjaehrige >= 1 wenn familienModus; Checkbox setzt Default auf 1
  [`SuggestionWizard.tsx:66`](../../frontend/src/pages/SuggestionWizard.tsx#L66)

- Step 0: beide Checkboxen + bedingtes minderjaehrige-Feld; location_name in Step-1-Cards
  [`SuggestionWizard.tsx:177`](../../frontend/src/pages/SuggestionWizard.tsx#L177)
