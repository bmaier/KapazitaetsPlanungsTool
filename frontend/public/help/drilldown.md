# Einrichtungsdetail — Betten verwalten

## Bett-Farben verstehen

| Farbe | Bedeutung |
|-------|-----------|
| 🟢 Grün | Bett frei |
| 🔴 Rot | Bett belegt |
| 🟣 Lila | Bett vorgemerkt (bestätigte Reservierung) |
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
- **Intern verlegen** — wählt ein freies Bett in derselben Einrichtung. Die Belegungsdaten werden übertragen.
- **Zu anderer Einrichtung verlegen** — öffnet den Reservierungsassistenten mit vorausgefüllter Person.

## Notbetten

Notbetten erscheinen in einem eigenen Abschnitt unten auf der Seite. Sie sind für max. **1 Nacht** vorgesehen und können einmalig um 1 Tag verlängert werden. Notbetten zählen **nicht** zur EU-Quota.

## Eingehende Reservierungsanfragen

Die Zahl neben „Anfragen" im Einrichtungs-Header zeigt offene Anfragen an Ihre Einrichtung. Ein Klick öffnet die Liste — von dort können Sie direkt zur Reservierungsansicht oder eine Anfrage bearbeiten.

## Räume & Betten verwalten (Administratoren)

Im Bearbeitungs-Dialog (Stift-Symbol) → Tab **„Räume & Betten"**:

- **Raum anlegen** — neuer Raum, Geschlechtsdesignation wird über Labels gesetzt
- **Bett hinzufügen** — Bett-Nummer und Typ (Standard/Notbett) eingeben
- **Bett deaktivieren** — Klick auf Bett-Chip → Datum für geplante Deaktivierung setzen
- **Verfügbar-ab-Datum** — Bett ist erst ab diesem Datum buchbar
- **Raum deaktivieren** — nur wenn kein Bett mehr belegt ist
- **Raum reaktivieren** — inaktive Räume können wieder aktiviert werden

Labels am Raum (z. B. „Männer", „Frauen", „Familie") steuern die Geschlechtsfarbe. Ein Geschlechts-Label kann erst entfernt werden, wenn der Raum vollständig leer ist.
