# Anforderungskonzept: Kapazitäts- und Bettenplanung für BAMF-Grenzverfahren (GEAS-Reform)

## 1. Dokumentensteuerung & Metadaten

* **Projektkontext:** GEAS-Reform (Gemeinsames Europäisches Asylsystem), BMI / BAMF
* **Thema:** Web-Anwendung zur Kapazitäts- und Bettenplanung in geschlossenen/teilgeschlossenen Einrichtungen
* **Moderatoren/Autoren:** Berthold, Kausik
* **Datum des Konzeptstands:** 22. Mai 2026
* **Status:** Bereit für Implementierung (Fokus: Demo-Stack)

---

## 2. Fachlicher Kontext & Strategische Leitplanken

### 2.1 Kontextuelle Rahmenbedingungen

* **Rechtlicher Status:** Asylsuchende in diesem Verfahren gelten rechtlich als „nicht eingereist“. Die Unterbringung erfolgt in geschlossenen oder teilgeschlossenen Einrichtungen.
* **Der 12-Wochen-Timer:** Das Verfahren darf maximal 12 Wochen dauern. Bei Überbelegung oder Zeitüberschreitung wird das Grenzverfahren für nachfolgende Personen rechtlich unmöglich.
* **Kompetenzverteilung:** Das BMI und das BAMF geben den strategischen Rahmen sowie EU-Kapazitätsvorgaben vor. Die operative Umsetzung und Unterbringung liegt in der Zuständigkeit der Bundesländer (z. B. Hessen, Bayern).

### 2.2 Strategische Leitprinzipien

* **Schnelligkeit vor Perfektion:** Fokus auf eine schnelle, lauffähige Umsetzung ohne das Anhäufen von Architekturschulden.
* **YAGNI-Prinzip ("You Ain't Gonna Need It"):** Keine präventiven Compliance-Absicherungen für hypothetische Fälle. Organisatorische Prozesse und Datentransparenz lösen Probleme vor technischem Over-Engineering.
* **Human-in-the-loop:** Das System automatisiert keine finalen Platzbelegungen. Die Letztentscheidung liegt immer beim Sachbearbeiter (SB).

---

## 3. Architektur- & Stack-Strategie (Dual-Stack)

Das System folgt einer strikten **Zwei-Stufen-Strategie**. Die unmittelbare Umsetzung fokussiert sich vollständig auf den **Demo-Stack**, um schnellstmöglich ein visuell und funktional überzeugendes System bereitzustellen.

```
+-----------------------------------------------------------------------+
| Architektonischer Kern (Gemeinsame Fachlogik & Datenmodell)           |
| - Hexagonale Architektur (Ports & Adapter)                            |
| - Lokale Datensouveränität (Offline-first, MBTiles, Keycloak)          |
+-----------------------------------------------------------------------+
                                   |
         +-------------------------+-------------------------+
         |                                                   |
         v                                                   v
+---------------------------------+ +---------------------------------+
| STUFE 1: Demo Stack (Prio: Sofort)| | STUFE 2: Enterprise Stack (Abruf)|
| - Python / FastAPI              | | - Java Spring Boot Modulith     |
| - React + MUI (Material UI)     | | - Angular + Angular Material    |
| - Docker Compose                | | - Helm Charts + K3S + Istio     |
+---------------------------------+ +---------------------------------+

```

### 3.1 Stufe 1: Demo Stack (Höchste Priorität für initiale Phase)

Ziel ist ein voll funktionsfähiges, lokal installierbares System mit moderner, ansprechender UI ohne Infrastruktur-Overhead.

* **Backend:** Python / FastAPI
* **Frontend:** React + MUI (Material UI) + Tailwind CSS
* **Datenbank:** PostgreSQL (im Docker-Container)
* **Authentifizierung:** Keycloak (vereinfacht in Docker) oder JWT-basiert
* **Deployment:** Ein zentrales Shell-Skript + Docker Compose. Lauffähig auf einem einzelnen Rechner ohne Kubernetes-Vorkenntnisse.
* **Karten-Infrastruktur:** Lokale MBTiles + Tile-Server (Docker-Container).

### 3.2 Stufe 2: Enterprise Stack (Optional auf Abruf)

Architektonisch identischer Funktionsumfang, jedoch ausgelegt auf den finalen Betrieb im BAMF-Ziel-Infrastrukturrahmen.

* **Backend:** Java Spring Boot, strukturiert als **Spring Modulith** (Module: `capacity`, `reservations`, `tasks`, `reporting`, `reference-data`, `audit`).
* **BFF (Backend for Frontend):** Schlanker Spring Boot Service für Token-Exchange (Keycloak mit PKCE), API-Aggregation und CSRF-Schutz.
* **Frontend:** Angular SPA + Angular Material + BAMF Corporate Design Theme.
* **Infrastruktur:** K3S (Kubernetes) + Istio Service Mesh (für mTLS, Circuit Breaker, Rate Limiting und Traffic Management). Stateless 12-Factor-Apps.

---

## 4. Funktionale Anforderungen (Functional Requirements)

### [HF-01] Zweistufiges Kapazitätsmodell

* **Konzept:** Strikte Trennung von zwei Kapazitätsebenen in jeder Einrichtung.
1. **Offizielles Kontingent:** EU-quoten-relevant. Mit dem Einzug startet der 12-Wochen-Verfahrenstimer.
2. **Notbetten:** Maximale Verweildauer von 1 Nacht. Zählen *nicht* in das EU-Kontingent und lösen *keinen* Verfahrenstimer aus.


* **Integritätsregel:** Notbetten dürfen im System niemals direkt in das offizielle Kontingent überführt werden, um eine Verfälschung der EU-Compliance-Kennzahlen zu verhindern.

### [HF-02] Reservierungs-Workflow mit konkurrierenden Anfragen

* **Konzept:** Jeder Sachbearbeiter (SB) kann für jede Einrichtung Reservierungsanfragen stellen.
* **Logik:** Parallele Anfragen für dasselbe Bett sind zulässig. Es gilt das *First-come-first-served*-Prinzip im Moment der Bestätigung.
* **Rechte:** Eine Rücknahme/Stornierung ist nur durch den Ersteller der Anfrage oder den SB der Zieleinrichtung möglich.
* **Rechtlicher Übergang:** Mit der Bestätigung der Reservierung wechselt die rechtliche Verantwortung für die Person auf das jeweilige Bundesland.

### [HF-03] Standort-granulares Rollenmodell

* **Konzept:** Berechtigungen basieren auf einer flachen Matrix ohne politische BAMF/Land-Hierarchie: `Rechte = (Lokation × Rolle)`.
* **Rollenprofile:**
* *Lesend:* Kann Belegungen und Status einsehen.
* *Schreibend:* Kann die zugewiesene Lokation operativ verwalten.
* *Admin:* Kann Rollen innerhalb der Lokation zuweisen.
* *System-Admin:* Globaler Vollzugriff.


* **Infrastruktur:** IAM erfolgt lokal über Keycloak. Jede Rollenänderung muss zwingend auditiert werden.

### [HF-04] Raum-Bett-Geschlechtsmodell & Familienschutz

* **Raum-Zuweisung:** Räume besitzen eine dynamische Geschlechtsdesignation (*männlich, weiblich, Familie, divers*). Räume können auch im belegten Zustand umgewidmet werden, um operative Flexibilität zu sichern.
* **Familienschutz (Hard Constraint):** Familienmitglieder unter 18 Jahren sind untrennbar mit ihren Sorgeberechtigten verknüpft (§43 AsylG, EU-RL 2013/33/EU). Eine systemseitige Trennung ist blockiert.
* **Vollbelegungs-Logik:** Bei Vollauslastung ist eine Zusammenlegung von Einzelpersonen im Rahmen der EU-Richtlinien zulässig. Die Wahrung der Familieneinheit agiert hierbei als *Soft-Constraint* (System gibt eine Warnung aus, blockiert aber nicht).

### [HF-05] Belegungsvorschlag-Funktion (Human-in-the-loop)

* **Konzept:** Der SB gibt Constraints ein (z. B. "Unterbringung von 3 Frauen"). Das System berechnet optimale Optionen.
* **Ausgabe:** Anzeige mehrerer Varianten (einrichtungsintern sowie standortübergreifend).
* **Entscheidung:** Der SB wählt manuell. Lehnt er alle Vorschläge ab, kann er eine manuelle Alternative eingeben. Diese Abweichung muss zwingend im Audit-Log dokumentiert werden.
* **Gewichtung (Soft Constraints):** Familieneinheit, verbleibende Restzeit des 12-Wochen-Timers, Geschlechtsdesignation.

### [HF-06] Postkorb & Asynchrones Task-Management

* **Konzept:** Jede Einrichtung verfügt über eine gemeinsame Inbox, die für alle dort zugeordneten SBs einsehbar ist.
* **Task-Typen (Phase 1):** *Übernahmeanfrage, Kontingent-Aufstockungsantrag, Notbett-Meldung, Umbelegungsvorschlag-zur-Entscheidung*.
* **Einschränkung Phase 1:** Die Verwaltung der Task-Typen erfolgt direkt auf Datenbankebene per SQL durch den DB-Admin. Es gibt keine administrative GUI hierfür.

### [HF-07] Dashboard mit datensouveräner Offline-Karte

* **Konzept:** Die Startansicht nach dem Login zeigt alle Einrichtungen auf einer interaktiven, lokal gehosteten Karte (Verwendung von lokalen `MBTiles` + `tileserver-gl`, keine externen API-Aufrufe).
* **Visualisierung:** Ein klares Ampel-Overlay (Grün/Gelb/Rot) signalisiert den Kapazitätsstatus. Die eigene Einrichtung wird permanent oben fixiert.
* **Interaktion:** Ein Klick öffnet die Echtzeit-Belegung (Frei / Offene Reservierungen / Belegt). Analytische Historiendaten oder Statistiken werden auf der Karte bewusst *nicht* dargestellt.

### [HF-08] DSGVO-konformes Minimaldatenmodell (Datensparsamkeit)

* **Personendaten:** Es werden **keine** Klarnamen und **keine** biometrischen Daten erfasst. Pro Person werden ausschließlich folgende Attribute gespeichert:
* `AZR-ID` (Zentrales Ausländerregister-ID, rein manuelle Eingabe ohne Echtzeit-Validierung gegen das AZR)
* `Alias-ID` (z. B. Ausweisnummer oder einrichtungseigene Kennung zur Flexibilität vor Ort)
* `Geschlecht`
* `Klassifikation` (Nur der Status "Kind" ist erlaubt; gesundheitliche Daten wie "Krank" dürfen *nicht* gespeichert werden)
* `Belegungsbeginn` & `Geplantes Belegungsende`


* **Löschfristen:** Automatische Löschung der Personendaten direkt nach Verfahrensabschluss. Audit-Logs unterliegen automatisierten, DSGVO-konformen Löschzyklen.

### [HF-09] EU-Gesamtquote und Verteilungs-Validierung

* **Konzept:** Erfassung der EU-Gesamtkapazitätsvorgabe für Deutschland durch den System-Admin (Read-only nach Eintrag).
* **Logik:** Die Behörden verteilen dieses Kontingent auf die einzelnen Standorte (Lokations-Kontingente). Die Anwendung validiert aggregiert: Die Summe aller Lokations-Kontingente darf das EU-Gesamtkontingent nicht überschreiten (Warnmeldung bei Verletzung).

### [HF-10] Reporting & EU-Compliance-Berichte

* **Analytisches Modul:** Strikt getrennt vom operativen Dashboard existiert eine separate Reporting-Ansicht für Auslastungen und Zeitreihenstatistiken (Belegungsverläufe).
* **EU-Nachweis (PDF):** Manuell anforderbarer PDF-Export für monatliche, quartalsweise und jährliche Berichte. Inhalt: Belegungsauslastung, Kontingentnutzung und Kapazitäten vs. EU-Vorgabe. (Phase 1: Manueller Download & Mailversand; Phase 2: Automatisierung).

---

## 5. Nicht-funktionale Anforderungen (Non-Functional Requirements)

### [NF-01] Barrierefreiheit (BITV 2.0 / WCAG 2.1 AA)

* **Verbindlichkeit:** Strikt einzuhalten ab Tag 1 (Pflicht für Bundesbehörden).
* **UX-Vorgabe:** Da Ampelfarben (Grün/Gelb/Rot) zur Statusanzeige genutzt werden, muss eine **Icon-Redundanz** implementiert werden, um die Lesbarkeit für Menschen mit Farbfehlsichtigkeiten (z. B. Rot-Grün-Schwäche) zu garantieren.

### [NF-02] Vollständige Netzwerisolation & Datensouveränität

* **Prinzip:** Absolut null externe Abhängigkeiten oder API-Aufrufe in Phase 1 (weder Google Maps, noch externe Schrifttypen oder CDN-Bibliotheken). Alle Komponenten (Karten-Tiles, Keycloak, Codelisten) agieren autark im lokalen Netz.

### [NF-03] Audit-Sicherheit (Write-Only-Schema)

* **Konzept:** Das Audit-Log wird in einem dedizierten, DB-seitig isolierten PostgreSQL-Schema abgelegt.
* **Sicherheitsregel:** Die Applikation besitzt ausschließlich Schreibrechte (`INSERT`). Weder Sachbearbeiter noch lokale Administratoren besitzen Leserechte oder Modifikationsrechte (`UPDATE`/`DELETE`) auf dieses Schema.

### [NF-04] Hochverfügbarkeit & Recovery-SLA (Phase 1)

* **Verfügbarkeit:** Angestrebt wird ein 24/7-Betrieb. Roll-outs und Updates im K3S (Enterprise Stack) müssen über Rolling Updates in unter 10 Minuten abgeschlossen sein.
* **SLA-Einstufung:** Für die Phase 1 ist **kein** teures Hochverfügbarkeits-Cluster gefordert. Ein automatisiertes Datenbank-Backup ist ausreichend. Systemausfälle von 10 Minuten (in Ausnahmen bis zu 30 Minuten) sind in der Pilotphase tolerierbar.

---

## 6. Technische Kernkonzepte & Daten-Infrastruktur

### [TECH-01] XAusländer Codelisten via lokalem SKOS-Service

* **Konzept:** XAusländer-Codelisten (mindestens: *Geschlecht, Staatsangehörigkeit*, ggf. *Verfahrensstatus*) werden zur Entwicklungszeit per Skript heruntergeladen und in das SKOS-Format (Simple Knowledge Organization System) konvertiert.
* **Auslieferung:** Die Listen werden versioniert direkt mit der Software ausgeliefert und als lokaler REST-Service bereitgestellt. Die Datenbank speichert performant nur die IDs. Es gibt keine GUI zur Pflege in Phase 1.
* **Zukunftssicherheit:** Das SKOS-Format bildet in Phase 2 die Basis für die Interoperabilität mit anderen XÖV-konformen Systemen im BAMF.

### [TECH-02] PostgreSQL Schemata-Trennung

* **Struktur:** Logische Isolation statt komplexem Microservice-Overhead. Innerhalb einer PostgreSQL-Instanz werden separate Schemata genutzt. Eine spätere Migration der Datenstrukturen hin zu einer zentralen BAMF-Datenbank ist im Design von Beginn an mitgedacht.

### [TECH-03] Resilience & Degradation (Karten-Fallback)

* **Konzept:** Sollte der lokale Tile-Server fehlschlagen oder nicht erreichbar sein, darf die Anwendung nicht blockieren.
* **Fallback:** Das System schaltet automatisch auf eine statisch im Frontend hinterlegte, interaktive SVG-Grafik (Deutschlandkarte mit klickbaren Einrichtungspunkten) um. Die UX bleibt unter reduzierter grafischer Detailtiefe vollständig erhalten.

### [TECH-04] Automatisierte Validierungsjobs (Self-Monitoring)

* **Logik:** Ein im Hintergrund laufender Job-Scheduler prüft periodisch die Datenintegrität und rechtliche Schwellenwerte (z. B. "Nährung an die 12-Wochen-Frist").
* **Aktion:** Der Job generiert bei Auffälligkeiten automatisierte Prüfaufträge oder Handlungsempfehlungen und legt diese direkt in den Postkörben der betroffenen Einrichtungen ab. Es ist kein separates Monitoring-Tool notwendig.

---

## 7. Prozess: Entwicklungsreihenfolge (Roadmap)

Die technische Implementierung folgt einer logischen, aufeinander aufbauenden Sequenz, um Abhängigkeiten zu minimieren:

```
+--------------------------------------------------------------+
| 1. DB-Schema-Design (3NF/4NF, Trennung) & Codelisten-Ident.   |
+--------------------------------------------------------------+
                               |
                               v
+--------------------------------------------------------------+
| 2. SKOS-Codelisten-Skript & lokaler Python REST-Service      |
+--------------------------------------------------------------+
                               |
                               v
+--------------------------------------------------------------+
| 3. Keycloak-Setup & lokales Rollenmodell                     |
+--------------------------------------------------------------+
                               |
                               v
+--------------------------------------------------------------+
| 4. Core CRUD (Einrichtungen, Räume, Betten, Belegung)        |
+--------------------------------------------------------------+
                               |
                               v
+--------------------------------------------------------------+
| 5. Reservierungs-Workflow & Postkorb-System (Async)          |
+--------------------------------------------------------------+
                               |
                               v
+--------------------------------------------------------------+
| 6. Dashboard & Ampel-Zusammenfassung (UI)                    |
+--------------------------------------------------------------+
                               |
                               v
+--------------------------------------------------------------+
| 7. Karte (React-Leaflet + Tile-Server + SVG-Fallback)        |
+--------------------------------------------------------------+
                               |
                               v
+--------------------------------------------------------------+
| 8. Belegungsvorschlags-Funktion (Constraint-Algorithmus)     |
+--------------------------------------------------------------+
                               |
                               v
+--------------------------------------------------------------+
| 9. Validierungsjobs (Hintergrund-Scheduler -> Postkorb)      |
+--------------------------------------------------------------+
                               |
                               v
+--------------------------------------------------------------+
| 10. Reporting & PDF-Erstellung (EU-Compliance-Export)        |
+--------------------------------------------------------------+

```

---

## 8. Abnehmbare Test- und Qualitätsstrategie

Um die Verhaltenskonformität (insb. bei rechtlichen Rahmenbedingungen) sicherzustellen, wird über die Stacks hinweg ein **BDD-Ansatz (Behavior-Driven Development)** gewählt.

* **Unit-Tests:** Pragmatisch gesteuert über das jeweilige Sprach-Framework (Python: `pytest` / Java: `JUnit 5` + `Mockito`).
* **Integrationstests (Fachlogik):** Definition der Akzeptanzkriterien in Gherkin-Syntax (*Given-When-Then*).
* *Demo-Stack:* Test-Ausführung via Python-Bibliotheken.
* *Enterprise-Stack:* Integration über `Cucumber` + `JUnit 5`.


* **End-to-End (E2E) & API-Tests:** Vollautomatisiert über Python `Behave`. Die Testsuite agiert als Black-Box-Tester gegen das laufende System (unabhängig vom gewählten Stack).
* **Frontend-Testing:** Komponententests im jeweiligen Framework; E2E-Flüsse über `Cypress`.

---

## 9. Anhang: Offene Klärungspunkte (Für spätere Phasen)

1. **Codelisten-Spezifikation:** Finale Festlegung aller benötigten XAusländer-Codelisten-IDs nach Abschluss des exakten DB-Tabellendesigns.
2. **Karten-Geometrie:** Entscheidung über die finale Granularität der `MBTiles` (Gesamt-Deutschland vs. reine Fokussierung auf Grenzregionen zur Speicherplatzoptimierung).
3. **Infrastruktur-Sizing:** Exakte Analyse der RAM/CPU-Ressourcenanforderungen für den lokalen K3S-Betrieb im Enterprise-Szenario.
4. **BAMF-Styleguide:** Bereitstellung der konkreten UI-Design-Vorgaben (Farbcodes, spezifische Behörden-Fonts), relevant erst bei Aktivierung des Enterprise-Stacks.

---

## 10. Ergänzungen aus Implementierungsphase (Mai 2026)

### 10.1 Labels-System [HF-11]

**Kontext:** Aus den Implementierungsgesprächen wurde deutlich, dass SBs beim Belegungsvorschlag und bei der manuellen Bett-Zuweisung operative Hinweise zu Räumen, Betten und Personen benötigen, die weder durch das DSGVO-Minimaldatenmodell (AZR-ID, Alias, Geschlecht) noch durch das strukturelle Rollen-/Raummodell abgedeckt werden.

**Anforderung:** Einführung eines flexiblen Labels-Systems für drei Entitätstypen:

* **Raum-Labels:** Ausstattungsmerkmale und Eignungshinweise (Beispiele: `Rollstuhlgerecht`, `Erdgeschoss`, `Ruhige Lage`, `Dusche vorhanden`). Ermöglichen SBs, passende Räume für Personen mit besonderen Anforderungen zu identifizieren.
* **Bett-Labels:** Positions- und Typinformationen (Beispiele: `Unteres Bett`, `Oberes Bett`, `Einzelbett`, `Barrierefrei`). Unterstützen die Feinauswahl innerhalb eines Raums.
* **Belegungs-Labels (Personen-Hinweise):** Operative Hinweise zur aktuellen Belegung eines Bettes (Beispiele: `Kind`, `Unbegleitete Minderjährige`, `Sprache: Arabisch`, `Sprache: Farsi`, `Halal`, `Medizinische Einschränkung`).

**DSGVO-Klarstellung:** Labels auf Belegungsebene sind ausschließlich operative Hinweise für den laufenden Belegungszeitraum. Sie sind nicht AZR-relevant, nicht personenbezogen im Sinne einer dauerhaften Profilerstellung und werden gemeinsam mit der Belegung gelöscht. Labels dürfen keine gesundheitlichen Diagnosen oder biometrischen Merkmale erfassen.

**UX-Prinzip (Human-in-the-loop):** Das System zeigt Labels als visuelle Matching-Hints (farbige Chips) an. Es gibt keinen Algorithmus, der Belegungen erzwingt oder ablehnt — die Entscheidung liegt immer beim SB.

**Prädefinierter Katalog:** Labels werden aus einem vordefinierten Katalog gewählt (kein Freitext). Der Katalog ist wartbar (DB-Tabelle oder hardcodierte Enum-Liste), jedoch nicht über eine Admin-GUI in Phase 1.

**Technischer Ansatz (Demo Stack):**
* `TEXT[]`-Spalten auf `capacity.rooms`, `capacity.beds` und `persons.occupants`
* `PATCH`-Endpoints zum Setzen/Ersetzen der Labels-Liste
* `GET /api/labels/catalog` liefert den vordefinierten Katalog (gruppiert nach Entitätstyp)
* Frontend: `LabelChips`-Komponente zeigt Labels als MUI-Chips; im Bett-Dialog editierbar

**Roadmap-Einordnung:** [HF-11] ergänzt [HF-04] (Raum-Bett-Modell), [HF-05] (Belegungsvorschlag) und [HF-08] (DSGVO-Minimaldaten). Es handelt sich um ein optionales Feature, das den Nutzen des Belegungsvorschlags und der manuellen Belegung deutlich erhöht, ohne das Datenschutzprinzip zu kompromittieren.

### 10.2 UI/UX-Verfeinerungen (Dashboard & Drilldown)

Aus der Implementierungsphase wurden folgende Interaktionsverbesserungen identifiziert und realisiert:

* **Dashboard — Direktbelegung:** Klick auf ein Bett im Dashboard öffnet einen BelegDialog mit vorausgefüllten Daten (Einrichtung, Raum), sodass SBs ohne Umweg über den Drilldown belegen können.
* **Dashboard — Reservierungs-Chips:** Die letzten 5 eigenen Reservierungen werden als Chips unterhalb des Dashboards angezeigt; Klick navigiert zur `/reservations`-Ansicht.
* **Dashboard — Admin-Shortcut:** Admins sehen direkt im Dashboard einen "Neue Einrichtung anlegen"-Button.
* **Drilldown — Freies Bett:** Klick auf ein freies Bett öffnet den `BelegDialog` (AZR-ID + Alias + Datumsfeld).
* **Drilldown — Belegtes Bett:** Klick auf ein belegtes Bett öffnet den `BedManageDialog` mit Optionen: Ausbuchen, Intern verlegen, Verlegen zu anderer Einrichtung (löst Reservierungsanfrage aus).
* **Drilldown — Pending-Indikator:** Offene Reservierungsanfragen pro Raum werden als oranges Chip sichtbar gemacht.
* **Drilldown — Admin-Tab:** Im Edit-Dialog der Einrichtung gibt es einen Tab "Räume & Betten" (Räume anlegen, Betten hinzufügen, Betten deaktivieren).
* **Postkorb — ReservierungsID:** Die ReservierungsID (#XXXXXXXX, kopierbar) wird auf allen Reservierungsansichten immer angezeigt.
* **Postkorb — Ablehnungsgrund:** Beim Ablehnen einer Anfrage ist ein Pflichtfeld für den Ablehnungsgrund vorhanden.
* **Postkorb — Jump-to-Bed:** Tasks mit AZR-ID im Body erhalten einen "Zum Bett springen"-Button, der direkt zum Drilldown der betroffenen Einrichtung navigiert.
* **Globale AZR-Suche:** Ein Suchsymbol in der NavBar öffnet einen Dialog zur Suche nach AZR-ID oder Alias. Ergebnisse zeigen Einrichtung, Raum, Bett und Zeitraum; Klick navigiert zum entsprechenden Drilldown.

### 10.3 Demo-Daten (Benutzer & Einrichtungen)

Für die Demo wurden realistische Testdaten angelegt:

* **Benutzer:** Mehrere SBs und Admins mit verschiedenen Rollen und Standortzugehörigkeiten.
* **Einrichtungen:** Mindestens 4 Einrichtungen mit je mehreren Räumen und unterschiedlichen Geschlechtsdesignationen.
* **Belegungsgrade:** Realistische Auslastung (ca. 75% / 93% / 30% / 42%) zur Demonstration der Ampellogik.

---

## 11. Fehlerberichte und neue Anforderungen (25. Mai 2026)

Dieses Kapitel dokumentiert Fehler und Funktionswünsche, die aus der laufenden Implementierungsphase gemeldet wurden. Alle Einträge sind dem 25. Mai 2026 (Melder: Berthold Maier) zuzuordnen.

---

### 11.1 Fehler-Behebungen

#### [F-01] Reservierungsvorschlag-Suche fehlgeschlagen (SuggestionWizard)

**Symptom:** Im SuggestionWizard schlägt die Suche mit der Fehlermeldung „Suche fehlgeschlagen" fehl. Betroffen sind alle drei Modi: Einzel-, Gruppen- und Familienmodus.

**Ursache:** Das JWT-Token des angemeldeten Benutzers enthält keinen `location_id`-Claim. Da der Frontend-Client diesen Claim ausliest und als `X-Location-Id`-Header an das Backend übergibt, fehlt der Header in der Anfrage vollständig. Das Backend beantwortet jede solche Anfrage mit HTTP 422 (Unprocessable Entity).

**Behebung:**
* JWT-Token-Generierung in Keycloak prüfen und `location_id` als Pflicht-Claim aufnehmen.
* Alternativ: Backend-Fallback einbauen, der bei fehlendem Header den Standort aus dem Benutzerprofil ermittelt.
* Frontend: Aussagekräftige Fehlermeldung anzeigen, wenn `location_id` im Token fehlt, statt generisches „Suche fehlgeschlagen".
* Regressions-Test: E2E-Testfall für alle drei SuggestionWizard-Modi ergänzen, der das Vorhandensein des Headers sicherstellt.

---

#### [F-02] Labels persistieren nicht bei Personen (Belegung)

**Symptom:** Labels, die einer Person (Belegung) zugeordnet werden, sind beim nächsten Öffnen des Belegungsdialogs nicht mehr sichtbar. Die Labels scheinen gespeichert zu werden, verschwinden aber nach dem Schließen und erneuten Öffnen des Dialogs.

**Ursache:** Nach dem Speichern der Labels wird der `rooms`-State im Frontend nicht aktualisiert. Der Dialog liest beim Öffnen den veralteten State aus dem lokalen Cache, in dem die Labels noch nicht enthalten sind. Es handelt sich um einen UI-Bug in `Drilldown.tsx`.

**Behebung:**
* In `Drilldown.tsx`: Nach erfolgreichem `PATCH`-Aufruf auf den Labels-Endpoint den `rooms`-State neu laden (re-fetch oder optimistisches State-Update mit den zurückgelieferten Daten).
* Sicherstellen, dass der `BelegDialog` und der `BedManageDialog` immer mit den aktuellen Serverdaten initialisiert werden und nicht ausschließlich auf dem lokalen State basieren.
* Unit-Test: Renderverhalten des Dialogs nach Label-Speicherung prüfen.

---

#### [F-03] Neue Reservierungsanfrage schlägt fehl (ReservationCreateDialog)

**Symptom:** Beim Anlegen einer neuen Reservierungsanfrage im `ReservationCreateDialog` erscheint die Fehlermeldung „Unbekannter Fehler", obwohl das Backend eine spezifische Fehlermeldung zurückliefert.

**Ursache:** Der Fehlerparser im Frontend greift nicht korrekt auf die API-Antwort zu. Die tatsächliche Fehlermeldung steckt in der Antwortstruktur des Backends (z. B. `response.data.detail` oder `response.data.message`), wird aber nicht ausgelesen. Stattdessen fällt der Parser auf einen generischen Fallback zurück.

**Behebung:**
* Fehlerparser im `ReservationCreateDialog` korrigieren: Fehlerstruktur der Backend-API-Antwort exakt auslesen (Pfad: `error.response?.data?.detail ?? error.message`).
* Zentrale Fehlerbehandlungs-Utility erstellen, die alle FastAPI-Fehlermuster (`detail`, `message`, HTTP-Statustext) einheitlich auflöst und für alle Dialoge nutzbar macht.
* Integrations-Test: Fehlerpfad im `ReservationCreateDialog` mit Mock-Backend-Fehlerantworten abdecken.

---

### 11.2 Neue Anforderungen

Die folgenden Anforderungen ergänzen den bestehenden Funktionsumfang. Sie sind alle dem Entwicklungsziel **[Ziel 9]** zugeordnet und bauen auf den bestehenden Anforderungen [HF-01] bis [HF-11] auf.

---

#### [HF-12] Labels als Filterkriterium bei Reservierungsanfragen

**Kontext:** Bisher können SBs bei der Suche nach freien Plätzen im SuggestionWizard keine labelbezogenen Einschränkungen angeben. Ein Raum, der als „Rollstuhlgerecht" oder „Familienraum" gekennzeichnet ist, erscheint gleichwertig neben nicht gekennzeichneten Räumen.

**Anforderung:** Im SuggestionWizard können Raumlabels und Bettlabels als optionale Filterkriterien ausgewählt werden.

* Auswahl über Mehrfach-Chips (Multi-Select); kein Pflichtfeld.
* Ist kein Label ausgewählt, verhält sich die Suche wie bisher.
* Ist mindestens ein Label ausgewählt, werden nur Räume/Betten zurückgegeben, die alle gewählten Labels besitzen.
* Ergebnis-Varianten zeigen einen visuellen Hinweis, wenn ein Vorschlag gewählte Label-Einschränkungen nicht vollständig erfüllen konnte (Soft-Match-Indikator).
* **DSGVO:** Nur Raum- und Bettlabels sind filterbar. Belegungs-Labels (Personen-Hinweise) sind kein Suchkriterium.

---

#### [HF-13] Geschlechts-Zuordnung über Labels statt fester Designation

**Kontext:** Die bisherige `geschlechts_designation`-Spalte am Raum ist ein fester Wert, der unabhängig von der tatsächlichen Belegungssituation gesetzt werden muss. Das erfordert manuelle Pflege und spiegelt den Echtzeit-Zustand nicht wider.

**Anforderung:** Ablösung der festen Geschlechtsdesignation durch ein dynamisches, labelbasiertes Modell.

* Ein leerer Raum (keine aktive Belegung im angefragten Zeitraum) ist für jede Person belegbar.
* Sobald ein Raum mindestens eine aktive Belegung des Geschlechts M enthält, wird er systemseitig automatisch als Männerraum behandelt (und umgekehrt für F).
* Explizite Labels (`Männer`, `Frauen`, `Familie/Gemischt`) am Raum können die automatische Zuordnung übersteuern und den Raum fest einem Geschlecht oder dem Familienmodus zuordnen.
* Die bestehende Familienschutz-Logik ([HF-04]) bleibt unverändert als Hard Constraint erhalten.
* **Enterprise-Stack:** Langfristige Migration der `geschlechts_designation`-Spalte auf das Label-basierte System. Übergangsweise Dual-Auswertung (Spalte und Labels) zur Wahrung der Abwärtskompatibilität.

---

#### [HF-14] Gruppen-Suche über mehrere Unterkünfte

**Kontext:** Beim heutigen Gruppen-Modus des SuggestionWizard wird ausschließlich innerhalb einer einzelnen Einrichtung gesucht. Kann eine Gruppe dort nicht vollständig untergebracht werden, erhält der SB lediglich eine Fehlermeldung ohne weiterführende Handlungsoptionen.

**Anforderung:** Der SuggestionWizard unterstützt standortübergreifende Gruppenunterbringung.

* Schritt 1: Suche zuerst in der Heimat-Einrichtung des SBs.
* Schritt 2: Kann die Gruppe dort nicht vollständig untergebracht werden, schlägt das System automatisch eine Aufteilung auf mehrere Einrichtungen vor.
* Eine Ergebnis-Variante darf mehrere Einrichtungen kombinieren.
* Der SB erhält für jede Variante eine klare Darstellung: Wer kommt wohin, wie viele Personen verbleiben getrennt.
* Verbesserte Fehlermeldung wenn keine Variante gefunden werden kann: Angabe, wie viele Plätze im angefragten Zeitraum systemweit verfügbar sind und wo.

---

#### [HF-15] Labels für Einrichtungen

**Kontext:** Bisher existiert das Labels-System ([HF-11]) nur für Räume, Betten und Belegungen. Einrichtungen selbst tragen keine strukturierten Merkmalsinformationen.

**Anforderung:** Einrichtungen können Labels erhalten, die ihre Eignung und ihren Charakter beschreiben.

* Beispiel-Labels: `Erstaufnahme`, `Familiengeeignet`, `Barrierefrei`, `Medizinische Versorgung vor Ort`, `Gesichert (geschlossene Einrichtung)`.
* Labels werden im Einrichtungs-Edit-Dialog beim Anlegen und Bearbeiten vergeben (gleiche Chip-Auswahl-UX wie bei Räumen).
* Labels erscheinen im Dashboard (unterhalb des Einrichtungsnamens) und als Tooltip-Information auf der Karte.
* Labels sind filterfähig: Im Dashboard und auf der Karte kann nach Einrichtungs-Labels gefiltert werden.

---

#### [HF-16] Geo-Lokation für Einrichtungen

**Kontext:** Die Kartenpositionierung von Einrichtungen basiert derzeit ausschließlich auf der hinterlegten Adresse (Geocoding-Fallback). Das ist fehleranfällig bei unvollständigen oder nicht eindeutigen Adressen.

**Anforderung:** Einrichtungen erhalten explizite Geo-Koordinaten als primäre Positionierungsgrundlage.

* Neue Felder `geo_lat` (Breitengrad) und `geo_lng` (Längengrad) im Einrichtungsdatenmodell.
* Eingabe im Einrichtungs-Edit-Dialog: Dezimalgrad-Eingabefelder mit Validierung (Bereich: Deutschland).
* Karte zeigt Marker an Geo-Koordinaten, wenn vorhanden; fällt andernfalls auf Adress-Geocoding zurück ([TECH-03]).
* Koordinaten können auch per Klick auf eine eingebettete Miniaturkarte gesetzt werden (Phase 2, sofern technisch umsetzbar).

---

#### [HF-17] Gültigkeitszeitraum für Einrichtungen

**Kontext:** Einrichtungen werden im BAMF-Grenzverfahren temporär betrieben. Es fehlt bisher eine Möglichkeit, den operativen Zeitraum einer Einrichtung im System zu hinterlegen.

**Anforderung:** Einrichtungen erhalten die Felder `gueltig_ab` und `gueltig_bis` (jeweils `DATE`).

* Außerhalb des Gültigkeitszeitraums sind keine neuen Belegungen und keine neuen Reservierungsanfragen für diese Einrichtung möglich.
* Das Backend validiert den Gültigkeitszeitraum beim Anlegen von Belegungen und Reservierungen und gibt HTTP 409 zurück, wenn die Einrichtung außerhalb ihres Gültigkeitsfensters liegt.
* Im Dashboard wird eine Einrichtung, deren `gueltig_bis` in weniger als 30 Tagen liegt, mit einem Warnindikator versehen (Hinweis: „Einrichtung endet in X Tagen").
* Ein Gültigkeitszeitraum ist optional; Einrichtungen ohne Datumsangabe gelten als unbefristet aktiv.

---

#### [HF-18] Einrichtungs- und Raum-Deaktivierung mit Belegungsschutz

**Kontext:** Derzeit können Einrichtungen und Räume ohne Prüfung deaktiviert oder gelöscht werden, auch wenn noch aktive Belegungen vorhanden sind. Das führt zu inkonsistenten Daten.

**Anforderung:** Deaktivierung nur wenn keine aktiven Belegungen vorliegen.

* Eine Einrichtung darf nur deaktiviert (nicht gelöscht) werden, wenn zum Deaktivierungszeitpunkt keine aktiven Belegungen in ihr vorhanden sind.
* Gleiches Prinzip gilt für die Raum-Deaktivierung.
* Das Backend gibt bei Verstoß HTTP 409 zurück mit einem aussagekräftigen Fehlertext: „X aktive Belegungen vorhanden. Erst umbuchen."
* Das Frontend zeigt diesen Hinweis im Deaktivierungs-Dialog an und unterdrückt den Bestätigen-Button, wenn der Server einen 409-Status meldet.
* **Wichtig:** Physisches Löschen von Einrichtungen oder Räumen ist im System grundsätzlich nicht vorgesehen (Soft-Delete / Deaktivierung als einziger Weg).

---

#### [HF-19] Kontingent-Änderung mit Belegungs-Prüfung

**Kontext:** Das offizielle Bettenkontingent einer Einrichtung kann aktuell ohne Einschränkung unter die aktuelle Belegungszahl abgesenkt werden, was zu einer rechnerisch unmöglichen Überbuchung führt.

**Anforderung:** Das Kontingent kann nicht unter die aktuelle Belegungszahl abgesenkt werden.

* Beim Speichern einer Kontingentreduktion prüft das Backend: `neues_kontingent >= aktuelle_belegungszahl`.
* Bei Verletzung: HTTP 409 mit Meldung „Aktuelle Belegung (X) übersteigt neues Kontingent (Y). Erst ausbuchen."
* Eine Kontingentaufstockung ist jederzeit ohne zusätzliche Prüfung möglich.
* **Enterprise-Stack:** Kontingentänderungen unterliegen einem Approval-Workflow (4-Augen-Prinzip). Kontingentreduzierungen werden im Audit-Trail mit Antragsteller, Genehmiger und Zeitstempel dokumentiert.

---

#### [HF-20] Zeitbasierte Bett-Deaktivierung

**Kontext:** Betten können heute nur sofort deaktiviert werden. Es gibt keine Möglichkeit, eine zukünftige Deaktivierung zu planen, obwohl die operative Praxis (z. B. geplante Sanierung eines Bettes) das erfordert.

**Anforderung:** Bett-Deaktivierung zu einem definierten zukünftigen Datum.

* Neues Feld `deaktiviert_ab DATE` im Bett-Datenmodell (nullable; `NULL` = Bett aktiv und unbefristet).
* Beim Setzen von `deaktiviert_ab` für ein Bett: Das Bett ist noch belegbar für Zeiträume, die vollständig vor `deaktiviert_ab` liegen.
* Der Suggestion-SQL berücksichtigt `deaktiviert_ab`: Ein Bett gilt als nicht verfügbar, wenn `deaktiviert_ab <= period_start`.
* Wenn eine aktive Belegung über `deaktiviert_ab` hinaus läuft, wird automatisch ein Postkorb-Task erstellt: „Bett [ID] wird ab [Datum] deaktiviert. Belegung von [AZR-ID/Alias] muss bis dahin umgebucht werden."
* Im Drilldown wird ein Bett mit gesetztem `deaktiviert_ab` visuell markiert (z. B. Strikethrough-Stil oder Warnindikator mit Datum).

---

#### [HF-21] Direkte Bett-Anfrage-Zuordnung aus dem Drilldown

**Kontext:** Der aktuelle Workflow erfordert, dass ein SB den Drilldown verlässt, zur Reservierungsübersicht navigiert, eine Anfrage auswählt, bestätigt und dann manuell zum Drilldown zurücknavigiert. Dieser Kontextverlust ist ineffizient und fehleranfällig.

**Anforderung:** Zuordnung offener Reservierungsanfragen zu freien Betten direkt aus dem Drilldown heraus.

* Im Drilldown: Der orangefarbene Pending-Indikator (vgl. 10.2) ist anklickbar und öffnet eine Liste aller offenen (`PENDING`) Reservierungsanfragen für diesen Raum.
* Klick auf ein freies Bett im Drilldown öffnet einen Dialog „Anfrage zuordnen" mit einer Liste aller offenen Anfragen, die für dieses Bett passen (Geschlecht, Familienstatus, Zeitraum).
* Der SB kann direkt aus diesem Dialog eine Anfrage auswählen und bestätigen, ohne den Drilldown zu verlassen.
* Nach Bestätigung aktualisiert sich der Drilldown sofort (das Bett wechselt in den Status „Belegt", der Pending-Indikator wird angepasst).

---

#### [HF-22] Notbetten-Tracking und -Darstellung

**Kontext:** Notbetten sind laut [HF-01] ein definierter Bettentyp mit einer Maximalverweildauer von einer Nacht. Bisher fehlt jedoch eine strukturierte Darstellung und ein systemseitiges Monitoring der Notbettbelegungen im Tagesverlauf.

**Anforderung:** Eigenständige Erfassung, Darstellung und Verfallsüberwachung von Notbetten.

* **Datenmodell:** `bett_typ = 'NOTBETT'` als eigener Enum-Wert in der Betten-Tabelle (neben `KONTINGENT`).
* **Drilldown-Darstellung:** Notbetten werden in einem separaten, klar abgegrenzten Bereich unterhalb der Kontingentbetten dargestellt. Für jedes Notbett werden angezeigt: wer belegt es (AZR-ID / Alias), seit wann, wann endet die Belegung.
* **Technische Validierung:** Das Backend verhindert Belegungen auf Notbetten mit einer Dauer von mehr als 1 Tag (HTTP 400).
* **Verlängerungsoption:** Eine Einrichtung kann für eine laufende Notbettbelegung einmalig eine Verlängerung um 1 weiteren Tag gewähren. Diese Verlängerung wird im Audit-Log dokumentiert. Eine zweite Verlängerung ist systemseitig nicht möglich; danach ist zwingend eine Verlegung auf ein Kontingentbett oder in eine andere Einrichtung vorzunehmen.
* **Täglicher Scheduler-Task:** Täglich um 06:00 Uhr erstellt ein Hintergrundprozess (vgl. [TECH-04]) für jede Notbettbelegung, die an diesem Tag endet, automatisch einen Postkorb-Task: „Notbett [ID]: Belegung von [AZR-ID/Alias] endet heute. Verlegung oder Verlängerung erforderlich."
* **Enterprise-Stack:** Scheduler als Spring `@Scheduled`-Job mit konfigurierbarer Uhrzeit (Default: 06:00 Uhr). Benachrichtigung auch als E-Mail an den zuständigen SB der Einrichtung möglich.

---

### 11.3 Enterprise-Stack-Implikationen (HF-12 bis HF-22)

Die folgenden Umsetzungshinweise gelten spezifisch für den Enterprise Stack (Java/Spring Boot, Angular) und ergänzen die Demo-Stack-Umsetzung der obigen Anforderungen.

| Anforderung | Enterprise-Stack-Besonderheit |
|---|---|
| **HF-12 / HF-15 (Labels als Filter)** | Labels-Tabelle statt `TEXT[]`-Array (normalisierte Many-to-Many-Verknüpfung für Filterbarkeit und Datenbankindizierung). |
| **HF-16 (Geo-Koordinaten)** | Speicherung als PostGIS-`GEOGRAPHY(POINT)`-Typ; ermöglicht native Umkreissuche (`ST_DWithin`) für künftige Standortanalysen. |
| **HF-17 / HF-18 / HF-19 (Kapazitätsprüfungen)** | Komplexe Prüflogik als dedizierter Domain-Service (`CapacityGuard`) mit pessimistischem Datenbank-Locking (`SELECT ... FOR UPDATE`), um Race Conditions bei parallelen Buchungen zu verhindern. |
| **HF-19 (Kontingent-Approval)** | Kontingentänderungen unterliegen einem 4-Augen-Approval-Workflow. Antragsteller und Genehmiger werden im Audit-Trail mit Zeitstempel erfasst. |
| **HF-20 / HF-22 (Scheduler)** | Notbett-Scheduler und Bett-Deaktivierungs-Prüfung als Spring `@Scheduled`-Jobs mit konfigurierbarer Uhrzeit. |
| **HF-22 (Audit-Trail)** | Alle Kapazitätsänderungen (Kontingent, Bett-Deaktivierung, Notbett-Verlängerung) werden im Write-Only-Audit-Schema ([NF-03]) mit Benutzer, Zeitstempel und Delta-Wert protokolliert. |
| **HF-13 (Geschlechts-Migration)** | Übergangsweise Dual-Auswertung von `geschlechts_designation`-Spalte und Labels. Datenmigrations-Skript überführt bestehende Designationen in Labels. Spalte wird nach Stabilisierung entfernt (Breaking Change, mit Migrations-Guide). |