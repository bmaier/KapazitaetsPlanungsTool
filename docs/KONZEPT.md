# KapzitätsPlanungsTool — Fachliches Konzept & Anforderungen

*Erstellt: 2026-05-26 | Stack: Python/FastAPI + React/MUI (Demo) | Zielstack: Java/Angular (Enterprise)*

---

## 1. Fachlicher Kontext

Das KapzitätsPlanungsTool dient zur Verwaltung von Kapazitäten und Belegungen in **Aufnahmeeinrichtungen** (z. B. Flughäfen, Grenzübergangsstellen). Es bildet den gesamten Lebenszyklus einer Person von der Aufnahme bis zur Verlegung ab und stellt sicher, dass DSGVO-Anforderungen eingehalten werden (keine Namensfelder, nur technische Identifikatoren: AZR-ID, Alias-ID).

### Beteiligte Akteure

| Rolle | Beschreibung |
|-------|-------------|
| `system-admin` | Voller Zugriff auf alle Einrichtungen, kann neue Einrichtungen anlegen |
| `location-admin` | Admin-Zugriff auf eigene Einrichtung (Räume, Betten, Labels) |
| `location-user` | Kann Betten belegen/ausbuchen, Reservierungsanfragen stellen |
| Viewer | Lesezugriff auf Dashboard |

Benutzer erhalten ihre Einrichtungszuordnung als `location_id` User-Attribut in Keycloak, das per JWT übertragen wird.

---

## 2. Domänenmodell

### Entitätshierarchie

```
Einrichtung (Location)
  └── Raum (Room)  [1:N]
        └── Bett (Bed)  [1:N]
              └── Belegung (Occupancy)  [0:N, zeitlich]
```

### Kernentitäten

#### Einrichtung (Location)
- `id`, `name`, `adresse`, `kontingent` (Gesamtkapazität), `notbett_kapazitaet`
- `is_active`, `labels: TEXT[]`
- `lat`, `lon` (Geokoordinaten für Kartenansicht)
- `valid_from`, `valid_until` (Datum ab/bis wann Einrichtung verfügbar ist; NULL = unbegrenzt)

#### Raum (Room)
- `id`, `location_id`, `name`
- `geschlechts_designation` (M/W/D/F) — wird nicht direkt gesetzt, sondern **aus Labels abgeleitet**
- `is_active`, `labels: TEXT[]`
- `valid_from`, `valid_until` (Raum-Gültigkeitsbereich, übersteuert Bett-Verfügbarkeit)

> **Wichtig:** Das Geschlecht eines Raumes ist ausschließlich ein Label, kein Pflichtfeld. Es wird automatisch gesetzt, wenn die erste Person (M oder W) einem Bett in diesem Raum zugewiesen wird. Nur wenn kein Geschlechts-Label gesetzt ist, gilt der Raum als gemischt ("D").

#### Bett (Bed)
- `id`, `room_id`, `bett_nummer`, `bett_typ` (KONTINGENT | NOTBETT)
- `is_active`, `labels: TEXT[]`
- `deaktiviert_ab` (geplante Deaktivierung ab Datum)
- `valid_from` (Verfügbar ab Datum; NULL = sofort)

> **Hinweis:** Doppelbetten (`DOPPEL`) werden in der aktuellen Version nicht unterstützt und ausgeblendet.

#### Belegung (Occupancy)
- `id`, `bed_id`
- `azr_id` (AZR-Identifikationsnummer), `alias_id` (optionaler Alias)
- `geschlecht` (M/W/D)
- `belegung_start`, `belegung_ende` (zeitlicher Belegungszeitraum)
- `labels: TEXT[]` (Hinweis-Labels, nicht verbindlich)

> **DSGVO:** Kein `name`-Feld in der Belegung. Nur technische Identifikatoren.

---

## 3. Fachlogik & Regeln

### Bettbelegung
1. **Zeitraumprüfung:** Bett darf im gewünschten Zeitraum nicht bereits belegt sein.
2. **Geschlechtertrennung:** Standardmäßig müssen belegte Personen im gleichen Raum das gleiche Geschlecht haben (oder Raum ist Gemischt/Familie). Kann vom Benutzer explizit deaktiviert werden (`ignore_gender`-Toggle).
3. **Notbett-Belegungsdauer:** Notbetten haben eine maximale Belegungsdauer (z. B. 3 Wochen). Überschreitung erzeugt Warnung.
4. **12-Wochen-Regel:** Belegungen über 12 Wochen erzeugen eine Warn-Response-Header `X-12W-Warning: true`.
5. **EU-Gesamtquote:** Systemweite Kapazitätsgrenze. Bei `eu_gesamtquote = 0` ist sie unbegrenzt. Prüfung gegen `SUM(belegt)` aller Einrichtungen.

### Gültigkeitsdaten
- Räume und Betten können Gültigkeitsbereiche haben (`valid_from`/`valid_until`).
- `valid_from` = "geplant, noch nicht verfügbar"
- `valid_until` = "läuft ab / abgelaufen"
- **NULL** bedeutet: unbegrenzt aktiv
- Der **Raum** übersteuert die Bett-Verfügbarkeit: Ist ein Raum noch nicht gültig, sind alle Betten darin ebenfalls nicht buchbar.
- Die **Belegungsansicht** dimmt Räume/Betten, die außerhalb des gewählten Datumsfensters liegen, statt sie auszublenden. So bleibt die Planung sichtbar.
- **Einrichtungen**: `valid_from`/`valid_until` werden bei Reservierungssuche beachtet (Betten aus Einrichtungen außerhalb des Gültigkeitszeitraums werden nicht angeboten).

### Ampelstatus
| Auslastung | Status | Farbe |
|-----------|--------|-------|
| < 70 % | GRÜN | grün |
| 70–90 % | GELB | orange |
| ≥ 90 % | ROT | rot |

---

## 4. Labels-System

Labels sind freie Textmarker, die an Räume, Betten und Belegungen angehängt werden können. Sie sind **nicht** enum-basiert, sondern aus einem konfigurierbaren Katalog wählbar.

### Label-Katalog (Auszug)

| Name | Kategorie | Entity-Typen |
|------|-----------|-------------|
| Männer | Geschlecht | ROOM |
| Frauen | Geschlecht | ROOM |
| Gemischt | Geschlecht | ROOM |
| Familienraum | Eignung | ROOM |
| Rollstuhlgerecht | Ausstattung | ROOM |
| Barrierefreiheit | Ausstattung | ROOM, BED |
| Unteres Bett | Position | BED |
| Kinderbett | Typ | BED |
| Kind | Schutz | OCCUPANCY |
| Unbegleitete Minderjährige | Schutz | OCCUPANCY |
| Arabisch/Farsi/Türkisch/... | Sprache | OCCUPANCY |
| Familienmitglied | Gruppe | OCCUPANCY |

### Auto-Label Geschlecht
Wenn eine Person (M/W) einem Bett in einem Raum ohne Geschlechts-Label zugewiesen wird:
- Automatisches Setzen von "Männer" oder "Frauen" als Room-Label via `PATCH /api/rooms/{id}/labels`
- Bei Divers-Zuweisung: kein automatisches Label
- Label ist löschbar, wenn Raum leer (keine aktiven Belegungen)

---

## 5. Reservierungssystem

### Ablauf
1. **Reservierungsanfrage**: Einrichtung A stellt Anfrage für Person X an Einrichtung B
2. **Status PENDING**: Anfrage wartet auf Bestätigung
3. **Bestätigung/Ablehnung** durch Einrichtung B (Target)
4. **Verlegung**: Bei Bestätigung wird Person transferiert (Status TRANSFERRED)

### Suchwizard (SuggestionWizard)
Der Wizard sucht freie Betten für eine Reservierungsanfrage:

**Suchmodi:**
- **Einzelperson**: Geschlecht + 1 Bett
- **Gruppe**: Entweder einheitliches Geschlecht (anzahl) oder gemischte Gruppe (anzahlM + anzahlW + anzahlD getrennt)
- **Familie**: Minderjährige + Erwachsene (M/W), bevorzugt Familienräume, Fallback: geschlechtergetrennte Zuweisung

**Optionen:**
- `cross_location`: Suche in allen aktiven Einrichtungen (eigene Einrichtung zuerst)
- `ignore_gender`: Geschlechtertrennung deaktivieren (explizites Opt-in)
- `label_filter`: Nur Räume mit bestimmten Labels anbieten

**Ergebnis:** Mehrere Varianten werden angeboten, gruppiert nach Einrichtung. Eigene Einrichtung zuerst.

---

## 6. Datenbank-Schema

### Schemas
- `capacity`: Einrichtungen, Räume, Betten
- `persons`: Belegungen (Occupants)
- `reservations`: Reservierungsanfragen, Tasks/Aufgaben
- `alembic_version`: Migrationsversionierung

### Migrationsverlauf (Alembic)
| Migration | Inhalt |
|-----------|--------|
| 0001 | Initiale Schemas |
| 0002 | Kapazitäts-Tabellen (locations, rooms, beds, occupants) |
| 0003 | Reservierungen, Tasks |
| 0004 | Familien-Gruppenfelder |
| 0005 | Grant DELETE auf Tasks |
| 0006 | Labels-Spalten an rooms, beds, occupants |
| 0007 | Locations: labels, lat, lon, valid_from, valid_until; Beds: deaktiviert_ab |
| 0008 | Rooms: valid_from, valid_until; Beds: valid_from |

### Wichtige SQL-Muster
```sql
-- TEXT[] Labels in dynamischem SQL: immer ::TEXT[] cast nötig!
UPDATE capacity.rooms SET labels = :labels::TEXT[] WHERE id = :id

-- Belegungsüberschneidung (halboffenes Intervall):
o.belegung_start < :date_to AND o.belegung_ende > :date_from

-- Gültigkeitscheck Einrichtung:
(l.valid_from IS NULL OR l.valid_from <= :period_start)
AND (l.valid_until IS NULL OR l.valid_until > :period_start)
```

---

## 7. API-Übersicht

### Capacity-Router `/api/`
| Method | Endpoint | Beschreibung |
|--------|----------|-------------|
| GET | `/locations/summary` | Dashboard-Übersicht mit Auslastung, lat/lon |
| POST | `/locations` | Neue Einrichtung anlegen |
| PATCH | `/locations/{id}` | Stammdaten aktualisieren (name, adresse, kontingent, labels, lat, lon, valid_from/until) |
| GET | `/locations/{id}/bed-status` | Bett-Belegungsstatus inkl. room/bed valid_from/until |
| GET | `/locations/{id}/rooms` | Raumliste (optional inkl. inaktiver) |
| POST | `/locations/{id}/rooms` | Raum anlegen (geschlechts_designation default='D') |
| DELETE | `/rooms/{id}` | Raum deaktivieren |
| POST | `/rooms/{id}/activate` | Raum reaktivieren (optional mit valid_from) |
| PATCH | `/rooms/{id}/validity` | Gültigkeitsdaten setzen |
| PATCH | `/rooms/{id}/labels` | Raum-Labels setzen (::TEXT[] cast) |
| POST | `/rooms/{id}/beds` | Bett anlegen (KONTINGENT oder NOTBETT) |
| DELETE | `/beds/{id}` | Bett deaktivieren |
| PATCH | `/beds/{id}/deactivate` | Bett mit Deaktivierungsdatum markieren |
| PATCH | `/beds/{id}/labels` | Bett-Labels setzen |
| POST | `/beds/{id}/occupancy` | Bett belegen (antwortet mit X-12W-Warning Header) |
| DELETE | `/beds/{id}/occupancy/{occ_id}` | Belegung beenden |
| PATCH | `/occupancy/{id}/labels` | Belegungs-Labels setzen |
| GET | `/labels/catalog` | Label-Katalog für UI |
| GET/POST | `/system/eu-quota` | EU-Gesamtquote lesen/setzen |

### Suggestions-Router `/api/suggestions/`
| Method | Endpoint | Beschreibung |
|--------|----------|-------------|
| POST | `/` | Bett-Vorschläge berechnen |
| POST | `/{id}/accept` | Variante bestätigen → Reservierungsanfrage erstellen |
| POST | `/{id}/reject` | Anfrage ablehnen mit Begründung |

### SuggestionRequest-Parameter
```json
{
  "geschlecht": "M|W|D",
  "anzahl": 1,
  "belegung_start": "2026-05-26",
  "belegung_ende": "2026-06-09",
  "cross_location": false,
  "familien_modus": false,
  "minderjaehrige": 0,
  "label_filter": [],
  "maenner_anzahl": 0,
  "frauen_anzahl": 0,
  "divers_anzahl": 0,
  "ignore_gender": false
}
```

---

## 8. Frontend-Architektur

### Technologie
- React 18 + TypeScript + Vite
- Material UI 5 (MUI)
- React Router 6
- React-Leaflet + OpenStreetMap (Kartenansicht)
- Keycloak-JS (PKCE/JWT Auth)

### Wichtige Komponenten

| Komponente | Beschreibung |
|-----------|-------------|
| `Dashboard` | Grid- + Kartenansicht aller Einrichtungen mit Ampelstatus |
| `Drilldown` | Detailansicht einer Einrichtung: Bett-Grid, Belegen, Stammdaten, Raum-Management |
| `SuggestionWizard` | 3-Schritt-Wizard: Suche → Variante wählen → Bestätigen |
| `Reservations` | Liste aller eigenen Reservierungsanfragen |
| `TaskInbox` | Eingehende Reservierungsanfragen bestätigen/ablehnen |
| `LabelChips` | Wiederverwendbare Label-Auswahl-Komponente (entityId='new' = nur lokal) |
| `MapView` | Leaflet-Karte mit Marker pro Einrichtung (nutzt lat/lon aus DB) |

### `deriveRoomGender(room)` — Kernlogik
```typescript
function deriveRoomGender(room: RoomStatus): string {
  const labels = room.labels ?? []
  if (labels.includes('Männer')) return 'M'
  if (labels.includes('Frauen')) return 'W'
  if (labels.includes('Familie') || labels.includes('Familienraum')) return 'D'
  const occupied = room.beds.filter((b) => b.status === 'BELEGT' && b.occ_geschlecht)
  if (occupied.length === 0) return 'D'
  const genders = [...new Set(occupied.map((b) => b.occ_geschlecht!))]
  return genders.length === 1 ? genders[0] : 'D'
}
```

### Auth-Flow
1. Keycloak PKCE-Auth → JWT-Token
2. Alle API-Calls: `Authorization: Bearer <token>` + `X-Location-Id: <locationId>`
3. Backend liest `location_id` aus `X-Location-Id`-Header oder JWT-Token-Claim

---

## 9. Technische Besonderheiten & Fallstricke

### TEXT[] Cast in asyncpg
Bei dynamisch gebauten `text()`-SQL-Queries in SQLAlchemy mit asyncpg:
```python
# FALSCH — funktioniert nicht ohne Cast:
text("UPDATE t SET labels = :labels WHERE id = :id")

# RICHTIG:
text("UPDATE t SET labels = :labels::TEXT[] WHERE id = :id")
```

### BedType Enum
Nur `KONTINGENT` und `NOTBETT` sind gültige Bett-Typen. `STANDARD` und `DOPPEL` existieren nicht.

### LabelChips — entityId='new'
Wenn `entityId='new'`: Chips arbeiten nur lokal (kein API-Call). Speichern erfolgt über übergeordneten Form-Submit.
Wenn `entityId=<uuid>`: Automatischer PATCH an `/api/{entityType}/{id}/labels`.

### Volume-Mount
Das Backend-Verzeichnis `./backend/src` ist direkt in den Container gemountet. Dateiänderungen werden sofort hot-reloaded. **Niemals `podman cp` für Backend-Source-Dateien verwenden** (verursacht doppelten Reload).

### Alembic in Container
```bash
podman exec kapzitaetsplanungstool_backend_1 sh -c "cd /home/appuser/app && python3 -m alembic upgrade head"
```

---

## 10. Bekannte Einschränkungen

1. Doppelbetten: Aktuell deaktiviert (kein `DOPPEL` BedType in der Enum)
2. Geschlechts-Label löschbar nur wenn Raum komplett leer (prüfung im Frontend noch nicht implementiert)
3. Bed valid_from: Bereits in DB + Backend, aber kein UI zum Setzen (noch zu implementieren)
4. Room valid_from/valid_until: Backend + DB vorhanden, aber nur Anzeige im Bed-Grid; kein UI zum Bearbeiten im Raum-Management (noch zu implementieren)

---

## 11. Anforderungen für Reimplementierung (Enterprise Stack)

Beim Aufbau mit Java/Spring Boot + Angular sind folgende Punkte besonders zu beachten:

1. **Geschlecht als Label** — nicht als Pflichtfeld, automatisch aus erster Belegung
2. **TEXT[] als PostgreSQL-Array** — bei Hibernate/JPA: `@Type(type = "list-array")` oder JPA 2.1 `@Convert`
3. **Zeitraumüberschneidung** — halboffenes Intervall: `start < date_to AND end > date_from`
4. **EU-Quota** — Singleton in `system_settings`-Tabelle, `eu_gesamtquote = 0` = unbegrenzt
5. **12-Wochen-Header** — Response-Header `X-12W-Warning: true` für lange Belegungen
6. **DSGVO** — Kein `name` in Occupancy; nur `azr_id` (technisch) + `alias_id` (optional)
7. **Gültigkeitsdaten** — `valid_from IS NULL` = immer gültig; `valid_until IS NULL` = kein Ablauf
8. **Keycloak-Attribute** — `location_id` als User-Attribut, wird per JWT-Claim übertragen
9. **asyncpg → JDBC**: TEXT[]-Spalten erfordern expliziten Type-Mapping
10. **Suggestions-Algorithmus** — Varianten-Berechnung mit Greedy-Raum-Packing (Betten aus gleichen Räumen bevorzugen)
