---
title: 'Label-Verwaltung — DB-Katalog + Junction-Tables'
type: 'feature'
created: '2026-06-06'
status: 'done'
baseline_commit: 'f4ef285650d8a401d600138962a5bb62737060f5'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Der Label-Katalog ist hardcodiert in `router.py` (LABEL_CATALOG Python-Dict). Labels werden als `TEXT[]` ohne referenzielle Integrität gespeichert. System-Pflicht-Labels (Geschlecht-Labels für gender designation) haben keine Garantie, in der DB zu sein. System-Admins können den Katalog nicht pflegen.

**Approach:** Neue DB-Tabelle `capacity.label_catalog` (Composite PK: entity_type + name, `is_system`-Flag, category, color). Junction-Tables ersetzen `TEXT[]`-Spalten auf allen vier Entitäten (location, room, bed, occupant). Pflicht-Labels werden in Migration 0018 angelegt — nicht im Seed. System-admin bekommt Label-Verwaltungs-UI in den Stammdaten. Bestehende API-Response-Formate bleiben erhalten.

## Boundaries & Constraints

**Always:**
- Composite PK `(entity_type, name)` — Labelname ist ID innerhalb eines Entity-Typs; ein Label kann mehreren Types angehören (je eine Zeile)
- entity_type Werte: `'ROOM'` `'BED'` `'OCCUPANCY'` `'LOCATION'` (Großbuchstaben, konsistent mit aktuellem Code)
- `is_system=True`-Labels können weder gelöscht noch umbenannt werden — Backend 409
- In-Verwendung-Labels (FK-Referenz in junction table) können nicht gelöscht werden — Backend 409
- Migration 0018 fügt ALLE aktuellen Katalog-Einträge + System-Labels ein; danach sind `TEXT[]`-Spalten entfernt
- `GET /api/labels` Response-Format bleibt identisch (`LabelCatalogResponse` mit items: LabelCatalogEntry)
- Alle PATCH `/{type}/{id}/labels` Endpoints bleiben erhalten (gleiche URL, gleicher Request-Body)
- `deriveGenderFromLabels` und `GENDER_LABELS` im Frontend unverändert
- Keine Änderung an anderen Endpoints oder Business-Logik

**Never:**
- TEXT[] Spalten behalten (vollständig entfernen in 0018)
- Seed-Datei (demo_data.py) für System-Labels verwenden
- Freitext-Label-Eingabe ohne Katalog-Validierung
- is_system über API/UI verändern (nur via Migration/DB-Admin)

## I/O & Edge-Case Matrix

| Szenario | Zustand | Erwartetes Verhalten | Fehlerbehandlung |
|---|---|---|---|
| Admin legt Label an | POST /api/label-catalog | 201, sichtbar in GET /api/labels | 409 wenn (entity_type, name) existiert |
| Admin löscht is_system-Label | is_system=True | 409 „Pflicht-Label kann nicht gelöscht werden" | — |
| Admin löscht in-Verwendung-Label | FK-Referenz in junction table | 409 „Label ist in Verwendung" | — |
| Admin löscht nicht verwendetes Label | is_system=False, kein FK | 200, aus Katalog entfernt | — |
| Dialog öffnet | Entity hat junction-table-Einträge | Labels als Chips angezeigt | — |
| Label zuweisen | PATCH /{type}/{id}/labels, Label im Katalog | Junction-Row erstellt | 422 wenn Label nicht im Katalog |
| Label zuweisen, nicht im Katalog | PATCH mit unbekanntem Namen | 422 Unprocessable | — |
| viewer versucht Katalog-Verwaltung | GET /api/label-catalog | 200 (lesen ok), POST/DELETE → 403 | Rollenprüfung |

</frozen-after-approval>

## Code Map

- `backend/migrations/versions/0018_label_catalog_junction_tables.py` — Migration: CREATE catalog + junction tables; INSERT Katalog-Daten; Datenmigration TEXT[] → rows; DROP TEXT[] columns
- `backend/src/api/capacity/router.py:70-110` — `LABEL_CATALOG`-Dict entfernen; GET /api/labels DB-gestützt; neue Endpoints: `GET /api/label-catalog`, `POST /api/label-catalog`, `DELETE /api/label-catalog/{entity_type}/{name}`
- `backend/src/api/capacity/router.py:768` — `PATCH /locations/{id}/labels`: SQL-Update auf `TEXT[]` → junction table REPLACE
- `backend/src/api/capacity/router.py:1508-1550` — `PATCH /rooms/{id}/labels`, `PATCH /beds/{id}/labels`, `PATCH /occupancy/{id}/labels` analog
- `backend/src/api/capacity/schemas.py` — `LabelCatalogEntry`: `entity_types: list[str]` bleibt; neuer Schema `LabelCatalogCreateRequest`
- `frontend/src/components/LabelChips.tsx` — `entityType="ROOM"` für Location-Labels → `"LOCATION"` korrigieren; is_system-Flag in UI (Schloss-Icon, nicht löschbar im Edit-Modus)
- `frontend/src/pages/Drilldown.tsx` — Admin-Sektion „Label-Verwaltung" (nur system-admin): Tab pro entity_type, Labels listen, neues Label anlegen, nicht-System-Labels löschen
- `tests/features/label_catalog.feature` — Neue BDD-Feature-Datei
- `tests/steps/label_catalog_steps.py` — HTTP + DB Steps

## Tasks & Acceptance

**Execution:**

- [x] `backend/migrations/versions/0018_label_catalog_junction_tables.py` — `upgrade()`: (1) CREATE `capacity.label_catalog(name TEXT, entity_type TEXT, is_system BOOL DEFAULT FALSE, category TEXT NOT NULL, color TEXT NOT NULL DEFAULT '#757575', sort_order INT DEFAULT 0, PRIMARY KEY(entity_type, name))`; (2) CREATE junction tables `capacity.location_labels(location_id UUID REFERENCES capacity.locations ON DELETE CASCADE, label_name TEXT, label_entity_type TEXT DEFAULT 'LOCATION', PRIMARY KEY(location_id, label_name), FOREIGN KEY(label_entity_type, label_name) REFERENCES capacity.label_catalog(entity_type, name))`, analog `capacity.room_labels`, `capacity.bed_labels`, `persons.occupant_labels`; (3) INSERT alle LABEL_CATALOG-Einträge als separate Rows (eine Row pro entity_type pro Name), is_system=TRUE für: Männer/Frauen/Gemischt/Familie/Familienraum (ROOM); (4) INSERT `capacity.location_labels` FROM `SELECT id, unnest(labels) FROM capacity.locations WHERE labels != '{}'`; analog für room_labels, bed_labels, occupant_labels (überspringen wenn Label nicht im Katalog); (5) ALTER TABLE capacity.locations DROP COLUMN labels; analog rooms, beds, persons.occupants. `downgrade()`: DROP junction tables + label_catalog; ADD COLUMN labels TEXT[] DEFAULT '{}' zurück

- [x] `backend/src/api/capacity/router.py` — LABEL_CATALOG-Dict + get_labels() ersetzen: GET /api/labels → `SELECT name, entity_type, category, color, is_system FROM capacity.label_catalog ORDER BY sort_order, name`, Response als `LabelCatalogResponse(items=[LabelCatalogEntry(name=r.name, category=r.category, entity_types=[r.entity_type], color=r.color) for r in rows])`

- [x] `backend/src/api/capacity/router.py` — Neuer Admin-Endpoint `POST /api/label-catalog` (Writer-Plus + system-admin-Check): body `{name, entity_type, category, color?, sort_order?}`; INSERT; 409 bei Duplikat. `DELETE /api/label-catalog/{entity_type}/{name}` (system-admin only): 409 wenn is_system=True; 409 wenn Referenz in junction table; sonst DELETE

- [x] `backend/src/api/capacity/router.py:768` (+ rooms/beds/occupancy analoga) — PATCH /{type}/{id}/labels: (1) validate alle body.labels gegen `SELECT name FROM capacity.label_catalog WHERE entity_type=:et AND name = ANY(:names)` → 422 wenn ein Name fehlt; (2) DELETE FROM {type}_labels WHERE {type}_id=:id; (3) INSERT INTO {type}_labels SELECT :id, name, :et FROM unnest(:names) AS name

- [x] `frontend/src/components/LabelChips.tsx` — entityType prop: wenn `"LOCATION"` → filtert Katalog nach entity_type='LOCATION'; korrigiere alle Aufrufe mit falschem entityType (Drilldown.tsx:2049 hat `entityType="ROOM"` für Location-Labels → `"LOCATION"`); Edit-Modus: Labels mit `is_system=true` im Katalog kriegen Schloss-Icon + sind nicht entfernbar

- [x] `frontend/src/pages/Drilldown.tsx` — Admin-Sektion „Label-Verwaltung" (nur `isSystemAdmin`): Collapsible Box unterhalb des bestehenden Admin-Bereichs; vier Tabs (Einrichtung/Raum/Bett/Belegung); jeder Tab zeigt Label-Liste aus `GET /api/labels` gefiltert nach entity_type; Button „+ Label hinzufügen" öffnet Mini-Dialog (Name, Kategorie, Farbe); Löschen-Button auf nicht-System-Labels mit Confirm; Fehler via Snackbar

- [x] `tests/features/label_catalog.feature` — 5 Szenarien: (1) Label anlegen; (2) Duplikat anlegen → 409; (3) System-Label löschen → 409; (4) In-Verwendung-Label löschen → 409; (5) Nicht-verwendetes Label löschen → 200

- [x] `tests/steps/label_catalog_steps.py` — psycopg2 + requests; Fixtures: Test-Location + Room + Bed mit junction-table-Labels; Cleanup in given-Step; auth_token aus Env

**Acceptance Criteria:**

- Given Migration 0018 läuft, then `capacity.label_catalog` enthält alle bisherigen Katalog-Einträge; Männer/Frauen/Gemischt/Familie/Familienraum haben `is_system=true`; kein TEXT[]-labels-Feld mehr auf rooms/beds/locations/occupants
- Given system-admin, when POST /api/label-catalog mit neuem (entity_type, name), then 201 und Label in GET /api/labels sichtbar
- Given system-admin, when DELETE auf is_system=true-Label, then 409
- Given Label auf Raum in Verwendung, when DELETE, then 409
- Given viewer oder writer, when POST/DELETE /api/label-catalog, then 403
- Given Dialog für Room, when LabelChips zeigt Labels, then nur ROOM-Katalog-Labels auswählbar; is_system-Labels mit Schloss-Icon
- Given PATCH /locations/{id}/labels mit Label das nicht im LOCATION-Katalog ist, then 422

## Design Notes

**Composite PK statt Label-UUID:** Ein Label ist im System vollständig durch `(entity_type, name)` identifiziert. URLs für Admin-CRUD: `DELETE /api/label-catalog/ROOM/Männer`. Sonderfälle wie Umlaute im Pfad: URL-encoden.

**Multi-Type-Labels:** "Barrierefreiheit" gehört zu ROOM und BED — je eine Zeile im Katalog. Wenn admin "Barrierefreiheit" bei ROOM löscht, bleibt die BED-Variante erhalten.

**API-Kompatibilität:** `LabelCatalogEntry.entity_types` enthält jetzt immer genau ein Element. LabelChips filtert ohnehin nach entity_type — kein Frontend-Brecher.

**Datenmigration TEXT[] → junction tables:** Labels in TEXT[] die nicht im Katalog sind, werden übersprungen (Warning im Migrations-Log). So wird kein Fehler durch historische Freitext-Labels ausgelöst.

## Spec Change Log

## Verification

**Commands:**
- `cd /Users/A3694852/KapzitaetsPlanungsTool/tests && python3 -m behave features/label_catalog.feature` — expected: 7 Szenarien grün
- `cd /Users/A3694852/KapzitaetsPlanungsTool/frontend && npx tsc --noEmit` — expected: 0 Fehler

**Manual checks:**
- Nach 0018: `SELECT name, entity_type, is_system FROM capacity.label_catalog WHERE is_system ORDER BY entity_type, name` → Männer/Frauen/Gemischt/Familie/Familienraum mit ROOM und is_system=t
- GET /api/labels → 200, items enthalten alle bekannten Labels mit entity_types: ['ROOM'] etc.
- Drilldown system-admin: „Label-Verwaltung"-Sektion sichtbar; viewer: nicht sichtbar

## Suggested Review Order

**DB-Schema: Migration 0018**

- Composite PK `(entity_type, name)` + alle Junction-Tables + Katalog-Seed in einer Migration
  [`0018_label_catalog_junction_tables.py:1`](../../backend/alembic/versions/0018_label_catalog_junction_tables.py#L1)

- Datenmigration TEXT[] → junction tables mit catalog-filter (Patch: location_labels erhielt fehlenden EXISTS-Filter)
  [`0018_label_catalog_junction_tables.py:116`](../../backend/alembic/versions/0018_label_catalog_junction_tables.py#L116)

**Backend: Label-Katalog Endpoints**

- GET /api/labels — DB-gestützt statt hardcoded LABEL_CATALOG dict
  [`router.py:1523`](../../backend/src/api/capacity/router.py#L1523)

- POST /api/label-catalog — system-admin only, 409 bei Duplikat
  [`router.py:1552`](../../backend/src/api/capacity/router.py#L1552)

- DELETE /api/label-catalog — is_system + FK-Nutzung prüfen → 409
  [`router.py:1593`](../../backend/src/api/capacity/router.py#L1593)

**Backend: PATCH label Endpoints (Junction-Table REPLACE)**

- set_location_labels: validate → DELETE → INSERT; Patch: auch in update_location integriert
  [`router.py:789`](../../backend/src/api/capacity/router.py#L789)

- Catalog-Validation in update_location (Patch: war ohne Validierung → 500 statt 422)
  [`router.py:450`](../../backend/src/api/capacity/router.py#L450)

- set_room_labels, set_bed_labels, set_occupancy_labels — analoges REPLACE-Pattern
  [`router.py:1636`](../../backend/src/api/capacity/router.py#L1636)

**Frontend: LabelChips — is_system Lock-Icon**

- is_system-Flag: LockIcon + Tooltip + nicht entfernbar im Edit-Modus
  [`LabelChips.tsx:194`](../../frontend/src/components/LabelChips.tsx#L194)

**Frontend: Label-Verwaltung Admin-Sektion**

- Collapsible Box für system-admin — Tabs je entity_type, Anlegen + Löschen
  [`Drilldown.tsx:2331`](../../frontend/src/pages/Drilldown.tsx#L2331)

- Tab-Reset beim Wechsel (Patch: geteilter newLabel-State wurde bei Tab-Wechsel nicht geleert)
  [`Drilldown.tsx:2354`](../../frontend/src/pages/Drilldown.tsx#L2354)

**ORM-Modell: labels ARRAY entfernt**

- ARRAY(String) aus allen vier ORM-Modellen entfernt; Repo-Stubs returnen `[]`
  [`models.py:28`](../../backend/src/adapters/db/models.py#L28)

**Tests**

- 7 BDD-Szenarien: CRUD, Duplikat, is_system 409, FK 409, viewer 403, 422 PATCH
  [`label_catalog.feature:1`](../../tests/features/label_catalog.feature#L1)

- Step-Definitionen inkl. neuer writer-Auth + PATCH-Step
  [`label_catalog_steps.py:1`](../../tests/steps/label_catalog_steps.py#L1)
