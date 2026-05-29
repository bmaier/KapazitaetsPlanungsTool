Feature: Bettsuche — SuggestionWizard
  Als Sachbearbeiter einer Einrichtung
  möchte ich für eine Person alle freien Betten an allen aktiven Einrichtungen sehen,
  damit ich das passende Bett gezielt auswählen kann.

  Background:
    Given die API läuft auf http://localhost:8000
    And die Datenbank ist leer (Suggestion-Test-Isolation)
    And eine Einrichtung "Quelle" mit ID "src-loc" existiert mit 0 freien Betten
    And eine Einrichtung "Ziel-A" mit ID "dst-a" existiert mit 3 freien Männerbetten
    And eine Einrichtung "Ziel-B" mit ID "dst-b" existiert mit 5 freien Männerbetten

  # ─── Varianten-Anzahl ──────────────────────────────────────────────────────

  Scenario: Einzelperson-Suche liefert jedes freie Bett als eigene Variante
    When ich POST /api/suggestions sende als Einrichtung "src-loc" mit anzahl=1 geschlecht=M cross_location=true
    Then ist der HTTP-Status 200
    And die Antwort enthält genau 8 Varianten
    And jede Variante enthält genau 1 Bett

  Scenario: Pro Zieleinrichtung werden alle freien Betten zurückgegeben
    When ich POST /api/suggestions sende als Einrichtung "src-loc" mit anzahl=1 geschlecht=M cross_location=true
    Then ist der HTTP-Status 200
    And die Einrichtung "Ziel-A" ist in 3 Varianten vertreten
    And die Einrichtung "Ziel-B" ist in 5 Varianten vertreten

  Scenario: Einrichtung ohne freie Betten erscheint nicht in Varianten
    When ich POST /api/suggestions sende als Einrichtung "src-loc" mit anzahl=1 geschlecht=M cross_location=true
    Then ist der HTTP-Status 200
    And die Einrichtung "Quelle" erscheint nicht in den Varianten

  # ─── Genderfilter ─────────────────────────────────────────────────────────

  Scenario: Frauensuche liefert keine Männer-Betten
    Given eine Einrichtung "Ziel-C" mit ID "dst-c" existiert mit 2 freien Frauenbetten
    When ich POST /api/suggestions sende als Einrichtung "src-loc" mit anzahl=1 geschlecht=W cross_location=true
    Then ist der HTTP-Status 200
    And alle Varianten gehören zu Frauenräumen
    And die Einrichtung "Ziel-A" erscheint nicht in den Varianten

  # ─── Einzelstandort-Suche ─────────────────────────────────────────────────

  Scenario: Lokale Suche (cross_location=false) liefert nur eigene Einrichtung
    Given eine Einrichtung "Lokal" mit ID "local-loc" existiert mit 4 freien Männerbetten
    When ich POST /api/suggestions sende als Einrichtung "local-loc" mit anzahl=1 geschlecht=M cross_location=false
    Then ist der HTTP-Status 200
    And alle Varianten gehören zur Einrichtung "Lokal"

  # ─── Gruppen-Suche (anzahl > 1) ───────────────────────────────────────────

  Scenario: Gruppen-Suche gibt pro Einrichtung maximal 2 kompakte Varianten zurück
    When ich POST /api/suggestions sende als Einrichtung "src-loc" mit anzahl=2 geschlecht=M cross_location=true
    Then ist der HTTP-Status 200
    And die Einrichtung "Ziel-B" ist in maximal 2 Varianten vertreten
    And jede Variante enthält genau 2 Betten
