@agent
Feature: Agentic Betten- und Raumpflege (Capacity Management)
  Als Einrichtungsleiter
  Möchte ich dem Agenten mitteilen, dass ein Raum ein neues Label hat oder ein Bett gesperrt wird
  Damit ich das System via Chat aktualisieren kann, ohne tiefe Menüs zu durchsuchen.

  Scenario: Hinzufügen eines Labels zu einem Raum
    Given der MCP-Server ist mit der FastAPI verbunden
    And der "CapacityManagerSkill" ist im "FacilityAgent" initialisiert
    When der Benutzer im Chat schreibt: "Setze Raum A auf rollstuhlgerecht"
    Then sollte der Agent das MCP-Tool "update_room_labels" aufrufen
    And die Antwort sollte als semantisches A2UI-Widget "LabelChipsWidget" formatiert sein
    And der JSON-LD Payload sollte den "@type" "Room" und die neuen "bcc:labels" enthalten
    And die Änderungen sollten durch SHACL Constraints validiert werden
