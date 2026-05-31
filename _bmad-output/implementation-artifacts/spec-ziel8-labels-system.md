---
title: 'Ziel 8 — Labels-System (Räume, Betten, Belegungen)'
type: 'feature'
created: '2026-05-25'
status: 'done'
baseline_commit: 'NO_VCS'
context: ['spec-core-crud-api.md', 'spec-ziel4a-frontend-setup-dashboard-drilldown.md', 'spec-ziel4b-frontend-reservierungsworkflow-postkorb.md']
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** SBs können beim Belegen und beim Belegungsvorschlag keine operativen Hinweise zu Räumen, Betten und Personen erfassen oder sehen — z.B. "Unteres Bett", "Rollstuhlgerecht" oder "Sprache: Arabisch". Das erzwingt mündliche Absprachen oder externe Notizen außerhalb des Systems.

**Approach:** `TEXT[]`-Spalten auf den drei Entitätstypen `capacity.rooms`, `capacity.beds` und `persons.occupants`. Ein vordefinierter Katalog (kein Freitext) begrenzt erlaubte Werte. Drei `PATCH`-Endpoints ersetzen die Labels-Liste atomisch. Ein neuer `GET /api/labels/catalog`-Endpoint liefert den Katalog gruppiert nach Entitätstyp. Im Frontend zeigt eine `LabelChips`-Komponente Labels als MUI-Chips — readonly in Listenansichten, editierbar in `BelegDialog` und `BedManageDialog`.

## Boundaries & Constraints

**Always:**
- Labels sind `TEXT[]`, kein eigenes Entity-Modell auf DB-Ebene (Demo-Scope: einfachster Ansatz)
- Nur Werte aus dem vordefinierten Katalog sind erlaubt; Backend validiert gegen Katalog und gibt 422 bei unbekannten Labels zurück
- `PATCH`-Semantik: Die übergebene Liste ersetzt vollständig die bisherigen Labels (kein Merge, kein Append)
- Leere Liste `[]` ist erlaubt und löscht alle Labels der Entität
- Authentifizierung über `get_current_user` bei allen schreibenden Endpoints; Location-Scope-Check für `rooms` und `beds` (SB darf nur eigene Einrichtung bearbeiten)
- Belegungs-Labels (`occupants.labels`): Location-Scope-Check des Bettes, auf dem die Belegung liegt
- DSGVO: `occupants.labels` wird gemeinsam mit der Belegung gelöscht — kein eigener Löschzyklus nötig
- `GET /api/labels/catalog` ist ohne Authentication abrufbar (statische Daten, kein Personenbezug)

**Ask First:**
- Wenn Labels über eine Admin-GUI verwaltet werden sollen (nicht in Phase 1 vorgesehen)
- Wenn Labels in den Belegungsvorschlag-Solver (Ziel 6a/6b) als Constraint einfließen sollen

**Never:**
- Kein Freitext — nur vordefinierte Katalogwerte
- Keine eigene DB-Tabelle für Label-Catalog-Einträge (Demo-Scope: hardcodierte Liste in `src/labels/catalog.py`)
- Keine Audit-Log-Einträge für Label-Änderungen (Demo-Scope)
- Keine Versionierung oder History der Labels
- Keine Labels auf `capacity.locations`-Ebene

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Labels setzen (Raum) | `PATCH /api/rooms/42/labels` Body: `{"labels": ["Rollstuhlgerecht", "Erdgeschoss"]}` | 200, Raum-Labels aktualisiert, Response enthält aktualisierten Raum | — |
| Unbekanntes Label | Body: `{"labels": ["UnbekannterWert"]}` | 422 Unprocessable Entity mit Feldmeldung | Katalog-Validierung im Router |
| Labels leeren | Body: `{"labels": []}` | 200, `labels = []` | — |
| Bett-Labels setzen | `PATCH /api/beds/7/labels` Body: `{"labels": ["Unteres Bett"]}` | 200, Bett-Labels aktualisiert | — |
| Belegungs-Labels setzen | `PATCH /api/occupants/99/labels` Body: `{"labels": ["Kind", "Sprache: Arabisch"]}` | 200, Belegungs-Labels aktualisiert | — |
| Falscher Location-Scope | SB Einrichtung A, Raum gehört Einrichtung B | 403 Forbidden | Location-Scope-Check |
| Nicht eingeloggt (PATCH) | Kein Token | 401 Unauthorized | Standard-Auth |
| Katalog abrufen | `GET /api/labels/catalog` | 200, JSON mit `room`, `bed`, `occupant` als Keys | — |
| Entität nicht gefunden | `PATCH /api/rooms/9999/labels` | 404 Not Found | Repo-Lookup |

</frozen-after-approval>

## Datenmodell

### Migrationsscript 0006 (Alembic)

```sql
-- capacity.rooms
ALTER TABLE capacity.rooms ADD COLUMN IF NOT EXISTS labels TEXT[] NOT NULL DEFAULT '{}';

-- capacity.beds
ALTER TABLE capacity.beds ADD COLUMN IF NOT EXISTS labels TEXT[] NOT NULL DEFAULT '{}';

-- persons.occupants
ALTER TABLE persons.occupants ADD COLUMN IF NOT EXISTS labels TEXT[] NOT NULL DEFAULT '{}';
```

Kein Index auf `labels`-Spalten (Demo-Scope: keine Array-Suche benötigt).

### Label-Katalog

Der Katalog wird in `backend/src/labels/catalog.py` als Python-Dict hardcodiert:

```python
LABEL_CATALOG: dict[str, list[str]] = {
    "room": [
        "Rollstuhlgerecht",
        "Barrierefrei",
        "Erdgeschoss",
        "Ruhige Lage",
        "Dusche vorhanden",
        "Barrierefreies Bad",
        "Familienzimmer",
        "Einzelzimmer",
    ],
    "bed": [
        "Unteres Bett",
        "Oberes Bett",
        "Einzelbett",
        "Barrierefrei",
        "Breitest verfügbar",
    ],
    "occupant": [
        "Kind",
        "Unbegleitete Minderjährige",
        "Sprache: Arabisch",
        "Sprache: Farsi",
        "Sprache: Türkisch",
        "Sprache: Englisch",
        "Sprache: Französisch",
        "Halal",
        "Vegetarisch",
        "Medizinische Einschränkung",
        "Mobilität eingeschränkt",
    ],
}

ALL_LABELS: set[str] = {label for labels in LABEL_CATALOG.values() for label in labels}
```

**DSGVO-Hinweis:** `occupant`-Labels sind operative Hinweise für den laufenden Belegungszeitraum. Sie sind nicht AZR-relevant und werden nicht zur dauerhaften Profilerstellung genutzt. Keine gesundheitlichen Diagnosen oder biometrischen Merkmale erlaubt — "Medizinische Einschränkung" ist nur ein Hinweis auf Mobilitäts-/Ausstattungsbedarf, kein Diagnosedatensatz.

## API-Design

### GET /api/labels/catalog

```
GET /api/labels/catalog
Response 200:
{
  "room": ["Rollstuhlgerecht", "Barrierefrei", ...],
  "bed": ["Unteres Bett", "Oberes Bett", ...],
  "occupant": ["Kind", "Unbegleitete Minderjährige", "Sprache: Arabisch", ...]
}
```

Kein Auth-Token erforderlich. Statische Antwort aus `LABEL_CATALOG`.

### PATCH /api/rooms/{room_id}/labels

```
PATCH /api/rooms/{room_id}/labels
Authorization: Bearer <token>
Content-Type: application/json

{"labels": ["Rollstuhlgerecht", "Erdgeschoss"]}

Response 200: <vollständiges Room-Objekt mit aktualisierten labels>
Response 403: SB gehört nicht zur Einrichtung des Raums
Response 404: Raum nicht gefunden
Response 422: Unbekanntes Label im Body
```

### PATCH /api/beds/{bed_id}/labels

```
PATCH /api/beds/{bed_id}/labels
Authorization: Bearer <token>
Content-Type: application/json

{"labels": ["Unteres Bett"]}

Response 200: <vollständiges Bed-Objekt>
Response 403: SB gehört nicht zur Einrichtung des Bettes
Response 404: Bett nicht gefunden
Response 422: Unbekanntes Label
```

### PATCH /api/occupants/{occupant_id}/labels

```
PATCH /api/occupants/{occupant_id}/labels
Authorization: Bearer <token>
Content-Type: application/json

{"labels": ["Kind", "Sprache: Arabisch"]}

Response 200: <vollständiges Occupant-Objekt>
Response 403: SB gehört nicht zur Einrichtung der Belegung
Response 404: Belegung nicht gefunden
Response 422: Unbekanntes Label
```

## Code Map

- `backend/migrations/versions/0006_add_labels_columns.py` — Neu: Alembic-Migration
- `backend/src/labels/__init__.py` — Neu: leeres Package
- `backend/src/labels/catalog.py` — Neu: `LABEL_CATALOG` + `ALL_LABELS`
- `backend/src/api/rooms/router.py` — Neu: `PATCH /{room_id}/labels`-Endpoint ergänzen
- `backend/src/api/beds/router.py` — Neu: `PATCH /{bed_id}/labels`-Endpoint ergänzen
- `backend/src/api/occupants/router.py` — Neu: `PATCH /{occupant_id}/labels`-Endpoint ergänzen
- `backend/src/api/labels/__init__.py` — Neu: leeres Package
- `backend/src/api/labels/router.py` — Neu: `GET /catalog`-Endpoint
- `backend/src/main.py` — labels-Router mit `prefix="/api/labels"` registrieren
- `frontend/src/components/LabelChips.tsx` — Neu: MUI-Chip-Komponente (readonly + editable Modus)
- `frontend/src/api/client.ts` — `patchRoomLabels`, `patchBedLabels`, `patchOccupantLabels`, `getLabelCatalog` ergänzen

## Tasks & Acceptance

**Execution:**

- [ ] `backend/migrations/versions/0006_add_labels_columns.py` — Alembic-Migration. `upgrade()`: `ALTER TABLE capacity.rooms ADD COLUMN IF NOT EXISTS labels TEXT[] NOT NULL DEFAULT '{}'`, analog für `capacity.beds` und `persons.occupants`. `downgrade()`: `ALTER TABLE ... DROP COLUMN IF EXISTS labels` für alle drei Tabellen.

- [ ] `backend/src/labels/__init__.py` — Leere Datei.

- [ ] `backend/src/labels/catalog.py` — `LABEL_CATALOG` Dict und `ALL_LABELS` Set wie oben definiert.

- [ ] `backend/src/api/rooms/router.py` — Neuen Endpoint ergänzen:
  `PATCH /{room_id}/labels`: Liest Raum aus DB, prüft Location-Scope (403 wenn SB-Location != Raum-Location), validiert alle Labels gegen `ALL_LABELS` (422 wenn unbekannt), setzt `room.labels = body.labels`, commit, gibt Raum zurück.

- [ ] `backend/src/api/beds/router.py` — Analog zu rooms: `PATCH /{bed_id}/labels` mit Location-Scope-Check über `bed.room.location_id`.

- [ ] `backend/src/api/occupants/router.py` — Analog zu beds: `PATCH /{occupant_id}/labels` mit Location-Scope-Check über `occupant.bed.room.location_id`.

- [ ] `backend/src/api/labels/router.py` — `GET /catalog` ohne Auth: gibt `LABEL_CATALOG` als JSON zurück.

- [ ] `backend/src/main.py` — `labels_router` mit `prefix="/api/labels"` registrieren (kein `Depends(get_current_user)` auf Router-Ebene, da `/catalog` öffentlich ist).

- [ ] `frontend/src/api/client.ts` — Vier neue Funktionen:
  - `getLabelCatalog(): Promise<LabelCatalog>` — `GET /api/labels/catalog`
  - `patchRoomLabels(roomId: number, labels: string[]): Promise<Room>` — `PATCH /api/rooms/{id}/labels`
  - `patchBedLabels(bedId: number, labels: string[]): Promise<Bed>` — `PATCH /api/beds/{id}/labels`
  - `patchOccupantLabels(occupantId: number, labels: string[]): Promise<Occupant>` — `PATCH /api/occupants/{id}/labels`

- [ ] `frontend/src/components/LabelChips.tsx` — MUI-Chip-Komponente. Props: `labels: string[]`, `entityType: 'room' | 'bed' | 'occupant'`, `editable?: boolean`, `onSave?: (labels: string[]) => void`. Readonly-Modus: Chips mit `size="small"` und farb-kodierter Variante (room=default, bed=outlined, occupant=filled). Edit-Modus: öffnet Dropdown (MUI Autocomplete) mit Katalog-Optionen; bei Klick auf "Speichern" → `onSave(selected)` aufrufen.

- [ ] Integration `BelegDialog.tsx` — `LabelChips`-Komponente mit `entityType="occupant"` und `editable={true}` einbinden; beim Speichern der Belegung direkt `patchOccupantLabels` aufrufen.

- [ ] Integration `BedManageDialog.tsx` — `LabelChips` für Bett (`entityType="bed"`, `editable={true}`) und für aktuelle Belegung (`entityType="occupant"`, `editable={true}`) anzeigen.

- [ ] Integration `DrilldownPage.tsx` — Raum-Labels in der Raumliste als readonly `LabelChips` mit `entityType="room"` anzeigen.

**Acceptance Criteria:**

- Given: SB ist eingeloggt und gehört zu Einrichtung A, When: `PATCH /api/rooms/{raum_A_id}/labels` mit `{"labels": ["Rollstuhlgerecht"]}`, Then: 200, Raum hat `labels: ["Rollstuhlgerecht"]`
- Given: Labels-Liste enthält unbekannten Wert, When: `PATCH`-Request, Then: 422 mit Feldmeldung
- Given: SB gehört zu Einrichtung A, When: `PATCH /api/rooms/{raum_B_id}/labels` (Raum aus Einrichtung B), Then: 403
- Given: Keine Auth, When: `PATCH`-Request, Then: 401
- Given: Keine Auth, When: `GET /api/labels/catalog`, Then: 200 mit Katalog-JSON (kein 401)
- Given: Belegung wird gelöscht (`DELETE /api/occupants/{id}`), Then: Keine verwaisten Labels in DB (Labels-Spalte entfällt mit der Zeile)
- Given: `LabelChips` im Readonly-Modus, When: Labels vorhanden, Then: MUI-Chips sichtbar, kein Edit-Trigger
- Given: `LabelChips` im Edit-Modus, When: User wählt Label aus Katalog + klickt Speichern, Then: `patchOccupantLabels`/`patchBedLabels` aufgerufen, UI aktualisiert

## Design Notes

**TEXT[] statt Junction-Table:** Für Demo-Scope ist eine `TEXT[]`-Spalte ausreichend — keine JOIN-Overhead, kein separates Entity-Modell. Der Nachteil (keine referenzielle Integrität auf DB-Ebene) wird durch Backend-Validierung gegen `ALL_LABELS` kompensiert.

**Hardcodierter Katalog statt DB-Tabelle:** Der Katalog ändert sich selten und benötigt keine Admin-GUI in Phase 1. Eine spätere Migration zu einer `label_catalog_items`-Tabelle ist durch den `GET /api/labels/catalog`-Endpoint transparent (Frontend merkt nichts von der Implementierungsänderung).

**PATCH-Semantik (ersetzen statt mergen):** Einfachere Implementierung, keine Delta-Logik. Der SB sieht im Dialog immer die vollständige aktuelle Liste und speichert die gesamte neue Liste — konsistent mit dem "Human-in-the-loop"-Prinzip.

**Farbkodierung der Chips:** Zur schnellen visuellen Unterscheidung: `room`-Labels in grauem Default-Style, `bed`-Labels als Outlined-Chips, `occupant`-Labels als farbig gefüllte Chips (z.B. Warnorange für "Unbegleitete Minderjährige", Neutral für Sprachen).

## Enterprise Stack Considerations

Für den Enterprise Stack (Spring Boot / Angular) gelten folgende Anpassungen:

**Backend (Spring Boot / Spring Modulith):**

- **Modul:** `capacity` (für Room/Bed-Labels), `persons` (für Occupant-Labels)
- **Datenmodell:** Statt `TEXT[]` (PostgreSQL-spezifisch) eigene `LabelCatalogItem`-Entity in einer separaten `label_catalog` DB-Tabelle:
  ```java
  @Entity
  @Table(name = "label_catalog_items")
  public class LabelCatalogItem {
      @Id @GeneratedValue private Long id;
      @Enumerated(EnumType.STRING) private EntityType entityType; // ROOM, BED, OCCUPANT
      private String value;
      private String displayName;
      private Integer sortOrder;
  }
  ```
  `Room`, `Bed`, `Occupant` halten eine `@ElementCollection Set<String> labels` (JPA mapped zu JOIN-Tabelle) oder alternativ eine `@ManyToMany`-Beziehung zu `LabelCatalogItem`.
- **Validierung:** Bean Validation mit Custom `@ValidLabels`-Annotation, die gegen die `LabelCatalogItemRepository` prüft.
- **API:** Spring MVC `@PatchMapping("/{id}/labels")` mit `@RequestBody LabelUpdateRequest`.
- **Catalog-Endpoint:** `GET /api/labels/catalog` in einem eigenen `LabelController` im `reference-data`-Modul.

**Frontend (Angular / Angular Material):**

- **Komponente:** `LabelChipsComponent` als eigenständige Angular-Komponente mit `@Input() labels: string[]`, `@Input() editable: boolean`, `@Output() labelsChanged: EventEmitter<string[]>`.
- **Edit-Modus:** Angular Material `MatChipList` + `MatAutocomplete` für die Label-Auswahl aus dem Katalog.
- **Service:** `LabelService` mit `getCatalog()`, `patchRoomLabels()`, `patchBedLabels()`, `patchOccupantLabels()` — HTTP-Calls über den zentralen `ApiService`.
- **Accessibility:** `MatChip` bietet out-of-the-box ARIA-Support; Edit-Dialog mit `role="dialog"` und Fokus-Management für BITV 2.0 / WCAG 2.1 AA.

## Spec Change Log

_(Leer — initiale Version)_

## Verification

**Commands:**
- `cd backend && python -c "from src.labels.catalog import LABEL_CATALOG, ALL_LABELS; print(f'OK — {len(ALL_LABELS)} Labels')"` — erwartet: kein ImportError
- `cd backend && python -c "from src.api.labels.router import router; print('OK')"` — erwartet: kein ImportError
- `cd frontend && npm run build` — erwartet: kein TypeScript-Fehler

**Manual checks:**
- Nach `make migrate`: `SELECT column_name FROM information_schema.columns WHERE table_schema='capacity' AND table_name='rooms' AND column_name='labels'` → 1 Zeile
- `GET /api/labels/catalog` (ohne Token) → 200, JSON mit `room`, `bed`, `occupant` Keys
- `PATCH /api/rooms/1/labels` mit Token + Body `{"labels": ["Rollstuhlgerecht"]}` → 200
- `PATCH /api/rooms/1/labels` mit Token + Body `{"labels": ["UNBEKANNT"]}` → 422
- Frontend: `LabelChips` im Drilldown zeigt Raum-Labels als Chips
