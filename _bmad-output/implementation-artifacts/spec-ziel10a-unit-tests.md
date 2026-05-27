---
title: 'Ziel 10a — pytest Unit-Tests: Domain-Regeln'
type: 'test'
created: '2026-05-27'
status: 'done'
baseline_commit: 'NO_VCS'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Domain-Regeln in `src/domain/capacity/rules.py` und `src/domain/reservations/rules.py` haben keine automatisierten Unit-Tests. Diese sind reine Funktionen ohne I/O — ideal für schnelle, infrastrukturfreie pytest-Tests.

**Approach:** `backend/tests/domain/test_capacity_rules.py` + `test_reservation_rules.py` mit pytest. Keine DB, kein HTTP, kein laufender Stack.

## Boundaries & Constraints

- Tests laufen via `cd backend && pytest tests/domain/ -v`.
- Ausschließlich pytest — kein pytest-asyncio, kein httpx, keine Fixtures mit DB.
- 100% der öffentlichen Funktionen in beiden rules.py-Dateien abgedeckt (Happy + Error Paths).

## Tasks & Acceptance

- [x] `backend/tests/__init__.py` und `backend/tests/domain/__init__.py` — leere Init-Dateien erstellen.
- [x] `backend/tests/domain/test_capacity_rules.py` — Tests für alle 4 Funktionen in `capacity/rules.py`.
- [x] `backend/tests/domain/test_reservation_rules.py` — Tests für `check_retraction_allowed` und `check_state_transition`.

**Acceptance Criteria:**
- `pytest backend/tests/domain/ -v` läuft ohne Fehler durch
- Alle Happy-Path- und Fehler-Szenarien aus der I/O-Matrix abgedeckt

</frozen-after-approval>

## Code Map

- `backend/tests/__init__.py` (neu, leer)
- `backend/tests/domain/__init__.py` (neu, leer)
- `backend/tests/domain/test_capacity_rules.py` (neu)
- `backend/tests/domain/test_reservation_rules.py` (neu)

## I/O & Testmatrix

| Funktion | Eingabe | Erwartet |
|---|---|---|
| `check_notbett_duration(NOTBETT, d, d+1)` | 1 Tag | kein Fehler |
| `check_notbett_duration(NOTBETT, d, d+3)` | 3 Tage | DomainError |
| `check_notbett_duration(KONTINGENT, d, d+3)` | beliebig | kein Fehler |
| `check_12_weeks(d, d+84)` | exakt 84 Tage | False |
| `check_12_weeks(d, d+85)` | 85 Tage | True |
| `check_eu_quota(0, 0, 0)` | quota=0 | kein Fehler (deaktiviert) |
| `check_eu_quota(180, 30, 200)` | 210 > 200 | DomainError |
| `check_eu_quota(150, 30, 200)` | 180 ≤ 200 | kein Fehler |
| `check_bed_available(None)` | frei | kein Fehler |
| `check_bed_available("irgendwas")` | belegt | DomainError |
| `check_retraction_allowed(loc_a, req_a, False)` | requester=loc_a | kein Fehler |
| `check_retraction_allowed(loc_b, req_a, False)` | fremde Location | RetractionForbiddenError |
| `check_retraction_allowed(None, req_a, True)` | system-admin | kein Fehler |
| `check_state_transition("PENDING", "CONFIRMED")` | erlaubt | kein Fehler |
| `check_state_transition("PENDING", "TRANSFERRED")` | nicht erlaubt | InvalidStateTransitionError |
| `check_state_transition("CONFIRMED", "PENDING")` | nicht erlaubt | InvalidStateTransitionError |

## Verification

- `cd backend && pytest tests/domain/ -v` → alle Tests grün, kein ImportError
