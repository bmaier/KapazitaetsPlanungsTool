Feature: JWT Auth Protection
  Als API-Nutzer
  möchte ich sicherstellen, dass alle /api/-Endpoints geschützt sind
  und /health ohne Token erreichbar bleibt

  Background:
    Given die API läuft auf http://localhost:8000

  Scenario: Kein Authorization-Header → HTTP 401
    When ich GET /api/locations ohne Authentifizierung sende
    Then ist der HTTP-Status 401

  Scenario: /health ohne Authorization-Header → kein HTTP 401
    When ich GET /health ohne Authentifizierung sende
    Then ist der HTTP-Status nicht 401
