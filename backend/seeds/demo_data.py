"""
Demo-Seed für BorderCapControl.
Setzt 5 Demo-Einrichtungen mit realistischen Räumen, Betten und Belegungen.
Enthält auch Reservierungsanfragen, Tasks und Audit-Events.

ACHTUNG: Löscht und erneuert alle Demo-Daten (Belegungen, Aufgaben, Reservierungen).
         Standorte, Räume und Betten werden per UPSERT idempotent angelegt.
"""
import os
import uuid
from datetime import date, timedelta

import psycopg2

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://bordercap_app:bordercap_app_dev@localhost:5432/bordercap?gssencmode=disable",
)

today = date.today()
EU_GESAMTQUOTE = 800

# ─── Demo-Standorte ──────────────────────────────────────────────────────────
# Repräsentiert 5 typische BAMF-Erstaufnahmeeinrichtungen an deutschen Grenzen
LOCATIONS = [
    {
        "id": "a1b2c3d4-0001-0001-0001-000000000001",
        "name": "Flughafen Frankfurt",
        "adresse": "Flughafenstr. 1, 60547 Frankfurt am Main",
        "kontingent": 40,
        "notbett_kapazitaet": 8,
        "lat": 50.0264,
        "lon": 8.5431,
        "labels": ["Erstaufnahme", "Familiengeeignet", "Barrierefrei"],
        "valid_from": None,
        "valid_until": None,
    },
    {
        "id": "a1b2c3d4-0002-0002-0002-000000000002",
        "name": "Flughafen München",
        "adresse": "Nordallee 25, 85356 Flughafen München",
        "kontingent": 30,
        "notbett_kapazitaet": 6,
        "lat": 48.3537,
        "lon": 11.7750,
        "labels": ["Erstaufnahme", "Klimaanlage"],
        "valid_from": None,
        "valid_until": None,
    },
    {
        "id": "a1b2c3d4-0003-0003-0003-000000000003",
        "name": "Grenzübergang Passau",
        "adresse": "Innstraße 45, 94032 Passau",
        "kontingent": 20,
        "notbett_kapazitaet": 4,
        "lat": 48.5667,
        "lon": 13.4319,
        "labels": ["Grenzverfahren", "Barrierefrei", "Dolmetscher vor Ort"],
        "valid_from": None,
        "valid_until": None,
    },
    {
        "id": "a1b2c3d4-0004-0004-0004-000000000004",
        "name": "Flughafen Hamburg",
        "adresse": "Flughafenstr. 1-3, 22335 Hamburg",
        "kontingent": 25,
        "notbett_kapazitaet": 5,
        "lat": 53.6304,
        "lon": 9.9882,
        "labels": ["Erstaufnahme", "Familiengeeignet"],
        "valid_from": None,
        "valid_until": None,
    },
    {
        "id": "a1b2c3d4-0005-0005-0005-000000000005",
        "name": "Grenzübergang Kiefersfelden",
        "adresse": "Rosenheimer Str. 2, 83088 Kiefersfelden",
        "kontingent": 15,
        "notbett_kapazitaet": 3,
        "lat": 47.6167,
        "lon": 12.1833,
        "labels": ["Grenzverfahren", "Erstaufnahme"],
        "valid_from": str(today - timedelta(days=90)),
        "valid_until": str(today + timedelta(days=180)),
    },
]

# ─── Räume + Betten pro Standort ─────────────────────────────────────────────
# Format: name, designation (M/W/D), beds, labels, bett_typ (KONTINGENT|NOTBETT|WARTEPLATZ),
#         room_type (STANDARD|WARTEBEREICH), valid_from, valid_until
ROOMS_CONFIG = {
    # Frankfurt: 10+10+8+6+6=40 Kontingent + 8 Notbetten + Wartebereich
    "a1b2c3d4-0001-0001-0001-000000000001": [
        {"name": "Raum A",       "designation": "M", "beds": 10,
         "labels": ["Erdgeschoss", "Rollstuhlgerecht", "Männer"]},
        {"name": "Raum B",        "designation": "W", "beds": 10,
         "labels": ["Erdgeschoss", "Frauen", "Sicherheitszugang"]},
        {"name": "Raum C",    "designation": "M", "beds": 8,
         "labels": ["Obergeschoss", "Männer", "Ruhig"]},
        {"name": "Raum D",       "designation": "D", "beds": 6,
         "labels": ["Familienraum", "Familie", "Spielecke"]},
        {"name": "Raum E",    "designation": "W", "beds": 6,
         "labels": ["Obergeschoss", "Frauen"]},
        {"name": "Notbettenraum",          "designation": "D", "beds": 8,
         "labels": ["Notbetten"], "bett_typ": "NOTBETT"},
        {"name": "Wartebereich", "designation": "D", "beds": 5,
         "labels": ["Wartebereich"], "room_type": "WARTEBEREICH", "bett_typ": "WARTEPLATZ"},
    ],
    # München: 8+8+8+6=30 Kontingent + 6 Notbetten + Wartebereich
    "a1b2c3d4-0002-0002-0002-000000000002": [
        {"name": "Raum A",       "designation": "M", "beds": 8,
         "labels": ["Klimaanlage", "Männer"]},
        {"name": "Raum B",        "designation": "W", "beds": 8,
         "labels": ["Klimaanlage", "Frauen", "Sicherheitszugang"]},
        {"name": "Raum C 2",     "designation": "M", "beds": 8,
         "labels": ["Klimaanlage", "Ruhig", "Männer"]},
        {"name": "Raum D 2",     "designation": "W", "beds": 6,
         "labels": ["Frauen"]},
        {"name": "Notbettenraum",          "designation": "D", "beds": 6,
         "labels": ["Notbetten"], "bett_typ": "NOTBETT"},
        {"name": "Wartebereich", "designation": "D", "beds": 5,
         "labels": ["Wartebereich"], "room_type": "WARTEBEREICH", "bett_typ": "WARTEPLATZ"},
    ],
    # Passau: 5+5+5+5=20 Kontingent + 4 Notbetten + Wartebereich
    "a1b2c3d4-0003-0003-0003-000000000003": [
        {"name": "Raum A",       "designation": "M", "beds": 5,
         "labels": ["Erdgeschoss", "Barrierefreiheit", "Männer"]},
        {"name": "Raum B",        "designation": "W", "beds": 5,
         "labels": ["Erdgeschoss", "Frauen", "Sicherheitszugang"]},
        {"name": "Raum C 2",     "designation": "M", "beds": 5,
         "labels": ["Männer", "Ruhig"]},
        {"name": "Raum D – Familie",       "designation": "D", "beds": 5,
         "labels": ["Familienraum", "Familie"]},
        {"name": "Notbettenraum",          "designation": "D", "beds": 4,
         "labels": ["Notbetten"], "bett_typ": "NOTBETT"},
        {"name": "Wartebereich", "designation": "D", "beds": 5,
         "labels": ["Wartebereich"], "room_type": "WARTEBEREICH", "bett_typ": "WARTEPLATZ"},
    ],
    # Hamburg: 6+6+6+7=25 Kontingent + 5 Notbetten + Wartebereich
    "a1b2c3d4-0004-0004-0004-000000000004": [
        {"name": "Raum A",       "designation": "M", "beds": 6,
         "labels": ["Männer", "Meerblick"]},
        {"name": "Raum B",        "designation": "W", "beds": 6,
         "labels": ["Frauen", "Ruhig", "Sicherheitszugang"]},
        {"name": "Raum C – Familie/Mix",  "designation": "D", "beds": 6,
         "labels": ["Familienraum", "Familie"]},
        {"name": "Raum D 2",     "designation": "M", "beds": 7,
         "labels": ["Männer"]},
        {"name": "Notbettenraum",          "designation": "D", "beds": 5,
         "labels": ["Notbetten"], "bett_typ": "NOTBETT"},
        {"name": "Wartebereich", "designation": "D", "beds": 5,
         "labels": ["Wartebereich"], "room_type": "WARTEBEREICH", "bett_typ": "WARTEPLATZ"},
    ],
    # Kiefersfelden: 4+4+4+3=15 Kontingent + 3 Notbetten + Wartebereich  (geplant ab -90d)
    "a1b2c3d4-0005-0005-0005-000000000005": [
        {"name": "Raum A",       "designation": "M", "beds": 4,
         "labels": ["Männer", "Alpenblick"]},
        {"name": "Raum B",        "designation": "W", "beds": 4,
         "labels": ["Frauen", "Alpenblick"]},
        {"name": "Raum C – Familie",       "designation": "D", "beds": 4,
         "labels": ["Familienraum", "Familie"]},
        {"name": "Raum D – Gemischt",     "designation": "D", "beds": 3,
         "labels": ["Gemischt"]},
        {"name": "Notbettenraum",          "designation": "D", "beds": 3,
         "labels": ["Notbetten"], "bett_typ": "NOTBETT"},
        {"name": "Wartebereich", "designation": "D", "beds": 5,
         "labels": ["Wartebereich"], "room_type": "WARTEBEREICH", "bett_typ": "WARTEPLATZ"},
    ],
}

# ─── Wartebereich-Belegungen pro Standort ────────────────────────────────────
# Personen die noch auf Bett-Zuweisung warten (kein festes Kontingent-Bett)
ANKUNFT_OCCUPANCY = {
    "a1b2c3d4-0001-0001-0001-000000000001": [
        {"geschlecht": "M", "country": "SYR"},
        {"geschlecht": "W", "country": "AFG"},
        {"geschlecht": "M", "country": "IRQ"},
    ],
    "a1b2c3d4-0002-0002-0002-000000000002": [
        {"geschlecht": "M", "country": "ERI"},
        {"geschlecht": "W", "country": "SOM"},
        {"geschlecht": "D", "country": "ETH"},
    ],
    "a1b2c3d4-0003-0003-0003-000000000003": [
        {"geschlecht": "M", "country": "PAK"},
        {"geschlecht": "W", "country": "IRN"},
    ],
    "a1b2c3d4-0004-0004-0004-000000000004": [
        {"geschlecht": "M", "country": "NGA"},
        {"geschlecht": "W", "country": "TUR"},
        {"geschlecht": "M", "country": "SYR"},
    ],
    "a1b2c3d4-0005-0005-0005-000000000005": [
        {"geschlecht": "M", "country": "AFG"},
        {"geschlecht": "W", "country": "SYR"},
    ],
}

# ─── Belegungsquoten pro Raum ─────────────────────────────────────────────────
# Ziel-Belegungsgrade:
#   Frankfurt:      30/40 = 75 % (Gelb)
#   München:        29/30 = 97 % (Rot)
#   Passau:          6/20 = 30 % (Grün)
#   Hamburg:        10/25 = 40 % (Grün)
#   Kiefersfelden:   8/15 = 53 % (Gelb)
OCCUPANCY_CONFIG = {
    "a1b2c3d4-0001-0001-0001-000000000001": {
        "Raum A": {"count": 8, "geschlecht": "M"},
        "Raum B": {"count": 9, "geschlecht": "W"},
        "Raum C": {"count": 7, "geschlecht": "M"},
        "Raum D": {"count": 4, "geschlecht": "D"},
        "Raum E": {"count": 2, "geschlecht": "W"},
    },
    "a1b2c3d4-0002-0002-0002-000000000002": {
        "Raum A":  {"count": 8, "geschlecht": "M"},
        "Raum B":  {"count": 8, "geschlecht": "W"},
        "Raum C 2": {"count": 8, "geschlecht": "M"},
        "Raum D 2": {"count": 5, "geschlecht": "W"},
    },
    "a1b2c3d4-0003-0003-0003-000000000003": {
        "Raum A": {"count": 3, "geschlecht": "M"},
        "Raum B": {"count": 2, "geschlecht": "W"},
        "Raum D – Familie": {"count": 1, "geschlecht": "D"},
    },
    "a1b2c3d4-0004-0004-0004-000000000004": {
        "Raum A":    {"count": 3, "geschlecht": "M"},
        "Raum B":    {"count": 4, "geschlecht": "W"},
        "Raum C – Familie/Mix": {"count": 2, "geschlecht": "D"},
        "Raum D 2":  {"count": 1, "geschlecht": "M"},
    },
    "a1b2c3d4-0005-0005-0005-000000000005": {
        "Raum A":  {"count": 3, "geschlecht": "M"},
        "Raum B":  {"count": 3, "geschlecht": "W"},
        "Raum C – Familie": {"count": 2, "geschlecht": "D"},
    },
}

# ─── Herkunftsländer für realistische Demo-AZR-IDs ──────────────────────────
COUNTRIES = ["SYR", "AFG", "IRQ", "ERI", "SOM", "ETH", "NGA", "PAK", "IRN", "TUR"]

DEMO_LOC_IDS = [loc["id"] for loc in LOCATIONS]

# Saisonale Auslastungskurve für historische Daten:
# Index 0 = jüngster Monat (vor ~46T), Index 11 = ältester Monat (vor ~365T)
# Herbst/Winter hoch, Sommer niedrig
SEASONAL_RATE = [0.90, 0.85, 0.80, 0.75, 0.68, 0.58, 0.55, 0.62, 0.70, 0.76, 0.82, 0.87]

# Kontingent-Verlauf pro Einrichtung für Treppenfunktion im Chart
# Format: (location_id, kontingent_value, tage_vor_heute)
KONTINGENT_HISTORY_DATA = [
    ("a1b2c3d4-0001-0001-0001-000000000001", 30, 365),  # Frankfurt: 30 → 35 → 40
    ("a1b2c3d4-0001-0001-0001-000000000001", 35, 240),
    ("a1b2c3d4-0001-0001-0001-000000000001", 40,  90),
    ("a1b2c3d4-0002-0002-0002-000000000002", 25, 365),  # München: 25 → 30
    ("a1b2c3d4-0002-0002-0002-000000000002", 30, 180),
    ("a1b2c3d4-0003-0003-0003-000000000003", 15, 365),  # Passau: 15 → 20
    ("a1b2c3d4-0003-0003-0003-000000000003", 20, 120),
    ("a1b2c3d4-0004-0004-0004-000000000004", 20, 365),  # Hamburg: 20 → 25
    ("a1b2c3d4-0004-0004-0004-000000000004", 25, 200),
    ("a1b2c3d4-0005-0005-0005-000000000005", 10, 365),  # Kiefersfelden: 10 → 15
    ("a1b2c3d4-0005-0005-0005-000000000005", 15, 150),
]


def _room_id(location_id: str, room_name: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{location_id}::{room_name}"))


def _bed_id(room_id: str, bett_nr: int) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{room_id}::{bett_nr}"))


def _azr_id(location_id: str, geschlecht: str, room_name: str, idx: int) -> str:
    loc_codes = {
        "a1b2c3d4-0001-0001-0001-000000000001": "FFM",
        "a1b2c3d4-0002-0002-0002-000000000002": "MUC",
        "a1b2c3d4-0003-0003-0003-000000000003": "PAS",
        "a1b2c3d4-0004-0004-0004-000000000004": "HAM",
        "a1b2c3d4-0005-0005-0005-000000000005": "KIF",
    }
    g = geschlecht if geschlecht in ("M", "W") else "X"
    room_short = "".join(c for c in room_name if c.isupper() and c.isalpha())[:3]
    code = loc_codes.get(location_id, "UNK")
    return f"AZR-2024-{code}-{room_short}{g}{idx:02d}"


def _alias_id(geschlecht: str, location_id: str, idx: int) -> str:
    loc_num = location_id[-4:]
    return f"AL-{loc_num}-{idx:04d}"


def seed_historical_occupants(cur) -> int:
    """12 Monats-Kohorten vergangener Belegungen für jeden Standort.

    Jede Kohorte endet ≥ 46 Tage vor heute, kein Overlap mit aktuellen Belegungen.
    Saisonale Auslastungskurve erzeugt einen interessanten Chart-Verlauf.
    """
    n_hist = 0
    genders = ["M", "W", "M", "W", "D"]

    for loc in LOCATIONS:
        loc_id = loc["id"]
        kontingent = loc["kontingent"]

        # Alle KONTINGENT-Bett-IDs sammeln
        kontingent_beds: list[str] = []
        for room_def in ROOMS_CONFIG[loc_id]:
            if room_def.get("room_type") == "WARTEBEREICH":
                continue
            if room_def.get("bett_typ", "KONTINGENT") != "KONTINGENT":
                continue
            rid = _room_id(loc_id, room_def["name"])
            for bett_nr in range(1, room_def["beds"] + 1):
                kontingent_beds.append(_bed_id(rid, bett_nr))

        for m in range(12):
            # Periode: 30 Tage lang, endet heute-(46+m*30)
            period_end   = today - timedelta(days=46 + m * 30)
            period_start = period_end - timedelta(days=29)
            n_belegt     = min(int(kontingent * SEASONAL_RATE[m]), len(kontingent_beds))

            for i in range(n_belegt):
                bed_id = kontingent_beds[i % len(kontingent_beds)]
                occ_id = str(uuid.uuid5(
                    uuid.NAMESPACE_URL, f"hist-occ::{loc_id}::{m}::{i}"
                ))
                g   = genders[i % len(genders)]
                azr = f"AZR-HIST-{loc_id[-4:]}-M{m:02d}-{i:02d}"

                cur.execute("""
                    INSERT INTO persons.occupants
                        (id, bed_id, azr_id, alias_id, geschlecht,
                         belegung_start, belegung_ende, labels, created_at)
                    VALUES (%s, %s, %s, NULL, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO NOTHING
                """, (occ_id, bed_id, azr, g, period_start, period_end, [], period_start))
                n_hist += 1

    return n_hist


def seed_kontingent_history(cur) -> int:
    """Historische Kontingent-Snapshots für Treppenfunktionslinie im Chart."""
    for loc_id, kval, days_ago in KONTINGENT_HISTORY_DATA:
        cur.execute("""
            INSERT INTO capacity.kontingent_history
                (id, location_id, kontingent_value, valid_from, actor_id)
            VALUES (gen_random_uuid(), %s, %s, %s, 'system-seed')
        """, (loc_id, kval, today - timedelta(days=days_ago)))
    return len(KONTINGENT_HISTORY_DATA)


def main() -> None:
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False
    cur = conn.cursor()

    start_long = today - timedelta(days=45)
    start_mid  = today - timedelta(days=20)
    start_new  = today - timedelta(days=5)

    try:
        print("Lösche Demo-Belegungen, Tasks, Reservierungen und Kontingent-History...")
        loc_ids_sql = [str(x) for x in DEMO_LOC_IDS]

        cur.execute("""
            DELETE FROM persons.occupants o
            USING capacity.beds b
            JOIN capacity.rooms r ON r.id = b.room_id
            WHERE o.bed_id = b.id AND r.location_id = ANY(%s::uuid[])
        """, (loc_ids_sql,))
        cur.execute(
            "DELETE FROM capacity.kontingent_history WHERE location_id = ANY(%s::uuid[])",
            (loc_ids_sql,)
        )

        cur.execute(
            "DELETE FROM tasks.inbox WHERE location_id = ANY(%s::uuid[])",
            (loc_ids_sql,)
        )
        cur.execute(
            """DELETE FROM reservations.requests
               WHERE requester_location_id = ANY(%s::uuid[])
                  OR target_location_id    = ANY(%s::uuid[])""",
            (loc_ids_sql, loc_ids_sql)
        )
        cur.execute("""
            DELETE FROM capacity.beds b
            USING capacity.rooms r
            WHERE b.room_id = r.id AND r.location_id = ANY(%s::uuid[])
        """, (loc_ids_sql,))
        cur.execute(
            "DELETE FROM capacity.rooms WHERE location_id = ANY(%s::uuid[])",
            (loc_ids_sql,)
        )

        print("Lege Standorte, Räume, Betten und Belegungen an...")
        n_rooms = n_beds = n_occ = 0
        occ_global_idx = 1  # fortlaufender Index für eindeutige AZR-IDs

        for loc in LOCATIONS:
            cur.execute("""
                INSERT INTO capacity.locations
                    (id, name, adresse, kontingent, notbett_kapazitaet,
                     labels, lat, lon, valid_from, valid_until, is_active,
                     created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE, NOW(), NOW())
                ON CONFLICT (id) DO UPDATE
                  SET kontingent         = EXCLUDED.kontingent,
                      notbett_kapazitaet = EXCLUDED.notbett_kapazitaet,
                      adresse            = EXCLUDED.adresse,
                      labels             = EXCLUDED.labels,
                      lat                = EXCLUDED.lat,
                      lon                = EXCLUDED.lon,
                      valid_from         = EXCLUDED.valid_from,
                      valid_until        = EXCLUDED.valid_until,
                      updated_at         = NOW()
            """, (
                loc["id"], loc["name"], loc["adresse"],
                loc["kontingent"], loc["notbett_kapazitaet"],
                loc.get("labels", []), loc.get("lat"), loc.get("lon"),
                loc.get("valid_from"), loc.get("valid_until"),
            ))

            rooms_cfg = ROOMS_CONFIG[loc["id"]]
            occ_cfg   = OCCUPANCY_CONFIG.get(loc["id"], {})

            for room_def in rooms_cfg:
                room_id = _room_id(loc["id"], room_def["name"])
                room_type = room_def.get("room_type", "STANDARD")
                cur.execute("""
                    INSERT INTO capacity.rooms
                        (id, location_id, name, geschlechts_designation,
                         labels, room_type, is_active, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, TRUE, NOW(), NOW())
                """, (room_id, loc["id"], room_def["name"],
                      room_def["designation"], room_def.get("labels", []), room_type))
                n_rooms += 1

                bett_typ = room_def.get("bett_typ", "KONTINGENT")
                for bett_nr in range(1, room_def["beds"] + 1):
                    bed_id = _bed_id(room_id, bett_nr)
                    if bett_typ == "NOTBETT":
                        bed_labels: list[str] = ["Notbett"]
                    elif bett_typ == "WARTEPLATZ":
                        bed_labels = ["Wartebereich"]
                    elif bett_nr % 3 == 0:
                        bed_labels = ["Einzelbett"]
                    elif bett_nr % 2 == 1:
                        bed_labels = ["Unteres Bett"]
                    else:
                        bed_labels = ["Oberes Bett"]

                    cur.execute("""
                        INSERT INTO capacity.beds
                            (id, room_id, bett_nummer, bett_typ,
                             labels, is_active, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, TRUE, NOW(), NOW())
                    """, (bed_id, room_id, str(bett_nr), bett_typ, bed_labels))
                    n_beds += 1

                # Warteplätze bekommen keine regulären Belegungen hier
                if room_type == "WARTEBEREICH":
                    continue

                occ_def = occ_cfg.get(room_def["name"])
                if not occ_def:
                    continue

                for i in range(1, occ_def["count"] + 1):
                    bed_id_occ = _bed_id(room_id, i)
                    geschlecht = occ_def["geschlecht"]
                    actual_g   = geschlecht if geschlecht != "D" else ("M" if i % 2 == 1 else "W")
                    azr        = _azr_id(loc["id"], actual_g, room_def["name"], occ_global_idx)
                    alias      = _alias_id(actual_g, loc["id"], occ_global_idx)
                    country    = COUNTRIES[occ_global_idx % len(COUNTRIES)]
                    occ_id     = str(uuid.uuid5(uuid.NAMESPACE_URL, f"occ2::{bed_id_occ}::{occ_global_idx}"))

                    # Varied stay lengths for more realistic data
                    if i <= 2:
                        start, ende = start_long, today + timedelta(days=45)
                    elif i <= 4:
                        start, ende = start_mid, today + timedelta(days=70)
                    else:
                        start, ende = start_new, today + timedelta(days=90)

                    occ_labels = []
                    if country in ("SYR", "AFG"):
                        occ_labels.append("Arabisch")
                    elif country in ("IRN", "PAK"):
                        occ_labels.append("Farsi/Dari")
                    if actual_g == "W" and i % 3 == 0:
                        occ_labels.append("Alleinreisende Frau")

                    cur.execute("""
                        INSERT INTO persons.occupants
                            (id, bed_id, azr_id, alias_id, geschlecht,
                             belegung_start, belegung_ende, labels, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                    """, (occ_id, bed_id_occ, azr, alias, actual_g,
                          start, ende, occ_labels))
                    n_occ += 1
                    occ_global_idx += 1

            # Wartebereich-Belegungen (Personen warten auf Bett-Zuweisung)
            ankunft_room_id = _room_id(loc["id"], "Wartebereich")
            ankunft_persons = ANKUNFT_OCCUPANCY.get(loc["id"], [])
            loc_codes = {
                "a1b2c3d4-0001-0001-0001-000000000001": "FFM",
                "a1b2c3d4-0002-0002-0002-000000000002": "MUC",
                "a1b2c3d4-0003-0003-0003-000000000003": "PAS",
                "a1b2c3d4-0004-0004-0004-000000000004": "HAM",
                "a1b2c3d4-0005-0005-0005-000000000005": "KIF",
            }
            code = loc_codes.get(loc["id"], "UNK")
            for i, ap in enumerate(ankunft_persons, start=1):
                bed_id_ankunft = _bed_id(ankunft_room_id, i)
                g = ap["geschlecht"] if ap["geschlecht"] in ("M", "W") else "X"
                azr = f"AZR-2024-{code}-ANK{g}{i:02d}"
                alias = f"AL-ANK-{code}-{i:02d}"
                occ_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"ankunft-occ::{bed_id_ankunft}"))
                occ_labels = []
                if ap["country"] in ("SYR", "AFG"):
                    occ_labels.append("Arabisch")
                elif ap["country"] in ("IRN", "PAK"):
                    occ_labels.append("Farsi/Dari")
                cur.execute("""
                    INSERT INTO persons.occupants
                        (id, bed_id, azr_id, alias_id, geschlecht,
                         belegung_start, belegung_ende, labels, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                """, (occ_id, bed_id_ankunft, azr, alias, ap["geschlecht"],
                      today, today + timedelta(days=30), occ_labels))
                n_occ += 1

        # Historische Belegungen (12 Monate zurück)
        print("Seed historische Belegungsdaten (12 Monate)...")
        n_hist = seed_historical_occupants(cur)

        # Kontingent-History-Snapshots
        print("Seed Kontingent-History...")
        n_kh = seed_kontingent_history(cur)

        # EU-Gesamtquote
        cur.execute("""
            INSERT INTO capacity.system_settings (id, eu_gesamtquote, updated_at)
            VALUES (1, %s, NOW())
            ON CONFLICT (id) DO UPDATE
              SET eu_gesamtquote = EXCLUDED.eu_gesamtquote, updated_at = NOW()
        """, (EU_GESAMTQUOTE,))

        # ─── Reservierungsanfragen ────────────────────────────────────────────
        loc_ffm = "a1b2c3d4-0001-0001-0001-000000000001"
        loc_muc = "a1b2c3d4-0002-0002-0002-000000000002"
        loc_pas = "a1b2c3d4-0003-0003-0003-000000000003"
        loc_ham = "a1b2c3d4-0004-0004-0004-000000000004"
        loc_kif = "a1b2c3d4-0005-0005-0005-000000000005"

        def _res_id(key: str) -> str:
            return str(uuid.uuid5(uuid.NAMESPACE_URL, f"demo-res-v2::{key}"))

        # CONFIRMED-Reservierung: Person sitzt in Frankfurt Raum A Bett 9 (frei, da nur 8/10 belegt)
        # und soll nach Passau Raum A Bett 4 verlegt werden (frei, da nur 3/5 belegt).
        ffm_room_a_id = _room_id(loc_ffm, "Raum A")
        pas_room_a_id = _room_id(loc_pas, "Raum A")
        confirmed_source_bed = _bed_id(ffm_room_a_id, 9)   # Frankfurt Raum A Bett 9
        confirmed_target_bed = _bed_id(pas_room_a_id, 4)   # Passau Raum A Bett 4

        # Occupant für die CONFIRMED-Person am Quellbett anlegen (Frankfurt)
        conf_occ_id = str(uuid.uuid5(uuid.NAMESPACE_URL, "occ2::confirmed-transfer-ffm-res08"))
        cur.execute("""
            INSERT INTO persons.occupants
                (id, bed_id, azr_id, alias_id, geschlecht,
                 belegung_start, belegung_ende, labels, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
        """, (conf_occ_id, confirmed_source_bed, "AZR-2024-FFM-M-RES08", "AL-RES08-FFM",
              "M", today - timedelta(days=30), today + timedelta(days=40), ["Farsi/Dari"]))
        n_occ += 1

        # Tupel-Format: (id, req_loc, tgt_loc, azr, g, gj, land, start, ende, status, confirmed_bed_id)
        reservations = [
            # München (97 %) → Frankfurt: 3 PENDING
            (_res_id("muc-ffm-1"), loc_muc, loc_ffm, "AZR-2024-MUC-M-RES01",
             "M", 1991, "SYR", today + timedelta(days=3), today + timedelta(days=65), "PENDING", None),
            (_res_id("muc-ffm-2"), loc_muc, loc_ffm, "AZR-2024-MUC-W-RES02",
             "W", 1994, "AFG", today + timedelta(days=3), today + timedelta(days=65), "PENDING", None),
            (_res_id("muc-ffm-3"), loc_muc, loc_ffm, "AZR-2024-MUC-M-RES03",
             "M", 1987, "IRQ", today + timedelta(days=4), today + timedelta(days=70), "PENDING", None),
            # Passau → Frankfurt: 1 PENDING
            (_res_id("pas-ffm-1"), loc_pas, loc_ffm, "AZR-2024-PAS-M-RES04",
             "M", 1982, "ERI", today + timedelta(days=6), today + timedelta(days=60), "PENDING", None),
            # Hamburg → München: 1 PENDING
            (_res_id("ham-muc-1"), loc_ham, loc_muc, "AZR-2024-HAM-W-RES05",
             "W", 1999, "SOM", today + timedelta(days=7), today + timedelta(days=50), "PENDING", None),
            # Kiefersfelden → Frankfurt: 2 PENDING
            (_res_id("kif-ffm-1"), loc_kif, loc_ffm, "AZR-2024-KIF-M-RES06",
             "M", 1978, "IRN", today + timedelta(days=5), today + timedelta(days=55), "PENDING", None),
            (_res_id("kif-ffm-2"), loc_kif, loc_ffm, "AZR-2024-KIF-W-RES07",
             "W", 2001, "TUR", today + timedelta(days=5), today + timedelta(days=55), "PENDING", None),
            # Frankfurt → Passau: 1 CONFIRMED — Person noch in FFM (Bett 9), Zielbett in Passau (Bett 4)
            (_res_id("ffm-pas-1"), loc_ffm, loc_pas, "AZR-2024-FFM-M-RES08",
             "M", 1990, "PAK", today - timedelta(days=3), today + timedelta(days=40),
             "CONFIRMED", confirmed_target_bed),
            # München → Hamburg: 1 REJECTED
            (_res_id("muc-ham-1"), loc_muc, loc_ham, "AZR-2024-MUC-W-RES09",
             "W", 1985, "ETH", today - timedelta(days=5), today + timedelta(days=30), "REJECTED", None),
            # Wartebereich-Personen: PENDING Verlegungsanfragen (lila Dot im Wartebereich)
            (_res_id("ffm-ank-1"), loc_ffm, loc_pas, "AZR-2024-FFM-ANKM01",
             "M", 1995, "SYR", today, today + timedelta(days=30), "PENDING", None),
            (_res_id("muc-ank-1"), loc_muc, loc_ham, "AZR-2024-MUC-ANKM01",
             "M", 1988, "ERI", today, today + timedelta(days=30), "PENDING", None),
        ]

        for (rid, req_loc, tgt_loc, azr, g, gj, land, start, ende, status, conf_bed) in reservations:
            cur.execute("""
                INSERT INTO reservations.requests
                    (id, requester_location_id, target_location_id, azr_id,
                     geschlecht, geburtsjahr, herkunftsland,
                     belegung_start, belegung_ende, status, confirmed_bed_id,
                     confirmed_at, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        CASE WHEN %s = 'CONFIRMED' THEN NOW() - INTERVAL '1 day' ELSE NULL END,
                        NOW() - INTERVAL '3 days', NOW())
            """, (rid, req_loc, tgt_loc, azr, g, gj, land, start, ende, status, conf_bed, status))

        n_reservations = len(reservations)

        # ─── Postkorb-Aufgaben ────────────────────────────────────────────────
        def _task_id(key: str) -> str:
            return str(uuid.uuid5(uuid.NAMESPACE_URL, f"demo-task-v2::{key}"))

        tasks: list[tuple] = [
            # Frankfurt empfängt 4 eingehende Anfragen
            (_task_id("ffm-inc-1"), loc_ffm, _res_id("muc-ffm-1"), "RESERVATION_RECEIVED", "HIGH",
             "Eingehende Anfrage: AZR-2024-MUC-M-RES01",
             f"München (97 % ausgelastet) bittet um Aufnahme von AZR-2024-MUC-M-RES01 "
             f"(männlich, Syrien, *1991). Zeitraum: {today+timedelta(3)} – {today+timedelta(65)}."),
            (_task_id("ffm-inc-2"), loc_ffm, _res_id("muc-ffm-2"), "RESERVATION_RECEIVED", "HIGH",
             "Eingehende Anfrage: AZR-2024-MUC-W-RES02",
             f"München bittet um Aufnahme von AZR-2024-MUC-W-RES02 "
             f"(weiblich, Afghanistan, *1994). Zeitraum: {today+timedelta(3)} – {today+timedelta(65)}."),
            (_task_id("ffm-inc-3"), loc_ffm, _res_id("muc-ffm-3"), "RESERVATION_RECEIVED", "HIGH",
             "Eingehende Anfrage: AZR-2024-MUC-M-RES03",
             f"München bittet um Aufnahme von AZR-2024-MUC-M-RES03 "
             f"(männlich, Irak, *1987). Zeitraum: {today+timedelta(4)} – {today+timedelta(70)}."),
            (_task_id("ffm-inc-4"), loc_ffm, _res_id("pas-ffm-1"), "RESERVATION_RECEIVED", "HIGH",
             "Eingehende Anfrage: AZR-2024-PAS-M-RES04",
             f"Passau bittet um Aufnahme von AZR-2024-PAS-M-RES04 "
             f"(männlich, Eritrea, *1982). Zeitraum: {today+timedelta(6)} – {today+timedelta(60)}."),
            (_task_id("ffm-inc-5"), loc_ffm, _res_id("kif-ffm-1"), "RESERVATION_RECEIVED", "MEDIUM",
             "Eingehende Anfrage: AZR-2024-KIF-M-RES06",
             f"Kiefersfelden bittet um Aufnahme von AZR-2024-KIF-M-RES06 "
             f"(männlich, Iran, *1978). Zeitraum: {today+timedelta(5)} – {today+timedelta(55)}."),
            (_task_id("ffm-inc-6"), loc_ffm, _res_id("kif-ffm-2"), "RESERVATION_RECEIVED", "MEDIUM",
             "Eingehende Anfrage: AZR-2024-KIF-W-RES07",
             f"Kiefersfelden bittet um Aufnahme von AZR-2024-KIF-W-RES07 "
             f"(weiblich, Türkei, *2001). Zeitraum: {today+timedelta(5)} – {today+timedelta(55)}."),
            # Frankfurt: 12-Wochen-Warnungen
            (_task_id("ffm-12w-1"), loc_ffm, None, "RESERVATION_CONFIRMED", "MEDIUM",
             "12-Wochen-Warnung: 5 Belegungen laufen bald ab",
             "AZR-2024-FFM-AAM01, -AIM02, -ABM03 (Raum A) und AZR-2024-FFM-BAW01, -BAW02 (Raum B) "
             "erreichen in < 12 Wochen ihr Belegungsende. Bitte prüfen und Übergabe planen."),
            # Frankfurt: Kapazitätsmeldung
            (_task_id("ffm-cap-1"), loc_ffm, None, "RESERVATION_CONFIRMED", "LOW",
             "Kapazität: Frankfurt bei 75 % (30/40 Plätze)",
             f"Noch 10 freie Kontingentplätze. "
             f"6 offene eingehende Verlegungsanfragen noch nicht bearbeitet."),
            # München: kritisch
            (_task_id("muc-cap-1"), loc_muc, None, "RESERVATION_CONFIRMED", "HIGH",
             "Kapazität kritisch: München bei 97 % (29/30 Plätze)",
             "Nur noch 1 freier Platz (Raum D 2). "
             "3 Anfragen an Frankfurt, 1 an Hamburg gesendet. Abwarten auf Bestätigung."),
            (_task_id("muc-inc-1"), loc_muc, _res_id("ham-muc-1"), "RESERVATION_RECEIVED", "MEDIUM",
             "Eingehende Anfrage: AZR-2024-HAM-W-RES05",
             f"Hamburg bittet um Aufnahme von AZR-2024-HAM-W-RES05 "
             f"(weiblich, Somalia, *1999). Zeitraum: {today+timedelta(7)} – {today+timedelta(50)}."),
            # Passau: ausgehende Anfrage bestätigt
            (_task_id("pas-out-1"), loc_pas, _res_id("ffm-pas-1"), "RESERVATION_CONFIRMED", "LOW",
             "Verlegungsanfrage bestätigt: AZR-2024-FFM-M-RES08 → Passau",
             f"Frankfurt hat die Übernahme von AZR-2024-FFM-M-RES08 (männlich, Pakistan, *1990) "
             f"zum {today-timedelta(3)} bestätigt. Bett bitte freigeben."),
            # Hamburg: abgelehnte ausgehende Anfrage
            (_task_id("ham-rej-1"), loc_muc, _res_id("muc-ham-1"), "RESERVATION_CONFIRMED", "LOW",
             "Verlegungsanfrage abgelehnt: AZR-2024-MUC-W-RES09",
             f"Hamburg hat die Anfrage für AZR-2024-MUC-W-RES09 (weiblich, Äthiopien, *1985) "
             f"abgelehnt. Bitte alternative Einrichtung suchen."),
            # Kiefersfelden: Kapazitätsmeldung
            (_task_id("kif-cap-1"), loc_kif, None, "RESERVATION_CONFIRMED", "MEDIUM",
             "Kapazität: Kiefersfelden bei 53 % (8/15 Plätze)",
             f"Einrichtung ist in Betrieb bis {today+timedelta(180)}. "
             f"2 offene Anfragen an Frankfurt. Gültigkeitszeitraum: bis {today+timedelta(180)}."),
        ]

        for (tid, loc_id, rel_res_id, task_type, priority, title, body_text) in tasks:
            cur.execute("""
                INSERT INTO tasks.inbox
                    (id, location_id, related_reservation_id, task_type,
                     priority, status, title, body, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, 'OPEN', %s, %s, NOW(), NOW())
            """, (tid, loc_id, rel_res_id, task_type, priority, title, body_text))

        conn.commit()

        n_pending   = sum(1 for r in reservations if r[9] == "PENDING")
        n_confirmed = sum(1 for r in reservations if r[9] == "CONFIRMED")
        n_rejected  = sum(1 for r in reservations if r[9] == "REJECTED")

        n_warte = sum(len(v) for v in ANKUNFT_OCCUPANCY.values())
        print(
            f"\n✓ Seed abgeschlossen:\n"
            f"  {len(LOCATIONS)} Standorte\n"
            f"  {n_rooms} Räume (inkl. je 1 Wartebereich pro Standort), {n_beds} Betten\n"
            f"  {n_occ} aktuelle Belegungen (inkl. {n_warte} Personen im Wartebereich)\n"
            f"  {n_hist} historische Belegungen (12 Monate, saisonal)\n"
            f"  {n_kh} Kontingent-History-Einträge\n"
            f"  {n_reservations} Verlegungsanfragen "
            f"({n_pending} PENDING · {n_confirmed} CONFIRMED · {n_rejected} REJECTED)\n"
            f"  {len(tasks)} Postkorb-Aufgaben\n"
            f"  EU-Gesamtquote = {EU_GESAMTQUOTE}\n"
            f"\nBelegungsgrade (Kontingent):\n"
            f"  Frankfurt:      30/40 = 75 %  (Gelb)\n"
            f"  München:        29/30 = 97 %  (Rot)\n"
            f"  Passau:          6/20 = 30 %  (Grün)\n"
            f"  Hamburg:        10/25 = 40 %  (Grün)\n"
            f"  Kiefersfelden:   8/15 = 53 %  (Gelb)"
        )

    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
