Feature: Bettsuche — Auto-Warteplatz und Verlegungsanfrage für neue Personen
  Als Sachbearbeiter einer Einrichtung
  möchte ich bei der Bettsuche eine neue (unbekannte) Person automatisch
  in den Wartebereich einbuchen und direkt eine Verlegungsanfrage senden,
  damit keine Person ohne Wartebereich-Einbuchung eine Cross-Location-Anfrage auslöst.

  Background:
    Given die API läuft auf http://localhost:8000
    And eine Quell-Einrichtung "Frankfurt" mit Wartebereich (3 freie Plätze) existiert
    And eine Ziel-Einrichtung "München" mit 2 freien Männerbetten existiert

  Scenario: Auto-Flow — neue Person wird in Wartebereich eingebucht, dann Verlegungsanfrage gesendet
    When ich das erste freie Wartebereich-Bett in "Frankfurt" abfrage
    Then gibt es mindestens 1 freies Wartebereich-Bett
    When ich "AZR-TEST-AUTOWP-001" (Geschlecht M) in das erste freie Wartebereich-Bett von "Frankfurt" einbuche
    Then ist der HTTP-Status 201
    And die Person "AZR-TEST-AUTOWP-001" belegt ein Wartebereich-Bett in "Frankfurt"
    When ich eine Verlegungsanfrage von "Frankfurt" nach "München" für "AZR-TEST-AUTOWP-001" sende
    Then ist der HTTP-Status 201
    And die Reservierungsantwort enthält Status "PENDING"
    And die Reservierungsantwort enthält ein "id"-Feld

  Scenario: Kein freier Warteplatz — Bed-Status gibt leere FREI-Liste für Wartebereich zurück
    Given alle Wartebereich-Betten in "Frankfurt" sind belegt
    When ich das erste freie Wartebereich-Bett in "Frankfurt" abfrage
    Then gibt es kein freies Wartebereich-Bett

  Scenario: Verlegungsanfrage ohne X-Location-Id Header wird abgelehnt
    When ich eine Verlegungsanfrage ohne Location-Header nach "München" sende
    Then ist der HTTP-Status 422
