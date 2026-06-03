---
title: 'Anfragen-Workflow: Lila-Bett-Info + Farbwechsel nach Annahme'
type: 'bugfix'
created: '2026-06-03'
status: 'done'
baseline_commit: '06401b44f6c52cdaa2d224a8fa0cc71749d81a42'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Wenn ein Bett im Drilldown lila (hasPendingRequest) angezeigt wird, sieht der Nutzer nicht, von welcher Einrichtung die Anfrage stammt, und ein Klick öffnet fälschlicherweise den Belegungs-Dialog. Nach dem Annehmen einer Anfrage (PENDING → CONFIRMED) bleibt die Farbe lila statt auf Blau zu wechseln, wodurch nicht erkennbar ist, dass ein physisches Einbuchen noch aussteht.

**Approach:** (1) Backend: `BedStatusItem` um `pending_requester_location_name` erweitern, damit der Tooltip den Anfragenden anzeigt. (2) Frontend: `handleBedClick` für `hasPendingRequest`-Betten auf `/reservations` navigieren statt den Belegungs-Dialog zu öffnen. (3) `isVorgemerkt`-Farbe von Lila auf Blau ändern (kongruent mit `hasConfirmedTransfer`), Legende aktualisieren.

## Boundaries & Constraints

**Always:**
- Einrichtungsname exakt wie in `capacity.locations.name` gespeichert anzeigen.
- Die Farb-Semantik bleibt konsistent: Lila = PENDING (unbestätigte Anfrage), Blau = CONFIRMED (bestätigt, Ankunft ausstehend), Orange = Verlegungsanfrage läuft, Dunkelblau-dashed = Verlegung genehmigt. `isVorgemerkt` entspricht semantisch CONFIRMED → Blau.
- Kein neuer Endpunkt; `pending_requester_location_name` wird im bestehenden Beds-Status-Query per Subquery befüllt.
- `isClickable`-Logik für `hasPendingRequest`-Betten bleibt `true` (der Click wird umgeleitet, nicht deaktiviert).

**Ask First:**
- Falls der `pending_reservation_id`-Subquery auf `capacity.locations` und `reservations.requests` in einem korrekten JOIN keine Location findet (z.B. wegen Datenmigrations-Lücke) → `null` zurückgeben und im Tooltip wegfallen lassen ist OK, HALT wenn mehr als das nötig wäre.

**Never:**
- Keine Änderungen am Reservierungs-Backend-Workflow (confirm/reject/transfer-Endpoints).
- Kein separater API-Aufruf vom Frontend beim Rendern der Bett-Karte.
- Keine Änderungen an `Reservations.tsx` oder `TaskInbox.tsx`.

## I/O & Edge-Case Matrix

| Szenario | Input / Zustand | Erwartetes Verhalten | Fehlerfall |
|----------|----------------|----------------------|-----------|
| Klick auf Lila-Bett (hasPendingRequest) | Bett hat `pending_reservation_id`, Status=FREI | Navigate zu `/reservations` (keine Dialog-Öffnung) | n/a |
| Tooltip Lila-Bett mit bekanntem Requester | `pending_requester_location_name = "München-Süd"` | Tooltip: "Verlegungsanfrage von: München-Süd" | n/a |
| Tooltip Lila-Bett ohne Requester (null) | `pending_requester_location_name = null` | Tooltip: "Verlegungsanfrage vorhanden — Bett vorgeschlagen" (Fallback) | n/a |
| Bett nach Annahme (isVorgemerkt) | `bed.status = 'VORGEMERKT'`, Anfrage CONFIRMED | Bett-Farbe blau (#0d47a1), Hintergrund #e3f2fd, Rand solid #1565c0 | n/a |
| Legende mit vorgemerkten Betten | `vorgemerkt > 0` | Legendeneintrag "Vorgemerkt" mit blauem Swatch | n/a |
| Klick auf Vorgemerkt-Bett | Bestehend: navigate zu Reservation-Highlight | Verhalten unverändert | n/a |

</frozen-after-approval>

## Code Map

- `backend/src/api/capacity/schemas.py:195` -- `BedStatusItem`: Feld `pending_requester_location_name: Optional[str]` hinzufügen
- `backend/src/api/capacity/router.py:491-498` -- Subquery für `pending_reservation_id`: um zweiten Subquery für `pending_requester_location_name` ergänzen (JOIN auf `capacity.locations`)
- `backend/src/api/capacity/router.py:558` -- `BedStatusItem`-Konstruktor: neues Feld befüllen
- `frontend/src/pages/Drilldown.tsx:233-235` -- `bedColor`/`bedBg`/`bedBorder` für `isVorgemerkt` auf Blau-Werte ändern
- `frontend/src/pages/Drilldown.tsx:246-247` -- Tooltip-Text für `hasPendingRequest` mit Requester-Name versehen
- `frontend/src/pages/Drilldown.tsx:270` -- `isVorgemerkt` in dashed-Border-Bedingung aufnehmen (optional, kongruent mit anderen pending-Zuständen)
- `frontend/src/pages/Drilldown.tsx:287` -- Hardcodierte Farbe `#6a1b9a` auf `#0d47a1` ändern (AZR-ID-Text bei VORGEMERKT)
- `frontend/src/pages/Drilldown.tsx:697` -- `handleBedClick`: vor dem `FREI`-Branch einen `hasPendingRequest`-Guard einbauen
- `frontend/src/pages/Drilldown.tsx:314-323` -- Legende: VORGEMERKT-Swatch von `#7b1fa2` auf `#1565c0` ändern

## Tasks & Acceptance

**Execution:**
- [x] `backend/src/api/capacity/schemas.py` -- `BedStatusItem` um `pending_requester_location_name: Optional[str] = None` nach `pending_reservation_id` erweitern -- Neues Feld für Requester-Name im Bed-Status-Response
- [x] `backend/src/api/capacity/router.py` -- Zweiten korrellierten Subquery direkt nach dem `pending_reservation_id`-Subquery einfügen: `SELECT l.name FROM reservations.requests pen_in JOIN capacity.locations l ON l.id = pen_in.requester_location_id WHERE pen_in.suggested_bed_id = b.id AND pen_in.status = 'PENDING' AND pen_in.belegung_start < :date_to AND pen_in.belegung_ende > :date_from LIMIT 1) AS pending_requester_location_name`; im `BedStatusItem`-Konstruktor befüllen -- Requester-Name ohne zusätzlichen API-Call
- [x] `frontend/src/pages/Drilldown.tsx` -- `bedColor`/`bedBg`/`bedBorder` (Z.233-235): `isVorgemerkt`-Zweig von Lila-Werten (`#6a1b9a`, `#f3e5f5`, `#7b1fa2`) auf Blau-Werte (`#0d47a1`, `#e3f2fd`, `#1565c0`) umstellen; gleiche Änderung an Z.287 (`color: '#6a1b9a'` → `'#0d47a1'`) -- CONFIRMED-Zustand visuell von PENDING unterscheiden
- [x] `frontend/src/pages/Drilldown.tsx` -- Z.270 `border`-Bedingung: `isVorgemerkt ||` vor `hasPendingRequest` ergänzen, damit VORGEMERKT-Betten ebenfalls gestrichelt dargestellt werden -- Konsistenz: alle "Person kommt noch"-Zustände haben gestrichelten Rand
- [x] `frontend/src/pages/Drilldown.tsx` -- Tooltip-Text Z.246-247 für `hasPendingRequest`: `bed.pending_requester_location_name ? \`Verlegungsanfrage von: ${bed.pending_requester_location_name}\` : 'Verlegungsanfrage vorhanden — Bett vorgeschlagen'` -- Anfragende Einrichtung im Tooltip sichtbar machen
- [x] `frontend/src/pages/Drilldown.tsx` -- `handleBedClick` (Z.697): Am Anfang der Funktion Guard einfügen: `if (bed.pending_reservation_id) { navigate('/reservations'); return }` -- Verhindert fälschliches Öffnen des Belegungs-Dialogs
- [x] `frontend/src/pages/Drilldown.tsx` -- Legende Z.316: `bgcolor: '#7b1fa2'` → `bgcolor: '#1565c0'`; Text "Vorgemerkt" → "Vorgemerkt (Eincheck ausst.)" -- Legende konsistent mit neuer Farbe

**Acceptance Criteria:**
- Given ein Bett hat Status FREI und `pending_reservation_id` gesetzt, when der Nutzer darauf klickt, then wird zur Seite `/reservations` navigiert (kein Belegungs-Dialog).
- Given `pending_requester_location_name = "München-Süd"`, when der Nutzer über das lila Bett hovert, then zeigt der Tooltip "Verlegungsanfrage von: München-Süd".
- Given `pending_requester_location_name = null`, when Hover auf lila Bett, then Fallback-Text "Verlegungsanfrage vorhanden — Bett vorgeschlagen".
- Given eine Anfrage wurde angenommen (bed.status = 'VORGEMERKT'), when der Drilldown gerendert wird, then ist das Bett blau (#0d47a1) mit blauem Hintergrund (#e3f2fd) und gestricheltem blauen Rand (#1565c0), nicht lila.
- Given `vorgemerkt > 0`, when die Legende angezeigt wird, then zeigt der "Vorgemerkt"-Eintrag einen blauen Swatch (#1565c0).

## Suggested Review Order

**Farbkorrektur VORGEMERKT (Blau statt Lila)**

- Einstiegspunkt: bedColor/bedBg/bedBorder für isVorgemerkt → #0d47a1 (semantisch gleich hasConfirmedTransfer)
  [`Drilldown.tsx:234`](../../frontend/src/pages/Drilldown.tsx#L234)

- Gestrichelter Rand für isVorgemerkt ergänzt — alle "Person kommt noch"-Zustände einheitlich
  [`Drilldown.tsx:271`](../../frontend/src/pages/Drilldown.tsx#L271)

- AZR-ID-Text auf VORGEMERKT-Betten: Farbe von Lila auf Blau angepasst
  [`Drilldown.tsx:288`](../../frontend/src/pages/Drilldown.tsx#L288)

- Legende: VORGEMERKT-Swatch blau, Text "Eincheck ausst." für Klarheit
  [`Drilldown.tsx:318`](../../frontend/src/pages/Drilldown.tsx#L318)

**Click-Navigation für hasPendingRequest**

- Guard: pending_reservation_id + FREI → navigate('/reservations') statt Belegen-Dialog
  [`Drilldown.tsx:699`](../../frontend/src/pages/Drilldown.tsx#L699)

- Tooltip-Hint korrigiert: hasPendingRequest → 'Klicken → Anfragen anzeigen'
  [`Drilldown.tsx:254`](../../frontend/src/pages/Drilldown.tsx#L254)

**Requester-Name im Tooltip**

- Tooltip für hasPendingRequest zeigt Einrichtungsname wenn vorhanden, Fallback sonst
  [`Drilldown.tsx:248`](../../frontend/src/pages/Drilldown.tsx#L248)

- Neuer korrelierter SQL-Subquery mit ORDER BY für Determinismus
  [`router.py:501`](../../backend/src/api/capacity/router.py#L501)

- BedStatusItem-Konstruktor befüllt neues Feld
  [`router.py:570`](../../backend/src/api/capacity/router.py#L570)

**Schema / Peripherals**

- Neues Feld `pending_requester_location_name: Optional[str]` in BedStatusItem
  [`schemas.py:223`](../../backend/src/api/capacity/schemas.py#L223)

- TypeScript-Interface um `pending_requester_location_name` erweitert
  [`Drilldown.tsx:101`](../../frontend/src/pages/Drilldown.tsx#L101)

## Spec Change Log

## Design Notes

Der `pending_requester_location_name`-Subquery nutzt dieselbe `WHERE`-Bedingung wie der `pending_reservation_id`-Subquery und ist damit immer paarweise konsistent — kein separater Join nötig.

`isVorgemerkt` (CONFIRMED, Bett reserviert, Person kommt) und `hasConfirmedTransfer` (CONFIRMED, Person belegt Bett, soll verlegt werden) haben dieselbe semantische Bedeutung aus Sicht der Zieleinrichtung: "Bestätigt, physisches Einbuchen steht noch aus" → gleiche Blau-Farbe ist korrekt.

## Verification

**Manual checks (if no CLI):**
- Drilldown einer Einrichtung aufrufen, die ein Bett mit PENDING-Anfrage hat → Bett ist lila, Tooltip zeigt Requester-Name, Klick navigiert zu `/reservations`.
- Anfrage im Reservierungsworkflow annehmen → Drilldown neu laden → Bett wechselt von lila auf blau.
- Legende auf der Drilldown-Seite: VORGEMERKT-Swatch ist blau statt lila.
