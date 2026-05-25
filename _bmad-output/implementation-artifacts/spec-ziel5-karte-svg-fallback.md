---
title: 'Ziel 5 — Karte + SVG-Fallback auf Dashboard'
type: 'feature'
created: '2026-05-24'
status: 'done'
baseline_commit: 'NO_VCS'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Das Dashboard zeigt Einrichtungskapazitäten nur als Card-Grid. Eine geografische Kartenansicht fehlt — Sachbearbeiter können räumliche Zusammenhänge (nahe Einrichtungen, regionale Lastverteilung) nicht erkennen. Fällt der lokale Tile-Server aus, bleibt die Karte leer.

**Approach:** Toggle-Button (Grid / Karte) im Dashboard-Header. Karte: react-leaflet mit Ampel-CircleMarkern auf lokalem Tileserver (Port 8082, Vite-Proxy `/tiles`). Fällt der Tileserver beim Mount-Health-Check aus, zeigt das Frontend ein SVG-Schaubild vom Backend-Endpoint `GET /api/map/svg`. Klick auf Marker → Drilldown.

## Boundaries & Constraints

**Always:**
- Tile-URL nur via Vite-Proxy `/tiles/...` → `http://localhost:8082` — kein direkter Localhost-Zugriff im Frontend-Code
- Ampel-Schwellwerte: < 70 % grün (#4caf50), 70–90 % orange (#ff9800), ≥ 90 % rot (#f44336) — identisch zu Dashboard-Grid
- `import 'leaflet/dist/leaflet.css'` in `MapView.tsx` — Pflicht, sonst fehlen Marker-Styles
- Kein Personenname oder AZR-ID auf der Karte
- SVG-Fallback nutzt dieselbe Locations-Summary-Query wie `GET /api/locations/summary`

**Ask First:**
- Wenn der tileserver-gl Stil-Name (Pfad-Prefix im Tile-URL) von `basic-preview` abweicht

**Never:**
- Kein OpenStreetMap-CDN als Primärquelle (offline-first)
- Kein Mapbox, kein anderes Kartensystem
- Kein globaler State für Ansichts-Toggle — nur lokales `useState` in `Dashboard.tsx`
- Kein Umbau des bestehenden Card-Grid-Renders — nur ausblenden, nicht löschen

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Karte laden | Tileserver `/tiles/health` → 200 | Leaflet-Map mit Ampel-Markern aller aktiven Einrichtungen | — |
| Tileserver down | `/tiles/health` → 5xx oder Network Error | Fetch `GET /api/map/svg` → SVG als `<img>`; Snackbar "Kartenserver nicht erreichbar, Fallback aktiv" | — |
| SVG-Fallback auch down | beide Fehler | Snackbar "Karte nicht verfügbar", leerer Bereich | — |
| Marker-Klick | Klick auf CircleMarker | `navigate('/locations/${id}')` | — |
| Toggle Grid→Karte | Klick "Karte" | MapView erscheint, Health-Check startet | — |
| Toggle Karte→Grid | Klick "Grid" | Card-Grid wieder sichtbar, MapView ausgeblendet | — |

</frozen-after-approval>

## Code Map

- `frontend/vite.config.ts` — Proxy `/tiles` → `http://localhost:8082` ergänzen
- `frontend/package.json` — `react-leaflet`, `leaflet`, `@types/leaflet` ergänzen
- `frontend/src/pages/Dashboard.tsx` — `viewMode` State + Toggle-Buttons + bedingte MapView-Einbindung
- `frontend/src/components/MapView.tsx` — Neu: Health-Check, Leaflet-Map oder SVG-Fallback
- `backend/src/api/map/router.py` — Neu: `GET /api/map/svg` generiert SVG-Schaubild
- `backend/src/main.py` — map-Router registrieren

## Tasks & Acceptance

**Execution:**

- [x] `frontend/vite.config.ts` — `/tiles`-Proxy ergänzen: `{ target: 'http://localhost:8082', changeOrigin: true, rewrite: (p) => p.replace(/^\/tiles/, '') }` (Prefix `/tiles` wird gestripped, da tileserver-gl die Pfade ohne Prefix erwartet)

- [x] `frontend/package.json` — `"react-leaflet": "^4.2.1"`, `"leaflet": "^1.9.4"`, `"@types/leaflet": "^1.9.14"` ergänzen; `npm install` ausführen

- [x] `frontend/src/components/MapView.tsx` — Neu. Props: `locations: LocationSummary[]` (Interface aus Dashboard importieren oder inline). On mount: `fetch('/tiles/health')` — 200 → Leaflet-Modus; sonst → `fetch('/api/map/svg')` → Blob-URL setzen, SVG-Modus. Leaflet-Modus: `MapContainer` center=`[51.1, 10.4]` zoom=6, `TileLayer` url=`/tiles/styles/basic-preview/{z}/{x}/{y}.png`, je Location ein `CircleMarker` (radius=14, color/fillColor per Ampel-Schwellwert, fillOpacity=0.8), `Popup` mit Name + Auslastung %, useNavigate für Marker-onClick. SVG-Modus: `<img src={blobUrl} width="100%" style={{maxHeight: '70vh'}} />`. `import 'leaflet/dist/leaflet.css'` am Dateianfang.

- [x] `frontend/src/pages/Dashboard.tsx` — `viewMode: 'grid' | 'map'` useState (initial `'grid'`). Header-Box: rechts `ToggleButtonGroup` (exclusive) mit `ToggleButton value="grid"` (GridViewIcon) + `ToggleButton value="map"` (MapIcon). Bestehender Card-Grid-Block: `display: viewMode === 'grid' ? 'block' : 'none'` oder bedingte Einbindung. Unter dem Header: `{viewMode === 'map' && <MapView locations={locations} />}`. MUI Icons: `GridViewIcon` aus `@mui/icons-material/GridView`, `MapIcon` aus `@mui/icons-material/Map`.

- [x] `backend/src/api/map/router.py` — Neu. `GET /api/map/svg`: Query identisch zu `/locations/summary` via `AsyncSessionFactory`. SVG-Generierung: viewBox `0 0 800 600`; grauer Hintergrund-Rect (`fill='#e8ecef'`); je Location `<circle>` an SVG-Pixelkoordinaten (Bounding-Box: lat 47.3–55.1, lon 5.9–15.0 → SVG 700×500 + Offset 50,50; `svgX = (lon - 5.9)/(15.0-5.9)*700+50`, `svgY = (55.1-lat)/(55.1-47.3)*500+50`); hardcodierte lon/lat je Location-Name (Frankfurt=8.68/50.11, München=11.58/48.14, Passau=13.46/48.57, Hamburg=10.00/53.55; für unbekannte Locations: lon=10.4/lat=51.1 Mittelpunkt); Farbe per Ampel-Schwellwert; `<text>` mit Name+Auslastung. Rückgabe: `Response(content=svg_str, media_type='image/svg+xml')`.

- [x] `backend/src/main.py` — `from src.api.map.router import router as map_router` importieren; `app.include_router(map_router, prefix="/api", dependencies=[Depends(get_current_user)])` nach den bestehenden Routen einfügen.

**Acceptance Criteria:**
- Given auth. Nutzer auf Dashboard, when er "Karte"-Toggle klickt, then erscheint Leaflet-Karte mit farbigen Kreisen für alle aktiven Einrichtungen
- Given Leaflet-Karte sichtbar, when Nutzer Marker klickt, then navigiert er zu `/locations/{id}` (Drilldown)
- Given Tileserver ist gestoppt, when Nutzer "Karte" wählt, then erscheint SVG-Schaubild und Snackbar "Kartenserver nicht erreichbar, Fallback aktiv"
- Given SVG-Karte zeigt Frankfurt (belegungsgrad ≥ 90 %), when Nutzer die Karte sieht, then ist der Frankfurter Marker rot (#f44336)
- Given Toggle auf "Grid", when Nutzer zurückwechselt, then ist das Card-Grid vollständig sichtbar

## Spec Change Log

### Iteration 1 (Review 2026-05-24) — drei Patches

**Patch A — Unmount-Race + Object-URL-Leak (patch):**
- Problem: `objectUrl` wird in async `detectMode()` erst nach Cleanup gesetzt → Blob-URL nie revoked; `setSvgUrl` nach Unmount löst React-Warning aus.
- Fix: `mounted`-Flag + `AbortController` in `useEffect`; `ctrl.abort()` + `mounted = false` im Cleanup; `URL.revokeObjectURL` nur wenn objectUrl gesetzt; alle `setState`-Aufrufe via `if (mounted)` guard.

**Patch B — MapView remountet bei jedem Toggle (patch):**
- Problem: `{viewMode === 'map' && <MapView />}` zerstört und remountet die Komponente bei jedem Toggle → Health-Check und Fetches wiederholen sich, Snackbar-State wird zurückgesetzt.
- Fix: `<Box sx={{ display: viewMode === 'map' ? 'block' : 'none' }}><MapView /></Box>` — identisch zum Grid-Muster; Komponente bleibt gemountet.

**Patch C — SVG XSS / Location-Name nicht HTML-escaped (patch):**
- Problem: `{name}` direkt in SVG-f-String interpoliert — Zeichen wie `&` brechen SVG-XML; Sonderzeichen aus DB-Namen könnten SVG korrumpieren.
- Fix: `import html as html_module`; `name = html_module.escape(str(row.name))`; Koordinaten-Lookup auf `row.name` (unescaped) vor Escape.

## Design Notes

**Tile-URL prüfen:** Der tileserver-gl-Pfad hängt vom geladenen Stil ab. `basic-preview` ist der häufigste Default — bei Abweichung Ask-First-Constraint einhalten und Spec aktualisieren.

**SVG-Koordinatenumrechnung:** Deutschland-Bounding-Box (lat 47.3–55.1°N, lon 5.9–15.0°E) auf 700×500 SVG-Bereich (Offset 50,50):
```
svgX = (lon - 5.9) / (15.0 - 5.9) * 700 + 50
svgY = (55.1 - lat) / (55.1 - 47.3) * 500 + 50
```

**Leaflet Icon-Bug vermieden:** react-leaflet verliert Standard-Marker-Icons bei Vite-Bundling. `CircleMarker` braucht keine externen Icon-Assets — kein Icon-Bug.

**Hardcodierte Koordinaten im Backend:** Die 4 Demo-Einrichtungen (Frankfurt, München, Passau, Hamburg) haben feste lon/lat im Backend-Code. Für unbekannte Einrichtungs-Namen → Mittelpunkt Deutschland. Für Phase 1 ausreichend; später: `locations`-Tabelle um `lat`/`lon`-Spalten erweitern.

## Suggested Review Order

**Fallback-Erkennung — Herzstück der Implementierung**

- `mounted`-Flag + `AbortController` verhindern Leak/setState nach Unmount
  [`MapView.tsx:42`](../../frontend/src/components/MapView.tsx#L42)

- Drei Render-Äste: Leaflet / SVG-img / leere Box
  [`MapView.tsx:90`](../../frontend/src/components/MapView.tsx#L90)

**Leaflet-Karte**

- Hardcodierte Demo-Koordinaten (Frankfurt/München/Passau/Hamburg)
  [`MapView.tsx:19`](../../frontend/src/components/MapView.tsx#L19)

- `CircleMarker` mit `eventHandlers.click` → navigate; `Popup` mit Auslastung
  [`MapView.tsx:100`](../../frontend/src/components/MapView.tsx#L100)

**Dashboard-Integration**

- `viewMode` State + ToggleButtonGroup
  [`Dashboard.tsx:56`](../../frontend/src/pages/Dashboard.tsx#L56)

- MapView per `display:none` gemountet (verhindert Remount-Fetches)
  [`Dashboard.tsx:155`](../../frontend/src/pages/Dashboard.tsx#L155)

**Backend SVG-Renderer**

- `html.escape(name)` verhindert SVG-XML-Korrumpierung durch DB-Sonderzeichen
  [`router.py:54`](../../backend/src/api/map/router.py#L54)

- Koordinatenformel lat/lon → SVG-Pixel; `ampel_color` Schwellwerte
  [`router.py:23`](../../backend/src/api/map/router.py#L23)

**Konfiguration**

- `/tiles`-Proxy mit Prefix-Strip (tileserver-gl erwartet Pfade ohne `/tiles`)
  [`vite.config.ts:17`](../../frontend/vite.config.ts#L17)

- map_router registriert mit `get_current_user` Dependency
  [`main.py:33`](../../backend/src/main.py#L33)

## Verification

**Commands:**
- `cd frontend && npm run build` — erwartet: kein TypeScript-Fehler

**Manual checks:**
- `make dev` → Dashboard → Toggle → Leaflet-Karte mit 4 Ampel-Markern
- Marker-Klick → Drilldown
- Tileserver im Docker stoppen → SVG-Schaubild erscheint + Snackbar
