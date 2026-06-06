"""Label-Katalog als DB-Tabelle + Junction-Tables ersetzen TEXT[]

Revision ID: 0018
Revises: 0017
Create Date: 2026-06-06
"""
from alembic import op

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. CREATE capacity.label_catalog
    op.execute("""
        CREATE TABLE capacity.label_catalog (
            name          TEXT NOT NULL,
            entity_type   TEXT NOT NULL,
            is_system     BOOLEAN NOT NULL DEFAULT FALSE,
            category      TEXT NOT NULL,
            color         TEXT NOT NULL DEFAULT '#757575',
            sort_order    INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (entity_type, name)
        )
    """)

    # 2. CREATE junction tables
    op.execute("""
        CREATE TABLE capacity.location_labels (
            location_id       UUID NOT NULL
                REFERENCES capacity.locations(id) ON DELETE CASCADE,
            label_name        TEXT NOT NULL,
            label_entity_type TEXT NOT NULL DEFAULT 'LOCATION',
            PRIMARY KEY (location_id, label_name),
            FOREIGN KEY (label_entity_type, label_name)
                REFERENCES capacity.label_catalog(entity_type, name)
        )
    """)
    op.execute("""
        CREATE TABLE capacity.room_labels (
            room_id           UUID NOT NULL
                REFERENCES capacity.rooms(id) ON DELETE CASCADE,
            label_name        TEXT NOT NULL,
            label_entity_type TEXT NOT NULL DEFAULT 'ROOM',
            PRIMARY KEY (room_id, label_name),
            FOREIGN KEY (label_entity_type, label_name)
                REFERENCES capacity.label_catalog(entity_type, name)
        )
    """)
    op.execute("""
        CREATE TABLE capacity.bed_labels (
            bed_id            UUID NOT NULL
                REFERENCES capacity.beds(id) ON DELETE CASCADE,
            label_name        TEXT NOT NULL,
            label_entity_type TEXT NOT NULL DEFAULT 'BED',
            PRIMARY KEY (bed_id, label_name),
            FOREIGN KEY (label_entity_type, label_name)
                REFERENCES capacity.label_catalog(entity_type, name)
        )
    """)
    op.execute("""
        CREATE TABLE persons.occupant_labels (
            occupant_id       UUID NOT NULL
                REFERENCES persons.occupants(id) ON DELETE CASCADE,
            label_name        TEXT NOT NULL,
            label_entity_type TEXT NOT NULL DEFAULT 'OCCUPANCY',
            PRIMARY KEY (occupant_id, label_name),
            FOREIGN KEY (label_entity_type, label_name)
                REFERENCES capacity.label_catalog(entity_type, name)
        )
    """)

    # 3. INSERT alle Katalog-Einträge (eine Zeile pro entity_type)
    # is_system=TRUE: Männer, Frauen, Gemischt, Familie, Familienraum (alle ROOM)
    op.execute("""
        INSERT INTO capacity.label_catalog (name, entity_type, is_system, category, color, sort_order) VALUES
        -- ROOM-Labels
        ('Rollstuhlgerecht', 'ROOM', FALSE, 'Ausstattung', '#1565c0', 10),
        ('Erdgeschoss',      'ROOM', FALSE, 'Ausstattung', '#1565c0', 11),
        ('Barrierefreiheit', 'ROOM', FALSE, 'Ausstattung', '#1565c0', 12),
        ('Ruhig',            'ROOM', FALSE, 'Ausstattung', '#2e7d32', 13),
        ('Klimaanlage',      'ROOM', FALSE, 'Ausstattung', '#2e7d32', 14),
        ('Familienraum',     'ROOM', TRUE,  'Eignung',     '#6a1b9a', 20),
        ('Männer',           'ROOM', TRUE,  'Geschlecht',  '#1565c0', 30),
        ('Frauen',           'ROOM', TRUE,  'Geschlecht',  '#880e4f', 31),
        ('Gemischt',         'ROOM', TRUE,  'Geschlecht',  '#4a148c', 32),
        ('Familie',          'ROOM', TRUE,  'Geschlecht',  '#6a1b9a', 33),
        ('Mobilitätseinschränkung', 'ROOM', FALSE, 'Schutz', '#e65100', 40),
        -- BED-Labels
        ('Unteres Bett',     'BED',  FALSE, 'Position',    '#e65100', 10),
        ('Oberes Bett',      'BED',  FALSE, 'Position',    '#e65100', 11),
        ('Bodeneben',        'BED',  FALSE, 'Position',    '#e65100', 12),
        ('Breites Bett',     'BED',  FALSE, 'Typ',         '#00695c', 20),
        ('Kinderbett',       'BED',  FALSE, 'Typ',         '#6a1b9a', 21),
        ('Barrierefreiheit', 'BED',  FALSE, 'Ausstattung', '#1565c0', 30),
        ('Mobilitätseinschränkung', 'BED', FALSE, 'Schutz', '#e65100', 40),
        -- OCCUPANCY-Labels
        ('Kind',                       'OCCUPANCY', FALSE, 'Schutz',  '#6a1b9a', 10),
        ('Unbegleitete Minderjährige', 'OCCUPANCY', FALSE, 'Schutz',  '#b71c1c', 11),
        ('Pflegebedarf',               'OCCUPANCY', FALSE, 'Schutz',  '#b71c1c', 12),
        ('Mobilitätseinschränkung',    'OCCUPANCY', FALSE, 'Schutz',  '#e65100', 13),
        ('Arabisch',                   'OCCUPANCY', FALSE, 'Sprache', '#00796b', 20),
        ('Farsi/Dari',                 'OCCUPANCY', FALSE, 'Sprache', '#00796b', 21),
        ('Türkisch',                   'OCCUPANCY', FALSE, 'Sprache', '#00796b', 22),
        ('Englisch',                   'OCCUPANCY', FALSE, 'Sprache', '#00796b', 23),
        ('Französisch',                'OCCUPANCY', FALSE, 'Sprache', '#00796b', 24),
        ('Russisch',                   'OCCUPANCY', FALSE, 'Sprache', '#00796b', 25),
        ('Halal',                      'OCCUPANCY', FALSE, 'Hinweis', '#558b2f', 30),
        ('Vegetarisch',                'OCCUPANCY', FALSE, 'Hinweis', '#558b2f', 31),
        ('Familienmitglied',           'OCCUPANCY', FALSE, 'Gruppe',  '#6a1b9a', 40),
        ('Alleinstehend',              'OCCUPANCY', FALSE, 'Gruppe',  '#455a64', 41)
    """)

    # 4. Datenmigration: TEXT[] → junction tables (Labels die nicht im Katalog sind, werden übersprungen)
    op.execute("""
        INSERT INTO capacity.location_labels (location_id, label_name, label_entity_type)
        SELECT l.id, lbl.label_name, 'LOCATION'
        FROM capacity.locations l
        CROSS JOIN LATERAL unnest(l.labels) AS lbl(label_name)
        WHERE l.labels IS NOT NULL AND array_length(l.labels, 1) > 0
          AND EXISTS (
              SELECT 1 FROM capacity.label_catalog lc
              WHERE lc.entity_type = 'LOCATION' AND lc.name = lbl.label_name
          )
        ON CONFLICT (location_id, label_name) DO NOTHING
    """)
    # room_labels
    op.execute("""
        INSERT INTO capacity.room_labels (room_id, label_name, label_entity_type)
        SELECT r.id, lbl.label_name, 'ROOM'
        FROM capacity.rooms r
        CROSS JOIN LATERAL unnest(r.labels) AS lbl(label_name)
        WHERE r.labels IS NOT NULL AND array_length(r.labels, 1) > 0
          AND EXISTS (
              SELECT 1 FROM capacity.label_catalog lc
              WHERE lc.entity_type = 'ROOM' AND lc.name = lbl.label_name
          )
        ON CONFLICT (room_id, label_name) DO NOTHING
    """)
    # bed_labels
    op.execute("""
        INSERT INTO capacity.bed_labels (bed_id, label_name, label_entity_type)
        SELECT b.id, lbl.label_name, 'BED'
        FROM capacity.beds b
        CROSS JOIN LATERAL unnest(b.labels) AS lbl(label_name)
        WHERE b.labels IS NOT NULL AND array_length(b.labels, 1) > 0
          AND EXISTS (
              SELECT 1 FROM capacity.label_catalog lc
              WHERE lc.entity_type = 'BED' AND lc.name = lbl.label_name
          )
        ON CONFLICT (bed_id, label_name) DO NOTHING
    """)
    # occupant_labels
    op.execute("""
        INSERT INTO persons.occupant_labels (occupant_id, label_name, label_entity_type)
        SELECT o.id, lbl.label_name, 'OCCUPANCY'
        FROM persons.occupants o
        CROSS JOIN LATERAL unnest(o.labels) AS lbl(label_name)
        WHERE o.labels IS NOT NULL AND array_length(o.labels, 1) > 0
          AND EXISTS (
              SELECT 1 FROM capacity.label_catalog lc
              WHERE lc.entity_type = 'OCCUPANCY' AND lc.name = lbl.label_name
          )
        ON CONFLICT (occupant_id, label_name) DO NOTHING
    """)

    # 5. TEXT[] Spalten entfernen
    op.execute("ALTER TABLE capacity.locations DROP COLUMN labels")
    op.execute("ALTER TABLE capacity.rooms DROP COLUMN labels")
    op.execute("ALTER TABLE capacity.beds DROP COLUMN labels")
    op.execute("ALTER TABLE persons.occupants DROP COLUMN labels")


def downgrade() -> None:
    # Spalten zurückfügen
    op.execute("ALTER TABLE capacity.locations ADD COLUMN labels TEXT[] NOT NULL DEFAULT '{}'")
    op.execute("ALTER TABLE capacity.rooms ADD COLUMN labels TEXT[] NOT NULL DEFAULT '{}'")
    op.execute("ALTER TABLE capacity.beds ADD COLUMN labels TEXT[] NOT NULL DEFAULT '{}'")
    op.execute("ALTER TABLE persons.occupants ADD COLUMN labels TEXT[] NOT NULL DEFAULT '{}'")

    # Daten zurück migrieren
    op.execute("""
        UPDATE capacity.locations l
        SET labels = (
            SELECT COALESCE(array_agg(ll.label_name), '{}')
            FROM capacity.location_labels ll
            WHERE ll.location_id = l.id
        )
    """)
    op.execute("""
        UPDATE capacity.rooms r
        SET labels = (
            SELECT COALESCE(array_agg(rl.label_name), '{}')
            FROM capacity.room_labels rl
            WHERE rl.room_id = r.id
        )
    """)
    op.execute("""
        UPDATE capacity.beds b
        SET labels = (
            SELECT COALESCE(array_agg(bl.label_name), '{}')
            FROM capacity.bed_labels bl
            WHERE bl.bed_id = b.id
        )
    """)
    op.execute("""
        UPDATE persons.occupants o
        SET labels = (
            SELECT COALESCE(array_agg(ol.label_name), '{}')
            FROM persons.occupant_labels ol
            WHERE ol.occupant_id = o.id
        )
    """)

    # Junction tables + Katalog-Tabelle entfernen
    op.execute("DROP TABLE IF EXISTS persons.occupant_labels")
    op.execute("DROP TABLE IF EXISTS capacity.bed_labels")
    op.execute("DROP TABLE IF EXISTS capacity.room_labels")
    op.execute("DROP TABLE IF EXISTS capacity.location_labels")
    op.execute("DROP TABLE IF EXISTS capacity.label_catalog")
