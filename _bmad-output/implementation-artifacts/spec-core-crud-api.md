ok, ziel 3---
title: 'BorderCapControl — Core CRUD API (Ziel 2/7)'
type: 'feature'
created: '2026-05-23'
status: 'done'
baseline_commit: 'NO_VCS'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Die Demo-Infrastruktur läuft, aber es existiert kein Datenmodell und keine API. Sachbearbeiter können noch keine Belegungsdaten verwalten.

**Approach:** Vollständiges Datenmodell (Location → Room → Bed → Occupancy) mit SQLAlchemy-Modellen, Alembic-Migration 0002, hexagonaler Domainlogik (Kapazitätsregeln, 12-Wochen-Warnung, EU-Gesamtquote) und FastAPI-CRUD-Endpoints. TDD via Behave.

## Boundaries & Constraints

**Always:**
- DSGVO-Minimaldatenmodell: Belegung speichert nur `azr_id`, `alias_id`, `geschlecht`, `belegung_start`, `belegung_ende` — kein Name, keine biometrischen Daten
- Zweistufiges Kapazitätsmodell: jedes Bett ist entweder `KONTINGENT` (EU-quotenrelevant, 12-Wochen-Timer) oder `NOTBETT` (max. 1 Nacht, nicht im EU-Kontingent)
- Notbett-Regel: Belegungsdauer > 1 Tag → HTTP 422 (harter Block, kein Warning)
- 12-Wochen-Regel: Belegungsende > 12 Wochen ab Start → HTTP 200 + Response-Header `X-12W-Warning: true` (Warnung, kein Block — SB entscheidet)
- EU-Gesamtquote: Summe aller `location.kontingent` darf `system_settings.eu_gesamtquote` nicht überschreiten → HTTP 422 bei Überschreitung
- Räume haben `geschlechts_designation` (M/W/F/D — aus SKOS-Codeliste)
- Alle Mutations-Operationen erzeugen Eintrag in `audit.events` (INSERT only, kein Update/Delete des Audit-Schemas)
- Hexagonale Architektur: Kapazitätsregeln nur in `domain/capacity/rules.py`, kein FastAPI-Import in domain/
- TDD-First: `capacity_crud.feature` wird vor Implementierungscode geschrieben
- **Soft-Delete:** `DELETE /api/locations/{id}`, `DELETE /api/rooms/{id}`, `DELETE /api/beds/{id}` setzen `is_active = False` — kein physisches Löschen. Inaktive Entitäten erscheinen nicht in Listen-Endpoints (außer mit `?include_inactive=true`). Belegung-Beenden (`DELETE /api/beds/{id}/occupancy/{occ_id}`) ist physisch — es endet eine laufende Belegung.

**Ask First:** — (alle Fragen beantwortet)

**Never:**
- Kein physisches Löschen von Locations, Rooms oder Beds
- Kein Reservierungsworkflow (Ziel 3), kein Frontend (Ziel 4)
- Kein automatisches Belegungsmanagement — nur Vorschläge in Ziel 6
- Familienmitglieder-Verknüpfung (Ziel 6), Reporting (Ziel 7)

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Location erstellen | POST `/api/locations` mit `kontingent=50` | 201 + Location-JSON mit `id` | 422 wenn `kontingent`-Summe > `eu_gesamtquote` |
| Notbett: Belegung > 1 Tag | POST `/api/beds/{id}/occupancy`, Bett ist NOTBETT, Ende > Start + 1d | 422 "Notbett: max. 1 Nacht erlaubt" | — |
| 12-Wochen-Überschreitung | POST `/api/beds/{id}/occupancy`, Ende > Start + 84 Tage | 201 + Header `X-12W-Warning: true` | — |
| Doppelbelegung | POST `/api/beds/{id}/occupancy`, Bett bereits aktiv belegt | 422 "Bett bereits belegt" | — |
| EU-Quote erschöpft | POST `/api/locations`, neue Summe > `eu_gesamtquote` | 422 "EU-Gesamtquote würde überschritten" | — |
| Belegung beenden | DELETE `/api/beds/{id}/occupancy/{occ_id}` | 200 + Audit-Eintrag | 404 wenn Belegung nicht gefunden |
| Location deaktivieren | DELETE `/api/locations/{id}` | 200, `is_active=false` in DB, Audit-Eintrag | 404 wenn nicht gefunden |
| Inaktive Entität | GET `/api/locations` (ohne Parameter) | Nur Locations mit `is_active=true` | — |

</frozen-after-approval>

## Code Map

Bestehend aus Ziel 1 (relevant):
- `backend/src/domain/__init__.py` — leer, Hexagon-Einstieg
- `backend/src/ports/__init__.py` — leer, Interface-Layer
- `backend/src/adapters/db/engine.py` — AsyncEngine + SessionFactory
- `backend/alembic/versions/0001_initial_schemas.py` — Placeholder-Tabellen (werden in 0002 ersetzt)
- `backend/src/main.py` — FastAPI-App, Router hier einzubinden

Neu in Ziel 2 (erstellt):
```
backend/src/
├── domain/capacity/
│   ├── __init__.py         -- /Users/A3694852/KapzitaetsPlanungsTool/backend/src/domain/capacity/__init__.py
│   ├── value_objects.py    -- /Users/A3694852/KapzitaetsPlanungsTool/backend/src/domain/capacity/value_objects.py
│   ├── entities.py         -- /Users/A3694852/KapzitaetsPlanungsTool/backend/src/domain/capacity/entities.py
│   └── rules.py            -- /Users/A3694852/KapzitaetsPlanungsTool/backend/src/domain/capacity/rules.py
├── ports/capacity/
│   ├── __init__.py         -- /Users/A3694852/KapzitaetsPlanungsTool/backend/src/ports/capacity/__init__.py
│   └── repository.py       -- /Users/A3694852/KapzitaetsPlanungsTool/backend/src/ports/capacity/repository.py
├── adapters/db/
│   ├── models.py           -- /Users/A3694852/KapzitaetsPlanungsTool/backend/src/adapters/db/models.py
│   └── capacity_repo.py    -- /Users/A3694852/KapzitaetsPlanungsTool/backend/src/adapters/db/capacity_repo.py
└── api/capacity/
    ├── __init__.py         -- /Users/A3694852/KapzitaetsPlanungsTool/backend/src/api/capacity/__init__.py
    ├── schemas.py          -- /Users/A3694852/KapzitaetsPlanungsTool/backend/src/api/capacity/schemas.py
    └── router.py           -- /Users/A3694852/KapzitaetsPlanungsTool/backend/src/api/capacity/router.py

backend/alembic/versions/
└── 0002_capacity_tables.py -- /Users/A3694852/KapzitaetsPlanungsTool/backend/alembic/versions/0002_capacity_tables.py

tests/features/
└── capacity_crud.feature   -- /Users/A3694852/KapzitaetsPlanungsTool/tests/features/capacity_crud.feature
tests/steps/
└── capacity_steps.py       -- /Users/A3694852/KapzitaetsPlanungsTool/tests/steps/capacity_steps.py
```

## Tasks & Acceptance

**Execution:**
- [x] `tests/features/capacity_crud.feature` -- TDD-First: Gherkin-Scenarios vor Implementierung schreiben -- Scenarios decken alle 6 I/O-Matrix-Fälle ab
- [x] `backend/src/domain/capacity/value_objects.py` -- `GenderDesignation` (M/W/F/D), `BedType` (KONTINGENT/NOTBETT) als Python Enums -- kein FastAPI-Import
- [x] `backend/src/domain/capacity/entities.py` -- Dataclasses Location, Room, Bed, Occupancy, SystemSettings -- keine ORM-Abhängigkeit
- [x] `backend/src/domain/capacity/rules.py` -- `check_notbett_duration()` → raises DomainError; `check_12_weeks()` → returns bool; `check_eu_quota()` → raises DomainError -- reine Funktionen, kein I/O
- [x] `backend/src/ports/capacity/repository.py` -- Abstract Repos mit AsyncContextManager für Session -- Ports definieren Interface, nicht Implementierung
- [x] `backend/src/adapters/db/models.py` -- SQLAlchemy Mapped-Klassen für alle 5 Tabellen; Location/Room/Bed haben `is_active: bool = True` Spalte -- `__table_args__ = {"schema": "capacity"}` etc.
- [x] `backend/alembic/versions/0002_capacity_tables.py` -- DROP placeholder-Tabellen; CREATE 5 echte Tabellen mit allen Feldern + Indexes + FK-Constraints -- idempotent (IF NOT EXISTS / IF EXISTS)
- [x] `backend/src/adapters/db/capacity_repo.py` -- Async CRUD-Implementierungen + `_audit_log(session, event_type, payload)` für alle Mutations -- audit.events INSERT via ORM-Session
- [x] `backend/src/api/capacity/schemas.py` -- Pydantic v2 Request/Response Schemas (BaseModel) -- DSGVO: kein Name-Feld in OccupancyCreate
- [x] `backend/src/api/capacity/router.py` -- FastAPI APIRouter mit allen CRUD-Endpoints; DELETE setzt `is_active=False` (Soft-Delete); 12-Wochen-Warning als Response-Header; DomainError → HTTP 422 -- Dependency Injection für Session
- [x] `backend/src/main.py` aktualisieren -- `app.include_router(capacity_router, prefix="/api")` -- kein sonstiger Code-Change
- [x] `tests/steps/capacity_steps.py` -- HTTP-Steps via `requests`; prüft Status-Codes, Response-JSON, Warning-Headers -- kein Mock

**Acceptance Criteria:**
- Given `eu_gesamtquote = 100` in system_settings, when POST `/api/locations` mit `kontingent=50`, then HTTP 201 und Location-JSON enthält `id` (UUID)
- Given Bett vom Typ NOTBETT, when POST `/api/beds/{id}/occupancy` mit `belegung_ende` = Morgen + 2 Tage, then HTTP 422 mit Detail "Notbett: max. 1 Nacht erlaubt"
- Given Bett KONTINGENT und Belegungsende = heute + 85 Tage, when POST Occupancy, then HTTP 201 und Response-Header `X-12W-Warning: true` vorhanden
- Given Bett aktiv belegt, when erneut POST Occupancy, then HTTP 422 mit Detail "Bett bereits belegt"
- Given Kontingent-Summe würde 101 ergeben (> eu_gesamtquote=100), when POST Location, then HTTP 422 mit Detail "EU-Gesamtquote würde überschritten"
- Given Location existiert, when DELETE `/api/locations/{id}`, then HTTP 200 und Location hat `is_active=false` in DB; GET `/api/locations` gibt sie nicht zurück; Audit-Eintrag `location.deactivated` vorhanden
- Given `make test`, when Behave, then alle `capacity_crud.feature`-Scenarios `passed`, Exit-Code 0

## Spec Change Log

## Design Notes

**Hexagonale Schichtentrennung:** `rules.py` ist reine Python-Logik (Dataclasses rein/raus, kein I/O). Adapter-Schicht übersetzt ORM-Modelle ↔ Dataclasses. FastAPI-Layer übersetzt HTTP ↔ Pydantic Schemas ↔ Domain-Entities.

**DomainError → HTTP 422:** Ein eigener `DomainError(message: str)` in `domain/capacity/` wird vom Router als FastAPI `HTTPException(422)` behandelt. Kein Exceptions-Leak aus der Domain.

**audit.events INSERT:** Die Adapter-Repo-Methoden schreiben nach jedem mutierenden DB-Call (create/update/delete) einen Eintrag in `audit.events` mit `event_type` (z.B. `"location.created"`) und `payload` (JSONB mit Entity-ID und relevanten Feldern). Gleiche Session → atomares Commit.

## Suggested Review Order

**Domain Logic — reiner Python-Kern, kein I/O**

- Alle vier Kapazitätsregeln als pure Funktionen; DomainError-Definition hier
  [`rules.py:11`](../../backend/src/domain/capacity/rules.py#L11)

- GenderDesignation (M/W/F/D) und BedType (KONTINGENT/NOTBETT) als str-Enums
  [`value_objects.py:8`](../../backend/src/domain/capacity/value_objects.py#L8)

- Dataclasses Location → Room → Bed → Occupancy — keine ORM-Abhängigkeit
  [`entities.py:13`](../../backend/src/domain/capacity/entities.py#L13)

**Hexagonale Ports — Interface-Vertrag**

- Abstrakte Repo-Interfaces inkl. list_all_for_location/list_all_for_room
  [`repository.py:18`](../../backend/src/ports/capacity/repository.py#L18)

**Datenbank-Schema — Migration und ORM**

- DROP Placeholder, CREATE 5 Tabellen mit UNIQUE/CHECK-Constraints und Grants
  [`0002_capacity_tables.py:17`](../../backend/alembic/versions/0002_capacity_tables.py#L17)

- SQLAlchemy 2.0 Mapped-Klassen; OccupantModel in persons-Schema
  [`models.py:18`](../../backend/src/adapters/db/models.py#L18)

**Repository-Implementierungen — Adapter-Schicht**

- _audit_log: schreibt in gleicher Session atomar mit jeder Mutation
  [`capacity_repo.py:42`](../../backend/src/adapters/db/capacity_repo.py#L42)

- SqlLocationRepo: sum_kontingent filtert nur is_active=True für EU-Quota-Check
  [`capacity_repo.py:111`](../../backend/src/adapters/db/capacity_repo.py#L111)

- SqlOccupancyRepo.get_active_for_bed: scalars().first() statt scalar_one_or_none() (Race-sicherer)
  [`capacity_repo.py:338`](../../backend/src/adapters/db/capacity_repo.py#L338)

- SqlSystemSettingsRepo: Singleton-Fallback mit eu_gesamtquote=0 bei fehlendem Eintrag
  [`capacity_repo.py:363`](../../backend/src/adapters/db/capacity_repo.py#L363)

**API-Schicht — HTTP ↔ Domain**

- OccupancyCreate: DSGVO-konform + model_validator belegung_ende > belegung_start
  [`schemas.py:82`](../../backend/src/api/capacity/schemas.py#L82)

- POST /beds/{id}/occupancy: Bett-Check → Notbett → 12W-Warnung → create
  [`router.py:352`](../../backend/src/api/capacity/router.py#L352)

- POST /locations: EU-Quota-Check vor Create; is_active-Elternprüfung bei Rooms/Beds
  [`router.py:98`](../../backend/src/api/capacity/router.py#L98)

- DELETE /locations/{id}: Soft-Delete (is_active=False) mit Audit-Eintrag
  [`router.py:181`](../../backend/src/api/capacity/router.py#L181)

- Session-Dependency: begin()-Transaktion als Context Manager
  [`router.py:53`](../../backend/src/api/capacity/router.py#L53)

**App-Integration**

- include_router-Eintrag; einzige Änderung in main.py
  [`main.py:27`](../../backend/src/main.py#L27)

**Tests**

- 10 Gherkin-Scenarios (TDD-First): alle I/O-Matrix-Fälle inkl. Belegung beenden
  [`capacity_crud.feature:1`](../../tests/features/capacity_crud.feature#L1)

- after_scenario DB-Teardown für Testisolation zwischen Scenarios
  [`environment.py:1`](../../tests/environment.py#L1)

- Alle Step-Definitionen: Given-Voranlegen, When-Aktionen, Then-Assertions
  [`capacity_steps.py:53`](../../tests/steps/capacity_steps.py#L53)

## Verification

**Commands:**
- `make test` -- expected: `capacity_crud.feature: X scenarios passed, 0 failed`
- `curl -s -X POST http://localhost:8000/api/locations -H 'Content-Type: application/json' -d '{"name":"Test","kontingent":10}' | python3 -m json.tool` -- expected: JSON mit `id`-Feld
- `docker compose exec backend alembic upgrade head` -- expected: `Running upgrade 0001 -> 0002, capacity_tables`
