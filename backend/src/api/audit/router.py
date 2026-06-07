"""
Audit-Log API: gefiltertes Listing, CSV-Export (Streaming), DSGVO-Löschung.
Zugriff: GET-Endpoints für location-admin+, DELETE nur location-admin+/system-admin.
"""
import csv
import io
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func, text, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.adapters.db.engine import AsyncSessionFactory
from src.adapters.db.models import AuditEventModel
from src.adapters.keycloak.jwt import UserContext, get_current_user
from src.api.audit.schemas import AuditEntryOut, AuditListResponse

router = APIRouter(tags=["audit"])


async def _get_session():
    async with AsyncSessionFactory() as session:
        async with session.begin():
            yield session


def _require_location_admin(user: UserContext) -> None:
    if not ({"location-admin", "system-admin"} & set(user.roles)):
        raise HTTPException(status_code=403, detail="Zugriff nur für location-admin oder system-admin")


def _require_system_admin(user: UserContext) -> None:
    if "system-admin" not in user.roles:
        raise HTTPException(status_code=403, detail="Zugriff nur für system-admin")


def _event_type_pattern(raw: str) -> str:
    """Konvertiert Wildcard-Eingabe (*) in SQL-ILIKE-Pattern (%)."""
    return raw.replace("*", "%") if raw else "%"


def _build_filters(
    date_from: Optional[datetime],
    date_to: Optional[datetime],
    azr_id: Optional[str],
    event_type: Optional[str],
    location_id: Optional[UUID],
):
    conditions = []
    if date_from:
        conditions.append(AuditEventModel.created_at >= date_from)
    if date_to:
        conditions.append(AuditEventModel.created_at <= date_to)
    if azr_id:
        conditions.append(AuditEventModel.entity_id == azr_id)
    if event_type:
        # ILIKE: case-insensitiv + Wildcard-Support via *→%
        conditions.append(AuditEventModel.event_type.ilike(_event_type_pattern(event_type)))
    if location_id:
        conditions.append(AuditEventModel.location_id == location_id)
    return conditions


async def _enrich_entries(
    session: AsyncSession,
    rows: list,
) -> List[AuditEntryOut]:
    """
    Reichert Audit-Einträge mit fachlichen Namen an:
    - location_id → location_name (Einrichtungsname)
    - payload.requester_location_id / target_location_id → *_name
    - payload.bed_id / confirmed_bed_id → *_info (Raum / Bettnummer)
    - payload.room_id → room_name
    """
    # 1. Alle zu auflösenden IDs sammeln
    loc_ids: set[str] = set()
    bed_ids: set[str] = set()
    room_ids: set[str] = set()

    for row in rows:
        if row.location_id:
            loc_ids.add(str(row.location_id))
        payload = row.payload or {}
        for key in ("requester_location_id", "target_location_id"):
            val = payload.get(key)
            if val:
                loc_ids.add(str(val))
        for key in ("bed_id", "confirmed_bed_id"):
            val = payload.get(key)
            if val:
                bed_ids.add(str(val))
        val = payload.get("room_id")
        if val:
            room_ids.add(str(val))

    # 2. Batch-Auflösung Einrichtungsnamen
    loc_name_map: dict[str, str] = {}
    if loc_ids:
        result = await session.execute(
            text(
                "SELECT id::text, name FROM capacity.locations "
                "WHERE id::text = ANY(:ids)"
            ),
            {"ids": list(loc_ids)},
        )
        loc_name_map = {r.id: r.name for r in result.fetchall()}

    # 3. Batch-Auflösung Bettinfos
    bed_info_map: dict[str, str] = {}
    if bed_ids:
        result = await session.execute(
            text(
                "SELECT b.id::text, b.bett_nummer, r.name AS room_name "
                "FROM capacity.beds b "
                "JOIN capacity.rooms r ON r.id = b.room_id "
                "WHERE b.id::text = ANY(:ids)"
            ),
            {"ids": list(bed_ids)},
        )
        bed_info_map = {r.id: f"{r.room_name} / Bett {r.bett_nummer}" for r in result.fetchall()}

    # 4. Batch-Auflösung Raumname (für historische Einträge ohne room_name im Payload)
    room_name_map: dict[str, str] = {}
    if room_ids:
        result = await session.execute(
            text("SELECT id::text, name FROM capacity.rooms WHERE id::text = ANY(:ids)"),
            {"ids": list(room_ids)},
        )
        room_name_map = {r.id: r.name for r in result.fetchall()}

    # 5. Einträge anreichern
    items: List[AuditEntryOut] = []
    for row in rows:
        entry = AuditEntryOut.model_validate(row.__dict__)

        # location_name für die Audit-Einrichtungsspalte
        if row.location_id:
            entry.location_name = loc_name_map.get(str(row.location_id))

        # Payload anreichern
        if entry.payload:
            enriched: dict = dict(entry.payload)
            for key in ("requester_location_id", "target_location_id"):
                if key in enriched:
                    name = loc_name_map.get(str(enriched[key]))
                    if name:
                        enriched[key.replace("_id", "_name")] = name
            for key in ("bed_id", "confirmed_bed_id"):
                if key in enriched:
                    info = bed_info_map.get(str(enriched[key]))
                    if info:
                        enriched[key.replace("_id", "_info")] = info
            if "room_id" in enriched and "room_name" not in enriched:
                rname = room_name_map.get(str(enriched["room_id"]))
                if rname:
                    enriched["room_name"] = rname
            entry.payload = enriched

        items.append(entry)

    return items


@router.get("/audit/event-types", response_model=List[str])
async def list_event_types(
    session: AsyncSession = Depends(_get_session),
    user: UserContext = Depends(get_current_user),
):
    """Gibt alle im Log vorhandenen Event-Typen zurück (für Filter-Dropdown)."""
    result = await session.execute(
        text("SELECT DISTINCT event_type FROM audit.events ORDER BY event_type")
    )
    return [r.event_type for r in result.fetchall()]


@router.get("/audit", response_model=AuditListResponse)
async def list_audit(
    date_from: Optional[datetime] = Query(None, description="Von (ISO-8601), default: letzte 5 Tage"),
    date_to: Optional[datetime] = Query(None),
    azr_id: Optional[str] = Query(None, description="AZR-ID oder Alias für DSGVO-Suche"),
    event_type: Optional[str] = Query(None, description="Event-Typ, Wildcard * möglich, case-insensitiv"),
    location_id: Optional[UUID] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    session: AsyncSession = Depends(_get_session),
    user: UserContext = Depends(get_current_user),
):
    """Paginiertes Audit-Log mit fachlicher Anreicherung. Default: letzte 5 Tage."""
    if date_from is None and azr_id is None:
        date_from = datetime.now(timezone.utc) - timedelta(days=5)

    conditions = _build_filters(date_from, date_to, azr_id, event_type, location_id)

    total_q = select(func.count()).select_from(AuditEventModel)
    if conditions:
        total_q = total_q.where(and_(*conditions))
    total_result = await session.execute(total_q)
    total = total_result.scalar_one()

    items_q = select(AuditEventModel).order_by(AuditEventModel.created_at.desc())
    if conditions:
        items_q = items_q.where(and_(*conditions))
    items_q = items_q.offset((page - 1) * page_size).limit(page_size)
    rows_result = await session.execute(items_q)
    rows = list(rows_result.scalars().all())

    items = await _enrich_entries(session, rows)

    return AuditListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/audit/export.csv")
async def export_audit_csv(
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    azr_id: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    location_id: Optional[UUID] = Query(None),
    user: UserContext = Depends(get_current_user),
):
    """
    Streaming-CSV-Export des Audit-Logs für den aktiven Filter.
    Nur location-admin oder system-admin dürfen exportieren.
    """
    _require_location_admin(user)

    if date_from is None and azr_id is None:
        date_from = datetime.now(timezone.utc) - timedelta(days=5)

    where_parts = []
    params: dict = {}
    if date_from:
        where_parts.append("created_at >= :date_from")
        params["date_from"] = date_from
    if date_to:
        where_parts.append("created_at <= :date_to")
        params["date_to"] = date_to
    if azr_id:
        where_parts.append("entity_id = :azr_id")
        params["azr_id"] = azr_id
    if event_type:
        where_parts.append("event_type ILIKE :event_type")
        params["event_type"] = _event_type_pattern(event_type)
    if location_id:
        where_parts.append("location_id = :location_id")
        params["location_id"] = str(location_id)

    where_sql = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""
    query_sql = text(
        "SELECT e.created_at, e.event_type, e.actor_id, e.actor_role, "
        "       e.location_id, l.name AS location_name, "
        "       e.entity_type, e.entity_id, e.payload "
        f"FROM audit.events e "
        f"LEFT JOIN capacity.locations l ON l.id = e.location_id "
        f"{where_sql} ORDER BY e.created_at DESC"
    )

    async with AsyncSessionFactory() as session:
        result = await session.execute(query_sql, params)
        rows = result.fetchall()

    def csv_generator():
        yield "timestamp;event_type;actor_id;actor_role;location_id;location_name;entity_type;entity_id;payload\n".encode("utf-8")
        buf = io.StringIO()
        writer = csv.writer(buf, delimiter=";", quoting=csv.QUOTE_MINIMAL)
        for row in rows:
            writer.writerow([
                row.created_at.isoformat() if row.created_at else "",
                row.event_type or "",
                row.actor_id or "",
                row.actor_role or "",
                str(row.location_id) if row.location_id else "",
                row.location_name or "",
                row.entity_type or "",
                row.entity_id or "",
                str(row.payload) if row.payload else "",
            ])
            yield buf.getvalue().encode("utf-8")
            buf.truncate(0)
            buf.seek(0)

    return StreamingResponse(
        csv_generator(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=audit.csv"},
    )


@router.delete("/audit/azr/{azr_id}", status_code=200)
async def delete_audit_for_azr(
    azr_id: str,
    confirm: bool = Query(False, description="Sicherheitsbestätigung erforderlich"),
    session: AsyncSession = Depends(_get_session),
    user: UserContext = Depends(get_current_user),
):
    """
    DSGVO-Löschung: entfernt alle Audit-Einträge zur angegebenen AZR-ID.
    Erfordert ?confirm=true und Rolle location-admin oder system-admin.
    """
    _require_location_admin(user)
    if not confirm:
        raise HTTPException(status_code=400, detail="Sicherheitsbestätigung erforderlich: ?confirm=true")
    if not azr_id:
        raise HTTPException(status_code=400, detail="azr_id darf nicht leer sein")

    result = await session.execute(
        text(
            "DELETE FROM audit.events "
            "WHERE entity_id = :azr_id "
            "   OR (entity_id IS NULL AND payload->>'azr_id' = :azr_id)"
        ),
        {"azr_id": azr_id},
    )
    await session.flush()
    return {"deleted": result.rowcount, "azr_id": azr_id}


@router.delete("/audit/purge-old", status_code=200)
async def purge_old_audit(
    session: AsyncSession = Depends(_get_session),
    user: UserContext = Depends(get_current_user),
):
    """
    Löscht alle Audit-Einträge älter als 10 Jahre. Nur system-admin.
    """
    _require_system_admin(user)
    result = await session.execute(
        text("DELETE FROM audit.events WHERE created_at < NOW() - INTERVAL '10 years'")
    )
    await session.flush()
    return {"deleted": result.rowcount}
