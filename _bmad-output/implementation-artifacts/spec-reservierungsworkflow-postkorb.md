---
title: 'BorderCapControl — Reservierungsworkflow + Postkorb (Ziel 3/7)'
type: 'feature'
created: '2026-05-23'
status: 'done'
baseline_commit: 'NO_VCS'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** SBs können Betten verwalten (Ziel 2), aber es gibt keinen Workflow um Plätze zwischen Einrichtungen anzufragen und zu übertragen — Koordination erfolgt manuell außerhalb des Systems.

**Approach:** Reservierungsanfragen-Flow (PENDING → CONFIRMED/REJECTED → TRANSFERRED; CANCELLED durch Requester oder Target) mit DSGVO-Minimalprofil, Postkorb pro Einrichtung (Task-Inbox, Priorität LOW/MEDIUM/HIGH), SSE-Echtzeit-Benachrichtigung und Keycloak-JWT-Auth auf allen API-Endpoints. TDD via Behave.

## Boundaries & Constraints

**Always:**
- JWT-Auth: alle `/api/`-Endpoints erfordern Keycloak Bearer-Token (Rolle `writer` oder höher). `/health` bleibt offen. Dependency `get_current_user` global per `app.include_router(..., dependencies=[Depends(get_current_user)])`.
- SB-Einrichtung: `X-Location-Id`-Header (UUID) wird bei jedem mutierenden Request validiert — Einrichtung muss `is_active=True` sein.
- DSGVO-Minimalprofil im Reservierungsantrag: nur `azr_id`, `geschlecht`, `geburtsjahr` (4-stelliges Jahr), `herkunftsland` (ISO 3166-1 alpha-3) — kein Name, kein Foto.
- Retraktionsregel: DELETE /api/reservations/{id} (Abbrechen) nur wenn `X-Location-Id` == `requester_location_id` oder `target_location_id`. Sonst HTTP 403.
- Statusübergang: ungültige Transition (z.B. REJECTED → CONFIRMED) → HTTP 409.
- Jede Zustandsänderung an einer Reservation erzeugt: Audit-Eintrag in `audit.events` + Task in `tasks.inbox` für die betroffene(n) Einrichtung(en).
- First-come-first-served: `GET /api/reservations?target=mine` gibt PENDING-Anfragen sortiert nach `created_at` aufsteigend zurück.
- Hexagonale Architektur: Domain-Regeln nur in `domain/reservations/rules.py`, kein FastAPI-Import in domain/.
- Bestehende Behave-Scenarios (Ziel 1+2) bekommen Auth-Token über gemeinsame `before_all()`-Fixture in `environment.py`.
- TDD-First: `reservation_workflow.feature` wird vor Implementierungscode geschrieben.

**Ask First:** — (alle Fragen beantwortet)

**Resolved — Concurrent Confirmation:** `SELECT ... FOR UPDATE` auf die Reservation-Zeile beim confirm/reject/cancel. Zweiter concurrent Request wartet, sieht dann status ≠ PENDING → HTTP 409. Kein NOWAIT, kein Retry.

**Never:**
- Keine automatische Occupancy-Erstellung nach Transfer — SB legt Belegung manuell in Ziel 2 an.
- Kein Frontend (Ziel 4), kein automatisches Matching.
- Keine biometrischen Daten, kein Name in Reservierungsdaten.
- Kein Reservierungs-DELETE von außerhalb der beteiligten Einrichtungen.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output | Error Handling |
|----------|--------------|-----------------|----------------|
| Reservierung erstellen | POST /api/reservations, JWT + X-Location-Id=A, target=B | 201 + Reservation (PENDING) + Task für B | 422 wenn target == requester |
| Bestätigung | POST /api/reservations/{id}/confirm, X-Location-Id=B | 200 + Reservation (CONFIRMED) + Task für A | 403 wenn X-Location-Id ≠ B; 409 wenn nicht PENDING |
| Ablehnung | POST /api/reservations/{id}/reject, X-Location-Id=B | 200 + Reservation (REJECTED) + Task für A | 403, 409 analog |
| Rücknahme durch Requester | DELETE /api/reservations/{id}, X-Location-Id=A, status=PENDING | 200 + Reservation (CANCELLED) | 403 wenn nicht A oder B; 409 wenn TRANSFERRED |
| Unauth Zugriff | Request ohne JWT | 401 | — |
| SSE-Notification | GET /api/notifications/stream, neuer Task für eigene Location | data-Event innerhalb 10s | 401 ohne Token |
| Postkorb filtern | GET /api/tasks?priority=HIGH | 200 + Tasks für X-Location-Id, priority DESC, created_at ASC | — |

</frozen-after-approval>

## Code Map

Baseline (fertig in Ziel 3a — nicht ändern):
- `backend/src/adapters/keycloak/jwt.py` — JWKS-Cache, JWT-Decode, UserContext, `get_current_user` (mit Reader/Writer-Rollenprüfung), `get_location_context` (bereitgestellt, noch nicht erzwungen)
- `backend/src/main.py` — capacity_router mit `dependencies=[Depends(get_current_user)]`; /health offen
- `tests/environment.py` — `before_all()` holt Keycloak-Token (fail-fast); `after_scenario()` DB-Teardown
- `tests/steps/capacity_steps.py` — `_post/_get/_delete` übergeben Auth-Header aus context

Bestehend (relevant, unverändert):
- `backend/src/adapters/db/engine.py` — AsyncSessionFactory
- `backend/src/adapters/db/models.py` — Base, LocationModel (für FK); wird ergänzt
- `backend/src/adapters/db/capacity_repo.py` — Repo-Pattern für neue Repos
- `backend/src/domain/capacity/rules.py` — DomainError(Exception) Basisklasse

Neu in Ziel 3b:
- `backend/alembic/versions/0003_reservation_tasks.py` — CREATE reservations.requests + tasks.inbox, Indexes, Grants
- `backend/src/adapters/db/models.py` ergänzen — ReservationRequestModel, TaskModel
- `backend/src/domain/reservations/entities.py` — ReservationRequest Dataclass, ReservationStatus Enum
- `backend/src/domain/reservations/rules.py` — RetractionForbiddenError, InvalidStateTransitionError, check_retraction_allowed(), check_state_transition()
- `backend/src/domain/tasks/entities.py` — Task Dataclass, TaskType/TaskPriority/TaskStatus Enums
- `backend/src/ports/reservations/repository.py` — AbstractReservationRepo
- `backend/src/ports/tasks/repository.py` — AbstractTaskRepo
- `backend/src/adapters/db/reservation_repo.py` — SqlReservationRepo; SELECT FOR UPDATE bei Statusübergängen; `_create_task_and_audit()` bei jeder Statusänderung; FCFS in `list_pending_for_target()`
- `backend/src/adapters/db/task_repo.py` — SqlTaskRepo; `list_for_location()`, `list_new_since()`
- `backend/src/api/reservations/schemas.py` — ReservationCreate (DSGVO), ReservationResponse
- `backend/src/api/reservations/router.py` — POST/GET/DELETE + /confirm, /reject; RetractionForbiddenError → 403; InvalidStateTransitionError → 409; `get_location_context` Dependency erzwungen
- `backend/src/api/tasks/schemas.py` — TaskResponse, TaskPriorityUpdate
- `backend/src/api/tasks/router.py` — GET /api/tasks (filter by X-Location-Id + priority), PATCH /api/tasks/{id}
- `backend/src/api/notifications/router.py` — GET /api/notifications/stream; SSE StreamingResponse; Polling-Loop alle 5s via `list_new_since()`
- `backend/src/main.py` ergänzen — reservation/task/notification Router mit `dependencies=[Depends(get_current_user)]` einbinden
- `tests/features/reservation_workflow.feature`
- `tests/steps/reservation_steps.py`

## Tasks & Acceptance

**Execution:**
- [x] `tests/features/reservation_workflow.feature` — TDD-First Gherkin: alle I/O-Matrix-Fälle (Erstellen, Bestätigen, Ablehnen, Rücknahme, Dritter-403, Transfer-409, SSE-Event)
- [x] `backend/alembic/versions/0003_reservation_tasks.py` — `reservations.requests`: id UUID PK, requester_location_id UUID FK capacity.locations, target_location_id UUID FK capacity.locations, azr_id VARCHAR(50) NOT NULL, geschlecht VARCHAR(10) NOT NULL, geburtsjahr SMALLINT NOT NULL CHECK(geburtsjahr > 1900), herkunftsland CHAR(3) NOT NULL, belegung_start DATE NOT NULL, belegung_ende DATE NOT NULL CHECK(belegung_ende > belegung_start), status VARCHAR(20) NOT NULL CHECK(status IN ('PENDING','CONFIRMED','REJECTED','CANCELLED','TRANSFERRED')) DEFAULT 'PENDING', confirmed_bed_id UUID nullable FK capacity.beds, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(); `tasks.inbox`: id UUID PK, location_id UUID FK capacity.locations NOT NULL, related_reservation_id UUID nullable FK reservations.requests, task_type VARCHAR(50) NOT NULL, priority VARCHAR(10) NOT NULL CHECK(priority IN ('LOW','MEDIUM','HIGH')), status VARCHAR(20) NOT NULL CHECK(status IN ('OPEN','IN_PROGRESS','DONE','DISMISSED')), title VARCHAR(255) NOT NULL, body TEXT NOT NULL DEFAULT '', created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(); Indexes auf status, location_id, created_at; GRANT INSERT,SELECT,UPDATE ON BOTH TO bordercap_app
- [x] `backend/src/adapters/db/models.py` — ReservationRequestModel(__tablename__="requests", schema="reservations"); TaskModel(__tablename__="inbox", schema="tasks"); alle Felder als Mapped[T]
- [x] `backend/src/domain/reservations/entities.py` — `ReservationStatus(str, Enum)`: PENDING, CONFIRMED, REJECTED, CANCELLED, TRANSFERRED; `ReservationRequest` Dataclass (alle DB-Felder)
- [x] `backend/src/domain/reservations/rules.py` — `RetractionForbiddenError(DomainError)`, `InvalidStateTransitionError(DomainError)`, `check_retraction_allowed(location_id, req)` prüft requester_location_id == location_id OR target_location_id == location_id; `check_state_transition(current, new)` erlaubt nur: PENDING→CONFIRMED, PENDING→REJECTED, PENDING→CANCELLED, CONFIRMED→TRANSFERRED, CONFIRMED→CANCELLED
- [x] `backend/src/domain/tasks/entities.py` — `TaskType(str, Enum)`: RESERVATION_RECEIVED, RESERVATION_CONFIRMED, RESERVATION_REJECTED, RESERVATION_CANCELLED, RESERVATION_TRANSFERRED; `TaskPriority(str, Enum)`: LOW, MEDIUM, HIGH; `TaskStatus(str, Enum)`: OPEN, IN_PROGRESS, DONE, DISMISSED; `Task` Dataclass
- [x] `backend/src/ports/reservations/repository.py` — `AbstractReservationRepo`: `create()`, `get()`, `update_status()`, `list_pending_for_target()`
- [x] `backend/src/ports/tasks/repository.py` — `AbstractTaskRepo`: `create()`, `list_for_location()`, `list_new_since()`
- [x] `backend/src/adapters/db/reservation_repo.py` — `SqlReservationRepo`; `update_status()` macht `SELECT FOR UPDATE` auf reservation, ruft `check_state_transition()`, updated status, ruft `_create_task_and_audit()`; `list_pending_for_target()` sortiert nach created_at ASC; `_create_task_and_audit()` schreibt TaskModel + audit.events in derselben Session/Transaktion
- [x] `backend/src/adapters/db/task_repo.py` — `SqlTaskRepo`; `list_new_since(location_id, since)` für SSE-Polling
- [x] `backend/src/api/reservations/schemas.py` — `ReservationCreate`: azr_id, geschlecht, geburtsjahr, herkunftsland, target_location_id, belegung_start, belegung_ende; Validator belegung_ende > belegung_start; `ReservationResponse`: alle Felder + status
- [x] `backend/src/api/reservations/router.py` — POST /api/reservations (Dependency: get_location_context); GET /api/reservations (filter ?status=); DELETE /api/reservations/{id} → CANCELLED; POST /api/reservations/{id}/confirm → CONFIRMED; POST /api/reservations/{id}/reject → REJECTED; RetractionForbiddenError → 403; InvalidStateTransitionError → 409
- [x] `backend/src/api/tasks/schemas.py` — `TaskResponse`, `TaskPriorityUpdate(priority: TaskPriority)`
- [x] `backend/src/api/tasks/router.py` — GET /api/tasks (X-Location-Id aus get_location_context, filter ?priority=, sort priority DESC / created_at ASC); PATCH /api/tasks/{id} (priority oder status)
- [x] `backend/src/api/notifications/router.py` — GET /api/notifications/stream; `StreamingResponse(media_type="text/event-stream")`; async generator pollt alle 5s `list_new_since(location_id, last_seen)`; sendet `data: {json}\n\n`; HTTP 401 wenn kein Token (get_current_user Dependency)
- [x] `backend/src/main.py` — reservation_router, task_router, notification_router mit `prefix="/api"`, `dependencies=[Depends(get_current_user)]` einbinden
- [x] `tests/steps/reservation_steps.py` — `_post/_get/_delete/_patch` Hilfsfunktionen mit Auth-Header; Steps für alle Workflow-Scenarios; context.reservation_id, context.task_id speichern

**Acceptance Criteria:**
- Given JWT (writer) + X-Location-Id=A, when POST /api/reservations target=B, then HTTP 201 (PENDING) + Task für B in GET /api/tasks mit X-Location-Id=B
- Given X-Location-Id=C (Dritter), when DELETE /api/reservations/{id}, then HTTP 403
- Given ungültiger/fehlender Token, when GET /api/locations, then HTTP 401
- Given X-Location-Id=B (Target), when POST /api/reservations/{id}/confirm, then HTTP 200, status=CONFIRMED, Task für A erzeugt
- Given Reservation status=TRANSFERRED, when DELETE /api/reservations/{id}, then HTTP 409
- Given offene SSE-Verbindung für X-Location-Id=B, when neue Reservation für B erstellt wird, then Event innerhalb 10s
- Given make test, when Behave, then alle reservation_workflow.feature-Scenarios passed, 0 failed

## Spec Change Log

## Design Notes

**JWT-Validation (Ziel 3a bereits fertig):** `get_current_user` in `jwt.py` validiert JWKS-gecachten Token, prüft Issuer und Rollen (reader-plus für GET, writer-plus für mutating). `get_location_context` liest `X-Location-Id`-Header und prüft is_active; wird in Ziel 3b bei den Reservierungs-/Task-Routen als Dependency erzwungen.

**Concurrent Confirmation:** `SELECT ... FOR UPDATE` in `update_status()` sperrt die Reservation-Zeile für die Dauer der Transaktion. Zweiter concurrent Request wartet, liest dann status ≠ PENDING, ruft `check_state_transition()` auf → `InvalidStateTransitionError` → HTTP 409. Kein NOWAIT, kein Retry erforderlich.

**Atomic Task + Audit:** `_create_task_and_audit()` schreibt TaskModel-Insert und INSERT INTO audit.events in derselben Session und Transaktion wie die Statusänderung — entweder alles committed oder alles rolled back.

**SSE-Polling:** Generator in `/notifications/stream` öffnet AsyncSession, `last_seen = datetime.now(UTC)`, Loop: `await asyncio.sleep(5)` → `list_new_since(location_id, last_seen)` → pro Task `data: {json}\n\n` → `last_seen` = jetzt. Client bricht Connection ab → generator wird durch `GeneratorExit` beendet. Kein Redis, kein WebSocket.

**Domain-Fehler-Mapping:** `RetractionForbiddenError(DomainError)` → HTTP 403; `InvalidStateTransitionError(DomainError)` → HTTP 409; `DomainError` (Basis) → HTTP 422.

**after_scenario Teardown (Ergänzung):** `DELETE FROM reservations.requests` und `DELETE FROM tasks.inbox` in `after_scenario()` hinzufügen (in Abhängigkeitsreihenfolge vor capacity.beds).

## Verification

**Commands:**
- `make test` -- expected: `reservation_workflow.feature: 10 scenarios passed, 0 failed`
- `curl http://localhost:8000/api/locations` -- expected: HTTP 401 (kein Token)
- `curl -H "Authorization: Bearer <token>" -H "X-Location-Id: <uuid>" http://localhost:8000/api/reservations` -- expected: JSON-Array
- `docker compose exec backend alembic upgrade head` -- expected: `Running upgrade 0002 -> 0003`

## Suggested Review Order

**Domain — State Machine (Entry Point)**

- Vollständige Transition-Matrix; `VALID_TRANSITIONS`-Dict definiert alle erlaubten Wechsel
  [`rules.py:13`](../../backend/src/domain/reservations/rules.py#L13)

- `check_retraction_allowed`: einzige Regel die Teilnehmer-Identität prüft
  [`rules.py:29`](../../backend/src/domain/reservations/rules.py#L29)

**Repo — Atomicity & Concurrency**

- `update_status`: SELECT FOR UPDATE + State-Check + Task+Audit in einer Transaktion
  [`reservation_repo.py:96`](../../backend/src/adapters/db/reservation_repo.py#L96)

- `confirm` / `reject`: target-location-Prüfung + SELECT FOR UPDATE
  [`reservation_repo.py:129`](../../backend/src/adapters/db/reservation_repo.py#L129)

- `_create_task_and_audit`: alle Task-Typen je Statusübergang + json.dumps für sicheres Audit-JSON
  [`reservation_repo.py:257`](../../backend/src/adapters/db/reservation_repo.py#L257)

- `list_pending_for_target`: FCFS-Sort für `?target=mine`
  [`reservation_repo.py:183`](../../backend/src/adapters/db/reservation_repo.py#L183)

**API Layer**

- POST/GET/DELETE/confirm/reject — `get_location_context` erzwungen; `?target=mine` + Literal-Status
  [`reservations/router.py:31`](../../backend/src/api/reservations/router.py#L31)

- PATCH /tasks/{id} — Ownership-Check via `location_id` an Repo übergeben
  [`tasks/router.py:43`](../../backend/src/api/tasks/router.py#L43)

- SSE Generator: `query_since`/`last_seen` Timing-Fix + `CancelledError` gefangen
  [`notifications/router.py:33`](../../backend/src/api/notifications/router.py#L33)

**Schema & Validation**

- `ReservationCreate`: geburtsjahr-Range + herkunftsland 3-char + belegung_ende > start
  [`reservations/schemas.py:12`](../../backend/src/api/reservations/schemas.py#L12)

**Persistence**

- Migration 0003: beide Tabellen, CHECK-Constraints, 4 Indexes, Grants
  [`0003_reservation_tasks.py:16`](../../backend/alembic/versions/0003_reservation_tasks.py#L16)

- `ReservationRequestModel` + `TaskModel` im ORM
  [`models.py:134`](../../backend/src/adapters/db/models.py#L134)

**Tests**

- 10 Szenarien: alle I/O-Matrix-Fälle inkl. TRANSFERRED-Setup via direktem DB-Write
  [`reservation_workflow.feature:19`](../../tests/features/reservation_workflow.feature#L19)

- Hilfsfunktionen und TRANSFERRED-Vorzustand
  [`reservation_steps.py:251`](../../tests/steps/reservation_steps.py#L251)
