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

**Wartebereich** — spezieller Raumtyp für kurzfristige Aufnahme bei Ankunft. Erscheint in der Einrichtungsdetail-Ansicht mit orangem Rahmen oberhalb der Standardräume. Ermöglicht Einzel- und Gruppenverlegung.

### 1.4 Der 12-Wochen-Timer

Jede Belegung eines Kontingentbetts läuft maximal 12 Wochen (84 Tage). Eine Überschreitung wird beim Belegen durch eine Warnung angezeigt. Das System speichert die Belegung, aber das EU-Berichtswesen zeigt die Überschreitung. Eine 12-Wochen-Warnung erscheint auch als Aufgabe im Postkorb.

### 1.5 Geschlechtsdesignation von Räumen

Räume werden durch Labels als Männer-, Frauen- oder Familienraum gekennzeichnet. Das Geschlechts-Label schützt vor falschen Belegungen. Es kann erst entfernt werden, wenn alle Betten des Raums leer sind.

Bei Geschlecht-Abweichung (Person passt nicht zum Raum) erscheint eine Warnung — eine Begründung ist verpflichtend und wird im Audit-Log gespeichert.

### 1.6 AZR-ID und Alias-ID

**AZR-ID** — die Ausländerzentralregister-Nummer der Person. Keine Personennamen werden gespeichert (DSGVO-konform). Format z. B.: `AZR-2024-FFM-M01`.

**Alias-ID** — optionale einrichtungsinterne Kennung für die Person. Erleichtert die Suche ohne die vollständige AZR-ID.

### 1.7 Bett-Status im Überblick

| Status / Rand | Farbe | Bedeutung |
|---|---|---|
| FREI | Grün | Bett kann belegt werden |
| BELEGT | Rot | Bett hat eine aktive Belegung |
| VORGEMERKT | Lila-Blau (gestrichelt) | Bett für bestätigte Reservierung — Person noch unterwegs |
| Anfrage läuft | Orange (gestrichelt) | Ausgehende Verlegungsanfrage, Antwort ausstehend |
| Verlegen genehmigt | Hellblau (gestrichelt) | Anfrage bestätigt, Eincheck ausstehend |
| Anfrage-Zielbett | Lila Rand (gestrichelt) | Eingehende Anfrage zielt auf dieses Bett |
| INAKTIV | Grau | Bett ist inaktiv oder noch nicht verfügbar |

### 1.8 Rollen und Berechtigungen

| Rolle | Berechtigungen |
|-------|----------------|
| `reader` | Nur Lesen (alle Einrichtungen) |
| `writer` | Lesen + Belegungen verwalten + Verlegungsanfragen |
| `location-admin` | Alles des `writer` + Räume/Betten/Einrichtungsstammdaten |
| `system-admin` | Voller Zugriff auf alle Einrichtungen, alle Anfragen + Label-Katalog |

---

## 2. Dashboard — Kapazitätsübersicht

### 2.1 Ampelfarben

Die Farbe jeder Einrichtungskachel zeigt den Belegungsgrad:

- **Grün** — unter 70 % belegt — Kapazität verfügbar
- **Gelb** — 70–90 % belegt — Kapazität begrenzt
- **Rot** — über 90 % belegt — Kapazität kritisch

### 2.2 Rasteransicht vs. Kartenansicht

**Rasteransicht** — zeigt alle Einrichtungen als Kacheln mit Kennzahlen. Ein orangener Chip **„Endet in X Tagen"** erscheint, wenn `valid_until` der Einrichtung bald abläuft.

**Kartenansicht** — Standard-Ansicht. Zeigt Einrichtungen auf einer Karte mit farbigen Markierungen entsprechend der Ampelfarbe. Einrichtungen mit `show_on_map = false` werden hier ausgeblendet.

### 2.3 Meine Reservierungen (Schnellzugriff)

Laufende Verlegungsanfragen Ihrer Einrichtung (eingehend und ausgehend) werden als kleine Chips unter der Hauptüberschrift angezeigt (max. 5). Ein Klick öffnet die vollständige Verlegungsansicht.

### 2.4 Neue Einrichtung anlegen (Administratoren)

Der Button „Neue Einrichtung" erscheint nur für Nutzer mit Administratorrechten. Pflichtfelder: Name und Kontingent. Adresse und Notbett-Kapazität sind optional. Nach dem Anlegen können Räume, Betten und ein Wartebereich im Einrichtungsdetail verwaltet werden.

### 2.5 Kontingent-Reporting (nur System-Admin)

Unterhalb der Einrichtungsübersicht sehen System-Admins das Kontingent-Reporting-Panel mit EU-Gesamtquote, Sum Kontingente, regulären Betten und Abweichung je Einrichtung.

---

## 3. Einrichtungsdetail — Betten verwalten

### 3.1 Belegungszeitraum einstellen

Der Datumsfilter oben steuert, für welchen Zeitraum der Belegungsstand geprüft wird. Standard: heute bis +14 Tage.

### 3.2 30-Tage-Auslastung (Sparkline)

Im blauen Header der Einrichtung befindet sich oben rechts eine kompakte Auslastungsgrafik der letzten 30 Tage.

### 3.3 Bett belegen (freies Bett)

1. Klicken Sie auf ein **grünes** Bett
2. Tragen Sie die **AZR-ID** ein (Pflicht)
3. Optional: **Alias-ID** eingeben
4. Bei Räumen ohne feste Geschlechtsdesignation: Geschlecht auswählen
5. Belegungsende einstellen (Beginn ist immer heute)
6. Optionale Hinweis-Labels zur Person auswählen
7. „Bett belegen" klicken

Bei Geschlecht-Abweichung erscheint eine Warnung mit Pflicht-Begründungsfeld.

### 3.4 Belegung verwalten (belegtes Bett anklicken)

Ein Klick auf ein **rotes** Bett öffnet die Verwaltungsansicht:

- **Belegungsende anpassen** — Datum direkt im Dialog ändern und „OK" klicken
- **Ausbuchen** — beendet die Belegung; Grund ist Pflichtfeld (Audit-Log)
- **Intern verlegen** — öffnet eine Liste freier Betten und Warteplätze in derselben Einrichtung
- **Zu anderer Einrichtung verlegen** — öffnet die Bettsuche mit vorausgefüllten Personendaten

### 3.5 Laufende Verlegungsanfragen am Bett

Ein belegtes Bett mit **orangem Rand (gestrichelt)** hat eine laufende ausgehende Verlegungsanfrage. Klick öffnet einen Dialog mit Stornierungsmöglichkeit (Pflicht: Stornierungsgrund).

### 3.6 Person ausbuchen

1. Klicken auf rotes Bett → „Ausbuchen"
2. Grund eingeben (Pflichtfeld)
3. „Ausbuchen" klicken — Bett ist sofort wieder frei

### 3.7 Vorgemerkte Betten (lila-blau, gestrichelt)

Lila-blaue Betten sind für eine bestätigte Verlegungsanfrage reserviert. Die Person ist noch nicht eingecheckt. Klick zeigt die zugehörige Anfrage.

### 3.8 Notbetten

Notbetten erscheinen in einem eigenen Abschnitt:
- Max. 1 Nacht Belegung
- Einmalige Verlängerung um 1 Tag möglich
- Tägliche Postkorb-Erinnerung bei belegten Notbetten
- Keine EU-Quota-Relevanz

### 3.9 Wartebereich

Der Wartebereich erscheint ganz oben in der Einrichtungsdetail-Ansicht. Warteplätze sind für Personen vorgesehen, die gerade eingetroffen sind.

**Warteplatz hinzufügen**: Button „+ Warteplatz" legt automatisch einen neuen leeren Platz an.

**Leeren Warteplatz löschen**: Papierkorb-Symbol beim leeren Platz.

**Einzelne Person verlegen**: Belegten Warteplatz anklicken → „Zu anderer Einrichtung verlegen" oder „Intern verlegen".

**Gruppe einrichtungsübergreifend verlegen (Mehrfachauswahl):**
1. Button „Gruppe auswählen" aktivieren
2. Belegte Warteplätze anklicken (lila = ausgewählt)
3. „X Personen verlegen" klicken → Bettsuche öffnet sich für alle Personen

**Gruppe intern verlegen:**
1. Mehrfachauswahl aktivieren
2. „X Intern verlegen" klicken
3. Zielbett für jede Person auswählen
4. Bei Geschlecht-Abweichungen: Begründung je Person eingeben
5. „Verlegen bestätigen"

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

### 4.3 Eingehende Anfrage bestätigen

1. Postkorb → Tab „Zu beantworten" → „Aufnahme bestätigen"
2. Dialog: freie Betten im Anfragezeitraum werden aufgelistet
3. Vorgeschlagenes Bett (lila umrandet) ist vorausgewählt — Sie können ein anderes wählen
4. Bei Geschlecht-Abweichung: Pflicht-Begründung eingeben
5. „Bestätigen & Bett vormerken" klicken

### 4.4 Anfrage ablehnen

Postkorb → Tab „Zu beantworten" → „Ablehnen" → Ablehnungsgrund eingeben → Bestätigen.

### 4.5 Person einchecken (Transfer)

Postkorb → Tab „Zu beantworten" oder Verlegungsanfragen → Zeile „Bestätigt" → Button „Einchecken".

### 4.6 Anfrage stornieren

Von der anfragenden Seite: solange Status nicht „Verlegt", „Stornieren" klicken.

---

## 5. Bettsuche (Reservierungsassistent)

### 5.1 Suchmodi

**Einzelperson** — sucht ein einzelnes Bett für eine Person mit bekanntem Geschlecht.

**Gruppe** — sucht Betten für mehrere Personen (M/W/D-Anzahl angeben).

**Familie / Minderjährige** — für gemischte Gruppen aus Erwachsenen und Kindern. Suche nach Familienräumen.

### 5.2 Suchoptionen

- **Einrichtungsübergreifend** — durchsucht alle Einrichtungen
- **Geschlecht ignorieren** — zeigt auch Räume ohne passende Designation
- **Raum-Labels** — filtert auf Räume mit bestimmten Labels

### 5.3 Belegung vormerken (ohne Personenbezug)

Im Bestätigen-Schritt kann für jedes Bett eine Person per AZR-ID gesucht werden. Wenn die Person gefunden wird, werden Labels und Geschlecht automatisch übernommen. Wenn die Person nicht im System ist, kann sie direkt als neue Person im Wartebereich eingebucht werden.

### 5.4 Gruppenverlegung aus Wartebereich

Wenn mehrere Personen im Wartebereich ausgewählt wurden, öffnet die Bettsuche automatisch im Gruppenmodus. Nach Bestätigung wird für jede Person eine eigene Anfrage gestellt oder eine interne Verlegung durchgeführt.

---

## 6. Postkorb

### 6.1 Tabs

**Zu beantworten** — eingehende Anfragen (PENDING oder CONFIRMED) + offene Systemaufgaben Ihrer Einrichtung. System-Admins sehen hier alle offenen Anfragen aller Einrichtungen.

**Meine Anfragen** — Anfragen, die Sie gestellt haben. Orangener Zähler = Anzahl noch ausstehender eigener Anfragen.

**Erledigt / Archiv** — abgeschlossene, abgelehnte, stornierte oder als erledigt markierte Aufgaben.

### 6.2 Aufgaben als erledigt markieren

Für eigenständige Systemaufgaben erscheint der Button „Als erledigt markieren". Reservierungsbezogene Aufgaben werden automatisch archiviert.

### 6.3 Zur Belegung einer Person springen

Enthält eine Aufgabe eine AZR-ID, erscheint der Button „Zur Belegung: AZR-…". Klicken öffnet direkt das Einrichtungsdetail mit dem Bett der Person hervorgehoben.

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
2. Raumnamen eingeben und Typ wählen: **Standard** oder **Wartebereich**
3. „Raum anlegen" klicken

### 7.2 Betten hinzufügen

1. Tab „Räume & Betten" → beim Raum „Bett" klicken
2. Bett-Nummer eingeben
3. Typ wählen: **Kontingent** oder **Notbett** (bei Wartebereich automatisch Warteplatz)
4. „Hinzufügen" klicken

### 7.3 Betten deaktivieren (geplant)

1. Bett-Chip anklicken → Deaktivierungsdatum eingeben
2. Das Bett ist ab diesem Datum automatisch inaktiv (grau)

Rechtsklick auf Bett-Chip → „Verfügbar ab" setzen: Bett ist erst ab einem bestimmten Datum buchbar.

### 7.4 Räume deaktivieren und reaktivieren

**Deaktivieren**: Papierkorb-Symbol beim Raum. Nur möglich, wenn keine aktive Belegung vorhanden.

**Reaktivieren**: Inaktive Räume können mit „Reaktivieren" (optional: neues Gültigkeits-ab-Datum) wieder aktiviert werden.

### 7.5 Stammdaten & Sichtbarkeit anpassen

Im Bearbeitungs-Dialog → Tab „Stammdaten":

- **Kontingent** — EU-quotenrelevante Gesamtkapazität der Einrichtung
- **Notbett-Kapazität** — maximale Anzahl gleichzeitiger Notbett-Belegungen
- **Koordinaten** — Position für die Kartenansicht (muss im gültigen geografischen Bereich liegen)
- **Gültig ab / Gültig bis** — Einrichtung ist außerhalb ausgegraut
- **Einrichtung aktiv** — vorübergehend deaktivieren ohne Löschen
- **Auf Karte anzeigen** — steuert die Sichtbarkeit in der Kartenansicht des Dashboards

> Achtung: Das Reduzieren des Kontingents unter die aktuelle Belegungszahl erzeugt eine Überkapazität im EU-Reporting.

---

## 8. Statistik

Die Statistik-Seite (**Navigationsmenü → „Statistik"**) zeigt den Belegungsverlauf als Zeitreihe mit:

- KPI-Karten (aktuelle Auslastung, 30-Tage-Durchschnitt, Trend)
- Kombiniertes Balken-/Liniendiagramm
- Schnellauswahl 7T / 30T / 3M / 1J

Die Granularität (Tag/Woche/Monat) wird automatisch je nach Zeitraum gewählt. System-Admins können die Einrichtung wechseln.

---

## 9. Protokoll (Audit-Log)

Das Protokoll (**Navigationsmenü → „Protokoll"**) zeigt alle Aktionen im System chronologisch. Es ist für alle Rollen lesbar und write-only (unveränderlich). Einträge können nach Zeitraum, Event-Typ und AZR-ID gefiltert werden. Ein Klick auf den Pfeil in der letzten Spalte zeigt alle Payload-Details.

System-Admins können die gefilterten Einträge als CSV exportieren.

---

## 10. Weitere Funktionen

### 10.1 Personensuche (AZR-ID / Alias)

Die Lupe in der Navigationsleiste öffnet eine Suche nach AZR-ID oder Alias-ID. Das Ergebnis zeigt Einrichtung, Raum, Bett und Zeitraum. Klicken öffnet die Einrichtungsdetail-Ansicht mit hervorgehobenem Bett. Die Suche findet nur **aktive** Belegungen.

### 10.2 Label-Verwaltung (nur System-Admin)

System-Admins sehen in der Einrichtungsdetail-Ansicht den Button **„Labels verwalten"**. Hier können Einrichtungs-, Raum-, Bett- und Belegungs-Labels im globalen Katalog angelegt und gelöscht werden.

### 10.3 Gültigkeitsdaten (Einrichtungen und Räume)

- **Gültig ab**: Einrichtung/Raum ist erst ab diesem Datum sichtbar und buchbar
- **Gültig bis**: Einrichtung/Raum erscheint nach diesem Datum ausgegraut

### 10.4 Support und Hilfe

Der **Hilfe-Button** (?) in der Navigationsleiste öffnet einen seitenspezifischen Hilfetext und ermöglicht den Zugriff auf dieses vollständige Handbuch.

Der **Support-Button** (Headset-Symbol, falls konfiguriert) öffnet das interne Support-Portal Ihrer Organisation.

---

*Dieses Handbuch kann von Administratoren unter `/help/handbuch.md` auf dem Server bearbeitet werden.*
