"""
Demo-Seed für BorderCapControl.
Setzt alle 4 Demo-Einrichtungen mit realistischeren Räumen und Belegungen.
ACHTUNG: Löscht und erneuert alle Demo-Daten (Belegungen, Aufgaben, Reservierungen).
"""
import os
import uuid
from datetime import date, timedelta

import psycopg2

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://bordercap_app:bordercap_app_dev@localhost:5432/bordercap?gssencmode=disable",
)

# ─── Demo-Standorte ──────────────────────────────────────────────────────────
LOCATIONS = [
    {
        "id": "a1b2c3d4-0001-0001-0001-000000000001",
        "name": "Flughafen Frankfurt",
        "adresse": "Flughafenstr. 1, 60547 Frankfurt",
        "kontingent": 20,
        "notbett_kapazitaet": 5,
    },
    {
        "id": "a1b2c3d4-0002-0002-0002-000000000002",
        "name": "Flughafen München",
        "adresse": "Nordallee 25, 85356 München",
        "kontingent": 15,
        "notbett_kapazitaet": 4,
    },
    {
        "id": "a1b2c3d4-0003-0003-0003-000000000003",
        "name": "Grenzübergang Passau",
        "adresse": "Innstraße 45, 94032 Passau",
        "kontingent": 10,
        "notbett_kapazitaet": 2,
    },
    {
        "id": "a1b2c3d4-0004-0004-0004-000000000004",
        "name": "Flughafen Hamburg",
        "adresse": "Flughafenstr. 1-3, 22335 Hamburg",
        "kontingent": 12,
        "notbett_kapazitaet": 3,
    },
]

EU_GESAMTQUOTE = 57

# ─── Räume + Betten pro Standort ─────────────────────────────────────────────
# geschlechts_designation: M=Männer, W=Frauen, D=Gemischt/Familie
ROOMS_CONFIG = {
    "a1b2c3d4-0001-0001-0001-000000000001": [  # Frankfurt: 6+6+4+4=20 Betten
        {"name": "Raum A – Männer", "designation": "M", "beds": 6},
        {"name": "Raum B – Frauen", "designation": "W", "beds": 6},
        {"name": "Raum C – Männer 2", "designation": "M", "beds": 4},
        {"name": "Raum D – Familie/Gemischt", "designation": "D", "beds": 4},
    ],
    "a1b2c3d4-0002-0002-0002-000000000002": [  # München: 6+6+3=15 Betten
        {"name": "Raum A – Männer", "designation": "M", "beds": 6},
        {"name": "Raum B – Frauen", "designation": "W", "beds": 6},
        {"name": "Raum C – Frauen 2", "designation": "W", "beds": 3},
    ],
    "a1b2c3d4-0003-0003-0003-000000000003": [  # Passau: 5+5=10 Betten
        {"name": "Raum A – Männer", "designation": "M", "beds": 5},
        {"name": "Raum B – Frauen", "designation": "W", "beds": 5},
    ],
    "a1b2c3d4-0004-0004-0004-000000000004": [  # Hamburg: 4+4+4=12 Betten
        {"name": "Raum A – Männer", "designation": "M", "beds": 4},
        {"name": "Raum B – Frauen", "designation": "W", "beds": 4},
        {"name": "Raum C – Familie/Gemischt", "designation": "D", "beds": 4},
    ],
}

# ─── Belegungen pro Raum ─────────────────────────────────────────────────────
# Anzahl belegter Betten; Rest bleibt frei.
# Frankfurt: ~15/20=75% → Gelb
# München: ~14/15=93% → Rot
# Passau: ~3/10=30% → Grün
# Hamburg: ~5/12=42% → Grün
OCCUPANCY_CONFIG = {
    "a1b2c3d4-0001-0001-0001-000000000001": {
        "Raum A – Männer":           {"count": 5, "geschlecht": "M"},
        "Raum B – Frauen":           {"count": 5, "geschlecht": "W"},
        "Raum C – Männer 2":         {"count": 3, "geschlecht": "M"},
        "Raum D – Familie/Gemischt": {"count": 2, "geschlecht": "D"},
    },
    "a1b2c3d4-0002-0002-0002-000000000002": {
        "Raum A – Männer":  {"count": 6, "geschlecht": "M"},
        "Raum B – Frauen":  {"count": 6, "geschlecht": "W"},
        "Raum C – Frauen 2": {"count": 2, "geschlecht": "W"},
    },
    "a1b2c3d4-0003-0003-0003-000000000003": {
        "Raum A – Männer": {"count": 2, "geschlecht": "M"},
        "Raum B – Frauen": {"count": 1, "geschlecht": "W"},
    },
    "a1b2c3d4-0004-0004-0004-000000000004": {
        "Raum A – Männer":           {"count": 2, "geschlecht": "M"},
        "Raum B – Frauen":           {"count": 2, "geschlecht": "W"},
        "Raum C – Familie/Gemischt": {"count": 1, "geschlecht": "D"},
    },
}

DEMO_LOC_IDS = [loc["id"] for loc in LOCATIONS]


def _room_id(location_id: str, room_name: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{location_id}-{room_name}"))


def _bed_id(room_id: str, bett_nr: int) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{room_id}-{bett_nr}"))


def _azr_code(loc_id: str, designation: str, idx: int) -> str:
    loc_short = loc_id[-4:]
    return f"AZR-2024-{loc_short}-{designation}{idx:02d}"


def _alias_code(designation: str, idx: int) -> str:
    return f"AL-{designation}-{idx:03d}"


def main() -> None:
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False
    cur = conn.cursor()

    today = date.today()
    start_30d = today - timedelta(days=30)
    end_60d = today + timedelta(days=60)
    end_80d = today + timedelta(days=80)
    end_100d = today + timedelta(days=100)

    try:
        print("Lösche Demo-Daten...")

        # UUID-Array für psycopg2 (cast zu uuid[])
        loc_ids_sql = [str(x) for x in DEMO_LOC_IDS]

        # Belegungen löschen (in Abhängigkeitsreihenfolge)
        cur.execute("""
            DELETE FROM persons.occupants o
            USING capacity.beds b
            JOIN capacity.rooms r ON r.id = b.room_id
            WHERE o.bed_id = b.id AND r.location_id = ANY(%s::uuid[])
        """, (loc_ids_sql,))

        cur.execute(
            "DELETE FROM tasks.inbox WHERE location_id = ANY(%s::uuid[])",
            (loc_ids_sql,)
        )
        cur.execute(
            "DELETE FROM reservations.requests WHERE requester_location_id = ANY(%s::uuid[]) OR target_location_id = ANY(%s::uuid[])",
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

        for loc in LOCATIONS:
            cur.execute("""
                INSERT INTO capacity.locations
                    (id, name, adresse, kontingent, notbett_kapazitaet, is_active, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, TRUE, NOW(), NOW())
                ON CONFLICT (id) DO UPDATE
                  SET kontingent = EXCLUDED.kontingent,
                      notbett_kapazitaet = EXCLUDED.notbett_kapazitaet,
                      adresse = EXCLUDED.adresse,
                      updated_at = NOW()
            """, (loc["id"], loc["name"], loc["adresse"],
                  loc["kontingent"], loc["notbett_kapazitaet"]))

            rooms_cfg = ROOMS_CONFIG[loc["id"]]
            occ_cfg = OCCUPANCY_CONFIG[loc["id"]]

            for room_def in rooms_cfg:
                room_id = _room_id(loc["id"], room_def["name"])
                cur.execute("""
                    INSERT INTO capacity.rooms
                        (id, location_id, name, geschlechts_designation, is_active, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, TRUE, NOW(), NOW())
                """, (room_id, loc["id"], room_def["name"], room_def["designation"]))
                n_rooms += 1

                for bett_nr in range(1, room_def["beds"] + 1):
                    bed_id = _bed_id(room_id, bett_nr)
                    cur.execute("""
                        INSERT INTO capacity.beds
                            (id, room_id, bett_nummer, bett_typ, is_active, created_at, updated_at)
                        VALUES (%s, %s, %s, 'KONTINGENT', TRUE, NOW(), NOW())
                    """, (bed_id, room_id, str(bett_nr)))
                    n_beds += 1

                # Belegungen anlegen
                occ_def = occ_cfg.get(room_def["name"])
                if not occ_def:
                    continue

                occ_count = occ_def["count"]
                geschlecht = occ_def["geschlecht"]

                for i in range(1, occ_count + 1):
                    bed_id = _bed_id(room_id, i)
                    occ_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"occ-{bed_id}-{geschlecht}"))
                    end = end_60d if i <= 2 else (end_80d if i <= 4 else end_100d)
                    azr = _azr_code(loc["id"], geschlecht if geschlecht != "D" else "X", i)
                    alias = _alias_code(geschlecht if geschlecht != "D" else "X", i)
                    # Für D-Räume: abwechselnd M und W
                    actual_g = geschlecht if geschlecht != "D" else ("M" if i % 2 == 1 else "W")
                    cur.execute("""
                        INSERT INTO persons.occupants
                            (id, bed_id, azr_id, alias_id, geschlecht,
                             belegung_start, belegung_ende, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                    """, (occ_id, bed_id, azr, alias, actual_g, start_30d, end))
                    n_occ += 1

        # EU-Gesamtquote
        cur.execute("""
            INSERT INTO capacity.system_settings (id, eu_gesamtquote, updated_at)
            VALUES (1, %s, NOW())
            ON CONFLICT (id) DO UPDATE SET eu_gesamtquote = EXCLUDED.eu_gesamtquote, updated_at = NOW()
        """, (EU_GESAMTQUOTE,))

        # ─── Demo-Reservierungsanfragen ───────────────────────────────────────
        loc_ffm = "a1b2c3d4-0001-0001-0001-000000000001"
        loc_muc = "a1b2c3d4-0002-0002-0002-000000000002"
        loc_pas = "a1b2c3d4-0003-0003-0003-000000000003"
        loc_ham = "a1b2c3d4-0004-0004-0004-000000000004"

        res1_id = str(uuid.uuid5(uuid.NAMESPACE_URL, "demo-reservation-1"))
        res2_id = str(uuid.uuid5(uuid.NAMESPACE_URL, "demo-reservation-2"))
        res3_id = str(uuid.uuid5(uuid.NAMESPACE_URL, "demo-reservation-3"))
        res4_id = str(uuid.uuid5(uuid.NAMESPACE_URL, "demo-reservation-4"))

        reservations = [
            # München → Frankfurt (kritische Auslastung → sendet Anfragen raus)
            (res1_id, loc_muc, loc_ffm, "AZR-2024-MUC-M99", "M", 1985, "SYR",
             today + timedelta(days=3), today + timedelta(days=60)),
            (res2_id, loc_muc, loc_ffm, "AZR-2024-MUC-W88", "W", 1990, "AFG",
             today + timedelta(days=3), today + timedelta(days=60)),
            # Passau → Frankfurt
            (res3_id, loc_pas, loc_ffm, "AZR-2024-PAU-M77", "M", 1978, "IRQ",
             today + timedelta(days=5), today + timedelta(days=60)),
            # Hamburg → München (zum Testen von Ablehnung)
            (res4_id, loc_ham, loc_muc, "AZR-2024-HAM-W55", "W", 1995, "ERI",
             today + timedelta(days=7), today + timedelta(days=45)),
        ]

        for (rid, req_loc, tgt_loc, azr, g, gj, land, start, ende) in reservations:
            cur.execute("""
                INSERT INTO reservations.requests
                    (id, requester_location_id, target_location_id, azr_id,
                     geschlecht, geburtsjahr, herkunftsland, belegung_start,
                     belegung_ende, status, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'PENDING', NOW(), NOW())
            """, (rid, req_loc, tgt_loc, azr, g, gj, land, start, ende))

        # ─── Demo-Postkorb-Tasks ──────────────────────────────────────────────
        tasks = [
            # Frankfurt empfängt 3 eingehende Anfragen
            (str(uuid.uuid5(uuid.NAMESPACE_URL, "demo-task-1")),
             loc_ffm, res1_id, "RESERVATION_RECEIVED", "HIGH",
             "Eingehende Reservierungsanfrage",
             f"München bittet um Aufnahme von AZR-2024-MUC-M99 (männlich, Syrien, *1985). "
             f"Belegungszeitraum: {today + timedelta(days=3)} – {today + timedelta(days=60)}."),

            (str(uuid.uuid5(uuid.NAMESPACE_URL, "demo-task-2")),
             loc_ffm, res2_id, "RESERVATION_RECEIVED", "HIGH",
             "Eingehende Reservierungsanfrage",
             f"München bittet um Aufnahme von AZR-2024-MUC-W88 (weiblich, Afghanistan, *1990). "
             f"Belegungszeitraum: {today + timedelta(days=3)} – {today + timedelta(days=60)}."),

            (str(uuid.uuid5(uuid.NAMESPACE_URL, "demo-task-3")),
             loc_ffm, res3_id, "RESERVATION_RECEIVED", "HIGH",
             "Eingehende Reservierungsanfrage",
             f"Passau bittet um Aufnahme von AZR-2024-PAU-M77 (männlich, Irak, *1978). "
             f"Belegungszeitraum: {today + timedelta(days=5)} – {today + timedelta(days=60)}."),

            # Frankfurt: 12-Wochen-Warnung
            (str(uuid.uuid5(uuid.NAMESPACE_URL, "demo-task-4")),
             loc_ffm, None, "RESERVATION_CONFIRMED", "MEDIUM",
             "12-Wochen-Warnung: 2 Belegungen laufen bald ab",
             "AZR-2024-0001-M01 und AZR-2024-0001-M02 (Raum A) erreichen in < 12 Wochen "
             "ihr Belegungsende. Bitte prüfen und ggf. verlängern oder Übergabe einleiten."),

            # Frankfurt: Kapazitätsmeldung
            (str(uuid.uuid5(uuid.NAMESPACE_URL, "demo-task-5")),
             loc_ffm, None, "RESERVATION_CONFIRMED", "LOW",
             "Kapazität: Frankfurt zu 75 % ausgelastet",
             "Das Kontingent der Einrichtung Frankfurt ist zu 75 % ausgelastet. "
             f"Noch {5} freie Plätze verfügbar."),

            # München: kritische Auslastung
            (str(uuid.uuid5(uuid.NAMESPACE_URL, "demo-task-6")),
             loc_muc, None, "RESERVATION_CONFIRMED", "HIGH",
             "Kapazität kritisch: München bei 93 %",
             "München hat nur noch 1 freien Platz (Raum C – Frauen 2). "
             "Reservierungsanfragen wurden an Frankfurt und Hamburg gesendet."),

            # München empfängt Anfrage von Hamburg (res4)
            (str(uuid.uuid5(uuid.NAMESPACE_URL, "demo-task-7")),
             loc_muc, res4_id, "RESERVATION_RECEIVED", "MEDIUM",
             "Eingehende Reservierungsanfrage",
             f"Hamburg bittet um Aufnahme von AZR-2024-HAM-W55 (weiblich, Eritrea, *1995). "
             f"Belegungszeitraum: {today + timedelta(days=7)} – {today + timedelta(days=45)}."),
        ]

        for td in tasks:
            tid, loc_id, rel_res_id, task_type, priority, title, body_text = td
            cur.execute("""
                INSERT INTO tasks.inbox
                    (id, location_id, related_reservation_id, task_type,
                     priority, status, title, body, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, 'OPEN', %s, %s, NOW(), NOW())
            """, (tid, loc_id, rel_res_id, task_type, priority, title, body_text))

        conn.commit()
        print(
            f"\nSeed abgeschlossen:\n"
            f"  {len(LOCATIONS)} Standorte\n"
            f"  {n_rooms} Räume, {n_beds} Betten\n"
            f"  {n_occ} Belegungen\n"
            f"  {len(reservations)} Reservierungsanfragen\n"
            f"  {len(tasks)} Postkorb-Aufgaben\n"
            f"  EU-Gesamtquote = {EU_GESAMTQUOTE}\n"
            f"\nBelegungsgrad:\n"
            f"  Frankfurt: 15/20 = 75% (Gelb)\n"
            f"  München:   14/15 = 93% (Rot)\n"
            f"  Passau:     3/10 = 30% (Grün)\n"
            f"  Hamburg:    5/12 = 42% (Grün)"
        )

    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
