---
title: 'Ziel 4a — Frontend Setup + Auth + Dashboard + Drilldown'
type: 'feature'
created: '2026-05-23'
status: 'done'
baseline_commit: 'NO_VCS'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Kein Frontend vorhanden — Sachbearbeiter sehen keine Kapazitätsübersicht und können keine Standortdetails abrufen.

**Approach:** Vite+npm React 18+MUI v5 App mit Keycloak PKCE-Flow; neuer Backend-Endpoint `GET /api/locations/summary` liefert Belegungsgrad je Einrichtung; Dashboard zeigt Ampel-Karten (< 70 % grün, 70–90 % gelb, ≥ 90 % rot); Drilldown-Seite zeigt Räume und Betten. Eigene Einrichtung wird aus JWT-Claim `location_id` gelesen und oben gepinnt. Demo-Seed-Skript erzeugt 4 Einrichtungen mit festen UUIDs, die mit dem Keycloak-Realm synchronisiert sind.

## Boundaries & Constraints

**Always:**
- BITV 2.0 / WCAG 2.1 AA — Ampelfarben immer mit Icon-Redundanz (nie Farbe allein): Grün = `CheckCircleIcon`, Gelb = `WarningIcon`, Rot = `ErrorIcon`; aria-label trägt Klartext-Auslastung
- JWT-Claim `location_id` aus `tokenParsed.location_id` → stets als `X-Location-Id`-Header bei jedem API-Call
- Bearer-Token in `Authorization`-Header auf jedem Request
- Kein Personenname und kein Klarname (nur Alias-ID, AZR-ID) in der UI
- Demo-Seed idempotent (INSERT … ON CONFLICT DO NOTHING); Keycloak-User-UUIDs synchron mit Seed-Location-UUIDs

**Ask First:**
- Wenn Keycloak PKCE-Redirect-Loop auftritt (z. B. falsche redirectUri)
- Wenn `location_id` im JWT fehlt — Toast statt Crash; HALT und frage ob Fallback-Auswahl-Dialog nötig

**Never:**
- Kein Redux / Zustand / anderer globaler State-Manager — React Context + useState reicht für Demo
- Kein Next.js / SSR
- Keine anderen Auth-Bibliotheken außer `keycloak-js`
- Kein Produktions-Build-Deployment in diesem Ziel — nur `npm run dev`

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Unangemeldeter Aufruf | GET / ohne Token | Keycloak-Login-Seite (PKCE-Redirect) | — |
| Token-Ablauf | Token < 60 s Restlaufzeit beim nächsten API-Call | `updateToken(60)` erneuert still | Falls Refresh fehlschlägt → `keycloak.logout()` |
| Dashboard-Load | GET /api/locations/summary 200 | MUI-Grid mit Ampel-Karten; eigene Einrichtung erste Karte | Snackbar "Daten konnten nicht geladen werden" |
| Ampel GRÜN | belegungsgrad_pct < 70 | Grüne Card-Header + CheckCircleIcon | — |
| Ampel GELB | 70 ≤ belegungsgrad_pct < 90 | Gelbe Card-Header + WarningIcon | — |
| Ampel ROT | belegungsgrad_pct ≥ 90 | Rote Card-Header + ErrorIcon | — |
| kontingent = 0 | Location ohne Quota | belegungsgrad_pct = 0 → GRÜN | — |
| Fehlender location_id-Claim | tokenParsed.location_id undefined | Snackbar "Standort-Zuordnung fehlt im Token"; kein Absturz; alle Karten sichtbar, keine Pinning | — |
| Drilldown-Navigation | Klick auf Location-Karte | Route /locations/:id; GET /api/locations/:id/rooms | Snackbar "Räume konnten nicht geladen werden" |
| Raum-Expand | Klick auf Raum-Accordion | GET /api/rooms/:id/beds | Snackbar "Betten konnten nicht geladen werden" |

</frozen-after-approval>

## Code Map

- `infra/keycloak/realm-export.json` — Keycloak-Realm; User-Attribute + protocolMapper fehlen noch
- `backend/seeds/demo_data.py` — Neu: idempotenter Seed mit 4 Locations + je 2 Räumen + je 4 Betten
- `Makefile` — Targets `seed`, `frontend-install`, `frontend-dev` ergänzen
- `backend/src/api/capacity/schemas.py` — `LocationSummaryResponse` neu
- `backend/src/api/capacity/router.py` — `GET /api/locations/summary` neu (raw SQL via `text()`, kein X-Location-Id dep)
- `frontend/` — Vite project root (noch nicht vorhanden)
- `frontend/vite.config.ts` — Proxy `/api` → `http://localhost:8000`, `/realms` → `http://localhost:8080`
- `frontend/src/auth/KeycloakProvider.tsx` — PKCE-Init, Token-Refresh, `useKeycloak`-Hook
- `frontend/src/api/client.ts` — Fetch-Wrapper (Bearer + X-Location-Id)
- `frontend/src/pages/Dashboard.tsx` — Ampel-Karten, Pinning, Navigation zum Drilldown
- `frontend/src/pages/Drilldown.tsx` — Accordion-Raum-Liste + Betten-Tabelle
- `frontend/src/App.tsx` — BrowserRouter, Protected-Route-Wrapper

## Tasks & Acceptance

**Execution:**

- [x] `infra/keycloak/realm-export.json` — Ergänzen: (1) `attributes: {"location_id": ["a1b2c3d4-0001-0001-0001-000000000001"]}` auf `writer_user`; `attributes: {"location_id": ["a1b2c3d4-0003-0003-0003-000000000003"]}` auf `reader_user`; `attributes: {"location_id": ["a1b2c3d4-0001-0001-0001-000000000001"]}` auf `admin_user`; (2) In `bordercapcontrol-frontend.protocolMappers` neuen Eintrag: `name: "location_id"`, `protocolMapper: "oidc-usermodel-attribute-mapper"`, config: `user.attribute=location_id`, `claim.name=location_id`, `id.token.claim=true`, `access.token.claim=true`, `jsonType.label=String`

- [x] `backend/seeds/demo_data.py` — Neu anlegen. Psycopg2-Skript (sync). Fügt ein (ON CONFLICT DO NOTHING auf PK): 4 Locations (feste UUIDs: `a1b2c3d4-0001…`, `…0002…`, `…0003…`, `…0004…`), Namen: "Flughafen Frankfurt", "Flughafen München", "Grenzübergang Passau", "Flughafen Hamburg", kontingent 200/150/80/100, notbett_kapazitaet 20/15/10/10. Je 2 Räume pro Location (schema `capacity.rooms`), je 4 Betten pro Raum (schema `capacity.beds`). DB-URL aus `DATABASE_URL` env-Variable oder Default `postgresql://bordercap_app:bordercap_pass@localhost:5432/bordercap`.

- [x] `Makefile` — Drei Targets ergänzen (nach bestehendem `migrate`-Target): `seed: ## Seed Demo-Daten` → `python3 backend/seeds/demo_data.py`; `frontend-install: ## npm install im frontend/` → `cd frontend && npm install`; `frontend-dev: ## Vite Dev-Server starten` → `cd frontend && npm run dev`

- [x] `backend/src/api/capacity/schemas.py` — `LocationSummaryResponse` ergänzen: Felder `id: UUID`, `name: str`, `kontingent: int`, `belegungsgrad_pct: float`, `is_active: bool`; `model_config = ConfigDict(from_attributes=True)`

- [x] `backend/src/api/capacity/router.py` — Neuer Endpoint `GET /api/locations/summary` (keine `get_location_context`-Dependency, nur `get_current_user` via Router-Default). Raw SQL mit `text()`: JOINs auf `capacity.rooms`, `capacity.beds`, `persons.occupants` (COUNT WHERE `belegung_ende IS NULL OR belegung_ende > NOW()`); `belegungsgrad_pct = CASE WHEN kontingent > 0 THEN occupied * 100.0 / kontingent ELSE 0.0 END`; nur `is_active=True` Locations; gibt `List[LocationSummaryResponse]` zurück.

- [x] `frontend/` — Scaffold ausführen: `npm create vite@latest frontend -- --template react-ts` dann `cd frontend && npm install @mui/material @emotion/react @emotion/styled @mui/icons-material keycloak-js react-router-dom axios`. `.gitignore` für `node_modules/` prüfen.

- [x] `frontend/vite.config.ts` — `server.proxy`: `/api` → `{ target: "http://localhost:8000", changeOrigin: true }`; `/realms` → `{ target: "http://localhost:8080", changeOrigin: true }`.

- [x] `frontend/src/auth/KeycloakProvider.tsx` — `new Keycloak({ url: "/realms", realm: "bordercapcontrol", clientId: "bordercapcontrol-frontend" })`; `keycloak.init({ onLoad: "login-required", pkceMethod: "S256" })`; Context exportiert `{ keycloak, initialized, locationId: keycloak.tokenParsed?.location_id ?? null }`; `useInterval`-ähnlicher Effekt ruft `keycloak.updateToken(60)` jede 30 s auf.

- [x] `frontend/src/api/client.ts` — Thin Wrapper um `axios.create`; Axios Interceptor injiziert `Authorization: Bearer {keycloak.token}` + `X-Location-Id: {locationId}` (falls vorhanden). Exportiert `apiClient` als Default.

- [x] `frontend/src/pages/Dashboard.tsx` — `useEffect` → `apiClient.get("/api/locations/summary")`; sortiert Ergebnis: eigene Einrichtung (id === locationId) zuerst; rendert MUI `Grid` mit `Card`-Komponenten; Card-Header-Hintergrund nach Ampel-Farbe; Icon in Card-Avatar-Slot mit `aria-label="Auslastung: Grün/Gelb/Rot"`; Klick auf Card → `navigate("/locations/:id")`. Snackbar bei Fehler.

- [x] `frontend/src/pages/Drilldown.tsx` — Route-Param `:id` → `apiClient.get("/api/locations/:id/rooms")`; MUI `Accordion` pro Raum (Name + Geschlechts-Designation als Summary); bei Expand → `apiClient.get("/api/rooms/:roomId/beds")`; Betten in MUI `Table` (bett_nummer, bett_typ, is_active-Chip). Snackbar bei Fehler.

- [x] `frontend/src/App.tsx` — `<BrowserRouter>`: Route `/` → `<Dashboard />`, Route `/locations/:id` → `<Drilldown />`; Wrapped in `<KeycloakProvider>`; Render nur wenn `initialized === true` (Loading-Spinner sonst). MUI `ThemeProvider` mit Gov-geeignetem Theme (primärblau #003366, neutral-grau, kein Neon).

**Acceptance Criteria:**
- Given unangemeldeter Nutzer, when er `/` aufruft, then erscheint die Keycloak-Login-Seite (kein App-Content sichtbar)
- Given `writer_user` eingeloggt (location_id im JWT = Flughafen Frankfurt UUID), when Dashboard geladen, then ist "Flughafen Frankfurt"-Karte die erste Karte
- Given Einrichtung mit `belegungsgrad_pct = 85`, when Dashboard angezeigt, then ist die Karte gelb und trägt ein WarningIcon mit `aria-label` das "Gelb" oder "Warnung" enthält
- Given `location_id` fehlt im JWT (`tokenParsed.location_id` undefined), when Dashboard lädt, then erscheint Snackbar "Standort-Zuordnung fehlt im Token" und die App stürzt nicht ab
- Given Drilldown-Seite für eine Einrichtung mit geseedeten Räumen, when Raum-Accordion aufgeklappt, then werden Betten in einer Tabelle angezeigt
- Given abgelaufener Token, when nächster API-Call ausgelöst, then erneuert `updateToken(60)` still und der Call läuft durch (kein 401 für Nutzer sichtbar)

## Spec Change Log

### Iteration 1 (2026-05-24)
- **Triggering finding:** Keycloak `url: "/realms"` führt zu doppeltem Pfad `/realms/realms/bordercapcontrol/...` — keycloak-js hängt intern `/realms/{realm}` an den `url`-Wert an. Auth schlägt permanent fehl (404 auf Discovery-Endpoint).
- **Amended:** Design Notes Keycloak URL-Proxy: `url: "/realms"` → `url: "/"`.
- **Known-bad state avoided:** PKCE-Init schlägt immer fehl; App rendert ohne Token; alle API-Calls 401.
- **KEEP:** PKCE S256, `didInit.current`-Guard, `location_id` aus `tokenParsed`, Modul-Level-Singleton, Interval-Cleanup.

## Design Notes

**Keycloak URL-Proxy:** keycloak-js konstruiert intern `{url}/realms/{realm}/...`. Der Vite-Proxy leitet `/realms` → `http://localhost:8080` weiter. Deshalb muss `url: "/"` verwendet werden — daraus entsteht `/realms/bordercapcontrol/...`, das der Proxy korrekt auf `http://localhost:8080/realms/bordercapcontrol/...` abbildet. `url: "/realms"` würde `/realms/realms/...` erzeugen (doppelt) und Auth permanent brechen.

**Demo-Seed UUID-Schema:** Feste UUIDs `a1b2c3d4-00XX-00XX-00XX-0000000000XX` (XX = 01–04) sind absichtlich mnemotechnisch, nicht RFC-4122-zufällig — ausreichend für Demo-Scope, nicht für Produktion.

**Ampel-Farben MUI:** `success.main` (#2e7d32), `warning.main` (#ed6c02), `error.main` (#d32f2f) — MUI-Defaults sind WCAG-AA-konform bei weißem Hintergrundtext wenn `contrastText` genutzt wird. Icon-Redundanz sichert WCAG 1.4.1 (Use of Color).

**GET /api/locations/summary ohne X-Location-Id:** Absicht — der Endpoint liefert eine globale Übersicht (kein Location-Filter). Alle authentifizierten Reader+-Nutzer dürfen alle aktiven Einrichtungen sehen.

## Verification

**Commands:**
- `cd frontend && npm run build` -- erwartet: kein TypeScript-Fehler, kein Vite-Build-Fehler
- `python3 backend/seeds/demo_data.py` -- erwartet: "4 Locations eingefügt (oder bereits vorhanden)" ohne Exception
- `curl -s http://localhost:8000/api/locations/summary -H "Authorization: Bearer {token}"` -- erwartet: JSON-Array mit 4 Einrichtungen und `belegungsgrad_pct`-Feld

**Manual checks:**
- Nach `make down && make dev && make seed`: Dashboard im Browser (http://localhost:3000) zeigt 4 Ampel-Karten; writer_user sieht "Flughafen Frankfurt" an erster Stelle
- Drilldown: Klick auf eine Karte → Räume erscheinen als Accordion; Expand → Betten-Tabelle sichtbar
- Screenreader-Check (VoiceOver / NVDA): Ampel-Icons sprechen `aria-label` aus

## Suggested Review Order

**Auth & Token-Flow**

- Keycloak PKCE-Singleton-Init; url `"/"` damit Proxy korrekt auf `/realms/{realm}/...` mappt
  [`KeycloakProvider.tsx:20`](../../frontend/src/auth/KeycloakProvider.tsx#L20)

- `initialized`-Guard verhindert false-positive Snackbar; locationId aus `tokenParsed`
  [`KeycloakProvider.tsx:36`](../../frontend/src/auth/KeycloakProvider.tsx#L36)

- Fetch-Wrapper mit Bearer + X-Location-Id; `updateToken`-Rejection wirft, stoppt den Fetch
  [`client.ts:16`](../../frontend/src/api/client.ts#L16)

**Backend Summary Endpoint**

- `GET /api/locations/summary` vor `/locations/{id}` registriert; kein doppeltes `get_current_user`
  [`router.py:164`](../../backend/src/api/capacity/router.py#L164)

- LEAST-Cap bei 100.0 verhindert belegungsgrad > 100%; LEFT JOINs wegen Locations ohne Betten
  [`router.py:180`](../../backend/src/api/capacity/router.py#L180)

- `LocationSummaryResponse` mit `belegungsgrad_pct: float`
  [`schemas.py:126`](../../backend/src/api/capacity/schemas.py#L126)

**Dashboard — Ampel & Pinning**

- `getAmpel`-Schwellen; AMPEL_CONFIG mit SvgIconComponent-Typ; `initialized`-Guard im Warn-Effect
  [`Dashboard.tsx:30`](../../frontend/src/pages/Dashboard.tsx#L30)

- Sortierung: eigene Einrichtung zuerst; `initialized`-Guard vor Snackbar
  [`Dashboard.tsx:55`](../../frontend/src/pages/Dashboard.tsx#L55)

- `CardActionArea` aria-label mit Name + Ampel-Label + Prozentzahl; Icon aria-hidden
  [`Dashboard.tsx:96`](../../frontend/src/pages/Dashboard.tsx#L96)

**Drilldown — Lazy Loading**

- `handleExpand` lazy-fetched Betten; `bett_nummer: string` (VARCHAR im DB)
  [`Drilldown.tsx:38`](../../frontend/src/pages/Drilldown.tsx#L38)

**Demo Seed**

- Deterministische uuid5 für Räume/Betten — Idempotenz über mehrere Runs
  [`demo_data.py:58`](../../backend/seeds/demo_data.py#L58)

- `bett_typ='KONTINGENT'`, `geschlechts_designation='M'/'W'` — konform mit DB-CHECK + Pydantic-Enum
  [`demo_data.py:99`](../../backend/seeds/demo_data.py#L99)

**Config & Peripherals**

- Vite-Proxy: `/realms` → :8080, `/api` → :8000; Port 3000
  [`vite.config.ts:1`](../../frontend/vite.config.ts#L1)

- App-Shell: KP-Provider wraps AppRoutes; `initialized`-Spinner; MUI-Theme gov-blau #003366
  [`App.tsx:19`](../../frontend/src/App.tsx#L19)

- `location_id` User-Attribute + protocolMapper auf `bordercapcontrol-frontend`-Client
  [`realm-export.json:63`](../../infra/keycloak/realm-export.json#L63)

- `make seed / frontend-install / frontend-dev` Targets
  [`Makefile:92`](../../Makefile#L92)
