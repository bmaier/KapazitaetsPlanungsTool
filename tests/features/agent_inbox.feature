@agent
Feature: Agentic Task Inbox und Genehmigungen (Postkorb)
  Als Einrichtungsleiter
  Möchte ich meine offenen Aufgaben und Genehmigungen über den Chat verwalten
  Damit ich Verlegungsanfragen schnell bestätigen oder ablehnen kann, ohne das Postkorb-Menü aufzurufen.

  Scenario: Offene Aufgaben abrufen und genehmigen
    Given der MCP-Server ist mit der FastAPI verbunden
    And der "TaskResolutionSkill" ist im "InboxAgent" initialisiert
    When der Benutzer im Chat schreibt: "Zeige meinen Postkorb"
    Then sollte der Agent das MCP-Tool "get_inbox_tasks" aufrufen
    And die Antwort sollte als semantisches A2UI-Widget "TaskInboxWidget" formatiert sein
    And der JSON-LD Payload sollte eine Liste der offenen Tasks (z. B. Reservierungsanfragen) enthalten
    And der Benutzer kann interaktiv auf "Genehmigen" klicken, was das MCP Tool "resolve_task" triggert
