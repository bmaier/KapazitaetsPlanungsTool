# Feature: Transfer-Historisierung (Ein-Platz-Regel bei Check-in)
#
# Sicherstellt, dass beim Check-in (CONFIRMED → TRANSFERRED) die alte Belegung
# nicht gelöscht, sondern auf belegung_ende = heute gesetzt wird.
# Damit bleibt die Unterbringungshistorie lückenlos und die Person hat zu jedem
# Zeitpunkt einen nachweisbaren Platz.

Feature: Historisierung der Quell-Belegung beim Transfer
  Als System
  möchte ich sicherstellen, dass beim Check-in einer Person in der Zieleinrichtung
  die alte Belegung nicht gelöscht, sondern mit belegung_ende = heute abgeschlossen wird,
  damit keine Lücken in der Unterbringungshistorie entstehen.

  Background:
    Given die API läuft auf http://localhost:8000
    And zwei aktive Einrichtungen Alpha und Beta für Transfertests existieren
    And ein freies Bett in Einrichtung Alpha und ein freies Bett in Einrichtung Beta existieren

  Scenario: Alte Belegung bleibt nach Transfer erhalten und wird auf heute abgeschlossen
    Given die Testperson ist aktiv in Transfer-Einrichtung Alpha eingebucht
    And eine bestätigte Verlegungsanfrage nach Beta für diese Person existiert
    When Einrichtung Beta den Transfer durchführt
    Then ist der HTTP-Status 200
    And die alte Belegung der Person in Alpha existiert noch in der Datenbank
    And die alte Belegung hat belegung_ende = heute

  Scenario: Neue Belegung in der Zieleinrichtung wird angelegt
    Given die Testperson ist aktiv in Transfer-Einrichtung Alpha eingebucht
    And eine bestätigte Verlegungsanfrage nach Beta für diese Person existiert
    When Einrichtung Beta den Transfer durchführt
    Then ist der HTTP-Status 200
    And eine aktive Belegung der Person in Einrichtung Beta existiert

  Scenario: Person hat nach dem Transfer keine Belegungslücke
    Given die Testperson ist aktiv in Transfer-Einrichtung Alpha eingebucht
    And eine bestätigte Verlegungsanfrage nach Beta für diese Person existiert
    When Einrichtung Beta den Transfer durchführt
    Then ist der HTTP-Status 200
    And die Belegungshistorie der Person enthält keine Zeitlücke

  Scenario: Reservierungsstatus wechselt nach Transfer auf TRANSFERRED
    Given die Testperson ist aktiv in Transfer-Einrichtung Alpha eingebucht
    And eine bestätigte Verlegungsanfrage nach Beta für diese Person existiert
    When Einrichtung Beta den Transfer durchführt
    Then ist der HTTP-Status 200
    And die Reservierung hat Status "TRANSFERRED"
