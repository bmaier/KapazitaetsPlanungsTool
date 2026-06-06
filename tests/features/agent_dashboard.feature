@agent
Feature: Agentic Dashboard und Informationsabruf
  Als Benutzer der BorderCapControl Anwendung
  Möchte ich den Orchestrator-Agenten nach der aktuellen Auslastung fragen
  Damit ich schnell einen Überblick über die Kapazitäten erhalte, ohne manuell zu navigieren.

  Scenario: Abfrage der globalen Auslastung
    Given der MCP-Server ist mit der FastAPI verbunden
    And der "LocationAnalyzer" Agent ist initialisiert
    When der Benutzer im Chat fragt: "Zeige mir die Auslastung am Flughafen Frankfurt"
    Then sollte der Agent das MCP-Tool "get_locations_summary" aufrufen
    And die Antwort sollte als semantisches A2UI-Widget "LocationSummaryWidget" formatiert sein
    And der JSON-LD Payload sollte den "@type" "Location" enthalten
    And die "bcc:euQuotaCapacity" sollte validiert im SHACL-Shape enthalten sein
