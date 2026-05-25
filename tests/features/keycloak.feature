Feature: Keycloak Realm Konfiguration
  Als Systemadministrator
  möchte ich sicherstellen, dass Keycloak korrekt konfiguriert ist
  damit Benutzer sich mit den richtigen Rollen anmelden können

  Background:
    Given Keycloak läuft auf http://localhost:8080

  Scenario: Realm bordercapcontrol existiert
    When ich die Keycloak Admin-API abfrage
    Then existiert der Realm "bordercapcontrol"

  Scenario: Alle 4 Rollen vorhanden
    When ich die Realm-Rollen abfrage
    Then existiert die Rolle "reader"
    And existiert die Rolle "writer"
    And existiert die Rolle "location-admin"
    And existiert die Rolle "system-admin"

  Scenario: PKCE-Client konfiguriert
    When ich den Client "bordercapcontrol-frontend" abfrage
    Then ist der Client ein Public Client
    And unterstützt der Client PKCE
