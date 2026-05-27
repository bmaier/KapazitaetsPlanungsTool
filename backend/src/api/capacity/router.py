"""
FastAPI APIRouter für alle Kapazitäts-CRUD-Endpoints.

Schichtentrennung:
- Router: HTTP ↔ Pydantic Schemas, Session-Dependency, Domain-Error → HTTP 422
- Repos: DB-Zugriff, Audit-Log
- Domain-Rules: reine Logik ohne I/O
"""
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.adapters.db.capacity_repo import (
    SqlBedRepo,
    SqlLocationRepo,
    SqlOccupancyRepo,
    SqlRoomRepo,
    SqlSystemSettingsRepo,
)
from src.adapters.db.engine import AsyncSessionFactory
from src.adapters.keycloak.jwt import UserContext, get_current_user
from src.api.capacity.schemas import (
    BedCreate,
    BedResponse,
    BedStatusItem,
    BedUpdateRequest,
    EuQuotaUpdate,
    LabelCatalogEntry,
    LabelCatalogResponse,
    LabelsUpdateRequest,
    LocationCreate,
    LocationResponse,
    LocationSummaryResponse,
    LocationUpdateRequest,
    OccupancyCreate,
    OccupancyResponse,
    RoomBedStatus,
    RoomCreate,
    RoomResponse,
)
from src.domain.capacity.entities import Bed, Location, Occupancy, Room
from src.domain.capacity.rules import (
    DomainError,
    check_bed_available,
    check_eu_quota,
    check_12_weeks,
    check_notbett_duration,
)
from src.domain.capacity.value_objects import BedType

router = APIRouter(tags=["capacity"])




# ---------------------------------------------------------------------------
# Label Catalog (hardcoded — kein DB-Model nötig)
# ---------------------------------------------------------------------------

LABEL_CATALOG = [
    # ROOM
    {"name": "Rollstuhlgerecht", "category": "Ausstattung", "entity_types": ["ROOM"], "color": "#1565c0"},
    {"name": "Erdgeschoss", "category": "Ausstattung", "entity_types": ["ROOM"], "color": "#1565c0"},
    {"name": "Barrierefreiheit", "category": "Ausstattung", "entity_types": ["ROOM", "BED"], "color": "#1565c0"},
    {"name": "Ruhig", "category": "Ausstattung", "entity_types": ["ROOM"], "color": "#2e7d32"},
    {"name": "Klimaanlage", "category": "Ausstattung", "entity_types": ["ROOM"], "color": "#2e7d32"},
    {"name": "Familienraum", "category": "Eignung", "entity_types": ["ROOM"], "color": "#6a1b9a"},
    {"name": "Männer", "category": "Geschlecht", "entity_types": ["ROOM"], "color": "#1565c0"},
    {"name": "Frauen", "category": "Geschlecht", "entity_types": ["ROOM"], "color": "#880e4f"},
    {"name": "Gemischt", "category": "Geschlecht", "entity_types": ["ROOM"], "color": "#4a148c"},
    # BED
    {"name": "Unteres Bett", "category": "Position", "entity_types": ["BED"], "color": "#e65100"},
    {"name": "Oberes Bett", "category": "Position", "entity_types": ["BED"], "color": "#e65100"},
    {"name": "Bodeneben", "category": "Position", "entity_types": ["BED"], "color": "#e65100"},
    {"name": "Breites Bett", "category": "Typ", "entity_types": ["BED"], "color": "#00695c"},
    {"name": "Kinderbett", "category": "Typ", "entity_types": ["BED"], "color": "#6a1b9a"},
    # OCCUPANCY
    {"name": "Kind", "category": "Schutz", "entity_types": ["OCCUPANCY"], "color": "#6a1b9a"},
    {"name": "Unbegleitete Minderjährige", "category": "Schutz", "entity_types": ["OCCUPANCY"], "color": "#b71c1c"},
    {"name": "Pflegebedarf", "category": "Schutz", "entity_types": ["OCCUPANCY"], "color": "#b71c1c"},
    {"name": "Mobilitätseinschränkung", "category": "Schutz", "entity_types": ["OCCUPANCY", "BED", "ROOM"], "color": "#e65100"},
    {"name": "Arabisch", "category": "Sprache", "entity_types": ["OCCUPANCY"], "color": "#00796b"},
    {"name": "Farsi/Dari", "category": "Sprache", "entity_types": ["OCCUPANCY"], "color": "#00796b"},
    {"name": "Türkisch", "category": "Sprache", "entity_types": ["OCCUPANCY"], "color": "#00796b"},
    {"name": "Englisch", "category": "Sprache", "entity_types": ["OCCUPANCY"], "color": "#00796b"},
    {"name": "Französisch", "category": "Sprache", "entity_types": ["OCCUPANCY"], "color": "#00796b"},
    {"name": "Russisch", "category": "Sprache", "entity_types": ["OCCUPANCY"], "color": "#00796b"},
    {"name": "Halal", "category": "Hinweis", "entity_types": ["OCCUPANCY"], "color": "#558b2f"},
    {"name": "Vegetarisch", "category": "Hinweis", "entity_types": ["OCCUPANCY"], "color": "#558b2f"},
    {"name": "Familienmitglied", "category": "Gruppe", "entity_types": ["OCCUPANCY"], "color": "#6a1b9a"},
    {"name": "Alleinstehend", "category": "Gruppe", "entity_types": ["OCCUPANCY"], "color": "#455a64"},
]


# ---------------------------------------------------------------------------
# Session Dependency
# ---------------------------------------------------------------------------


async def get_session():
    """Liefert eine AsyncSession aus der SessionFactory als DI-Dependency."""
    async with AsyncSessionFactory() as session:
        async with session.begin():
            yield session


# ---------------------------------------------------------------------------
# Hilfsfunktion: DomainError → HTTP 422
# ---------------------------------------------------------------------------


def _raise_422(e: DomainError) -> None:
    raise HTTPException(status_code=422, detail=e.message)


# ---------------------------------------------------------------------------
# System Settings
# ---------------------------------------------------------------------------


@router.post("/system/eu-quota", status_code=200)
async def set_eu_quota(
    body: EuQuotaUpdate,
    session: AsyncSession = Depends(get_session),
):
    """Setzt die EU-Gesamtquote (Singleton in capacity.system_settings)."""
    repo = SqlSystemSettingsRepo(session)
    await repo.set_eu_quota(body.eu_gesamtquote)
    return {"eu_gesamtquote": body.eu_gesamtquote}


@router.get("/system/eu-quota", status_code=200)
async def get_eu_quota(session: AsyncSession = Depends(get_session)):
    """Liest die aktuelle EU-Gesamtquote."""
    repo = SqlSystemSettingsRepo(session)
    settings = await repo.get()
    return {"eu_gesamtquote": settings.eu_gesamtquote}


# ---------------------------------------------------------------------------
# Locations
# ---------------------------------------------------------------------------


@router.post("/locations", response_model=LocationResponse, status_code=201)
async def create_location(
    body: LocationCreate,
    session: AsyncSession = Depends(get_session),
):
    """
    Erstellt eine neue Einrichtung.
    422 wenn die Kontingent-Summe die EU-Gesamtquote überschreiten würde.
    """
    settings_repo = SqlSystemSettingsRepo(session)
    loc_repo = SqlLocationRepo(session)

    settings = await settings_repo.get()
    current_sum = await loc_repo.sum_kontingent()

    try:
        check_eu_quota(current_sum, body.kontingent, settings.eu_gesamtquote)
    except DomainError as e:
        _raise_422(e)

    location = Location(
        id=uuid4(),
        name=body.name,
        adresse=body.adresse,
        kontingent=body.kontingent,
        notbett_kapazitaet=body.notbett_kapazitaet,
        is_active=True,
    )
    created = await loc_repo.create(location)
    return LocationResponse(
        id=created.id,
        name=created.name,
        adresse=created.adresse,
        kontingent=created.kontingent,
        notbett_kapazitaet=created.notbett_kapazitaet,
        is_active=created.is_active,
        labels=[],
        lat=None,
        lon=None,
        valid_from=None,
        valid_until=None,
    )


@router.get("/locations", response_model=List[LocationResponse])
async def list_locations(
    include_inactive: bool = False,
    session: AsyncSession = Depends(get_session),
):
    """Listet alle aktiven Einrichtungen. Mit ?include_inactive=true auch inaktive."""
    where_clause = "" if include_inactive else "WHERE is_active = true"
    result = await session.execute(
        text(f"""
            SELECT id, name, adresse, kontingent, notbett_kapazitaet, is_active,
                   labels, lat, lon, valid_from, valid_until
            FROM capacity.locations
            {where_clause}
            ORDER BY name
        """)
    )
    rows = result.mappings().all()
    return [
        LocationResponse(
            id=row["id"],
            name=row["name"],
            adresse=row["adresse"],
            kontingent=row["kontingent"],
            notbett_kapazitaet=row["notbett_kapazitaet"],
            is_active=row["is_active"],
            labels=list(row["labels"] or []),
            lat=row["lat"],
            lon=row["lon"],
            valid_from=row["valid_from"],
            valid_until=row["valid_until"],
        )
        for row in rows
    ]


@router.get("/locations/summary", response_model=List[LocationSummaryResponse])
async def get_locations_summary() -> List[LocationSummaryResponse]:
    """
    Alle aktiven Einrichtungen mit aktuellem Belegungsgrad.
    Kein X-Location-Id erforderlich — gibt globale Übersicht zurück.
    get_current_user wird via Router-Level-Dependency in main.py bereits erzwungen.
    """
    async with AsyncSessionFactory() as session:
        result = await session.execute(
            text("""
                SELECT
                    l.id,
                    l.name,
                    l.kontingent,
                    l.notbett_kapazitaet,
                    l.is_active,
                    l.lat,
                    l.lon,
                    l.valid_from,
                    l.valid_until,
                    COUNT(o.id) FILTER (
                        WHERE o.belegung_ende >= CURRENT_DATE
                    ) AS belegt,
                    CASE
                        WHEN l.kontingent > 0 THEN
                            LEAST(
                                COUNT(o.id) FILTER (
                                    WHERE o.belegung_ende >= CURRENT_DATE
                                ) * 100.0 / l.kontingent,
                                100.0
                            )
                        ELSE 0.0
                    END AS belegungsgrad_pct
                FROM capacity.locations l
                LEFT JOIN capacity.rooms r ON r.location_id = l.id AND r.is_active = true
                LEFT JOIN capacity.beds b ON b.room_id = r.id AND b.is_active = true
                LEFT JOIN persons.occupants o ON o.bed_id = b.id
                WHERE l.is_active = true
                GROUP BY l.id, l.name, l.kontingent, l.notbett_kapazitaet, l.is_active, l.lat, l.lon, l.valid_from, l.valid_until
                ORDER BY l.name
            """)
        )
        rows = result.mappings().all()
    return [
        LocationSummaryResponse(
            id=row["id"],
            name=row["name"],
            kontingent=row["kontingent"],
            notbett_kapazitaet=row["notbett_kapazitaet"],
            belegt=int(row["belegt"]),
            belegungsgrad_pct=float(row["belegungsgrad_pct"]),
            is_active=row["is_active"],
            lat=row["lat"],
            lon=row["lon"],
            valid_from=row["valid_from"],
            valid_until=row["valid_until"],
        )
        for row in rows
    ]


@router.get("/locations/{location_id}", response_model=LocationResponse)
async def get_location(
    location_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """Gibt eine einzelne Einrichtung zurück."""
    result = await session.execute(
        text("""
            SELECT id, name, adresse, kontingent, notbett_kapazitaet, is_active,
                   labels, lat, lon, valid_from, valid_until
            FROM capacity.locations
            WHERE id = :id
        """),
        {"id": str(location_id)},
    )
    row = result.mappings().one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Location nicht gefunden")
    return LocationResponse(
        id=row["id"],
        name=row["name"],
        adresse=row["adresse"],
        kontingent=row["kontingent"],
        notbett_kapazitaet=row["notbett_kapazitaet"],
        is_active=row["is_active"],
        labels=list(row["labels"] or []),
        lat=row["lat"],
        lon=row["lon"],
        valid_from=row["valid_from"],
        valid_until=row["valid_until"],
    )


@router.patch("/locations/{location_id}", response_model=LocationResponse, status_code=200)
async def update_location(
    location_id: UUID,
    body: LocationUpdateRequest,
    session: AsyncSession = Depends(get_session),
    _: UserContext = Depends(get_current_user),
):
    """Aktualisiert Felder einer Einrichtung inkl. Labels, Koordinaten und Gültigkeitsdaten."""
    updates: dict = {}
    if body.name is not None:
        updates["name"] = body.name
    if body.adresse is not None:
        updates["adresse"] = body.adresse
    if body.kontingent is not None:
        updates["kontingent"] = body.kontingent
    if body.notbett_kapazitaet is not None:
        updates["notbett_kapazitaet"] = body.notbett_kapazitaet
    if body.labels is not None:
        updates["labels"] = body.labels
    if body.lat is not None:
        updates["lat"] = body.lat
    if body.lon is not None:
        updates["lon"] = body.lon
    if body.valid_from is not None:
        updates["valid_from"] = body.valid_from
    if body.valid_until is not None:
        updates["valid_until"] = body.valid_until

    if not updates:
        raise HTTPException(status_code=422, detail="Keine Felder zum Aktualisieren")

    # Kontingent-Schutz: nicht unter aktuelle Belegung
    if body.kontingent is not None:
        result = await session.execute(
            text("""
                SELECT COUNT(o.id) AS belegt
                FROM persons.occupants o
                JOIN capacity.beds b ON b.id = o.bed_id AND b.bett_typ = 'KONTINGENT'
                JOIN capacity.rooms r ON r.id = b.room_id
                WHERE r.location_id = :lid
                  AND o.belegung_start <= CURRENT_DATE
                  AND o.belegung_ende > CURRENT_DATE
            """),
            {"lid": str(location_id)}
        )
        row = result.fetchone()
        belegt = int(row.belegt) if row else 0
        if body.kontingent < belegt:
            raise HTTPException(
                status_code=409,
                detail=f"Aktuelle Belegung ({belegt} Plätze) übersteigt das neue Kontingent ({body.kontingent}). Erst ausbuchen oder verlegen."
            )

    updates["id"] = str(location_id)
    set_parts = []
    for k in (k for k in updates if k != "id"):
        if k == "labels":
            set_parts.append("labels = CAST(:labels AS TEXT[])")
        else:
            set_parts.append(f"{k} = :{k}")
    set_clause = ", ".join(set_parts)
    result = await session.execute(
        text(
            f"UPDATE capacity.locations SET {set_clause}, updated_at = NOW() "
            f"WHERE id = :id RETURNING id, name, adresse, kontingent, notbett_kapazitaet, "
            f"is_active, labels, lat, lon, valid_from, valid_until"
        ),
        updates,
    )
    row = result.mappings().one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Einrichtung nicht gefunden")
    return LocationResponse(
        id=row["id"],
        name=row["name"],
        adresse=row["adresse"],
        kontingent=row["kontingent"],
        notbett_kapazitaet=row["notbett_kapazitaet"],
        is_active=row["is_active"],
        labels=list(row["labels"] or []),
        lat=row["lat"],
        lon=row["lon"],
        valid_from=row["valid_from"],
        valid_until=row["valid_until"],
    )


@router.get("/locations/{location_id}/bed-status", response_model=List[RoomBedStatus])
async def get_bed_status(
    location_id: UUID,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
):
    """
    Gibt alle Räume mit Bett-Belegungsstatus für einen Zeitraum zurück.
    Betten ohne Belegungsüberschneidung → FREI, sonst → BELEGT.
    """
    d_from = date_from or date.today()
    d_to = date_to or date(d_from.year + 1, d_from.month, d_from.day)
    async with AsyncSessionFactory() as session:
        result = await session.execute(text("""
            SELECT
              r.id        AS room_id,
              r.name      AS room_name,
              r.geschlechts_designation,
              r.labels    AS room_labels,
              r.valid_from AS room_valid_from,
              r.valid_until AS room_valid_until,
              b.id        AS bed_id,
              b.bett_nummer,
              b.bett_typ,
              b.labels    AS bed_labels,
              b.deaktiviert_ab,
              b.valid_from AS bed_valid_from,
              CASE WHEN o.id IS NOT NULL THEN 'BELEGT' ELSE 'FREI' END AS status,
              o.id        AS occupancy_id,
              o.azr_id,
              o.alias_id,
              o.geschlecht AS occ_geschlecht,
              o.belegung_start,
              o.belegung_ende,
              o.labels    AS occ_labels,
              o.extended_once,
              (
                SELECT COUNT(*) FROM reservations.requests req
                WHERE req.target_location_id = r.location_id
                  AND req.status = 'PENDING'
                  AND (req.geschlecht = r.geschlechts_designation
                       OR r.geschlechts_designation = 'D')
              ) AS pending_count
            FROM capacity.rooms r
            JOIN capacity.beds b ON b.room_id = r.id AND b.is_active = true AND b.bett_typ != 'DOPPEL'
            LEFT JOIN persons.occupants o
              ON o.bed_id = b.id
              AND o.belegung_start < :date_to
              AND o.belegung_ende > :date_from
            WHERE r.location_id = :location_id
              AND r.is_active = true
            ORDER BY r.name, b.bett_nummer::integer
        """), {"location_id": str(location_id), "date_from": d_from, "date_to": d_to})
        rows = result.mappings().all()

    rooms_map: dict[str, dict] = {}
    rooms_order: list[str] = []
    for row in rows:
        rid = str(row["room_id"])
        if rid not in rooms_map:
            rooms_map[rid] = {
                "room_id": row["room_id"],
                "room_name": row["room_name"],
                "geschlechts_designation": row["geschlechts_designation"],
                "labels": list(row["room_labels"] or []),
                "beds": [],
                "pending_count": int(row.get("pending_count") or 0),
                "valid_from": row.get("room_valid_from"),
                "valid_until": row.get("room_valid_until"),
            }
            rooms_order.append(rid)
        rooms_map[rid]["beds"].append(BedStatusItem(
            bed_id=row["bed_id"],
            bett_nummer=row["bett_nummer"],
            bett_typ=row["bett_typ"],
            status=row["status"],
            occupancy_id=row.get("occupancy_id"),
            azr_id=row.get("azr_id"),
            alias_id=row.get("alias_id"),
            occ_geschlecht=row.get("occ_geschlecht"),
            belegung_start=row.get("belegung_start"),
            belegung_ende=row.get("belegung_ende"),
            room_labels=list(row["room_labels"] or []),
            bed_labels=list(row["bed_labels"] or []),
            occ_labels=list(row["occ_labels"] or []),
            deaktiviert_ab=row.get("deaktiviert_ab"),
            bed_valid_from=row.get("bed_valid_from"),
            is_notbett=(row["bett_typ"] == "NOTBETT"),
            extended_once=bool(row.get("extended_once") or False),
        ))
    return [RoomBedStatus(**rooms_map[rid]) for rid in rooms_order]


@router.get("/occupants/search")
async def search_occupants(
    q: Optional[str] = None,
    azr_id: Optional[str] = None,
    alias_id: Optional[str] = None,
    labels: Optional[str] = None,
):
    """
    Sucht nach Belegungen anhand von AZR-ID, Alias-ID oder freitext (q).
    Optionale Filterung per ?labels=Label1,Label2 (kommagetrennt, AND-Logik).
    Gibt Bett, Raum, Einrichtung und Belegungszeitraum zurück.
    """
    search_term = q or azr_id or alias_id
    # At least one of search_term or labels must be provided
    if not search_term and not labels:
        return []

    label_list = [lbl.strip() for lbl in labels.split(",") if lbl.strip()] if labels else []

    params: dict = {}
    where_clauses = ["o.belegung_ende >= CURRENT_DATE"]

    if search_term:
        term = f"%{search_term.strip()}%"
        params["term"] = term
        where_clauses.append("(o.azr_id ILIKE :term OR o.alias_id ILIKE :term)")

    if label_list:
        # All requested labels must appear in o.labels (AND logic)
        # Use PostgreSQL array literal to avoid asyncpg type-encoding issues
        params["label_filter"] = label_list
        where_clauses.append("o.labels @> CAST(:label_filter AS TEXT[])")

    where_sql = " AND ".join(where_clauses)

    async with AsyncSessionFactory() as session:
        result = await session.execute(text(f"""
            SELECT
              o.id          AS occupancy_id,
              o.azr_id,
              o.alias_id,
              o.geschlecht,
              o.belegung_start,
              o.belegung_ende,
              o.labels      AS occ_labels,
              b.id          AS bed_id,
              b.bett_nummer,
              b.bett_typ,
              b.labels      AS bed_labels,
              r.id          AS room_id,
              r.name        AS room_name,
              r.geschlechts_designation,
              r.labels      AS room_labels,
              l.id          AS location_id,
              l.name        AS location_name
            FROM persons.occupants o
            JOIN capacity.beds b ON b.id = o.bed_id AND b.is_active = true
            JOIN capacity.rooms r ON r.id = b.room_id AND r.is_active = true
            JOIN capacity.locations l ON l.id = r.location_id AND l.is_active = true
            WHERE {where_sql}
            ORDER BY o.belegung_ende ASC
            LIMIT 50
        """), params)
        rows = result.mappings().all()
    return [dict(row) for row in rows]


@router.patch("/locations/{location_id}/labels", status_code=200)
async def set_location_labels(
    location_id: UUID,
    body: LabelsUpdateRequest,
    session: AsyncSession = Depends(get_session),
    _: UserContext = Depends(get_current_user),
):
    """Setzt die Labels einer Einrichtung (vollständiges Ersetzen)."""
    result = await session.execute(
        text("UPDATE capacity.locations SET labels = CAST(:labels AS TEXT[]), updated_at = NOW() WHERE id = :id RETURNING id"),
        {"labels": body.labels, "id": str(location_id)},
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Einrichtung nicht gefunden")
    return {"labels": body.labels}


@router.post("/locations/{location_id}/deactivate", status_code=200)
async def deactivate_location_safe(
    location_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: UserContext = Depends(get_current_user),
):
    """Deaktiviert eine Einrichtung. Schlägt fehl, wenn noch aktive Belegungen vorhanden sind."""
    result = await session.execute(
        text("""
            SELECT COUNT(*) AS cnt
            FROM persons.occupants o
            JOIN capacity.beds b ON b.id = o.bed_id
            JOIN capacity.rooms r ON r.id = b.room_id
            WHERE r.location_id = :loc_id
              AND o.belegung_ende >= CURRENT_DATE
        """),
        {"loc_id": str(location_id)},
    )
    row = result.fetchone()
    if row and row.cnt > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Einrichtung hat noch {row.cnt} aktive Belegungen. Erst umbuchen, dann deaktivieren.",
        )
    await session.execute(
        text("UPDATE capacity.locations SET is_active = false, updated_at = NOW() WHERE id = :id"),
        {"id": str(location_id)},
    )
    return {"status": "deactivated"}


@router.delete("/locations/{location_id}", status_code=200)
async def deactivate_location(
    location_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """Soft-Delete: setzt is_active=False, löscht nicht physisch."""
    repo = SqlLocationRepo(session)
    loc = await repo.get_by_id(location_id)
    if not loc:
        raise HTTPException(status_code=404, detail="Location nicht gefunden")
    await repo.deactivate(location_id)
    return {"deactivated": True}


# ---------------------------------------------------------------------------
# Rooms
# ---------------------------------------------------------------------------


@router.post(
    "/locations/{location_id}/rooms",
    response_model=RoomResponse,
    status_code=201,
)
async def create_room(
    location_id: UUID,
    body: RoomCreate,
    session: AsyncSession = Depends(get_session),
):
    """Fügt einen Raum zu einer Einrichtung hinzu."""
    loc_repo = SqlLocationRepo(session)
    loc = await loc_repo.get_by_id(location_id)
    if not loc or not loc.is_active:
        raise HTTPException(status_code=404, detail="Location nicht gefunden")

    room = Room(
        id=uuid4(),
        location_id=location_id,
        name=body.name,
        geschlechts_designation=body.geschlechts_designation,
        is_active=True,
    )
    room_repo = SqlRoomRepo(session)
    created = await room_repo.create(room)
    return RoomResponse(
        id=created.id,
        location_id=created.location_id,
        name=created.name,
        geschlechts_designation=created.geschlechts_designation,
        is_active=created.is_active,
    )


@router.get(
    "/locations/{location_id}/rooms",
    response_model=List[RoomResponse],
)
async def list_rooms(
    location_id: UUID,
    include_inactive: bool = False,
    session: AsyncSession = Depends(get_session),
):
    """Listet alle aktiven Räume einer Einrichtung. Mit ?include_inactive=true auch inaktive."""
    repo = SqlRoomRepo(session)
    if include_inactive:
        rooms = await repo.list_all_for_location(location_id)
    else:
        rooms = await repo.list_active_for_location(location_id)
    return [
        RoomResponse(
            id=r.id,
            location_id=r.location_id,
            name=r.name,
            geschlechts_designation=r.geschlechts_designation,
            is_active=r.is_active,
            labels=list(r.labels or []),
            valid_from=r.valid_from,
            valid_until=r.valid_until,
        )
        for r in rooms
    ]


@router.delete("/rooms/{room_id}", status_code=200)
async def deactivate_room(
    room_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """Soft-Delete eines Raums."""
    repo = SqlRoomRepo(session)
    room = await repo.get_by_id(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Raum nicht gefunden")
    result = await session.execute(
        text("""
            SELECT COUNT(*) AS cnt
            FROM persons.occupants o
            JOIN capacity.beds b ON b.id = o.bed_id
            WHERE b.room_id = :room_id
              AND o.belegung_ende >= CURRENT_DATE
        """),
        {"room_id": str(room_id)},
    )
    row = result.fetchone()
    if row and row.cnt > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Raum hat noch {row.cnt} aktive Belegung(en). Erst umbuchen, dann deaktivieren.",
        )
    await repo.deactivate(room_id)
    return {"deactivated": True}


class RoomActivateRequest(BaseModel):
    valid_from: Optional[date] = None
    valid_until: Optional[date] = None


@router.post("/rooms/{room_id}/activate", status_code=200)
async def activate_room(
    room_id: UUID,
    body: RoomActivateRequest,
    session: AsyncSession = Depends(get_session),
):
    """Reaktiviert einen inaktiven Raum, optional mit Gültigkeitsdaten."""
    updates: dict = {"is_active": True}
    if body.valid_from is not None:
        updates["valid_from"] = body.valid_from
    if body.valid_until is not None:
        updates["valid_until"] = body.valid_until
    set_parts = ", ".join(f"{k} = :{k}" for k in updates if k != "id")
    updates["id"] = str(room_id)
    result = await session.execute(
        text(f"UPDATE capacity.rooms SET {set_parts} WHERE id = :id RETURNING id"),
        updates,
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Raum nicht gefunden")
    return {"activated": True}


@router.patch("/rooms/{room_id}/validity", status_code=200)
async def update_room_validity(
    room_id: UUID,
    body: RoomActivateRequest,
    session: AsyncSession = Depends(get_session),
):
    """Setzt Gültigkeitsdaten (valid_from / valid_until) für einen Raum."""
    updates: dict = {}
    if body.valid_from is not None:
        updates["valid_from"] = body.valid_from
    if body.valid_until is not None:
        updates["valid_until"] = body.valid_until
    if not updates:
        return {"message": "Keine Änderungen"}
    set_parts = ", ".join(f"{k} = :{k}" for k in updates)
    updates["id"] = str(room_id)
    result = await session.execute(
        text(f"UPDATE capacity.rooms SET {set_parts} WHERE id = :id RETURNING id"),
        updates,
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Raum nicht gefunden")
    return {"updated": True}


# ---------------------------------------------------------------------------
# Beds
# ---------------------------------------------------------------------------


@router.post(
    "/rooms/{room_id}/beds",
    response_model=BedResponse,
    status_code=201,
)
async def create_bed(
    room_id: UUID,
    body: BedCreate,
    session: AsyncSession = Depends(get_session),
):
    """Fügt ein Bett zu einem Raum hinzu."""
    room_repo = SqlRoomRepo(session)
    room = await room_repo.get_by_id(room_id)
    if not room or not room.is_active:
        raise HTTPException(status_code=404, detail="Raum nicht gefunden")

    bed = Bed(
        id=uuid4(),
        room_id=room_id,
        bett_nummer=body.bett_nummer,
        bett_typ=body.bett_typ,
        is_active=True,
    )
    bed_repo = SqlBedRepo(session)
    created = await bed_repo.create(bed)
    return BedResponse(
        id=created.id,
        room_id=created.room_id,
        bett_nummer=created.bett_nummer,
        bett_typ=created.bett_typ,
        is_active=created.is_active,
    )


@router.get(
    "/rooms/{room_id}/beds",
    response_model=List[BedResponse],
)
async def list_beds(
    room_id: UUID,
    include_inactive: bool = False,
    session: AsyncSession = Depends(get_session),
):
    """Listet alle aktiven Betten eines Raums. Mit ?include_inactive=true auch inaktive."""
    repo = SqlBedRepo(session)
    if include_inactive:
        beds = await repo.list_all_for_room(room_id)
    else:
        beds = await repo.list_active_for_room(room_id)
    return [
        BedResponse(
            id=b.id,
            room_id=b.room_id,
            bett_nummer=b.bett_nummer,
            bett_typ=b.bett_typ,
            is_active=b.is_active,
            deaktiviert_ab=b.deaktiviert_ab,
        )
        for b in beds
    ]


@router.delete("/beds/{bed_id}", status_code=200)
async def deactivate_bed(
    bed_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """Soft-Delete eines Betts."""
    repo = SqlBedRepo(session)
    bed = await repo.get_by_id(bed_id)
    if not bed:
        raise HTTPException(status_code=404, detail="Bett nicht gefunden")
    await repo.deactivate(bed_id)
    return {"deactivated": True}


@router.patch("/beds/{bed_id}/validity", status_code=200)
async def update_bed_validity(
    bed_id: UUID,
    body: BedUpdateRequest,
    session: AsyncSession = Depends(get_session),
    _: UserContext = Depends(get_current_user),
):
    """Setzt valid_from für ein Bett (geplante Verfügbarkeit ab Datum)."""
    if body.valid_from is None:
        return {"message": "Keine Änderungen"}
    result = await session.execute(
        text("UPDATE capacity.beds SET valid_from = :valid_from WHERE id = :id RETURNING id"),
        {"valid_from": body.valid_from, "id": str(bed_id)},
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Bett nicht gefunden")
    return {"updated": True, "valid_from": str(body.valid_from)}


@router.patch("/beds/{bed_id}/deactivate", status_code=200)
async def deactivate_bed_timed(
    bed_id: UUID,
    body: BedUpdateRequest,
    session: AsyncSession = Depends(get_session),
    _: UserContext = Depends(get_current_user),
):
    """Deaktiviert ein Bett sofort oder setzt ein zukünftiges Deaktivierungsdatum."""
    from datetime import date as date_type
    today = date_type.today()

    deakt_ab = body.deaktiviert_ab

    if deakt_ab and deakt_ab > today:
        # Future deactivation: check for occupancies overlapping with deakt_ab
        conflict = await session.execute(
            text("""
                SELECT o.azr_id, o.belegung_ende
                FROM persons.occupants o
                WHERE o.bed_id = :bid
                  AND o.belegung_ende > :deakt_ab
                LIMIT 1
            """),
            {"bid": str(bed_id), "deakt_ab": deakt_ab}
        )
        row = conflict.fetchone()
        if row:
            raise HTTPException(
                status_code=409,
                detail=f"Belegung {row.azr_id} endet {row.belegung_ende} — nach dem Deaktivierungsdatum {deakt_ab}. Erst umbuchen."
            )
        await session.execute(
            text("UPDATE capacity.beds SET deaktiviert_ab = :d WHERE id = :id"),
            {"d": deakt_ab, "id": str(bed_id)}
        )
        return {"status": "scheduled", "deaktiviert_ab": str(deakt_ab)}
    else:
        # Immediate deactivation
        conflict = await session.execute(
            text("""
                SELECT o.azr_id FROM persons.occupants o
                WHERE o.bed_id = :bid
                  AND o.belegung_ende > CURRENT_DATE
                LIMIT 1
            """),
            {"bid": str(bed_id)}
        )
        row = conflict.fetchone()
        if row:
            raise HTTPException(
                status_code=409,
                detail=f"Belegung {row.azr_id} ist noch aktiv. Erst ausbuchen, dann deaktivieren."
            )
        await session.execute(
            text("UPDATE capacity.beds SET is_active = false, updated_at = NOW() WHERE id = :id"),
            {"id": str(bed_id)}
        )
        return {"status": "deactivated"}


# ---------------------------------------------------------------------------
# Occupancy
# ---------------------------------------------------------------------------


@router.post(
    "/beds/{bed_id}/occupancy",
    response_model=OccupancyResponse,
    status_code=201,
)
async def create_occupancy(
    bed_id: UUID,
    body: OccupancyCreate,
    response: Response,
    session: AsyncSession = Depends(get_session),
):
    """
    Erstellt eine Belegung für ein Bett.

    Domain-Checks:
    - Bett muss frei sein (kein aktiver Eintrag in persons.occupants)
    - Notbett: max. 1 Nacht (sonst HTTP 422)
    - 12-Wochen-Überschreitung: HTTP 201 + Header X-12W-Warning: true
    """
    bed_repo = SqlBedRepo(session)
    occ_repo = SqlOccupancyRepo(session)

    bed = await bed_repo.get_by_id(bed_id)
    if not bed or not bed.is_active:
        raise HTTPException(status_code=404, detail="Bett nicht gefunden")

    loc_validity = await session.execute(
        text("""
            SELECT l.valid_from, l.valid_until
            FROM capacity.rooms r
            JOIN capacity.locations l ON l.id = r.location_id
            WHERE r.id = :room_id
        """),
        {"room_id": str(bed.room_id)},
    )
    loc_row = loc_validity.fetchone()
    if loc_row:
        if loc_row.valid_from and body.belegung_start < loc_row.valid_from:
            raise HTTPException(status_code=409, detail=f"Einrichtung ist erst ab {loc_row.valid_from} aktiv")
        if loc_row.valid_until and body.belegung_start >= loc_row.valid_until:
            raise HTTPException(status_code=409, detail=f"Einrichtung ist ab {loc_row.valid_until} inaktiv")

    existing = await occ_repo.get_active_for_bed(bed_id)

    try:
        check_bed_available(existing)
        check_notbett_duration(
            BedType(bed.bett_typ), body.belegung_start, body.belegung_ende
        )
    except DomainError as e:
        _raise_422(e)

    warn_12w = check_12_weeks(body.belegung_start, body.belegung_ende)

    occupancy = Occupancy(
        id=uuid4(),
        bed_id=bed_id,
        azr_id=body.azr_id,
        alias_id=body.alias_id,
        geschlecht=body.geschlecht.value,
        belegung_start=body.belegung_start,
        belegung_ende=body.belegung_ende,
    )
    created = await occ_repo.create(occupancy)

    if warn_12w:
        response.headers["X-12W-Warning"] = "true"

    return OccupancyResponse(
        id=created.id,
        bed_id=created.bed_id,
        azr_id=created.azr_id,
        alias_id=created.alias_id,
        geschlecht=created.geschlecht,
        belegung_start=created.belegung_start,
        belegung_ende=created.belegung_ende,
    )


@router.post("/occupants/{occupancy_id}/extend", status_code=200)
async def extend_notbett_occupancy(
    occupancy_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: UserContext = Depends(get_current_user),
):
    """Verlängert eine Notbett-Belegung einmalig um 1 Tag."""
    result = await session.execute(
        text("""
            SELECT o.id, o.belegung_ende, o.extended_once, b.bett_typ
            FROM persons.occupants o
            JOIN capacity.beds b ON b.id = o.bed_id
            WHERE o.id = :occ_id
        """),
        {"occ_id": str(occupancy_id)},
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Belegung nicht gefunden")
    if row.bett_typ != "NOTBETT":
        raise HTTPException(status_code=422, detail="Nur Notbetten können verlängert werden")
    if row.extended_once:
        raise HTTPException(status_code=409, detail="Notbett-Verlängerung wurde bereits einmal gewährt")
    new_ende = row.belegung_ende + timedelta(days=1)
    await session.execute(
        text("""
            UPDATE persons.occupants
            SET belegung_ende = :new_ende, extended_once = TRUE
            WHERE id = :occ_id
        """),
        {"new_ende": new_ende, "occ_id": str(occupancy_id)},
    )
    return {"belegung_ende": str(new_ende), "extended_once": True}


@router.delete("/beds/{bed_id}/occupancy/{occupancy_id}", status_code=200)
async def end_occupancy(
    bed_id: UUID,
    occupancy_id: UUID,
    grund: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
):
    """
    Beendet eine aktive Belegung — physisches Löschen aus persons.occupants.
    `grund` wird als Pflichtfeld aus der UI übergeben und geloggt.
    """
    occ_repo = SqlOccupancyRepo(session)
    occupancy = await occ_repo.get_by_id(occupancy_id)
    if not occupancy:
        raise HTTPException(
            status_code=404, detail="Belegung nicht gefunden"
        )
    if occupancy.bed_id != bed_id:
        raise HTTPException(
            status_code=404,
            detail="Belegung gehört nicht zu diesem Bett",
        )
    if grund:
        import logging as _logging
        _logging.getLogger("capacity").info(
            "Ausbuchen: occ=%s azr_id=%s grund=%s", occupancy_id, occupancy.azr_id, grund
        )
    await occ_repo.delete(occupancy_id)
    return {"ended": True, "grund": grund}


# ---------------------------------------------------------------------------
# Labels
# ---------------------------------------------------------------------------


@router.get("/labels", response_model=LabelCatalogResponse)
async def get_labels(session: AsyncSession = Depends(get_session)):
    """
    Gibt den vordefinierten Label-Katalog zurück, ergänzt um alle aktuell
    in der DB verwendeten Labels (rooms, beds, occupants).
    """
    result_rooms = await session.execute(
        text("SELECT DISTINCT unnest(labels) AS label FROM capacity.rooms")
    )
    result_beds = await session.execute(
        text("SELECT DISTINCT unnest(labels) AS label FROM capacity.beds")
    )
    result_occ = await session.execute(
        text("SELECT DISTINCT unnest(labels) AS label FROM persons.occupants")
    )

    in_use = set()
    for row in result_rooms.mappings().all():
        in_use.add(row["label"])
    for row in result_beds.mappings().all():
        in_use.add(row["label"])
    for row in result_occ.mappings().all():
        in_use.add(row["label"])

    catalog_names = {entry["name"] for entry in LABEL_CATALOG}
    catalog_entries = [LabelCatalogEntry(**entry) for entry in LABEL_CATALOG]

    # Add any in-use labels not yet in the predefined catalog as generic entries
    for label in sorted(in_use):
        if label not in catalog_names:
            catalog_entries.append(LabelCatalogEntry(
                name=label,
                category="Sonstige",
                entity_types=["ROOM", "BED", "OCCUPANCY"],
                color="#757575",
            ))

    return LabelCatalogResponse(items=catalog_entries)


@router.patch("/rooms/{room_id}/labels", status_code=200)
async def set_room_labels(
    room_id: UUID,
    body: LabelsUpdateRequest,
    session: AsyncSession = Depends(get_session),
):
    """Setzt die Labels eines Raums (vollständiges Ersetzen)."""
    result = await session.execute(
        text("UPDATE capacity.rooms SET labels = CAST(:labels AS TEXT[]) WHERE id = :id RETURNING id"),
        {"labels": body.labels, "id": str(room_id)},
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Raum nicht gefunden")
    return {"labels": body.labels}


@router.patch("/beds/{bed_id}/labels", status_code=200)
async def set_bed_labels(
    bed_id: UUID,
    body: LabelsUpdateRequest,
    session: AsyncSession = Depends(get_session),
):
    """Setzt die Labels eines Betts (vollständiges Ersetzen)."""
    result = await session.execute(
        text("UPDATE capacity.beds SET labels = CAST(:labels AS TEXT[]) WHERE id = :id RETURNING id"),
        {"labels": body.labels, "id": str(bed_id)},
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Bett nicht gefunden")
    return {"labels": body.labels}


@router.patch("/occupancy/{occupancy_id}/labels", status_code=200)
async def set_occupancy_labels(
    occupancy_id: UUID,
    body: LabelsUpdateRequest,
    session: AsyncSession = Depends(get_session),
):
    """Setzt die Labels einer Belegung (vollständiges Ersetzen)."""
    result = await session.execute(
        text("UPDATE persons.occupants SET labels = CAST(:labels AS TEXT[]) WHERE id = :id RETURNING id"),
        {"labels": body.labels, "id": str(occupancy_id)},
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Belegung nicht gefunden")
    return {"labels": body.labels}
