---
title: 'BorderCapControl — JWT-Auth-Retrofit (Ziel 3a/7)'
type: 'feature'
created: '2026-05-23'
status: 'done'
baseline_commit: 'NO_VCS'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Alle `/api/`-Endpoints aus Ziel 2 sind vollständig offen — keine Authentifizierung, kein Zugriffsschutz. Das ist für einen Demo-Betrieb inakzeptabel.

**Approach:** FastAPI-Dependency `get_current_user` mit Keycloak-JWT-Validation (python-jose + JWKS-Cache) wird auf alle `/api/`-Router angewendet. `/health` bleibt offen. Bestehende Behave-Tests (Ziel 1+2) erhalten einmalig einen Auth-Token-Setup in `environment.py` damit sie weiterhin laufen.

## Boundaries & Constraints

**Always:**
- Alle `/api/`-Endpoints erfordern einen gültigen Keycloak Bearer-Token (Rolle `writer` oder höher für mutierende Endpoints; `reader` für GET). `/health` und FastAPI `/docs`, `/openapi.json` bleiben offen.
- JWKS-Endpoint: `{keycloak_url}/realms/{realm}/protocol/openid-connect/certs`. In-Memory-Cache mit TTL 5 Minuten (kein Redis). Erster Request fetched synchron via httpx.
- Bei ungültigem/fehlendem Token: HTTP 401 mit `{"detail": "Not authenticated"}`.
- Token-Audience-Check: `iss` muss `{keycloak_url}/realms/{realm}` entsprechen.
- `X-Location-Id`-Header: nur validieren dass die UUID eine aktive Location ist (HTTP 403 wenn nicht) — wird von mutierenden Reservierungs-Endpoints (Ziel 3b) genutzt; in Ziel 3a nur die Dependency `get_location_context` bereitstellen, noch nicht erzwingen.
- `python-jose[cryptography]` ist bereits in pyproject.toml — keine neuen Packages nötig.
- Bestehende Behave-Scenarios dürfen nach dieser Änderung NICHT brechen.

**Ask First:** — (alle Fragen beantwortet)

**Never:**
- Kein Rate-Limiting, kein RBAC jenseits Rollen-Check (Ziel 3b/4).
- Kein Token-Refresh-Mechanismus im Backend.
- Keinen Breaking Change an bestehenden Endpoint-Signaturen.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output | Error Handling |
|----------|--------------|-----------------|----------------|
| Valider Token | GET /api/locations + Bearer Token (role=reader+) | 200 + JSON-Array | — |
| Kein Token | GET /api/locations ohne Authorization-Header | 401 | — |
| Abgelaufener Token | Bearer Token mit exp in der Vergangenheit | 401 | — |
| Falscher Issuer | Token von anderem Keycloak-Realm | 401 | — |
| /health ohne Token | GET /health | 200 (kein Auth-Check) | — |

</frozen-after-approval>

## Code Map

Bestehend (geändert):
- `backend/src/main.py` — Router-Einbindung; alle capacity/... Router bekommen Dependency
- `tests/environment.py` — before_all() Token-Setup; after_scenario() DB-Teardown (unverändert)
- `tests/steps/capacity_steps.py` — _post/_get/_delete Funktionen ergänzen
- `tests/steps/smoke_steps.py` — analog

Neu in Ziel 3a:
- `backend/src/adapters/keycloak/__init__.py` — leer
- `backend/src/adapters/keycloak/jwt.py` — JWKS-Fetch + Cache + Decode, UserContext Dataclass, get_current_user Dependency, get_location_context Dependency (bereitgestellt, noch nicht erzwungen)

## Tasks & Acceptance

**Execution:**
- [x] `backend/src/adapters/keycloak/jwt.py` — `UserContext(sub: str, roles: list[str])`; `_fetch_jwks()` via httpx, cached mit `_jwks_cache` + `_jwks_fetched_at` (TTL 5 min); `async def get_current_user(request: Request) -> UserContext` prüft Authorization-Header, decoded JWT, prüft Issuer; HTTP 401 bei Fehler; `async def get_location_context(x_location_id: UUID, session=Depends(...)) -> Location` prüft DB-Existenz + is_active; HTTP 403 wenn nicht aktiv
- [x] `backend/src/main.py` — `from src.adapters.keycloak.jwt import get_current_user`; `app.include_router(capacity_router, prefix="/api", dependencies=[Depends(get_current_user)])`; /health Route bleibt ohne Dependency
- [x] `tests/environment.py` — `before_all(context)`: POST `{keycloak_url}/realms/{realm}/protocol/openid-connect/token` mit writer_user-Credentials (aus Env-Variablen), speichert Token in `context.auth_token`; `_get_auth_headers(context)` Hilfsfunktion exportieren
- [x] `tests/steps/capacity_steps.py` — `_post/_get/_delete` erhalten optionales `headers`-Argument; alle Aufrufe übergeben `_get_auth_headers(context)` aus `environment`
- [x] `tests/steps/smoke_steps.py` — analog zu capacity_steps.py

**Acceptance Criteria:**
- Given kein Authorization-Header, when GET /api/locations, then HTTP 401
- Given abgelaufener Token, when GET /api/locations, then HTTP 401
- Given Token mit role=writer, when GET /api/locations, then HTTP 200
- Given GET /health ohne Token, then HTTP 200 oder 503 (kein 401)
- Given make test, when Behave, then alle bestehenden capacity_crud.feature- und smoke.feature-Scenarios passed (kein Regression durch Auth)

## Spec Change Log

## Design Notes

**JWKS-Cache:** Modul-globale Variablen `_jwks_cache: dict | None = None` und `_jwks_fetched_at: datetime | None = None`. Bei jedem Request: wenn Cache älter als 5 min → re-fetch. Thread-safety ist bei asyncio single-threaded nicht nötig.

**Keycloak-Token für Tests:** `before_all()` in `environment.py` ruft den Keycloak Resource-Owner-Password-Flow (`grant_type=password`) mit `writer_user` / `Writer1234!` auf. Token wird in `context.auth_token` gespeichert und von allen Steps via `{"Authorization": f"Bearer {context.auth_token}"}` genutzt.

## Verification

**Commands:**
- `make test` -- expected: alle smoke.feature + capacity_crud.feature + auth.feature Scenarios passed, 0 failed
- `curl http://localhost:8000/api/locations` -- expected: HTTP 401
- `curl -H "Authorization: Bearer <token>" http://localhost:8000/api/locations` -- expected: HTTP 200 + JSON
- `curl http://localhost:8000/health` -- expected: HTTP 200 oder 503 (kein 401)

## Suggested Review Order

**JWT Validation Core**

- Entry point: JWKS-Fetch, issuer-check, role-hierarchy enforcement all in one dependency
  [`jwt.py:57`](../../backend/src/adapters/keycloak/jwt.py#L57)

- In-memory JWKS cache with 5-min TTL; single httpx call per cache miss
  [`jwt.py:36`](../../backend/src/adapters/keycloak/jwt.py#L36)

- Role-hierarchy frozensets — `_READER_PLUS` / `_WRITER_PLUS` — define what "or higher" means
  [`jwt.py:32`](../../backend/src/adapters/keycloak/jwt.py#L32)

- Role check: method-based dispatch (GET → reader-plus, mutating → writer-plus)
  [`jwt.py:79`](../../backend/src/adapters/keycloak/jwt.py#L79)

- `get_location_context`: prepared for Ziel 3b; not yet wired to any route in Ziel 3a
  [`jwt.py:97`](../../backend/src/adapters/keycloak/jwt.py#L97)

**Router Wiring**

- Single `dependencies=` call applies auth to all `/api/` routes; `/health` stays open
  [`main.py:28`](../../backend/src/main.py#L28)

**Keycloak Realm**

- `bordercapcontrol-test` client: confidential ROPC-enabled client for Behave token fetch
  [`realm-export.json:81`](../../infra/keycloak/realm-export.json#L81)

**Test Infrastructure**

- `before_all`: ROPC token fetch; now fail-fast (AssertionError) if Keycloak unavailable
  [`environment.py:28`](../../tests/environment.py#L28)

- New auth scenarios: "no token → 401" and "health open without token"
  [`auth.feature:7`](../../tests/features/auth.feature#L7)

- New unauthenticated-request steps + `ist der HTTP-Status nicht 401` assertion
  [`capacity_steps.py:41`](../../tests/steps/capacity_steps.py#L41)

- Helper functions: `_post/_get/_delete` transparently inject auth header from context
  [`capacity_steps.py:20`](../../tests/steps/capacity_steps.py#L20)
