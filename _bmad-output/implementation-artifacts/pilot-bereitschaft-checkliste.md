# BorderCapControl — Pilot-Bereitschaft & Inbetriebnahme-Anleitung

_Erstellt: 2026-06-07 | Git-Tag: v1.0.0-beta_

---

## 1. Gesamtbewertung

**Fachlich:** Das System ist für einen begrenzten Piloten mit eingewiesenen Nutzern geeignet. Alle Kernprozesse (Bettenverwaltung, Verlegungsworkflow, Wartebereich, Audit-Log) sind vollständig und BDD-getestet.

**Sicherheit:** Es gibt **3 Blockers** die vor dem ersten produktiven Login behoben sein müssen. Alle drei sind reine Konfigurationsänderungen — kein Code.

---

## 2. Sicherheits-Blockers (MÜSSEN vor Go-Live behoben werden)

### Blocker 1 — Keycloak Brute-Force-Schutz aktivieren

**Problem:** `bruteForceProtected: false` in `infra/keycloak/realm-export.json`.

**Fix:** Im Keycloak Admin-UI nach dem ersten Start:
1. Realm `bordercapcontrol` → **Realm Settings** → **Security Defenses** → **Brute Force Detection** → aktivieren
2. Empfehlung: Max. Login Failures = 5, Wait Increment = 30s, Max Wait = 900s

Oder in `realm-export.json` vor dem ersten Import setzen:
```json
"bruteForceProtected": true,
"failureFactor": 5,
"maxDeltaTimeSeconds": 43200,
"waitIncrementSeconds": 30
```

### Blocker 2 — SSL Required auf `external` setzen

**Problem:** `sslRequired: none` erlaubt Tokens über unverschlüsseltes HTTP.

**Fix:** Keycloak Admin-UI → Realm Settings → General → **Require SSL** → `external requests`.
Oder in `realm-export.json`: `"sslRequired": "external"`.

**Hinweis:** Wenn der Pilot ausschließlich im internen Netz ohne TLS läuft, kann dieser Blocker vorübergehend zurückgestellt werden — dokumentieren warum.

### Blocker 3 — Demo-Benutzer entfernen / Passwörter als temporär markieren

**Problem:** 14 Test-Benutzer mit bekannten Passwörtern sind im Realm. In Produktion dürfen diese nicht bestehen bleiben.

**Fix:** Alle Demo-Benutzer (`sb_frankfurt`, `loc_admin_muenchen`, etc.) löschen und durch echte Pilotbenutzer ersetzen. Wenn Demo-Benutzer temporär behalten werden:
- Keycloak Admin-UI → User → Credentials → **Temporary** = ON (erzwingt Passwort-Reset beim ersten Login)

---

## 3. Deployment (bereits vorbereitet)

Für Produktion:
```bash
cp .env.prod.example .env.prod
# .env.prod befüllen (alle PFLICHTFELD-Markierungen)

docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.prod up -d
docker compose exec backend alembic upgrade head
```

`docker-compose.prod.yml` schaltet Keycloak auf `start` (Produktionsmodus) und exponiert nur Port 80 nach außen. Alle anderen Services kommunizieren intern.

---

## 4. Stammdaten — Reihenfolge der Erstbefüllung

### Schritt 0: EU-Gesamtquote setzen (System-Admin)

**Ohne diesen Schritt können keine Einrichtungen mit `kontingent > 0` angelegt werden.**

```http
POST /api/system/eu-quota
Authorization: Bearer {system-admin-token}

{"eu_gesamtquote": 5000}
```

Den Wert auf die tatsächliche EU-Gesamtquote Deutschlands setzen. Der Wert kann jederzeit angepasst werden.

---

### Schritt 1: Einrichtungen anlegen (System-Admin oder Location-Admin)

Für jede Piloteinrichtung:

```http
POST /api/locations
Authorization: Bearer {token}

{
  "name": "Ankunftszentrum Frankfurt",
  "kontingent": 200,
  "adresse": "Musterstraße 1, 60311 Frankfurt",
  "valid_from": null,
  "valid_until": null
}
```

**→ Die Antwort enthält die UUID der Einrichtung. Diese UUID sofort notieren — sie wird für Schritt 4 (Keycloak) benötigt.**

```json
{"id": "550e8400-e29b-41d4-a716-446655440000", "name": "Ankunftszentrum Frankfurt", ...}
```

**`kontingent`** = Anzahl EU-quotenrelevanter KONTINGENT-Betten. Darf die `eu_gesamtquote` nicht überschreiten.

---

### Schritt 2: Räume anlegen (Location-Admin der Einrichtung)

**Pflicht für jede Einrichtung: mindestens 1 WARTEBEREICH-Raum**, sonst funktioniert die Bettensuche für neue Personen nicht.

#### 2a — Wartebereich anlegen (zwingend erforderlich)

```http
POST /api/locations/{location_id}/rooms
X-Location-Id: {location_id}
Authorization: Bearer {location-admin-token}

{
  "name": "Wartebereich EG",
  "geschlechts_designation": "M",
  "room_type": "WARTEBEREICH"
}
```

> **Hinweis:** `geschlechts_designation` im Wartebereich ist formal erforderlich, spielt aber keine Rolle — Wartebereich-Betten sind geschlechtsneutral.

#### 2b — Reguläre Schlafräume anlegen

```http
POST /api/locations/{location_id}/rooms
X-Location-Id: {location_id}

{
  "name": "Zimmer 101",
  "geschlechts_designation": "M",
  "room_type": "STANDARD"
}
```

`geschlechts_designation`: `M` (Männer), `W` (Frauen), `D` (Divers/Gemischt), `F` (Familie).

---

### Schritt 3: Betten anlegen (Location-Admin)

#### 3a — KONTINGENT-Betten (EU-quotenrelevant, Standardbelegung)

```http
POST /api/rooms/{room_id}/beds
X-Location-Id: {location_id}

{
  "bett_nummer": "101-A",
  "bett_typ": "KONTINGENT"
}
```

#### 3b — NOTBETT (1-Nacht-Betten, nicht EU-quotenrelevant)

```http
POST /api/rooms/{room_id}/beds
X-Location-Id: {location_id}

{
  "bett_nummer": "N-101",
  "bett_typ": "NOTBETT"
}
```

#### 3c — WARTEPLATZ (im WARTEBEREICH-Raum)

Warteplätze können manuell angelegt werden oder werden vom System automatisch angelegt (wenn der SB im SuggestionWizard "Im Wartebereich einbuchen" klickt und kein freier Platz vorhanden ist).

```http
POST /api/rooms/{wartebereich_room_id}/beds
X-Location-Id: {location_id}

{
  "bett_nummer": "W-1",
  "bett_typ": "WARTEPLATZ"
}
```

**Empfehlung:** Pro Einrichtung 5-10 Warteplätze initial anlegen, um häufige Auto-Anlage zu vermeiden.

---

### Schritt 4: Benutzer in Keycloak anlegen und mit Einrichtung verknüpfen

Dies ist der kritischste manuelle Schritt. Jeder Benutzer (außer `system-admin`) muss mit **genau einer** Einrichtung verknüpft werden.

#### 4a — Benutzer in Keycloak anlegen

Keycloak Admin-UI → Realm `bordercapcontrol` → Users → Add user:
- Username: z.B. `max.mustermann`
- Email: `max.mustermann@behoerde.de`
- ✅ Email verified
- Nach dem Anlegen: Credentials → Set password → **Temporary = ON** (Erstpasswort)

#### 4b — Rolle zuweisen

Role Mappings → Realm roles → eine der vier Rollen:

| Rolle | Verwendung |
|-------|-----------|
| `writer` | Sachbearbeiter — kann belegen, anfragen, einchecken |
| `location-admin` | Einrichtungsleiter — zusätzlich Stammdaten bearbeiten, Räume/Betten verwalten |
| `reader` | Beobachter (Bund/Land) — nur lesen, keine Änderungen |
| `system-admin` | IT-Administrator — alle Einrichtungen, kein X-Location-Id nötig |

#### 4c — Einrichtungs-UUID als Attribut setzen (PFLICHT für alle außer system-admin)

Keycloak Admin-UI → User → Attributes → **Add attribute**:
- Key: `location_id`
- Value: `{UUID der Einrichtung aus Schritt 1}` (z.B. `550e8400-e29b-41d4-a716-446655440000`)

**Ohne diesen Schritt kann der Benutzer keine Daten seiner Einrichtung sehen.**

> **Tipp:** Die UUID einer Einrichtung ist jederzeit abrufbar über `GET /api/locations` (als system-admin) oder steht in der URL beim Öffnen der Einrichtung im Frontend.

---

## 5. Minimale Datenbasis für den Start

Eine Einrichtung ist betriebsbereit wenn:

| # | Was | Warum |
|---|-----|-------|
| ✅ | EU-Gesamtquote gesetzt | Kontingent-Prüfung |
| ✅ | Mindestens 1 Einrichtung angelegt | Basis |
| ✅ | Mindestens 1 WARTEBEREICH-Raum mit ≥1 WARTEPLATZ | SuggestionWizard neue Personen |
| ✅ | Mindestens 1 STANDARD-Raum mit ≥1 KONTINGENT-Bett | Kernbelegung |
| ✅ | Mindestens 1 `location-admin` Benutzer in Keycloak mit korrekter `location_id` | Stammdatenpflege |
| ✅ | Mindestens 1 `writer` Benutzer in Keycloak mit korrekter `location_id` | Tagesbetrieb |
| ✅ | Für Verlegungen: ≥2 Einrichtungen mit je ≥1 STANDARD-Raum | Cross-Location-Workflow |

---

## 6. Was der Pilot NICHT abdeckt (geplante spätere Ausbaustufen)

Diese Features fehlen bewusst und blockieren den Pilot nicht:

| Feature | Status | Auswirkung im Pilot |
|---------|--------|---------------------|
| Kartenansicht (Leaflet + MBTiles) | Placeholder-Tileserver | Karte lädt nicht, Listenansicht funktioniert vollständig |
| EU-Compliance PDF-Export | Nicht implementiert | Reporting manuell |
| Zeitreihenstatistik | Nicht implementiert | Keine Charts, Grundzahlen über API abrufbar |
| SMTP / E-Mail Passwort-Reset | Konfigurationsaufgabe | Admin muss Passwörter manuell zurücksetzen |
| Automatische Validierungsjobs | Nicht implementiert | Manuelle Kontrolle durch Sachbearbeiter |

---

## 7. Bekannte Einschränkungen im Pilotbetrieb

1. **APScheduler Single-Worker**: Der Hintergrundprozessor (12-Wochen-Warnung, Notbett-Warnung) läuft nur korrekt mit einem uvicorn-Worker. `docker-compose.prod.yml` startet standardmäßig mit 1 Worker — **nicht skalieren** ohne Jobstore-Migration.

2. **Keycloak Volume-Reimport**: Änderungen an `realm-export.json` nach dem ersten Start werden ignoriert. Um Realm-Einstellungen zu ändern: Keycloak Admin-UI verwenden. Um komplett neu zu importieren: `docker compose down -v && docker compose up`.

3. **EU-Quota Race Condition**: Bei gleichzeitigen Location-Creates (sehr unwahrscheinlich im Pilot) kann die EU-Quota minimal überschritten werden. Für den Piloten irrelevant.

4. **Location-UUID / Keycloak-Binding**: Die UUID einer neuen Einrichtung wird beim Anlegen generiert und muss dann manuell in Keycloak als `location_id`-Attribut eingetragen werden. Es gibt keinen automatischen Sync. → Prozess dokumentieren und bei jedem neuen Benutzer / jeder neuen Einrichtung einhalten.

---

## 8. Support-Pfad im Pilotbetrieb

| Problem | Erstmaßnahme |
|---------|-------------|
| Benutzer kann sich nicht einloggen | Keycloak Admin-UI → User → Credentials → Reset |
| Benutzer sieht keine Einrichtungsdaten | Keycloak → User Attributes → `location_id` prüfen |
| Bett nicht verfügbar obwohl sichtbar frei | `period_available`-Flag prüfen; Gültigkeitsdaten des Betts/Raums in Stammdaten prüfen |
| Verlegung schlägt fehl | HTTP 409? → Zeitraum prüfen; Person bereits woanders belegt? |
| Warteplatz anlegen schlägt fehl | Kein WARTEBEREICH-Raum an der Einrichtung → Stammdaten anlegen |
| System ist nicht erreichbar | `docker compose ps` + `docker compose logs backend` |
