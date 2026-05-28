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
| Docker **oder** Podman | Docker 24 / Podman 4.9 | Alle Services |
| docker-compose **oder** podman-compose | v2 / 1.2 | Orchestrierung |
| Python | 3.11 | Seed-Skript (`make seed`) |

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

## Entwicklungsumgebung (Dev)

### Wie Hot-Reload in Docker funktioniert

Im Dev-Betrieb laufen alle Services in Docker-Containern, lesen den Quellcode
aber **direkt aus deinem lokalen Verzeichnis** über Volume-Mounts:

```
dein Laptop                        Docker-Container
──────────────────────────────────────────────────
./backend/src/  ←── Volume-Mount ──→  /home/appuser/app/src/
./frontend/     ←── Volume-Mount ──→  /app/
```

- **Backend:** Uvicorn läuft mit `--reload` — jede Änderung an `backend/src/` startet den
  Python-Prozess automatisch neu (< 1 s).
- **Frontend:** Vite läuft mit HMR (Hot Module Replacement) und `usePolling: true` — jede
  Änderung an `frontend/src/` wird sofort im Browser sichtbar, ohne Reload (~200 ms).

Du brauchst kein lokales Python-venv und kein lokales `npm run dev` —
**alles läuft im Container, der Code kommt vom Host**.

---

### docker-compose.yml vs. docker-compose.override.yml

Docker Compose lädt **automatisch** beide Dateien und merged sie — kein extra Flag nötig.

```
docker-compose.yml              ← Basis: läuft überall (Prod, CI, Dev)
docker-compose.override.yml     ← Wird automatisch drübergelegt (nur lokal/Dev)
```

| Was steht in `docker-compose.yml` | Was steht in `docker-compose.override.yml` |
|---|---|
| Image-Namen (Docker Hub) | Build-Kontexte (`build: ./backend`) |
| Netzwerke, Volumes | Port-Mappings (`5432:5432`) |
| Healthchecks | Volume-Mounts für Hot-Reload |
| Produktions-Env-Vars | Dev-Env-Variablen |
| — | `KC_HOSTNAME_URL: http://localhost:8080` |
| — | Uvicorn `--reload`, Vite `npm run dev` |

**Faustregel:** Was auf einem Server oder in CI nie gebraucht wird → Override.

Das Override wird von Git getrackt, weil es der einzige Weg ist, den lokalen Stack zu
starten. Für Produktions-Deployments wird eine eigene Datei verwendet (s. unten).

---

### Stack starten

```bash
# Repository klonen
git clone <repo-url> KapzitaetsPlanungsTool
cd KapzitaetsPlanungsTool

# Stack starten (Volume-Mounts aktiv, kein Image-Rebuild)
make dev
```

`make dev` startet alle Services, wartet auf Healthchecks und gibt die Endpoints aus.
Das Frontend (Vite, Port 3000) startet im Hintergrund und braucht ~60 s für `npm install`.

> **Nach Änderungen an einem Dockerfile oder `package.json`** Images neu bauen:
> ```bash
> make build
> ```

### Datenbank und Demo-Daten

```bash
make migrate   # Alembic-Migrationen ausführen (nach erstem Start oder neuen Migrationen)
make seed      # Demo-Daten einfügen (idempotent — mehrfaches Ausführen ist sicher)
```

Nach `make down` (Volumes gelöscht) müssen beide Befehle erneut ausgeführt werden.

---

### Ports anpassen

Ports werden im `docker-compose.override.yml` gesetzt. Beispiel: Frontend auf 4000
statt 3000 verlegen:

```yaml
# docker-compose.override.yml
services:
  frontend:
    ports:
      - "4000:3000"   # HOST:CONTAINER — nur die linke Zahl ändern
```

Danach den Stack neu starten: `make dev`

> Die rechte Zahl (Container-Port) darf nicht geändert werden — sie ist im
> Dockerfile und in der Anwendungskonfiguration fest verdrahtet.

Alle Standard-Ports im Überblick:

| Service | Container-Port | Standard Host-Port | Override-Schlüssel |
|---------|---------------|-------------------|-------------------|
| Frontend (Vite) | 3000 | 3000 | `frontend.ports` |
| Backend API | 8000 | 8000 | `backend.ports` |
| SKOS Service | 8001 | 8001 | `skos_service.ports` |
| Keycloak | 8080 | 8080 | `keycloak.ports` |
| Tileserver | 8080 | 8082 | `tileserver.ports` |
| PostgreSQL | 5432 | 5432 | `postgres.ports` |

> **Keycloak-Sonderfall:** Wenn du den Keycloak-Host-Port änderst, muss auch
> `KC_HOSTNAME_URL` im Override aktualisiert werden:
> ```yaml
> keycloak:
>   ports:
>     - "9090:8080"
>   environment:
>     KC_HOSTNAME_URL: "http://localhost:9090"
>     KC_HOSTNAME_ADMIN_URL: "http://localhost:9090"
> ```

---

### System prüfen

```bash
# Alle Container und ihr Status
make logs           # Log-Stream aller Services (Ctrl+C zum Beenden)
podman compose ps   # oder: docker compose ps

# Einzelne Services prüfen
curl http://localhost:8000/health          # Backend Healthcheck
curl http://localhost:8001/health          # SKOS Service
curl http://localhost:8080/health/ready    # Keycloak

# API im Browser
open http://localhost:8000/docs            # Swagger UI (Backend)
open http://localhost:8001/docs            # Swagger UI (SKOS)
open http://localhost:8080/admin           # Keycloak Admin (admin / admin_dev)
```

Alle Core-Services zeigen `(healthy)` in `compose ps`, sobald sie bereit sind.
Das Frontend hat keinen Healthcheck — es startet im Hintergrund.

---

### Anwendung starten

```bash
open http://localhost:3000
```

Login mit einem der Demo-Benutzer (s. Abschnitt [Demo-Benutzer](#demo-benutzer)).
Der Browser wird zu Keycloak (`http://localhost:8080`) weitergeleitet und nach
erfolgreichem Login zurück zur Anwendung.

---

### Stack stoppen

```bash
make down                    # Services + Volumes entfernen (sauberer Reset)
podman compose down          # Services stoppen, Volumes behalten
podman compose down -v       # Services stoppen + Volumes löschen
```

---

## Produktions-Deployment

Für Produktion wird das Override **nicht** verwendet. Stattdessen eine eigene
`docker-compose.prod.yml` anlegen und explizit angeben:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

Eine minimale `docker-compose.prod.yml` für den Anfang:

```yaml
version: "3.9"

services:
  postgres:
    environment:
      POSTGRES_PASSWORD: "<sicheres-passwort>"

  keycloak:
    environment:
      KEYCLOAK_ADMIN_PASSWORD: "<sicheres-passwort>"
      KC_HOSTNAME_URL: "https://meine-domain.de"
      KC_HOSTNAME_ADMIN_URL: "https://meine-domain.de"
      KC_PROXY: "edge"       # wenn ein Reverse-Proxy (nginx/Traefik) vorgelagert ist

  backend:
    environment:
      DATABASE_URL: "postgresql+asyncpg://bordercap:<passwort>@postgres:5432/bordercap"
      KEYCLOAK_URL: "http://keycloak:8080"
      KEYCLOAK_PUBLIC_URL: "https://meine-domain.de"

  frontend:
    image: bosenet/bordercapcontrol-frontend:latest   # gebautes Prod-Image
```

> **Wichtig:** In Produktion keine Port-Mappings für PostgreSQL und Keycloak nach
> außen öffnen. Nur Frontend (80/443) und ggf. Backend-API nach außen exponieren.

---

## Erreichbare Services (Dev)

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

### Vordefinierte Rollen

| Rolle | Beschreibung |
|-------|-------------|
| `system-admin` | Globaler Vollzugriff — alle Einrichtungen, Nutzerverwaltung |
| `location-admin` | Admin für zugewiesenen Standort — Räume, Betten, Kontingent |
| `writer` | Sachbearbeiter — Belegung, Reservierungen, Postkorb bearbeiten |
| `reader` | Lesezugriff — alle Daten einsehen, keine Änderungen |

### Benutzerkonten

| Benutzername | Passwort | Rolle | Standort |
|-------------|---------|-------|---------|
| `admin_user` | `Admin1234!` | system-admin | Frankfurt (Default) |
| `writer_user` | `Writer1234!` | writer | Frankfurt |
| `reader_user` | `Reader1234!` | reader | Passau |
| `sb_frankfurt` | `SbFfm2024!` | writer | Frankfurt |
| `sb_muenchen` | `SbMuc2024!` | writer | München |
| `sb_passau` | `SbPau2024!` | writer | Passau |
| `sb_hamburg` | `SbHam2024!` | writer | Hamburg |
| `loc_admin_ffm` | `LocAdmin2024!` | location-admin | Frankfurt |
| `leser_bund` | `Leser2024!` | reader | Frankfurt (bundesweit) |

> **Hinweis:** Der `location_id`-Claim im JWT bestimmt, welche Einrichtung im Dashboard hervorgehoben wird.
> System-Admins sehen alle Einrichtungen mit vollem Zugriff.
> Nach Keycloak-Neustart (`make down && make dev`) werden alle Benutzer automatisch importiert.

---

## Demo-Daten

Nach `make seed` sind vorhanden:

### Einrichtungen

| Einrichtung | Kontingent | Notbetten | Räume | Betten | Belegung | Ampel |
|-------------|-----------|-----------|-------|--------|----------|-------|
| Flughafen Frankfurt | 20 | 5 | 4 | 20 | 15 (75 %) | Gelb |
| Flughafen München | 15 | 3 | 3 | 15 | 14 (93 %) | Rot |
| Grenzübergang Passau | 10 | 2 | 2 | 10 | 3 (30 %) | Grün |
| Flughafen Hamburg | 12 | 3 | 3 | 12 | 5 (42 %) | Grün |

EU-Gesamtquote: 800 (wird vom Seed automatisch gesetzt)

### Räume pro Einrichtung

| Einrichtung | Raum | Designation | Betten |
|-------------|------|------------|--------|
| Frankfurt | Raum A | Männer | 6 |
| Frankfurt | Raum B | Frauen | 6 |
| Frankfurt | Raum C | Männer | 4 |
| Frankfurt | Raum D | Gemischt (Familie) | 4 |
| München | Raum A | Männer | 6 |
| München | Raum B | Frauen | 6 |
| München | Raum C | Frauen | 3 |
| Passau | Raum A | Männer | 5 |
| Passau | Raum B | Frauen | 5 |
| Hamburg | Raum A | Männer | 4 |
| Hamburg | Raum B | Frauen | 4 |
| Hamburg | Raum C | Gemischt (Familie) | 4 |

### Labels-System

Das System unterstützt Hinweis-Labels für Räume, Betten und Belegungen:

- **Raum-Labels:** Rollstuhlgerecht, Erdgeschoss, Ruhig, Familienraum, Klimaanlage, …
- **Bett-Labels:** Unteres Bett, Oberes Bett, Breites Bett, Kinderbett, …
- **Belegungs-Labels (nicht verbindlich):** Kind, Arabisch, Farsi/Dari, Türkisch, Halal, Mobilitätseinschränkung, …

> Labels sind operative Hinweise zur Unterstützung der Bett-Zuweisung.
> Sie sind **nicht AZR-relevant**, **nicht rechtlich bindend** und erscheinen
> nicht in offiziellen Berichten. DSGVO Art. 9 beachten bei Belegungs-Labels.

---

## Makefile-Referenz

```bash
make dev       # Stack starten (kein Rebuild — Volume-Mounts für Hot-Reload)
make build     # Stack starten + Images neu bauen (nach Dockerfile-/Dep-Änderungen)
make migrate   # Alembic-Migrationen ausführen
make seed      # Demo-Daten einfügen (idempotent)
make test      # Behave-Integrationstests ausführen
make logs      # Log-Stream aller Services (Ctrl+C zum Beenden)
make down      # Services + Volumes entfernen (sauberer Reset)
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
│   ├── alembic/              DB-Migrationen (0001–0006)
│   └── seeds/                Demo-Daten
├── frontend/                 React 18 + MUI 5 + Vite
│   └── src/
│       ├── pages/            Dashboard, Drilldown, Reservierungen, Postkorb, Karte
│       └── components/       Wiederverwendbare MUI-Komponenten
├── skos_service/             Codelisten-Service (FastAPI)
├── infra/
│   ├── keycloak/             Realm-Export (Benutzer, Rollen, Client-Config)
│   └── postgres/             Initialisierungs-SQL, Rollen
├── tests/                    Behave-Integrationstests
├── docker-compose.yml        Basis-Konfiguration (Prod-tauglich)
├── docker-compose.override.yml  Dev-Overrides (Port-Bindings, Hot-Reload, lokale Env-Vars)
└── Makefile                  Workflow-Einstiegspunkt
```

---

## Bekannte Hinweise

- **Keycloak-Realm-Import:** Keycloak importiert den Realm nur beim ersten Start (leeres Volume).
  Bei Änderungen an `infra/keycloak/realm-export.json` zuerst `make down` ausführen.
- **EU-Gesamtquote:** Der Demo-Seed setzt die Quote automatisch auf 800. Nach einem `make down` einfach `make seed` erneut ausführen.
- **Tileserver ohne MBTiles:** Der Tileserver startet, liefert aber ohne Deutschland-MBTiles keine Kacheln.
  Das Frontend fällt automatisch auf den SVG-Fallback zurück.
- **PDF-Report:** `GET /api/reports/eu-compliance?zeitraum=monat` liefert eine PDF-Datei.
  Im Browser direkt aufrufbar (wenn Token im Cookie vorhanden), sonst via Swagger mit Bearer-Token.
