# BorderCapControl — Demo-Script

**Zielgruppe:** Fachexpertenrunde (BAMF, Ländervertreter), technische Entscheider  
**Dauer:** ca. 25–30 Minuten  
**Vortragende:** 1 Person (Präsentation + Live-System)

---

## Vor der Demo: Checkliste

```bash
# 1. Services starten und auf Healthchecks warten
docker compose up -d --build
docker compose ps   # alle "healthy"?

# 2. Migrationen ausführen
docker compose exec backend alembic upgrade head

# 3. Demo-Daten einfügen
python3 backend/seeds/demo_data.py

# 4. EU-Gesamtquote setzen (einmalig, via Swagger oder curl)
# → http://localhost:8000/docs → POST /api/system/eu-quota → {"eu_gesamtquote": 500}
# oder:
# curl -X POST http://localhost:8000/api/system/eu-quota \
#   -H "Authorization: Bearer <token>" \
#   -H "Content-Type: application/json" \
#   -d '{"eu_gesamtquote": 500}'

# 5. Frontend starten
cd frontend && npm run dev
# → http://localhost:3000

# 6. Browser-Tab öffnen: http://localhost:3000
# 7. Swagger-Tab öffnen: http://localhost:8000/docs (für PDF-Demo am Ende)
```

**Anmeldedaten bereit haben:**
| Rolle | Benutzername | Passwort |
|-------|-------------|---------|
| System-Admin | `admin_user` | `Admin1234!` |
| Sachbearbeiter | `writer_user` | `Writer1234!` |
| Leser | `reader_user` | `Reader1234!` |

---

## Demo-Ablauf

---

### Block 1 — Kontext & Login (3 Min)

**Sprechen:** *"BorderCapControl ist das Planungswerkzeug für Grenzverfahrens-Einrichtungen
unter der GEAS-Reform. Sachbearbeiter bei BAMF und in den Ländern koordinieren
täglich, welche Betten frei sind, wer wo untergebracht werden kann — und ob wir
innerhalb der EU-vorgegebenen Gesamtkapazität bleiben."*

**Schritt 1:** Browser öffnen → http://localhost:3000

> Keycloak-Login-Seite erscheint automatisch (PKCE-Flow).

**Sprechen:** *"Die Authentifizierung läuft über Keycloak — in Produktion gegen das zentrale
BAMF-IDM. Wir haben drei Rollen: System-Admin, Sachbearbeiter (Writer) und Leser."*

**Schritt 2:** Mit `writer_user` / `Writer1234!` einloggen.

---

### Block 2 — Dashboard: Ampel-Übersicht (4 Min)

> Dashboard zeigt alle 4 Einrichtungen als Kacheln mit Ampelfarbe.

**Sprechen:** *"Das Dashboard zeigt auf einen Blick den Kapazitätsstatus aller Einrichtungen.
Grün = Puffer vorhanden, Gelb = Kontingent ausgeschöpft aber Notbetten noch frei,
Rot = Überkapazität. Das ist die Information, die ein SB morgens als erstes braucht."*

**Schritt 3:** Einrichtungskacheln zeigen — Kontingent, Notbetten, aktuelle Belegung.

**Demo-Aktion:** Swagger öffnen → `POST /api/locations/{id}/occupants` → Für Frankfurt
einige Belegungen erstellen, bis die Ampel auf Gelb springt.

> Alternativ: Seed-Skript hat keine Belegungen → Belegungen live anlegen macht die
> Statusänderung sichtbar.

**Sprechen:** *"Sobald die Belegung das Kontingent erreicht, springt die Kachel auf Gelb —
die Notbetten sind noch verfügbar. Erst wenn auch diese überschritten sind, kommt Rot.
Das ist rechtlich relevant: Rotbelegung bedeutet Verletzung der EU-Kontingentquote."*

---

### Block 3 — Kartenansicht (3 Min)

**Schritt 4:** Menüpunkt "Karte" öffnen.

> Einrichtungen erscheinen als farbige Marker auf der Deutschland-Karte.

**Sprechen:** *"Die Karte nutzt einen lokalen Tile-Server mit Deutschland-MBTiles — keine
externen Abhängigkeiten, keine Datenweitergabe an Google oder OSM-Server.
Jeder Marker zeigt den Ampelstatus; Klick öffnet den Drilldown zur Einrichtung."*

> Falls Tileserver keine Kacheln liefert (ohne MBTiles-Datei):

**Sprechen:** *"Im Fallback-Modus rendert das Backend eine SVG-Karte direkt aus den
Datenbank-Koordinaten — das System ist also auch ohne Internetverbindung und ohne
MBTiles-Datei voll funktionsfähig."*

---

### Block 4 — Einrichtungs-Drilldown & Belegung (5 Min)

**Schritt 5:** Auf "Flughafen Frankfurt" klicken → Drilldown-Ansicht.

> Zeigt Räume, Betten, laufende Belegungen, Reservierungsanfragen.

**Sprechen:** *"Jede Einrichtung hat Räume mit Geschlechtsdesignation — männlich, weiblich,
Familie, divers — und jedes Bett eine feste ID. Das Modell bildet die physische
Realität ab, nicht abstrakte Kapazitätszahlen."*

**Schritt 6:** Neue Belegung anlegen:
- Raum auswählen → Bett auswählen
- AZR-ID eingeben (z.B. `AZR-2024-001`), Alias-ID, Geschlecht, Von/Bis-Datum
- Speichern

**Sprechen:** *"Wir speichern nur das gesetzlich Notwendige: AZR-ID, eine Alias-ID für
interne Kommunikation, Geschlecht und Aufenthaltszeitraum. Kein Name, kein Bild,
keine Adresse — DSGVO-Minimalprinzip."*

**Schritt 7:** Belegungsstand im Dashboard beobachten → Zahl erhöht sich.

---

### Block 5 — Reservierungsworkflow (5 Min)

**Sprechen:** *"Ein zentrales Feature: Einrichtungen können Personen an andere Einrichtungen
überstellen — wenn z.B. Frankfurt voll ist und Passau freie Kapazität hat."*

**Schritt 8:** Als `writer_user` (Frankfurt) → Neue Reservierungsanfrage:
- Ziel-Einrichtung: München
- Person anlegen oder auswählen
- Anfrage absenden

> Status: PENDING

**Schritt 9:** In neuem Tab als zweiter Nutzer (oder in Swagger als admin_user) die
Anfrage von München-Seite bestätigen:
- `PATCH /api/reservations/{id}` mit `status: CONFIRMED`

**Sprechen:** *"Mit der Bestätigung wechselt die rechtliche Verantwortung zur Ziel-Einrichtung.
Das System erzeugt automatisch einen Postkorb-Eintrag bei der Frankfurt-SB:
'Reservierungsanfrage bestätigt'. Die SSE-Verbindung liefert die Benachrichtigung
in Echtzeit — kein Polling, kein manuelles Neuladen."*

---

### Block 6 — Postkorb (Task Inbox) (3 Min)

**Schritt 10:** Menüpunkt "Postkorb" öffnen.

> Zeigt Task-Liste: Reservierungsbestätigung, ggf. automatisch generierte Warnungen.

**Sprechen:** *"Der Postkorb ist einrichtungsbezogen — jede SB sieht nur die eigenen Aufgaben.
Prioritäten sind LOW / MEDIUM / HIGH. Tasks die vom System generiert werden
(Überkapazitäts-Alerts, 12-Wochen-Warnungen) erscheinen automatisch hier."*

**Schritt 11:** Task auf "In Bearbeitung" setzen, dann auf "Erledigt".

**Sprechen:** *"Hintergrundprozesse laufen täglich: um 6 Uhr prüft das System alle Einrichtungen
auf Überkapazität und erstellt Alerts. Belegungen, die in 12 Wochen enden,
bekommen eine Warnung — denn nach 12 Wochen ist das Grenzverfahren rechtlich
abzuschließen. Ein Cleanup-Job entfernt erledigte Tasks nach 30 Tagen automatisch."*

---

### Block 7 — Belegungsvorschlag (3 Min)

**Sprechen:** *"Wenn ein SB eine neue Person zuweisen will, gibt es einen Vorschlags-Assistenten.
Das System sucht passende freie Betten unter Beachtung von Geschlecht,
Familienregeln und Kapazitätsgrenzen."*

**Schritt 12:** `POST /api/suggestions` (via Swagger oder Frontend-Button):
```json
{
  "geschlecht": "M",
  "anzahl_personen": 1,
  "preferred_location_id": "<Frankfurt-ID>"
}
```

> System antwortet mit 1–3 Vorschlagsvarianten (Raum + Bett pro Variante).

**Schritt 13:** Zweiten Aufruf mit Familie:
```json
{
  "geschlecht": "F",
  "anzahl_personen": 3,
  "is_familie": true
}
```

**Sprechen:** *"Bei Familien gilt §43 AsylG: Kinder unter 18 dürfen nicht von Sorgeberechtigten
getrennt werden. Der Solver findet automatisch Familienräume mit ausreichend
freien Betten — oder sucht standortübergreifend, wenn lokal nichts passt.
Der SB entscheidet immer selbst, welchen Vorschlag er annimmt."*

---

### Block 8 — EU-Compliance-Report (PDF) (3 Min)

**Sprechen:** *"Für den EU-Nachweis brauchen wir regelmäßige Berichte: Welche Einrichtung
hat wie viele Betten, wie viele sind belegt, und überschreiten wir die
EU-Gesamtquote für Deutschland?"*

**Schritt 14:** Swagger öffnen → `GET /api/reports/eu-compliance?zeitraum=monat`
→ "Execute" → Response-Body herunterladen.

> PDF öffnen — zeigt: Tabelle aller Einrichtungen mit Ampelfarben, Fußzeile
> mit Gesamt-Kontingent vs. EU-Gesamtquote.

**Sprechen:** *"Das PDF wird serverseitig generiert — keine Abhängigkeit von Browser-Print,
kein JavaScript-PDF. WeasyPrint rendert aus HTML+CSS direkt zu PDF/A.
Drei Zeiträume: laufender Monat, laufendes Quartal, laufendes Jahr.
Dieser Report kann automatisiert oder on-demand exportiert werden."*

**Schritt 15:** Report mit `zeitraum=quartal` zeigen — anderer Zeitraum, gleiche Struktur.

---

### Block 9 — Rollenkonzept (2 Min)

**Schritt 16:** Ausloggen → als `reader_user` einloggen.

> Schreib-Buttons verschwinden. Alles ist lesend.

**Sprechen:** *"Reader sehen alle Daten, können aber nichts ändern — geeignet für
Controlling oder externe Prüfer. Writer sind die operativen SBs.
System-Admins können Einrichtungen anlegen/deaktivieren und die EU-Gesamtquote setzen."*

**Schritt 17:** Als `admin_user` einloggen → EU-Gesamtquote ändern:
- `POST /api/system/eu-quota` mit `{"eu_gesamtquote": 480}`
- Dashboard und Report zeigen jetzt die neue Grenze.

---

### Abschluss (1 Min)

**Sprechen:** *"Das System läuft vollständig lokal — kein Internetzugang während des Betriebs,
keine externen Cloud-Dienste. Alle Daten bleiben auf dem Behörden-Server.
Die Demo-Umgebung startet mit einem einzigen Befehl: `docker compose up --build`.
Die Architektur ist hexagonal und auf den Enterprise-Stack vorbereitet:
Java Spring Boot Modulith mit Angular und Kubernetes-Deployment."*

---

## Schnell-Referenz: Häufige Demo-Aktionen via Swagger

Swagger-UI: http://localhost:8000/docs → "Authorize" → Bearer Token eintragen

| Aktion | Endpoint |
|--------|---------|
| Token holen | `POST http://localhost:8080/realms/bordercapcontrol/protocol/openid-connect/token` |
| EU-Quote setzen | `POST /api/system/eu-quota` |
| Einrichtung anlegen | `POST /api/locations` |
| Belegung anlegen | `POST /api/locations/{id}/occupants` |
| Belegungsvorschlag | `POST /api/suggestions` |
| Reservierungsanfrage | `POST /api/reservations` |
| Reservierung bestätigen | `PATCH /api/reservations/{id}` |
| Postkorb lesen | `GET /api/tasks` |
| PDF-Report | `GET /api/reports/eu-compliance?zeitraum=monat` |

### Token via curl holen

```bash
curl -s -X POST \
  "http://localhost:8080/realms/bordercapcontrol/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password&client_id=bordercapcontrol-frontend&username=writer_user&password=Writer1234!" \
  | python3 -m json.tool | grep access_token
```

---

## Notfall-Optionen

| Problem | Lösung |
|---------|--------|
| Services nicht healthy | `docker compose logs backend` / `docker compose logs keycloak` |
| Keycloak-Login schlägt fehl | `docker compose down -v && docker compose up -d --build` (Realm-Reset) |
| Frontend zeigt weiße Seite | Keycloak noch nicht ready? `docker compose ps` prüfen, dann Browser-Refresh |
| PDF-Download leer | Backend-Log prüfen: `docker compose logs backend` — WeasyPrint-Fehler? |
| Demo-Daten fehlen | `python3 backend/seeds/demo_data.py` erneut ausführen (idempotent) |
