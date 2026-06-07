# Einrichtungsdetail — Betten verwalten

## Bett-Farben verstehen

| Farbe / Rand | Bedeutung |
|---|---|
| 🟢 Grün (ausgefüllt) | Bett frei |
| 🔴 Rot (ausgefüllt) | Bett belegt |
| 🟣 Lila-Blau (gestrichelt) | Bett vorgemerkt — bestätigte Reservierung, Person noch unterwegs |
| 🟠 Orange (gestrichelt) | Ausgehende Verlegungsanfrage läuft — Antwort der Zieleinrichtung ausstehend |
| 🔵 Hellblau (gestrichelt) | Verlegung genehmigt — Eincheck in Zieleinrichtung ausstehend |
| 🟣 Lila Rand (gestrichelt) | Anfrage-Zielbett — eingehende Anfrage ist auf dieses Bett gerichtet |
| ⚫ Grau (ausgefüllt) | Bett inaktiv oder noch nicht verfügbar |

Hovern über ein Bett zeigt Details: AZR-ID, Zeitraum, Labels sowie den Status laufender Verlegungsanfragen.

## Belegungszeitraum einstellen

Der Datumsfilter oben steuert, für welchen Zeitraum der Belegungsstand angezeigt wird. Standard: heute bis +14 Tage. Ein Bett erscheint als belegt, wenn der gewählte Zeitraum mit einer Belegung überlappt.

## 30-Tage-Auslastung (Sparkline)

Im blauen Header-Bereich der Einrichtung befindet sich oben rechts eine kompakte Auslastungsgrafik der letzten 30 Tage. Sie zeigt auf einen Blick, ob die Einrichtung tendenziell zu- oder abnimmt.

## Bett belegen (freies Bett anklicken)

1. Klicken Sie auf ein **grünes** Bett
2. Tragen Sie die **AZR-ID** der Person ein (Pflicht)
3. Optional: **Alias-ID** (interne Kennung Ihrer Einrichtung)
4. Bei Räumen ohne feste Geschlechtsdesignation: Geschlecht auswählen
5. Belegungsende einstellen (Beginn ist immer heute)
6. Optional: Hinweis-Labels zur Person wählen
7. „Bett belegen" klicken

> **AZR-ID** — die Ausländerzentralregister-Nummer. Es werden keine Personennamen gespeichert (DSGVO).

> ⚠ Bei einer Belegungsdauer über 12 Wochen erscheint eine Warnung. Die Belegung wird gespeichert, die EU-Quota kann jedoch überschritten werden.

> ⚠ **Geschlecht-Abweichung:** Stimmt das Geschlecht der Person nicht mit der Raumdesignation überein (z. B. Frau in Männerraum), erscheint eine Warnung. Eine Begründung ist dann verpflichtend — sie wird im Audit-Log gespeichert.

## Belegung verwalten (belegtes Bett anklicken)

Ein Klick auf ein **rotes** Bett öffnet die Verwaltungsansicht:

- **Belegungsende anpassen** — Datum direkt in der Detailansicht des Dialogs ändern und „OK" klicken.
- **Ausbuchen** — beendet die Belegung. Ein Ausbuche-Grund ist Pflicht (Audit-Log).
- **Intern verlegen** — wählt ein freies Bett (oder Warteplatz) in derselben Einrichtung.
- **Zu anderer Einrichtung verlegen** — öffnet die Bettsuche mit vorausgefüllter Person.

## Laufende Verlegungsanfragen am Bett

Ein belegtes Bett mit **orangem Rand (gestrichelt)** hat eine laufende ausgehende Verlegungsanfrage. Ein Klick öffnet einen Dialog mit Details zur Anfrage (Zieleinrichtung, Status) und ermöglicht die **Stornierung** (Pflicht: Stornierungsgrund angeben).

Ein belegtes Bett mit **hellblauem Rand (gestrichelt)** bedeutet, die Anfrage wurde von der Zieleinrichtung genehmigt — das Eincheck-Datum steht noch aus. Dieser Status wird automatisch aufgelöst, sobald die Person eingecheckt wird.

## Vorgemerkte Betten (lila-blau, gestrichelt)

Lila Betten sind durch eine bestätigte Reservierung blockiert — die Person ist noch unterwegs. Das Bett kann nicht direkt belegt werden. Ein Klick zeigt die zugehörige Reservierungsdetail-Info.

## Notbetten

Notbetten erscheinen in einem eigenen Abschnitt. Sie sind für max. **1 Nacht** vorgesehen und können einmalig um 1 Tag verlängert werden. Notbetten zählen **nicht** zur EU-Quota.

## Wartebereich

Der Wartebereich erscheint mit orangem Rahmen oberhalb der regulären Räume. Er ist für Personen gedacht, die gerade eingetroffen sind und noch auf ein reguläres Bett warten.

**Warteplatz belegen** — wie ein reguläres Bett anklicken. Warteplätze zählen nicht zur EU-Quota.

**Weiteren Warteplatz anlegen** — der Button „+ Warteplatz" legt automatisch einen neuen leeren Platz im Wartebereich an (nur für Writer und Admins).

**Leeren Warteplatz löschen** — Papierkorb-Symbol beim leeren Warteplatz (nur wenn kein Bett belegt ist).

**Einzeln verlegen** — belegten Warteplatz anklicken → „Zur Bettsuche" oder „Intern verlegen".

**Gruppe verlegen (einrichtungsübergreifend):**
1. Button **„Gruppe auswählen"** im Wartebereich aktivieren
2. Belegte Warteplätze anklicken (lila Markierung = ausgewählt)
3. Button **„X Personen verlegen"** klicken
4. Die Bettsuche öffnet sich mit allen ausgewählten Personen vorausgefüllt — auch zu anderen Einrichtungen

**Gruppe intern verlegen:**
1. Mehrfachauswahl wie oben aktivieren
2. Button **„X Intern verlegen"** klicken
3. Dialog öffnet sich: für jede Person ein Zielbett auswählen
4. Bei Geschlecht-Abweichungen: Begründung je Person eingeben
5. „Verlegen bestätigen" klicken

## Räume & Betten verwalten (Administratoren)

Im Bearbeitungs-Dialog (Stift-Symbol oben rechts) → Tab **„Räume & Betten"**:

- **Raum anlegen** — neuer Standardraum oder Wartebereich anlegen
- **Bett hinzufügen** — Bett-Nummer und Typ (Kontingent/Notbett) eingeben
- **Bett deaktivieren** — Klick auf Bett-Chip → Deaktivierungsdatum setzen (geplante Abschaltung)
- **Verfügbar-ab-Datum** — Rechtsklick auf Bett-Chip → Bett erst ab einem bestimmten Datum buchbar
- **Raum deaktivieren** — Papierkorb-Symbol beim Raum (nur wenn kein Bett belegt)
- **Raum reaktivieren** — inaktive Räume können mit „Reaktivieren" wieder aktiviert werden

## Stammdaten & Sichtbarkeit (Administratoren)

Im Bearbeitungs-Dialog → Tab **„Stammdaten"**:

- **Kontingent** — EU-quotenrelevante Gesamtkapazität
- **Notbett-Kapazität** — maximale gleichzeitige Notbett-Belegungen
- **Adresse** — Freitext-Adresse
- **Koordinaten (Lat/Lon)** — Position für die Kartenansicht; muss im gültigen Bereich liegen (Deutschland/Österreich/Schweiz)
- **Gültig ab / Gültig bis** — Einrichtung ist außerhalb dieses Zeitraums ausgegraut und nicht buchbar
- **Einrichtung aktiv** — Toggle zum vorübergehenden Deaktivieren ohne Löschen
- **Auf Karte anzeigen** — Toggle: steuert, ob die Einrichtung in der Kartenansicht des Dashboards erscheint

## Label-Verwaltung (nur System-Admin)

System-Admins sehen in der Einrichtungsdetail-Ansicht zusätzlich den Button **„Labels verwalten"**. Hier können Einrichtungs-, Raum-, Bett- und Belegungs-Labels im globalen Katalog angelegt und gelöscht werden.
