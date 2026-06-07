# Protokoll (Audit-Log)

## Was ist das Protokoll?

Das Protokoll zeigt alle Aktionen im System chronologisch in tabellarischer Form. Es dient der Nachvollziehbarkeit und ist für alle Rollen lesbar (kein Schreibzugriff).

Jeder Eintrag enthält:
- **Zeitpunkt** der Aktion
- **Event-Typ** (z. B. Belegung angelegt, Verlegungsanfrage abgelehnt)
- **Nutzername** und Rolle
- **AZR-ID / Entity-ID** des betroffenen Objekts
- **Payload** mit fachlichen Details (z. B. Ablehnungsgrund, Belegungszeitraum)

## Event-Typen (Auswahl)

| Event | Farbe | Bedeutung |
|-------|-------|-----------|
| OCCUPANCY_CREATED | Grün | Bett belegt |
| OCCUPANCY_DELETED | Rot | Belegung beendet (Ausbuchen) |
| RESERVATION_CREATED | Blau | Verlegungsanfrage gestellt |
| RESERVATION_CONFIRMED | Hellblau | Verlegungsanfrage bestätigt |
| RESERVATION_REJECTED | Dunkelrot | Verlegungsanfrage abgelehnt |
| RESERVATION_CANCELLED | Orange | Verlegungsanfrage storniert |
| RESERVATION_TRANSFERRED | Lila | Person eingecheckt (Transfer) |

## Filtern

Oberhalb der Tabelle stehen Filter für **Zeitraum** (Von/Bis), **Event-Typ** und **AZR-ID / Entity-ID** zur Verfügung. Standard: letzte 5 Tage. Die Ergebnisse werden seitenweise angezeigt.

## Eintrag-Details

Ein Klick auf den **▶-Pfeil** in der letzten Spalte öffnet einen Dialog mit dem vollständigen Payload-Datensatz des Eintrags. Hier sind alle Felder tabellarisch aufgelistet, einschließlich fachlicher Gründe (z. B. Ausbuche-Grund, Ablehnungsgrund, Geschlechtsmismatch-Begründung).

## Export (nur System-Admin)

System-Admins sehen einen **„Export"**-Button, der die aktuell gefilterten Einträge als CSV-Datei herunterlädt.

## Hinweis zur Datensicherheit

Das Audit-Log ist **write-only** — Einträge können weder bearbeitet noch gelöscht werden. Dies ist für die rechtliche Nachvollziehbarkeit (EU-Compliance, AsylG §83) erforderlich.
