---
title: 'Bettsuche: Warteplatz → automatische Verlegungsanfrage + hasPerson-Guard'
type: 'bugfix'
created: '2026-06-03'
status: 'done'
baseline_commit: 'd958295'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** (1) Wenn in der Bettsuche eine neue (unbekannte) AZR-ID eingegeben wird, sendet `handleAccept` nach dem manuellen Warteplatz-Anlegen keine Verlegungsanfrage an die Zieleinrichtung — der Nutzer sitzt mit einer Person im Wartebereich, aber ohne ausstehende Anfrage. (2) Wenn `hasPerson=true` (URL-Param) aber die Person kein aktives Bett hat (`currentPerson=null`), fällt `handleAccept` in den "Belegung vormerken"-Branch und versucht, ein Fremd-Bett direkt zu buchen → Backend-Fehler.

**Approach:** (1) In `handleAccept`: nach dem Warteplatz-Block, wenn `warteplatzCreated=true` UND Zielbett ist an anderer Einrichtung → POST `/api/reservations` analog zum `hasPerson`-Pfad. (2) Guard am Anfang von `handleAccept`: `hasPerson && !currentPerson` → Snackbar-Fehler, frühes Return.

## Boundaries & Constraints

**Always:**
- Verlegungsanfrage nur senden wenn `variant.beds[0]?.location_id !== locationId` (cross-location). Bei lokalem Ziel: direkte Buchung wie bisher.
- Wenn kein freies Wartebereich-Bett vorhanden → bestehende Fehlermeldung bleibt, keine Anfrage.
- Daten für Reservierungsanfrage: `azr_id` + `geschlecht` aus `bedAssignment`, `geburtsjahr`/`herkunftsland` als Demo-Defaults (`new Date().getFullYear() - 30`, `'UNK'`), `suggested_bed_id` = `variant.beds[idx]?.bed_id`.

**Ask First:** — keine offenen Fragen.

**Never:**
- Kein neuer Backend-Endpoint.
- Kein automatisches Überspringen des Warteplatz-Formulars (Geschlecht-Auswahl + Enddatum bleibt manuell).

## I/O & Edge-Case Matrix

| Szenario | Zustand | Erwartetes Verhalten |
|----------|---------|---------------------|
| Warteplatz erstellt, Ziel = andere Einrichtung | `warteplatzCreated=true`, `beds[0].location_id !== locationId` | POST `/api/reservations` + Dialog schließen + "Abgeschlossen" |
| Warteplatz erstellt, Ziel = eigene Einrichtung | `warteplatzCreated=true`, `beds[0].location_id === locationId` | Wie bisher: kein POST, Dialog schließt (Person ist bereits im Wartebereich) |
| `hasPerson=true`, Person kein aktives Bett | `currentPerson=null` | Snackbar: "Person hat kein aktives Bett — bitte zuerst im Wartebereich einbuchen.", kein API-Call |
| `hasPerson=true`, `currentPerson` vorhanden | `currentPerson` gesetzt | Unverändertes Verhalten |

</frozen-after-approval>

## Code Map

- `frontend/src/pages/SuggestionWizard.tsx:460` — `handleAccept`: hier beide Fixes
- `frontend/src/pages/SuggestionWizard.tsx:545-562` — Aktueller "keine Person"-Branch (warteplatzCreated-Logik) — hier Änderung

## Tasks & Acceptance

**Execution:**
- [x] `frontend/src/pages/SuggestionWizard.tsx` — In `handleAccept` direkt nach `if (!suggestion || selectedVariant === null) return`: Guard einfügen `if (hasPerson && !currentPerson) { setSnackbar({open: true, message: 'Person hat kein aktives Bett — bitte zuerst im Wartebereich einbuchen.', severity: 'error'}); setLoading(false); return }` — verhindert falschen Fall-Through in Belegung-vormerken-Branch
- [x] `frontend/src/pages/SuggestionWizard.tsx` — Im `else`-Branch (Belegung vormerken, ~Z.545): nach dem `if (assigned.length > 0)` und dem `else if (!bedAssignments.some(a => a.warteplatzCreated))` Block einen neuen `else`-Branch ergänzen: wenn `bedAssignments.some(a => a.warteplatzCreated)` UND `variant.beds[0]?.location_id !== locationId` → für jede `warteplatzCreated`-Zuweisung POST `/api/reservations` mit `{target_location_id: variant.beds[idx]?.location_id, azr_id: a.azr_id.trim(), geschlecht: a.geschlecht, geburtsjahr: new Date().getFullYear()-30, herkunftsland: 'UNK', belegung_start: start, belegung_ende: ende, suggested_bed_id: variant.beds[idx]?.bed_id ?? null}` — sendet Verlegungsanfrage nach Warteplatz-Anlage

**Acceptance Criteria:**
- Given Warteplatz erstellt (`warteplatzCreated=true`) und Ziel ist andere Einrichtung, when Nutzer "Abschließen" klickt, then wird POST `/api/reservations` gesendet und Dialog zeigt "Abgeschlossen".
- Given Warteplatz erstellt und Ziel ist eigene Einrichtung, when "Abschließen", then kein POST `/api/reservations` (lokale Situation, keine Anfrage nötig).
- Given `hasPerson=true` und Person hat kein aktives Bett, when Nutzer "Verlegungsanfrage senden" klickt, then Snackbar-Fehler erscheint, kein API-Call, Dialog bleibt offen.

## Spec Change Log

## Design Notes

Im Bettsuche-Modus (hasPerson=false) enthält `variant.beds` eine Liste von Betten geordnet nach `bedAssignments`-Index. Bei Einzelbett-Vorschlag: `variant.beds[0]` ist das einzige Bett → `target_location_id = variant.beds[0].location_id`.

Der `warteplatzCreated`-Branch im aktuellen Code (Z.560): `else if (!bedAssignments.some(a => a.warteplatzCreated))` gibt `false` zurück wenn warteplatzCreated=true → korrekt, nichts wird gebucht. Der neue Branch muss NACH diesem `else if` als zusätzliches `else` eingefügt werden.

## Verification

**Manual checks:**
- Neue AZR-ID in Bettsuche (cross-location) eingeben → "Warteplatz anlegen" → Formular ausfüllen → "Abschließen" → Reservierungen-Seite sollte neue PENDING-Anfrage zeigen.
- `hasPerson`-Modus mit AZR-ID einer Person ohne Bett → Confirm-Dialog → "Verlegungsanfrage senden" → Snackbar-Fehler erscheint.
