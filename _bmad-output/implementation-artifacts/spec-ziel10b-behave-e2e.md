---
title: 'Ziel 10b — Behave E2E Tests: HF-17/18/19/22 + Smoke-Fix'
type: 'test'
created: '2026-05-27'
status: 'done'
baseline_commit: 'NO_VCS'
context: []
---

## Summary

Neue Behave-E2E-Szenarien für die in Ziel 9 implementierten Schutzregeln.
Dry-Run mit 0 undefined Steps verifiziert — Ausführung erfordert laufenden Stack (`make dev`).

## Änderungen

- [x] `tests/features/ziel9_guards.feature` (neu) — 9 Szenarien für HF-17/18/19/22
- [x] `tests/steps/ziel9_steps.py` (neu) — Given/When/Then für die neuen Szenarien
- [x] `tests/steps/smoke_steps.py` — 2 Duplikate (`ist der HTTP-Status`, `die Antwort enthält ... mit Wert`) entfernt
- [x] `tests/features/capacity_crud.feature`, `reservation_workflow.feature` — `# language: de` entfernt (Parser-Fix)

## Szenarien

| HF | Szenario | Erwarteter Status |
|---|---|---|
| HF-18 | Raum mit aktiver Belegung deaktivieren | 409 |
| HF-18 | Leerer Raum deaktivieren | 200 |
| HF-19 | Kontingent unter Belegung senken | 409 |
| HF-19 | Kontingent auf Belegungszahl setzen | 200 |
| HF-17 | Belegung auf abgelaufener Einrichtung | 409 |
| HF-17 | Belegung auf unbefristeter Einrichtung | 201 |
| HF-22 | Notbett erstmals verlängern | 200 |
| HF-22 | Notbett zweimal verlängern | 409 |
| HF-22 | Kontingent-Bett über extend | 422 |

## Ausführung

```
cd tests && python3 -m behave features/ziel9_guards.feature
```
