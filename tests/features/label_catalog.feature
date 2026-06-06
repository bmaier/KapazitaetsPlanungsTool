# encoding: utf-8
@label_catalog
Feature: Label-Katalog Verwaltung
  Als System-Admin möchte ich den Label-Katalog verwalten können,
  damit Labels mit referenzieller Integrität in der DB gespeichert werden.

  Background:
    Given der Label-Katalog enthält mindestens einen Eintrag
    And ich bin als system-admin authentifiziert

  Scenario: Label anlegen
    When ich POST /api/label-catalog mit {"name": "Test-Label-BDD", "entity_type": "ROOM", "category": "Test", "color": "#aabbcc"} sende
    Then der HTTP-Status ist 201
    And GET /api/labels enthält ein Label mit name "Test-Label-BDD" und entity_type "ROOM"

  Scenario: Duplikat anlegen ergibt 409
    Given das Label "Test-Label-BDD" für entity_type "ROOM" existiert bereits im Katalog
    When ich POST /api/label-catalog mit {"name": "Test-Label-BDD", "entity_type": "ROOM", "category": "Test", "color": "#aabbcc"} sende
    Then der HTTP-Status ist 409

  Scenario: System-Label löschen ergibt 409
    Given das Label "Männer" für entity_type "ROOM" ist ein System-Label
    When ich DELETE /api/label-catalog/ROOM/Männer sende
    Then der HTTP-Status ist 409
    And die Fehlermeldung enthält "Pflicht-Label"

  Scenario: In-Verwendung-Label löschen ergibt 409
    Given das Label "Test-Label-InUse" für entity_type "ROOM" existiert bereits im Katalog
    And ein Raum hat das Label "Test-Label-InUse" gesetzt
    When ich DELETE /api/label-catalog/ROOM/Test-Label-InUse sende
    Then der HTTP-Status ist 409
    And die Fehlermeldung enthält "in Verwendung"

  Scenario: Nicht-verwendetes Label löschen ergibt 200
    Given das Label "Test-Label-Unused" für entity_type "BED" existiert im Katalog und ist nicht in Verwendung
    When ich DELETE /api/label-catalog/BED/Test-Label-Unused sende
    Then der HTTP-Status ist 200
    And GET /api/labels enthält kein Label mit name "Test-Label-Unused" und entity_type "BED"

  Scenario: Writer darf Label-Katalog nicht schreiben
    Given ich bin als writer authentifiziert
    When ich POST /api/label-catalog mit {"name": "Unauthorized-Label", "entity_type": "ROOM", "category": "Test", "color": "#000000"} sende
    Then der HTTP-Status ist 403

  Scenario: PATCH labels mit unbekanntem Label ergibt 422
    Given ein Raum mit ID aus der Datenbank existiert
    When ich PATCH /api/rooms/{room_id}/labels mit ["NichtImKatalog-XYZ"] sende
    Then der HTTP-Status ist 422
