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
