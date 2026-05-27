"""
FastAPI APIRouter für alle Reservierungs-Endpoints.
Schichtentrennung: Router → Repo → Domain-Rules.

system-admin: X-Location-Id Header optional — alle Reservierungen sichtbar, Stornieren immer erlaubt.
location-admin / writer: X-Location-Id Pflicht — nur eigene Einrichtung sichtbar.
"""
from typing import List, Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.adapters.db.engine import AsyncSessionFactory
from src.adapters.db.models import LocationModel
from src.adapters.db.reservation_repo import SqlReservationRepo
from src.adapters.keycloak.jwt import UserContext, get_current_user
from src.api.reservations.schemas import ReservationCreate, ReservationResponse
from src.domain.reservations.rules import (
    InvalidStateTransitionError,
    RetractionForbiddenError,
)

router = APIRouter(tags=["reservations"])


async def _get_session():
    async with AsyncSessionFactory() as session:
        async with session.begin():
            yield session


async def _resolve_location(
    request: Request,
    user: UserContext,
    session: AsyncSession,
) -> Optional[LocationModel]:
    """
    Liest X-Location-Id aus Header.
    system-admin: Header optional → None zurückgeben wenn nicht vorhanden.
    Alle anderen: Header Pflicht → 422 wenn fehlt.
    """
    x_location_id_str = request.headers.get("X-Location-Id")
    is_system_admin = "system-admin" in user.roles

    if not x_location_id_str:
        if is_system_admin:
            return None
        raise HTTPException(status_code=422, detail="X-Location-Id Header erforderlich")

    try:
        loc_id = UUID(x_location_id_str)
    except ValueError:
        raise HTTPException(status_code=422, detail="Ungültige X-Location-Id")

    result = await session.execute(select(LocationModel).where(LocationModel.id == loc_id))
    loc = result.scalar_one_or_none()
    if not loc or not loc.is_active:
        raise HTTPException(status_code=403, detail="Location nicht gefunden oder inaktiv")
    return loc


@router.post("/reservations", status_code=201)
async def create_reservation(
    request: Request,
    body: ReservationCreate,
    user: UserContext = Depends(get_current_user),
    session: AsyncSession = Depends(_get_session),
) -> ReservationResponse:
    """Erstellt eine Reservierungsanfrage. Requester und Target dürfen nicht gleich sein."""
    location = await _resolve_location(request, user, session)
    if location is None:
        raise HTTPException(status_code=422, detail="system-admin benötigt X-Location-Id zum Erstellen einer Anfrage")
    if body.target_location_id == location.id:
        raise HTTPException(status_code=422, detail="Requester und Target dürfen nicht gleich sein")
    target_loc_row = await session.execute(
        text("SELECT valid_from, valid_until FROM capacity.locations WHERE id = :id"),
        {"id": str(body.target_location_id)},
    )
    target_row = target_loc_row.fetchone()
    if target_row:
        if target_row.valid_from and body.belegung_start < target_row.valid_from:
            raise HTTPException(status_code=409, detail=f"Einrichtung ist erst ab {target_row.valid_from} aktiv")
        if target_row.valid_until and body.belegung_start >= target_row.valid_until:
            raise HTTPException(status_code=409, detail=f"Einrichtung ist ab {target_row.valid_until} inaktiv")
    repo = SqlReservationRepo(session)
    req = await repo.create(body, requester_location_id=location.id)
    return ReservationResponse.model_validate(req)


@router.get("/reservations")
async def list_reservations(
    request: Request,
    status: Optional[Literal["PENDING", "CONFIRMED", "REJECTED", "CANCELLED", "TRANSFERRED"]] = None,
    target: Optional[str] = None,
    user: UserContext = Depends(get_current_user),
    session: AsyncSession = Depends(_get_session),
) -> List[ReservationResponse]:
    """
    Listet Reservierungen.
    system-admin ohne X-Location-Id: alle Reservierungen aller Einrichtungen.
    Alle anderen: nur eigene Einrichtung.
    ?target=mine — nur PENDING-Anfragen bei denen die eigene Einrichtung Ziel ist.
    ?status=... — filtert nach Status.
    """
    location = await _resolve_location(request, user, session)
    repo = SqlReservationRepo(session)

    is_system_admin = "system-admin" in user.roles
    if location is None and is_system_admin:
        results = await repo.list_all(status_filter=status)
    elif target == "mine" and location:
        results = await repo.list_pending_for_target(location.id)
    else:
        results = await repo.list_for_location(location.id, status_filter=status)  # type: ignore[union-attr]
    return [ReservationResponse.model_validate(r) for r in results]


@router.delete("/reservations/{reservation_id}")
async def cancel_reservation(
    reservation_id: UUID,
    request: Request,
    user: UserContext = Depends(get_current_user),
    session: AsyncSession = Depends(_get_session),
) -> ReservationResponse:
    """
    Bricht eine Reservierung ab (→ CANCELLED).
    system-admin: darf immer stornieren.
    Alle anderen: nur wenn X-Location-Id die anfragende Einrichtung ist (requester).
    """
    location = await _resolve_location(request, user, session)
    is_system_admin = "system-admin" in user.roles
    repo = SqlReservationRepo(session)
    try:
        result = await repo.update_status(
            reservation_id,
            "CANCELLED",
            location_id=location.id if location else None,
            is_system_admin=is_system_admin,
        )
    except RetractionForbiddenError as e:
        raise HTTPException(status_code=403, detail=e.message)
    except InvalidStateTransitionError as e:
        raise HTTPException(status_code=409, detail=e.message)
    return ReservationResponse.model_validate(result)


@router.post("/reservations/{reservation_id}/confirm")
async def confirm_reservation(
    reservation_id: UUID,
    request: Request,
    user: UserContext = Depends(get_current_user),
    session: AsyncSession = Depends(_get_session),
) -> ReservationResponse:
    """
    Bestätigt eine Reservierung (→ CONFIRMED).
    system-admin: darf immer bestätigen.
    Alle anderen: nur wenn X-Location-Id die Zieleinrichtung ist.
    """
    location = await _resolve_location(request, user, session)
    is_system_admin = "system-admin" in user.roles
    repo = SqlReservationRepo(session)
    try:
        if is_system_admin and location is None:
            # system-admin ohne location: Statusübergang direkt prüfen und ausführen
            result = await repo.update_status(
                reservation_id, "CONFIRMED", is_system_admin=True
            )
        else:
            result = await repo.confirm(reservation_id, location.id)  # type: ignore[union-attr]
    except RetractionForbiddenError as e:
        raise HTTPException(status_code=403, detail=e.message)
    except InvalidStateTransitionError as e:
        raise HTTPException(status_code=409, detail=e.message)
    return ReservationResponse.model_validate(result)


@router.post("/reservations/{reservation_id}/reject")
async def reject_reservation(
    reservation_id: UUID,
    request: Request,
    user: UserContext = Depends(get_current_user),
    session: AsyncSession = Depends(_get_session),
) -> ReservationResponse:
    """
    Lehnt eine Reservierung ab (→ REJECTED).
    system-admin: darf immer ablehnen.
    Alle anderen: nur wenn X-Location-Id die Zieleinrichtung ist.
    """
    location = await _resolve_location(request, user, session)
    is_system_admin = "system-admin" in user.roles
    repo = SqlReservationRepo(session)
    try:
        if is_system_admin and location is None:
            result = await repo.update_status(
                reservation_id, "REJECTED", is_system_admin=True
            )
        else:
            result = await repo.reject(reservation_id, location.id)  # type: ignore[union-attr]
    except RetractionForbiddenError as e:
        raise HTTPException(status_code=403, detail=e.message)
    except InvalidStateTransitionError as e:
        raise HTTPException(status_code=409, detail=e.message)
    return ReservationResponse.model_validate(result)
