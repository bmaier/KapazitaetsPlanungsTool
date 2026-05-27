---
title: 'Ziel 9b — HF-18 Deaktivierungsschutz (Raum) + HF-19 Kontingentschutz (Verify)'
type: 'feature'
created: '2026-05-27'
status: 'done'
baseline_commit: 'NO_VCS'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Räume können per `DELETE /rooms/{id}` deaktiviert werden, ohne dass aktive Belegungen in ihren Betten geprüft werden — führt zu inkonsistenten Daten. Frontend zeigt bei 409-Fehlern nur eine generische Meldung. (HF-19 Kontingentschutz ist bereits im Backend implementiert und per `saveEdit` korrekt angezeigt — nur verifizieren.)

**Approach:** (1) Backend: `deactivate_room` prüft vor Soft-Delete via SQL ob aktive Occupants in Raum-Betten vorhanden sind → 409 mit Anzahl. (2) Frontend `handleDeactivateRoom` extrahiert 409-Detail analog zu `handleDeaktiviereBedTimed` (detail.detail-Muster). HF-19: kein Code-Change — nur Acceptance-Test.

## Boundaries & Constraints

**Always:**
- B-01: `DELETE /rooms/{room_id}` prüft `belegung_ende >= CURRENT_DATE` (aktive + zukünftige) — identisches Kriterium wie `POST /locations/{id}/deactivate`.
- B-01: 409-Detail: `"Raum hat noch {cnt} aktive Belegung(en). Erst umbuchen, dann deaktivieren."`.
- B-02: Frontend nutzt `extractApiError` aus `client.ts` für die Fehlermeldung in `handleDeactivateRoom`.
- B-02: Fehler wird als Snackbar angezeigt (kein Dialog, kein Confirm — bestehender Snackbar-Mechanismus).
- `DELETE /locations/{id}` wird nicht angefasst — Frontend nutzt ausschließlich `POST /locations/{id}/deactivate` (bereits geschützt).
- `DELETE /beds/{id}` wird nicht angefasst — separater Flow (timed deactivation) bereits mit 409 versehen.

**Never:**
- Kein neuer Bestätigungs-Dialog für Raum-Deaktivierung.
- Keine Änderungen am Raum-Reaktivierungs-Flow.
- Kein Umbau der Snackbar-Infrastruktur.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Raum mit aktiven Belegungen deaktivieren | `DELETE /rooms/{id}`, Raum hat ≥1 Occupant mit `belegung_ende >= CURRENT_DATE` | HTTP 409 `"Raum hat noch X aktive Belegung(en). Erst umbuchen, dann deaktivieren."` | — |
| Raum ohne Belegungen deaktivieren | `DELETE /rooms/{id}`, keine aktiven Occupants | HTTP 200 `{"deactivated": true}`, Frontend zeigt Erfolgs-Snackbar | — |
| Raum nicht gefunden | `DELETE /rooms/{unknown-uuid}` | HTTP 404 (unverändert) | — |
| Frontend: 409 empfangen | `handleDeactivateRoom` fängt Fehler | Snackbar zeigt Backend-Detailtext statt "Raum deaktivieren fehlgeschlagen." | — |
| Kontingent unter Belegung senken | `PATCH /locations/{id}` mit `kontingent < aktuelle_belegung` | HTTP 409 `"Aktuelle Belegung (X Plätze) übersteigt das neue Kontingent (Y)..."`, Snackbar zeigt es | bereits implementiert ✅ |

</frozen-after-approval>

## Code Map

- `backend/src/api/capacity/router.py` — `deactivate_room` (Zeile ~696): Occupancy-Check vor `repo.deactivate()`
- `frontend/src/pages/Drilldown.tsx` — `handleDeactivateRoom` (Zeile ~527): Catch-Block mit `extractApiError`

## Tasks & Acceptance

**Execution:**

- [x] `backend/src/api/capacity/router.py` — In `deactivate_room` (nach `if not room: raise 404`): SQL-Check einfügen:
  ```python
  result = await session.execute(
      text("""
          SELECT COUNT(*) AS cnt
          FROM persons.occupants o
          JOIN capacity.beds b ON b.id = o.bed_id
          WHERE b.room_id = :room_id
            AND o.belegung_ende >= CURRENT_DATE
      """),
      {"room_id": str(room_id)},
  )
  row = result.fetchone()
  if row and row.cnt > 0:
      raise HTTPException(
          status_code=409,
          detail=f"Raum hat noch {row.cnt} aktive Belegung(en). Erst umbuchen, dann deaktivieren.",
      )
  ```
  Danach unverändert: `await repo.deactivate(room_id)`.

- [x] `frontend/src/pages/Drilldown.tsx` — `handleDeactivateRoom` (Zeile ~527): Import `extractApiError` bereits vorhanden (aus `../api/client`). Catch-Block ersetzen:
  ```typescript
  // VORHER:
  } catch {
    setSnackbar({ open: true, message: 'Raum deaktivieren fehlgeschlagen.', severity: 'error' })
  }
  // NACHHER:
  } catch (err: unknown) {
    const msg = extractApiError(err)
    setSnackbar({ open: true, message: msg, severity: 'error' })
  }
  ```

**Acceptance Criteria:**
- Given Raum mit 2 aktiven Belegungen, when `DELETE /rooms/{id}`, then HTTP 409 "Raum hat noch 2 aktive Belegung(en). Erst umbuchen, dann deaktivieren."
- Given leerer Raum (keine aktiven Belegungen), when `DELETE /rooms/{id}`, then HTTP 200, Frontend-Snackbar "Raum deaktiviert"
- Given 409 vom Backend bei Raum-Deaktivierung, when Frontend `handleDeactivateRoom` fängt Fehler, then Snackbar zeigt "Raum hat noch X aktive Belegung(en)..." statt Fallback
- Given Kontingent 10, aktuelle Belegung 8, when `PATCH /locations/{id}` mit `kontingent: 5`, then HTTP 409, Snackbar zeigt "Aktuelle Belegung (8 Plätze) übersteigt das neue Kontingent (5)" [HF-19 — bereits implementiert, manuelle Verifikation]

## Design Notes

**Analogie zu Location-Safe-Deactivate:** Identisches SQL-Muster wie `POST /locations/{id}/deactivate` (Zeile 582), nur mit `b.room_id` statt `r.location_id`-Join-Kette. Konsistenz über alle Ebenen (Location → Room → Bed mit timed-deactivate).

**`extractApiError` statt Inline-Cast:** `handleDeaktiviereBedTimed` nutzt noch den alten inline `(err as {detail?: {detail?: string}}).detail?.detail`-Cast. `handleDeactivateRoom` nutzt die neue Utility — kein Refactor des alten Handlers nötig.

**`DELETE /locations/{id}` ungeschützt:** Endpoint existiert aber ist im Frontend nicht referenziert. Kein Fix nötig — noted in `deferred-work.md`.

## Verification

**Commands:**
- `cd backend && python -c "from src.api.capacity.router import deactivate_room; print('OK')"` — kein ImportError
- `cd frontend && npm run build` — kein TypeScript-Fehler

**Manual checks:**
- Raum mit aktiver Belegung → "Raum deaktivieren"-Button → Snackbar mit Belegungs-Hinweis
- Leerer Raum → "Raum deaktivieren"-Button → Raum verschwindet aus Verwaltungsliste
- Kontingent-Feld auf Wert unter aktueller Belegung setzen → Speichern → Snackbar mit 409-Text
