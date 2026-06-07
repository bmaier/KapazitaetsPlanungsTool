# Feature: Zeitraum-Gültigkeitsprüfung
#
# Sicherstellt, dass Betten, Räume und Einrichtungen nur für Zeiträume
# angeboten und gebucht werden, in denen sie tatsächlich vollständig verfügbar sind.
# Deckt die in Ziel-D fixierten Edge-Cases ab:
#   - deaktiviert_ab muss >= period_end sein (nicht nur > period_start)
#   - valid_until muss >= period_end sein (nicht nur > period_start)
#   - valid_from muss <= period_start sein
#   - is_active muss auch bei scoped-Suche geprüft werden
#   - Kaskade: Einrichtung → Raum → Bett

Feature: Zeitraum-Gültigkeitsprüfung bei Bettsuche, Belegung und Reservierung
  Als Sachbearbeiter
  möchte ich sicherstellen, dass Betten, Räume und Einrichtungen
  nur für Zeiträume angeboten und gebucht werden können,
  in denen sie tatsächlich für den gesamten gewünschten Zeitraum verfügbar sind.

  Background:
    Given die API läuft auf http://localhost:8000
    And eine Einrichtung mit einem freien Kontingent-Bett für Gültigkeitstests existiert

  # ─────────────────────────────────────────────────────────────────
  # Bettsuche (POST /api/suggestions)
  # ─────────────────────────────────────────────────────────────────

  Scenario: Bettsuche schließt Bett aus, dessen deaktiviert_ab vor Periodenende liegt
    Given das Bett wird in der Mitte des Suchzeitraums deaktiviert
    When ich eine Bettsuche für den gesamten Zeitraum durchführe
    Then sind keine Vorschläge für dieses Bett verfügbar

  Scenario: Bettsuche schließt Bett aus, dessen valid_from nach dem Periodenstart liegt
    Given das Bett ist erst nach dem Beginn des Suchzeitraums gültig
    When ich eine Bettsuche für den gesamten Zeitraum durchführe
    Then sind keine Vorschläge für dieses Bett verfügbar

  Scenario: Bettsuche schließt Raum aus, dessen valid_until vor dem Periodenende liegt
    Given der Raum des Betts endet vor dem Ende des Suchzeitraums
    When ich eine Bettsuche für den gesamten Zeitraum durchführe
    Then sind keine Vorschläge für dieses Bett verfügbar

  Scenario: Bettsuche schließt Bett aus, wenn Einrichtung deaktiviert ist
    Given die Einrichtung ist deaktiviert
    When ich eine lokale Bettsuche als Mitglied dieser Einrichtung durchführe
    Then ist der HTTP-Status 403

  Scenario: Bettsuche findet Bett, das für den gesamten Zeitraum gültig ist
    Given das Bett hat keine einschränkenden Gültigkeitsdaten
    When ich eine Bettsuche für den gesamten Zeitraum durchführe
    Then enthält die Antwort mindestens einen Vorschlag

  # ─────────────────────────────────────────────────────────────────
  # Belegungsanlage (POST /api/beds/{id}/occupancy)
  # ─────────────────────────────────────────────────────────────────

  Scenario: Belegung wird abgelehnt, wenn Einrichtung zum Belegungszeitraum deaktiviert ist
    Given die Einrichtung ist deaktiviert
    When ich versuche eine Belegung für das Bett anzulegen
    Then ist der HTTP-Status 409
    And die Fehlermeldung enthält "deaktiviert"

  Scenario: Belegung wird abgelehnt, wenn belegung_ende die valid_until der Einrichtung überschreitet
    Given die Einrichtung läuft vor dem Ende des gewünschten Belegungszeitraums aus
    When ich eine Belegung anlege, die über das Einrichtungsende hinausgeht
    Then ist der HTTP-Status 409
    And die Fehlermeldung enthält "Einrichtung"

  Scenario: Belegung wird abgelehnt, wenn belegung_start vor dem valid_from des Betts liegt
    Given das Bett ist erst nach dem Beginn des gewünschten Belegungszeitraums gültig
    When ich eine Belegung anlege, die vor dem Gültigkeitsbeginn des Betts beginnt
    Then ist der HTTP-Status 409
    And die Fehlermeldung enthält "Bett"

  Scenario: Belegung wird abgelehnt, wenn belegung_ende über das deaktiviert_ab des Betts hinausgeht
    Given das Bett wird in der Mitte des gewünschten Belegungszeitraums deaktiviert
    When ich eine Belegung anlege, die über das Deaktivierungsdatum des Betts hinausgeht
    Then ist der HTTP-Status 409
    And die Fehlermeldung enthält "Bett"

  Scenario: Belegung wird abgelehnt, wenn belegung_ende die valid_until des Raums überschreitet
    Given der Raum des Betts läuft vor dem Ende des gewünschten Belegungszeitraums aus
    When ich eine Belegung anlege, die über das Raumende hinausgeht
    Then ist der HTTP-Status 409
    And die Fehlermeldung enthält "Raum"

  # ─────────────────────────────────────────────────────────────────
  # Verlegungsanfrage (POST /api/reservations)
  # ─────────────────────────────────────────────────────────────────

  Scenario: Verlegungsanfrage wird abgelehnt, wenn Zieleinrichtung deaktiviert ist
    Given eine zweite Einrichtung als Ziel existiert und deaktiviert wurde
    When ich eine Verlegungsanfrage zur deaktivierten Zieleinrichtung stelle
    Then ist der HTTP-Status 409
    And die Fehlermeldung enthält "deaktiviert"

  Scenario: Verlegungsanfrage wird abgelehnt, wenn belegung_ende die valid_until der Zieleinrichtung überschreitet
    Given eine zweite Einrichtung als Ziel existiert und läuft vor dem Belegungsende aus
    When ich eine Verlegungsanfrage stelle, deren Ende über die Gültigkeit der Zieleinrichtung hinausgeht
    Then ist der HTTP-Status 409
    And die Fehlermeldung enthält "Verfügbarkeit"

  # ─────────────────────────────────────────────────────────────────
  # period_available Flag in bed-status API
  # ─────────────────────────────────────────────────────────────────

  Scenario: bed-status gibt period_available=false zurück für Bett mit deaktiviert_ab innerhalb des Zeitraums
    Given das Bett wird in der Mitte des Suchzeitraums deaktiviert
    When ich GET /api/locations/{id}/bed-status mit dem Suchzeitraum abfrage
    Then hat das Bett in der Antwort period_available = false

  Scenario: bed-status gibt period_available=true zurück für uneingeschränktes Bett
    Given das Bett hat keine einschränkenden Gültigkeitsdaten
    When ich GET /api/locations/{id}/bed-status mit dem Suchzeitraum abfrage
    Then hat das Bett in der Antwort period_available = true
