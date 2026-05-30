# BorderCapControl — Keycloak Produktiv-Setup

Anleitung für die Einrichtung auf einem **bestehenden Keycloak-Server** (ohne vorkonfigurierten Docker-Container).

## Voraussetzungen

- Keycloak 20 oder höher läuft und ist per Browser erreichbar
- Du hast Admin-Zugang zum Keycloak-Master-Realm
- `curl` und `jq` sind auf dem Setup-Rechner installiert (`brew install jq` / `apt install jq`)

---

## Option A — Automatisch mit Setup-Skript (empfohlen)

### Schritt 1: Umgebungsvariablen setzen

```bash
export KC_URL="https://auth.meine-behoerde.de"   # Keycloak-URL (kein /auth am Ende)
export KC_ADMIN="admin"                            # KC-Admin-Username
export KC_ADMIN_PW="IhrAdminPasswort"
```

### Schritt 2: Realm importieren und konfigurieren

```bash
cd infra/keycloak
./setup-prod-realm.sh
```

Das Skript:
- Importiert `realm-export.json` falls der Realm noch nicht existiert
- Aktiviert E-Mail-Verifizierung und Passwort-Reset
- Setzt `VERIFY_EMAIL` + `UPDATE_PASSWORD` als Pflichtaktionen für neue User

### Schritt 2b: Bordercap-Theme deployen

Das Custom-Theme liefert die deutsche Login-Seite, BSI-Policy-Box beim Passwort-setzen und den „Passwort vergessen"-Link.

```bash
# Theme in den Keycloak-Themes-Ordner kopieren
cp -r infra/keycloak/themes/bordercap/ /opt/keycloak/themes/
```

Danach in der Keycloak Admin-UI:
`Realm bordercapcontrol → Realm Settings → Themes → Login-Theme: bordercap → Speichern`

> Keycloak muss nach dem Kopieren **nicht** neu gestartet werden — Themes werden beim nächsten Seitenaufruf geladen.  
> Falls Änderungen an `.ftl`-Templates gemacht wurden: KC Admin-UI → `bordercapcontrol` → Realm Settings → Themes → Login-Theme neu setzen (leert den Theme-Cache).

### Schritt 3: Rollen anlegen

```bash
./setup-prod-roles.sh
```

Legt die vier Rollen an: `reader`, `writer`, `location-admin`, `system-admin`

### Schritt 4: SMTP konfigurieren

```bash
export KC_SMTP_HOST="smtp.office365.com"
export KC_SMTP_PORT="587"
export KC_SMTP_FROM="noreply@meine-behoerde.de"
export KC_SMTP_FROM_DISPLAY="BorderCapControl"
export KC_SMTP_USER="noreply@meine-behoerde.de"
export KC_SMTP_PASSWORD="IhrSMTP-Passwort"
export KC_SMTP_STARTTLS="true"
export KC_SMTP_SSL="false"

./setup-prod-realm.sh   # SMTP wird gesetzt wenn KC_SMTP_HOST gesetzt ist
```

**Alternativ in Keycloak Admin-UI:**
`Realm bordercapcontrol → Realm Settings → E-Mail → Werte eintragen → „Verbindung testen"`

### Schritt 5: Einrichtungs-IDs ermitteln (für standortgebundene Rollen)

Bevor Nutzer mit Standortbindung angelegt werden, müssen die UUIDs der Einrichtungen aus der Datenbank abgerufen werden:

```bash
./list-locations.sh
```

Ausgabe (Beispiel):
```
  3fa85f64-5717-4562-b3fc-2c963f66afa6   Frankfurt Ankunftszentrum   ✓ aktiv
  7c9e6679-7425-40de-944b-e07fc1f90ae7   Hamburg Erstaufnahme        ✓ aktiv
  ...
```

Diese UUIDs werden als `location_id`-Attribut beim User hinterlegt.

> **Wichtig — Rollenlogik:**
> - `system-admin` → **keine** `location_id` — hat Vollzugriff auf alle Einrichtungen
> - `location-admin`, `writer`, `reader` → **muss** `location_id` gesetzt haben, sonst sieht der User keine Einrichtungsdaten

### Schritt 6: Ersten System-Admin anlegen

```bash
./setup-prod-user.sh \
  --username admin.mustermann \
  --email admin.mustermann@meine-behoerde.de \
  --firstname Admin \
  --lastname Mustermann \
  --role system-admin
```

Der User erhält sofort eine Onboarding-E-Mail und kann sein Passwort selbst setzen.

### Schritt 7: Einrichtungs-Admins und Sachbearbeiter anlegen

```bash
# Einrichtungs-Admin für Frankfurt:
./setup-prod-user.sh \
  --username max.mustermann \
  --email max.mustermann@behoerde.de \
  --firstname Max \
  --lastname Mustermann \
  --role location-admin \
  --location-id 3fa85f64-5717-4562-b3fc-2c963f66afa6   # UUID aus list-locations.sh

# Sachbearbeiter (writer) für Hamburg:
./setup-prod-user.sh \
  --username erika.musterfrau \
  --email erika.musterfrau@behoerde.de \
  --firstname Erika \
  --lastname Musterfrau \
  --role writer \
  --location-id 7c9e6679-7425-40de-944b-e07fc1f90ae7
```

---

## Option B — Manuell über Keycloak Admin-UI

### 1. Realm importieren

1. Keycloak Admin-UI öffnen → „Realm hinzufügen"
2. `infra/keycloak/realm-export.json` hochladen → Importieren

### 2. E-Mail-Onboarding aktivieren

Realm `bordercapcontrol` → Realm Settings:

| Einstellung | Wert |
|-------------|------|
| Tab „Anmeldung" → Selbstregistrierung | **Aus** |
| Tab „Anmeldung" → Passwort vergessen | **Ein** |
| Tab „Anmeldung" → E-Mail als Benutzername | Beliebig |
| Tab „E-Mail" | (SMTP-Daten eintragen, siehe unten) |

### 3. Required Actions konfigurieren

Realm Settings → Authentication → Required Actions:

| Aktion | Status | Standard-Aktion |
|--------|--------|-----------------|
| Update Password | Aktiviert | **Ja** |
| Verify Email | Aktiviert | **Ja** |
| Configure OTP | Aktiviert | Nein |
| Update Profile | Aktiviert | Nein |

### 4. SMTP konfigurieren

Realm Settings → E-Mail:

| Feld | Wert (Beispiel Office 365) |
|------|---------------------------|
| Von | noreply@meine-behoerde.de |
| Von Anzeigename | BorderCapControl |
| Host | smtp.office365.com |
| Port | 587 |
| Verschlüsselung | STARTTLS aktivieren |
| Authentifizierung | Aktivieren |
| Benutzername | noreply@meine-behoerde.de |
| Passwort | (SMTP-Passwort) |

→ „Verbindung testen" klicken

### 5. Rollen anlegen

Realm `bordercapcontrol` → Realm-Rollen → „Rolle erstellen":

- `reader` — Lesezugriff
- `writer` — Belegungen bearbeiten
- `location-admin` — Einrichtungs-Admin
- `system-admin` — Vollzugriff

### 6. User anlegen

Users → „Benutzer erstellen":
1. Username, E-Mail, Vor-/Nachname eintragen
2. „Erstellen" klicken
3. Tab **„Role mapping"** → Rolle zuweisen (reader / writer / location-admin / system-admin)
4. Tab **„Attributes"** → `location_id` eintragen (nur für standortgebundene Rollen, **nicht** für system-admin):
   - Key: `location_id`
   - Value: UUID der Einrichtung (ermitteln via `./list-locations.sh` oder direkt in der DB)
5. Speichern
6. Tab **„Details"** → Feld „Required user actions": `Update Password` + `Verify Email` auswählen → Speichern
7. Aktionen-Dropdown → **„Send verification email"**

**Wo finde ich die Einrichtungs-UUID?**
- Skript: `./list-locations.sh` (braucht `psql`-Client und DB-Zugang)
- Datenbank direkt: `SELECT id, name FROM capacity.locations WHERE is_active = true ORDER BY name;`
- Anwendung: Dashboard → Einrichtung anklicken → UUID steht in der Browser-URL `/locations/{UUID}`

**Rollenlogik für location_id:**

| Rolle | location_id | Zugriff |
|-------|-------------|---------|
| `system-admin` | **nicht setzen** | Alle Einrichtungen |
| `location-admin` | UUID der Einrichtung | Nur diese Einrichtung |
| `writer` | UUID der Einrichtung | Nur diese Einrichtung |
| `reader` | UUID der Einrichtung (optional) | Nur diese Einrichtung |

---

## Frontend-Konfiguration

Die Frontend-App braucht die korrekte Keycloak-URL:

```bash
# In .env oder als Umgebungsvariable beim Deployment:
KEYCLOAK_PUBLIC_URL=https://auth.meine-behoerde.de
VITE_KEYCLOAK_URL=https://auth.meine-behoerde.de
```

---

## Regelmäßige User-Anlage (nach Erstsetup)

Für jeden neuen Mitarbeiter:

```bash
./setup-prod-user.sh \
  --username vorname.nachname \
  --email vorname.nachname@behoerde.de \
  --firstname Vorname \
  --lastname Nachname \
  --role writer \
  --location-id "UUID-der-Einrichtung"   # optional, nur für location-gebundene Rollen
```

Oder interaktiv (ohne Parameter): `./setup-prod-user.sh`

---

## Betriebsprozesse

### Neuen Mitarbeiter anlegen (Regelbetrieb)

```bash
./setup-prod-user.sh \
  --username vorname.nachname \
  --email vorname.nachname@behoerde.de \
  --firstname Vorname \
  --lastname Nachname \
  --role writer \
  --location-id "UUID-der-Einrichtung"
```

Der Nutzer erhält sofort die Onboarding-E-Mail und setzt sein Passwort selbst.

### Passwort-Reset für einen Nutzer auslösen

```bash
# User-ID ermitteln
TOKEN=$(curl -sf -X POST "$KC_URL/realms/master/protocol/openid-connect/token" \
  -d "grant_type=password&client_id=admin-cli&username=$KC_ADMIN&password=$KC_ADMIN_PW" \
  | jq -r '.access_token')

USER_ID=$(curl -sf "$KC_URL/admin/realms/bordercapcontrol/users?username=max.mustermann&exact=true" \
  -H "Authorization: Bearer $TOKEN" | jq -r '.[0].id')

# Reset-E-Mail senden
curl -sf -X PUT \
  "$KC_URL/admin/realms/bordercapcontrol/users/$USER_ID/execute-actions-email" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '["UPDATE_PASSWORD"]'
```

Alternativ: KC Admin-UI → Users → Nutzer auswählen → Aktionen → „Passwort zurücksetzen"-E-Mail senden.

### Standort eines Nutzers ändern

KC Admin-UI → Users → Nutzer auswählen → Tab „Attributes" → Wert von `location_id` anpassen → Speichern.

Der Nutzer muss sich danach neu einloggen (Token-Cache verfällt nach max. 5 Minuten).

### Abgelaufenen Onboarding-Link erneuern

Onboarding-Links sind 12 Stunden gültig. Falls ein Nutzer den Link verpasst hat:

KC Admin-UI → Users → Nutzer auswählen → Aktionen → „Verifizierungs-E-Mail senden"

Oder per Skript (wie `setup-prod-user.sh`, Schritt 3/4).

### Nutzer sperren / entsperren

**Sperren:** KC Admin-UI → Users → Nutzer auswählen → Tab „Details" → „Aktiviert" deaktivieren → Speichern.

**Entsperren (nach Brute-Force-Sperre):** KC Admin-UI → Users → Nutzer auswählen → Tab „Details" → Schaltfläche „Brute-Force-Sperre aufheben".

### Passwortrichtlinie prüfen / anpassen

KC Admin-UI → Realm `bordercapcontrol` → Realm Settings → Sicherheit → Passwortrichtlinie.

Aktuelle BSI-Policy:
```
length(12) and upperCase(1) and lowerCase(1) and digits(1) and specialChars(1) and notUsername and notEmail and passwordHistory(5)
```

Änderungen wirken sofort für neue Passwort-Setzungen (nicht für bestehende Passwörter).

### Realm-Konfiguration aktualisieren (ohne Container-Neustart)

Realm-Einstellungen können jederzeit über die KC Admin-UI geändert werden, ohne Neustart:
- Realm Settings → Tokens → Lifespan-Werte anpassen
- Realm Settings → E-Mail → SMTP-Zugangsdaten aktualisieren
- Authentication → Required Actions → Aktionen aktivieren/deaktivieren

### Keycloak startet nicht (Crash-Loop)

**Ursache prüfen:**
```bash
docker logs <keycloak-container> --tail 50
```

**Häufigste Ursache: Ungültiges Feld in realm-export.json**
Wenn der Log `UnrecognizedPropertyException` auf `realm-export.json` zeigt: Ungültiges Feld entfernen. Insbesondere `"defaultRequiredActions"` ist in KC 24 kein gültiges Top-Level-Feld — stattdessen `"defaultAction": true` auf den einzelnen `requiredActions`-Einträgen setzen. Siehe auch KONZEPT.md §9.

**Nach Fix:** Container neu starten:
```bash
docker restart <keycloak-container>
# oder mit docker compose:
docker compose restart keycloak
```

---

## Häufige Probleme

**E-Mail kommt nicht an:**
- SMTP-Verbindung testen: KC Admin-UI → Realm Settings → E-Mail → „Verbindung testen"
- Firewall: Port 587 (STARTTLS) oder 465 (SSL) muss nach außen offen sein
- SPF/DKIM: Absender-Domain muss den Keycloak-Server als gültigen Sender eintragen

**„Ungültige Redirect-URI" beim Login:**
- KC Admin-UI → Clients → `bordercapcontrol-frontend` → Valid Redirect URIs
- Produktive Frontend-URL eintragen: `https://bordercap.meine-behoerde.de/*`

**Token-Fehler / Endlosumleitung:**
- `KEYCLOAK_PUBLIC_URL` muss die URL sein, die der **Browser** für Keycloak verwendet
- Nicht die interne Docker/Kubernetes-URL, sondern die öffentliche HTTPS-URL

**Bestehende Docker-Dev-User in realm-export.json:**
- Die 14 Demo-User (azr-user-*, admin@*, etc.) können im Prod-Realm gelöscht werden
- KC Admin-UI → Users → alle Demo-User markieren → Löschen

**Nutzer sieht keine Einrichtungsdaten nach Login:**
- `location_id`-Attribut fehlt oder ist falsch gesetzt: KC Admin-UI → Users → Nutzer → Tab „Attributes"
- Nutzer muss sich neu einloggen damit der neue JWT-Token greift
- `system-admin` braucht keine `location_id` — alle anderen Rollen schon
