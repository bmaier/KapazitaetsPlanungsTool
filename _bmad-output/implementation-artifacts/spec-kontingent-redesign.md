---
title: 'Kontingent-Redesign — Nationale Quote + Reporting'
type: 'feature'
created: '2026-06-05'
status: 'done'
baseline_commit: 'ec4046f'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Das `kontingent`-Feld pro Einrichtung ist aktuell von jedem Writer editierbar, obwohl es die EU-Quota-relevante Bettenzahl abbildet, die der system-admin national verteilt. Es gibt kein Reporting, das zeigt, ob die Einrichtungen ihre zugeteilten Kontingente mit regulären Betten abdecken — und wie die Summe aller Kontingente gegen die `eu_gesamtquote` steht.

**Approach:** (1) `PATCH /api/locations/{id}` gibt 403, wenn `kontingent` im Body steht und der Aufrufer kein `system-admin` ist. (2) Neuer Endpunkt `GET /api/system/kontingent-report` liefert eu_gesamtquote, Summen und pro Location: kontingent, reguläre Betten (bett_typ NOT IN ('NOTBETT','WARTEPLATZ'), is_active=true), Abweichung. (3) Dashboard zeigt ein Reporting-Panel nur für system-admin. (4) Drilldown: Kontingent-Feld im Edit-Dialog nur für system-admin editierbar (sonst disabled mit Hinweis).

## Boundaries & Constraints

**Always:**
- `kontingent`-Feld in `capacity.locations` bleibt erhalten — kein Schema-Change, kein Löschen.
- Reguläre Betten = `bett_typ NOT IN ('NOTBETT', 'WARTEPLATZ') AND is_active = true`. DOPPEL-Betten zählen mit.
- Abweichung pro Location = `kontingent − regulaere_betten` (negativ = Betten fehlen, positiv = Überschuss).
- Bestehende `check_eu_quota`-Logik beim Anlegen neuer Locations bleibt unverändert.
- `GET /api/system/kontingent-report` ist für alle Rollen ≥ reader zugänglich (Lesedaten, kein Schreiben).

**Ask First:**
- Soll das Reporting-Panel auch für location-admin sichtbar sein? → Für Ziel 3: nur system-admin.

**Never:**
- Physisches Löschen oder Umbenennen von `kontingent`, `eu_gesamtquote` oder `system_settings`.
- Breaking Changes an bestehenden API-Pfaden (`/system/eu-quota`, `/locations/summary`, etc.).
- Kontingent-Feld aus der UI entfernen — nur disabled + helperText für Nicht-Admins.

## I/O & Edge-Case Matrix

| Szenario | Input / State | Erwartetes Verhalten | Fehlerbehandlung |
|----------|--------------|----------------------|-----------------|
| Writer ändert kontingent via PATCH | `{"kontingent": 50}` + writer-Token | HTTP 403 | "Nur system-admin kann das Kontingent ändern." |
| system-admin ändert kontingent via PATCH | `{"kontingent": 50}` + system-admin-Token | HTTP 200, kontingent gespeichert | — |
| Kontingent-Report abrufen | GET /api/system/kontingent-report | JSON mit eu_gesamtquote, sum_kontingent, sum_regulaere_betten, abweichung_gesamt, locations[] | — |
| Einrichtung ohne reguläre Betten | location hat nur NOTBETT/WARTEPLATZ-Betten | regulaere_betten=0, abweichung=kontingent | — |
| eu_gesamtquote = 0 (ungesetzt) | Singleton noch nie gesetzt | abweichung_gesamt = sum_kontingent (gesamtes Kontingent unbedeckt) | — |
| location-admin öffnet Drilldown-Edit | Kontingent-Feld im Dialog | Feld disabled mit helperText "Nur system-admin kann das Kontingent ändern" | — |

</frozen-after-approval>

## Code Map

- `backend/src/api/capacity/router.py:332` — `update_location`: role-check für kontingent-Feld (user.roles); neuer Endpunkt `GET /system/kontingent-report` am Ende System-Settings-Block (~Z.152)
- `backend/src/api/capacity/schemas.py:145` — nach `EuQuotaUpdate`: neue Schemas `KontingentReportLocation` + `KontingentReportResponse`
- `frontend/src/pages/Dashboard.tsx:81` — neue State + useEffect für Report-Fetch; neues Panel unterhalb der Grid/Map-Toggle-Zeile, nur wenn `isSysAdmin`
- `frontend/src/pages/Drilldown.tsx:357` — `isSysAdmin`-Konstante ergänzen; Kontingent-TextField (`editKontingent`, ~Z.1599) `disabled={!isSysAdmin}`-Prop + helperText

## Tasks & Acceptance

**Execution:**
- [x] `backend/src/api/capacity/schemas.py` — nach `EuQuotaUpdate` zwei neue Klassen: `KontingentReportLocation` (id, name, kontingent, regulaere_betten, abweichung) und `KontingentReportResponse` (eu_gesamtquote, sum_kontingent, sum_regulaere_betten, abweichung_gesamt, locations)
- [x] `backend/src/api/capacity/router.py` — in `update_location`: direkt nach `updates`-Dict-Aufbau prüfen ob `body.kontingent is not None and 'system-admin' not in user.roles` → HTTPException 403; neuer Endpunkt `GET /system/kontingent-report` im System-Settings-Block: SQL-Query über `capacity.locations` + `capacity.rooms` + `capacity.beds` (bett_typ NOT IN ('NOTBETT','WARTEPLATZ') AND is_active=true), JOIN auf `system_settings`, gibt `KontingentReportResponse` zurück
- [x] `frontend/src/pages/Dashboard.tsx` — `isSysAdmin = roles.includes('system-admin')`; neuer State `report` + `reportLoading`; `useEffect` ruft `GET /api/system/kontingent-report` wenn `isSysAdmin`; neues `<Paper>`-Panel nach der Grid/Map-Ansicht: Kopfzeile mit eu_gesamtquote und Gesamtabweichung, MUI-Table mit Spalten Location / Kontingent / Reguläre Betten / Abweichung, Ampel-Chip pro Zeile (grün ≥0, rot <0)
- [x] `frontend/src/pages/Drilldown.tsx` — `isSysAdmin = roles.includes('system-admin')`; Kontingent-TextField `disabled={!isSysAdmin}` + `helperText` für Nicht-system-admin

**Acceptance Criteria:**
- Given writer-Token, when PATCH /api/locations/{id} mit `{"kontingent": 50}`, then HTTP 403 "Nur system-admin kann das Kontingent ändern".
- Given system-admin-Token, when PATCH /api/locations/{id} mit `{"kontingent": 50}`, then HTTP 200 und kontingent aktualisiert.
- Given GET /api/system/kontingent-report, then JSON enthält eu_gesamtquote, sum_kontingent, sum_regulaere_betten, abweichung_gesamt, locations-Array.
- Given system-admin-User im Dashboard, then Kontingent-Reporting-Panel sichtbar mit korrekten Summen.
- Given location-admin-User im Dashboard, then kein Reporting-Panel sichtbar.
- Given location-admin im Drilldown Edit-Dialog, then Kontingent-Feld disabled mit helperText.
- Given system-admin im Drilldown Edit-Dialog, then Kontingent-Feld editierbar.

## Design Notes

Der Reporting-Endpunkt kann direkt als Raw-SQL mit einer einzigen Abfrage implementiert werden — kein neues Repo nötig:

```sql
SELECT
  l.id, l.name, l.kontingent,
  COUNT(b.id) FILTER (WHERE b.is_active = true
    AND b.bett_typ NOT IN ('NOTBETT','WARTEPLATZ')) AS regulaere_betten
FROM capacity.locations l
LEFT JOIN capacity.rooms r ON r.location_id = l.id AND r.is_active = true
LEFT JOIN capacity.beds b ON b.room_id = r.id
WHERE l.is_active = true
GROUP BY l.id, l.name, l.kontingent
ORDER BY l.name
```

`eu_gesamtquote` wird in derselben Anfrage via `SELECT eu_gesamtquote FROM capacity.system_settings WHERE id = 1` gelesen (oder via vorhandenem `SqlSystemSettingsRepo`).

Das Drilldown-Kontingent-Feld: `disabled={!isSysAdmin}` + `helperText={!isSysAdmin ? 'Nur system-admin kann das Kontingent ändern' : 'EU-quotenrelevante Gesamtkapazität...'}`.

## Verification

**Commands:**
- `cd /Users/A3694852/KapzitaetsPlanungsTool/frontend && npx tsc --noEmit` — expected: 0 Fehler
- `cd /Users/A3694852/KapzitaetsPlanungsTool && python3 -m pytest backend/tests/ -x -q 2>/dev/null` — expected: alle grün
