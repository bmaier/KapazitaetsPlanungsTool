---
title: 'Ziel 11 — Interne Zeitreihenstatistik (Belegung & Kapazität)'
type: 'feature'
created: '2026-05-31'
status: 'done'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Das System zeigt nur den aktuellen Belegungsstand — historische Auslastungstrends, Kapazitätsengpässe über Zeit und die Entwicklung der Kontingentnutzung sind nicht auswertbar.

**Approach:** Neue Statistik-Seite mit interaktiven Recharts-Charts (Belegungsgrad, Kontingentnutzung, Notbetten) über frei wählbare Zeiträume mit Auto-Granularität; Mini-Sparkline im Drilldown-Header; Kontingentänderungen werden historisiert in einer neuen `capacity.kontingent_history`-Tabelle; Belegungshistorie wird aus den bestehenden `persons.occupants`-Datumsbereichen per SQL rekonstruiert.

## Boundaries & Constraints

**Always:**
- Belegungshistorie wird aus `OccupantModel.belegung_start/belegung_ende` berechnet — keine neue Historisierungstabelle für Belegungsdaten
- Kontingentänderung schreibt immer einen Snapshot in `capacity.kontingent_history` (actor_id aus JWT-Sub)
- Chart-Bibliothek: ausschließlich `recharts@^2.12` (MIT, React-nativ, kein weiteres Chart-Framework)
- Rollen: alle Rollen (reader+) können Statistik sehen; location-gebundene Rollen sehen nur ihre Einrichtung; system-admin kann per Picker wechseln
- Auto-Granularität: ≤60 Tage → täglich, 61–180 Tage → wöchentlich, >180 Tage → monatlich
- Alembic-Namenskonvention: `0015_kontingent_history.py`

**Ask First:**
- Falls system-admin mehrere Einrichtungen gleichzeitig in einem Chart vergleichen soll (aktuell: Switcher, kein Multi-Line-Vergleich)

**Never:**
- EU-Statistik-Export oder PDF-Generierung (→ Ziel B, zurückgestellt in deferred-work.md)
- Realtime-Updates per SSE/WebSocket für Charts
- Backfill von Kontingent-History vor Systemstart
- Andere Chart-Bibliotheken (kein Chart.js, Nivo, ApexCharts, D3)

## I/O & Edge-Case Matrix

| Szenario | Input / Zustand | Erwartetes Verhalten | Fehlerbehandlung |
|---|---|---|---|
| Normaler Abruf | location_id, date_from=−30T, granularity=day | LineChart mit 30 Datenpunkten, Kontingent-Linie als Treppe | — |
| Kein Kontingent-History | Neue Einrichtung, noch kein Snapshot | Kontingent-Linie zeigt aktuellen `kontingent`-Wert als Fallback für gesamten Zeitraum | — |
| Leerer Zeitraum | date_from > date_to | HTTP 422 | Fehlermeldung im Frontend |
| Keine Belegung im Zeitraum | 0 Occupants | Charts zeigen Nulllinie, KPI-Cards zeigen 0 % | Kein Error, kein Spinner-Loop |
| system-admin, Einrichtung wechseln | location_id wechseln per Picker | Charts re-fetchen, alle KPIs aktualisieren | Loading-State während Fetch |
| Zeitraum 1 Jahr | granularity=month | 12 Monatspunkte, kein Datums-Overflow | — |

</frozen-after-approval>

## Code Map

- `backend/alembic/versions/0015_kontingent_history.py` — neue Migration: Tabelle `capacity.kontingent_history`
- `backend/src/adapters/db/models.py` — KontingentHistoryModel (mapped_column, schema="capacity")
- `backend/src/api/capacity/router.py` — PATCH /locations/{id}: Snapshot nach Kontingentänderung schreiben
- `backend/src/api/statistics/schemas.py` — neue Datei: Pydantic v2 DTOs (OccupancyDataPoint, KpiResponse, StatisticsResponse)
- `backend/src/api/statistics/router.py` — neue Datei: GET /statistics/occupancy + GET /statistics/kpis
- `backend/src/main.py` — statistics-Router einbinden
- `frontend/package.json` — recharts@^2.12 hinzufügen
- `frontend/src/pages/Statistik.tsx` — neue Seite: Picker, Shortcuts, ComposedChart, KPI-Cards
- `frontend/src/components/BelegungSparkline.tsx` — Mini-LineChart (30T, kein Axis) für Drilldown
- `frontend/src/pages/Drilldown.tsx` — BelegungSparkline in Kopfzeile einbinden
- `frontend/src/App.tsx` — Route /statistik ergänzen
- `frontend/src/components/NavBar.tsx` — Statistik-Navigationseintrag (BarChart-Icon)

## Tasks & Acceptance

**Execution:**
- [x] `backend/alembic/versions/0015_kontingent_history.py` -- Migration anlegen: `capacity.kontingent_history` (id UUID PK, location_id UUID FK→locations, kontingent_value INTEGER NOT NULL, valid_from TIMESTAMPTZ DEFAULT now(), actor_id TEXT); revision_id="0015", down_revision="0014" -- Historisierungsgrundlage
- [x] `backend/src/adapters/db/models.py` -- KontingentHistoryModel mit `mapped_column()` hinzufügen, `__table_args__ = {"schema": "capacity"}` -- ORM-Mapping
- [x] `backend/src/api/capacity/router.py` -- PATCH /locations/{id}: nach erfolgreichem Kontingent-Update Snapshot in kontingent_history einfügen (actor_id = current_user.sub, valid_from = now()) -- Historisierung bei Änderung
- [x] `backend/src/api/statistics/schemas.py` -- Pydantic v2 DTOs: `OccupancyDataPoint(date, belegt, frei, notbetten_belegt, kontingent, belegungsgrad_pct)`, `KpiResponse(aktuell_pct, avg30t_pct, trend_delta_pct)`, `StatisticsResponse(data: list[OccupancyDataPoint], kpis: KpiResponse)`; `model_config = ConfigDict(from_attributes=True)` -- Typsichere Contracts
- [x] `backend/src/api/statistics/router.py` -- `GET /statistics/occupancy` (query params: location_id UUID, date_from date, date_to date, granularity Literal["day","week","month"]="day"): SQL via `generate_series` über `persons.occupants` + letzten `kontingent_history`-Snapshot je Datenpunkt (Fallback: aktuelles `kontingent`); `GET /statistics/kpis`: aktuelle Auslastung, Ø30T, Trend; beide mit `Depends(get_current_user)` + Location-Auth-Check -- Statistik-Endpoints
- [x] `backend/src/main.py` -- `from src.api.statistics.router import router as statistics_router` + `app.include_router(statistics_router, prefix="/api")` -- Router einbinden
- [x] `frontend/package.json` -- `npm install recharts@^2.12` ausführen -- Chart-Bibliothek installieren
- [x] `frontend/src/pages/Statistik.tsx` -- Einrichtungs-Picker (system-admin: alle Einrichtungen per Dropdown; andere Rollen: fest), Zeitraum-Shortcuts (7T / 30T / 3M / 1J) + MUI DatePicker (frei), `ComposedChart`: `Line` Belegungsgrad % (blau #003366), `Line stepAfter` Kontingent-Auslastung % (orange gestrichelt), `Bar` Notbetten gestapelt (halbtransparent orange), 3 KPI-Cards (Aktuell / Ø30T / Trend-Pfeil) -- Hauptstatistik-Ansicht
- [x] `frontend/src/components/BelegungSparkline.tsx` -- `<LineChart width={200} height={50}>` ohne Axis, Tooltip on hover, Datenpunkte letzter 30T -- kompakter Trendindikator
- [x] `frontend/src/pages/Drilldown.tsx` -- BelegungSparkline neben Belegungsgrad-KPI in Kopfzeile (Paper) einbinden -- Kontext-Trend im Drilldown
- [x] `frontend/src/App.tsx` -- `<Route path="/statistik" element={<Statistik />} />` ergänzen -- Routing
- [x] `frontend/src/components/NavBar.tsx` -- Statistik-Eintrag mit `BarChartIcon` (MUI) hinzufügen, für alle Rollen sichtbar -- Navigation

**Acceptance Criteria:**
- Given Nutzer ist eingeloggt, when er /statistik aufruft, then sieht er einen LineChart mit Belegungsgrad % der letzten 30 Tage und 3 KPI-Cards
- Given location-admin ruft /statistik auf, when Seite lädt, then ist kein Einrichtungs-Picker sichtbar (nur eigene Einrichtung)
- Given system-admin ruft /statistik auf, when er im Picker die Einrichtung wechselt, then laden Charts neu für die gewählte Einrichtung
- Given Admin ändert Kontingent via PATCH /locations/{id}, when Request erfolgreich, then existiert ein neuer Eintrag in `capacity.kontingent_history`
- Given Kontingent wurde 3x geändert und Statistik umfasst alle Änderungszeitpunkte, when Chart lädt, then zeigt die Kontingent-Linie eine Treppenfunktion mit historisch korrekten Werten
- Given Zeitraum >180 Tage gewählt, when Chart lädt, then zeigt er monatliche Granularität (nicht tägliche Datenpunkte)
- Given Drilldown einer Einrichtung geöffnet, when Seite lädt, then ist eine 30-Tage-Sparkline im Kopfbereich sichtbar

## Design Notes

**Belegungshistorie per SQL (kein extra Table):**
```sql
SELECT date_trunc(:granularity, gs)::date AS day,
  COUNT(o.id) FILTER (WHERE o.belegung_start <= gs::date
    AND (o.belegung_ende IS NULL OR o.belegung_ende >= gs::date)) AS belegt
FROM generate_series(:date_from, :date_to, ('1 ' || :granularity)::interval) AS gs
LEFT JOIN persons.occupants o ON o.location_id = :location_id
GROUP BY day ORDER BY day
```

**Kontingent-Treppenlinie:** Pro Datenpunkt letzten History-Eintrag mit `valid_from <= datenpunkt` nehmen; falls kein Eintrag → aktuellen `locations.kontingent` als Konstante verwenden.

**Recharts ComposedChart:**
```tsx
<ComposedChart data={data}>
  <Line type="monotone" dataKey="belegungsgrad_pct" stroke="#003366" dot={false} />
  <Line type="stepAfter" dataKey="kontingent_auslastung_pct" stroke="#f57c00" strokeDasharray="4 2" dot={false} />
  <Bar dataKey="notbetten_belegt" fill="#ff9800" opacity={0.4} />
  <Tooltip /><Legend /><XAxis dataKey="date" /><YAxis unit="%" />
</ComposedChart>
```

## Verification

**Commands:**
- `cd frontend && npm run build` -- expected: TypeScript strict ohne Fehler, kein `noUnusedLocals`-Verstoß
- `cd backend && python -m alembic upgrade head` -- expected: Migration 0015 läuft fehlerfrei durch

**Manual checks:**
- /statistik öffnen → LineChart mit Datenpunkten und 3 KPI-Cards sichtbar
- Kontingent einer Einrichtung in Drilldown ändern → `SELECT * FROM capacity.kontingent_history ORDER BY valid_from DESC LIMIT 5` zeigt neuen Eintrag
- Zeitraum auf 1J setzen → Chart zeigt ~12 Monatspunkte, nicht 365 Tagespunkte

## Spec Change Log
