Feature: Konsistenzregeln für aktive Verlegungsanfragen
  Als Sachbearbeiter
  möchte ich nicht versehentlich Personen ausbuchen oder doppelt einbuchen,
  wenn eine aktive Verlegungsanfrage läuft.

  Background:
    Given die API läuft auf http://localhost:8000

  Scenario: Ausbuchen bei aktiver PENDING-Reservation blockiert (409)
    Given eine Person mit PENDING-Reservation ist aktiv belegt
    When ich die Belegung per DELETE beende
    Then ist der HTTP-Status 409
    And die Fehlermeldung enthält "Verlegungsanfrage"

  Scenario: Ausbuchen bei aktiver CONFIRMED-Reservation blockiert (409)
    Given eine Person mit CONFIRMED-Reservation ist aktiv belegt
    When ich die Belegung per DELETE beende
    Then ist der HTTP-Status 409

  Scenario: Ausbuchen ohne aktive Reservation möglich (200)
    Given eine Person ohne aktive Reservation ist aktiv belegt
    When ich die Belegung per DELETE mit Grund "Auszug" beende
    Then ist der HTTP-Status 200
    And das Audit-Event OCCUPANCY_DELETED enthält den Grund "Auszug"

  Scenario: Ein-Platz-Regel blockiert Cross-Location-Einbuchung (409)
    Given eine Person ist aktiv in Einrichtung Alpha belegt
    When ich versuche dieselbe Person in Einrichtung Beta einzubuchen
    Then ist der HTTP-Status 409
    And die Fehlermeldung enthält "Ein-Platz"

  Scenario: Internes Verlegen bei aktiver Person erlaubt (201)
    Given eine Person ist aktiv in Einrichtung Alpha belegt
    When ich dieselbe Person in ein anderes Bett in Einrichtung Alpha einbuche
    Then ist der HTTP-Status 201

  Scenario: Cross-Location-Einbuchung bei PENDING-Reservation blockiert (409)
    Given eine Person hat eine PENDING-Reservation von Alpha nach Beta
    When ich versuche dieselbe Person in Einrichtung Gamma einzubuchen
    Then ist der HTTP-Status 409

  Scenario: Internes Verlegen mit PENDING-Reservation erlaubt (201)
    Given eine Person hat eine PENDING-Reservation von Alpha nach Beta
    When ich dieselbe Person in ein anderes Bett in Einrichtung Alpha einbuche
    Then ist der HTTP-Status 201
