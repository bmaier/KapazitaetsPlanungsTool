-- BorderCapControl PostgreSQL Initialisierung
-- Erstellt 6 fachliche Schemata, Grants und Basis-Tabellen
-- Wird beim ersten Container-Start von PostgreSQL automatisch ausgeführt

-- ---------------------------------------------------------------------------
-- 6 Fachliche Schemata
-- ---------------------------------------------------------------------------

CREATE SCHEMA IF NOT EXISTS capacity;
CREATE SCHEMA IF NOT EXISTS reservations;
CREATE SCHEMA IF NOT EXISTS persons;
CREATE SCHEMA IF NOT EXISTS audit;
CREATE SCHEMA IF NOT EXISTS tasks;
CREATE SCHEMA IF NOT EXISTS reference_data;

-- ---------------------------------------------------------------------------
-- Grants für app_role: Vollzugriff auf alle Schemata außer audit
-- ---------------------------------------------------------------------------

GRANT USAGE ON SCHEMA capacity, reservations, persons, tasks, reference_data TO app_role;
GRANT CREATE ON SCHEMA capacity, reservations, persons, tasks, reference_data TO app_role;

-- Zukünftige Tabellen in diesen Schemata automatisch zugänglich machen.
-- FOR ROLE bordercap: gilt explizit für Tabellen die bordercap erstellt (z.B. via Alembic).
ALTER DEFAULT PRIVILEGES FOR ROLE bordercap IN SCHEMA capacity
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_role;
ALTER DEFAULT PRIVILEGES FOR ROLE bordercap IN SCHEMA reservations
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_role;
ALTER DEFAULT PRIVILEGES FOR ROLE bordercap IN SCHEMA persons
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_role;
ALTER DEFAULT PRIVILEGES FOR ROLE bordercap IN SCHEMA tasks
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_role;
ALTER DEFAULT PRIVILEGES FOR ROLE bordercap IN SCHEMA reference_data
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_role;

-- audit: Nur USAGE + INSERT — KEIN UPDATE/DELETE für app_role (Manipulationsschutz!)
GRANT USAGE ON SCHEMA audit TO app_role;

-- audit_role: Lesezugriff für Compliance-Abfragen
GRANT USAGE ON SCHEMA audit TO audit_role;

-- ---------------------------------------------------------------------------
-- Placeholder-Tabellen für Health-Check und erste Migration
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS capacity.locations (
    id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL    DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS persons.occupants (
    id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL    DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS audit.events (
    id         UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type VARCHAR(100) NOT NULL,
    payload    JSONB,
    created_at TIMESTAMPTZ  NOT NULL    DEFAULT NOW()
);

-- ---------------------------------------------------------------------------
-- Explizite Grants auf konkrete Tabellen
-- ---------------------------------------------------------------------------

-- app_role darf auf Nicht-Audit-Tabellen voll zugreifen
GRANT SELECT, INSERT, UPDATE, DELETE ON capacity.locations    TO app_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON persons.occupants     TO app_role;

-- Audit-Tabelle: NUR INSERT für app_role — kein SELECT, UPDATE, DELETE!
GRANT INSERT ON audit.events TO app_role;

-- audit_role darf audit-Tabellen lesen (Compliance)
GRANT SELECT ON audit.events TO audit_role;
