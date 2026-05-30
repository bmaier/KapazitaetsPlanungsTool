---
title: 'Keycloak E-Mail-Onboarding: Passwort-Selbstvergabe + Reset per E-Mail'
type: 'feature'
created: '2026-05-30'
status: 'in-review'
baseline_commit: '16f5beb1ca4f35809724617cd88cea31fe5272e5'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Admin kann in Keycloak neue User anlegen und eine E-Mail hinterlegen, aber der User wird nicht automatisch aufgefordert, sein Passwort selbst zu setzen und seine E-Mail zu bestätigen. Passwort-Reset per E-Mail-Link funktioniert mangels SMTP-Konfiguration nicht.

**Approach:** SMTP-Server im Realm konfigurieren (Mailpit für Dev, echtes SMTP per Env-Vars für Prod), Required Actions `VERIFY_EMAIL` + `UPDATE_PASSWORD` als Standard für neue User aktivieren, und einen lokalen Mail-Catcher (Mailpit) im Dev-Compose ergänzen.

## Boundaries & Constraints

**Always:**
- SMTP-Zugangsdaten (User/Passwort) dürfen niemals in realm-export.json committed werden — nur Host/Port/From (keine Auth) für den Dev-Mailpit
- realm-export.json bleibt die einzige Quelle der Wahrheit für Realm-Konfiguration im Repo
- Alle 14 bestehenden Demo-User in realm-export.json bleiben unverändert
- Mailpit läuft nur im docker-compose.override.yml (kein Prod-Service)

**Ask First:**
- Falls der Kunde einen bestehenden SMTP-Server (z.B. Office 365, Sendgrid) hat, der in .env.example eingetragen werden soll, Berthold fragen bevor Defaults gesetzt werden
- Falls der Absender-Name/Adresse vom Default `noreply@bordercapcontrol.local` abweichen soll

**Never:**
- Keycloak-Registration (Selbstregistrierung) aktivieren — User werden ausschließlich durch Admins angelegt
- TOTP/MFA als Pflichtaktion einrichten (liegt außerhalb des Scopes)
- SMTP-Credentials in realm-export.json eintragen

## I/O & Edge-Case Matrix

| Szenario | Eingabe / Zustand | Erwartetes Verhalten | Fehlerbehandlung |
|----------|-------------------|----------------------|------------------|
| Admin legt User an | Admin erstellt User im KC-Admin-UI mit E-Mail | User hat automatisch VERIFY_EMAIL + UPDATE_PASSWORD als Required Actions; beim nächsten Login wird er zu Passwort-Vergabe + E-Mail-Bestätigung aufgefordert | – |
| Admin sendet Setup-Link | Admin klickt „Aktionen → Verifizierungs-E-Mail senden" | User erhält E-Mail mit Link (Mailpit in Dev), klickt Link, setzt Passwort und bestätigt E-Mail | SMTP-Fehler: KC zeigt Admin-Fehlermeldung |
| Erster Login | User meldet sich erstmalig an | KC-Flows: zuerst UPDATE_PASSWORD (Passwort vergeben), dann VERIFY_EMAIL (Link per Mail) | E-Mail-Zustellung schlägt fehl: Link-Seite zeigt Retry-Möglichkeit |
| Passwort vergessen | User klickt „Passwort vergessen" auf Login-Seite, gibt E-Mail ein | User erhält Reset-Link per E-Mail | Ungültige/unbekannte E-Mail: keine Fehlermeldung (Anti-Enumeration) |
| Dev-Mailpit | Irgendeine E-Mail wird von KC gesendet | E-Mail erscheint in Mailpit-WebUI unter http://localhost:8025 | – |

</frozen-after-approval>

## Code Map

- `infra/keycloak/realm-export.json` — Realm-Konfiguration: smtpServer, verifyEmail, requiredActions, defaultRequiredActions
- `docker-compose.override.yml` — Dev-Overrides: Mailpit-Service ergänzen
- `.env.example` — SMTP-Env-Vars für Produktion dokumentieren
- `docker-compose.yml` — Keycloak-Service: SMTP-Env-Vars durchreichen (für Prod-Override)
- `docs/KONZEPT.md` — Admin-Workflow für User-Anlage dokumentieren

## Tasks & Acceptance

**Execution:**
- [x] `infra/keycloak/realm-export.json` -- SMTP-Config hinzufügen (`smtpServer` mit host=mailpit, port=1025, from=noreply@bordercapcontrol.local, fromDisplayName=BorderCapControl, ssl=false, auth=false); `verifyEmail: true` setzen; `requiredActions`-Array mit Standard-KC24-Actions befüllen, dabei VERIFY_EMAIL und UPDATE_PASSWORD auf `enabled: true, defaultAction: true` setzen; `defaultRequiredActions: ["VERIFY_EMAIL", "UPDATE_PASSWORD"]` setzen -- Kern der Feature-Aktivierung
- [x] `docker-compose.override.yml` -- Mailpit-Service ergänzen (image: axllent/mailpit, ports: 1025/SMTP + 8025/WebUI, networks: bordercap_net) -- lokaler Mail-Catcher für Dev-Tests ohne echten SMTP-Server
- [x] `.env.example` -- SMTP-Block hinzufügen mit Variablen KC_SMTP_HOST, KC_SMTP_PORT, KC_SMTP_FROM, KC_SMTP_USER, KC_SMTP_PASSWORD und Erklärung wann für Prod benötigt -- Dokumentation für Prod-Betrieb
- [x] `docker-compose.yml` -- Im Keycloak-Service: Env-Vars KC_SMTP_* → KC-Startup-Params durchreichen (nur für Prod-Overrides; Dev nutzt realm-export SMTP-Config) -- Ermöglicht Prod-Konfiguration ohne realm-export-Änderung
- [x] `docs/KONZEPT.md` -- Abschnitt „Benutzerverwaltung / E-Mail-Onboarding" ergänzen: Admin-Workflow (User anlegen → E-Mail setzen → Required Actions prüfen → Verifizierungs-E-Mail senden), Prod-SMTP-Konfiguration (KC Admin-UI: Realm Settings → E-Mail), Mailpit-URL für Dev -- Betriebsdokumentation

**Acceptance Criteria:**
- Given Dev-Stack läuft (`make dev`), when Admin in Keycloak einen neuen User mit E-Mail anlegt und auf „Aktionen → Verifizierungs-E-Mail senden" klickt, then erscheint die E-Mail in Mailpit unter http://localhost:8025
- Given neuer User existiert mit Required Actions VERIFY_EMAIL + UPDATE_PASSWORD, when User sich erstmalig einloggt, then fordert Keycloak ihn auf, ein Passwort zu setzen und danach seine E-Mail zu bestätigen
- Given User ist eingeloggt, when User auf „Passwort vergessen" klickt und seine E-Mail eingibt, then erhält er einen Reset-Link in Mailpit (Dev) und kann sein Passwort neu setzen
- Given bestehende Demo-User in realm-export.json, when Stack neu gestartet wird, then können alle bestehenden User sich weiterhin normal einloggen (keine Breaking Changes)
- Given Prod-Deployment, when KC_SMTP_HOST und KC_SMTP_PORT als Env-Vars gesetzt sind, then verwendet Keycloak den konfigurierten externen SMTP-Server

## Design Notes

**Warum Mailpit statt Mailhog:** Mailpit ist aktiv gepflegt (Mailhog deprecated), unterstützt modernes TLS-Testing, kleineres Image.

**Keycloak SMTP-Precedence:** realm-export.json setzt SMTP beim `--import-realm` nur beim ersten Import (wenn Realm noch nicht existiert). Bei laufenden Systemen muss SMTP über Keycloak Admin-UI (Realm Settings → E-Mail) oder Keycloak-REST-API aktualisiert werden. Für Dev ist das kein Problem (Stack wird oft neu gebaut).

**Prod-SMTP ohne Credentials im Repo:** Die SMTP-Auth-Kreds werden NICHT in realm-export.json eingetragen. Admin konfiguriert diese einmalig über Keycloak Admin-UI nach Erstdeployment. Alternativ können KC_SPI_* Env-Vars für CI/CD-Injection genutzt werden (in .env.example dokumentiert).

**requiredActions-Array:** Keycloak 24 erwartet alle Built-in Required Actions vollständig im Array — fehlen welche, werden sie bei Start als "unknown" markiert. Alle Standard-Actions (CONFIGURE_TOTP, UPDATE_PROFILE, VERIFY_EMAIL, UPDATE_PASSWORD, TERMS_AND_CONDITIONS, delete_account) werden mit korrekten `priority`-Werten eingetragen.

## Verification

**Commands:**
- `docker compose -f docker-compose.yml -f docker-compose.override.yml up -d` -- expected: alle Services starten, Mailpit auf Port 8025 erreichbar
- `curl -s http://localhost:8025/api/v1/messages | python3 -c "import json,sys; print('Mailpit OK')"` -- expected: `Mailpit OK` (leeres Postfach ist valide)

**Manual checks (if no CLI):**
- Keycloak Admin-UI → Realm bordercapcontrol → Realm Settings → E-Mail: SMTP-Host zeigt `mailpit`, Port `1025`
- Keycloak Admin-UI → Realm bordercapcontrol → Authentication → Required Actions: VERIFY_EMAIL und UPDATE_PASSWORD sind als „Standard-Aktion" aktiviert
- Neuen Test-User anlegen mit E-Mail → „Aktionen → Verifizierungs-E-Mail senden" → E-Mail erscheint in http://localhost:8025

## Spec Change Log
