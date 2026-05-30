# Einrichtungsdetail — Betten verwalten

## Bett-Farben verstehen

| Farbe | Bedeutung |
|-------|-----------|
| 🟢 Grün | Bett frei |
| 🔴 Rot | Bett belegt |
| 🟣 Lila | Bett vorgemerkt (bestätigte Reservierung — Person noch nicht eingecheckt) |
| 🟠 Orange | Warteplatz im Wartebereich |
| ⚫ Grau | Bett inaktiv oder noch nicht verfügbar |

Hovern über ein Bett zeigt Details: AZR-ID, Zeitraum, Labels.

## Belegungszeitraum einstellen

Der Datumsfilter oben steuert, für welchen Zeitraum der Belegungsstand angezeigt wird. Standard: heute bis +14 Tage. Ein Bett erscheint als belegt, wenn der gewählte Zeitraum mit einer Belegung überlappt.

## Bett belegen (freies Bett anklicken)

1. Klicken Sie auf ein **grünes** Bett
2. Tragen Sie die **AZR-ID** der Person ein (Pflicht)
3. Optional: **Alias-ID** (interne Kennung Ihrer Einrichtung)
4. Wählen Sie Belegungsbeginn und -ende
5. Klicken Sie „Bett belegen"

> **AZR-ID** — die Ausländerzentralregister-Nummer. Es werden keine Personennamen gespeichert (DSGVO).
>
> **Alias-ID** — eine einrichtungsinterne optionale Kennung, z. B. für interne Listen.

> ⚠ Bei einer Belegungsdauer über 12 Wochen erscheint eine Warnung. Das System speichert die Belegung, aber die EU-Quota kann überschritten werden.

## Belegung verwalten (belegtes Bett anklicken)

Ein Klick auf ein **rotes** Bett öffnet die Verwaltungsansicht mit drei Optionen:

- **Ausbuchen** — beendet die Belegung. Ein Ausbuche-Grund ist Pflicht (Audit-Log).
- **Intern verlegen** — wählt ein freies Bett (oder Warteplatz) in derselben Einrichtung. Die Belegungsdaten werden übertragen.
- **Zu anderer Einrichtung verlegen** — öffnet die Bettsuche mit vorausgefüllter Person.

## Vorgemerkte Betten (lila)

Lila Betten sind durch eine bestätigte Reservierung blockiert — die Person ist noch unterwegs. Das Bett kann nicht direkt belegt werden. Ein Klick zeigt die zugehörige Reservierungsdetail-Info. Das Bett wird automatisch zur aktiven Belegung, sobald die Person eingecheckt wird (Transfer).

## Notbetten

Notbetten erscheinen in einem eigenen Abschnitt. Sie sind für max. **1 Nacht** vorgesehen und können einmalig um 1 Tag verlängert werden. Notbetten zählen **nicht** zur EU-Quota.

## Wartebereich

Der Wartebereich ist ein spezieller Raumtyp für Personen, die noch keinem regulären Bett zugewiesen wurden (z. B. bei Ankunft oder kurzer Durchschleusung). Er erscheint mit orangem Rahmen oberhalb der regulären Räume.

**Warteplatz belegen** — wie ein reguläres Bett anklicken. Warteplätze zählen nicht zur EU-Quota.

**Einzeln verlegen** — belegten Warteplatz anklicken → „Zur Bettsuche" oder „Intern verlegen" für Transfer in ein reguläres Bett.

**Gruppe verlegen (Mehrfachauswahl):**
1. Button **„Gruppe auswählen"** im Wartebereich aktivieren
2. Belegte Warteplätze anklicken (lila Markierung = ausgewählt)
3. Button **„X Personen verlegen"** klicken
4. Die Bettsuche öffnet sich mit allen ausgewählten Personen vorausgefüllt

## Räume & Betten verwalten (Administratoren)

Im Bearbeitungs-Dialog (Stift-Symbol) → Tab **„Räume & Betten"**:

- **Raum anlegen** — neuer Standardraum oder **Wartebereich** anlegen
- **Bett hinzufügen** — Bett-Nummer und Typ (Standard/Notbett) eingeben; Wartebereich-Räume erhalten automatisch den Typ Warteplatz
- **Bett deaktivieren** — Datum für geplante Deaktivierung setzen
- **Verfügbar-ab-Datum** — Bett ist erst ab diesem Datum buchbar
- **Raum deaktivieren** — nur wenn kein Bett mehr belegt ist
- **Raum reaktivieren** — inaktive Räume können wieder aktiviert werden

Labels am Raum (z. B. „Männer", „Frauen", „Familie") steuern die Geschlechtsfarbe. Ein Geschlechts-Label kann erst entfernt werden, wenn der Raum vollständig leer ist.
