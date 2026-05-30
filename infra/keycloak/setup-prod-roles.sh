#!/usr/bin/env bash
# =============================================================================
# BorderCapControl — Keycloak Rollen-Setup
# =============================================================================
# Legt die vier Anwendungsrollen im Realm bordercapcontrol an.
# Kann unabhängig von setup-prod-realm.sh ausgeführt werden,
# wenn der Realm bereits existiert (z.B. nach manuellem Import).
#
# Rollen:
#   reader         — Nur-Lesen (Dashboard, Bettübersicht)
#   writer         — Belegungen anlegen/bearbeiten
#   location-admin — Einrichtungs-Admin (Reservierungen bestätigen, Audit-Log)
#   system-admin   — Vollzugriff auf alle Einrichtungen
# =============================================================================

set -euo pipefail

KC_URL="${KC_URL:-http://localhost:8080}"
KC_ADMIN="${KC_ADMIN:-admin}"
KC_ADMIN_PW="${KC_ADMIN_PW:-admin_dev}"
REALM="bordercapcontrol"

echo "=============================================="
echo " BorderCapControl — Rollen-Setup"
echo "=============================================="

# Admin-Token
TOKEN_RESPONSE=$(curl -sf -X POST \
  "$KC_URL/realms/master/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password&client_id=admin-cli&username=$KC_ADMIN&password=$KC_ADMIN_PW")
ACCESS_TOKEN=$(echo "$TOKEN_RESPONSE" | jq -r '.access_token')

create_role() {
  local name="$1"
  local description="$2"
  local response
  response=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
    "$KC_URL/admin/realms/$REALM/roles" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"name\": \"$name\", \"description\": \"$description\"}")
  if [ "$response" = "201" ]; then
    echo "   ✓ Rolle '$name' angelegt"
  elif [ "$response" = "409" ]; then
    echo "   ○ Rolle '$name' existiert bereits"
  else
    echo "   ✗ Fehler bei Rolle '$name' (HTTP $response)"
  fi
}

create_role "reader"         "Lesezugriff: Dashboard und Bettübersicht"
create_role "writer"         "Schreibzugriff: Belegungen anlegen und bearbeiten"
create_role "location-admin" "Einrichtungs-Admin: Reservierungen bestätigen, Audit-Log"
create_role "system-admin"   "System-Admin: Vollzugriff auf alle Einrichtungen"

echo ""
echo " Rollen erfolgreich konfiguriert."
echo " Weiter mit Benutzeranlage in Keycloak Admin-UI:"
echo " $KC_URL/admin/master/console/#/$REALM/users"
echo ""
