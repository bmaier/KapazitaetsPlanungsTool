@agent
Feature: Agentic Verlegungsanfrage und Suggestion Wizard (Transfer Workflow)
  Als Disponent der Zentrale
  Möchte ich eine Person im Wartebereich einer Einrichtung zuweisen
  Damit der Agent mir automatisch Vorschläge liefert und den Reservierungsprozess im Hintergrund via MCP initiiert.

  Scenario: Automatische Platzsuche für eine Person
    Given der MCP-Server ist mit der FastAPI verbunden
    And der "TransferWorkflowSkill" ist im "TransferAgent" initialisiert
    When der Benutzer im Chat schreibt: "Suche ein Bett für Max Mustermann"
    Then sollte der Agent das MCP-Tool "run_suggestion_wizard" aufrufen
    And die Antwort sollte als semantisches A2UI-Widget "SuggestionWizardWidget" formatiert sein
    And der JSON-LD Payload sollte den Vorschlag inklusive Ziel-Einrichtung enthalten
    And der User hat im Frontend die Möglichkeit, die Reservierung interaktiv (MCP Tool "create_reservation_request") zu bestätigen
