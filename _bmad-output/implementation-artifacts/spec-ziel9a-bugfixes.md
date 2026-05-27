---
title: 'Ziel 9a — Bug-Fixes: SuggestionWizard / Labels / Fehleranzeige'
type: 'bugfix'
created: '2026-05-27'
status: 'done'
baseline_commit: 'NO_VCS'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Drei Bugs beeinträchtigen den Kernworkflow: (1) SuggestionWizard schlägt fehl wenn `X-Location-Id`-Header fehlt (422), (2) Belegungs-Labels verschwinden nach erneutem Öffnen des Drilldown-Dialogs, (3) ReservationCreateDialog zeigt "Unbekannter Fehler" statt der tatsächlichen Fehlermeldung.

**Approach:** (1) Backend: `get_location_context` macht `x_location_id` optional und liest JWT-Claim als Fallback. (2) Frontend Drilldown.tsx: Nach PATCH auf Labels `loadBedStatus()` aufrufen statt lokalem State-Update. (3) Frontend: Robuste `extractApiError`-Utility in `client.ts`, `ReservationCreateDialog` nutzt sie.

## Boundaries & Constraints

**Always:**
- F-01: `get_location_context` muss weiterhin den Header bevorzugen wenn vorhanden; JWT-Claim ist nur Fallback. 403 wenn weder Header noch JWT-Claim vorhanden oder Location nicht in DB.
- F-01: `UserContext` bekommt neues optionales Feld `location_id: Optional[str] = None`; `get_current_user` extrahiert es aus JWT-Payload.
- F-02: Kein SSE-seitiger Fix — nur `loadBedStatus()` in den `onSaved`-Callbacks für OCCUPANCY-Labels in Drilldown.tsx (Zeile ~1018 und ~952).
- F-03: `extractApiError` muss alle bekannten FastAPI-Muster abdecken: `{detail: string}`, `{detail: [{msg: string}]}`, `{detail: {detail: string}}`, rohe `Error.message` als letzter Fallback.
- Kein Refactoring über den Bug-Fix-Scope hinaus.

**Ask First:**
- Wenn F-01 dazu führt, dass system-admin (ohne Location-Binding) versehentlich eine Location bekommt — dann Prüfung überspringen und 403 werfen.

**Never:**
- Keine Änderung am Keycloak-Realm-Export.
- Keine neuen API-Endpoints.
- Kein Umbau des SSE-Polling-Mechanismus.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| F-01: Header gesetzt | `X-Location-Id: <valid-uuid>` im Header | Location aus DB geladen, Request verarbeitet | wie bisher |
| F-01: Header fehlt, JWT-Claim vorhanden | kein Header, JWT enthält `location_id` | Claim als UUID genutzt, Location aus DB geladen | 403 wenn Location nicht aktiv |
| F-01: Kein Header, kein Claim | system-admin ohne Location | 403 "Keine Einrichtung im Token oder Header" | — |
| F-02: Labels gespeichert | PATCH `/api/occupancy/{id}/labels` 200 | `loadBedStatus()` aufgerufen → Dialog zeigt neue Labels bei Wiederöffnen | — |
| F-03: Backend 422 string-detail | `{"detail": "EU-Quote überschritten"}` | Alert zeigt "EU-Quote überschritten" | — |
| F-03: Backend 422 array-detail | `{"detail": [{"msg": "field required"}]}` | Alert zeigt "field required" | — |
| F-03: Netzwerkfehler | fetch wirft Error ohne .detail | Alert zeigt `err.message` oder "Verbindungsfehler" | — |

</frozen-after-approval>

## Code Map

- `backend/src/adapters/keycloak/jwt.py` — `UserContext` Dataclass + `get_current_user` + `get_location_context`
- `frontend/src/pages/Drilldown.tsx` — Zeilen ~952 und ~1018: onSaved-Callbacks für Occupancy-Labels
- `frontend/src/api/client.ts` — Neue `extractApiError`-Utility
- `frontend/src/components/ReservationCreateDialog.tsx` — Error-Handling-Block (Zeilen ~101–116)

## Tasks & Acceptance

**Execution:**

- [x] `backend/src/adapters/keycloak/jwt.py` — In `UserContext` Dataclass `location_id: Optional[str] = None` ergänzen (Import `Optional` von `typing` bereits vorhanden). In `get_current_user`: nach `sub = payload.get("sub", "")` auch `loc_id = payload.get("location_id")` extrahieren und in `UserContext(sub=sub, roles=roles, location_id=loc_id)` übergeben. In `get_location_context`: Parameter auf `x_location_id: Optional[UUID] = Header(None)` ändern; neuen Parameter `user: UserContext = Depends(get_current_user)` ergänzen; Logik: wenn `x_location_id` vorhanden → nutzen; sonst wenn `user.location_id` vorhanden → `UUID(user.location_id)` nutzen; sonst `raise HTTPException(403, "Keine Einrichtung im Token oder Header")`.

- [x] `frontend/src/pages/Drilldown.tsx` — Zeile ~1018 (onSaved für Occupancy-Labels in manageBed-Dialog, existierende Belegung): lokalen State-Update entfernt, stattdessen `loadBedStatus()` aufgerufen: `onSaved={() => { loadBedStatus() }}`. Zeile ~952 (entityId="new") bleibt unverändert — LabelChips macht bei entityId="new" keinen API-Call, daher kein Re-Fetch nötig.

- [x] `frontend/src/api/client.ts` — Neue exportierte Funktion `extractApiError(err: unknown): string` am Ende der Datei ergänzen. Logik: `const detail = (err as {detail?: unknown})?.detail; if (typeof detail === 'string') return detail; const inner = (detail as {detail?: unknown})?.detail; if (typeof inner === 'string') return inner; if (Array.isArray(inner)) return inner.map((d: {msg: string}) => d.msg).join('; '); if (Array.isArray(detail)) return detail.map((d: {msg: string}) => d.msg).join('; '); return (err as Error)?.message ?? 'Unbekannter Fehler'`.

- [x] `frontend/src/components/ReservationCreateDialog.tsx` — Import `extractApiError` aus `'../api/client'` ergänzen. Catch-Block (Zeilen ~101–116) vereinfachen: `} catch (err: unknown) { setApiError(extractApiError(err)) } finally { setSubmitting(false) }`.

**Acceptance Criteria:**
- Given SB ohne `location_id`-Claim (system-admin), when `POST /api/suggestions`, then 403 "Keine Einrichtung im Token oder Header"
- Given SB mit `location_id`-Claim im JWT aber ohne Header, when SuggestionWizard abschickt, then Vorschlag wird normal berechnet (200)
- Given Occupancy-Labels in Drilldown gespeichert, when Dialog geschlossen und wieder geöffnet (nach SSE-Refresh), then Labels noch sichtbar
- Given Reservierungsanfrage schlägt fehl mit `{"detail": "Zieleinrichtung hat keine freien Plätze"}`, when Fehler angezeigt wird, then Alert enthält "Zieleinrichtung hat keine freien Plätze" statt "Unbekannter Fehler"
- Given Netzwerkfehler (fetch wirft), when Reservierung anlegen fehlschlägt, then Alert zeigt sinnvollen Fallback-Text

## Design Notes

**F-01 Fallback-Chain:** Header → JWT-Claim → 403. System-Admin (role `system-admin`) hat bewusst keine Location-Bindung; Fallback zu JWT verhindert, dass system-admin versehentlich zu einem zufälligen Location-Scope kommt — der hat keinen Claim, daher immer 403 auf Endpoints die Location erfordern.

**F-02 Re-fetch statt State-Merge:** Lokales State-Update war fragil gegenüber SSE-getriggertem loadBedStatus(). Re-fetch nach save() ist eine Server-as-source-of-truth-Garantie — einfacher und korrekter als optimistisches Update.

**F-03 `extractApiError`:** Zentrale Utility statt verschachtelter inline-Logik. Deckt alle bekannten FastAPI-Fehlermuster ab. Zukünftige Dialoge importieren diese Funktion.

## Verification

**Commands:**
- `cd backend && python -c "from src.adapters.keycloak.jwt import get_location_context, UserContext; print('OK')"` — erwartet: kein ImportError
- `cd frontend && npm run build` — erwartet: kein TypeScript-Fehler

**Manual checks:**
- Login als `sb_frankfurt` → SuggestionWizard öffnen → Suche starten → kein 422
- Occupancy-Label setzen → Dialog schließen → Dialog wieder öffnen → Label noch sichtbar
- Reservierungsanfrage mit ungültigem Datum erstellen → spezifische Fehlermeldung sichtbar
