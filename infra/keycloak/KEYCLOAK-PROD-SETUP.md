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

### Schritt 5: Ersten Admin-User anlegen

```bash
./setup-prod-user.sh \
  --username admin.mustermann \
  --email admin.mustermann@meine-behoerde.de \
  --firstname Admin \
  --lastname Mustermann \
  --role system-admin
```

Der User erhält sofort eine Onboarding-E-Mail und kann sein Passwort selbst setzen.

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

### 6. Ersten User anlegen

Users → „Benutzer erstellen":
1. Username, E-Mail, Vor-/Nachname eintragen
2. „Erstellen" klicken
3. Tab „Rollen" → Rolle zuweisen
4. Tab „Attribute" → `location_id` setzen (wenn kein system-admin)
5. Aktionen-Dropdown → „Verifizierungs-E-Mail senden"

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
