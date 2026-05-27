---
title: 'Ziel 9d — HF-22: Notbett-Verlängerung (einmalig +1 Tag)'
type: 'feature'
created: '2026-05-27'
status: 'done'
baseline_commit: 'NO_VCS'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Notbett-Belegungen sind auf max. 1 Tag begrenzt (check_notbett_duration, bereits implementiert). Laut HF-22 soll eine Einrichtung eine laufende Notbett-Belegung einmalig um 1 Tag verlängern können — bisher kein Endpoint und kein UI.

**Approach:** (1) DB-Migration: `extended_once BOOLEAN NOT NULL DEFAULT FALSE` in `persons.occupants`. (2) Backend: `POST /occupants/{id}/extend` — prüft Notbett-Typ und `extended_once=False`, verlängert `belegung_ende +1 Tag`, setzt `extended_once=True`. (3) Backend: Bed-Status-Query gibt `extended_once` mit. (4) Frontend Drilldown: "+1 Tag"-Button unter belegtem Notbett wenn noch nicht verlängert.

## Boundaries & Constraints

**Always:**
- B-01: Verlängerung nur möglich wenn `extended_once = False` → sonst HTTP 409 `"Notbett-Verlängerung wurde bereits einmal gewährt"`.
- B-01: Verlängerung nur für Betten mit `bett_typ = 'NOTBETT'` → sonst HTTP 422 `"Nur Notbetten können verlängert werden"`.
- B-01: Endpoint: `POST /api/occupants/{occupancy_id}/extend`; kein Request-Body; Response: `{"belegung_ende": "YYYY-MM-DD", "extended_once": true}`.
- B-02: BedStatusItem (`schemas.py`) bekommt `extended_once: bool = False`; SQL-Query ergänzt `o.extended_once`.
- B-03: Frontend-Button "+1 Tag" erscheint nur wenn `bed.is_notbett && bed.status === 'BELEGT' && !bed.extended_once`. Nach Klick: `loadBedStatus()` (Server-as-source-of-truth).
- Kein Audit-Log-Eintrag in dieser Iteration (Postkorb-Task besteht bereits via jobs.py).
- `canEdit`-Guard gilt auch für den Verlängerungs-Button.

**Never:**
- Keine zweite Verlängerung — auch kein Admin-Override.
- Kein neuer Dialog — Button direkt, kein Bestätigungs-Popup.
- Kein Umbau der bestehenden Notbett-Belegungs-UI.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Erste Verlängerung | `extended_once=False`, Bett ist NOTBETT | `belegung_ende += 1 Tag`, `extended_once=True`, HTTP 200 | — |
| Zweite Verlängerung | `extended_once=True` | HTTP 409 "Notbett-Verlängerung wurde bereits einmal gewährt" | — |
| Kein Notbett | Occupancy auf KONTINGENT-Bett | HTTP 422 "Nur Notbetten können verlängert werden" | — |
| Occupancy nicht gefunden | Ungültige UUID | HTTP 404 "Belegung nicht gefunden" | — |
| Frontend: Button sichtbar | `is_notbett=true, status=BELEGT, extended_once=false` | "+1 Tag"-Button sichtbar | — |
| Frontend: Button ausgeblendet | Nach Verlängerung (`extended_once=true`) | Kein Button; Tooltip zeigt verlängertes Datum | — |

</frozen-after-approval>

## Code Map

- `backend/alembic/versions/0009_notbett_extension.py` — Migration: `extended_once` Spalte
- `backend/src/adapters/db/models.py` — `OccupantModel`: `extended_once` Feld
- `backend/src/api/capacity/schemas.py` — `BedStatusItem`: `extended_once: bool = False`
- `backend/src/api/capacity/router.py` — Bed-Status-SQL (~430): `o.extended_once` ergänzen; Mapping (~481); neuer Endpoint `POST /occupants/{id}/extend`
- `frontend/src/pages/Drilldown.tsx` — `BedStatus` Interface + Notbett-UI: "+1 Tag"-Button

## Tasks & Acceptance

**Execution:**

- [x] `backend/alembic/versions/0009_notbett_extension.py` — Neue Migration erstellen:
  ```python
  revision = "0009"
  down_revision = "0008"
  branch_labels = None
  depends_on = None

  def upgrade() -> None:
      op.execute(
          "ALTER TABLE persons.occupants ADD COLUMN IF NOT EXISTS "
          "extended_once BOOLEAN NOT NULL DEFAULT FALSE"
      )

  def downgrade() -> None:
      op.execute("ALTER TABLE persons.occupants DROP COLUMN IF EXISTS extended_once")
  ```

- [x] `backend/src/adapters/db/models.py` — In `OccupantModel` (nach `labels`-Feld) ergänzen:
  ```python
  extended_once: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
  ```
  `Boolean` ist bereits via SQLAlchemy importiert (prüfen, ggf. ergänzen).

- [x] `backend/src/api/capacity/schemas.py` — In `BedStatusItem` (nach `is_notbett: bool = False`) ergänzen:
  ```python
  extended_once: bool = False
  ```

- [x] `backend/src/api/capacity/router.py` — Bed-Status-SQL (Zeile ~445, nach `o.labels AS occ_labels`): `o.extended_once,` ergänzen. Im BedStatusItem-Mapping (~Zeile 497, nach `is_notbett=...`) ergänzen: `extended_once=bool(row.get("extended_once") or False),`.

- [x] `backend/src/api/capacity/router.py` — Neuen Endpoint direkt nach `create_occupancy` (nach Zeile ~1010) einfügen:
  ```python
  @router.post("/occupants/{occupancy_id}/extend", status_code=200)
  async def extend_notbett_occupancy(
      occupancy_id: UUID,
      session: AsyncSession = Depends(get_session),
      _: UserContext = Depends(get_current_user),
  ):
      """Verlängert eine Notbett-Belegung einmalig um 1 Tag."""
      result = await session.execute(
          text("""
              SELECT o.id, o.belegung_ende, o.extended_once, b.bett_typ
              FROM persons.occupants o
              JOIN capacity.beds b ON b.id = o.bed_id
              WHERE o.id = :occ_id
          """),
          {"occ_id": str(occupancy_id)},
      )
      row = result.fetchone()
      if not row:
          raise HTTPException(status_code=404, detail="Belegung nicht gefunden")
      if row.bett_typ != "NOTBETT":
          raise HTTPException(status_code=422, detail="Nur Notbetten können verlängert werden")
      if row.extended_once:
          raise HTTPException(status_code=409, detail="Notbett-Verlängerung wurde bereits einmal gewährt")
      new_ende = row.belegung_ende + timedelta(days=1)
      await session.execute(
          text("""
              UPDATE persons.occupants
              SET belegung_ende = :new_ende, extended_once = TRUE
              WHERE id = :occ_id
          """),
          {"new_ende": new_ende, "occ_id": str(occupancy_id)},
      )
      await session.commit()
      return {"belegung_ende": str(new_ende), "extended_once": True}
  ```
  Import `timedelta` aus `datetime` prüfen und ggf. ergänzen.

- [x] `frontend/src/pages/Drilldown.tsx` — In `BedStatus` Interface (nach `is_notbett?: boolean`) ergänzen: `extended_once?: boolean`. Neue Handler-Funktion nach `handleDeactivateBed`:
  ```typescript
  async function handleExtendNotbett(occupancyId: string) {
    try {
      await post(`/api/occupants/${occupancyId}/extend`, {})
      loadBedStatus()
      setSnackbar({ open: true, message: 'Notbett um 1 Tag verlängert.', severity: 'success' })
    } catch (err: unknown) {
      setSnackbar({ open: true, message: extractApiError(err), severity: 'error' })
    }
  }
  ```
  Im Notbett-Bed-Rendering (Zeile ~847): Das existierende `<Tooltip>...<Box>...</Box></Tooltip>`-Element in ein äußeres `<Box display="flex" flexDirection="column" alignItems="center" gap={0.5}>` einwickeln und danach "+1 Tag"-Button ergänzen:
  ```typescript
  <Box key={bed.bed_id} display="flex" flexDirection="column" alignItems="center" gap={0.5}>
    <Tooltip ...>
      <Box ...>...</Box>  {/* unverändert */}
    </Tooltip>
    {canEdit && isBelegt && !bed.extended_once && bed.occupancy_id && (
      <Button size="small" variant="outlined" color="warning"
        sx={{ fontSize: 9, px: 0.5, py: 0.2, minWidth: 0 }}
        onClick={() => handleExtendNotbett(bed.occupancy_id!)}>
        +1 Tag
      </Button>
    )}
  </Box>
  ```

**Acceptance Criteria:**
- Given Notbett mit laufender Belegung (`extended_once=false`), when `POST /api/occupants/{id}/extend`, then HTTP 200, `belegung_ende += 1 Tag`, `extended_once=true`
- Given gleicher Endpoint erneut aufgerufen, then HTTP 409 "Notbett-Verlängerung wurde bereits einmal gewährt"
- Given Kontingent-Bett-Belegung, when extend aufgerufen, then HTTP 422
- Given Notbett belegt und nicht verlängert, when Drilldown geöffnet, then "+1 Tag"-Button sichtbar
- Given "+1 Tag" geklickt, when Erfolgsmeldung, then Drilldown-Bett zeigt neues Datum, Button verschwunden

## Design Notes

**`post({})` statt Body-Parameter:** `patch`/`post` in client.ts erfordern Body; leeres Objekt ist safe für FastAPI-Endpoints ohne Body-Modell.

**`session.commit()` explizit:** Andere Endpoints in diesem Router nutzen `session`-Autocommit via `get_session`-Dependency — konsistent halten: kein explizites Commit nötig wenn `get_session` autocommit hat. Prüfen was `get_session` macht; falls Autocommit → `await session.commit()` weglassen.

**`timedelta` Import:** In `capacity/router.py` prüfen ob `from datetime import timedelta` bereits vorhanden. Wenn nicht: `from datetime import date, timedelta` (beide ersetzen den bisherigen `date`-Import).

## Verification

**Commands:**
- `cd frontend && npm run build` — kein TypeScript-Fehler
- `cd backend && python3 -c "import ast; ast.parse(open('src/api/capacity/router.py').read()); print('OK')"` — kein Syntaxfehler

**Manual checks (nach DB-Migration + Restart):**
- Notbett belegen → "+1 Tag"-Button im Drilldown sichtbar → klicken → Datum +1 Tag, Button weg
- "+1 Tag" ein zweites Mal versuchen → Snackbar-Fehler "bereits gewährt"
