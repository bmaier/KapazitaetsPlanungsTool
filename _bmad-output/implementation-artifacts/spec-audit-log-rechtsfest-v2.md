---
title: 'Audit-Log rechtsfest v2 — vollständige Persistenz + Detailansicht'
type: 'feature'
created: '2026-06-06'
status: 'done'
baseline_commit: '6a4cc12dd02ba7c6ffaaccf1ac1dc52ee3892d4f'
context:
  - '{project-root}/_bmad-output/project-context.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Das bestehende Audit-Log ist für rechtssichere Dokumentation unvollständig: (1) Ablehnungsgründe werden im UI erfasst, aber nie ans Backend gesendet und gehen verloren; (2) `OCCUPANCY_VERLEGT` und `OCCUPANCY_GESCHLECHT_MISMATCH` schreiben rohe SQL-INSERTs ohne `actor_id`, `actor_role`, `location_id`; (3) `RESERVATION_CREATED` speichert nur `reservation_id` + `azr_id` — ohne Requester, Ziel, Person und Zeitraum; (4) die Detailspalte zeigt abgeschnittenes rohes JSON — für Gerichtsverfahren unlesbar.

**Approach:** Backend um `grund`-Body im Reject-Endpoint erweitern und alle rohen INSERTs auf `write_audit()` umstellen. Frontend: Ablehnungsgrund im Reject-Call mitsenden; Audit-Log-Seite erhält klare Übersichtszeile + Detaildialog per Klick mit strukturierten, beschrifteten Feldern.

## Boundaries & Constraints

**Always:**
- `audit.events` bleibt append-only — kein UPDATE außer DSGVO-Löschung
- `write_audit()` ist die einzige Schreibstelle — kein weiterer roher INSERT in Produktionscode
- Alle `write_audit()`-Calls laufen in derselben DB-Session/Transaktion wie die auslösende Mutation
- Neue Backend-Felder nullable — Rückwärtskompatibilität zu bestehenden Einträgen ohne Begründung

**Ask First:**
- Soll die UI in `Reservations.tsx` beim Ablehnen ebenfalls einen Begründungs-Dialog erhalten (aktuell direkter Klick ohne Textfeld)?

**Never:**
- Keine READ-Events (GET, LIST) ins Audit-Log aufnehmen
- `actor_username` weiterhin nur im Payload — nicht als eigene DB-Spalte
- Keine Breaking Changes am GET `/api/audit`-Response-Schema

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output | Error Handling |
|---|---|---|---|
| Ablehnen mit Begründung | POST /reject `{"grund":"Keine freien Plätze"}` | RESERVATION_REJECTED payload enthält `ablehnungsgrund` | grund leer → 422 |
| Ablehnen ohne Begründung (legacy) | POST /reject `{}` | RESERVATION_REJECTED ohne `ablehnungsgrund` — kein Fehler | — |
| Internes Verlegen | POST /beds/{id}/occupancy mit `verlegung_grund` | OCCUPANCY_CREATED + OCCUPANCY_VERLEGT je mit actor_id, actor_role, location_id | — |
| Klick auf Log-Eintrag | Klick auf Tabellenzeile | Dialog mit allen Feldern strukturiert beschriftet | — |

</frozen-after-approval>

## Code Map

- `backend/src/api/reservations/schemas.py` — RejectBody Schema ergänzen: `grund: Optional[str] = None`
- `backend/src/api/reservations/router.py` — `reject_reservation` nimmt `body: RejectBody = Body(default_factory=RejectBody)`; `grund` weiterreichen
- `backend/src/adapters/db/reservation_repo.py` — `reject()` + `update_status("REJECTED")` akzeptiert `ablehnungsgrund: Optional[str]`; in `_create_task_and_audit()` als `extra_payload` übergeben
- `backend/src/api/capacity/router.py` — rohe INSERTs für OCCUPANCY_VERLEGT und OCCUPANCY_GESCHLECHT_MISMATCH durch `write_audit()`-Calls ersetzen (mit `user`, `location_id`, `entity_type="OCCUPANCY"`, `entity_id=body.azr_id`)
- `backend/src/adapters/db/reservation_repo.py` — RESERVATION_CREATED Payload anreichern: `requester_location_id`, `target_location_id`, `belegung_start`, `belegung_ende`, `geschlecht`, `geburtsjahr`, `herkunftsland`
- `frontend/src/pages/TaskInbox.tsx` — `handleReject(resId, reason)`: `reason` statt `_reason`; POST body `{"grund": reason}`
- `frontend/src/pages/AuditLog.tsx` — Tabellenzeile klickbar; Details-Spalte entfernen; stattdessen `<DetailDialog>`; pro Eintrag strukturierte Label-Wert-Paare (dt. Bezeichner)

## Tasks & Acceptance

**Execution:**

- [x] `backend/src/api/reservations/schemas.py` — `class RejectBody(BaseModel): grund: Optional[str] = None` ergänzen
- [x] `backend/src/api/reservations/router.py` — `reject_reservation` Signatur: `body: RejectBody = Body(default_factory=RejectBody)`; `grund=body.grund` an `repo.reject()` weiterreichen; `update_status("REJECTED", ..., ablehnungsgrund=body.grund)` für system-admin-Pfad
- [x] `backend/src/adapters/db/reservation_repo.py` — `reject(self, ..., ablehnungsgrund=None)` + `update_status(..., ablehnungsgrund=None)`: `extra_payload={"ablehnungsgrund": ablehnungsgrund}` wenn gesetzt; RESERVATION_CREATED `_write_audit`-Call: Payload um `requester_location_id`, `target_location_id`, `belegung_start`, `belegung_ende`, `geschlecht`, `geburtsjahr`, `herkunftsland` aus `model` erweitern
- [x] `backend/src/api/capacity/router.py` — Beiden rohen `session.execute(INSERT INTO audit.events ...)` ersetzen: OCCUPANCY_VERLEGT → `await write_audit(session, "OCCUPANCY_VERLEGT", {...}, user=user, location_id=bed_location_id, entity_type="OCCUPANCY", entity_id=body.azr_id)`; analog für OCCUPANCY_GESCHLECHT_MISMATCH; Import `write_audit` oben ergänzen falls fehlend
- [x] `frontend/src/pages/TaskInbox.tsx` — `handleReject(resId: string, reason: string)`: `_reason` → `reason`; POST `/api/reservations/${resId}/reject` mit body `{grund: reason}` statt `{}`
- [x] `frontend/src/pages/AuditLog.tsx` — (a) State `selectedEntry: AuditEntry | null`; (b) Tabellenzeile bekommt `onClick={() => setSelectedEntry(row)}`; (c) Details-Spalte aus Tabelle entfernen, stattdessen Pfeil-Icon als letztes Element; (d) `<DetailDialog>` (MUI Dialog maxWidth="md") zeigt alle Felder strukturiert: Zeitpunkt, Event-Typ, Nutzer, Rolle, Einrichtungs-ID, AZR/Entity, alle Payload-Felder mit deutschen Bezeichnern; (e) Payload-Keys mit Mapping `LABEL_MAP` übersetzen (z.B. `ablehnungsgrund` → "Ablehnungsgrund", `verlegung_grund` → "Verlegungsgrund", `geschlecht_mismatch_grund` → "Begründung Geschlecht-Abweichung", `belegung_start/ende` → "Von/Bis")

**Acceptance Criteria:**
- Given Zieleinrichtung lehnt mit Grund "Keine Kapazität" ab, when POST /reject `{"grund":"Keine Kapazität"}`, then enthält der RESERVATION_REJECTED-Audit-Eintrag `ablehnungsgrund: "Keine Kapazität"`
- Given internes Verlegen mit `verlegung_grund`, when OCCUPANCY_VERLEGT-Eintrag, then sind `actor_id`, `actor_role`, `location_id` gesetzt (nicht null)
- Given Nutzer klickt auf eine Audit-Zeile, when Dialog öffnet, then sind alle Payload-Felder mit deutschen Bezeichnern sichtbar, kein rohes JSON
- Given RESERVATION_CREATED-Eintrag, when Detail-Dialog, then enthält Payload `requester_location_id`, `target_location_id`, `belegung_start`, `belegung_ende`, `geschlecht`

## Design Notes

**LABEL_MAP in AuditLog.tsx** (Auswahl):
```typescript
const LABEL_MAP: Record<string, string> = {
  ablehnungsgrund: 'Ablehnungsgrund',
  verlegung_grund: 'Verlegungsgrund',
  geschlecht_mismatch_grund: 'Begründung Geschlecht-Abweichung',
  belegung_start: 'Belegung von',
  belegung_ende: 'Belegung bis',
  requester_location_id: 'Anfragende Einrichtung (ID)',
  target_location_id: 'Zieleinrichtung (ID)',
  reservation_id: 'Reservierungs-ID',
  erstellt_von: 'Erstellt von (Keycloak-Sub)',
  actor_username: 'Nutzername',
}
```

**reject_reservation Signatur:**
```python
async def reject_reservation(
    reservation_id: UUID,
    body: RejectBody = Body(default_factory=RejectBody),
    request: Request = ...,
    ...
)
```
`Body(default_factory=RejectBody)` erlaubt leeren Body ohne 422.

## Verification

**Commands:**
- `cd /Users/A3694852/KapzitaetsPlanungsTool/frontend && npx tsc --noEmit` — expected: 0 errors
- `cd /Users/A3694852/KapzitaetsPlanungsTool && make build` — expected: Frontend-Image baut ohne Fehler

**Manual checks:**
- Ablehnen mit Begründung → Protokoll → RESERVATION_REJECTED-Detail-Dialog zeigt "Ablehnungsgrund: ..."
- Internes Verlegen → OCCUPANCY_VERLEGT-Eintrag im Protokoll hat Nutzer/Rolle gesetzt (nicht "–")
- Klick auf beliebigen Eintrag → Dialog mit deutschen Bezeichnern, kein `{...}` JSON-Blob
