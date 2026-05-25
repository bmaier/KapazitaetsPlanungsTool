-- DB-Rollen für BorderCapControl Applikation
-- Wird vor init.sql ausgeführt (alphabetische Sortierung: 00_ vor 01_)

-- Applikationsrolle: Lese-/Schreibzugriff auf alle Schemata außer audit (nur INSERT)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'app_role') THEN
        CREATE ROLE app_role;
    END IF;
END
$$;

-- Audit-Rolle: Nur-Lese-Zugriff auf Audit-Schema für Compliance-Abfragen
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'audit_role') THEN
        CREATE ROLE audit_role;
    END IF;
END
$$;

-- Applikationsuser (Superuser) bekommt app_role für Abwärtskompatibilität
GRANT app_role TO bordercap;

-- Dedizierter Non-Superuser-Login für Applikation und Tests
-- Dieser User hat NUR app_role — kein SUPERUSER, kein CREATEDB, kein CREATEROLE.
-- Nötig damit Privilege-Checks (z.B. Audit-GRANT-Tests) korrekt funktionieren.
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'bordercap_app') THEN
        CREATE ROLE bordercap_app WITH LOGIN PASSWORD 'bordercap_app_dev' NOSUPERUSER NOCREATEDB NOCREATEROLE;
    END IF;
END
$$;
GRANT app_role TO bordercap_app;
