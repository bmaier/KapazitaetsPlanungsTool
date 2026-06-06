# Stornierungsberechtigungsmodell — Postkorb-Sicht
# Dokumentiert und testet, welche Einrichtungen eine Reservierungsanfrage
# stornieren dürfen (DELETE /api/reservations/{id}).
#
# Berechtigungsregeln:
#   - Anfragende Einrichtung (Requester) darf PENDING-Anfrage stornieren → 200 + CANCELLED
#   - Anfragende Einrichtung darf CONFIRMED-Anfrage stornieren → 200 + CANCELLED
#   - Zieleinrichtung darf fremde Anfrage NICHT stornieren → 403
#   - Dritte Einrichtung darf nicht stornieren → 403

Feature: Stornierungsberechtigungsmodell im Postkorb
  Als Sachbearbeiter einer anfragenden Einrichtung
  möchte ich eigene Reservierungsanfragen stornieren können,
  damit abgesagte Verlegungen korrekt abgebildet werden,
  ohne dass Ziel- oder Dritteinrichtungen unbefugt stornieren können.

  Background:
    Given die API läuft auf http://localhost:8000
    And zwei aktive Einrichtungen A und B existieren
    And eine dritte Einrichtung C existiert

  Scenario: Anfragende Einrichtung storniert eigene PENDING-Anfrage erfolgreich
    Given eine Reservierung von A nach B im Status PENDING existiert
    When ich DELETE /api/reservations/{reservation_id} sende als Einrichtung A
    Then ist der HTTP-Status 200
    And die Reservierungsantwort enthält Status "CANCELLED"

  Scenario: Zieleinrichtung kann fremde Anfrage nicht stornieren
    Given eine Reservierung von A nach B im Status PENDING existiert
    When ich DELETE /api/reservations/{reservation_id} sende als Einrichtung B
    Then ist der HTTP-Status 403

  Scenario: Dritte Einrichtung kann Anfrage nicht stornieren
    Given eine Reservierung von A nach B im Status PENDING existiert
    When ich DELETE /api/reservations/{reservation_id} sende als Einrichtung C
    Then ist der HTTP-Status 403
