---
stepsCompleted: [1, 2, 3]
inputDocuments: []
session_topic: 'Web-Anwendung zur Kapazitäts- und Bettenplanung für BAMF-Grenzverfahren (GEAS-Reform)'
session_goals: 'Funktionale Anforderungen, Nicht-funktionale Anforderungen (Barrierefreiheit/Sicherheit/DSGVO), Architekturentscheidungen, Grundanforderungen als nicht verhandelbare Leitplanken, Strategie für schnelle Umsetzung ohne Architekturschulden'
selected_approach: 'ai-recommended'
techniques_used: ['Question Storming', 'Six Thinking Hats', 'Constraint Mapping']
ideas_generated: []
context_file: ''
---

# Brainstorming Session Results

**Facilitator:** Berthold
**Date:** 2026-05-22

## Session Overview

**Thema:** Web-Anwendung zur Kapazitäts- und Bettenplanung für BAMF-Grenzverfahren (GEAS-Reform, BMI/BAMF)

**Ziele:**
- Funktionale Anforderungen (Bettenkontingente, 12-Wochen-Tracking, Schutzbedürftige, Trennung nach Gruppen)
- Nicht-funktionale Anforderungen (Barrierefreiheit, IT-Sicherheit, DSGVO/Datenschutz)
- Architekturentscheidungen (sauber, erweiterbar, Phase 1 ohne externe Integrationen)
- Grundanforderungen als nicht verhandelbare Leitplanken festhalten
- Strategie: Schnelle Umsetzung **ohne** Architekturschulden

## Technik-Auswahl

**Ansatz:** KI-empfohlen
**Sequenz:**
1. **Question Storming** (deep) — Problemraum vollständig aufspannen
2. **Six Thinking Hats** (structured) — Alle Perspektiven systematisch beleuchten
3. **Constraint Mapping** (deep) — Leitplanken und Architekturpfade kartieren

---

### Kontextuelle Rahmenbedingungen

- Asylsuchende gelten rechtlich als „nicht eingereist" → geschlossene/teilgeschlossene Einrichtungen
- 12-Wochen-Maximum: Überbelegung macht Grenzverfahren für Folgende rechtlich unmöglich
- EU-Kapazitätsobergrenzen pro Mitgliedstaat
- Schutzbedürftige Gruppen (Familien, Kranke) müssen gesondert untergebracht werden
- Zuständigkeit: BMI (Rahmen) + Bundesländer (Umsetzung, z. B. Hessen/Bayern)

---

## Technik 1: Question Storming — Ergebnisse

### Entdeckte Kernkonzepte

**[Funktional #1]: Zweistufiges Kapazitätsmodell**
*Konzept:* Zwei Kapazitätsebenen — offizielles Kontingent (EU-quoten-relevant, 12-Wochen-Uhr läuft) und Notbetten (max. 1 Nacht, nicht im EU-Kontingent, kein Verfahrenstimer). Notbetten dürfen nicht ins Kontingent überführt werden.
*Besonderheit:* Trennung verhindert, dass Notlösungen die EU-Compliance-Kennzahlen verfälschen.

**[Funktional #2]: Reservierungs-Workflow mit konkurrierenden Anfragen**
*Konzept:* Jeder SB kann für jede Einrichtung eine Reservierungsanfrage stellen. Mehrere parallele Anfragen pro Bett erlaubt. First-come-first-served bei Bestätigung. Rücknahme nur durch Ersteller oder Ziel-Einrichtungs-SB. Rechtliche Verantwortung wechselt zum Bundesland bei Bestätigung.
*Besonderheit:* Das verteilte Genehmigungsmodell spiegelt die reale Bund/Land-Zuständigkeitsteilung wider.

**[Funktional #3]: Standort-granulares Rollenmodell**
*Konzept:* Rechte = (Lokation × SB-Rolle). Ein SB kann Schreibrecht für Einrichtung A und Leserecht für Einrichtung B haben. Keine BAMF/Land-Hierarchie. Rollen: Lesend / Schreibend (Lokation verwalten) / Admin (Rollen zuweisen) / System-Admin (alles). IAM via Keycloak (lokal). Jede Änderung auditpflichtig.
*Besonderheit:* Flaches Rollenmodell vermeidet politische BAMF/Land-Hierarchie bei feingranularer Zugriffskontrolle.

**[Funktional #4]: Raum-Bett-Geschlechtsmodell mit dynamischer Umwidmung**
*Konzept:* Räume haben Geschlechtsdesignation (männlich, weiblich, Familie, divers). Jedes Bett hat feste ID. Räume können auch bei Belegung umgewidmet werden. Familienmitglieder unter 18 streng verknüpft — keine Trennung von Sorgeberechtigten (EU-RL 2013/33/EU Art.11, §43 AsylG). Ab 18 flexibel, aber Nähe bevorzugt. Bei Vollbelegung: Zusammenlegung mit anderen Personen möglich (EU-RL konform), aber Familieneinheit Priorität als Soft-Constraint (Warnung, kein Block).
*Besonderheit:* Dynamische Umwidmung ermöglicht operative Flexibilität bei gleichzeitiger Rechtskonformität.

**[Funktional #5]: Belegungsvorschlag-Funktion (kein Auto-Assignment)**
*Konzept:* System berechnet optimale Belegungsvorschläge bei SB-Eingabe von Constraints (z.B. "3 Frauen unterbringen"). Zeigt mehrere Varianten (innerhalb Einrichtung + standortübergreifend). SB entscheidet immer. Abgelehnte Vorschläge ermöglichen eigene Alternativeingabe mit Dokumentation (Audit). Soft-Constraints: Familieneinheit, verbleibende 12-Wochen-Zeit, Geschlechtsdesignation.
*Besonderheit:* Human-in-the-loop-Prinzip für alle Belegungsentscheidungen.

**[Funktional #6]: Postkorb / konfigurierbares Task-Management**
*Konzept:* Jede Einrichtung hat einen Postkorb — sichtbar für alle SBs der Location. Task-Typen konfigurierbar (initial: Übernahmeanfrage, Kontingent-Aufstockungsantrag, Notbett-Meldung, Umbelegungsvorschlag-zur-Entscheidung). Phase 1: Task-Typ-Verwaltung via SQL durch DB-Admin, keine GUI. Alle Tasks auditiert.
*Besonderheit:* Async-Workflow zwischen Einrichtungen ohne direkte Systemintegration.

**[Funktional #7]: Dashboard mit Offline-Karte (Ampel-Overlay)**
*Konzept:* Hauptansicht zeigt alle Einrichtungen auf selbstgehosteter Karte (keine externen Abhängigkeiten, lokale MBTiles + tileserver-gl). Ampel-Overlay (Grün/Gelb/Rot) für Kapazitätsstatus. Klick zeigt Echtzeit-Belegung (frei / Reservierungsanfragen / belegt). Keine Statistik auf Karte — separates Reporting-Modul. Eigene Einrichtung immer oben.
*Besonderheit:* Offline-first, datensouverän, operativ fokussiert (Status nicht Historie auf Karte).

**[Funktional #8]: DSGVO-konformes Minimaldatenmodell**
*Konzept:* Pro Person: nur AZR-ID (manuell, keine Validierung), Geschlecht, Belegungsbeginn, geplantes Belegungsende. Klassifikation "Kind" erlaubt, "Krank" nicht gespeichert. Datenlöschung nach Verfahrensabschluss. Audit-Logs: DSGVO-konforme Aufbewahrungsfristen, dann automatische Löschung. Kein Personenname, keine biometrischen Daten.
*Besonderheit:* Minimale DSGVO-Risikofläche durch datensparsamste Lösung.

**[Funktional #9]: Reporting und Zeitstatistik**
*Konzept:* Separates Reporting-Modul: Auslastung je Einrichtung, Zeitreihenstatistiken (Belegungsverläufe). Nicht auf Karte, sondern eigene Ansicht. Konkrete Report-Typen noch zu definieren nach DB-Design.
*Besonderheit:* Klare Trennung von operativem Dashboard und analytischem Reporting.

**[Technisch #1]: Lokale Datensouveränität — Architekturprinzip**
*Konzept:* Docker Compose (Pilot) + K8S (Produktion) ohne Architekturwechsel. Keine externen Abhängigkeiten in Phase 1. Karten-Tiles lokal (tileserver-gl + Deutschland-MBTiles). Keycloak lokal. SKOS-Service lokal. Rolling Update in K8S (Ziel: max. 10 Minuten), Ausnahme: kurzes Maintenance-Fenster. 24/7 Verfügbarkeit.
*Besonderheit:* Vollständige Datensouveränität ab Tag 1, Deployment-Pfad von Pilot zu Produktion ohne Architekturbruch.

**[Technisch #2]: XAusländer Codelisten via SKOS**
*Konzept:* XAusländer-Codelisten werden zur Entwicklungszeit per Script heruntergeladen, in SKOS-Format konvertiert und lokal als REST-Service bereitgestellt. DB speichert nur IDs. Codelisten versioniert und mit Software ausgeliefert. Keine GUI-Pflege in Phase 1 — nur Script + Deployment. Spezifische Listen: nach DB-Design festzulegen (mindestens: Geschlecht, Staatsangehörigkeit, ggf. Verfahrensstatus).
*Besonderheit:* SKOS-Format ermöglicht spätere Interoperabilität mit XÖV-konformen Systemen bei vollständiger lokaler Souveränität.

**[Technisch #3]: PostgreSQL mit Schemata-Trennung**
*Konzept:* PostgreSQL (statt DuckDB — Single-Writer-Limitation inkompatibel mit 10–50 parallelen Nutzern). Separate DB-Schemata: capacity, reservations, persons, audit, tasks, reference_data. Striktes 3NF/4NF. Migrationspfad zu zentraler BAMF-DB von Anfang an mitgedacht. Phase 1: DB-Administration via SQL, keine Admin-GUI.
*Besonderheit:* Schema-Trennung innerhalb einer PostgreSQL-Instanz gibt logische Isolation ohne Microservice-Overhead.

---

## Technik 2: Six Thinking Hats — Ergebnisse

### ⚫ Schwarzer Hut — Risiken & Entscheidungen

**[Risiko #1]: Kein premature Compliance-Engineering**
*Konzept:* Org-Probleme werden erst bei realem Auftreten mit Systemlösung adressiert — kein Vorausbauen von Absicherungen für hypothetische Fälle. Transparente Datendarstellung als erste Verteidigungslinie.
*Entscheidung:* YAGNI-Prinzip auf Compliance-Ebene.

**[Risiko #2]: AZR-ID + Alias-ID**
*Konzept:* AZR-ID korrigierbar. Zusätzlich kann eine Alias-ID gespeichert werden (z.B. Ausweis-ID oder einrichtungseigene Kennung). Schnittstelle offen für Außenstellen-Konventionen.
*Entscheidung:* Flexibles Identifikationsmodell ohne Validierungszwang.

**[Risiko #3]: Automatische Validierungsjobs**
*Konzept:* System prüft sich selbst periodisch und schreibt Empfehlungen/Prüfaufträge direkt in die Postkörbe der zuständigen Einrichtungen. Kein separater Monitoring-Service nötig.
*Entscheidung:* Self-monitoring via Job → Postkorb-Integration.

**[Risiko #4]: Rollen-Audit mit Prüfpflicht**
*Konzept:* Jede Rollenzuweisung/-entnahme wird protokolliert. Automatisierter Bericht zur manuellen Prüfung durch verantwortliche Person in der Org. Organisatorische Kontrolle ersetzt technischen Enforcement.
*Entscheidung:* Compliance durch Org-Prozess + System-Report, nicht durch technische Sperre.

**[Risiko #5]: Audit-Log als write-only-Schema**
*Konzept:* Audit-Schema DB-seitig abgesichert: nur das System kann schreiben, kein SB/Admin kann ändern. Organisatorisch sichergestellt.
*Entscheidung:* DB-Berechtigungen als technisches Kontrollmittel.

**[Risiko #6]: Karten-Fallback**
*Konzept:* Wenn Tile-Server nicht erreichbar → statische Grafik (z.B. SVG-Karte) einblenden statt leerer Karte. System bleibt nutzbar.
*Entscheidung:* Offline-first + degradiertes Fallback-UI.

**[Risiko #7]: Recovery-SLA**
*Konzept:* Automatisiertes DB-Backup. Recovery-Zeitraum: Ausnahme toleriert (kein harter SLA). 10 Minuten Ausfall toleriert, Ausnahmen bis 30 Minuten akzeptabel.
*Entscheidung:* Kein Hochverfügbarkeits-Cluster in Phase 1 nötig.

### 🔴 Roter Hut — Nutzergefühle & UX-Entscheidungen

**[UX #1]: Primär-Dashboard — Schnellansicht**
*Konzept:* Erste Ansicht nach Login: alle Einrichtungen mit Anzahl freier Plätze auf einen Blick (Ampel + Zahl). Eigene Einrichtung oben. Click → Detailansicht mit Betttypen, Reservierungsanfragen, Belegungsdetails.
*Entscheidung:* Information-Scent-Prinzip: Überblick → Drill-Down, kein Navigieren durch Menüs.

**[UX #2]: Task-Inbox — personalisiert und priorisiert**
*Konzept:* SB sieht nur Tasks wo er als Bearbeiter eingetragen ist. Jeder Task hat Priorität. Task-Management vollständig von Fachdaten getrennt (eigenes Modul/Schema). Selbst-Löschen oder "Obsolete"-Markierung möglich. Erledigte Tasks: konfigurierbare Sichtbarkeit (1–2 Tage via Property), dann automatische Löschung durch System-Job.
*Entscheidung:* Kein globaler Postkorb — kontextbezogene Arbeitsliste.

**[UX #3]: Session-scoped Benachrichtigung**
*Konzept:* Kein Push-Notification in Phase 1. GUI zeigt Popup/Info wenn eine Bettanfrage auftaucht — nur für den aktuell eingeloggten SB, nur wenn er für die betreffende Einrichtung zuständig ist. Andere User-Sessions werden nicht berührt.
*Entscheidung:* Leichtgewichtige Event-Signalisierung (WebSocket/Polling) statt Push-Infrastruktur.

### 🟡 Gelber Hut — Chancen & strategische Vorteile

**[Chance #1]: EU-Referenzimplementierung**
*Konzept:* System nur für Deutschland und BAMF-SBs in Phase 1. Wenn gut implementiert und dokumentiert, können andere EU-Mitgliedstaaten es kopieren und selbst betreiben (eigene Instanz, eigene Daten). Kein Multi-Tenancy bauen — aber Architektur so sauber halten, dass ein Fork trivial ist.
*Entscheidung:* i18n und Konfigurations-Externalisierung vorbereiten aber nicht goldplatieren.

**[Chance #2]: SKOS-Investment zahlt sich aus**
*Konzept:* SKOS-Codelisten-Service lokal in Phase 1 → wird in Phase 2 zur Integrationsschicht für andere BAMF-Systeme. Die Arbeit wird nicht weggeworfen, sondern schrittweise aufgewertet.
*Entscheidung:* Service-Interface stabil und versioniert halten.

**[Chance #3]: Validierungsjobs als erweiterbares Compliance-Framework**
*Konzept:* Job → Postkorb-Muster ist generisch. Jede neue Prüflogik (z.B. 12-Wochen-Näherungswarnung, Rollen-Report, Überkapazitäts-Alert) als neuer Job hinzufügbar ohne Fachlogik-Änderung.
*Entscheidung:* Job-Scheduler mit konfigurierbarem Registry-Pattern bauen.

### 🟢 Grüner Hut — Architektur-Entscheidungen

**[Architektur #1]: Hexagonale Architektur — bestätigt**
*Konzept:* Fachlogik (Kapazitätsregeln, Reservierungsworkflow, Familienregeln) vollständig isoliert von Infrastruktur. Jede externe Abhängigkeit (PostgreSQL, Keycloak, SKOS-Service, Karte, Tile-Server) hinter Port/Adapter. DB-Migration in Phase 2 = nur Adapter tauschen, keine Fachlogik-Änderung.
*Entscheidung:* Hexagonal Architecture als Pflicht-Architekturmuster.

**[Architektur #2]: Cloud Native — Infrastruktur übernimmt Querschnittsthemen**
*Konzept:* K3S (lokal + Produktion) + Istio Service Mesh. Istio übernimmt: mTLS zwischen Services, Circuit Breaker, Retry, Rate Limiting, Distributed Tracing, Traffic Management (Canary). Keine Custom-Implementierung dieser Themen in der Software. Applikationsservices: stateless, 12-Factor, klein.
*Entscheidung:* Infrastruktur-Features statt Software-Komplexität.

**[Architektur #3]: Dual-Mode Deployment**
*Konzept:* Docker Compose für lokale Entwicklung und Tests (ohne K8S/Istio-Features). K3S + Istio für Staging und Produktion. Identischer Applikations-Code in beiden Modi — nur Infrastruktur unterschiedlich. Vollautomatisierte lokale Installation (alles auf einem Rechner ausführbar).
*Entscheidung:* Dev-Experience-First — ohne K3S testbar, mit K3S produktionsreif.

**[Architektur #4]: Kein Event Sourcing in Phase 1**
*Entscheidung:* Zu komplex. Standard CRUD + separates Audit-Schema (write-only). Event Sourcing als Option für Phase 2 offen halten.

**[Architektur #5]: SVG-Fallback für Karte**
*Konzept:* Backend rendert SVG-Karte mit aktuellen Kapazitätsdaten wenn Tile-Server nicht verfügbar. Klickbare Einrichtungspunkte, Ampelfarben — gleiche UX, andere Darstellung. Leaflet-Karte und SVG-Fallback sind zwei Adapter desselben Ports.

### 🔵 Blauer Hut — Prozess & Entwicklungsreihenfolge

**[Prozess #1]: Phase-1-Grenze ist klar**
*Alles in einem System, lokal, keine externen Integrationen:* PostgreSQL lokal, Keycloak lokal, SKOS-Service lokal, Tile-Server lokal. Kein AZR-Anbindung, keine zentrale BAMF-DB, kein zentrales IDM.

**[Prozess #2]: Empfohlene Entwicklungsreihenfolge**
1. DB-Schema-Design (3NF/4NF, Schema-Trennung) + Codelisten-Identifikation
2. SKOS-Codelisten-Script + lokaler REST-Service
3. Keycloak-Setup + Rollenmodell
4. Core CRUD (Einrichtungen, Räume, Betten, Belegung)
5. Reservierungs-Workflow + Postkorb
6. Dashboard + Ampel-Ansicht
7. Karte (Leaflet + Tile-Server + SVG-Fallback)
8. Vorschlagsfunktion (Belegungsoptimierung)
9. Validierungsjobs
10. Reporting + Zeitstatistik

**[Prozess #3]: Technologie-Stack**
*Noch offen — zu klären vor Implementierungsstart (beeinflusst Entwicklungsgeschwindigkeit erheblich)*

---

## Technik 3: Constraint Mapping — Architekturentscheidungen

### Nicht verhandelbare Leitplanken (Hard Constraints)

| Constraint | Begründung |
|---|---|
| BITV 2.0 / WCAG 2.1 AA von Anfang an | Bundesbehördenpflicht; Ampelfarben müssen auch für Farbenblinde lesbar sein |
| Keine externen Abhängigkeiten in Phase 1 | Datensouveränität, Netzwerk-Isolation, DSGVO |
| PostgreSQL — kein DuckDB | Single-Writer-Limitation inkompatibel mit 10–50 parallelen Nutzern |
| Audit-Log write-only (DB-Berechtigung) | DSGVO + Manipulationsschutz |
| AZR-ID + Alias-ID statt Personenname | Datensparsamkeit, DSGVO |
| Datenlöschung nach Verfahrensabschluss | Gesetzliche Pflicht |
| Familienmitglieder unter 18 nicht trennbar | §43 AsylG + EU-RL 2013/33/EU Art. 11 |
| Rolling Update ≤ 10 Min (Ausnahme 30 Min) | 24/7-Anforderung |
| Docker Compose testbar (ohne K3S) | Dev-Experience, CI-Pipeline |

### Tech-Stack-Entscheidungen (bestätigt)

**[Stack #1]: Backend — Java Spring Boot (Modulith)**
*Konzept:* Ein Deployment, intern hexagonal in Module getrennt: `capacity`, `reservations`, `tasks`, `reporting`, `reference-data`, `audit`. Spätere Service-Extraktion einzelner Module möglich ohne Architekturbruch. Spring Modulith erzwingt Modulgrenzen zur Compile-Zeit.
*Entscheidung:* Modulith in Phase 1, Microservice-Extraktion in Phase 2 bei Bedarf.

**[Stack #2]: Python für Jobs, Scripts und SKOS-Service**
*Konzept:* Python/FastAPI für: SKOS-Codelisten-REST-Service, Validierungsjobs, Entwicklungszeit-Scripts (Codelisten-Download + Konvertierung), DB-Migrations-Hilfsskripte. Wo Java zu viel Overhead erzeugt — Python.
*Entscheidung:* Polyglot nur wo sinnvoll, nicht als Prinzip.

**[Stack #3]: BFF (Backend for Frontend) — Spring Boot (thin)**
*Konzept:* BFF-Layer zwischen Angular SPA und Modulith-API. Aufgaben: Keycloak Token-Exchange (Authorization Code Flow mit PKCE), API-Aggregation für Frontend-optimierte Responses, CSRF-Schutz, Session-Management. Einziger Einstiegspunkt durch Istio Ingress Gateway.
*Entscheidung:* BFF als eigenständiger Spring Boot Service (thin, wenig Logik).

**[Stack #4]: Frontend — Angular (BAMF-Standard) + Angular Material + BAMF Design**
*Konzept:* Angular SPA mit Angular Material als Komponentenbibliothek. BAMF Corporate Design als Theme-Override auf Material. Modernes, barrierefreies Design. BITV-konformes Farbschema (Ampelfarben mit Icon-Redundanz für Farbenblinde).
*Entscheidung:* Angular als BAMF-Standard, Material als Basis-UI, BAMF-Styling als Theme.

**[Stack #5]: Testing-Strategie**
*Konzept:*
- **Unit-Tests (Java):** JUnit 5 + Mockito, optional Cucumber/Gherkin für fachliche Unit-Tests
- **Integration-Tests (Java):** Cucumber + JUnit 5 (BDD/Gherkin, Spring Boot Test Context)
- **API/E2E-Integration-Tests:** Python Behave (BDD/Gherkin) — externe API-Tests gegen laufendes System
- **Frontend-Tests:** Angular Testing Library + Karma/Jest für Komponenten, Cypress für E2E
*Entscheidung:* BDD durchgängig auf Integrations- und Akzeptanzebene; Unit-Tests pragmatisch.

**[Stack #6]: Build & Deployment**
*Konzept:*
- **Java:** Gradle (moderner als Maven, bessere Multi-Modul-Unterstützung)
- **Python:** Poetry + pip
- **Orchestrierung:** Makefile (einheitlicher Einstiegspunkt: `make dev`, `make test`, `make deploy-k3s`)
- **Container:** Docker Multi-Stage Builds
- **K3S Deployment:** Helm Charts pro Service + Umbrella-Chart
- **Stage-Konfiguration:** Spring Profiles (`dev`, `test`, `prod`) + Helm Values-Dateien je Stage (`values-dev.yaml`, `values-test.yaml`, `values-prod.yaml`) + K8S ConfigMaps/Secrets
- **Docker Compose:** `docker-compose.yml` (Basis) + `docker-compose.override.yml` (Dev-Overrides)
*Entscheidung:* Ein `make`-Befehl für jeden Workflow — keine manuelle Schritt-für-Schritt-Ausführung.

### Gelöste Constraints — Entscheidungsmatrix

| Frage | Entscheidung | Grund |
|---|---|---|
| DuckDB vs PostgreSQL | PostgreSQL | Concurrency |
| Microservices vs Modulith | Modulith | Phase-1-Geschwindigkeit |
| Event Sourcing | Nein in Phase 1 | Zu komplex |
| Push Notification | Nein (Session-Popup) | Phase-1-Scope |
| AZR-Validierung | Nein | Manuell korrigierbar + Alias-ID |
| GUI für Task-Typen | Nein Phase 1 | SQL-Admin reicht |
| Externe Karten-API | Nein | Lokale MBTiles |
| Automatisches Belegungsmanagement | Nein (nur Vorschlag) | SB entscheidet immer |

---

## Nachträgliche Ergänzungen (nach Six Thinking Hats / Constraint Mapping)

### Dual-Stack-Entscheidung

**[Stack-Entscheidung]: Demo Stack ZUERST — Enterprise Stack auf Abruf**

Das System wird in zwei Ausbaustufen implementiert, die architektonisch denselben Funktionsumfang abdecken:

#### Demo Stack (Priorität: diese Woche)

| Komponente | Technologie |
|---|---|
| Backend | Python / FastAPI |
| Frontend | React + modernes UI-Framework (shadcn/ui + Tailwind CSS oder MUI) |
| Datenbank | PostgreSQL (Docker) |
| Auth | Keycloak (vereinfacht) oder JWT-basiert |
| Deployment | Shell-Skripte + Docker Compose, keine K8S/Istio |
| Features | Vollständiger Funktionsumfang, KEIN Circuit Breaker / Scaling / Istio-Features |
| UI-Framework | MUI (Material UI) für React |
| Auth | Keycloak in Docker |
| Karte | Lokale MBTiles + Tile-Server (Docker Container) |
| Design | Super modernes Design, sehr ansprechende Benutzerführung, visuell ansprechend |
| Installation | Ein Skript, läuft lokal auf einem Rechner ohne Vorkenntnisse |

*Entscheidung:* Demo Stack wird als erstes vollständig implementiert. Enterprise Stack erst auf explizite Anforderung.

#### Enterprise Stack (auf Abruf)

| Komponente | Technologie |
|---|---|
| Backend | Java Spring Boot Modulith |
| BFF | Spring Boot (thin) |
| Frontend | Angular + Angular Material + BAMF Design |
| Jobs/Scripts | Python |
| Deployment | Helm Charts + K3S + Istio |
| Testing | JUnit 5 / Cucumber (Java) + Python Behave (E2E) |
| Build | Gradle + Makefile |

---

### Neue funktionale Anforderung: EU-Gesamtquote

**[Funktional #10]: EU-Kapazitätsquote und Verteilung**
*Konzept:* Die EU legt fest, wie viele Betten/Unterkünfte Deutschland als Gesamtkontingent bereitstellen muss. Diese Gesamtzahl wird im System eingetragen (Admin-Funktion). Die Behörden verteilen dieses Gesamtkontingent als Lokations-Kontingente auf die verschiedenen Einrichtungen. Die Summe aller Lokations-Kontingente darf das EU-Gesamtkontingent nicht überschreiten — das System validiert und warnt.
*Besonderheit:* Drei Ebenen: EU-Vorgabe (read-only nach Eintrag) → Deutschland-Gesamtkontingent → Lokations-Kontingente. Verteilung ist Aufgabe der zuständigen Behörden.

**[Funktional #11]: EU-Compliance-Reporting als PDF**
*Konzept:* Reporting-Modul erzeugt auf Anfrage strukturierte PDF-Berichte als Nachweis für die EU:
- Zeiträume: Monat, Quartal, Jahr
- Inhalt: Belegungsauslastung, Kontingentnutzung, Bettkapazitäten je Einrichtung vs. EU-Vorgabe
- Ausgabe: PDF-Download (Phase 1: manuell herunterladen + per E-Mail senden; Phase 2: automatisierter Versand)
- Statistiken über Zeit: Trends, Spitzen, Durchschnittsbelegung
*Entscheidung:* PDF-Generierung als eigenes Modul (z.B. WeasyPrint in Python oder JasperReports/iText in Java).

### Offene Fragen (zur Klärung in späteren Phasen)
- Welche XAusländer-Codelisten konkret benötigt (nach DB-Design)
- Granularität der Karten-Tiles (ganz Deutschland vs. relevante Grenzregionen)
- BAMF Corporate Design Guidelines (Farben, Fonts, Logoregeln) — nur für Enterprise Stack relevant
- K3S-Ressourcenanforderungen für lokalen Betrieb (RAM/CPU)
- Behave vs. Cucumber für Integration-Tests — finale Entscheidung nach erstem Spike
- Exaktes EU-Reporting-Format und Empfänger-Schnittstelle (Phase 2)
- ~~React UI-Framework-Entscheidung~~ → **MUI (Material UI)** ✓ bestätigt
