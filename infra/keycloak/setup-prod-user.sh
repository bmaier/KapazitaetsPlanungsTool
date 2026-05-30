#!/usr/bin/env bash
# =============================================================================
# BorderCapControl — Einzelnen User anlegen und Setup-Link senden
# =============================================================================
# Legt einen neuen Nutzer an und versendet sofort die Onboarding-E-Mail
# (Passwort setzen + E-Mail bestätigen).
#
# Verwendung:
#   ./setup-prod-user.sh \
#     --username max.mustermann \
#     --email max.mustermann@behoerde.de \
#     --firstname Max \
#     --lastname Mustermann \
#     --role writer \
#     [--location-id <UUID>]
#
# Oder interaktiv ohne Parameter einfach starten.
# =============================================================================

set -euo pipefail

KC_URL="${KC_URL:-http://localhost:8080}"
KC_ADMIN="${KC_ADMIN:-admin}"
KC_ADMIN_PW="${KC_ADMIN_PW:-admin_dev}"
REALM="bordercapcontrol"

# Parameter einlesen
USERNAME=""
EMAIL=""
FIRSTNAME=""
LASTNAME=""
ROLE=""
LOCATION_ID=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --username)    USERNAME="$2";    shift 2 ;;
    --email)       EMAIL="$2";       shift 2 ;;
    --firstname)   FIRSTNAME="$2";   shift 2 ;;
    --lastname)    LASTNAME="$2";    shift 2 ;;
    --role)        ROLE="$2";        shift 2 ;;
    --location-id) LOCATION_ID="$2"; shift 2 ;;
    *) echo "Unbekannter Parameter: $1"; exit 1 ;;
  esac
done

# Interaktive Eingabe falls Parameter fehlen
prompt() { local var="$1" msg="$2"; if [ -z "${!var}" ]; then read -rp "$msg: " "$var"; fi; }
prompt USERNAME  "Username (z.B. max.mustermann)"
prompt EMAIL     "E-Mail-Adresse"
prompt FIRSTNAME "Vorname"
prompt LASTNAME  "Nachname"
prompt ROLE      "Rolle (reader|writer|location-admin|system-admin)"

# location_id: Für location-admin und writer empfohlen, für system-admin NICHT setzen
if [ -z "$LOCATION_ID" ] && [ "$ROLE" != "system-admin" ] && [ "$ROLE" != "reader" ]; then
  echo ""
  echo " Einrichtungs-ID (location_id) — für Rolle '$ROLE' erforderlich."
  echo " Die UUID findest du mit: ./list-locations.sh"
  echo " (leer lassen → kein Standort-Kontext, User sieht keine Einrichtungsdaten)"
  read -rp " location_id (UUID, leer = kein Standort): " LOCATION_ID
fi
# system-admin darf keine location_id haben (hat Vollzugriff über alle Standorte)
if [ "$ROLE" = "system-admin" ] && [ -n "$LOCATION_ID" ]; then
  echo " ⚠ system-admin darf keine location_id haben — wird ignoriert."
  LOCATION_ID=""
fi

echo ""
echo "=============================================="
echo " Lege User an: $USERNAME ($EMAIL)"
echo " Rolle: $ROLE"
if [ -n "$LOCATION_ID" ]; then
  echo " Standort-ID: $LOCATION_ID"
else
  [ "$ROLE" = "system-admin" ] && echo " Standort: (keiner — system-admin hat Vollzugriff)" \
    || echo " Standort: (kein Standort-Kontext)"
fi
echo "=============================================="

# Admin-Token
TOKEN_RESPONSE=$(curl -sf -X POST \
  "$KC_URL/realms/master/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password&client_id=admin-cli&username=$KC_ADMIN&password=$KC_ADMIN_PW")
ACCESS_TOKEN=$(echo "$TOKEN_RESPONSE" | jq -r '.access_token')

# Attribute vorbereiten
ATTRIBUTES="{}"
if [ -n "$LOCATION_ID" ]; then
  ATTRIBUTES="{\"location_id\": [\"$LOCATION_ID\"]}"
fi

# 1. User anlegen
echo "[1/4] User anlegen..."
CREATE_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
  "$KC_URL/admin/realms/$REALM/users" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"username\": \"$USERNAME\",
    \"email\": \"$EMAIL\",
    \"firstName\": \"$FIRSTNAME\",
    \"lastName\": \"$LASTNAME\",
    \"enabled\": true,
    \"emailVerified\": false,
    \"requiredActions\": [\"UPDATE_PASSWORD\", \"VERIFY_EMAIL\"],
    \"attributes\": $ATTRIBUTES
  }")

HTTP_CODE=$(echo "$CREATE_RESPONSE" | tail -1)
if [ "$HTTP_CODE" != "201" ]; then
  echo "FEHLER: User konnte nicht angelegt werden (HTTP $HTTP_CODE)"
  echo "$CREATE_RESPONSE" | head -1
  exit 1
fi
echo "   ✓ User angelegt"

# 2. User-ID ermitteln
USER_ID=$(curl -sf \
  "$KC_URL/admin/realms/$REALM/users?username=$USERNAME&exact=true" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq -r '.[0].id')

if [ -z "$USER_ID" ] || [ "$USER_ID" = "null" ]; then
  echo "FEHLER: User-ID konnte nicht ermittelt werden."
  exit 1
fi
echo "   User-ID: $USER_ID"

# 3. Rolle zuweisen
echo "[2/4] Rolle '$ROLE' zuweisen..."
ROLE_ID=$(curl -sf \
  "$KC_URL/admin/realms/$REALM/roles/$ROLE" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq -r '.id')

if [ -z "$ROLE_ID" ] || [ "$ROLE_ID" = "null" ]; then
  echo "FEHLER: Rolle '$ROLE' nicht gefunden. Verfügbare Rollen: reader, writer, location-admin, system-admin"
  exit 1
fi

curl -sf -X POST \
  "$KC_URL/admin/realms/$REALM/users/$USER_ID/role-mappings/realm" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "[{\"id\": \"$ROLE_ID\", \"name\": \"$ROLE\"}]"
echo "   ✓ Rolle zugewiesen"

# 4. Onboarding-E-Mail senden
echo "[3/4] Sende Onboarding-E-Mail (Passwort setzen + E-Mail bestätigen)..."
MAIL_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" -X PUT \
  "$KC_URL/admin/realms/$REALM/users/$USER_ID/execute-actions-email" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '["UPDATE_PASSWORD", "VERIFY_EMAIL"]')

if [ "$MAIL_RESPONSE" = "204" ]; then
  echo "   ✓ Onboarding-E-Mail gesendet an: $EMAIL"
else
  echo "   ⚠ E-Mail konnte nicht gesendet werden (HTTP $MAIL_RESPONSE)"
  echo "     Bitte SMTP-Konfiguration in Keycloak Admin-UI prüfen."
  echo "     E-Mail kann manuell gesendet werden:"
  echo "     Keycloak Admin-UI → Users → $USERNAME → Aktionen → Verifizierungs-E-Mail senden"
fi

echo ""
echo "=============================================="
echo " ✓ User '$USERNAME' erfolgreich angelegt"
echo "=============================================="
echo ""
echo " Der Nutzer erhält eine E-Mail mit dem Link zum Passwort setzen."
echo " Nach erstem Login wird die E-Mail-Adresse bestätigt."
echo ""
echo " Direktlink zur Nutzerverwaltung:"
echo " $KC_URL/admin/master/console/#/$REALM/users/$USER_ID"
echo ""
