#!/usr/bin/env bash
# BorderCapControl — DB-Rollen Setup
# Ersetzt 00_roles.sql um das bordercap_app-Passwort aus der Umgebungsvariable zu lesen.
# PostgreSQL führt .sh-Skripte im docker-entrypoint-initdb.d-Verzeichnis vor .sql-Dateien aus.
set -euo pipefail

# :'pg_password' nutzt psql-Variable-Interpolation mit korrektem SQL-Quoting,
# damit Sonderzeichen im Passwort keine SQL-Syntaxfehler verursachen.
psql -v ON_ERROR_STOP=1 \
     --username "$POSTGRES_USER" \
     --dbname "$POSTGRES_DB" \
     --set=pg_password="${POSTGRES_APP_PASSWORD:-bordercap_app_dev}" \
     <<-EOSQL
    -- Applikationsrolle: Lese-/Schreibzugriff auf alle Schemata außer audit (nur INSERT)
    DO \$\$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'app_role') THEN
            CREATE ROLE app_role;
        END IF;
    END
    \$\$;

    -- Audit-Rolle: Nur-Lese-Zugriff auf Audit-Schema für Compliance-Abfragen
    DO \$\$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'audit_role') THEN
            CREATE ROLE audit_role;
        END IF;
    END
    \$\$;

    -- Superuser bekommt app_role für Abwärtskompatibilität
    GRANT app_role TO $POSTGRES_USER;

    -- Dedizierter Non-Superuser-Login für Applikation und Tests
    -- Passwort kommt aus POSTGRES_APP_PASSWORD (Env-Var), Dev-Default: bordercap_app_dev
    -- ELSE-Zweig: bei Wiederholung (z.B. Passwort-Rotation) wird Passwort aktualisiert
    DO \$\$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'bordercap_app') THEN
            CREATE ROLE bordercap_app WITH LOGIN PASSWORD :'pg_password' NOSUPERUSER NOCREATEDB NOCREATEROLE;
        ELSE
            ALTER ROLE bordercap_app WITH PASSWORD :'pg_password';
        END IF;
    END
    \$\$;
    GRANT app_role TO bordercap_app;
EOSQL
