---
title: 'Ziel 7b — EU-Compliance-Reporting (PDF)'
type: 'feature'
created: '2026-05-24'
status: 'done'
baseline_commit: 'NO_VCS'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** SBs und Leitungen haben keine Möglichkeit, den EU-Compliance-Status (Kontingentnutzung vs. EU-Gesamtquote) als druckbares Dokument zu exportieren — manuelle Datenaufbereitung ist fehleranfällig und zeitaufwendig.

**Approach:** Neuer Endpoint `GET /api/reports/eu-compliance?zeitraum=monat|quartal|jahr` generiert serverseitig ein PDF (WeasyPrint) mit Belegungsauslastung und Kontingentnutzung je Einrichtung und gibt es als Download zurück. Kein Frontend-Page-Build nötig — Download über direkte URL.

## Boundaries & Constraints

**Always:**
- Authentifizierung erforderlich (`get_current_user`), aber kein Location-Scope — Report zeigt alle aktiven Einrichtungen
- `zeitraum`-Werte: genau `monat` (laufender Kalendermonat), `quartal` (laufendes Quartal), `jahr` (laufendes Kalenderjahr) — ungültige Werte → 422
- Belegungszählung: Occupants, deren Zeitraum den Report-Zeitraum überlappt (`belegung_start <= period_end AND belegung_ende >= period_start`)
- EU-Gesamtquote aus `capacity.system_settings` (Singleton id=1)
- Response: `StreamingResponse` mit `Content-Type: application/pdf`, `Content-Disposition: attachment; filename=eu-compliance-{zeitraum}-{YYYY-MM-DD}.pdf`
- WeasyPrint-system-libs im `backend/Dockerfile` (libpango, libcairo, libgdk-pixbuf2.0) ergänzen

**Ask First:**
- Wenn WeasyPrint-Build im Docker länger als 3 Minuten dauert (Fallback: ReportLab oder xhtml2pdf)

**Never:**
- Kein neues Frontend-Feature (kein React-Page, kein Button)
- Keine neue DB-Tabelle, keine Migration
- Kein Caching der PDF-Ausgabe (Demo-Scope)
- Kein Export anderer Formate (Excel, CSV)

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Gültiger Zeitraum | `?zeitraum=monat` | PDF mit Monatsdaten aller aktiven Einrichtungen | — |
| Ungültiger Zeitraum | `?zeitraum=woche` | 422 Unprocessable Entity | FastAPI-Enum-Validierung |
| EU-Quote = 0 | `eu_gesamtquote = 0` | Report zeigt "0" als EU-Quote, kein Fehler | — |
| Keine aktiven Locations | `is_active = false` für alle | Leere Tabelle, PDF wird trotzdem erzeugt | — |
| Nicht eingeloggt | kein Token | 401 Unauthorized | Standard-FastAPI-Auth |

</frozen-after-approval>

## Code Map

- `backend/Dockerfile` — system-libs für WeasyPrint ergänzen (builder + final stage)
- `backend/pyproject.toml` — `weasyprint>=62,<63` ergänzen
- `backend/src/api/reports/__init__.py` — Neu: leeres Package
- `backend/src/api/reports/router.py` — Neu: GET-Endpoint, SQL, HTML-Template, PDF-Generierung
- `backend/src/main.py` — reports-Router registrieren

## Tasks & Acceptance

**Execution:**

- [x] `backend/Dockerfile` — In **builder** stage nach `gcc`-Block und in **final** stage nach `curl`-Block je ergänzt: `libpango-1.0-0 libpangocairo-1.0-0 libcairo2 libgdk-pixbuf-xlib-2.0-0 libfontconfig1 libharfbuzz0b`. (Hinweis: `libgdk-pixbuf2.0-0` nicht in python:3.11-slim-Repos → ersetzt durch `libgdk-pixbuf-xlib-2.0-0`)

- [x] `backend/pyproject.toml` — `weasyprint = ">=62,<63"` ergänzt.

- [x] `backend/src/api/reports/__init__.py` — Leere Datei.

- [x] `backend/src/api/reports/router.py` — Vollständig implementiert. Review-Fixes eingearbeitet (siehe Spec Change Log).

- [x] `backend/src/main.py` — `reports_router` registriert mit `prefix="/api"` und `Depends(get_current_user)`.

**Acceptance Criteria:**
- Given eingeloggter User, `GET /api/reports/eu-compliance?zeitraum=monat`, then Response-Status 200, Content-Type `application/pdf`, Dateiinhalt ist valides PDF (beginnt mit `%PDF`)
- Given `?zeitraum=woche`, then 422 mit Feldmeldung
- Given kein Auth-Token, then 401
- Given EU-Gesamtquote=500, 2 Locations mit kontingent=200 bzw. 350, then Fußzeile zeigt Gesamt=550, EU-Quote=500

## Spec Change Log

| # | Quelle | Befund | Fix |
|---|---|---|---|
| 1 | Edge Case Hunter | `weasyprint.write_pdf()` ist synchron/CPU-bound — blockiert asyncio event loop | `asyncio.to_thread(weasyprint.HTML(string=html).write_pdf)` |
| 2 | Blind Hunter | `r.name` raw in HTML-String interpoliert → XSS/HTML-Injection möglich | `from html import escape; escape(r.name)` |
| 3 | Edge Case Hunter | `_ampel_class(0, 0, 0)` gibt `"yellow"` zurück (0 >= 0) — unkonfigurierte Einrichtungen wirken aktiv | Guard: `if kontingent == 0 and notbett == 0: return "grey"` |
| 4 | Edge Case Hunter | `eu_gesamtquote=0` (COALESCE-Default) → Footer zeigt rot obwohl Quote nie gesetzt wurde | Sentinel-Prüfung: `if eu_gesamtquote == 0` → `eu_status_class="grey"`, `eu_quota_display="Nicht konfiguriert"`, Warning-Text statt rot |
| 5 | Blind Hunter | SQL-CROSS JOIN ohne COALESCE → CROSS JOIN auf leere system_settings → alle Zeilen fallen weg | CROSS JOIN umgeschrieben auf `COALESCE((SELECT eu_gesamtquote FROM ... WHERE id=1), 0)` |
| 6 | Acceptance Auditor | Auslastungs-Prozent mit Integer-Division `//` → ungenaue Darstellung | `:.0f`-Format-String statt `//` |
| 7 | Acceptance Auditor | Redundanter `_user=Depends(get_current_user)` im Handler (Auth bereits via `include_router`) | Entfernt |

## Design Notes

**WeasyPrint statt ReportLab:** WeasyPrint erlaubt HTML+CSS als Template — kein proprietäres API nötig. Demo-Layout entsteht direkt aus dem HTML-String ohne Versionierung.

**CROSS JOIN für eu_gesamtquote:** Statt zwei Queries (eine für Locations, eine für SystemSettings) holt der CROSS JOIN den Singleton-Wert in derselben Query und vermeidet zwei Roundtrips.

**`Literal`-Enum für zeitraum:** FastAPI validiert den Query-Parameter automatisch gegen die erlaubten Werte — kein manuelles `HTTPException` nötig.

## Verification

**Commands:**
- `cd backend && python -c "from src.api.reports.router import router; print('OK')"` — erwartet: kein ImportError
- `cd frontend && npm run build` — erwartet: kein TypeScript-Fehler (keine Frontend-Änderungen)

**Manual checks:**
- Nach `make down && make dev && make migrate`: `curl -H "Authorization: Bearer <token>" "http://localhost:8000/api/reports/eu-compliance?zeitraum=monat" --output test.pdf && file test.pdf` → `test.pdf: PDF document`
