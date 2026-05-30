#!/usr/bin/env bash
# =============================================================================
# BorderCapControl — Keycloak Prod-Setup-Skript
# =============================================================================
# Richtet den Realm bordercapcontrol auf einer bestehenden Keycloak-Instanz ein.
# Einsatz: Wenn NICHT der vorkonfigurierte Docker-Container verwendet wird,
# z.B. bei vorhandenem Keycloak-Server einer Behörde oder Cloud-Instanz.
#
# Voraussetzungen:
#   - curl und jq installiert
#   - Keycloak 20+ läuft und ist erreichbar
#   - Admin-Zugangsdaten bekannt
#
# Verwendung:
#   chmod +x setup-prod-realm.sh
#   ./setup-prod-realm.sh
#
# Oder mit Umgebungsvariablen:
#   KC_URL=https://auth.meine-behoerde.de \
#   KC_ADMIN=admin \
#   KC_ADMIN_PW=geheimesPasswort \
#   ./setup-prod-realm.sh
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Konfiguration (aus Umgebungsvariablen oder Defaults)
# ---------------------------------------------------------------------------
KC_URL="${KC_URL:-http://localhost:8080}"
KC_ADMIN="${KC_ADMIN:-admin}"
KC_ADMIN_PW="${KC_ADMIN_PW:-admin_dev}"
REALM="bordercapcontrol"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=============================================="
echo " BorderCapControl — Keycloak Realm Setup"
echo "=============================================="
echo " Keycloak-URL : $KC_URL"
echo " Realm        : $REALM"
echo " Admin        : $KC_ADMIN"
echo ""

# ---------------------------------------------------------------------------
# 1. Admin-Token holen
# ---------------------------------------------------------------------------
echo "[1/6] Hole Admin-Token..."
TOKEN_RESPONSE=$(curl -sf -X POST \
  "$KC_URL/realms/master/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password&client_id=admin-cli&username=$KC_ADMIN&password=$KC_ADMIN_PW")

ACCESS_TOKEN=$(echo "$TOKEN_RESPONSE" | jq -r '.access_token')
if [ -z "$ACCESS_TOKEN" ] || [ "$ACCESS_TOKEN" = "null" ]; then
  echo "FEHLER: Konnte kein Admin-Token holen. Zugangsdaten oder URL prüfen."
  exit 1
fi
echo "   ✓ Admin-Token erhalten"

# ---------------------------------------------------------------------------
# Hilfsfunktion: KC API-Aufruf
# ---------------------------------------------------------------------------
kc_api() {
  local method="$1"
  local path="$2"
  shift 2
  curl -sf -X "$method" \
    "$KC_URL/admin/realms/$REALM$path" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    "$@"
}

kc_api_master() {
  local method="$1"
  local path="$2"
  shift 2
  curl -sf -X "$method" \
    "$KC_URL/admin$path" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    "$@"
}

# ---------------------------------------------------------------------------
# 2. Realm importieren oder prüfen ob er existiert
# ---------------------------------------------------------------------------
echo "[2/6] Prüfe ob Realm '$REALM' existiert..."
REALM_EXISTS=$(curl -sf -o /dev/null -w "%{http_code}" \
  "$KC_URL/admin/realms/$REALM" \
  -H "Authorization: Bearer $ACCESS_TOKEN" || true)

if [ "$REALM_EXISTS" = "200" ]; then
  echo "   ✓ Realm existiert bereits — überspringe Import, führe nur Updates durch"
else
  echo "   → Importiere Realm aus realm-export.json..."
  REALM_JSON="$SCRIPT_DIR/realm-export.json"
  if [ ! -f "$REALM_JSON" ]; then
    echo "FEHLER: $REALM_JSON nicht gefunden."
    exit 1
  fi
  curl -sf -X POST \
    "$KC_URL/admin/realms" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d @"$REALM_JSON"
  echo "   ✓ Realm importiert"
fi

# ---------------------------------------------------------------------------
# 3. E-Mail-Verifizierung + Passwort-Reset aktivieren
# ---------------------------------------------------------------------------
echo "[3/6] Aktiviere verifyEmail + resetPasswordAllowed..."
# KC REST-API erfordert vollständiges Realm-Objekt beim PUT — Felder einzeln patchen
CURRENT_REALM=$(curl -sf "$KC_URL/admin/realms/$REALM" \
  -H "Authorization: Bearer $ACCESS_TOKEN")
PATCHED_REALM=$(echo "$CURRENT_REALM" | python3 -c "
import json, sys
d = json.load(sys.stdin)
d['verifyEmail'] = True
d['resetPasswordAllowed'] = True
d['registrationAllowed'] = False
print(json.dumps(d))
")
HTTP=$(curl -s -o /dev/null -w "%{http_code}" -X PUT \
  "$KC_URL/admin/realms/$REALM" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "$PATCHED_REALM")
[ "$HTTP" = "204" ] && echo "   ✓ Realm-Settings aktualisiert" || echo "   ⚠ Realm-PUT HTTP $HTTP"

# ---------------------------------------------------------------------------
# 4. Required Actions konfigurieren
# ---------------------------------------------------------------------------
echo "[4/6] Konfiguriere Required Actions (VERIFY_EMAIL, UPDATE_PASSWORD als Standard)..."

# UPDATE_PASSWORD als Standard-Aktion aktivieren
curl -sf -X PUT \
  "$KC_URL/admin/realms/$REALM/authentication/required-actions/UPDATE_PASSWORD" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "alias": "UPDATE_PASSWORD",
    "name": "Update Password",
    "providerId": "UPDATE_PASSWORD",
    "enabled": true,
    "defaultAction": true,
    "priority": 30,
    "config": {}
  }' || echo "   ⚠ UPDATE_PASSWORD konnte nicht gesetzt werden (evtl. bereits korrekt)"

# VERIFY_EMAIL als Standard-Aktion aktivieren
curl -sf -X PUT \
  "$KC_URL/admin/realms/$REALM/authentication/required-actions/VERIFY_EMAIL" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "alias": "VERIFY_EMAIL",
    "name": "Verify Email",
    "providerId": "VERIFY_EMAIL",
    "enabled": true,
    "defaultAction": true,
    "priority": 50,
    "config": {}
  }' || echo "   ⚠ VERIFY_EMAIL konnte nicht gesetzt werden (evtl. bereits korrekt)"

echo "   ✓ Required Actions konfiguriert"

# ---------------------------------------------------------------------------
# 5. SMTP konfigurieren (nur wenn Env-Vars gesetzt)
# ---------------------------------------------------------------------------
echo "[5/6] SMTP-Konfiguration..."
KC_SMTP_HOST="${KC_SMTP_HOST:-}"
KC_SMTP_PORT="${KC_SMTP_PORT:-587}"
KC_SMTP_FROM="${KC_SMTP_FROM:-}"

if [ -n "$KC_SMTP_HOST" ] && [ -n "$KC_SMTP_FROM" ]; then
  KC_SMTP_USER="${KC_SMTP_USER:-}"
  KC_SMTP_PASSWORD="${KC_SMTP_PASSWORD:-}"
  KC_SMTP_STARTTLS="${KC_SMTP_STARTTLS:-true}"
  KC_SMTP_SSL="${KC_SMTP_SSL:-false}"
  KC_SMTP_FROM_DISPLAY="${KC_SMTP_FROM_DISPLAY:-BorderCapControl}"

  AUTH_VALUE="false"
  if [ -n "$KC_SMTP_USER" ]; then AUTH_VALUE="true"; fi

  CURRENT_REALM2=$(curl -sf "$KC_URL/admin/realms/$REALM" \
    -H "Authorization: Bearer $ACCESS_TOKEN")
  PATCHED_SMTP=$(echo "$CURRENT_REALM2" | python3 -c "
import json, sys, os
d = json.load(sys.stdin)
d['smtpServer'] = {
  'host': os.environ['KC_SMTP_HOST'],
  'port': os.environ['KC_SMTP_PORT'],
  'from': os.environ['KC_SMTP_FROM'],
  'fromDisplayName': os.environ.get('KC_SMTP_FROM_DISPLAY', 'BorderCapControl'),
  'ssl': os.environ.get('KC_SMTP_SSL', 'false'),
  'starttls': os.environ.get('KC_SMTP_STARTTLS', 'true'),
  'auth': '$AUTH_VALUE',
  'user': os.environ.get('KC_SMTP_USER', ''),
  'password': os.environ.get('KC_SMTP_PASSWORD', ''),
}
print(json.dumps(d))
")
  HTTP_SMTP=$(curl -s -o /dev/null -w "%{http_code}" -X PUT \
    "$KC_URL/admin/realms/$REALM" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d "$PATCHED_SMTP")
  [ "$HTTP_SMTP" = "204" ] && echo "   ✓ SMTP konfiguriert: $KC_SMTP_HOST:$KC_SMTP_PORT" || echo "   ⚠ SMTP-PUT HTTP $HTTP_SMTP"
else
  echo "   ⚠ KC_SMTP_HOST / KC_SMTP_FROM nicht gesetzt — SMTP übersprungen"
  echo "     Bitte SMTP manuell in Keycloak Admin-UI konfigurieren:"
  echo "     $KC_URL/admin/master/console/#/$REALM/realm-settings (Tab: E-Mail)"
fi

# ---------------------------------------------------------------------------
# 6. Zusammenfassung
# ---------------------------------------------------------------------------
echo ""
echo "=============================================="
echo " Setup abgeschlossen"
echo "=============================================="
echo ""
echo " Nächste Schritte:"
echo " 1. SMTP testen: Keycloak Admin-UI → Realm Settings → E-Mail → 'Verbindung testen'"
echo " 2. Test-User anlegen: Users → Benutzer erstellen (Username + E-Mail)"
echo " 3. Setup-Link senden: User auswählen → Aktionen → 'Verifizierungs-E-Mail senden'"
echo " 4. E-Mail im Postfach des Nutzers prüfen"
echo ""
echo " Rollen anlegen (falls neu):"
echo "   ./setup-prod-roles.sh"
echo ""
