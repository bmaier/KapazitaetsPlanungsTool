---
title: 'Fachliches Audit-Log — rechtssichere Protokollierung, UI, Export, DSGVO-Löschung'
type: 'feature'
created: '2026-05-29'
status: 'done'
baseline_commit: '241edbb7053806cf8f41a22c85415fa5920cb9fe'
context:
  - '{project-root}/docs/KONZEPT.md'
  - '{project-root}/backend/src/adapters/keycloak/jwt.py'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Das System loggt bisher nur Vorschlags-Events ohne Akteur, Einrichtung oder Entitätsbezug. Einbuchungen, Ausbuchungen und Verlegungsschritte werden nicht vollständig protokolliert. Eine rechtssichere, gerichtsfeste Nachvollziehbarkeit (wer hat wann was an welcher Person getan?) fehlt vollständig — ebenso eine UI zur Einsicht, ein CSV-Export und eine DSGVO-konforme Löschfunktion.

**Approach:** Bestehende `audit.events`-Tabelle um Akteur-Felder erweitern (Migration 0014). Zentraler Audit-Service ersetzt alle Streu-INSERTs. Alle fachlichen Mutationen (Einbuchung, Ausbuchung, Verlegung, Reservierungsworkflow) werden nachgepflegt. Neuer `/api/audit`-Router mit gefilterter List-, CSV-Export-, und DSGVO-Lösch-Endpoint. Neue Frontend-Seite mit letzte 5-Tage-Default, AZR-Suche, Export-Button, Lösch-Dialogen.

## Boundaries & Constraints

**Always:**
- `audit.events` ist append-only: kein UPDATE auf bestehenden Zeilen (außer DSGVO-Löschung)
- Jeder Audit-Eintrag enthält: `actor_id` (Keycloak-Sub), `actor_role` (höchste Rolle), `location_id`, `entity_type`, `entity_id`, `event_type`, `payload` (JSONB), `created_at`
- CSV-Export und DSGVO-Löschung erfordern Rolle `location-admin` oder `system-admin`
- Löschung aller Einträge > 10 Jahre: nur `system-admin`
- CSV-Export wird als StreamingResponse generiert — kein vollständiges In-Memory-Laden
- Neue Spalten nullable (Backward-Compat zu bestehenden Einträgen ohne Akteur)

**Ask First:**
- DSGVO-Löschung bei AZR: Hard-Delete (Zeilen entfernen) oder Anonymisierung (AZR durch Hash ersetzen)? Default-Annahme: Hard-Delete — bei anderem Wunsch vor Implementierung fragen.

**Never:**
- Keine READ-Operationen (GET, LIST) in das Audit-Log aufnehmen
- Kein separates Audit-Schema anlegen — bestehende Tabelle erweitern
- Export-Button nicht für `reader`/`writer`-Rollen sichtbar

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output | Error Handling |
|---|---|---|---|
| Einbuchung | POST /api/occupants (Bett belegen) | Audit-Eintrag OCCUPANCY_CREATED mit azr_id, bed_id, actor | — |
| Ausbuchung | DELETE /api/occupants/{id} | Audit-Eintrag OCCUPANCY_DELETED mit azr_id, bed_id, actor | — |
| Verlegung bestätigt | PATCH /confirm | Audit RESERVATION_CONFIRMED mit reservation_id, azr_id, actor | — |
| List-Filter AZR | GET /api/audit?azr_id=AZR-2024-FFM-M-01 | Nur Einträge für diese AZR, paginiert | 400 wenn azr_id leer |
| CSV-Export (groß) | GET /api/audit/export.csv?date_from=... (100k Rows) | Streaming-Download, kein OOM | — |
| DSGVO-Löschung AZR | DELETE /api/audit/azr/{azr_id} | Alle Zeilen mit entity_id=azr_id gelöscht, Anzahl zurück | 403 wenn nicht admin |
| Löschung > 10 Jahre | DELETE /api/audit/purge-old | Alle Einträge älter als 10 Jahre gelöscht, Anzahl zurück | 403 wenn nicht system-admin |
| Unauthorized Export | GET /api/audit/export.csv als `writer` | HTTP 403 | — |

</frozen-after-approval>

## Code Map

- `backend/alembic/versions/0014_audit_extended.py` -- Migration: neue Spalten + Indexes auf audit.events
- `backend/src/adapters/db/audit_service.py` -- NEU: zentraler `write_audit()`-Service (ersetzt Streu-INSERTs)
- `backend/src/adapters/db/capacity_repo.py` -- OCCUPANCY_CREATED / OCCUPANCY_DELETED Events ergänzen
- `backend/src/adapters/db/reservation_repo.py` -- actor_id/role in alle _write_audit()-Calls ergänzen
- `backend/src/api/audit/router.py` -- NEU: GET /api/audit, GET /api/audit/export.csv, DELETE /api/audit/azr/{azr_id}, DELETE /api/audit/purge-old
- `backend/src/api/audit/schemas.py` -- NEU: AuditEntryOut, AuditListResponse
- `backend/src/main.py` -- neuen audit-Router registrieren
- `frontend/src/pages/AuditLog.tsx` -- NEU: Seite mit Filter, Tabelle, Export-Button, Lösch-Dialoge
- `frontend/src/components/NavBar.tsx` -- Link "Protokoll" ergänzen (sichtbar für location-admin+)
- `frontend/src/App.tsx` -- Route `/audit` → AuditLog registrieren
- `docs/KONZEPT.md` -- Abschnitt "Fachliche Protokollierung" ergänzen

## Tasks & Acceptance

**Execution:**
- [x] `backend/alembic/versions/0014_audit_extended.py` -- Migration: ADD COLUMN actor_id VARCHAR(255), actor_role VARCHAR(50), location_id UUID, entity_type VARCHAR(50), entity_id VARCHAR(255); CREATE INDEX auf created_at, entity_id, location_id, actor_id
- [x] `backend/src/adapters/db/audit_service.py` -- write_audit(session, event_type, payload, user: UserContext, location_id, entity_type=None, entity_id=None) implementieren; bestehende Streu-INSERTs in reservation_repo.py + suggestions/router.py auf write_audit() umstellen
- [x] `backend/src/adapters/db/capacity_repo.py` -- In create_occupant() und delete_occupant() je einen write_audit()-Call einfügen (OCCUPANCY_CREATED / OCCUPANCY_DELETED); UserContext als Parameter durchschleifen
- [x] `backend/src/api/audit/router.py` -- GET /api/audit (paginiert, Filter: date_from/date_to/azr_id/event_type/location_id), GET /api/audit/export.csv (StreamingResponse, location-admin+), DELETE /api/audit/azr/{azr_id} (location-admin+, Bestätigungsparameter confirm=true), DELETE /api/audit/purge-old (system-admin only)
- [x] `backend/src/api/audit/schemas.py` -- AuditEntryOut (alle Felder), AuditListResponse (items, total, page, page_size)
- [x] `backend/src/main.py` -- audit_router einbinden unter /api/audit
- [x] `frontend/src/pages/AuditLog.tsx` -- Filter (date_from default -5d, date_to, azr_id, event_type), Tabelle (MUI DataGrid oder manuell), Export-Button (nur wenn location-admin+), DSGVO-Lösch-Dialog (AZR), Admin-Button für Purge-Old (nur system-admin); Bestätigungs-Dialog vor Löschung
- [x] `frontend/src/components/NavBar.tsx` -- "Protokoll"-Link mit HistoryIcon, sichtbar für Rolle >= location-admin
- [x] `frontend/src/App.tsx` -- Route /audit eintragen
- [x] `docs/KONZEPT.md` -- Abschnitt 7b "Fachliche Protokollierung" hinzufügen: Event-Typen, Akteur-Felder, Aufbewahrungsfristen, DSGVO-Rechte

**Acceptance Criteria:**
- Given eine Einbuchung wird durchgeführt, when POST /api/occupants, then enthält audit.events einen OCCUPANCY_CREATED-Eintrag mit actor_id, location_id und azr_id im payload
- Given ein location-admin filtert nach AZR "AZR-2024-FFM-M-01", when GET /api/audit?azr_id=AZR-2024-FFM-M-01, then kommen nur Einträge für diese AZR, paginiert mit max. 100 pro Seite
- Given ein location-admin klickt "CSV exportieren" mit aktivem Filter, when der Download startet, then kommt ein Streaming-Response ohne Timeout auch bei 10.000+ Zeilen
- Given ein writer-User versucht den CSV-Export, when GET /api/audit/export.csv, then HTTP 403
- Given ein location-admin löscht AZR "XYZ" via Bestätigungs-Dialog, when DELETE /api/audit/azr/XYZ?confirm=true, then sind alle Einträge mit entity_id="XYZ" gelöscht und die Anzahl wird zurückgegeben
- Given ein system-admin klickt "Einträge > 10 Jahre löschen", when DELETE /api/audit/purge-old, then werden alle Einträge älter als 10 Jahre entfernt
- Given die AuditLog-Seite öffnet, when kein Filter gesetzt, then zeigt sie default die letzten 5 Tage

## Design Notes

**Streaming CSV:** FastAPI `StreamingResponse` mit Generator:
```python
async def csv_generator(rows):
    yield "timestamp;event_type;actor_id;actor_role;location_id;entity_id;payload\n"
    async for row in rows:
        yield f"{row.created_at};{row.event_type};...;\"{row.payload}\"\n"
return StreamingResponse(csv_generator(...), media_type="text/csv",
    headers={"Content-Disposition": "attachment; filename=audit.csv"})
```
Cursor-basiert (SQLAlchemy `stream_results=True`), kein `.all()`.

**DSGVO Hard-Delete:** `DELETE FROM audit.events WHERE entity_id = :azr_id` plus `WHERE payload->>'azr_id' = :azr_id` (Fallback für ältere Einträge ohne entity_id). Rückgabe: `{"deleted": N}`.

**Bulk-Purge Safety:** `DELETE ... WHERE created_at < NOW() - INTERVAL '10 years'` in einer Transaktion; Rückgabe Anzahl gelöschter Zeilen.

## Verification

**Commands:**
- `cd frontend && npx tsc --noEmit` -- expected: 0 errors
- `cd tests && python3 -m behave features/smoke.feature` -- expected: all green
- `curl -s http://localhost:8000/api/audit?date_from=2026-01-01 -H "Authorization: Bearer $TOKEN" -H "X-Location-Id: ..."` -- expected: JSON mit items-Array

**Manual checks:**
- Einbuchung durchführen → Protokoll-Seite öffnen → OCCUPANCY_CREATED-Eintrag sichtbar
- Als writer: Export-Button nicht sichtbar / 403 bei direktem API-Aufruf
- CSV-Download enthält Kopfzeile + korrekte Datensätze
- Nach AZR-Löschung: Eintrag in Tabelle verschwunden, Bestätigungsmeldung angezeigt
