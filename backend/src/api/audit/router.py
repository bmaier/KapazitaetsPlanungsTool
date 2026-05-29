"""
Audit-Log API: gefiltertes Listing, CSV-Export (Streaming), DSGVO-Löschung.
Zugriff: GET-Endpoints für location-admin+, DELETE nur location-admin+/system-admin.
"""
import csv
import io
from datetime import datetime, timedelta, timezone
from typing import Optional
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
        conditions.append(AuditEventModel.event_type == event_type)
    if location_id:
        conditions.append(AuditEventModel.location_id == location_id)
    return conditions


@router.get("/audit", response_model=AuditListResponse)
async def list_audit(
    date_from: Optional[datetime] = Query(None, description="Von (ISO-8601), default: letzte 5 Tage"),
    date_to: Optional[datetime] = Query(None),
    azr_id: Optional[str] = Query(None, description="AZR-ID oder Alias für DSGVO-Suche"),
    event_type: Optional[str] = Query(None),
    location_id: Optional[UUID] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    session: AsyncSession = Depends(_get_session),
    user: UserContext = Depends(get_current_user),
):
    """Paginiertes Audit-Log. Default: letzte 5 Tage. Filterbar nach AZR, Event-Typ, Standort."""
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
    rows = await session.execute(items_q)
    items = [AuditEntryOut.model_validate(r.__dict__) for r in rows.scalars().all()]

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
        where_parts.append("event_type = :event_type")
        params["event_type"] = event_type
    if location_id:
        where_parts.append("location_id = :location_id")
        params["location_id"] = str(location_id)

    where_sql = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""
    query_sql = text(
        f"SELECT created_at, event_type, actor_id, actor_role, location_id, entity_type, entity_id, payload "
        f"FROM audit.events {where_sql} ORDER BY created_at DESC"
    )

    async def csv_generator():
        header = "timestamp;event_type;actor_id;actor_role;location_id;entity_type;entity_id;payload\n"
        yield header.encode()
        async with AsyncSessionFactory() as session:
            result = await session.execute(query_sql, params, execution_options={"stream_results": True})
            while True:
                chunk = result.fetchmany(500)
                if not chunk:
                    break
                buf = io.StringIO()
                writer = csv.writer(buf, delimiter=";", quoting=csv.QUOTE_MINIMAL)
                for row in chunk:
                    writer.writerow([
                        row.created_at.isoformat() if row.created_at else "",
                        row.event_type or "",
                        row.actor_id or "",
                        row.actor_role or "",
                        str(row.location_id) if row.location_id else "",
                        row.entity_type or "",
                        row.entity_id or "",
                        str(row.payload) if row.payload else "",
                    ])
                yield buf.getvalue().encode()

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
