# Internes Verlegen per Direktbuchung
# Testet den internen Verlegungsflow, den der SuggestionWizard nutzt,
# wenn das Zielbett in der eigenen Einrichtung liegt (Reservierungs-API wird umgangen).
#
# Ablauf:
#   1. POST neue Belegung mit verlegung_grund → 201 (kurze Doppelbelegung erlaubt)
#   2. DELETE alte Belegung → 200
#   3. Danach: genau eine aktive Belegung für die Person
#
# Rollback-Szenario: neue Belegung wird gelöscht, falls nachfolgende Operation fehlschlägt.
# Block: Reservierungsanfrage auf eigene Einrichtung (requester == target) → 422.

Feature: Internes Verlegen per Direktbuchung (SuggestionWizard-Flow)
  Als Sachbearbeiter
  möchte ich eine Person intern (innerhalb meiner Einrichtung) verlegen,
  ohne den Reservierungsworkflow zu nutzen,
  damit das Verlegen direkt und ohne Genehmigung erfolgt.

  Background:
    Given die API läuft auf http://localhost:8000
    And eine Einrichtung mit Wartebereich und KONTINGENT-Bett für den Verlege-Test existiert
    And eine Person ist im Wartebereich-Bett belegt

  Scenario: POST neue Belegung mit verlegung_grund wird mit 201 akzeptiert
    When ich die Person mit verlegung_grund in das KONTINGENT-Bett einbuche
    Then ist der HTTP-Status 201

  Scenario: DELETE alte Belegung nach internem Verlegen liefert 200
    When ich die Person mit verlegung_grund in das KONTINGENT-Bett einbuche
    And ich die alte Wartebereich-Belegung lösche
    Then ist der HTTP-Status 200

  Scenario: Nach POST und DELETE hat die Person genau eine aktive Belegung
    When ich die Person mit verlegung_grund in das KONTINGENT-Bett einbuche
    And ich die alte Wartebereich-Belegung lösche
    Then hat die Person genau eine aktive Belegung

  Scenario: Rollback - neue Belegung kann separat gelöscht werden
    When ich die Person mit verlegung_grund in das KONTINGENT-Bett einbuche
    Then ist der HTTP-Status 201
    When ich die neue KONTINGENT-Belegung wieder lösche
    Then ist der HTTP-Status 200
    And hat die Person genau eine aktive Belegung

  Scenario: Reservierungsanfrage auf eigene Einrichtung schlägt fehl mit 422
    When ich eine Reservierungsanfrage von der eigenen Einrichtung auf sich selbst sende
    Then ist der HTTP-Status 422
