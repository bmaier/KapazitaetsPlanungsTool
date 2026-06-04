# Reservation Workflow Feature
# Tests for Ziel 3b: reservation requests, task inbox, and SSE notifications
#
# NOTE: SSE (Server-Sent Events) cannot be tested synchronously in Behave.
# The SSE scenario is documented here for reference but skipped in automated runs.
# Manual verification: open GET /api/notifications/stream in a browser or curl --no-buffer,
# then create a reservation — a data-event should appear within 10 seconds.

Feature: Reservierungsworkflow und Postkorb
  Als Sachbearbeiter einer Einrichtung (SB)
  möchte ich Reservierungsanfragen stellen, bestätigen, ablehnen und zurückziehen,
  damit freie Kapazitäten zwischen Einrichtungen koordiniert werden können.

  Background:
    Given die API läuft auf http://localhost:8000
    And zwei aktive Einrichtungen A und B existieren
    And eine dritte Einrichtung C existiert

  Scenario: Reservierung erstellen erzeugt PENDING-Status und Task für Zieleinrichtung
    When ich POST /api/reservations sende als Einrichtung A mit Ziel B
    Then ist der HTTP-Status 201
    And die Reservierungsantwort enthält Status "PENDING"
    And die Reservierungsantwort enthält ein "id"-Feld
    And GET /api/tasks für Einrichtung B enthält eine neue Task vom Typ "RESERVATION_RECEIVED"

  Scenario: Reservierung erstellen schlägt fehl wenn Requester gleich Target
    When ich POST /api/reservations sende als Einrichtung A mit Ziel A
    Then ist der HTTP-Status 422

  Scenario: Zieleinrichtung bestätigt Reservierung
    Given eine Reservierung von A nach B im Status PENDING existiert
    When ich POST /api/reservations/{reservation_id}/confirm sende als Einrichtung B
    Then ist der HTTP-Status 200
    And die Reservierungsantwort enthält Status "CONFIRMED"
    And GET /api/tasks für Einrichtung A enthält eine neue Task vom Typ "RESERVATION_CONFIRMED"

  Scenario: Dritte Einrichtung kann Reservierung nicht bestätigen
    Given eine Reservierung von A nach B im Status PENDING existiert
    When ich POST /api/reservations/{reservation_id}/confirm sende als Einrichtung C
    Then ist der HTTP-Status 403

  Scenario: Zieleinrichtung lehnt Reservierung ab
    Given eine Reservierung von A nach B im Status PENDING existiert
    When ich POST /api/reservations/{reservation_id}/reject sende als Einrichtung B
    Then ist der HTTP-Status 200
    And die Reservierungsantwort enthält Status "REJECTED"
    And GET /api/tasks für Einrichtung A enthält eine neue Task vom Typ "RESERVATION_REJECTED"

  Scenario: Requester zieht Reservierung zurück (CANCELLED)
    Given eine Reservierung von A nach B im Status PENDING existiert
    When ich DELETE /api/reservations/{reservation_id} sende als Einrichtung A
    Then ist der HTTP-Status 200
    And die Reservierungsantwort enthält Status "CANCELLED"

  Scenario: Dritte Einrichtung kann Reservierung nicht zurückziehen (403)
    Given eine Reservierung von A nach B im Status PENDING existiert
    When ich DELETE /api/reservations/{reservation_id} sende als Einrichtung C
    Then ist der HTTP-Status 403

  Scenario: TRANSFERRED-Reservierung kann nicht zurückgezogen werden (409)
    Given eine Reservierung von A nach B im Status TRANSFERRED existiert
    When ich DELETE /api/reservations/{reservation_id} sende als Einrichtung A
    Then ist der HTTP-Status 409

  Scenario: Postkorb liefert Tasks für die eigene Einrichtung
    Given eine Reservierung von A nach B im Status PENDING existiert
    When ich GET /api/tasks sende als Einrichtung B
    Then ist der HTTP-Status 200
    And die Antwort ist eine nicht-leere Liste

  Scenario: Postkorb kann nach Priorität gefiltert werden
    Given eine Reservierung von A nach B im Status PENDING existiert
    When ich GET /api/tasks?priority=HIGH sende als Einrichtung B
    Then ist der HTTP-Status 200

  # --- Neue Szenarien: POST /cancel + GET /{id} (Dialog + Stornierung) ---

  Scenario: GET /api/reservations/{id} gibt Reservierungsdetails zurück
    Given eine Reservierung von A nach B im Status PENDING existiert
    When ich GET /api/reservations/{reservation_id} sende als Einrichtung A
    Then ist der HTTP-Status 200
    And die Antwort enthält Felder "id", "azr_id", "status"

  Scenario: GET /api/reservations/{id} für Ziel-Einrichtung ebenfalls erlaubt
    Given eine Reservierung von A nach B im Status PENDING existiert
    When ich GET /api/reservations/{reservation_id} sende als Einrichtung B
    Then ist der HTTP-Status 200

  Scenario: GET /api/reservations/{id} für dritte Einrichtung verboten
    Given eine Reservierung von A nach B im Status PENDING existiert
    When ich GET /api/reservations/{reservation_id} sende als Einrichtung C
    Then ist der HTTP-Status 403

  Scenario: Requester storniert mit POST /cancel und Begründung
    Given eine Reservierung von A nach B im Status PENDING existiert
    When ich POST /api/reservations/{reservation_id}/cancel sende als Einrichtung A mit Grund "Kapazität gesichert"
    Then ist der HTTP-Status 200
    And die Reservierungsantwort enthält Status "CANCELLED"

  Scenario: Ziel-Einrichtung darf POST /cancel NICHT aufrufen
    Given eine Reservierung von A nach B im Status PENDING existiert
    When ich POST /api/reservations/{reservation_id}/cancel sende als Einrichtung B mit Grund "Bett nicht mehr frei"
    Then ist der HTTP-Status 403

  Scenario: Dritte Einrichtung darf POST /cancel nicht aufrufen
    Given eine Reservierung von A nach B im Status PENDING existiert
    When ich POST /api/reservations/{reservation_id}/cancel sende als Einrichtung C mit Grund "Versuch"
    Then ist der HTTP-Status 403

  Scenario: Reader-User ohne Schreibberechtigung erhält 403 bei POST /cancel
    Given eine Reservierung von A nach B im Status PENDING existiert
    When ich POST /api/reservations/{reservation_id}/cancel sende als Reader-User von Einrichtung A mit Grund "Test"
    Then ist der HTTP-Status 403

  Scenario: POST /cancel setzt offene Tasks auf DONE
    Given eine Reservierung von A nach B im Status PENDING existiert
    When ich POST /api/reservations/{reservation_id}/cancel sende als Einrichtung A mit Grund "Storniertest"
    Then ist der HTTP-Status 200
    And alle Tasks der Reservierung haben Status "DONE" oder "CANCELLED"

  Scenario: Bereits stornierte Reservierung kann nicht nochmals storniert werden (409)
    Given eine Reservierung von A nach B im Status PENDING existiert
    When ich POST /api/reservations/{reservation_id}/cancel sende als Einrichtung A mit Grund "Erster Versuch"
    And ich POST /api/reservations/{reservation_id}/cancel sende als Einrichtung A mit Grund "Zweiter Versuch"
    Then ist der HTTP-Status 409

  # SSE: nicht per Behave testbar (blockierender Stream)
  # Manuelle Verifikation:
  #   curl -N -H "Authorization: Bearer <token>" -H "X-Location-Id: <B-uuid>" \
  #        http://localhost:8000/api/notifications/stream
  # → nach POST /api/reservations (target=B) erscheint data-Event innerhalb 10s
