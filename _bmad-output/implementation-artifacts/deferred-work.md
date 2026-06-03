# Deferred Work — BorderCapControl Demo Stack

Zurückgestellt aus Spec `spec-demo-infrastruktur.md` am 2026-05-23.
Diese Ziele werden nach Abschluss von Ziel 1 sequenziell angegangen.

---

## Review-Findings (spec-anfragen-workflow-bett-status-fixes.md) — Zurückgestellt 2026-06-03

Gefunden beim Review. Kein Handlungsbedarf für Demo-Betrieb.

- **Wartebereich-Panel: canEdit-Guard fehlt in handleBedClick** (`Drilldown.tsx` ~1024): Das Wartebereich-Bett-Panel ruft `handleBedClick` direkt ohne `canEdit &&`-Guard auf. Der neue `pending_reservation_id`-Guard navigiert daher zu `/reservations` auch wenn `canEdit=false`. Pre-existing Architekturproblem; Navigation ist weniger schädlich als Dialog ohne Berechtigung.
- **ORDER BY created_at ohne Secondary-Sort bei Gleichwert** (`router.py` Subqueries): Wenn zwei PENDING-Anfragen exakt denselben `created_at`-Timestamp haben (z.B. Bulk-Insert in Demo-Daten), sind `pending_reservation_id` und `pending_requester_location_name` technisch non-deterministisch — bleiben aber konsistent zueinander. Fix: `ORDER BY pen_in.created_at, pen_in.id` als Tie-Breaker.
- **hasPendingRequest-Zustand bei VORGEMERKT+PENDING unsichtbar** (`Drilldown.tsx:233`): Wenn ein Bett gleichzeitig VORGEMERKT (CONFIRMED) und `suggested_bed_id` einer PENDING-Anfrage ist, wird nur der VORGEMERKT-Zustand angezeigt. `pending_requester_location_name` wird befüllt aber nie gerendert. Seltener Edge-Case im Datenmodell.
- **VORGEMERKT-Click ohne reservation_id ist silent** (`Drilldown.tsx:715`): `if (bed.reservation_id) navigate(...)` — kein else-Branch. Falls Backend je VORGEMERKT ohne reservation_id liefert, passiert beim Klick nichts. Pre-existing, API-Invariante verhindert diesen Fall aktuell.

---

---

## Ziel B — EU-Statistik-Report (zurückgestellt 2026-05-31)

Separate EU-Kontingentauslastungs-Ansicht mit Zahlenstatistik-Tabelle + Charts, PDF-Export für EU-Versand. Baut auf Ziel A (spec-ziel11-zeitreihenstatistik-intern.md) Backend-Infrastruktur auf.
- Frontend: Eigene Seite `/statistik/eu-report`
- Zahlenstatistik-Tabelle: Kontingent-Auslastung je Einrichtung + Zeitreihe
- PDF-Export via WeasyPrint (wie spec-ziel7b)
- Fokus: EU-Compliance-Nachweis, nicht Prozessoptimierung

---

## Deferred from: code review of spec-keycloak-email-onboarding.md (2026-05-31)

- **`bruteForceProtected: false` trotz E-Mail-Onboarding** — Pre-existing, außerhalb des Keycloak-Onboarding-Scopes. Für Produktion auf `true` setzen.
- **SMTP-Credentials per Plain-Env-Var** — Standard-Docker-Pattern (kein Secrets-Manager). Für Prod-Hardening: Docker Secrets oder Vault-Integration evaluieren.
- **`axllent/mailpit:latest` unpinned** — Konsistent mit Projekt-Pattern. Falls Mailpit Major-Version wechselt, API-Pfad `/api/v1/messages` prüfen.
- **smtpServer.host="mailpit" bei Prod-Import via --import-realm** — Silenter Fehler: SMTP-Verbindung schlägt fehl bis Admin manuell in KC Admin-UI überschreibt. In KONZEPT.md dokumentiert, manueller Post-Deploy-Schritt erforderlich.
- **--import-realm überspringt Re-Import auf bestehenden Volumes** — KC-Verhalten (by design). `make down` (Volume löschen) erforderlich nach realm-export.json-Änderungen. In KONZEPT.md dokumentiert.

---

## Review-Findings (Ziel 9a) — Zurückgestellt

Gefunden beim Review von `spec-ziel9a-bugfixes.md`. Nicht kritisch für Demo-Betrieb.

- **Inkonsistente HTTP-Statuscodes für fehlende Location:** `get_location_context` (genutzt von suggestions, tasks, notifications) gibt jetzt HTTP 403 zurück wenn weder Header noch JWT-Claim vorhanden ist. Die `_resolve_location`-Funktion in `reservations/router.py` gibt bei fehlendem Header HTTP 422 zurück. Beide Codes haben semantische Berechtigung (403 = Authorization, 422 = Validation), führen aber zu inkonsistenter Client-seitiger Fehlerbehandlung. Fix: `_resolve_location` auf 403 angleichen oder zentrale `_get_location_id`-Utility einführen.

---

## Review-Findings (Ziel 1) — Zurückgestellt

Gefunden beim Review von `spec-demo-infrastruktur.md`. Nicht kritisch für Demo-Betrieb.

- **Keycloak Dev-Settings:** `start-dev`, `sslRequired: none`, `bruteForceProtected: false`, `passwordPolicy: length(1)` sind bewusste Demo-Entscheidungen. Für Staging/Produktion auf `start`, `sslRequired: external`, Brute-Force-Schutz und sichere Password-Policy umstellen.
- **Klartextpasswörter in realm-export.json:** Für Dev akzeptabel. Vor Staging in gehashtes Format (Keycloak `HASHED_PASSWORD`) konvertieren.
- **Keycloak-Import bei bestehendem Volume:** Keycloak 24 importiert Realm nur einmal (beim ersten Start). Änderungen an `realm-export.json` greifen erst nach `make down` (Volume löscht Realm-Daten). Dokumentieren im README.
- **Alembic-Reihenfolge:** `make migrate` setzt voraus, dass `make dev` vorher lief (init.sql muss ausgeführt sein). Guard oder Abhängigkeitscheck im Makefile als zukünftige Verbesserung.
- **DB-Health-Unterscheidung:** `check_db_health()` unterscheidet nicht zwischen Connection-Refused und Query-Timeout. Für Monitoring-Ausbau in späteren Zielen relevant.
- **Keycloak Admin-Token Ablauf in Behave:** Token-Refresh-Mechanismus für langlaufende Test-Suiten. Aktuell kein Problem (Keycloak-Default: 60s, Tests laufen schneller).
- **Alembic downgrade:** `downgrade()` löscht Tabellen ohne Datenschutz-Check. Akzeptabel für Entwicklung, vor Produktion mit `RAISE EXCEPTION IF table NOT empty`-Guard absichern.
- **SKOS-Daten nicht volume-gemountet:** Codelisten-Änderungen erfordern Image-Rebuild. Für Phase-1-Scope akzeptabel; Hot-Reload via Volume als spätere Dev-UX-Verbesserung.

---

## Review-Findings (Ziel 2) — Zurückgestellt

Gefunden beim Review von `spec-core-crud-api.md`. Nicht kritisch für Demo-Betrieb.

- **EU-Quota Race Condition:** `check_eu_quota` liest Summe in App-Code und prüft dann. Unter concurrent requests können zwei Requests beide die Prüfung bestehen und beide committen → Überschreitung möglich. Fix: `SELECT ... FOR UPDATE` auf die Summe oder SERIALIZABLE Isolation. Demo-Scope: acceptabel.
- **Cascade Soft-Delete fehlt:** Wenn ein Raum deaktiviert wird, bleiben seine Betten aktiv (is_active=True). Wenn ein Bett deaktiviert wird, bleibt eine laufende Belegung in persons.occupants. Für Phase 1 acceptabel; für Produktion: Cascade-Deaktivierung implementieren.
- **POST /system/eu-quota ohne Untergrenze:** Quota kann unter bestehende Kontingent-Summe gesetzt werden → alle künftigen Location-Creates mit positivem Kontingent scheitern. Fix: Prüfung `new_quota >= current_sum` in set_eu_quota.
- **Default eu_gesamtquote=0 blockiert Fresh-Deploy:** Nach Migration 0002 ist eu_gesamtquote=0. Jede Location mit kontingent>0 scheitert bis ein Admin POST /api/system/eu-quota aufruft. Dokumentation oder Init-Schritt fehlt.
- **SystemSettings-Singleton-Erstellung ohne Audit-Log:** Wenn der Singleton beim ersten `get()` implizit angelegt wird (Fallback-Pfad), fehlt ein audit.events-Eintrag. Operativ irrelevant, aber Audit-Vollständigkeit unvollständig.

---

## Ziel 2: Core CRUD API (FastAPI)

FastAPI-Endpoints für die Kernobjekte: Einrichtungen (Locations), Räume (Rooms), Betten (Beds), Belegung (Occupancy).
- CRUD für alle Entitäten
- DSGVO-Minimaldatenmodell: AZR-ID + Alias-ID + Geschlecht + Von/Bis-Datum
- Zweistufiges Kapazitätsmodell (Kontingent + Notbetten)
- 12-Wochen-Timer-Logik
- EU-Gesamtquote mit Validierung
- Behave-Integrationstests für alle Endpoints
- Hexagonale Ports/Adapter-Struktur

---

## Review-Findings (Ziel 3a) — Zurückgestellt

Gefunden beim Review von `spec-jwt-auth-retrofit.md`. Nicht kritisch für Demo-Betrieb.

- **Token-Ablauf mid-Suite:** `context.auth_token` wird einmalig in `before_all` geholt. Keycloak-Default TTL ist 5 Minuten. Test-Suiten, die länger laufen, erhalten danach 401. Fix: `before_scenario`-Hook der Token-Alter prüft und bei Bedarf erneuert.
- **Stale JWKS bei Keycloak-Ausfall:** Wenn der JWKS-Cache abgelaufen ist und Keycloak nicht erreichbar ist, schlagen alle Auth-Requests mit 401 fehl statt einen gecachten JWKS zu servieren. Fix: Bei `httpx.HTTPError` in `_fetch_jwks()` den vorhandenen (veralteten) Cache zurückgeben wenn vorhanden, sonst HTTP 503.
- **`sub`-Claim leer akzeptiert:** `payload.get("sub", "")` akzeptiert leeren String als valide Sub-Claim. Ein fehlerhaftes Token ohne `sub` erzeugt `UserContext(sub="")` ohne Fehler. Fix: Prüfung `if not sub: raise HTTPException(401)` nach der Extraktion.
- **`_get_db_session`-Connection-Leak-Edge-Case:** In `get_location_context` (noch nicht in Ziel 3a erzwungen): wenn `session.begin()` wirft, wird `conn.close()` nicht garantiert aufgerufen. Fix für Ziel 3b: `finally: await session.close()` sicherstellen oder `AsyncSessionFactory` als Context-Manager nutzen.

---

## Review-Findings (Ziel 3b) — Zurückgestellt

Gefunden beim Review von `spec-reservierungsworkflow-postkorb.md`. Nicht kritisch für Demo-Betrieb.

- **actor_id fehlt im Audit-Log:** `_write_audit()` nimmt `actor_id` als Parameter, schreibt ihn aber nicht ins Payload. Audit-Einträge sind daher nicht attributierbar (wer hat die Statusänderung ausgelöst?). Fix: `UserContext.sub` aus JWT in `actor_id` übernehmen und ins Payload schreiben.
- **check_retraction_allowed vor check_state_transition (CANCELLED-Pfad):** Bei ungültigem Statusübergang (z.B. REJECTED → CANCELLED) von einer Nicht-Beteiligten-Einrichtung erhält der Caller HTTP 403 statt HTTP 409. Semantisch korrekt (Berechtigungsfehler hat Vorrang), aber inkonsistent mit confirm/reject (wo state-check zuerst kommt). Fix: Reihenfolge angleichen.
- **No-op PATCH /api/tasks/{id}:** Body `{}` oder `{priority: null, status: null}` wird akzeptiert — updated_at wird gesetzt, aber keine Felder geändert. Fix: Mindesens ein Feld muss gesetzt sein (model_validator).
- **Enum-Korruption in DB → 500:** Wenn `reservations.requests.status` oder `tasks.inbox.priority` einen ungültigen String enthält (z.B. durch direktes SQL), wirft `_to_entity()` bei der Enum-Konvertierung einen `ValueError` → unbehandelte 500-Antwort. Fix: try/except bei Enum-Konvertierung mit sprechendem Fehler.
- **SSE kein Heartbeat:** Bei langen Idle-Phasen (>60s ohne neue Tasks) trennen HTTP-Proxies/Load Balancer mit Default-Timeout die SSE-Verbindung still. Fix: Alle 30s leeren Comment-Event senden: `yield ": keepalive\n\n"`.
- **HTTPException in Repo-Schicht:** `reservation_repo.py` und `task_repo.py` werfen direkt `HTTPException` (404) statt Domain-Exceptions. Dies koppelt den Adapter an HTTP-Semantik. Fix für spätere Refactoring-Iteration: `ReservationNotFoundError(DomainError)` und `TaskNotFoundError(DomainError)` einführen.
- **Task-Body enthält keine Requester-Location-Info:** Der Task-Text „Einrichtung hat eine Reservierungsanfrage gestellt" nennt nicht die sendende Einrichtung. Die Zieleinrichtung sieht nicht, woher die Anfrage kommt, ohne die Reservierung zu öffnen. Fix: Requester-Name oder -ID in den Body aufnehmen.

---

## Ziel 3b: Reservierungsworkflow + Postkorb + SSE-Notifications

Zurückgestellt aus Ziel-3-Split (2026-05-23). Spec-Draft vorhanden: `_bmad-output/implementation-artifacts/spec-reservierungsworkflow-postkorb.md` (status: draft — enthält vollständige I/O-Matrix, Tasks und Design Notes).

Voraussetzung: Ziel 3a (JWT-Auth-Retrofit) muss abgeschlossen sein.

- Reservierungsanfragen-Flow: PENDING → CONFIRMED/REJECTED → TRANSFERRED; CANCELLED durch Requester oder Target
- DSGVO-Minimalprofil: azr_id, geschlecht, geburtsjahr, herkunftsland (ISO 3166-1 alpha-3)
- Retraktionsregel: nur Requester-Location oder Target-Location
- Postkorb (tasks.inbox pro Einrichtung): Task-Typen, Priorität LOW/MEDIUM/HIGH, Status OPEN/IN_PROGRESS/DONE/DISMISSED
- SSE-Notifications: GET /api/notifications/stream (Polling-Loop alle 5s, DB-basiert, kein Redis)
- Behave-Integrationstests für alle Workflow-Szenarien

---

## Ziel 3: Reservierungsworkflow + Postkorb

- Reservierungsanfragen-Flow: Anfragen → Bestätigung (First-come-first-served) → Transfer
- Rücknahme nur durch Ersteller oder Ziel-Einrichtungs-SB
- Postkorb (Task-Inbox) pro Einrichtung: konfigurierbare Task-Typen
- Priorisierte Task-Ansicht (nur eigene Tasks für SB)
- Session-scoped Benachrichtigung (WebSocket/Polling)
- Behave-Tests für Workflow-Szenarien

---

## Ziel 4: Frontend — Dashboard + Auth

- React + MUI (Material UI), modernes Theme
- Keycloak PKCE-Flow (Authorization Code)
- Hauptdashboard: Ampel-Overlay (Grün/Gelb/Rot) mit Kapazitätszahl
- Eigene Einrichtung immer oben
- Drilldown: Betttypen, Reservierungsanfragen, Belegungsdetails
- Task-Inbox-Ansicht (personalisiert)
- BITV 2.0 / WCAG 2.1 AA (Ampelfarben mit Icon-Redundanz)

---

## Ziel 5: Karte + SVG-Fallback

- Leaflet + lokaler Tile-Server (tileserver-gl + Deutschland-MBTiles)
- Ampel-Overlay auf Karte (Einrichtungspunkte, klickbar)
- SVG-Fallback wenn Tile-Server nicht verfügbar (Backend rendert SVG mit aktuellen Kapazitätsdaten)
- Beide Darstellungen als Adapter desselben Ports

---

## Ziel 6a: Belegungsvorschlag — Einfacher Solver ✅ (implementiert als spec-ziel6a-belegungsvorschlag-solver.md)

## Ziel 6b: Belegungsvorschlag — Familien-Constraint + Standortübergreifend ✅ (implementiert als spec-ziel6b-belegungsvorschlag-erweitert.md)

---

## Review-Findings (Ziel 6b) — Zurückgestellt

Gefunden beim Review von `spec-ziel6b-belegungsvorschlag-erweitert.md`. Nicht kritisch für Demo-Betrieb.

- **Cross-location Accept/Reject-Ownership:** Wenn `cross_location=True`, kann nur die erstellende Einrichtung den Vorschlag akzeptieren/ablehnen — die Einrichtung, deren Betten vorgeschlagen wurden, hat keinen Veto. Fix: `accept`/`reject`-Endpunkte: wenn `cross_location=True` im SUGGESTION_CREATED-Payload → Ownership-Check relaxieren oder Benachrichtigung an Ziel-Einrichtung. Voraussetzung: Einrichtungs-übergreifende Kommunikation (→ Ziel 7).
- **Alphabetische Priorisierung bei Familien-Cross-Location:** `_compute_family_variants` gibt immer den alphabetisch ersten qualifizierenden Raum zurück; keine Berücksichtigung von Nähe, Auslastung oder Präferenz. UX-Gap für Produktion.

---

## Ziel 7a: Validierungsjobs + Auto-Cleanup ✅ (implementiert als spec-ziel7a-validierungsjobs.md)

---

## Ziel 7b: EU-Compliance-Reporting (PDF) ✅ (implementiert als spec-ziel7b-eu-compliance-report.md)

---

## Ziel 8: Labels-System ✅ (implementiert 2026-05-25, spec-ziel8-labels-system.md)

Flexibles Labels-System für Räume, Betten und Belegungen (Personen-Hinweise). Unterstützt die manuelle Bett-Zuweisung durch visuelle Matching-Hints ohne algorithmischen Zwang.

**Technische Umsetzung (Demo Stack):**
- `TEXT[]`-Spalten auf `capacity.rooms.labels`, `capacity.beds.labels` und `persons.occupants.labels` (Migration 0006)
- `PATCH /api/rooms/{id}/labels` — Labels einer Einrichtungs-Raumliste setzen/ersetzen
- `PATCH /api/beds/{id}/labels` — Labels eines Bettes setzen/ersetzen
- `PATCH /api/occupants/{id}/labels` — Labels einer Belegung setzen/ersetzen
- `GET /api/labels/catalog` — Vordefinierter Katalog, gruppiert nach Entitätstyp (`room`, `bed`, `occupant`)
- Frontend: `LabelChips`-Komponente (MUI Chip) — readonly in Listenansichten, editierbar in `BelegDialog` und `BedManageDialog`

**DSGVO:** Belegungs-Labels sind operative Hinweise ohne AZR-Bezug; werden mit der Belegung gelöscht. Keine Freitexteingabe — nur vordefinierter Katalog erlaubt.

---

## Review-Findings (Ziel 5) — Zurückgestellt

Gefunden beim Review von `spec-ziel5-karte-svg-fallback.md`. Nicht kritisch für Demo-Betrieb.

- **FALLBACK_COORDS-Überlappung:** Mehrere Einrichtungen mit unbekanntem Namen landen alle bei [51.1, 10.4] (Deutschland-Mittelpunkt) und überlagern sich ohne visuelle Unterscheidung. Fix: Marker für unbekannte Locations überspringen oder Warning loggen. Kein Problem solange die 4 bekannten Demo-Orte (Frankfurt, München, Passau, Hamburg) verwendet werden.
- **Health-Check prüft nicht Content-Type:** `fetch('/tiles/health')` akzeptiert jede 2xx-Antwort — eine HTML-Fehlerseite mit HTTP 200 würde Leaflet-Modus aktivieren, obwohl keine Tiles verfügbar sind. Fix: Content-Type-Prüfung oder bekannten Sentinel-Body validieren.
- **Leaflet Chunk-Größe:** Leaflet + react-leaflet erhöhen Bundle auf ~653 kB (200 kB gzipped). Bei Bedarf mit dynamischem `import()` (`React.lazy`) in ein separates Chunk auslagern.

---

## Review-Findings (Ziel 4b) — Zurückgestellt

Gefunden beim Review von `spec-ziel4b-frontend-reservierungsworkflow-postkorb.md`. Nicht kritisch für Demo-Betrieb.

- **`post<T>()` und `patch<T>()` schlagen auf 204-Antworten fehl:** Beide Methoden rufen immer `response.json()` auf. Wenn das Backend 204 No Content zurückgibt (z.B. bei confirm/reject), wirft `response.json()` einen SyntaxError, obwohl die Aktion erfolgreich war. Fix: Prüfung `if (response.status !== 204) return response.json()` vor dem JSON-Parse.
- **SSE reconnect setzt kein frisches Token im Header:** Nach Token-Refresh via `updateToken(60)` in `onerror` verbindet `fetchEventSource` automatisch neu — nutzt aber noch den alten Token-Wert aus dem Closure. Das neue Token ist erst nach dem nächsten `useEffect`-Trigger (wenn `keycloak.token` sich ändert) aktiv. Fix: `getToken`-Callback-Pattern statt statischem Header-Wert.
- **Kein Error-Boundary in Reservations.tsx / TaskInbox.tsx:** Unerwartete Render-Fehler (z.B. malformed API response) bringen die gesamte Route zum Absturz ohne Recovery-UI. Fix: React ErrorBoundary um Seitenkomponenten wrappen.

---

## Review-Findings (Ziel 4a) — Zurückgestellt

Gefunden beim Review von `spec-ziel4a-frontend-setup-dashboard-drilldown.md`. Nicht kritisch für Demo-Betrieb.

- **DATE vs TIMESTAMPTZ in belegungsgrad-SQL:** `belegung_ende` ist `DATE`; `NOW()` gibt `TIMESTAMPTZ` zurück. PostgreSQL castet implizit auf Mitternacht UTC → Betten die heute auslaufen werden ab Mitternacht als frei gezählt, auch wenn physischer Checkout tagsüber erfolgt. Fix für Produktion: explizites `CURRENT_DATE` statt `NOW()` verwenden, oder `belegung_ende` auf `TIMESTAMPTZ` ändern.
- **Interval-Refresh + Per-Request-Refresh (concurrent updateToken):** `KeycloakProvider.tsx` ruft `updateToken(60)` alle 30s auf; `client.ts` ruft ihn vor jedem API-Call auf. Falls beide gleichzeitig feuern, kann keycloak-js 24 interne Deduplizierung leisten, garantiert aber keine thread-safe Ausführung. Für Produktion: Interval entfernen; per-Request-`updateToken(60)` in `client.ts` ist ausreichend.
- **Kein persistenter Fehlerzustand in Drilldown:** Bei API-Fehler verschwindet der Ladeindikator; die Seite bleibt leer nach Snackbar-Ablauf ohne Retry-Button. Demo-Scope akzeptabel.
- **Kein Location-Name im Drilldown-Breadcrumb:** Zweite Breadcrumb-Ebene zeigt statisch "Einrichtung" statt dem tatsächlichen Namen der Einrichtung. Fix: `GET /api/locations/{id}` aufrufen und Name in Header anzeigen.
- **Hardcodierte DB-Credentials in demo_data.py:** Fallback-URL enthält Klartext-Credentials. Für Staging/Produktion: Pflicht-Env-Var ohne Fallback oder `.env`-File-Ansatz.

---

## Review-Findings (Prod-Deployment-Compose) — Zurückgestellt (2026-06-01)

Gefunden beim Review von `spec-prod-deployment-compose.md`. Kein Handlungsbedarf für Story selbst.

- **Kein CPU/Memory-Limit:** Kein `deploy.resources.limits` in `docker-compose.prod.yml`. Runaway-Container kann Host-Ressourcen erschöpfen. Fix in separatem Hardening-Sprint: pro-Service-Limits basierend auf Last-Tests.
- **`.gitignore` Wildcard-Varianten fehlen:** Nur `.env.prod` ignoriert, nicht `.env.prod.local` o.ä. Falls Operator Variante anlegt, landet sie ggf. in Git. Fix: `.env.prod*` als Glob-Pattern (prüfen ob `.env.prod.example` dann ausgenommen werden muss).
- **KC_PROXY=edge ohne Proxy-Header-Validierung:** Keycloak vertraut `X-Forwarded-Proto` bedingungslos. Hardening: `KC_PROXY_HEADERS=xforwarded` und `KC_HOSTNAME_STRICT=true` in Keycloak 24+ dokumentieren. Liegt in Verantwortung des Reverse-Proxy-Betreibers.
- **KC_HOSTNAME_ADMIN_URL = öffentliche URL:** Keycloak Admin-Console über selbe öffentliche URL erreichbar wie die App. Für stärkere Isolation: Admin-URL auf interne Adresse zeigen lassen; erfordert aber separaten Ingress-Eintrag.
- **Alembic-Migration vor uvicorn fehlt:** Backend startet ohne `alembic upgrade head`. Für vollständiges Prod-Readiness: Init-Container oder Entrypoint-Skript ergänzen. In `docker-compose.prod.yml` Design Notes als "Deferred (nächste Story)" dokumentiert.

---

## Review-Findings (spec-belegung-vormerken-suche-fix.md) — Zurückgestellt 2026-06-01

Gefunden beim Review von Story 9-1. Kein Handlungsbedarf für diese Story.

- **`?? res[0]` in `handleOpenConfirm` (hasPerson-Pfad)**: `handleOpenConfirm` für Einzelperson (Zeile ~283) und Gruppen (Zeile ~274) nutzt weiterhin `res.find(...) ?? res[0]` beim Laden der Person-Labels für den Bestätigungs-Dialog. Kann falsche Labels für eine falsch gematchte Person anzeigen. Pre-existing; hasPerson-Pfad war in dieser Story out-of-scope. Fix in separatem Ticket.
- **Race condition bei schnellen aufeinanderfolgenden Suchen**: Zwei in-flight Requests für denselben `idx` — der später antwortende überschreibt das Ergebnis des neueren. Pre-existing Architekturmuster. Fix: AbortController oder monotoner Sequenzzähler in `searchPersonForBed`.
- **Stale Callback nach Dialog-Close**: Wenn Dialog geschlossen wird während `searchPersonForBed` noch läuft, kann der Callback nach erneutem Dialog-Öffnen den frisch initialisierten `bedAssignments`-State korrumpieren. Pre-existing.
- **Keyboard-Accessibility für Trefferliste**: Clickable `<Box>`-Elemente ohne `role="button"`, `tabIndex` oder `onKeyDown`. Keyboard- und Screen-Reader-Nutzer können nicht selektieren. Separates Accessibility-Ticket.
- **Duplicate Keys bei doppelten Label-Strings**: `<Chip key={lbl}>` — wenn `occ_labels` identische Strings enthält, React-Warning und stilles Auslassen. Pre-existing Muster überall in der Komponente.

---

## Deferred: Belegung-vormerken — Ziel B (zurückgestellt 2026-06-01)

Folgestory zu `spec-belegung-vormerken-suche-fix.md`. Setzt Ziel A (Bug-Fix + Trefferliste) voraus.

- **Neue Person direkt anlegen wenn AZR nicht gefunden**: „Person nicht gefunden"-Zustand im Dialog um Formular erweitern (Geschlecht, Geburtsjahr, Herkunftsland) → POST `/api/beds/{bed_id}/occupancy` mit neuen Personendaten direkt auf lokalem Bett; kein Verlegungsworkflow nötig.
- **Automatischer Warteplatz bei Verlegungsanfrage**: Wenn Person noch kein aktives Bett hat und lokale Kapazität vorhanden ist → vor dem POST `/api/reservations` automatisch ein lokales Bett als Warteplatz anlegen. Verhindert das „Verschwinden" der Person bei Ablehnung durch Zieleinrichtung. Erfordert: neuen Backend-Endpunkt oder atomare Frontend-Sequenz (Bett anlegen → Anfrage stellen).

---

## Review-Findings (spec-belegung-vormerken-suche-fix.md) — Zurückgestellt 2026-06-02

Gefunden beim Review von Story 9-1. Nicht kritisch für Demo-Betrieb.

- **`geschlecht: ""` leerer String nicht durch `??` gefangen**: In `searchPersonForBed` (Z.301) und im Trefferliste-Click-Handler (Z.1124) wird `person.geschlecht ?? a.geschlecht` verwendet. Der Nullish-Coalescing-Operator fängt nur `null`/`undefined`, nicht leere Strings. Fix: `person.geschlecht || a.geschlecht`.
- **`belegung_ende` ohne Datumsformatierung**: `foundEnde` wird als roher API-String (z.B. `"2025-12-31"`) angezeigt. Für DE-Locale: `new Date(val).toLocaleDateString("de-DE")`. Pre-existing Pattern in allen Pfaden die `foundEnde` befüllen.

---

## Deferred: Einrichtungsfilter in Bettensuche (zurückgestellt 2026-06-03)

Zurückgestellt aus Session "Anfragen-Workflow-Fixes" — Ziel A des Split.

In der Box "Standortübergreifend suchen" (Bettensuche ohne vorherige Personenauswahl) soll eine Multi-Select-Auswahl der aktuell angelegten Einrichtungen möglich sein. Design: ähnlich Raumfilter-Chips (MUI Chip / Toggle-Chip). Einrichtungsnamen exakt wie in der Administration hinterlegt anzeigen. API: `GET /api/locations` liefert die Daten.

---

## Review-Findings (spec-bettsuche-hasperson-exactmatch.md) — Zurückgestellt 2026-06-02

Gefunden beim Review von Story 10-1 (Edge Case Hunter). Kein Handlungsbedarf für Demo-Betrieb.

- **Trefferliste: visuell identische Zeilen bei mehrfach-aktiven Belegungen**: Wenn dieselbe Person zwei gleichzeitige Belegungen hat, erscheint sie zweimal in `searchResults` mit identischen Darstellungen (nur `azr_id` + `location_name`). Der neue Composite-Key `${person.azr_id}-${pi}` behebt den React-Warning, aber der User kann nicht unterscheiden, welche Belegung er auswählt. Fix: Bett-Nummer oder Raum-Name in der Trefferliste ergänzen (`frontend/src/pages/SuggestionWizard.tsx` Z. ~1137–1141).
