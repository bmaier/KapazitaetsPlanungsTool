#!/usr/bin/env bash
# =============================================================================
# BorderCapControl — Einrichtungen (Locations) und ihre UUIDs anzeigen
# =============================================================================
# Gibt alle aktiven Einrichtungen mit UUID, Name und Status aus.
# Die UUID wird beim Anlegen eines Users als location_id-Attribut benötigt.
#
# Verwendung:
#   ./list-locations.sh
#
# Oder mit DB-Parametern:
#   DB_HOST=localhost DB_PORT=5432 DB_NAME=bordercap DB_USER=bordercap \
#   DB_PASSWORD=bordercap_dev ./list-locations.sh
# =============================================================================

DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-bordercap}"
DB_USER="${DB_USER:-bordercap}"
DB_PASSWORD="${DB_PASSWORD:-bordercap_dev}"

export PGPASSWORD="$DB_PASSWORD"

echo "=============================================="
echo " BorderCapControl — Einrichtungen (Locations)"
echo "=============================================="
echo ""

if ! command -v psql &>/dev/null; then
  echo "FEHLER: psql nicht gefunden. PostgreSQL-Client installieren:"
  echo "  macOS:  brew install postgresql"
  echo "  Ubuntu: apt install postgresql-client"
  echo ""
  echo "Alternativ direkt im DB-Container:"
  echo "  docker exec -it <postgres-container> psql -U $DB_USER -d $DB_NAME \\"
  echo "    -c \"SELECT id, name, is_active FROM capacity.locations ORDER BY name;\""
  exit 1
fi

psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
  --tuples-only --no-align --field-separator '|' \
  -c "SELECT id, name, is_active FROM capacity.locations ORDER BY name;" \
2>/dev/null | while IFS='|' read -r uuid name active; do
  uuid=$(echo "$uuid" | xargs)
  name=$(echo "$name" | xargs)
  active=$(echo "$active" | xargs)
  status="✓ aktiv"
  [ "$active" = "f" ] && status="✗ inaktiv"
  printf "  %-38s  %-30s  %s\n" "$uuid" "$name" "$status"
done

echo ""
echo " Diese UUID als --location-id beim User-Anlegen verwenden:"
echo "   ./setup-prod-user.sh --username ... --location-id <UUID>"
echo ""
echo " In Keycloak Admin-UI:"
echo "   Users → User auswählen → Tab 'Attributes'"
echo "   Key: location_id   Value: <UUID>"
echo ""
