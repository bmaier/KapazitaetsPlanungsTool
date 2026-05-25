Feature: Infrastruktur Smoke Tests
  Als Entwickler
  möchte ich sicherstellen, dass alle Services erreichbar sind
  damit die Entwicklung auf einer stabilen Basis aufbaut

  Background:
    Given die Docker-Compose-Umgebung läuft

  Scenario: Backend Health Check
    When ich GET http://localhost:8000/health aufrufe
    Then ist der HTTP-Status 200
    And die Antwort enthält "status" mit Wert "ok"
    And die Antwort enthält "db" mit Wert "connected"
    And die Antwort enthält "keycloak" mit Wert "reachable"

  Scenario: SKOS-Service Geschlecht-Codeliste
    When ich GET http://localhost:8001/codes/geschlecht aufrufe
    Then ist der HTTP-Status 200
    And die Antwort enthält das Feld "concepts"
    And die Antwort enthält einen Code "M" mit Label "männlich"

  Scenario: PostgreSQL-Schemata vorhanden
    When ich die PostgreSQL-Schemata abfrage
    Then existiert das Schema "capacity"
    And existiert das Schema "reservations"
    And existiert das Schema "persons"
    And existiert das Schema "audit"
    And existiert das Schema "tasks"
    And existiert das Schema "reference_data"

  Scenario: Audit-Schema Manipulationsschutz — kein DELETE
    When ich versuche, einen Audit-Eintrag zu löschen
    Then schlägt die Operation mit einem Berechtigungsfehler fehl

  Scenario: Audit-Schema Manipulationsschutz — kein SELECT
    When ich versuche, Audit-Einträge zu lesen
    Then schlägt auch SELECT mit einem Berechtigungsfehler fehl
