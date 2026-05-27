Feature: Kapazitäts-CRUD API
  Als Sachbearbeiter
  möchte ich Einrichtungen, Räume, Betten und Belegungen verwalten
  damit ich den Belegungsstand nachverfolgen kann

  Background:
    Given die API läuft auf http://localhost:8000
    And die EU-Gesamtquote ist auf 200 gesetzt

  Scenario: Einrichtung erstellen
    When ich POST /api/locations sende mit Name "Grenzeinrichtung A" und Kontingent 50
    Then ist der HTTP-Status 201
    And die Antwort enthält ein "id"-Feld
    And die Antwort enthält "name" mit Wert "Grenzeinrichtung A"

  Scenario: EU-Gesamtquote wird überschritten
    Given eine Location mit Kontingent 190 existiert
    When ich POST /api/locations sende mit Kontingent 20
    Then ist der HTTP-Status 422
    And die Fehlermeldung enthält "EU-Gesamtquote"

  Scenario: Raum zu Einrichtung hinzufügen
    Given eine Location existiert
    When ich POST /api/locations/{location_id}/rooms sende mit Name "Raum 1" und Geschlechtsdesignation "M"
    Then ist der HTTP-Status 201
    And die Antwort enthält "geschlechts_designation" mit Wert "M"

  Scenario: Bett zu Raum hinzufügen
    Given ein Raum existiert
    When ich POST /api/rooms/{room_id}/beds sende mit Nummer "B-001" und Typ "KONTINGENT"
    Then ist der HTTP-Status 201
    And die Antwort enthält "bett_typ" mit Wert "KONTINGENT"

  Scenario: Belegung erstellen (Normalfall)
    Given ein Bett vom Typ KONTINGENT existiert
    When ich POST /api/beds/{bed_id}/occupancy sende mit AZR-ID "AZR-12345" und Belegungsende in 30 Tagen
    Then ist der HTTP-Status 201
    And die Antwort enthält "azr_id" mit Wert "AZR-12345"

  Scenario: 12-Wochen-Warnung
    Given ein Bett vom Typ KONTINGENT existiert
    When ich POST /api/beds/{bed_id}/occupancy sende mit Belegungsende in 90 Tagen
    Then ist der HTTP-Status 201
    And der Response-Header "X-12W-Warning" hat Wert "true"

  Scenario: Notbett - Belegung länger als 1 Nacht
    Given ein Bett vom Typ NOTBETT existiert
    When ich POST /api/beds/{bed_id}/occupancy sende mit Belegungsende in 3 Tagen
    Then ist der HTTP-Status 422
    And die Fehlermeldung enthält "Notbett"

  Scenario: Doppelbelegung verhindert
    Given ein belegtes Bett existiert
    When ich erneut POST /api/beds/{bed_id}/occupancy sende
    Then ist der HTTP-Status 422
    And die Fehlermeldung enthält "bereits belegt"

  Scenario: Belegung beenden
    Given ein belegtes Bett existiert
    When ich DELETE /api/beds/{bed_id}/occupancy/{occupancy_id} sende
    Then ist der HTTP-Status 200
    And die Antwort enthält ein "ended"-Feld

  Scenario: Einrichtung deaktivieren (Soft-Delete)
    Given eine Location existiert
    When ich DELETE /api/locations/{location_id} sende
    Then ist der HTTP-Status 200
    And GET /api/locations gibt die Location nicht zurück
    And GET /api/locations/{location_id} zeigt is_active als false
