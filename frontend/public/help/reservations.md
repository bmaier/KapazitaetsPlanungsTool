# Verlegungsanfragen

## Was ist eine Verlegungsanfrage?

Eine Verlegungsanfrage ist eine Anfrage einer Einrichtung an eine andere, eine Person für einen bestimmten Zeitraum aufzunehmen. Der Workflow:

**Anfrage (Ausstehend) → Bestätigung mit Bett (Bestätigt / Vorgemerkt) → Einchecken (Verlegt)**

## Statusübersicht

| Status | Bedeutung |
|--------|-----------|
| Ausstehend | Anfrage wurde gestellt, noch keine Entscheidung |
| Bestätigt | Zieleinrichtung hat zugestimmt, ein bestimmtes Bett ist vorgemerkt (lila) |
| Abgelehnt | Zieleinrichtung hat abgelehnt |
| Storniert | Anfrage wurde zurückgezogen |
| Verlegt | Person wurde eingecheckt, Belegung aktiv in Zieleinrichtung |

## Tabs

**Alle** — alle Verlegungsanfragen, an denen Ihre Einrichtung als anfragende oder empfangende Seite beteiligt ist.

**Aktionen erforderlich** — eingehende Anfragen (Status „Ausstehend" oder „Bestätigt"), auf die Ihre Einrichtung noch reagieren muss. Zeigt einen roten Zähler.

**Meine Verlegungsanfragen** — nur Anfragen, die Sie selbst gestellt haben, mit aktuellem Status. System-Admins sehen hier alle Anfragen des Systems.

## Filterleiste

Über der Tabelle können Sie nach **Erstellungsdatum** (von/bis) und **Status** filtern. Status-Chips lassen sich per Klick aktivieren/deaktivieren. „Zurücksetzen" setzt alle Filter zurück (letzte 5 Tage, alle Status).

## Reservierungs-ID kopieren

Die ID in der ersten Spalte wird als Kurzform (z. B. `#A1B2C3D4`) angezeigt. Ein Klick auf die ID kopiert die vollständige UUID in die Zwischenablage.

## Neue Verlegungsanfrage stellen

1. Klicken Sie auf **„Neue Verlegungsanfrage"** (oder nutzen Sie die **Bettsuche** im Navigationsmenü)
2. Wählen Sie die Zieleinrichtung
3. Tragen Sie AZR-ID, Geschlecht, Geburtsjahr, Herkunftsland und Zeitraum ein
4. Anfrage absenden

Die Anfrage erscheint sofort im Postkorb der Zieleinrichtung.

## Eingehende Anfragen bestätigen

Als Zieleinrichtung sehen Sie unter **„Aktionen erforderlich"** alle offenen Anfragen.

Klick auf **„Bestätigen"** öffnet einen Dialog zur Bettauswahl:
- Alle freien Betten im angefragten Zeitraum werden gelistet
- Ein vom Assistenten vorgeschlagenes Bett ist lila umrandet und vorausgewählt
- Wählen Sie ein Bett aus und klicken Sie „Bestätigen & Bett vormerken"

> ⚠ **Geschlecht-Abweichung:** Wenn das Geschlecht der Person nicht zur Raumdesignation des gewählten Betts passt, erscheint eine Warnung. Eine Begründung ist in diesem Fall verpflichtend — sie wird im Audit-Log gespeichert.

Das gewählte Bett erscheint danach in der Einrichtungsdetail-Ansicht als **lila (vorgemerkt)**.

## Anfrage ablehnen

Klick auf **„Ablehnen"** — Ablehnungsgrund im Textfeld eingeben — Bestätigen. Die anfragende Einrichtung wird per Postkorb informiert.

## Person einchecken (Transfer)

Wenn die Person physisch angekommen ist:
1. Tab „Aktionen erforderlich" → Zeile mit Status „Bestätigt"
2. Button **„Einchecken"** klicken
3. Status wechselt zu „Verlegt" — die Belegung ist nun in der Zieleinrichtung aktiv

## Anfrage stornieren

Eine Anfrage kann von der anfragenden Seite storniert werden, solange sie noch nicht den Status „Verlegt" hat. Klicken Sie auf „Stornieren" in der Aktionsspalte.

## Bestätigt-Datum

In der Zeitraumspalte erscheint grün das Datum, an dem die Anfrage bestätigt wurde — für die Nachvollziehbarkeit der Bearbeitungszeit.
