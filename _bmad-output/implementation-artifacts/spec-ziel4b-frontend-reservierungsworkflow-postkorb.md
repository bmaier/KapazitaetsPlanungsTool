---
title: 'Ziel 4b — Frontend Reservierungsworkflow + Postkorb + AppBar'
type: 'feature'
created: '2026-05-24'
status: 'done'
baseline_commit: 'NO_VCS'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Das Frontend (Ziel 4a) hat kein Navigationsrahmen und keine Seiten für Reservierungsanfragen oder den Postkorb — Sachbearbeiter können keine Reservierungen stellen, bestätigen oder Tasks bearbeiten.

**Approach:** Persistente AppBar mit drei Links (Dashboard / Reservierungen / Postkorb) und SSE-Badge; Reservierungen-Seite mit zwei Tabs (alle / Aktionen erforderlich) und Erstellen-Dialog; Task-Inbox-Seite mit Prioritätsfilter und Status-Update. Baut direkt auf der 4a-Infra (auth, API-Client, MUI-Theme, Routing) auf.

## Boundaries & Constraints

**Always:**
- Kein Personenname in der UI — nur AZR-ID und Alias-ID
- Bestätigen / Ablehnen nur in Tab "Aktionen erforderlich" (PENDING incoming); Stornieren nur auf eigenen ausgehenden Anfragen
- BITV 2.0 / WCAG 2.1 AA: Status-Badges mit Icon-Redundanz; aria-labels auf Aktions-Buttons
- SSE-Verbindung nutzt `@microsoft/fetch-event-source` (unterstützt Bearer-Header — native EventSource tut das nicht)
- `herkunftsland` muss ISO 3166-1 alpha-3 (3 Großbuchstaben) sein — Frontend-Validierung vor Submit
- `geburtsjahr` muss zwischen 1901 und aktuellem Jahr liegen — Frontend-Validierung

**Ask First:**
- Wenn der SSE-Stream dauerhaft 401 zurückgibt (Token nicht auto-refreshbar)

**Never:**
- Kein `/transfer`-Endpoint (existiert nicht im Backend)
- Kein direkter Datenbankzugriff
- Keine globalen State-Manager (nur React Context + useState)

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Neue Reservierung | Formular valide ausgefüllt | POST /api/reservations → Dialog schließt, Tab aktualisiert | Inline-Fehler im Dialog (422 → Feldmeldungen) |
| Ungültiger ISO-Code | herkunftsland = "Deutschland" | Submit-Button disabled; Hinweis "3 Buchstaben, z.B. DEU" | — |
| Bestätigen | Klick "Bestätigen" auf PENDING-Incoming | POST /api/reservations/{id}/confirm → Status-Chip → CONFIRMED | Snackbar "Bestätigung fehlgeschlagen" |
| Ablehnen | Klick "Ablehnen" auf PENDING-Incoming | POST /api/reservations/{id}/reject → Status-Chip → REJECTED | Snackbar "Ablehnung fehlgeschlagen" |
| Stornieren | Klick "Stornieren" auf eigene ausgehende Anfrage | DELETE /api/reservations/{id} → Zeile verschwindet | Snackbar "Stornierung fehlgeschlagen" |
| Task-Status-Update | Klick auf Status-Select einer Task | PATCH /api/tasks/{id} mit neuem Status → Chip aktualisiert | Snackbar "Aktualisierung fehlgeschlagen" |
| SSE-Neuereignis | Neuer Task im Stream | Badge-Zähler +1 auf Postkorb-Icon | Bei 401: reconnect mit frischem Token; bei dauerhaftem Fehler: kein Badge |
| Badge-Reset | Nutzer öffnet Postkorb-Seite | Zähler auf 0 zurücksetzen | — |
| Keine Reservierungen | Leere Liste | "Keine Reservierungen vorhanden."-Platzhalter | — |

</frozen-after-approval>

## Code Map

- `frontend/package.json` — `@microsoft/fetch-event-source` ergänzen
- `frontend/src/api/client.ts` — `post()`, `patch()`, `del()` Methoden ergänzen (4a: nur `get()`)
- `frontend/src/hooks/useSseNotifications.ts` — Neu: fetchEventSource-Hook; Badge-Counter; reset-Callback
- `frontend/src/components/NavBar.tsx` — Neu: AppBar mit drei Nav-Links + Badge + Logout-Button
- `frontend/src/App.tsx` — NavBar einbinden; Routen `/reservations` + `/tasks` ergänzen
- `frontend/src/pages/Reservations.tsx` — Neu: zwei MUI-Tabs; Locations-Cache; Confirm/Reject/Cancel-Aktionen
- `frontend/src/components/ReservationCreateDialog.tsx` — Neu: MUI-Dialog-Formular; Frontendvalidierung
- `frontend/src/pages/TaskInbox.tsx` — Neu: Task-Liste; Priority-Filter; Status-PATCH; Badge-Reset on mount

## Tasks & Acceptance

**Execution:**

- [x] `frontend/package.json` — `"@microsoft/fetch-event-source": "^2.0.1"` in `dependencies` ergänzen; `npm install` ausführen

- [x] `frontend/src/api/client.ts` — `useApiClient()`-Hook um `post<T>(path, body)`, `patch<T>(path, body)`, `del(path)` erweitern; gleiche Header-Injektion wie `get()`; gleiches rethrow-Muster auf `updateToken`-Fehler

- [x] `frontend/src/hooks/useSseNotifications.ts` — Neu anlegen. Exportiert `useSseNotifications(): { count: number; resetCount: () => void }`. Intern: `fetchEventSource('/api/notifications/stream', { headers: { Authorization: 'Bearer ...', 'X-Location-Id': '...' }, onmessage: () => setCount(n => n+1), onerror: reconnect-Logik mit `updateToken` })`. Auf Komponentenunmount: Controller abbrechen.

- [x] `frontend/src/components/NavBar.tsx` — Neu. MUI `AppBar` + `Toolbar`. Drei `Button`-Elemente: "Dashboard" (→ `/`), "Reservierungen" (→ `/reservations`), "Postkorb" (→ `/tasks` + `Badge` mit SSE-Count). Rechts: Username aus `tokenParsed.preferred_username` + Logout-Button. Aktive Route via `useLocation()` hervorheben.

- [x] `frontend/src/App.tsx` — `NavBar` oberhalb `<Routes>` einbinden (nur wenn `initialized`); neue Routen `/reservations` → `<Reservations />`, `/tasks` → `<TaskInbox />`.

- [x] `frontend/src/pages/Reservations.tsx` — Neu. Lädt beim Mount: (1) alle Locations `GET /api/locations` → Map `{id → name}` für Label-Anzeige; (2) alle Reservierungen `GET /api/reservations`. Tab 0 "Alle Anfragen": Tabelle mit Status-Chip, Einrichtungsname, Datum; Stornieren-Button wenn `requester_location_id === locationId && status ∈ {PENDING, CONFIRMED}`. Tab 1 "Aktionen erforderlich": `GET /api/reservations?target=mine` (nur PENDING); Bestätigen- und Ablehnen-Buttons. Button "Neue Reservierung" öffnet `ReservationCreateDialog`. Nach Aktion: Liste neu laden.

- [x] `frontend/src/components/ReservationCreateDialog.tsx` — Neu. MUI `Dialog` mit `DialogTitle`, `DialogContent`, `DialogActions`. Felder: Ziel-Einrichtung (Select aus Locations, eigene ausgeblendet), AZR-ID (TextField, max 50), Geschlecht (Select: M / W / D), Geburtsjahr (number input, 1901–heute), Herkunftsland (TextField, 3 Großbuchstaben, Tooltip ISO-3166-alpha-3), Von (date), Bis (date, > Von). Inline-Validierung beim Tippen; Submit disabled bis valide. `POST /api/reservations`; bei 422 Pydantic-Fehler: Feldmeldung aus `detail`.

- [x] `frontend/src/pages/TaskInbox.tsx` — Neu. Ruft `resetCount()` von `useSseNotifications` auf mount auf (Badge-Reset). Priority-Filter: MUI Select (Alle / HIGH / MEDIUM / LOW) → `GET /api/tasks?priority=X`. Task-Liste als MUI `List`: jede `ListItem` zeigt Titel, Body, Priority-Chip (HIGH=rot, MEDIUM=gelb, LOW=grün), Status-Select (OPEN / IN_PROGRESS / DONE / DISMISSED). Status-Änderung → `PATCH /api/tasks/{id}` mit `{ status: newStatus }`. Snackbar bei Fehler.

**Acceptance Criteria:**
- Given auth. Nutzer, when er die AppBar sieht, then sind alle drei Links sichtbar und der aktive Link ist hervorgehoben
- Given neuer Task via SSE, when er eintrifft und Nutzer ist nicht auf Postkorb-Seite, then zeigt Badge-Zähler um 1 erhöht
- Given Nutzer öffnet Postkorb-Seite, when Seite mounted, then ist Badge-Zähler 0
- Given PENDING-Incoming-Reservierung, when Nutzer klickt "Bestätigen", then verschwindet Zeile aus Tab "Aktionen erforderlich" und erscheint in Tab "Alle" mit Status CONFIRMED
- Given Formular mit herkunftsland = "DE" (2 Zeichen), when Nutzer tippt, then ist Submit-Button disabled und Feldmeldung sichtbar
- Given Task mit Status OPEN, when Nutzer wählt DONE im Select, then ist PATCH /api/tasks/{id} aufgerufen und Chip zeigt DONE
- Given eigene ausgehende PENDING-Reservierung, when Nutzer klickt "Stornieren", then verschwindet Zeile aus Tab "Alle Anfragen"

## Spec Change Log

### Iteration 1 (Review 2026-05-24) — zwei Patches

**Patch A — SSE-Instanz-Split (bad_spec):**
- Problem: `useSseNotifications()` in NavBar und TaskInbox erzeugte zwei separate Hook-Instanzen → zwei SSE-Verbindungen, `resetCount()` in TaskInbox hatte keinen Effekt auf NavBars Badge-Count. AC "Badge-Reset on mount" schlug fehl.
- Fix: Hook in Context-Pattern umgebaut. `useSseInternalState()` hält State + Effect; `SseNotificationsProvider` (TSX) stellt den Context bereit; `useSseNotifications()` liest nur noch aus dem Context. Provider in `App.tsx` um Routen-Baum gewickelt.
- Neue Datei: `frontend/src/hooks/SseNotificationsProvider.tsx`

**Patch B — Tab 0 zeigte nur eigene Reservierungen:**
- Problem: `ownReservations = reservations.filter(...)` filterte client-seitig, obwohl "Alle Anfragen" alle vom API zurückgegebenen Reservierungen zeigen soll; Stornieren-Button bedingt sichtbar per `canCancel()`.
- Fix: Tab 0 nutzt `reservations` (ungefiltert); Tab-Count-Label angepasst; Spalte "Von (Einrichtung)" ergänzt.

## Design Notes

**EventSource + Bearer-Token:** Native `EventSource` sendet keine Custom-Header. `@microsoft/fetch-event-source` nutzt `fetch` intern → Bearer-Token und X-Location-Id funktionieren wie bei anderen API-Calls. Bei 401 ruft `onerror` `updateToken(60)` auf und reconnectet.

**Locations-Cache in Reservations.tsx:** `GET /api/locations` gibt alle Einrichtungen zurück (kein X-Location-Id-Filter, analog zur summary). Das Array wird in eine `Map<string, string>` transformiert und per Prop/lokale Variable genutzt — kein Context nötig.

**SSE als geteilter Context:** Da NavBar (Badge) und TaskInbox (reset) auf denselben SSE-State zugreifen müssen, wird `SseNotificationsProvider` um den gesamten Routen-Baum gelegt. Die internen Hook-Implementierungen (`useSseInternalState`) laufen einmalig im Provider; alle Konsumenten lesen via `useSseNotifications()` aus dem Context.

**`del()` statt `delete()`:** `delete` ist ein JavaScript-Schlüsselwort — die API-Client-Methode wird `del()` benannt.

## Suggested Review Order

1. `frontend/src/hooks/useSseNotifications.ts` + `SseNotificationsProvider.tsx` — SSE-Context-Kern
2. `frontend/src/App.tsx` — Provider-Einbindung + Routing
3. `frontend/src/components/NavBar.tsx` — Badge + aktive Route
4. `frontend/src/pages/Reservations.tsx` — Tab-Logik + Confirm/Reject/Cancel
5. `frontend/src/components/ReservationCreateDialog.tsx` — Formularvalidierung
6. `frontend/src/pages/TaskInbox.tsx` — Badge-Reset + Status-PATCH
7. `frontend/src/api/client.ts` — post/patch/del-Erweiterungen

## Verification

**Commands:**
- `cd frontend && npm run build` -- erwartet: kein TypeScript-Fehler

**Manual checks:**
- Nach `make dev && make seed`: AppBar mit drei Links sichtbar; alle Routen erreichbar
- Neue Reservierung erstellen → erscheint in Tab "Alle Anfragen" mit Status PENDING
- Als second writer_user (separates Browserfenster mit reader_user auf Passau) eingehende Reservierung bestätigen — SSE-Badge auf Frankfurt-Session erhöht sich
