# encoding: utf-8
Feature: Wartebereich SB-Erweiterung — Schnelleinbuchen + Bett löschen

  Background:
    Given eine Einrichtung "Warte-SB-Test" mit Wartebereich existiert

  Scenario: Schnelleinbuchen wenn ein freier Warteplatz vorhanden ist
    Given der Wartebereich hat 1 freien Platz
    When SB bucht Person "AZR-WP-FREI-001" (Geschlecht M) direkt über API ein
    Then ist "AZR-WP-FREI-001" im Wartebereich eingebucht
    And wurde kein neues Bett angelegt

  Scenario: Schnelleinbuchen legt automatisch neuen Platz an wenn alle belegt
    Given alle Wartebereich-Plätze in "Warte-SB-Test" sind belegt
    When SB bucht Person "AZR-WP-AUTO-001" (Geschlecht F) direkt über API ein
    Then ist "AZR-WP-AUTO-001" im Wartebereich eingebucht
    And wurde ein neues Warteplatz-Bett angelegt

  Scenario: Freien Warteplatz löschen
    Given der Wartebereich hat 1 freien Platz
    When SB löscht den freien Warteplatz über die API
    Then ist der Warteplatz nicht mehr aktiv

  Scenario: Belegten Warteplatz kann nicht gelöscht werden
    Given der Wartebereich hat 1 freien Platz
    And Person "AZR-WP-BELEGT-DEL" belegt den Warteplatz
    When SB versucht den belegten Warteplatz zu löschen
    Then antwortet der Server mit Status 409
