---
project_name: 'BorderCapControl'
user_name: 'Berthold'
date: '2026-05-31'
sections_completed: ['technology_stack', 'backend_architecture', 'frontend_patterns', 'domain_model', 'auth_keycloak', 'unspecced_features', 'audit_rules']
status: 'complete'
rule_count: 47
optimized_for_llm: true
---

# Project Context — BorderCapControl

_Kritische Regeln und Patterns für AI-Agents. Fokus auf nicht-offensichtliche Details._

---

## Technology Stack & Versions

### Backend
- Python 3.11 · FastAPI 0.111 · **Pydantic v2** (mit FastAPI 0.111 gebündelt — v1-Syntax ist silent broken)
- SQLAlchemy 2.0 async · asyncpg 0.29 · Alembic 1.13
- APScheduler >=3.10,<4 (AsyncIOScheduler) — **v4 hat Breaking Changes, nicht upgraden**
- python-jose 3.3 (JWT-Validierung gegen Keycloak JWKS) · pydantic-settings 2.2
- httpx 0.27 · WeasyPrint 62 — **v63+ hat Breaking PDF-API; braucht System-Libs: libpango-1.0-0, libcairo2, libgdk-pixbuf2.0-0 im Docker-Image**
- PostgreSQL (Schemas: `capacity`, `audit`, `tasks`, `reservations`) · Keycloak 24

### Frontend
- React 18.2 · TypeScript 5.2 strict · Vite 5.2 · **MUI 5.15 (v5 — kein Upgrade auf v6, Breaking Changes)**
- react-router-dom 6.22 (BrowserRouter-Variante, kein Data Router / createBrowserRouter)
- keycloak-js 24.0.3 — **muss zur Keycloak-Server-Version passen (beide 24.x)**
- Leaflet 1.9.4 · react-leaflet 4.2.1
- react-markdown 10.1 · remark-gfm 4.0 · @microsoft/fetch-event-source 2.0

### Infra
- Docker Compose (Podman-kompatibel) · Nginx 1.27-alpine (Frontend-Container)
- Images: `bosenet/bordercapcontrol-{backend,frontend,skos}:latest`
- Alembic-Migrationen: aktuell `0019_beds_bett_nummer_partial_unique`

### Kritische Versions-Constraints

- **APScheduler**: `>=3.10,<4` — v4 ist ein harter Break im AsyncIOScheduler
- **WeasyPrint**: `==62.*` — v63+ bricht PDF-API; Docker-Basis-Image benötigt `libpango-1.0-0 libcairo2 libgdk-pixbuf2.0-0`
- **MUI**: `^5.x` — kein Upgrade auf v6; `makeStyles` ist deprecated, nur `sx`-Prop oder `styled()` verwenden
- **keycloak-js**: Version muss exakt zur Keycloak-Server-Version passen
- **Pydantic**: v2 aktiv — `@validator` → `@field_validator`, `orm_mode=True` → `model_config = ConfigDict(from_attributes=True)`, `dict()` → `model_dump()`
- **TypeScript strict**: `noUnusedLocals` + `noUnusedParameters` aktiv — Build bricht bei Verstößen
- **react-router-dom**: v6-Syntax (`useNavigate`, nicht `useHistory`)

---

## Backend-Architektur — Hexagonale Struktur

### Schichtentrennung (harte Regeln)

```
src/
  domain/          ← KEIN FastAPI-Import, KEIN SQLAlchemy-Import, KEIN ORM
    capacity/      entities.py, rules.py, value_objects.py
    reservations/  entities.py, rules.py
    tasks/         entities.py
  adapters/        ← KEIN Domain-Business-Logic, KEIN FastAPI-Import
    db/            models.py (ORM), *_repo.py (DB-Zugriff), engine.py
    keycloak/      jwt.py (Token-Validierung)
  api/             ← HTTP ↔ Pydantic Schemas, Session-Dependency, Domain-Error → HTTP
    capacity/      router.py, schemas.py
    reservations/  router.py, schemas.py
    ...
  jobs/            scheduler.py, jobs.py (APScheduler-Jobs)
  main.py          ← Orchestrierung only, keine Fachlogik
```

**Verstöße gegen diese Schichtentrennung sind verboten:**
- `domain/` darf NICHT importieren: `fastapi`, `sqlalchemy`, `asyncpg`, `httpx`
- `adapters/db/` darf NICHT importieren: `fastapi`, `domain.rules`
- `api/*/schemas.py` sind reine Pydantic-DTOs — **kein SQLAlchemy-Import, keine Domain-Entity-Instanziierung**

### SQLAlchemy 2.0 Regeln

- **Nur `mapped_column()`** — `Column()` ist verboten (erzeugt stille Type-Fehler)
- **Immer `await session.execute()`** — ohne `await` ist asyncpg-Hänger, kein Exception
- `scalars()` auf dem Result-Proxy aufrufen, nicht auf dem Coroutine-Objekt
- Session-Pattern: `async with AsyncSessionFactory() as session:` + `async with session.begin():`
- Alle Models haben explizites `__table_args__ = {"schema": "capacity"}` (oder jeweiliges Schema)

### Alembic-Migrationsregeln

- Dateiname-Schema: **`NNNN_<slug>.py`** — vierstellig, nullgepaddet, lückenlos (0001, 0002, ..., 0014)
- **Kein** `alembic revision --autogenerate` für Produktiv-Migrationen — erzeugt UUID-Dateinamen
- `alembic revision -m "slug"` und dann manuell `revision_id` setzen
- `env.py` hat `include_schemas=True` — Autogenerate erkennt sonst Nicht-Default-Schema-Änderungen nicht
- Aktuelle Head: `0014_audit_extended`

### Auth / Keycloak

- Alle `/api/`-Routen haben `dependencies=[Depends(get_current_user)]` in `main.py` — **nur `/health` ist offen**
- Rollen-Extraktion im JWT: `token["realm_access"]["roles"]` (Realm-Rollen) — **nicht** `token["roles"]`
- Rollenhierarchie: `system-admin` > `location-admin` > `writer` > `reader`
- JWKS-Cache TTL = 300s (`src/adapters/keycloak/jwt.py`) — nie synchron refreshen
- `X-Location-Id`-Header: Typ UUID, Extraktion via FastAPI `Header()`-Dependency im Router — **bei allen mutierenden Requests Pflicht**

### APScheduler — Deployment-Constraint

- `AsyncIOScheduler` läuft **ohne persistenten Jobstore** — bei `uvicorn --workers N` laufen Jobs N-mal
- **Deployment mit Single Worker** oder Jobstore-Migration erforderlich, bevor Multi-Worker aktiviert wird
- Registrierte Jobs: `job_12wochen_warnung` (06:00), `job_notbett_warnung` (06:05), `job_ueberkapazitaet` (06:10), `job_belegungsbericht` (Mon 07:00), `job_cleanup` (03:00)

---

## Frontend-Patterns

### API-Client

- **Immer `useApiClient()`** — niemals direktes `fetch()` in Komponenten
- `useApiClient()` gibt `{ get, post, patch, del }` zurück — stabilisiert über Refs (kein useEffect-Loop)
- `X-Location-Id` wird automatisch aus `useKeycloak().locationId` gesetzt
- Token-Refresh: `kc.updateToken(60)` vor jedem Call — bei Fehler → `kc.logout()`

### Umgebungsvariablen (Vite)

- Nur `VITE_`-prefixierte Variablen sind im Frontend verfügbar: `VITE_BACKEND_URL`, `VITE_KEYCLOAK_URL`, `VITE_TILESERVER_URL`, `VITE_SUPPORT_URL`
- Deklaration in `frontend/src/vite-env.d.ts` im `ImportMetaEnv`-Interface — neue Vars hier eintragen
- Vite-Dev-Server Proxy: `/api` → Backend, `/realms` + `/resources` → Keycloak, `/tiles` → Tileserver (in `vite.config.ts`)

### MUI / Styling

- **Kein `makeStyles`** — nur `sx`-Prop oder `styled()` aus `@mui/material/styles`
- Theme definiert in `frontend/src/App.tsx` — Farben: primary `#003366`, dark `#002147`
- `ThemeProvider` wraps alles in `App.tsx`

### React 18 Strict Mode

- `useEffect` läuft in Entwicklung **zweimal** — Side-Effects mit API-Calls können doppelte POST-Requests erzeugen
- Pattern: API-Calls nur bei tatsächlicher User-Interaktion oder mit AbortController-Cleanup

### Rollen-Check im Frontend

```typescript
const roles = (tokenParsed?.realm_access as { roles?: string[] })?.roles ?? []
const isSystemAdmin = roles.includes('system-admin')
```

---

## Domain-Modell — Kritische Regeln

### Bett-Status-Matrix

| BedType | room_type | Kontingent-relevant | EU-Quota |
|---------|-----------|---------------------|----------|
| KONTINGENT | STANDARD | Ja | Ja |
| NOTBETT | STANDARD | Nein | Nein |
| WARTEPLATZ | WARTEBEREICH | Nein | Nein |
| DOPPEL | STANDARD | Ja | Ja (deprecated, ausgeblendet) |

### Reservierungsstatus-Übergänge

```
PENDING → CONFIRMED (mit confirmed_bed_id + suggested_bed_id)
PENDING → REJECTED
PENDING → CANCELLED
CONFIRMED → TRANSFERRED (Einchecken — erzeugt Occupancy)
CONFIRMED → CANCELLED
```
Ungültige Übergänge → HTTP 409. `SELECT ... FOR UPDATE` auf Reservation-Zeile bei confirm/reject/cancel.

### Transfer-Historisierung (Ein-Platz-Regel)

Beim `CONFIRMED → TRANSFERRED`-Übergang (`POST /api/reservations/{id}/transfer`):
- Die **Quell-Belegung** (`persons.occupants`) wird **niemals gelöscht** — sie wird mit `belegung_ende = date.today()` abgeschlossen.
- Eine **neue Belegung** wird am `confirmed_bed_id` mit dem Reservierungs-`belegung_start`/`belegung_ende` angelegt.
- Jede Person ist damit zu jedem Zeitpunkt einem Platz zuordenbar (DSGVO-Nachweispflicht).
- Implementiert in: `reservation_repo.py:transfer()` — `spec-transfer-historisierung.md`

### Vollperioden-Validierungskaskade

Alle Belegungen und Reservierungen werden gegen den **gesamten** Zeitraum `[belegung_start, belegung_ende)` auf 3 Ebenen validiert:

| Ebene | Felder | Prüfung |
|-------|--------|---------|
| Einrichtung | `is_active`, `valid_from`, `valid_until` | start ≥ valid_from, ende ≤ valid_until, is_active = true |
| Raum | `valid_from`, `valid_until` | start ≥ valid_from, ende ≤ valid_until |
| Bett | `valid_from`, `deaktiviert_ab` | start ≥ valid_from, ende ≤ deaktiviert_ab |

- **Bettsuche**: SQL filtert Betten deren Gültigkeitsfenster kürzer als der angefragte Zeitraum ist.
- **`period_available`**: `BedStatusItem` enthält dieses Computed-Flag (server-seitig berechnet) — Frontend filtert Betten mit `period_available === false` aus Auswahllisten.
- Implementiert in: `capacity/router.py`, `suggestions/router.py`, `reservations/router.py` — `spec-vollperioden-validierung.md`

### Verlegungsanfragen — Rollenregeln (harte Invarianten)

**Wer darf stornieren (POST /cancel, DELETE /reservations/{id}):**
- Nur `requester_location_id` (anfragende Einrichtung) + `system-admin`
- `target_location_id` darf **niemals** stornieren — nur `confirm` oder `reject`
- `check_retraction_allowed` in `domain/reservations/rules.py` — Prüfbedingung: `location_id != req.requester_location_id`

**Bett-Klick-Verhalten im Drilldown (Drilldown.tsx `handleBedClick`):**

| Bett-Zustand | Einrichtungsrolle | Aktion |
|---|---|---|
| FREI + `pending_reservation_id` | Ziel-Einrichtung | `navigate('/reservations?highlight={pending_reservation_id}')` — **kein Dialog** |
| BELEGT + `has_pending_transfer` + `outgoing_reservation_id` | Requester-Einrichtung | Dialog mit Stornieren-Button öffnen |
| VORGEMERKT + `reservation_id` | beide | `navigate('/reservations?highlight={reservation_id}')` |

**Stornieren-Button im Dialog:** Guard `canEdit && transferDialogDetail?.requester_location_id === id` — schützt, dass nur die Drilldown-Einrichtung die Anfrage stellte, den Button sieht.

> Diese Regeln wurden durch `spec-verlegungsanfrage-berechtigung-klick-korrektur.md` eingeführt. Die ältere `spec-verlegungsanfrage-dialog-stornierung.md` enthält an mehreren Stellen **falsche** Gegenteilregeln — diese Spec nicht als Referenz für Rollenlogik verwenden.

### DSGVO-Minimalprofil

Kein `name`-Feld auf Belegungen oder Reservierungen. Nur: `azr_id`, `alias_id` (optional), `geschlecht` (M/W/D), `belegung_start`, `belegung_ende`, `labels: TEXT[]`

### Geschlechtsdesignation

Wird **aus Labels abgeleitet**, nicht direkt gesetzt. Automatisch gesetzt beim ersten M/W-Belegen eines Raums ohne Label. Labels: `Männer`, `Frauen`, `Familie`, `Familienraum`, `Gemischt`.

---

## Nicht durch Specs abgedeckte Features (ohne BMad implementiert)

Diese Features existieren im Code, haben aber keine Spec-Datei in `_bmad-output/implementation-artifacts/`:

| Feature | Schlüsseldateien |
|---------|-----------------|
| Wartebereich / Warteplatz | `alembic/0011_ankunftsbereich.py`, `0013_wartebereich.py`, `domain/capacity/value_objects.py` |
| suggested_bed_id in Reservierung | `alembic/0012_suggested_bed_id.py`, `api/reservations/` |
| VORGEMERKT-Status + 2-Schritt-Bestätigungsdialog | `frontend/src/pages/Reservations.tsx`, `TaskInbox.tsx` |
| Gruppenverlegung aus Wartebereich (Multi-Select) | `frontend/src/pages/Drilldown.tsx` |
| M/W/D-Gruppen-Anzahl im Solver | `api/suggestions/router.py`, `schemas.py` |
| BAMF-Branding (Logo, Footer, rechtliche Seiten) | `frontend/src/components/Footer.tsx`, `pages/Impressum.tsx`, `pages/Datenschutz.tsx`, `pages/Lizenzen.tsx` |
| Filterleiste Verlegungsseite | `frontend/src/pages/Reservations.tsx` |
| Help-Tooltips (HelpTooltip-Komponente) | `frontend/src/components/HelpTooltip.tsx` |
| Einrichtungs-Shortcut im NavBar | `frontend/src/components/NavBar.tsx` |
| Belegungszeitraum editierbar | `frontend/src/pages/Drilldown.tsx` |
| Protokoll für alle Rollen sichtbar | `frontend/src/components/NavBar.tsx` |

## Durch Specs nachträglich dokumentierte Features (post-hoc)

Wurden implementiert und danach spezifiziert:

| Feature | Spec |
|---------|------|
| Vollperioden-Validierung (alle 3 Ebenen, period_available Flag) | `spec-vollperioden-validierung.md` |
| Transfer-Historisierung (Quell-Belegung schließen statt löschen) | `spec-transfer-historisierung.md` |
| Bettsuche Zeitraum-Vorbelegung aus Verlegungskontext | `spec-bettsuche-zeitraum-prefill.md` |
| Warteplatz Soft-Delete-Kollision Fix | `spec-warteplatz-soft-delete-fix.md` |

---

## Keycloak-Konfiguration (Sync-Pflicht)

Neue Rollen müssen **synchron** in drei Stellen gepflegt werden:
1. `infra/keycloak/realm-export.json` (Realm-Definition)
2. Backend: `src/adapters/keycloak/jwt.py` (Rollen-Sets `_READER_PLUS`, `_WRITER_PLUS`)
3. Frontend: Rollen-Check in Komponenten (`roles.includes('...')`)

Realm: `bordercapcontrol` · Client-ID: `bordercapcontrol-frontend` · Flow: Standard (PKCE)

---

## Audit-Log-Regeln

- `audit.events` ist **append-only** — kein UPDATE auf bestehenden Zeilen (außer DSGVO-Löschung)
- Jeder Audit-Eintrag: `actor_id` (Keycloak-Sub), `actor_role`, `location_id`, `entity_type`, `entity_id`, `event_type`, `payload` (JSONB), `created_at`
- Audit-Log ist für **alle Rollen** sichtbar (reader, writer, location-admin, system-admin)

---

## Usage Guidelines

**Für AI-Agents:**
- Diese Datei vor jeder Implementierungsaufgabe lesen
- Alle Regeln exakt einhalten — bei Unklarheit die restriktivere Option wählen
- Schichtentrennung (hexagonal) ist eine harte Regel, kein Guideline
- Neue Env-Vars im Frontend immer in `vite-env.d.ts` deklarieren

**Für Menschen (Berthold):**
- Datei aktualisieren wenn neue Patterns entstehen oder Stack sich ändert
- Bei neuen Features ohne Spec: in der Tabelle "Nicht durch Specs abgedeckt" eintragen
- Regeln entfernen sobald sie offensichtlich werden
- Quartalsweise auf Aktualität prüfen

_Zuletzt aktualisiert: 2026-06-07 — Beta v1.0.0 Tag gesetzt_
