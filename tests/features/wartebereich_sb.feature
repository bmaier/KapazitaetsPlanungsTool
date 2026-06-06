# encoding: utf-8
Feature: Wartebereich SB-Erweiterung — Warteplatz hinzufügen + Bett löschen

  Background:
    Given eine Einrichtung "Warte-SB-Test" mit Wartebereich existiert

  Scenario: Neuen leeren Warteplatz hinzufügen
    Given der Wartebereich hat 1 freien Platz
    When SB legt über die API einen neuen Warteplatz an
    Then existiert ein zusätzlicher Warteplatz im Wartebereich

  Scenario: Freien Warteplatz löschen
    Given der Wartebereich hat 1 freien Platz
    When SB löscht den freien Warteplatz über die API
    Then ist der Warteplatz nicht mehr aktiv

  Scenario: Belegten Warteplatz kann nicht gelöscht werden
    Given der Wartebereich hat 1 freien Platz
    And Person "AZR-WP-BELEGT-DEL" belegt den Warteplatz
    When SB versucht den belegten Warteplatz zu löschen
    Then antwortet der Server mit Status 409
