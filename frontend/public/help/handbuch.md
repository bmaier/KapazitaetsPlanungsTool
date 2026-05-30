# BAMF BorderCapControl — Benutzerhandbuch

---

## 1. Grundkonzepte

### 1.1 Einrichtungen und Kapazitäten

Das System verwaltet Kapazitäten in Grenzeinrichtungen (z. B. Flughäfen, Grenzübergänge). Jede Einrichtung hat:

- **Kontingent** — Anzahl der EU-quotenrelevanten Plätze
- **Notbett-Kapazität** — zusätzliche temporäre Plätze (nicht EU-quotenrelevant)
- **Räume** mit Geschlechtsdesignation
- **Betten** mit eindeutiger Nummer und festem Typ

### 1.2 Betttypen

**Kontingentbett** — reguläres Bett, das zur deutschen EU-Gesamtkapazität zählt. Jede Belegung startet einen 12-Wochen-Timer.

**Notbett** — temporäre Unterbringung für max. 1 Nacht (einmalig um 1 Tag verlängerbar). Notbetten zählen **nicht** zur EU-Quota und starten keinen 12-Wochen-Timer.

**Warteplatz** — Platz im Wartebereich für Personen bei Ankunft, die noch keinem regulären Bett zugewiesen wurden. Zählt nicht zur EU-Quota.

### 1.3 Raumtypen

**Standardraum** — regulärer Schlafraum mit Kontingentbetten und/oder Notbetten.

**Wartebereich** — spezieller Raumtyp für kurzfristige Aufnahme bei Ankunft. Erscheint in der Einrichtungsdetail-Ansicht mit orangem Rahmen oberhalb der Standardräume. Ermöglicht Mehrfachauswahl für Gruppenverlegung.

### 1.4 Der 12-Wochen-Timer

Jede Belegung eines Kontingentbetts läuft maximal 12 Wochen (84 Tage). Eine Überschreitung wird beim Belegen durch eine Warnung angezeigt. Das System speichert die Belegung, aber das EU-Berichtswesen zeigt die Überschreitung. Eine 12-Wochen-Warnung erscheint auch als Aufgabe im Postkorb.

### 1.5 Geschlechtsdesignation von Räumen

Räume werden durch Labels als Männer-, Frauen- oder Familienraum gekennzeichnet. Das Geschlechts-Label schützt vor falschen Belegungen. Es kann erst entfernt werden, wenn alle Betten des Raums leer sind.

### 1.6 AZR-ID und Alias-ID

**AZR-ID** — die Ausländerzentralregister-Nummer der Person. Keine Personennamen werden gespeichert (DSGVO-konform). Format z. B.: `AZR-2024-FFM-M01`.

**Alias-ID** — optionale einrichtungsinterne Kennung für die Person. Erleichtert die Suche ohne die vollständige AZR-ID.

### 1.7 Bett-Status im Überblick

| Status | Farbe | Bedeutung |
|--------|-------|-----------|
| FREI | Grün | Bett kann belegt werden |
| BELEGT | Rot | Bett hat eine aktive Belegung |
| VORGEMERKT | Lila | Bett für bestätigte Reservierung reserviert — Person noch unterwegs |

### 1.8 Rollen und Berechtigungen

| Rolle | Berechtigungen |
|-------|----------------|
| `reader` | Nur Lesen (alle Einrichtungen) |
| `writer` | Lesen + Belegungen verwalten + Verlegungsanfragen |
| `location-admin` | Alles des `writer` + Räume/Betten/Einrichtungsstammdaten |
| `system-admin` | Voller Zugriff auf alle Einrichtungen und alle Anfragen |

---

## 2. Dashboard — Kapazitätsübersicht

### 2.1 Ampelfarben

Die Farbe jeder Einrichtungskachel zeigt den Belegungsgrad:

- **Grün** — unter 70 % belegt — Kapazität verfügbar
- **Gelb** — 70–90 % belegt — Kapazität begrenzt
- **Rot** — über 90 % belegt — Kapazität kritisch

### 2.2 Rasteransicht vs. Kartenansicht

**Rasteransicht** — zeigt alle Einrichtungen als Kacheln mit Kennzahlen.

**Kartenansicht** — zeigt Einrichtungen auf einer Karte mit farbigen Markierungen entsprechend der Ampelfarbe. Klick auf eine Markierung öffnet die Einrichtungsdetails.

### 2.3 Schnellzugriff Verlegungsanfragen

Laufende Verlegungsanfragen Ihrer Einrichtung (eingehend und ausgehend) werden als kleine Chips unter der Hauptüberschrift angezeigt. Ein Klick öffnet die vollständige Verlegungsansicht.

### 2.4 Neue Einrichtung anlegen (Administratoren)

Der Button „Neue Einrichtung" erscheint nur für Nutzer mit Administratorrechten. Pflichtfelder: Name und Kontingent. Adresse und Notbett-Kapazität sind optional. Nach dem Anlegen können Räume, Betten und ein Wartebereich im Einrichtungsdetail verwaltet werden.

---

## 3. Einrichtungsdetail — Betten verwalten

### 3.1 Belegungszeitraum einstellen

Der Datumsfilter oben in der Ansicht steuert, für welchen Zeitraum der Belegungsstand geprüft wird. Standard: heute bis +14 Tage. Ein Bett erscheint als **belegt** (rot), wenn der gewählte Zeitraum mit einer vorhandenen Belegung überlappt. Mit „+90 Tage" können Sie die Vorausplanung vergrößern.

### 3.2 Bett belegen (freies Bett)

1. Klicken Sie auf ein **grünes** Bett
2. Tragen Sie die **AZR-ID** ein (Pflicht)
3. Optional: **Alias-ID** eingeben
4. Bei Räumen ohne feste Geschlechtsdesignation: Geschlecht auswählen
5. Belegungsbeginn und -ende einstellen
6. Optionale Hinweis-Labels zur Person auswählen
7. „Bett belegen" klicken

Das System setzt automatisch ein Geschlechts-Label am Raum, wenn noch keins vorhanden ist und ein Bett mit M oder W belegt wird.

### 3.3 Belegung verwalten (belegtes Bett anklicken)

Ein Klick auf ein **rotes** Bett öffnet die Verwaltungsansicht:

- **Ausbuchen** — beendet die Belegung. Ein Ausbuche-Grund ist verpflichtend (wird im Audit-Log gespeichert).
- **Intern verlegen** — öffnet eine Liste freier Betten und Warteplätze in derselben Einrichtung.
- **Zu anderer Einrichtung verlegen** — öffnet die Bettsuche mit vorausgefüllten Personendaten.

### 3.4 Person intern verlegen

1. Klicken Sie auf das **rote** (belegte) Bett
2. Wählen Sie „Intern verlegen (anderes Bett in dieser Einrichtung)"
3. Wählen Sie das Zielbett oder den Warteplatz aus der Liste
4. Klicken Sie „Verlegen bestätigen"

Das System überträgt alle Belegungsdaten automatisch und gibt das alte Bett frei. Warteplätze erscheinen orange gekennzeichnet in der Auswahl.

### 3.5 Person zu anderer Einrichtung verlegen

1. Klicken Sie auf das **rote** Bett der Person
2. Wählen Sie „Zu anderer Einrichtung verlegen (Verlegungsanfrage)"
3. Die Bettsuche öffnet sich mit den Personendaten vorausgefüllt
4. Wählen Sie die Zieleinrichtung und den Zeitraum
5. Anfrage absenden — die Zieleinrichtung muss die Anfrage bestätigen

Erst nach Bestätigung durch die Zieleinrichtung und dem Einchecken (Transfer) ist die Person dort aktiv.

### 3.6 Person ausbuchen

1. Klicken Sie auf das **rote** Bett
2. Wählen Sie „Ausbuchen (Belegung beenden)"
3. Tragen Sie einen **Grund** ein (Pflichtfeld — wird im Audit-Log gespeichert)
4. Klicken Sie „Ausbuchen"

Das Bett ist anschließend sofort wieder frei (grün).

### 3.7 Vorgemerkte Betten (lila)

Lila Betten sind für eine bestätigte Verlegungsanfrage reserviert. Die Person ist noch nicht physisch eingecheckt. Das Bett kann nicht direkt belegt werden. Ein Klick zeigt die zugehörige Anfrage. Das Bett wird zur aktiven Belegung, wenn die Person eingecheckt wird.

### 3.8 Notbetten

Notbetten erscheinen in einem eigenen Abschnitt mit orangem Rand:
- Max. 1 Nacht Belegung
- Einmalige Verlängerung um 1 Tag möglich
- Tägliche Postkorb-Erinnerung bei belegten Notbetten
- Keine EU-Quota-Relevanz

### 3.9 Wartebereich

Der Wartebereich erscheint ganz oben in der Einrichtungsdetail-Ansicht. Warteplätze sind für Personen vorgesehen, die gerade eingetroffen sind und noch auf ein reguläres Bett warten.

**Einzelne Person verlegen:** Belegten Warteplatz anklicken → „Zu anderer Einrichtung verlegen" oder „Intern verlegen".

**Gruppe verlegen (Mehrfachauswahl):**
1. Button **„Gruppe auswählen"** aktivieren
2. Belegte Warteplätze anklicken (lila = ausgewählt)
3. **„X Personen verlegen"** klicken
4. Die Bettsuche öffnet sich für alle ausgewählten Personen gleichzeitig

---

## 4. Verlegungsworkflow

### 4.1 Statusübersicht

| Status | Bedeutung | Nächste Aktion |
|--------|-----------|----------------|
| Ausstehend | Anfrage gestellt | Zieleinrichtung: bestätigen oder ablehnen |
| Bestätigt | Bett vorgemerkt | Zieleinrichtung: Person einchecken |
| Abgelehnt | Keine Kapazität | Neue Anfrage stellen |
| Storniert | Aufgehoben | — |
| Verlegt | Eingecheckt | Belegung aktiv in Zieleinrichtung |

### 4.2 Neue Verlegungsanfrage stellen

1. Navigieren Sie zu **Verlegungsanfragen** → „Neue Verlegungsanfrage" oder nutzen Sie die **Bettsuche**
2. Wählen Sie die Zieleinrichtung
3. Füllen Sie Pflichtfelder aus: AZR-ID, Geschlecht, Geburtsjahr, Herkunftsland, Zeitraum
4. Absenden

Die Anfrage erscheint sofort im Postkorb der Zieleinrichtung.

### 4.3 Eingehende Anfrage bestätigen

1. Postkorb → Tab „Zu beantworten" → „Aufnahme bestätigen"
2. Dialog öffnet sich: freie Betten im Anfragezeitraum werden aufgelistet
3. Ein vorgeschlagenes Bett (lila umrandet) ist vorausgewählt — Sie können ein anderes wählen
4. Labels der Person können im Dialog eingesehen und angepasst werden
5. „Bestätigen & Bett vormerken" klicken

Das Bett erscheint danach als **vorgemerkt (lila)** in der Einrichtungsdetail-Ansicht.

### 4.4 Eingehende Anfrage ablehnen

1. Postkorb → Tab „Zu beantworten" → „Ablehnen"
2. Ablehnungsgrund eingeben
3. Bestätigen

Die anfragende Einrichtung sieht den Status „Abgelehnt".

### 4.5 Person einchecken (Transfer)

Wenn die Person physisch angekommen ist:

1. Postkorb → Tab „Zu beantworten" oder Verlegungsanfragen → Tab „Aktionen erforderlich"
2. Zeile mit Status „Bestätigt" → Button **„Einchecken"**
3. Status wechselt auf „Verlegt" — Belegung wird in der Zieleinrichtung aktiv

### 4.6 Anfrage stornieren

Eine Anfrage kann von der anfragenden Seite storniert werden, solange sie noch nicht den Status „Verlegt" hat.

---

## 5. Bettsuche (Reservierungsassistent)

### 5.1 Suchmodi

Die Bettsuche unterstützt drei Modi:

**Einzelperson** — sucht ein einzelnes Bett für eine Person mit bekanntem Geschlecht.

**Gruppe** — sucht Betten für mehrere Personen. Anzahl nach Geschlecht (M/W/D) angeben. Das System findet Einrichtungen mit ausreichend freien Betten in passenden Räumen.

**Familie / Minderjährige** — für gemischte Gruppen aus Erwachsenen und Kindern. Erwachsene Männer, Frauen und Kinderzahl getrennt angeben. Das System sucht nach Familienräumen.

### 5.2 Suchoptionen

- **Einrichtungsübergreifend** — durchsucht alle Einrichtungen (Standard bei Verlegung von Warteplatz)
- **Geschlecht ignorieren** — zeigt auch Räume ohne passende Designation
- **Raum-Labels** — filtert auf Räume mit bestimmten Labels

### 5.3 Gruppenverlegung aus Wartebereich

Wenn mehrere Personen im Wartebereich ausgewählt wurden, öffnet die Bettsuche automatisch im Gruppenmodus mit allen Personen vorausgefüllt. Nach Bestätigung wird für jede Person eine eigene Anfrage gestellt.

---

## 6. Postkorb

### 6.1 Aufgabentypen

**Eingehende Verlegungsanfragen** — andere Einrichtungen bitten um Aufnahme einer Person.

**Bestätigte Anfragen (Einchecken ausstehend)** — Person hat eine bestätigte Zusage, muss noch physisch einchecken.

**Systemaufgaben** — automatisch generierte Hinweise:
- Notbett-Erinnerung: tägliche Meldung bei belegten Notbetten
- 12-Wochen-Warnung: Belegung überschreitet die EU-Quota-Frist

**Ausgehende Anfragen (Tab „Meine Anfragen")** — Anfragen, die Sie gestellt haben.

### 6.2 Aufgaben als erledigt markieren

Für eigenständige Systemaufgaben erscheint der Button **„Als erledigt markieren"**. Reservierungsbezogene Aufgaben werden automatisch archiviert, wenn die Reservierung abgeschlossen, abgelehnt oder storniert wird.

### 6.3 Zur Belegung einer Person springen

Enthält eine Aufgabe eine AZR-ID, erscheint der Button **„Zur Belegung: AZR-…"**. Klicken öffnet direkt das Einrichtungsdetail mit dem Bett der Person hervorgehoben.

### 6.4 Prioritätsstufen

| Priorität | Farbe | Typische Ursache |
|-----------|-------|-----------------|
| Dringend | Rot | Eingehende Verlegungsanfrage |
| Mittel | Orange | Ausgehende offene Anfrage |
| Niedrig | Grün | Systemhinweis, archivierbar |

---

## 7. Bettendaten pflegen (Administratoren)

Nur Nutzer mit der Rolle `location-admin` oder `system-admin` haben Zugriff auf die Raumverwaltung.

### 7.1 Räume anlegen

1. Einrichtungsdetail → Stift-Symbol → Tab „Räume & Betten"
2. Scrollen Sie nach unten zu „Neuen Raum anlegen"
3. Raumnamen eingeben und Typ wählen: **Standard** oder **Wartebereich**
4. „Raum anlegen" klicken

### 7.2 Betten hinzufügen

1. Im Tab „Räume & Betten" → beim gewünschten Raum auf „Bett" klicken
2. Bett-Nummer eingeben (z. B. „B01", „1A")
3. Typ wählen: **Standard** (Kontingentbett) oder **Notbett** — bei Wartebereich automatisch Warteplatz
4. „Hinzufügen" klicken

### 7.3 Betten deaktivieren (geplant)

Wenn ein Bett ab einem bestimmten Datum nicht mehr verfügbar ist:

1. Tab „Räume & Betten" → auf den Bett-Chip klicken
2. Deaktivierungsdatum eingeben
3. Das Bett ist ab diesem Datum automatisch inaktiv (grau)

### 7.4 Räume deaktivieren und reaktivieren

**Deaktivieren**: Papierkorb-Symbol beim Raum. Nur möglich, wenn keine aktive Belegung vorhanden.

**Reaktivieren**: Inaktive Räume können mit „Reaktivieren" wieder aktiviert werden.

### 7.5 Kontingent und Notbett-Kapazität anpassen

Im Bearbeitungs-Dialog → Tab „Stammdaten":

- **Kontingent** — EU-quotenrelevante Gesamtkapazität der Einrichtung
- **Notbett-Kapazität** — maximale Anzahl gleichzeitiger Notbett-Belegungen

> Achtung: Das Reduzieren des Kontingents unter die aktuelle Belegungszahl erzeugt eine Überkapazität im EU-Reporting.

---

## 8. Weitere Funktionen

### 8.1 Personensuche (AZR-ID)

Die Lupe in der Navigationsleiste öffnet eine Suche nach AZR-ID oder Alias-ID. Das Ergebnis zeigt Einrichtung, Raum, Bett und Zeitraum der aktuellen Belegung. Klicken öffnet das Einrichtungsdetail mit hervorgehobenem Bett. Die Suche findet nur **aktive** Belegungen.

### 8.2 Protokoll (Audit-Log)

Das Protokoll (**Navigationsmenü → „Protokoll"**) zeigt alle Aktionen im System chronologisch: Belegungen, Ausbuchungen, Gründe, Verlegungen. Es ist für alle Rollen sichtbar.

### 8.3 Gültigkeitsdaten (Einrichtungen und Räume)

- **Gültig ab**: Einrichtung/Raum ist erst ab diesem Datum sichtbar und buchbar
- **Gültig bis**: Einrichtung/Raum erscheint nach diesem Datum ausgegraut

### 8.4 Support und Hilfe

Der **Hilfe-Button** (?) in der Navigationsleiste öffnet einen seitenspezifischen Hilfetext und ermöglicht den Zugriff auf dieses vollständige Handbuch.

Der **Support-Button** (Headset-Symbol, falls konfiguriert) öffnet das interne Support-Portal Ihrer Organisation.

---

*Dieses Handbuch kann von Administratoren unter `/help/handbuch.md` auf dem Server bearbeitet werden.*
