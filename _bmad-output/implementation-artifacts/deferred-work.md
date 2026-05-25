# Deferred Work — BorderCapControl Demo Stack

Zurückgestellt aus Spec `spec-demo-infrastruktur.md` am 2026-05-23.
Diese Ziele werden nach Abschluss von Ziel 1 sequenziell angegangen.

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
