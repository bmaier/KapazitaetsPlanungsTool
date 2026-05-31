from datetime import date, timedelta
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.adapters.db.engine import AsyncSessionFactory
from src.adapters.keycloak.jwt import UserContext, get_current_user
from src.api.statistics.schemas import KpiResponse, OccupancyDataPoint, StatisticsResponse

router = APIRouter(tags=["statistics"])


async def get_session():
    async with AsyncSessionFactory() as session:
        async with session.begin():
            yield session


@router.get("/statistics/occupancy", response_model=StatisticsResponse)
async def get_occupancy_statistics(
    location_id: UUID,
    date_from: date,
    date_to: date,
    granularity: Literal["day", "week", "month"] = "day",
    user: UserContext = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    if date_from > date_to:
        raise HTTPException(status_code=422, detail="date_from muss vor date_to liegen")

    if "system-admin" not in user.roles and user.location_id != str(location_id):
        raise HTTPException(status_code=403, detail="Zugriff auf diese Einrichtung nicht erlaubt")

    # Belegungshistorie via generate_series
    belegung_result = await session.execute(
        text("""
            WITH series AS (
                SELECT gs::date AS day
                FROM generate_series(
                    :date_from::date,
                    :date_to::date,
                    ('1 ' || :granularity)::interval
                ) gs
            ),
            occ_data AS (
                SELECT o.id, o.belegung_start, o.belegung_ende, b.bett_typ
                FROM persons.occupants o
                JOIN capacity.beds b ON b.id = o.bed_id AND b.is_active = true
                JOIN capacity.rooms r ON r.id = b.room_id AND r.is_active = true
                WHERE r.location_id = :location_id::uuid
            )
            SELECT
                s.day,
                COUNT(DISTINCT occ.id) FILTER (
                    WHERE occ.belegung_start <= s.day AND occ.belegung_ende > s.day
                ) AS belegt,
                COUNT(DISTINCT occ.id) FILTER (
                    WHERE occ.belegung_start <= s.day
                      AND occ.belegung_ende > s.day
                      AND occ.bett_typ = 'NOTBETT'
                ) AS notbetten_belegt
            FROM series s
            LEFT JOIN occ_data occ ON true
            GROUP BY s.day
            ORDER BY s.day
        """),
        {
            "date_from": date_from,
            "date_to": date_to,
            "granularity": granularity,
            "location_id": str(location_id),
        },
    )
    rows = belegung_result.mappings().all()

    # Kontingent History (aufsteigend sortiert für lineare Suche)
    history_result = await session.execute(
        text("""
            SELECT kontingent_value, valid_from::date AS valid_from
            FROM capacity.kontingent_history
            WHERE location_id = :location_id::uuid
            ORDER BY valid_from ASC
        """),
        {"location_id": str(location_id)},
    )
    history = history_result.mappings().all()

    # Aktuelles Kontingent als Fallback
    loc_result = await session.execute(
        text("SELECT kontingent FROM capacity.locations WHERE id = :location_id::uuid"),
        {"location_id": str(location_id)},
    )
    loc_row = loc_result.fetchone()
    current_kontingent = loc_row.kontingent if loc_row else 0

    # Datenpunkte zusammenbauen
    data: list[OccupancyDataPoint] = []
    for row in rows:
        day: date = row["day"]
        belegt = int(row["belegt"] or 0)
        notbetten_belegt = int(row["notbetten_belegt"] or 0)

        # Letzten History-Eintrag mit valid_from <= day finden
        kontingent = current_kontingent
        for h in history:
            if h["valid_from"] <= day:
                kontingent = h["kontingent_value"]
            else:
                break

        frei = max(0, kontingent - belegt)
        belegungsgrad_pct = round(belegt * 100.0 / kontingent, 1) if kontingent > 0 else 0.0

        data.append(
            OccupancyDataPoint(
                date=str(day),
                belegt=belegt,
                frei=frei,
                notbetten_belegt=notbetten_belegt,
                kontingent=kontingent,
                belegungsgrad_pct=belegungsgrad_pct,
            )
        )

    # KPIs berechnen
    today_str = str(date.today())
    today_point = next((d for d in data if d.date == today_str), None)
    aktuell_pct = today_point.belegungsgrad_pct if today_point else (data[-1].belegungsgrad_pct if data else 0.0)

    cutoff_30 = str(date.today() - timedelta(days=30))
    last_30 = [d for d in data if d.date >= cutoff_30]
    avg30t_pct = round(sum(d.belegungsgrad_pct for d in last_30) / len(last_30), 1) if last_30 else 0.0

    trend_delta_pct = round(data[-1].belegungsgrad_pct - data[0].belegungsgrad_pct, 1) if len(data) >= 2 else 0.0

    return StatisticsResponse(
        data=data,
        kpis=KpiResponse(
            aktuell_pct=aktuell_pct,
            avg30t_pct=avg30t_pct,
            trend_delta_pct=trend_delta_pct,
        ),
    )


@router.get("/statistics/kpis", response_model=KpiResponse)
async def get_kpis(
    location_id: UUID,
    user: UserContext = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    if "system-admin" not in user.roles and user.location_id != str(location_id):
        raise HTTPException(status_code=403, detail="Zugriff auf diese Einrichtung nicht erlaubt")

    today = date.today()
    date_from = today - timedelta(days=30)

    result = await get_occupancy_statistics(
        location_id=location_id,
        date_from=date_from,
        date_to=today,
        granularity="day",
        user=user,
        session=session,
    )
    return result.kpis
