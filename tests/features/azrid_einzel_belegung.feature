# AZR-ID Einzel-Belegungs-Guard
# Testet den Backend-Guard in create_occupancy, der doppelte aktive Belegungen
# pro azr_id verhindert.
#
# Guard-Logik:
#   - Ohne verlegung_grund + überlappende Belegung → 409 mit Fehlermeldung
#   - Mit verlegung_grund → Guard wird übersprungen, 201 (internes Verlegen)
#   - Nicht-überlappender Zeitraum → kein Guard, 201
#   - Nur historische Belegung (Ende gestern) → kein Guard, 201

Feature: AZR-ID Einzel-Belegungs-Guard
  Als Sachbearbeiter
  möchte ich, dass das System verhindert, dass eine Person gleichzeitig in mehreren
  Betten aktiv belegt ist,
  damit die Belegungsintegrität gewährleistet bleibt.

  Background:
    Given die API läuft auf http://localhost:8000
    And eine Einrichtung mit zwei Betten für den Guard-Test existiert

  Scenario: Doppelbuchung ohne verlegung_grund führt zu 409
    Given eine Person ist in Bett 1 aktiv belegt
    When ich versuche dieselbe Person ohne verlegung_grund in Bett 2 einzubuchen
    Then ist der HTTP-Status 409

  Scenario: Fehlermeldung bei Doppelbuchung enthält azr_id
    Given eine Person ist in Bett 1 aktiv belegt
    When ich versuche dieselbe Person ohne verlegung_grund in Bett 2 einzubuchen
    Then ist der HTTP-Status 409
    And die Fehlermeldung enthält "bereits aktiv belegt"

  Scenario: Einbuchung MIT verlegung_grund umgeht den Guard und liefert 201
    Given eine Person ist in Bett 1 aktiv belegt
    When ich dieselbe Person mit verlegung_grund in Bett 2 einbuche
    Then ist der HTTP-Status 201

  Scenario: Nicht-überlappender Zeitraum löst den Guard nicht aus
    Given eine Person ist in Bett 1 aktiv belegt
    When ich dieselbe Person ohne verlegung_grund in Bett 2 für einen nicht-überlappenden Zeitraum einbuche
    Then ist der HTTP-Status 201

  Scenario: Nur historische Belegung (Ende gestern) löst den Guard nicht aus
    Given eine Person hat nur eine historische Belegung in Bett 1 (Ende gestern)
    When ich dieselbe Person ohne verlegung_grund in Bett 2 einbuche
    Then ist der HTTP-Status 201
