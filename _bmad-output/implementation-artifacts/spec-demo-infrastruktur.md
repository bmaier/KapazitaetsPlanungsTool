---
title: 'BorderCapControl — Demo-Infrastruktur (Ziel 1/7)'
type: 'feature'
created: '2026-05-23'
status: 'done'
baseline_commit: 'NO_VCS'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** BorderCapControl ist ein Greenfield-Projekt ohne Infrastruktur. Ohne funktionierende Docker-Compose-Umgebung (PostgreSQL, Keycloak, FastAPI, SKOS-Service) können keine weiteren Features gebaut oder getestet werden.

**Approach:** Vollständige Demo-Infrastruktur aufsetzen: Docker Compose mit allen Services, PostgreSQL-Datenbankschema (6 Schemata + Alembic-Migrationen), Keycloak-Realm-Konfiguration (4 Rollen, standort-granular), hexagonale FastAPI-Basis, minimaler SKOS-Codelisten-Service und Behave-Testrahmen mit Smoke-Tests.

## Boundaries & Constraints

**Always:**
- Alle Services laufen ausschließlich in Docker — keine externen Abhängigkeiten, keine Cloud-Dienste
- PostgreSQL mit 6 getrennten Schemata: `capacity`, `reservations`, `persons`, `audit`, `tasks`, `reference_data`
- Audit-Schema-Tabellen: nur die Applikation hat `INSERT`-Rechte; kein `UPDATE`/`DELETE` über die App-DB-Rolle
- Keycloak-Realm `bordercapcontrol` mit 4 Realm-Rollen: `reader`, `writer`, `location-admin`, `system-admin`
- FastAPI-Projektstruktur folgt hexagonalem Muster: `domain/` (Fachlogik), `ports/` (Interfaces), `adapters/` (Infrastruktur)
- TDD-First: Jede Infrastrukturkomponente hat eine Behave-Feature-Datei; kein Produktionscode ohne zugehörigen Behave-Scenario
- `make dev` muss die gesamte Umgebung mit einem Befehl starten
- BITV 2.0 / WCAG 2.1 AA als Architekturprinzip — Frontend-Implementierung erst ab Ziel 4

**Ask First:**
- Falls Keycloak per Terraform statt Realm-JSON-Export konfiguriert werden soll
- Falls MBTiles-Deutschland-Datei (>500 MB) vorab beschafft und eingebunden werden soll oder Tile-Server als Placeholder bleibt

**Never:**
- Kein Kubernetes, kein Helm, kein Istio in diesem Spec
- Kein Frontend-Code (React/MUI) — gehört zu Ziel 4
- Keine AZR-ID-Validierungslogik — Datenmodell wird erst in Ziel 2 befüllt
- Kein Event Sourcing — standard CRUD + Audit-Schema

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Alle Services starten | `make dev` in leerem Verzeichnis | Alle 5 Container `healthy` in <120s | Logs zeigen Root-Cause; `make dev` ist idempotent |
| Health-Check | GET `/health` nach Start | `{"status": "ok", "db": "connected", "keycloak": "reachable"}` | 503 mit Fehlerdetail wenn DB/Keycloak nicht erreichbar |
| Schema-Isolation | Direkt-Query als App-Rolle auf `audit`-Schema mit DELETE | PostgreSQL-Permission-Error (42501) | — |
| Keycloak-Realm fehlt | Container-Start ohne `realm-export.json` | Import schlägt fehl, Container-Log zeigt Fehler | `docker-compose` Healthcheck markiert Keycloak `unhealthy` |
| Behave Smoke-Test | `make test` gegen laufende Umgebung | Alle Scenarios `passed`, Exit-Code 0 | Fehlermeldung zeigt welches Feature/Step failed |

</frozen-after-approval>

## Code Map

Implementiert 2026-05-23. Tatsächlich erstellte Dateipfade:

```
/Users/A3694852/KapzitaetsPlanungsTool/
├── Makefile                                         -- Targets: dev, test, down, logs, migrate
├── docker-compose.yml                               -- 5 Services mit Healthchecks und Netzwerk
├── docker-compose.override.yml                      -- Hot-Reload-Volume + explizite Port-Bindings
├── .env.example                                     -- Umgebungsvariablen-Template (kein Hardcoding)
├── infra/
│   ├── postgres/
│   │   ├── 00_roles.sql                             -- app_role, audit_role (idempotent per DO $$)
│   │   └── init.sql                                 -- 6 Schemata + Grants + Placeholder-Tabellen
│   └── keycloak/
│       └── realm-export.json                        -- Realm bordercapcontrol, 4 Rollen, 3 Test-User, PKCE-Client
├── backend/
│   ├── Dockerfile                                   -- Multi-Stage: builder + final (non-root)
│   ├── pyproject.toml                               -- Poetry: fastapi, uvicorn, sqlalchemy, asyncpg, alembic, python-jose, pydantic-settings, httpx
│   ├── alembic.ini                                  -- script_location=alembic, URL aus Env-Var
│   ├── alembic/
│   │   ├── env.py                                   -- Async-fähig mit asyncpg, URL aus Env-Var
│   │   └── versions/
│   │       └── 0001_initial_schemas.py              -- Idempotente Schema-Erstellung (CREATE IF NOT EXISTS)
│   └── src/
│       ├── main.py                                  -- FastAPI-App, /health (503 wenn DB/Keycloak down), CORS
│       ├── config.py                                -- Pydantic BaseSettings, kein Credential-Hardcoding
│       ├── domain/__init__.py                       -- Hexagonale Struktur (Ziel 2: Fachlogik)
│       ├── ports/__init__.py                        -- Hexagonale Struktur (Ziel 2: Interfaces)
│       └── adapters/
│           ├── __init__.py
│           └── db/
│               ├── __init__.py
│               ├── engine.py                        -- AsyncEngine + AsyncSessionFactory
│               └── health.py                        -- check_db_health() → bool
├── skos_service/
│   ├── Dockerfile                                   -- python:3.11-slim, non-root, Poetry
│   ├── pyproject.toml                               -- fastapi + uvicorn
│   └── src/
│       ├── main.py                                  -- /health, /codes/{list_name} (Path-Traversal-Schutz)
│       └── data/
│           ├── geschlecht.json                      -- M/W/D/X (XAusländer-Codes)
│           └── staatsangehoerigkeit.json            -- DE/AF/SY/IQ/ER (Placeholder)
└── tests/
    ├── behave.ini                                   -- format=pretty, show_timings=true
    ├── requirements.txt                             -- behave==1.2.6, requests, psycopg2-binary, python-dotenv
    ├── features/
    │   ├── smoke.feature                            -- 4 Scenarios: Backend-Health, SKOS, DB-Schemata, Audit-Schutz
    │   └── keycloak.feature                         -- 3 Scenarios: Realm, Rollen, PKCE-Client
    └── steps/
        ├── __init__.py
        ├── smoke_steps.py                           -- HTTP + psycopg2 + pgcode-42501-Assertion
        └── keycloak_steps.py                        -- Keycloak Admin REST API mit Bearer-Token
```

## Tasks & Acceptance

**Execution:**
- [x] `Makefile` -- erstellen mit Targets `dev`, `test`, `down`, `logs`, `migrate` -- einheitlicher Workflow-Einstiegspunkt
- [x] `docker-compose.yml` -- alle 5 Services mit Healthchecks, Netzwerk, Volumes -- kein Service ohne Healthcheck
- [x] `docker-compose.override.yml` -- Port-Bindings für lokale Entwicklung, Hot-Reload-Volume für Backend
- [x] `infra/postgres/init.sql` + `00_roles.sql` -- 6 Schemata anlegen, `app_role` mit `GRANT USAGE/SELECT/INSERT/UPDATE/DELETE` (außer `audit`-Tabellen: nur INSERT), `audit_role` write-only -- Audit-Manipulationsschutz
- [x] `infra/keycloak/realm-export.json` -- Realm `bordercapcontrol`, 4 Rollen, Test-User (admin/reader/writer je einer), PKCE-Client `bordercapcontrol-frontend` -- für lokale Entwicklung sofort nutzbar
- [x] `backend/pyproject.toml` -- Dependencies: fastapi, uvicorn, sqlalchemy[asyncio], asyncpg, alembic, python-jose[cryptography], pydantic-settings, httpx -- Poetry-Lockfile committen
- [x] `backend/src/config.py` -- Pydantic BaseSettings: DB_URL, KEYCLOAK_URL, KEYCLOAK_REALM, KEYCLOAK_CLIENT_ID, aus Env-Vars -- kein Hardcoding von Credentials
- [x] `backend/src/main.py` -- FastAPI-App, `/health`-Endpoint (DB-Ping + Keycloak-Reachability), CORS-Middleware, hexagonale Ordnerstruktur anlegen -- Health muss 503 zurückgeben wenn ein Dienst nicht erreichbar ist
- [x] `backend/adapters/db/engine.py` + `health.py` -- AsyncEngine, SessionFactory, Health-Check-Adapter -- Adapter-Muster, kein direkter DB-Zugriff in `main.py`
- [x] `backend/alembic/versions/0001_initial_schemas.py` -- `CREATE SCHEMA IF NOT EXISTS` für alle 6 Schemata; Placeholder-Tabellen `capacity.locations`, `persons.occupants` (nur IDs) -- Migration muss idempotent laufen
- [x] `skos_service/src/main.py` + Codedateien -- `/codes/geschlecht`, `/codes/staatsangehoerigkeit`, `/health` -- Daten aus lokalen JSON-Dateien, kein externer HTTP-Call
- [x] `tests/features/smoke.feature` -- Scenarios: Backend-Health, DB-Schema-Existenz, SKOS-Endpoint, Keycloak-Realm-Konfiguration -- Gherkin-Format, verständlich für Fachexperten
- [x] `tests/features/keycloak.feature` -- Scenarios: Realm existiert, 4 Rollen vorhanden, PKCE-Client konfiguriert -- Behave-Step gegen Keycloak-Admin-API
- [x] `tests/steps/smoke_steps.py` + `keycloak_steps.py` -- Step-Definitionen für alle Feature-Files -- Nur `requests` + Assertions, kein Mock

**Acceptance Criteria:**
- Given `make dev` in leerem Verzeichnis ausgeführt, when alle Container hochgefahren (max. 120s), then `GET http://localhost:8000/health` antwortet `{"status":"ok","db":"connected","keycloak":"reachable"}` mit HTTP 200
- Given PostgreSQL läuft, when `SELECT schema_name FROM information_schema.schemata` ausgeführt, then alle 6 Schemata `capacity`, `reservations`, `persons`, `audit`, `tasks`, `reference_data` sind vorhanden
- Given App-DB-Rolle (NON-Superuser `bordercap_app`), when `DELETE FROM audit.events` versucht, then PostgreSQL wirft Fehler 42501 (insufficient_privilege)
- Given Keycloak läuft, when Admin-API `/admin/realms/bordercapcontrol` abgefragt, then Realm existiert mit Rollen `reader`, `writer`, `location-admin`, `system-admin`
- Given `make test`, when Behave ausgeführt, then alle Scenarios in `smoke.feature` und `keycloak.feature` sind `passed`, Exit-Code 0
- Given `make dev` bereits läuft, when `make dev` erneut ausgeführt, then Befehl ist idempotent (kein Fehler, Zustand bleibt konsistent)

## Design Notes

**Hexagonale Ordnerstruktur in Ziel 1:** `domain/`, `ports/`, `adapters/` werden angelegt aber bleiben bis auf `adapters/db/` leer. Das verhindert Strukturschulden in Ziel 2.

**Audit-Sicherung via PostgreSQL-Grants:** DB-Rolle `app_role` bekommt auf Audit-Tabellen nur `INSERT`, kein `UPDATE`/`DELETE`. Das ist einfacher und sicherer als Application-Level-Enforcement.

**Behave vor Implementierung (TDD):** Feature-Files werden zuerst geschrieben (leere Steps mit `@step('...'): pass`), dann Produktionscode implementiert bis alle Steps `passed`. Das zwingt zu einem klaren Kontrakt vor der Umsetzung.

**Keycloak Realm-JSON-Import:** `realm-export.json` wird beim Keycloak-Start automatisch importiert via `KEYCLOAK_IMPORT` oder `--import-realm` Flag. Kein manueller Klick-Aufwand.

## Verification

**Commands:**
- `make dev` -- expected: alle Container `healthy` nach max. 120 Sekunden
- `curl -s http://localhost:8000/health | python3 -m json.tool` -- expected: `{"status":"ok","db":"connected","keycloak":"reachable"}`
- `make test` -- expected: `X features passed, 0 failed, 0 skipped` in Behave-Output
- `docker compose exec postgres psql -U bordercap -c "SELECT schema_name FROM information_schema.schemata WHERE schema_name IN ('capacity','reservations','persons','audit','tasks','reference_data') ORDER BY schema_name;"` -- expected: 6 Zeilen

## Suggested Review Order

**Einstiegspunkt — Infrastruktur-Übersicht**

- Gesamtbild aller 5 Services mit Healthchecks und Netzwerk-Topologie
  [`docker-compose.yml:1`](../../docker-compose.yml#L1)

- Einziger Workflow-Einstiegspunkt; Unhealthy-Detection + Exit-1-bei-Timeout
  [`Makefile:1`](../../Makefile#L1)

- Port-Bindings und Hot-Reload nur in Override (konsistentes Pattern)
  [`docker-compose.override.yml:1`](../../docker-compose.override.yml#L1)

**Datenbank — Schemata & Privilege-Isolation**

- Kernentscheidung: `bordercap_app` als Non-Superuser — Superuser würden Grants umgehen
  [`00_roles.sql:22`](../../infra/postgres/00_roles.sql#L22)

- `audit.events` bekommt nur `INSERT` für app_role — technischer Manipulationsschutz
  [`init.sql:35`](../../infra/postgres/init.sql#L35)

- `FOR ROLE bordercap` macht Default-Privileges user-spezifisch und deterministisch
  [`init.sql:24`](../../infra/postgres/init.sql#L24)

**Authentifizierung — Keycloak-Realm**

- 4 Realm-Rollen, PKCE-Client, Test-User; Realm-Import via `--import-realm` Flag
  [`realm-export.json:1`](../../infra/keycloak/realm-export.json#L1)

**Backend-API — Hexagonale Architektur**

- `/health`-Endpoint gibt 503 wenn DB oder Keycloak nicht erreichbar (kein false-positive)
  [`main.py:27`](../../backend/src/main.py#L27)

- Alle Settings aus Env-Vars; Defaults = docker-compose-kompatible Werte für Dev
  [`config.py:9`](../../backend/src/config.py#L9)

- Adapter-Schicht: Health-Check isoliert von main.py (hexagonal)
  [`health.py:1`](../../backend/src/adapters/db/health.py#L1)

- AsyncEngine + Session-Factory; kein direkter DB-Zugriff außerhalb adapters/
  [`engine.py:1`](../../backend/src/adapters/db/engine.py#L1)

**SKOS-Codelisten-Service**

- Path-Traversal-Schutz: `isascii() + isalnum()` + JSONDecodeError-Handling
  [`skos_service/main.py:42`](../../skos_service/src/main.py#L42)

**Tests — TDD-Verifikation**

- Kritischster Test: Audit-DELETE als Non-Superuser + SELECT-Prohibition
  [`smoke_steps.py:158`](../../tests/steps/smoke_steps.py#L158)

- Alle Infrastruktur-Scenarios; 5 Scenarios (Backend, SKOS, DB-Schemata, Audit-DELETE, Audit-SELECT)
  [`smoke.feature:1`](../../tests/features/smoke.feature#L1)

- Keycloak Admin-Token + Realm/Rollen/PKCE-Prüfung; nur S256 akzeptiert
  [`keycloak_steps.py:144`](../../tests/steps/keycloak_steps.py#L144)

**Migrationen & Build**

- Async-Alembic-Setup; URL aus Env-Var, kein Hardcoding
  [`alembic/env.py:1`](../../backend/alembic/env.py#L1)

- Multi-Stage Backend-Dockerfile; non-root, Poetry im Builder-Stage
  [`backend/Dockerfile:1`](../../backend/Dockerfile#L1)

## Spec Change Log

- 2026-05-23: Implementierung abgeschlossen. Alle 14 Tasks erledigt. Code Map mit tatsächlichen Dateipfaden befüllt.
- 2026-05-23 (Review-Patches): 11 Patches aus 3-fach-Review angewendet: (1) Audit-Test auf `bordercap_app` (NON-Superuser) umgestellt; (2) SELECT-Prohibition-Test hinzugefügt; (3) Makefile Unhealthy-Detection + Exit-1-bei-Timeout; (4) SKOS `isascii()` + JSONDecodeError-Handling; (5) `skos_service/Dockerfile` Multi-Stage ohne Root-Rollback; (6) Port-Bindings nur noch in `docker-compose.override.yml`; (7) PKCE-Test: "plain" entfernt (nur S256); (8) `ALTER DEFAULT PRIVILEGES FOR ROLE bordercap`; (9) AC-Text: "audit.logs" → "audit.events"; (10) `bordercap_app` Non-Superuser-Rolle in 00_roles.sql; (11) `backend/src/__init__.py` fehlend nachgetragen. KEEP: hexagonale Struktur, Behave-TDD-First, audit-only-INSERT via Grant.

