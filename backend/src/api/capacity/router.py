"""
FastAPI APIRouter für alle Kapazitäts-CRUD-Endpoints.

Schichtentrennung:
- Router: HTTP ↔ Pydantic Schemas, Session-Dependency, Domain-Error → HTTP 422
- Repos: DB-Zugriff, Audit-Log
- Domain-Rules: reine Logik ohne I/O
"""
from collections import defaultdict
from datetime import date, datetime, timezone
from typing import List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.adapters.db.capacity_repo import (
    SqlBedRepo,
    SqlLocationRepo,
    SqlOccupancyRepo,
    SqlRoomRepo,
    SqlSystemSettingsRepo,
)
from src.adapters.db.engine import AsyncSessionFactory
from src.adapters.db.models import LocationModel
from src.adapters.keycloak.jwt import get_current_user
from src.api.capacity.schemas import (
    BedCreate,
    BedResponse,
    BedStatusItem,
    EuQuotaUpdate,
    LocationCreate,
    LocationResponse,
    LocationSummaryResponse,
    LocationUpdate,
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
    )


@router.get("/locations", response_model=List[LocationResponse])
async def list_locations(
    include_inactive: bool = False,
    session: AsyncSession = Depends(get_session),
):
    """Listet alle aktiven Einrichtungen. Mit ?include_inactive=true auch inaktive."""
    repo = SqlLocationRepo(session)
    if include_inactive:
        locations = await repo.list_all()
    else:
        locations = await repo.list_active()
    return [
        LocationResponse(
            id=loc.id,
            name=loc.name,
            adresse=loc.adresse,
            kontingent=loc.kontingent,
            notbett_kapazitaet=loc.notbett_kapazitaet,
            is_active=loc.is_active,
        )
        for loc in locations
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
                GROUP BY l.id, l.name, l.kontingent, l.notbett_kapazitaet, l.is_active
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
        )
        for row in rows
    ]


@router.get("/locations/{location_id}", response_model=LocationResponse)
async def get_location(
    location_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """Gibt eine einzelne Einrichtung zurück."""
    repo = SqlLocationRepo(session)
    loc = await repo.get_by_id(location_id)
    if not loc:
        raise HTTPException(status_code=404, detail="Location nicht gefunden")
    return LocationResponse(
        id=loc.id,
        name=loc.name,
        adresse=loc.adresse,
        kontingent=loc.kontingent,
        notbett_kapazitaet=loc.notbett_kapazitaet,
        is_active=loc.is_active,
    )


@router.patch("/locations/{location_id}", response_model=LocationResponse, status_code=200)
async def update_location(
    location_id: UUID,
    body: LocationUpdate,
    session: AsyncSession = Depends(get_session),
):
    """Aktualisiert Kontingent, Notbett-Kapazität oder Adresse einer Einrichtung."""
    repo = SqlLocationRepo(session)
    loc = await repo.get_by_id(location_id)
    if not loc:
        raise HTTPException(status_code=404, detail="Location nicht gefunden")
    result = await session.execute(
        select(LocationModel).where(LocationModel.id == location_id)
    )
    model = result.scalar_one()
    if body.kontingent is not None:
        model.kontingent = body.kontingent
    if body.notbett_kapazitaet is not None:
        model.notbett_kapazitaet = body.notbett_kapazitaet
    if body.adresse is not None:
        model.adresse = body.adresse
    model.updated_at = datetime.now(timezone.utc)
    return LocationResponse(
        id=model.id,
        name=model.name,
        adresse=model.adresse,
        kontingent=model.kontingent,
        notbett_kapazitaet=model.notbett_kapazitaet,
        is_active=model.is_active,
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
              b.id        AS bed_id,
              b.bett_nummer,
              b.bett_typ,
              CASE WHEN o.id IS NOT NULL THEN 'BELEGT' ELSE 'FREI' END AS status,
              o.id        AS occupancy_id,
              o.azr_id,
              o.alias_id,
              o.geschlecht AS occ_geschlecht,
              o.belegung_start,
              o.belegung_ende,
              (
                SELECT COUNT(*) FROM reservations.requests req
                WHERE req.target_location_id = r.location_id
                  AND req.status = 'PENDING'
                  AND (req.geschlecht = r.geschlechts_designation
                       OR r.geschlechts_designation = 'D')
              ) AS pending_count
            FROM capacity.rooms r
            JOIN capacity.beds b ON b.room_id = r.id AND b.is_active = true
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
                "beds": [],
                "pending_count": int(row.get("pending_count") or 0),
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
        ))
    return [RoomBedStatus(**rooms_map[rid]) for rid in rooms_order]


@router.get("/occupants/search")
async def search_occupants(
    q: Optional[str] = None,
    azr_id: Optional[str] = None,
    alias_id: Optional[str] = None,
):
    """
    Sucht nach Belegungen anhand von AZR-ID, Alias-ID oder freitext (q).
    Gibt Bett, Raum, Einrichtung und Belegungszeitraum zurück.
    """
    search_term = q or azr_id or alias_id
    if not search_term:
        return []
    term = f"%{search_term.strip()}%"
    async with AsyncSessionFactory() as session:
        result = await session.execute(text("""
            SELECT
              o.id          AS occupancy_id,
              o.azr_id,
              o.alias_id,
              o.geschlecht,
              o.belegung_start,
              o.belegung_ende,
              b.id          AS bed_id,
              b.bett_nummer,
              b.bett_typ,
              r.id          AS room_id,
              r.name        AS room_name,
              r.geschlechts_designation,
              l.id          AS location_id,
              l.name        AS location_name
            FROM persons.occupants o
            JOIN capacity.beds b ON b.id = o.bed_id AND b.is_active = true
            JOIN capacity.rooms r ON r.id = b.room_id AND r.is_active = true
            JOIN capacity.locations l ON l.id = r.location_id AND l.is_active = true
            WHERE (o.azr_id ILIKE :term OR o.alias_id ILIKE :term)
              AND o.belegung_ende >= CURRENT_DATE
            ORDER BY o.belegung_ende ASC
            LIMIT 50
        """), {"term": term})
        rows = result.mappings().all()
    return [dict(row) for row in rows]


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
    await repo.deactivate(room_id)
    return {"deactivated": True}


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


@router.delete("/beds/{bed_id}/occupancy/{occupancy_id}", status_code=200)
async def end_occupancy(
    bed_id: UUID,
    occupancy_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """
    Beendet eine aktive Belegung — physisches Löschen aus persons.occupants.
    Erzeugt Audit-Eintrag occupancy.ended.
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
    await occ_repo.delete(occupancy_id)
    return {"ended": True}
