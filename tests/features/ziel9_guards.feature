Feature: Ziel-9-Schutzregeln (HF-17, HF-18, HF-19, HF-22)
  Als Sachbearbeiter
  möchte ich, dass das System dateninkonsistente Aktionen verhindert
  damit Belegungs- und Kapazitätsdaten jederzeit korrekt sind.

  Background:
    Given die API läuft auf http://localhost:8000

  # ---------------------------------------------------------------------------
  # HF-18: Raum-Deaktivierungsschutz
  # ---------------------------------------------------------------------------

  Scenario: Raum mit aktiver Belegung kann nicht deaktiviert werden
    Given ein belegtes Bett in einem Raum existiert
    When ich DELETE /api/rooms/{room_id} sende
    Then ist der HTTP-Status 409
    And die Fehlermeldung enthält "aktive Belegung"

  Scenario: Leerer Raum kann deaktiviert werden
    Given ein Raum existiert
    When ich DELETE /api/rooms/{room_id} sende
    Then ist der HTTP-Status 200

  # ---------------------------------------------------------------------------
  # HF-19: Kontingent-Änderung unter Belegungszahl
  # ---------------------------------------------------------------------------

  Scenario: Kontingent kann nicht unter aktuelle Belegungszahl gesenkt werden
    Given eine Location mit Kontingent 10 und 3 aktiven Belegungen existiert
    When ich PATCH /api/locations/{location_id} mit Kontingent 2 sende
    Then ist der HTTP-Status 409
    And die Fehlermeldung enthält "Belegung"

  Scenario: Kontingent kann auf die aktuelle Belegungszahl gesetzt werden
    Given eine Location mit Kontingent 10 und 3 aktiven Belegungen existiert
    When ich PATCH /api/locations/{location_id} mit Kontingent 3 sende
    Then ist der HTTP-Status 200

  # ---------------------------------------------------------------------------
  # HF-17: Gültigkeitszeitraum-Enforcement
  # ---------------------------------------------------------------------------

  Scenario: Belegung auf inaktiver Einrichtung (valid_until überschritten) schlägt fehl
    Given eine Location mit abgelaufenem Gültigkeitszeitraum existiert
    When ich POST /api/beds/{bed_id}/occupancy mit heutigem Belegungsstart sende
    Then ist der HTTP-Status 409
    And die Fehlermeldung enthält "inaktiv"

  Scenario: Belegung auf Einrichtung ohne Gültigkeitsbeschränkung funktioniert
    Given ein Bett vom Typ KONTINGENT existiert
    When ich POST /api/beds/{bed_id}/occupancy sende mit AZR-ID "AZR-VALID" und Belegungsende in 10 Tagen
    Then ist der HTTP-Status 201

  # ---------------------------------------------------------------------------
  # HF-22: Notbett-Verlängerung
  # ---------------------------------------------------------------------------

  Scenario: Notbett-Belegung kann einmalig um 1 Tag verlängert werden
    Given eine laufende Notbett-Belegung existiert
    When ich POST /api/occupants/{occupancy_id}/extend sende
    Then ist der HTTP-Status 200
    And die Antwort enthält ein "belegung_ende"-Feld
    And die Antwort enthält "extended_once" mit Wert true

  Scenario: Notbett-Belegung kann nicht zweimal verlängert werden
    Given eine bereits verlängerte Notbett-Belegung existiert
    When ich POST /api/occupants/{occupancy_id}/extend sende
    Then ist der HTTP-Status 409
    And die Fehlermeldung enthält "bereits einmal"

  Scenario: Kontingent-Belegung kann nicht über extend-Endpoint verlängert werden
    Given ein belegtes Bett existiert
    When ich POST /api/occupants/{occupancy_id}/extend sende
    Then ist der HTTP-Status 422
    And die Fehlermeldung enthält "Notbett"
