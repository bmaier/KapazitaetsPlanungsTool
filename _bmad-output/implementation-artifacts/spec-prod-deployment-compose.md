---
title: 'Produktions-Deployment: docker-compose.prod.yml + .env.prod.example'
type: 'chore'
created: '2026-06-01'
status: 'done'
baseline_commit: '88dd997fc1e2890320741aba55bb574a233a8115'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Das Projekt hat nur einen Dev-Stack (`docker-compose.yml` + `docker-compose.override.yml`) mit hartkodierten Dev-Passwörtern, `start-dev`-Keycloak (ohne Produktions-Sicherheitscontrols) und offenen Ports für alle Services. Ein Produktiv-Deployment ist so nicht möglich.

**Approach:** Eine `docker-compose.prod.yml`-Override-Datei wird erstellt, die den Dev-Stack produktionstauglich macht — Keycloak im `start`-Modus, nur Frontend-Port exponiert, alle Credentials über `.env.prod`-Variablen. Die hartcodierte `bordercap_app`-Password in `00_roles.sql` wird durch ein parametrisierbares Shell-Skript ersetzt.

## Boundaries & Constraints

**Always:**
- `docker-compose.prod.yml` ist eine Compose-Override-Datei; Verwendung: `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d`
- Nur der Frontend-Port (80) wird nach außen exponiert — alle anderen Services bleiben im internen `bordercap_net`
- Keycloak verwendet `start --import-realm` (statt `start-dev`) mit `KC_PROXY=edge` und `KC_HTTP_ENABLED=true`, da TLS am externen Reverse Proxy terminiert
- `.env.prod.example` enthält KEINE echten Credentials — nur Platzhalter mit Kommentaren
- `infra/postgres/00_roles.sh` ersetzt `infra/postgres/00_roles.sql` (gleiches Verhalten, aber Password aus Env-Var `${POSTGRES_APP_PASSWORD}`)
- SMTP-Credentials dürfen nicht in `realm-export.json` oder committed Dateien stehen

**Ask First:**
- Soll `skos_service` in Produktion weiter über das eigene Build-Image laufen oder wird ein fertiges Pre-built-Image erwartet?
- Soll der `tileserver` in Produktion aktiv sein, oder ist er optional/deaktiviert?

**Never:**
- Keinen `--reload` / Hot-Reload in Prod-Compose
- Keine Datenbankports, Backend-Ports oder Keycloak-Ports nach außen exponieren
- `docker-compose.yml` (Basis-Datei) nicht verändern
- `realm-export.json` nicht mit Prod-Credentials befüllen
- Keinen `mailpit`-Service in Prod-Compose aufnehmen

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Erster Start (frische DB) | `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d` mit befüllter `.env.prod` | Alle Services starten, DB-Schemas erstellt, `bordercap_app` mit Prod-Passwort angelegt, Keycloak-Realm importiert | Schlägt fehl wenn Pflicht-Env-Vars fehlen (POSTGRES_PASSWORD, KEYCLOAK_PUBLIC_URL) |
| Wiederholter Start (DB vorhanden) | Gleich wie oben | Init-Skripte übersprungen (PG-Daten vorhanden), Keycloak startet ohne Re-Import (Realm bereits vorhanden) | — |
| Fehlendes KEYCLOAK_PUBLIC_URL | `.env.prod` ohne `KEYCLOAK_PUBLIC_URL` | Keycloak startet, aber OIDC-Redirects scheitern im Browser | Betreiber-Fehler; muss in `.env.prod` gesetzt werden |

</frozen-after-approval>

## Code Map

- `docker-compose.yml` — Basis-Compose ohne Port-Bindings; bleibt unverändert
- `docker-compose.override.yml` — Dev-Only-Overrides (Ports, Hot-Reload, Mailpit); wird in Prod NICHT verwendet
- `docker-compose.prod.yml` — NEU: Prod-Override; ergänzt KC-Prod-Config + Frontend-Port
- `.env.example` — Dev-Template; bleibt unverändert
- `.env.prod.example` — NEU: Prod-Template mit Prod-Pflichtfeldern
- `infra/postgres/00_roles.sql` — wird ersetzt durch `00_roles.sh`
- `infra/postgres/00_roles.sh` — NEU: erstellt Rollen mit Passwort aus `${POSTGRES_APP_PASSWORD}`
- `infra/postgres/init.sql` — bleibt unverändert (Schemata/Grants)

## Tasks & Acceptance

**Execution:**

- [x] `infra/postgres/00_roles.sh` -- CREATE (neu, ersetzt `00_roles.sql`): Shell-Skript das `bordercap_app`-Rolle mit `${POSTGRES_APP_PASSWORD:-bordercap_app_dev}` anlegt; kopiert Logik aus `00_roles.sql` (Rollen-Prüfung + Grants), nutzt `psql` mit heredoc; Datei ausführbar (`chmod +x`) -- Ohne diesen Fix sind DB-Credentials in Prod hardkodiert
- [x] `infra/postgres/00_roles.sql` -- DELETE: Datei entfernen, da durch `00_roles.sh` ersetzt -- PostgreSQL-Init lädt beide, `.sh` vor `.sql` alphabetisch; Duplikat vermeiden
- [x] `docker-compose.prod.yml` -- CREATE: Compose-Override mit folgenden Overrides: (1) `postgres`: `POSTGRES_APP_PASSWORD` env var hinzufügen; (2) `keycloak`: command auf `start --import-realm`, Env-Vars `KC_PROXY=edge`, `KC_HTTP_ENABLED=true`, `KC_HOSTNAME_URL=${KEYCLOAK_PUBLIC_URL}`, `KC_HOSTNAME_ADMIN_URL=${KEYCLOAK_PUBLIC_URL}`, Themes-Volume; (3) `frontend`: Port `${FRONTEND_PORT:-80}:80` exponieren -- Prod-Stack braucht KC-Produktionsmodus und öffentlichen Frontend-Port
- [x] `.env.prod.example` -- CREATE: Vorlage mit allen Prod-Pflichtfeldern: `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` (kein Default), `POSTGRES_APP_USER`, `POSTGRES_APP_PASSWORD` (kein Default), `KEYCLOAK_ADMIN`, `KEYCLOAK_ADMIN_PASSWORD` (kein Default), `KEYCLOAK_PUBLIC_URL` (kein Default — Beispiel: `https://bordercap.behoerde.de`), `DATABASE_URL` (mit `bordercap_app`-User), `KEYCLOAK_REALM`, `KEYCLOAK_CLIENT_ID`, `FRONTEND_PORT` (Default 80), SMTP-Variablen als auskommentierte Beispiele -- Betreiber braucht eine klare Vorlage ohne Rätselraten

**Acceptance Criteria:**

- Given eine frische Linux-VM mit Docker/Podman, `.env.prod` aus Template befüllt und Images gepullt, when `docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.prod up -d` ausgeführt wird, then sind alle Services `healthy` und `http://<host>:80` liefert die Login-Seite
- Given `docker compose ... ps`, when alle Services laufen, then sind KEINE Ports außer `80` (Frontend) nach außen gebunden
- Given Keycloak-Startlog, when `start` Modus aktiv, then enthält das Log NICHT `start-dev` und enthält `Keycloak started in production mode`
- Given `docker exec postgres psql -U bordercap -c "\du"`, when Roles abgefragt, then hat `bordercap_app` kein SUPERUSER-Flag und existiert mit dem konfigurierten Prod-Passwort
- Given `.env.prod.example`, when geprüft, then enthält die Datei keine echten Passwörter und POSTGRES_PASSWORD / KEYCLOAK_ADMIN_PASSWORD haben leere oder Platzhalter-Werte

## Design Notes

**Warum Override-Compose statt eigenständiger Datei:**
Der Basis-`docker-compose.yml` hat keine Dev-spezifischen Settings — er ist bereits „neutral". `docker-compose.override.yml` fügt nur Dev-Tooling hinzu. Das Prod-Override ergänzt nur was wirklich prod-spezifisch ist (KC-Modus, Frontend-Port). Das verhindert Duplizierung und stellt sicher, dass Änderungen am Basis-Stack (z.B. neue Services) automatisch in Prod übernommen werden.

**Keycloak `start` vs. `start-dev`:**
`start-dev` deaktiviert alle Produktions-Security-Checks (z.B. Hostname-Validierung, sichere Cookies). In Prod muss `start` mit `KC_PROXY=edge` verwendet werden, da TLS am Reverse Proxy terminiert. `KC_HTTP_ENABLED=true` erlaubt internen HTTP-Traffic (KC↔Frontend im Docker-Netz).

**`00_roles.sh` statt `.sql`:**
PostgreSQL-Init-Skripte als `.sh` haben Zugriff auf Shell-Env-Vars. Die `.sql`-Variante kann keine Env-Vars interpolieren. Alphabetische Reihenfolge bleibt erhalten: `00_roles.sh` läuft vor `01_init.sql`.

**Deferred (nächste Story):** Backend-Migration-Entrypoint (`alembic upgrade head` vor `uvicorn`-Start) — heute läuft Alembic manuell oder via separatem Container.

## Verification

**Commands:**
- `docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.prod config` -- expected: Kein `start-dev` in Keycloak-Command, Port 80 bei Frontend, keine anderen Ports
- `docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.prod ps` -- expected: Alle Services `healthy` nach ca. 90s
- `docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.prod port frontend 80` -- expected: `0.0.0.0:80`
- `grep -r "bordercap_app_dev\|admin_dev\|bordercap_dev" .env.prod.example` -- expected: kein Treffer (keine Dev-Defaults in Prod-Template)

**Manual checks (if no CLI):**
- Keycloak-Log auf `Started in production mode` prüfen (nicht `dev mode`)
- `netstat -tlnp` auf Host: nur Port 80 (oder `$FRONTEND_PORT`) soll für Docker-Services gebunden sein

## Spec Change Log


## Suggested Review Order

**PostgreSQL Init — Password parametrization (entry point)**

- Shell passes password via `--set` flag; `:'pg_password'` quotes special chars safely in SQL
  [`00_roles.sh:12`](../../infra/postgres/00_roles.sh#L12)

- `ELSE ALTER ROLE` ensures password rotation works on redeployment (not just first run)
  [`00_roles.sh:40`](../../infra/postgres/00_roles.sh#L40)

**Compose Override — Production mode switching**

- `start --import-realm` replaces `start-dev`; enables all Keycloak production security checks
  [`docker-compose.prod.yml:36`](../../docker-compose.prod.yml#L36)

- `KC_PROXY=edge` + `KC_HTTP_ENABLED=true` for TLS-terminated reverse proxy pattern
  [`docker-compose.prod.yml:38`](../../docker-compose.prod.yml#L38)

- `POSTGRES_APP_PASSWORD` env var wired through to the init script
  [`docker-compose.prod.yml:24`](../../docker-compose.prod.yml#L24)

- Only `${FRONTEND_PORT:-80}:80` exposed; all other services stay internal
  [`docker-compose.prod.yml:51`](../../docker-compose.prod.yml#L51)

**Environment Template — Operator config**

- `POSTGRES_APP_PASSWORD` and `POSTGRES_PASSWORD` marked PFLICHTFELD (mandatory, no default)
  [`env.prod.example:20`](../../.env.prod.example#L20)

- `KEYCLOAK_PUBLIC_URL` marked PFLICHTFELD with example URL; without it OIDC redirects break
  [`env.prod.example:45`](../../.env.prod.example#L45)

**Security / Housekeeping**

- `.env.prod` added to gitignore so operator credentials are never accidentally committed
  [`.gitignore:28`](../../.gitignore#L28)
