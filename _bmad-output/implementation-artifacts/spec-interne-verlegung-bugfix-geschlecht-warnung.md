---
title: 'Interne Verlegung: Bugfix + Geschlecht-Warnpflicht'
type: 'bugfix'
created: '2026-06-04'
status: 'done'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** (1) `handleVerlegen` zeigt bei jedem Fehler nur "Verlegen fehlgeschlagen." — die eigentliche Ursache (z.B. 404 nach BDD-Testlauf, der alle Demo-Daten löscht) bleibt unsichtbar. (2) Der `after_scenario`-Hook in `tests/environment.py` löscht **alle** Capacity-Daten inkl. Demo-Daten — nach einem Testlauf sieht der Browser veraltete Bett-IDs, POST/DELETE schlagen mit 404 fehl. (3) Beim Verlegen in ein Bett eines Raums mit anderer `geschlechts_designation` als die Person erscheint keine Warnung — das Verlegen wird lautlos durchgeführt ohne Begründung und Audit-Eintrag.

**Approach:** (1) `catch`-Block in `handleVerlegen` auf `extractApiError` umstellen; bei 404 explizite Meldung "Bett nicht mehr verfügbar — bitte Seite aktualisieren". (2) `after_scenario` auf test-spezifische UUIDs (uuid5-Prefix `warteplatz-test::`) einschränken statt alles zu löschen. (3) Neuer Bestätigungs-Dialog in `handleVerlegen`: wenn Ziel-Raum `geschlechts_designation != 'D'` UND `!= src.occ_geschlecht` → Dialog mit Pflichtfeld "Begründung"; bei Bestätigung POST `/api/beds/{id}/occupancy` mit Body-Feld `geschlecht_mismatch_grund`; Backend schreibt Audit-Event `OCCUPANCY_GESCHLECHT_MISMATCH`.

## Boundaries & Constraints

**Always:**
- Warnung nur bei echtem Mismatch: Person-Geschlecht ≠ Raum-Designation. Wenn Raum-Designation = 'D' (Wartebereich/Gemischt) → keine Warnung.
- `geschlecht_mismatch_grund` ist Pflichtfeld im Dialog (min 1 Zeichen) — User kann nicht ohne Begründung bestätigen.
- Das Audit-Event enthält: `azr_id`, `bed_id`, `room_name`, `geschlecht_person`, `geschlecht_raum`, `grund`.
- NOTBETT- und WARTEPLATZ-Betten unterliegen derselben Prüfung (falls Raum eine Gender-Designation ≠ D hat).
- `after_scenario` darf nur noch Daten löschen, die von **diesem Test** angelegt wurden — erkennbar an den uuid5-basierten IDs aus `_loc_uuid`, `_room_uuid`, `_bed_uuid`.

**Ask First:** — keine offenen Fragen.

**Never:**
- Kein neues Backend-Endpoint. Kein neues DB-Schema (audit.events besteht).
- Kein automatisches Ablehnen des Verlegens bei Mismatch — Override durch Nutzer bleibt möglich.
- `OccupancyCreate.geschlecht_mismatch_grund` wird **nicht** validiert / erzwungen durch Backend — nur Frontend-seitige Pflicht.

## I/O & Edge-Case Matrix

| Szenario | Zustand | Erwartetes Verhalten |
|----------|---------|---------------------|
| Verlegen, gleiche Designation | Person M → Männerraum (M) | Kein Dialog, direkte Verlegung |
| Verlegen, Mismatch | Person M → Frauenraum (W) | Bestätigungs-Dialog mit Begründungs-Pflichtfeld erscheint |
| Verlegen, neutrale Designation | Person M/W → Wartebereich (D) | Kein Dialog, direkte Verlegung |
| Bestätigung ohne Begründung | Dialog offen, Feld leer | "Verlegen bestätigen" bleibt disabled |
| Bestätigung mit Begründung | Grund eingegeben, Klick | POST mit `geschlecht_mismatch_grund`, Audit-Event geschrieben |
| 404-Fehler | Bett nicht mehr in DB | Snackbar: "Bett nicht mehr verfügbar — bitte Seite aktualisieren." |
| Sonstiger Fehler | API-Fehler | Snackbar: `extractApiError(err)` |

</frozen-after-approval>

## Code Map

- `frontend/src/pages/Drilldown.tsx:793` — `handleVerlegen`: catch-Block + Mismatch-Prüfung + Mismatch-Grund mitschicken
- `frontend/src/pages/Drilldown.tsx:1365` — Intern-Verlegen-Dialog: neuer Bestätigungs-Sub-Dialog mit Begründungsfeld
- `frontend/src/pages/Drilldown.tsx:384` — State-Deklarationen: neue States für Mismatch-Dialog
- `backend/src/api/capacity/schemas.py:95` — `OccupancyCreate`: optionales Feld `geschlecht_mismatch_grund`
- `backend/src/api/capacity/router.py:1033` — `create_occupancy`: Audit-Event wenn `geschlecht_mismatch_grund` gesetzt
- `tests/environment.py` — `after_scenario`: nur test-spezifische UUIDs löschen

## Tasks & Acceptance

**Execution:**
- [ ] `backend/src/api/capacity/schemas.py` — `OccupancyCreate` um `geschlecht_mismatch_grund: Optional[str] = None` ergänzen — ermöglicht Mismatch-Begründung im Request-Body
- [ ] `backend/src/api/capacity/router.py` — In `create_occupancy`: nach `occ_repo.create()` prüfen ob `body.geschlecht_mismatch_grund` gesetzt ist → wenn ja, `await session.execute(text("INSERT INTO audit.events (event_type, payload) VALUES ('OCCUPANCY_GESCHLECHT_MISMATCH', :p)"), {"p": json.dumps({...})})` mit Payload `{azr_id, bed_id: str(bed_id), mismatch_grund, geschlecht_person: body.geschlecht.value, erstellt_von: user.sub}` — protokolliert Override mit Begründung
- [ ] `frontend/src/pages/Drilldown.tsx` — Neue State-Variablen: `verlegenMismatch: boolean` + `verlegenMismatchGrund: string` — für Bestätigungs-Dialog
- [ ] `frontend/src/pages/Drilldown.tsx` — In `handleVerlegen`: vor dem `try`-Block prüfen ob `targetBedInfo?.geschlecht && targetBedInfo.geschlecht !== 'D' && targetBedInfo.geschlecht !== (src.occ_geschlecht ?? 'D')` → wenn ja und `!verlegenMismatch` → `setVerlegenMismatch(true); setVerlegenSaving(false); return` — stoppt den Flow und öffnet Bestätigungs-Dialog
- [ ] `frontend/src/pages/Drilldown.tsx` — In `handleVerlegen` `catch`-Block: statt hardcodiertem Text `if ((err as {status?:number}).status === 404) { setSnackbar({..., message: 'Bett nicht mehr verfügbar — bitte Seite aktualisieren.'}) } else { setSnackbar({..., message: extractApiError(err)}) }` — zeigt verwertbare Fehlermeldung
- [ ] `frontend/src/pages/Drilldown.tsx` — Im Intern-Verlegen-Dialog (nach dem Betten-Select): wenn `verlegenMismatch` → Bestätigungs-Sub-Panel mit Alert (Geschlecht-Warnung) + TextField `label="Begründung *"` + Button "Override bestätigen" (disabled wenn `!verlegenMismatchGrund.trim()`) + Button "Abbrechen" → bei Override-Klick: `handleVerlegen()` erneut aufrufen mit `verlegenMismatch` gesetzt (damit zweiter Aufruf nicht wieder blockt) und `geschlecht_mismatch_grund` im POST mitschicken — wenn `!verlegenMismatch` → normaler Betten-Select ohne Sub-Panel
- [ ] `frontend/src/pages/Drilldown.tsx` — POST-Payload in `handleVerlegen` um `geschlecht_mismatch_grund: verlegenMismatch ? verlegenMismatchGrund.trim() : undefined` erweitern
- [ ] `frontend/src/pages/Drilldown.tsx` — Nach erfolgreichem Verlegen `setVerlegenMismatch(false)` und `setVerlegenMismatchGrund('')` zurücksetzen
- [ ] `tests/environment.py` — `after_scenario`: statt `DELETE FROM capacity.locations` (löscht alles) nur Test-UUIDs löschen: `DELETE FROM capacity.locations WHERE id IN (SELECT id FROM capacity.locations WHERE name LIKE '%-test-%' OR id IN (<uuid5-Liste der in context.loc_map gespeicherten IDs>)` — nutze `getattr(context, 'loc_map', {}).values()` als Whitelist — schützt Demo-Daten

**Acceptance Criteria:**
- Given Person M wird in Männerraum (M) verlegt, when "Verlegen bestätigen" geklickt, then direkte Verlegung ohne Dialog.
- Given Person M wird in Frauenraum (W) verlegt, when "Verlegen bestätigen" geklickt, then erscheint Bestätigungs-Panel mit Begründungsfeld; Button "Override bestätigen" ist disabled solange Feld leer.
- Given Begründung eingegeben, when "Override bestätigen" geklickt, then POST mit `geschlecht_mismatch_grund` und Audit-Event `OCCUPANCY_GESCHLECHT_MISMATCH` in DB.
- Given Person verlegen auf WARTEBEREICH-Bett (geschlecht='D'), when "Verlegen bestätigen", then kein Bestätigungs-Panel.
- Given Bett nach Datenwipe nicht mehr in DB, when intern verlegen, then Snackbar "Bett nicht mehr verfügbar — bitte Seite aktualisieren." (statt "Verlegen fehlgeschlagen.").
- Given BDD-Tests laufen, when `after_scenario` läuft, then Demo-Daten von Flughafen-Einrichtungen bleiben erhalten.

## Design Notes

Der Mismatch-Check `targetBedInfo?.geschlecht !== (src.occ_geschlecht ?? 'D')` nutzt `'D'` als Fallback für das Personen-Geschlecht, um einen falschen Warn-Trigger zu vermeiden wenn `occ_geschlecht` fehlt (unwahrscheinlich bei BELEGT-Betten, aber defensiv).

`verlegenMismatch` ist ein State-Flag das anzeigt "User hat bereits den Mismatch-Dialog gesehen und bestätigt". Beim zweiten `handleVerlegen`-Aufruf (nach Override-Klick) ist `verlegenMismatch=true` → der Guard wird übersprungen → POST läuft durch.

`after_scenario` Clean-up-Strategie: `context.loc_map` enthält alle vom Test angelegten Location-IDs. Über `ON DELETE CASCADE` werden zugehörige Rooms, Beds, Occupants automatisch mitgelöscht. Nur diese IDs löschen, nicht alle.

## Verification

**Manual checks:**
- Intern verlegen: Person M → Männerraum → kein Dialog, Erfolg.
- Intern verlegen: Person M → Frauenraum → Bestätigungs-Panel, Begründung eingeben → Erfolg + DB-Check `SELECT * FROM audit.events WHERE event_type='OCCUPANCY_GESCHLECHT_MISMATCH' ORDER BY created_at DESC LIMIT 1`.
- BDD-Test: `behave tests/features/warteplatz_auto_flow.feature` → Demo-Daten bleiben danach erhalten (Flughafen Frankfurt hat noch Betten).
