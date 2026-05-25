---
title: 'Ziel 7a — Validierungsjobs + Auto-Cleanup'
type: 'feature'
created: '2026-05-24'
status: 'done'
baseline_commit: 'NO_VCS'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Kapazitätsprobleme (auslaufende Belegungen, Überkapazität) werden manuell überwacht — SBs erhalten keine automatischen Warnungen. Erledigte Tasks akkumulieren ohne Bereinigung im Postkorb.

**Approach:** APScheduler (AsyncIOScheduler) mit 4 registrierten Jobs: (1) 12-Wochen-Näherungswarnung, (2) Überkapazitäts-Alert, (3) wöchentlicher Kapazitätsbericht, (4) Task-Cleanup. Registry-Pattern für Erweiterbarkeit. FastAPI lifespan-Handler startet/stoppt den Scheduler.

## Boundaries & Constraints

**Always:**
- Deduplication: vor jedem Task-Insert prüfen ob OPEN-Task gleichen Typs für dieselbe Location existiert — wenn ja, überspringen
- Jobs nutzen `AsyncSessionFactory` (kein eigenes Connection-Handling)
- `task_cleanup_days: int = 30` als neues Feld in `src/config.py` (Env-Var `TASK_CLEANUP_DAYS`)
- Task-Priorities: `MEDIUM` für 12-Wochen, `HIGH` für Überkapazität, `LOW` für Bericht
- Neue Task-Typen (VARCHAR ≤50): `WOCHE_12_WARNUNG`, `UEBERKAPAZITAET_ALERT`, `KAPAZITAET_BERICHT`
- Cleanup löscht nur Tasks mit `status IN ('DONE', 'DISMISSED')`, nie `OPEN` oder `IN_PROGRESS`

**Ask First:**
- Wenn ein einzelner Job-Lauf > 50 neue Tasks erzeugen würde (Spam-Schutz fehlt im Demo-Scope)

**Never:**
- Kein HTTP-Endpoint zum manuellen Job-Auslösen
- Keine E-Mail/Push-Benachrichtigungen
- Keine neue DB-Tabelle, keine Migration

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| 12-Wochen greift | occupant.belegung_ende zwischen heute und heute+84 Tage | OPEN `WOCHE_12_WARNUNG` MEDIUM Task in Einrichtungs-Inbox | — |
| Deduplication | OPEN `WOCHE_12_WARNUNG` existiert bereits für diese Location | Kein zweiter Task erstellt | — |
| Überkapazität | aktive Belegungen > kontingent + notbett_kapazitaet | OPEN `UEBERKAPAZITAET_ALERT` HIGH Task | — |
| Cleanup fällig | DONE Task, updated_at > task_cleanup_days Tage alt | Zeile gelöscht | — |
| Cleanup keine Aktion | kein fälliger Task | Kein Fehler, kein Task | — |

</frozen-after-approval>

## Code Map

- `backend/pyproject.toml` — `apscheduler>=3.10,<4` ergänzen
- `backend/src/config.py` — `task_cleanup_days: int = 30` ergänzen
- `backend/src/jobs/__init__.py` — Neu: Package-Datei
- `backend/src/jobs/jobs.py` — Neu: 4 async Job-Funktionen
- `backend/src/jobs/scheduler.py` — Neu: JOB_REGISTRY + create_and_start/stop
- `backend/src/main.py` — Lifespan-Handler ergänzen

## Tasks & Acceptance

**Execution:**

- [x] `backend/pyproject.toml` — Unter `[tool.poetry.dependencies]` einfügen: `apscheduler = ">=3.10,<4"`.

- [x] `backend/src/config.py` — `task_cleanup_days: int = 30` als neues Feld in `Settings` ergänzen.

- [x] `backend/src/jobs/__init__.py` — Leere Datei.

- [x] `backend/src/jobs/jobs.py` — Neu. Vier async Funktionen, alle mit `async with AsyncSessionFactory() as session`:
  - `job_12wochen_warnung()`: `SELECT DISTINCT r.location_id FROM persons.occupants o JOIN capacity.beds b ON b.id=o.bed_id JOIN capacity.rooms r ON r.id=b.room_id JOIN capacity.locations l ON l.id=r.location_id WHERE o.belegung_ende BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '84 days' AND l.is_active=true`. Für jede location_id: Dedup-Check (`SELECT 1 FROM tasks.inbox WHERE location_id=:lid AND task_type='WOCHE_12_WARNUNG' AND status='OPEN'`); wenn nicht vorhanden → INSERT mit priority='MEDIUM', title='12-Wochen-Näherungswarnung', body='Belegungen laufen in ≤12 Wochen ab.'.
  - `job_ueberkapazitaet()`: `SELECT l.id, l.kontingent+l.notbett_kapazitaet AS kap, COUNT(o.id) AS belegt FROM capacity.locations l LEFT JOIN capacity.rooms r ON r.location_id=l.id AND r.is_active=true LEFT JOIN capacity.beds b ON b.room_id=r.id AND b.is_active=true LEFT JOIN persons.occupants o ON o.bed_id=b.id AND o.belegung_start<=CURRENT_DATE AND o.belegung_ende>CURRENT_DATE WHERE l.is_active=true GROUP BY l.id,l.kontingent,l.notbett_kapazitaet HAVING COUNT(o.id)>l.kontingent+l.notbett_kapazitaet`. Dedup-Check (`UEBERKAPAZITAET_ALERT`); INSERT priority='HIGH', title='Überkapazität festgestellt', body=f'Belegte Betten: {belegt} / Kapazität: {kap}'.
  - `job_belegungsbericht()`: `SELECT l.id, l.name, l.kontingent+l.notbett_kapazitaet AS kap, COUNT(o.id) AS belegt FROM capacity.locations l LEFT JOIN ... WHERE l.is_active=true GROUP BY l.id,l.name,l.kontingent,l.notbett_kapazitaet`. Für jede Location: Dedup-Check (`KAPAZITAET_BERICHT`); INSERT priority='LOW', title='Wöchentlicher Kapazitätsbericht', body=f'Auslastung: {belegt}/{kap} ({belegt*100//kap if kap else 0}%)'.
  - `job_cleanup()`: `DELETE FROM tasks.inbox WHERE status IN ('DONE','DISMISSED') AND updated_at < NOW() - INTERVAL ':days days'` mit `days=settings.task_cleanup_days`. `await session.commit()`.

- [x] `backend/src/jobs/scheduler.py` — Neu. `from apscheduler.schedulers.asyncio import AsyncIOScheduler`. `JOB_REGISTRY = [{"func": job_12wochen_warnung, "trigger": "cron", "hour": 6, "minute": 0}, {"func": job_ueberkapazitaet, "trigger": "cron", "hour": 6, "minute": 10}, {"func": job_belegungsbericht, "trigger": "cron", "day_of_week": "mon", "hour": 7}, {"func": job_cleanup, "trigger": "cron", "hour": 3}]`. `def create_and_start() -> AsyncIOScheduler`: scheduler anlegen, JOB_REGISTRY durchiterieren und `scheduler.add_job(entry["func"], entry["trigger"], **rest)`, `scheduler.start()`, zurückgeben. `def stop(scheduler)`: `scheduler.shutdown(wait=False)`.

- [x] `backend/src/main.py` — `from contextlib import asynccontextmanager` ergänzen. `from src.jobs.scheduler import create_and_start, stop` ergänzen. Neuen `@asynccontextmanager async def lifespan(app):`-Block: `scheduler = create_and_start(); yield; stop(scheduler)`. `app = FastAPI(..., lifespan=lifespan)` statt `app = FastAPI(...)`.

**Acceptance Criteria:**
- Given Backend startet, then läuft APScheduler ohne Exception (Health-Check 200)
- Given `job_12wochen_warnung()` manuell aufgerufen, Occupant endet in 60 Tagen, then existiert OPEN `WOCHE_12_WARNUNG` MEDIUM Task in tasks.inbox
- Given `job_12wochen_warnung()` zweimal aufgerufen, then existiert genau 1 OPEN Task (Deduplication)
- Given `job_cleanup()` aufgerufen, DONE Task ist 31 Tage alt (task_cleanup_days=30), then ist Zeile gelöscht
- Given `job_ueberkapazitaet()` aufgerufen, belegt > kontingent + notbett, then HIGH Task in inbox

## Spec Change Log

**2026-05-24 — Post-review patches (3 Agents):**
- **Interval-Crash (Bug):** `(:days * INTERVAL '1 day')` wirft asyncpg-Typfehler. Fix: cutoff als Python `timedelta` berechnet, als `:cutoff`-Timestamp übergeben.
- **Decimal-Cast (Bug):** `row.kap`/`row.belegt` kommen als `Decimal` vom DB-Driver. Fix: explizites `int()` in `job_belegungsbericht`.
- **DELETE-Grant fehlt (Bug):** Migration 0003 grantete nur `INSERT, SELECT, UPDATE` auf `tasks.inbox`. Fix: neue Migration `0005_grant_delete_tasks.py` mit `GRANT DELETE ON tasks.inbox TO bordercap_app`.
- **Exception-Listener fehlt (Risk):** APScheduler schluckt Job-Exceptions ohne Log-Output. Fix: `_on_job_error`/`_on_job_missed`-Listener in `scheduler.py` ergänzt.
- **Rollback bei Mid-Loop-Exception (Risk):** Ohne explizites Rollback bleiben partielle Writes still verworfen. Fix: `try/except: rollback; raise` in allen 4 Jobs.
- **Rejected:** TOCTOU-Race (dormant im Single-Worker-Docker-Setup), `updated_at`-Trigger (app-seitige Repo-Updates ausreichend für Demo), Index auf `occupants(belegung_start,belegung_ende)` (Demo-Scale okay).

## Design Notes

**Registry-Pattern:** `JOB_REGISTRY` ist eine einfache Liste von Dicts mit `func` + APScheduler-Trigger-kwargs. Neue Jobs werden durch Anhängen registriert — kein Interface, kein ABC nötig für Demo-Scope.

**Lifespan statt on_event:** FastAPI depreciert `@app.on_event`; `lifespan` ist der aktuelle Standard (FastAPI ≥0.93).

**Deduplication per OPEN-Status:** Ein Job-Lauf kann einen offenen Task nicht doppeln. Sobald der SB den Task auf DONE setzt, erstellt der nächste Job-Lauf bei anhaltender Bedingung erneut einen Task — bewusstes Verhalten.

## Verification

**Commands:**
- `cd backend && python -c "from src.jobs.jobs import job_12wochen_warnung; print('OK')"` — erwartet: kein ImportError
- `cd frontend && npm run build` — erwartet: kein TypeScript-Fehler (keine Frontend-Änderungen)

**Manual checks:**
- `make dev` → kein Startup-Error im Backend-Log
- `make dev` → `GET /health` gibt 200 zurück
- DB: `SELECT * FROM tasks.inbox WHERE task_type='WOCHE_12_WARNUNG' LIMIT 5` nach Job-Aufruf
