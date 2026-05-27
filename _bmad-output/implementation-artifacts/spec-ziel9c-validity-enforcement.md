---
title: 'Ziel 9c — HF-17: Gültigkeitszeitraum-Enforcement für Einrichtungen'
type: 'feature'
created: '2026-05-27'
status: 'done'
baseline_commit: 'NO_VCS'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Einrichtungen haben `valid_from`/`valid_until`-Felder (gespeichert und bearbeitbar), die bei der Belegungs- und Reservierungserstellung nicht geprüft werden. Dadurch sind Buchungen außerhalb des operativen Fensters möglich. Das Dashboard zeigt kein Ablauf-Warnsignal wenn `valid_until` naht.

**Approach:** (1) Backend: `create_occupancy` und `create_reservation` prüfen die Gültigkeit der Zieleinrichtung für `belegung_start` → HTTP 409. (2) Backend: `GET /locations/summary` gibt `valid_from`/`valid_until` mit. (3) Frontend Dashboard: Warnanzeige wenn `valid_until` innerhalb von 30 Tagen.

## Boundaries & Constraints

**Always:**
- B-01: Prüfung auf `belegung_start` (nicht `belegung_ende`) — der Beginn der Belegung muss im Gültigkeitsfenster liegen.
- B-01: `valid_from` und `valid_until` sind optional (NULL = unbefristet); kein Fehler wenn beide NULL.
- B-01: Fehlermeldungen: `valid_from`-Verstoß → `"Einrichtung ist erst ab {date} aktiv"`, `valid_until`-Verstoß → `"Einrichtung ist ab {date} inaktiv"`.
- B-02: Bei Reservierungen wird die **Ziel-Einrichtung** (`target_location_id`) geprüft, nicht die anfragende.
- B-03: Dashboard-Warnung: Chip/Indikator am Einrichtungs-Card wenn `valid_until` ≤ today + 30 Tage (und `valid_until` > today). Einrichtungen die bereits abgelaufen sind (`valid_until` ≤ today) werden durch `is_active=false` bereits gefiltert.
- Kein neuer Endpoint; kein Umbau bestehender Endpoints außer den benannten.

**Never:**
- Keine Änderung am `valid_from`/`valid_until`-Edit-Flow (Drilldown.tsx `saveEdit`).
- Kein Bestätigungs-Dialog für die Validity-Warnung im Dashboard.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Belegung vor `valid_from` | `belegung_start < loc.valid_from` | HTTP 409 "Einrichtung ist erst ab {valid_from} aktiv" | — |
| Belegung nach `valid_until` | `belegung_start >= loc.valid_until` | HTTP 409 "Einrichtung ist ab {valid_until} inaktiv" | — |
| Belegung im gültigen Fenster | `valid_from <= belegung_start < valid_until` | Belegung wird normal angelegt | — |
| Keine Validity-Felder gesetzt | NULL/NULL | Keine Prüfung, Belegung wird angelegt | — |
| Reservierung: Ziel außerhalb Fenster | `body.target_location_id` → `valid_until` überschritten | HTTP 409 "Einrichtung ist ab {valid_until} inaktiv" | — |
| Dashboard: valid_until in 15 Tagen | `valid_until = today + 15` | Chip "Endet in 15 Tagen" (Warnfarbe orange) auf Location-Card | — |
| Dashboard: valid_until in 35 Tagen | `valid_until = today + 35` | Kein Warnindikator | — |

</frozen-after-approval>

## Code Map

- `backend/src/api/capacity/schemas.py` — `LocationSummaryResponse`: `valid_from`/`valid_until` ergänzen
- `backend/src/api/capacity/router.py` — `get_locations_summary` (~230): SELECT und Mapping erweitern
- `backend/src/api/capacity/router.py` — `create_occupancy` (~949): Validity-Check nach bed-Fetch
- `backend/src/api/reservations/router.py` — `create_reservation` (~64): Validity-Check für Ziel-Einrichtung
- `frontend/src/pages/Dashboard.tsx` — `LocationSummary` Interface + Card-Rendering: Warnindikator

## Tasks & Acceptance

**Execution:**

- [x] `backend/src/api/capacity/schemas.py` — In `LocationSummaryResponse` (nach `lon: Optional[float] = None`) ergänzen:
  ```python
  valid_from: Optional[date] = None
  valid_until: Optional[date] = None
  ```
  Import `date` aus `datetime` ist in der Datei bereits vorhanden (prüfen, ggf. ergänzen).

- [x] `backend/src/api/capacity/router.py` — `get_locations_summary` (~Zeile 240): `l.valid_from, l.valid_until` in SELECT ergänzen (nach `l.lon`). In der GROUP BY-Klausel ebenfalls ergänzen. Im `LocationSummaryResponse(...)`-Mapping (Zeile ~272) `valid_from=row["valid_from"], valid_until=row["valid_until"]` ergänzen.

- [x] `backend/src/api/capacity/router.py` — `create_occupancy` (~Zeile 966, nach `if not bed or not bed.is_active`): Validity-Check für Einrichtung des Betts einfügen:
  ```python
  loc_validity = await session.execute(
      text("""
          SELECT l.valid_from, l.valid_until
          FROM capacity.rooms r
          JOIN capacity.locations l ON l.id = r.location_id
          WHERE r.id = :room_id
      """),
      {"room_id": str(bed.room_id)},
  )
  loc_row = loc_validity.fetchone()
  if loc_row:
      if loc_row.valid_from and body.belegung_start < loc_row.valid_from:
          raise HTTPException(status_code=409, detail=f"Einrichtung ist erst ab {loc_row.valid_from} aktiv")
      if loc_row.valid_until and body.belegung_start >= loc_row.valid_until:
          raise HTTPException(status_code=409, detail=f"Einrichtung ist ab {loc_row.valid_until} inaktiv")
  ```

- [x] `backend/src/api/reservations/router.py` — `create_reservation` (~Zeile 76, nach dem `target == requester`-Check): Validity-Check für Ziel-Einrichtung einfügen:
  ```python
  target_loc_row = await session.execute(
      text("SELECT valid_from, valid_until FROM capacity.locations WHERE id = :id"),
      {"id": str(body.target_location_id)},
  )
  target_row = target_loc_row.fetchone()
  if target_row:
      if target_row.valid_from and body.belegung_start < target_row.valid_from:
          raise HTTPException(status_code=409, detail=f"Einrichtung ist erst ab {target_row.valid_from} aktiv")
      if target_row.valid_until and body.belegung_start >= target_row.valid_until:
          raise HTTPException(status_code=409, detail=f"Einrichtung ist ab {target_row.valid_until} inaktiv")
  ```
  Prüfen ob `session` in `create_reservation` verfügbar ist (kommt via `_get_session` — ja, vorhanden).

- [x] `frontend/src/pages/Dashboard.tsx` — `LocationSummary` Interface (Zeile ~37): `valid_from?: string | null` und `valid_until?: string | null` ergänzen. Im Card-Rendering: vor oder nach dem Ampel-Chip einen Ablauf-Chip einfügen:
  ```typescript
  {(() => {
    if (!loc.valid_until) return null
    const days = Math.ceil(
      (new Date(loc.valid_until).getTime() - Date.now()) / (1000 * 60 * 60 * 24)
    )
    if (days > 0 && days <= 30) {
      return (
        <Chip
          label={`Endet in ${days} Tag${days === 1 ? '' : 'en'}`}
          size="small"
          sx={{ bgcolor: '#fff3e0', color: '#e65100', fontWeight: 600 }}
        />
      )
    }
    return null
  })()}
  ```

**Acceptance Criteria:**
- Given Einrichtung mit `valid_from = 2026-06-01`, when Belegung mit `belegung_start = 2026-05-28`, then HTTP 409 "Einrichtung ist erst ab 2026-06-01 aktiv"
- Given Einrichtung mit `valid_until = 2026-05-01`, when Belegung mit `belegung_start = 2026-05-28`, then HTTP 409 "Einrichtung ist ab 2026-05-01 inaktiv"
- Given Einrichtung ohne Validity-Felder, when Belegung wird angelegt, then kein 409 — Belegung normal möglich
- Given Reservierung auf Ziel-Einrichtung außerhalb Validity-Fenster, when `POST /api/reservations`, then HTTP 409 mit Validity-Meldung
- Given Einrichtung mit `valid_until` in 20 Tagen, when Dashboard geladen, then Chip "Endet in 20 Tagen" auf der Einrichtungs-Karte sichtbar
- Given Einrichtung mit `valid_until` in 45 Tagen, when Dashboard geladen, then kein Ablauf-Chip

## Design Notes

**Warum `belegung_start` und nicht `belegung_ende`:** Der Beginn bestimmt den Eintritt. Eine laufende Belegung die über `valid_until` hinausgeht ist ein operativer Sonderfall (kein Fehler beim Anlegen, aber Postkorb-Job kann später warnen).

**`valid_until` in Summary statt nur Drilldown:** Dashboard hat keinen Zugriff auf die Detailfelder — `GET /locations/summary` ist der einzige Dashboard-Aufruf. Beide Felder kosten einen minimalen Schema-Overhead.

**Reservierungen: nur Zieleinrichtung:** Die anfragende Einrichtung ist bereits an den Benutzer-JWT gebunden und kann keine abgelaufene Einrichtung sein (wäre is_active=false). Nur die externe Zieleinrichtung kann ein Validity-Problem haben.

## Verification

**Commands:**
- `cd frontend && npm run build` — kein TypeScript-Fehler
- `cd backend && python3 -c "from src.api.capacity.schemas import LocationSummaryResponse; r = LocationSummaryResponse(id='00000000-0000-0000-0000-000000000000', name='x', kontingent=0, notbett_kapazitaet=0, belegt=0, belegungsgrad_pct=0.0, is_active=True); print(r.valid_until)"` — erwartet: None

**Manual checks:**
- Einrichtung mit `gültig bis` = morgen setzen → Belegung mit heute anlegen → kein Fehler
- Einrichtung mit `gültig bis` = gestern setzen (manuell in DB) → Belegung anlegen → 409
- Dashboard → Einrichtung mit ablaufendem Gültigkeitszeitraum → Chip sichtbar
