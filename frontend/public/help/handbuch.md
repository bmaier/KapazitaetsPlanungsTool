# BorderCapControl — Benutzerhandbuch

---

## 1. Grundkonzepte

### 1.1 Einrichtungen und Kapazitäten

Das System verwaltet Kapazitäten in Grenzeinrichtungen (z. B. Flughäfen, Grenzübergänge). Jede Einrichtung hat:

- **Kontingent** — Anzahl der EU-quotenrelevanten Plätze
- **Notbett-Kapazität** — zusätzliche temporäre Plätze (nicht EU-quotenrelevant)
- **Räume** mit Geschlechtsdesignation
- **Betten** mit eindeutiger Nummer und festem Typ

### 1.2 Betttypen: Kontingentbett vs. Notbett

**Kontingentbett** — reguläres Bett, das zur deutschen EU-Gesamtkapazität zählt. Jede Belegung startet einen 12-Wochen-Timer.

**Notbett** — temporäre Unterbringung für max. 1 Nacht (einmalig um 1 Tag verlängerbar). Notbetten zählen **nicht** zur EU-Quota und starten keinen 12-Wochen-Timer. Tägliche Postkorb-Erinnerung bei belegten Notbetten.

### 1.3 Der 12-Wochen-Timer

Jede Belegung eines Kontingentbetts läuft maximal 12 Wochen (84 Tage). Eine Überschreitung wird beim Belegen durch eine Warnung angezeigt. Das System speichert die Belegung, aber das EU-Berichtswesen zeigt die Überschreitung.

### 1.4 Geschlechtsdesignation von Räumen

Räume werden durch Labels als Männer-, Frauen- oder Familienraum gekennzeichnet. Das Geschlechts-Label schützt vor falschen Belegungen. Es kann erst entfernt werden, wenn alle Betten des Raums leer sind.

### 1.5 AZR-ID und Alias-ID

**AZR-ID** — die Ausländerzentralregister-Nummer der Person. Keine Personennamen werden gespeichert (DSGVO-konform). Format z. B.: `AZR-2024-FFM-M01`.

**Alias-ID** — optionale einrichtungsinterne Kennung für die Person. Erleichtert die Suche ohne die vollständige AZR-ID.

### 1.6 Rollen und Berechtigungen

| Rolle | Berechtigungen |
|-------|----------------|
| `reader` | Nur Lesen (alle Einrichtungen) |
| `writer` | Lesen + Belegungen verwalten + Reservierungen |
| `location-admin` | Alles des `writer` + Räume/Betten/Einrichtungsstammdaten |
| `system-admin` | Voller Zugriff auf alle Einrichtungen |

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

### 2.3 Schnellzugriff Reservierungen

Laufende Reservierungen Ihrer Einrichtung (eingehend und ausgehend) werden als kleine Chips unter der Hauptüberschrift angezeigt. Ein Klick öffnet die vollständige Reservierungsübersicht.

### 2.4 Neue Einrichtung anlegen (Administratoren)

Der Button „Neue Einrichtung" erscheint nur für Nutzer mit Administratorrechten. Pflichtfelder: Name und Kontingent. Adresse und Notbett-Kapazität sind optional. Nach dem Anlegen können Räume und Betten im Einrichtungsdetail verwaltet werden.

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
- **Intern verlegen** — öffnet eine Liste freier Betten in derselben Einrichtung.
- **Zu anderer Einrichtung verlegen** — öffnet den Reservierungsassistenten mit vorausgefüllten Personendaten.

### 3.4 Person intern verlegen

So verlegen Sie eine Person innerhalb derselben Einrichtung auf ein anderes Bett:

1. Klicken Sie auf das **rote** (belegte) Bett
2. Wählen Sie „Intern verlegen (anderes Bett in dieser Einrichtung)"
3. Wählen Sie das Zielbett aus der Liste der freien Betten
4. Klicken Sie „Verlegen bestätigen"

Das System überträgt alle Belegungsdaten automatisch und gibt das alte Bett frei.

### 3.5 Person zu anderer Einrichtung verlegen

So verlegen Sie eine Person in eine andere Einrichtung:

1. Klicken Sie auf das **rote** Bett der Person
2. Wählen Sie „Zu anderer Einrichtung verlegen (Reservierungsanfrage)"
3. Der Reservierungsassistent öffnet sich mit den Personendaten vorausgefüllt
4. Wählen Sie die Zieleinrichtung und den Zeitraum
5. Anfrage absenden — die Zieleinrichtung muss die Anfrage bestätigen

Erst nach Bestätigung durch die Zieleinrichtung und dem Einchecken (Transfer) ist die Person dort aktiv. Die ursprüngliche Belegung bleibt bis zum Transfer erhalten.

### 3.6 Person ausbuchen

1. Klicken Sie auf das **rote** Bett
2. Wählen Sie „Ausbuchen (Belegung beenden)"
3. Tragen Sie einen **Grund** ein (Pflichtfeld — wird im Audit-Log gespeichert)
4. Klicken Sie „Ausbuchen"

Das Bett ist anschließend sofort wieder frei (grün).

### 3.7 Notbetten

Notbetten erscheinen in einem eigenen Abschnitt unten auf der Seite mit orangem Rand. Besonderheiten:

- Max. 1 Nacht Belegung
- Einmalige Verlängerung um 1 Tag möglich (Button „+1 Tag" erscheint nur beim ersten Mal)
- Tägliche Postkorb-Erinnerung bei belegten Notbetten
- Keine EU-Quota-Relevanz

### 3.8 Vorgemerkte Betten (lila)

Lila Betten sind für eine bestätigte Reservierung vorgemerkt. Sie können nicht direkt belegt werden. Ein Klick öffnet die zugehörige Reservierung in der Reservierungsübersicht. Das Bett wird automatisch zur Belegung, sobald die Person eingecheckt wird (Transfer).

---

## 4. Reservierungsworkflow

### 4.1 Statusübersicht

| Status | Bedeutung | Nächste Aktion |
|--------|-----------|----------------|
| Ausstehend | Anfrage gestellt | Zieleinrichtung: bestätigen oder ablehnen |
| Bestätigt | Bett vorgemerkt | Zieleinrichtung: Person einchecken |
| Abgelehnt | Keine Kapazität | Neue Anfrage stellen |
| Storniert | Aufgehoben | — |
| Verlegt | Eingecheckt | Belegung aktiv in Zieleinrichtung |

### 4.2 Neue Reservierungsanfrage stellen

1. Navigieren Sie zu **Reservierungen** → „Neue Anfrage" oder nutzen Sie den **Reservierungsassistenten**
2. Wählen Sie die Zieleinrichtung
3. Füllen Sie Pflichtfelder aus: AZR-ID, Geschlecht, Geburtsjahr, Herkunftsland, Zeitraum
4. Absenden

Die Anfrage erscheint sofort im Postkorb der Zieleinrichtung.

### 4.3 Eingehende Anfrage bestätigen

1. Postkorb → Tab „Zu beantworten"
2. Klicken Sie „Aufnahme bestätigen"
3. Wählen Sie ein freies Bett aus — das Bett wird vorgemerkt (lila)

> Mit der Bestätigung übernimmt Ihre Einrichtung die rechtliche Verantwortung für die Person.

### 4.4 Eingehende Anfrage ablehnen

1. Postkorb → Tab „Zu beantworten" → „Ablehnen"
2. Tragen Sie einen Ablehnungsgrund ein
3. Bestätigen

Die anfragende Einrichtung sieht den Status „Abgelehnt" in ihren Anfragen.

### 4.5 Person einchecken (Transfer)

Wenn die Person physisch angekommen ist:

1. Reservierungen → Tab „Aktionen erforderlich"
2. Zeile mit Status „Bestätigt" → Button **„Einchecken"**
3. Status wechselt auf „Verlegt" — Belegung wird in der Zieleinrichtung aktiv

### 4.6 Anfrage stornieren

Eine Anfrage kann von beiden Seiten storniert werden, solange sie noch nicht den Status „Verlegt" hat. Klicken Sie auf „Stornieren" in der Reservierungszeile.

---

## 5. Postkorb

### 5.1 Aufgabentypen

Der Postkorb zeigt drei Arten von Einträgen:

**Eingehende Reservierungsanfragen** — andere Einrichtungen bitten um Aufnahme einer Person. Hohe Priorität, zeitnahe Bearbeitung erforderlich.

**Systemaufgaben** — automatisch generierte Hinweise, z. B. bei belegten Notbetten oder anderen Systemereignissen.

**Ausgehende Anfragen (Tab „Meine Anfragen")** — Anfragen, die Sie gestellt haben, mit aktuellem Status.

### 5.2 Aufgaben als erledigt markieren

Für eigenständige Systemaufgaben (ohne verknüpfte Reservierung) erscheint der Button **„Als erledigt markieren"**. Nach dem Klick:

- Die Aufgabe verschwindet aus dem aktiven Tab
- Sie wird im Tab „Erledigt / Archiv" archiviert
- Kann nicht rückgängig gemacht werden

Reservierungsbezogene Aufgaben werden automatisch archiviert, wenn die Reservierung abgeschlossen, abgelehnt oder storniert wird.

### 5.3 Zur Belegung einer Person springen

Enthält eine Aufgabe eine AZR-ID, erscheint der Button **„Zur Belegung: AZR-…"**. Klicken öffnet direkt das Einrichtungsdetail mit dem Bett der Person hervorgehoben.

### 5.4 Prioritätsstufen

| Priorität | Farbe | Typische Ursache |
|-----------|-------|-----------------|
| Dringend | Rot | Eingehende Reservierungsanfrage |
| Mittel | Orange | Ausgehende offene Anfrage |
| Niedrig | Grün | Systemhinweis, archivierbar |

---

## 6. Bettendaten pflegen (Administratoren)

Nur Nutzer mit der Rolle `location-admin` oder `system-admin` haben Zugriff auf die Raumverwaltung.

### 6.1 Räume anlegen

1. Einrichtungsdetail → Stift-Symbol → Tab „Räume & Betten"
2. Scrollen Sie nach unten zu „Neuen Raum anlegen"
3. Geben Sie einen Raumnamen ein (z. B. „Raum A", „Raum 101")
4. „Raum anlegen" klicken

Ein neuer Raum hat zunächst keine Geschlechtsdesignation. Sie können sie über Labels setzen.

### 6.2 Betten hinzufügen

1. Im Tab „Räume & Betten" → beim gewünschten Raum auf „Bett" klicken
2. Bett-Nummer eingeben (z. B. „B01", „1A")
3. Typ wählen: **Standard** (Kontingentbett) oder **Notbett**
4. „Hinzufügen" klicken

### 6.3 Betten deaktivieren (geplant)

Wenn ein Bett ab einem bestimmten Datum nicht mehr verfügbar ist (z. B. Renovierung):

1. Tab „Räume & Betten" → auf den Bett-Chip klicken
2. Deaktivierungsdatum eingeben
3. Das Bett ist ab diesem Datum automatisch inaktiv (grau in der Bettansicht)

### 6.4 Verfügbar-ab-Datum setzen

Für neue Betten, die noch nicht sofort verfügbar sind:

1. Tab „Räume & Betten" → Klick auf das kleine `+`-Symbol neben einem Bett-Chip
2. Datum eingeben, ab dem das Bett buchbar ist

### 6.5 Räume deaktivieren und reaktivieren

**Deaktivieren**: Im Tab „Räume & Betten" → Papierkorb-Symbol beim Raum. Nur möglich, wenn keine aktive Belegung vorhanden ist.

**Reaktivieren**: Inaktive Räume (grau dargestellt) können mit „Reaktivieren" wieder aktiviert werden. Optional: Verfügbar-ab-Datum angeben.

### 6.6 Kontingent und Notbett-Kapazität anpassen

Im Bearbeitungs-Dialog → Tab „Stammdaten":

- **Kontingent** — EU-quotenrelevante Gesamtkapazität der Einrichtung
- **Notbett-Kapazität** — maximale Anzahl gleichzeitiger Notbett-Belegungen

> Achtung: Das Reduzieren des Kontingents unter die aktuelle Belegungszahl erzeugt eine Überkapazität im EU-Reporting.

### 6.7 Labels verwalten

Labels können auf Einrichtungen, Räume, Betten und Belegungen gesetzt werden:

- **Räume**: Geschlechtsdesignation (Männer, Frauen, Familie), Zustand
- **Belegungen**: Hinweise zur Person (nicht bindend, kein Personenbezug)

Ein Geschlechts-Label an einem Raum kann erst entfernt werden, wenn alle Betten des Raums leer sind.

---

## 7. Weitere Funktionen

### 7.1 Personensuche (AZR-ID)

Die Lupe in der Navigationsleiste öffnet eine Suche nach AZR-ID oder Alias-ID. Das Ergebnis zeigt:
- Einrichtung und Raum/Bett der aktuellen Belegung
- Zeitraum der Belegung
- Klicken öffnet das Einrichtungsdetail mit hervorgehobenem Bett

Die Suche findet nur **aktive** Belegungen.

### 7.2 Gültigkeitsdaten (Einrichtungen und Räume)

Einrichtungen und Räume können mit **Gültig-ab** und **Gültig-bis**-Daten versehen werden:

- **Gültig ab**: Einrichtung/Raum ist erst ab diesem Datum in der Übersicht sichtbar und buchbar
- **Gültig bis**: Einrichtung/Raum erscheint nach diesem Datum ausgegraut und kann nicht mehr belegt werden

Räume außerhalb ihrer Gültigkeitsdaten sind in der Bettansicht ausgegraut und mit einem Datum-Chip gekennzeichnet.

---

*Dieses Handbuch kann von Administratoren unter `/help/handbuch.md` auf dem Server bearbeitet werden.*
