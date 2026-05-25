# BorderCapControl

Kapazitäts- und Bettenplanungssystem für BAMF-Grenzverfahren gemäß GEAS-Reform.
Sachbearbeiter (BAMF + Länder) verwalten Betten in Grenzeinrichtungen und halten EU-Kontingentquoten ein.

---

## Systemüberblick

```
Browser (React + MUI)
    │ PKCE / JWT
    ▼
FastAPI Backend  ──→  PostgreSQL 16
    │                   (6 Schemata: capacity, persons, reservations,
    │                    tasks, audit, reference_data)
    ├──→  Keycloak 24   (Realm: bordercapcontrol)
    ├──→  SKOS Service  (Codelisten: Herkunftsländer, Geschlecht)
    └──→  Tileserver GL (Karte)
```

**Backend-Architektur:** Hexagonal — Fachlogik von Infrastruktur getrennt  
**Hintergrundprozesse:** APScheduler (Überkapazitäts-Alerts, 12-Wochen-Warnungen, PDF-Reports)

---

## Voraussetzungen

| Tool | Mindestversion | Zweck |
|------|---------------|-------|
| Docker **oder** Podman | Docker 24 / Podman 4.9 | Alle Backend-Services |
| docker-compose **oder** podman-compose | v2 / 1.2 | Orchestrierung |
| Node.js | 18 LTS | Frontend Dev-Server |
| Python | 3.11 | Seed-Skript (einmalig) |

### Podman auf macOS

```bash
# Einmalig: Podman-Maschine starten
podman machine start

# DOCKER_HOST für Makefile setzen (in Shell-Profil aufnehmen)
export DOCKER_HOST="unix://${HOME}/.local/share/containers/podman/machine/qemu/podman.sock"

# podman-compose installieren (falls nicht vorhanden)
brew install podman-compose
```

> Bei Podman: In allen Befehlen unten `docker compose` durch `podman compose` ersetzen,
> oder `DOCKER_HOST` setzen und `make` wie gewohnt verwenden.

---

## Schnellstart

### 1 — Repository klonen (falls noch nicht geschehen)

```bash
git clone <repo-url> KapzitaetsPlanungsTool
cd KapzitaetsPlanungsTool
```

### 2 — Backend-Services starten

```bash
docker compose up -d --build
```

Warten, bis alle Services healthy sind (dauert beim ersten Build ~3–5 Min):

```bash
docker compose ps
# Alle Services sollten "(healthy)" zeigen
```

Alternativ mit dem Makefile (wartet automatisch auf Healthchecks):

```bash
make dev
```

### 3 — Datenbank migrieren

```bash
docker compose exec backend alembic upgrade head
# oder: make migrate
```

### 4 — Demo-Daten einfügen (einmalig)

```bash
python3 backend/seeds/demo_data.py
```

> Voraussetzung: `pip install psycopg2-binary` falls nicht installiert.
> Das Skript ist idempotent — mehrfaches Ausführen ist sicher.

### 5 — Frontend starten

```bash
cd frontend
npm install          # nur beim ersten Mal
npm run dev          # startet auf http://localhost:3000
```

---

## Erreichbare Services

| Service | URL | Zugangsdaten |
|---------|-----|-------------|
| **Frontend** | http://localhost:3000 | Keycloak-Login (s.u.) |
| **Backend API** (Swagger) | http://localhost:8000/docs | JWT erforderlich |
| **Backend Health** | http://localhost:8000/health | öffentlich |
| **SKOS Codelisten** | http://localhost:8001/docs | öffentlich |
| **Keycloak Admin** | http://localhost:8080/admin | `admin` / `admin_dev` |
| **Tileserver** | http://localhost:8082 | öffentlich |
| **PostgreSQL** | localhost:5432 | `bordercap` / `bordercap_dev` |

---

## Demo-Benutzer

| Benutzername | Passwort | Rolle |
|-------------|---------|-------|
| `admin_user` | `Admin1234!` | System-Admin (alle Rechte) |
| `writer_user` | `Writer1234!` | Sachbearbeiter (Lesen + Schreiben) |
| `reader_user` | `Reader1234!` | Leser (nur Lesen) |

---

## Demo-Daten

Nach `python3 backend/seeds/demo_data.py` sind vorhanden:

| Einrichtung | Kontingent | Notbetten | Räume | Betten | Belegung | Ampel |
|-------------|-----------|-----------|-------|--------|----------|-------|
| Flughafen Frankfurt | 20 | 5 | 2 | 20 | 15 (75 %) | Gelb |
| Flughafen München | 15 | 3 | 2 | 20 | 14 (93 %) | Rot |
| Grenzübergang Passau | 10 | 2 | 2 | 20 | 3 (30 %) | Grün |
| Flughafen Hamburg | 12 | 3 | 2 | 20 | 4 (33 %) | Grün |

EU-Gesamtquote: 55 (wird vom Seed automatisch gesetzt)

---

## Alle Services stoppen

```bash
docker compose down          # Services stoppen, Volumes behalten
docker compose down -v       # Services stoppen + Volumes löschen (sauberer Reset)
# oder: make down
```

---

## Wichtige Makefile-Ziele

```bash
make dev              # Services starten + auf Healthchecks warten
make migrate          # Alembic-Migrationen ausführen
make seed             # Demo-Daten einfügen
make test             # Behave-Integrationstests ausführen
make logs             # Log-Stream aller Services (Ctrl+C zum Beenden)
make down             # Services + Volumes entfernen
make frontend-install # npm install im frontend/-Verzeichnis
make frontend-dev     # Vite Dev-Server starten
```

---

## Projektstruktur

```
KapzitaetsPlanungsTool/
├── backend/                  FastAPI Backend (Python 3.11)
│   ├── src/
│   │   ├── api/              HTTP-Adapter (Router je Feature)
│   │   │   ├── capacity/     Einrichtungen, Räume, Betten, Belegung
│   │   │   ├── reservations/ Reservierungsworkflow
│   │   │   ├── tasks/        Postkorb (Task Inbox)
│   │   │   ├── notifications/ SSE-Stream
│   │   │   ├── suggestions/  Belegungsvorschlag-Solver
│   │   │   ├── map/          Kartendaten-Endpoint
│   │   │   └── reports/      EU-Compliance-PDF (WeasyPrint)
│   │   ├── adapters/
│   │   │   ├── db/           SQLAlchemy AsyncSession
│   │   │   └── keycloak/     JWT-Validierung
│   │   ├── jobs/             APScheduler-Hintergrundprozesse
│   │   └── config.py         Pydantic Settings
│   ├── alembic/              DB-Migrationen (0001–0005)
│   └── seeds/                Demo-Daten
├── frontend/                 React 18 + MUI 5 + Vite
│   └── src/
│       ├── pages/            Dashboard, Drilldown, Reservierungen, Postkorb, Karte
│       └── components/       Wiederverwendbare MUI-Komponenten
├── skos_service/             Codelisten-Service (FastAPI)
├── infra/
│   ├── keycloak/             Realm-Export (3 Benutzer, Rollen)
│   └── postgres/             Initialisierungs-SQL, Rollen
├── tests/                    Behave-Integrationstests
├── docker-compose.yml        Produktions-nahe Basis-Konfiguration
├── docker-compose.override.yml  Dev-Overrides (Port-Bindings, Hot-Reload)
└── Makefile                  Workflow-Einstiegspunkt
```

---

## Bekannte Hinweise

- **Keycloak-Realm-Import:** Keycloak importiert den Realm nur beim ersten Start (leeres Volume).
  Bei Änderungen an `infra/keycloak/realm-export.json` zuerst `docker compose down -v` ausführen.
- **EU-Gesamtquote:** Der Demo-Seed setzt die Quote automatisch auf 55. Nach einem `down -v` einfach den Seed nochmals laufen lassen.
- **Tileserver ohne MBTiles:** Der Tileserver startet, liefert aber ohne Deutschland-MBTiles keine Kacheln.
  Das Frontend fällt automatisch auf den SVG-Fallback zurück.
- **PDF-Report:** `GET /api/reports/eu-compliance?zeitraum=monat` liefert eine PDF-Datei.
  Im Browser direkt aufrufbar (wenn Token im Cookie vorhanden), sonst via Swagger mit Bearer-Token.
