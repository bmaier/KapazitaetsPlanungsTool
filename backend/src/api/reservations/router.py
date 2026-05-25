"""
FastAPI APIRouter für alle Reservierungs-Endpoints.
Schichtentrennung: Router → Repo → Domain-Rules.
get_location_context erzwingt X-Location-Id-Header und Einrichtungsvalidierung.
"""
from typing import List, Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.adapters.db.engine import AsyncSessionFactory
from src.adapters.db.models import LocationModel
from src.adapters.db.reservation_repo import SqlReservationRepo
from src.adapters.keycloak.jwt import get_location_context
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


@router.post("/reservations", status_code=201)
async def create_reservation(
    body: ReservationCreate,
    location: LocationModel = Depends(get_location_context),
    session: AsyncSession = Depends(_get_session),
) -> ReservationResponse:
    """Erstellt eine Reservierungsanfrage. Requester und Target dürfen nicht gleich sein."""
    if body.target_location_id == location.id:
        raise HTTPException(
            status_code=422,
            detail="Requester und Target dürfen nicht gleich sein",
        )
    repo = SqlReservationRepo(session)
    req = await repo.create(body, requester_location_id=location.id)
    return ReservationResponse.model_validate(req)


@router.get("/reservations")
async def list_reservations(
    status: Optional[Literal["PENDING", "CONFIRMED", "REJECTED", "CANCELLED", "TRANSFERRED"]] = None,
    target: Optional[str] = None,
    location: LocationModel = Depends(get_location_context),
    session: AsyncSession = Depends(_get_session),
) -> List[ReservationResponse]:
    """
    Listet Reservierungen der eigenen Einrichtung.
    ?target=mine — nur PENDING-Anfragen bei denen die eigene Einrichtung Ziel ist (FCFS-sortiert).
    ?status=PENDING|CONFIRMED|... — filtert nach Status.
    """
    repo = SqlReservationRepo(session)
    if target == "mine":
        results = await repo.list_pending_for_target(location.id)
    else:
        results = await repo.list_for_location(location.id, status_filter=status)
    return [ReservationResponse.model_validate(r) for r in results]


@router.delete("/reservations/{reservation_id}")
async def cancel_reservation(
    reservation_id: UUID,
    location: LocationModel = Depends(get_location_context),
    session: AsyncSession = Depends(_get_session),
) -> ReservationResponse:
    """
    Bricht eine Reservierung ab (→ CANCELLED).
    HTTP 403 wenn X-Location-Id weder Requester noch Target ist.
    HTTP 409 bei ungültigem Statusübergang (z.B. TRANSFERRED → CANCELLED).
    """
    repo = SqlReservationRepo(session)
    try:
        result = await repo.update_status(reservation_id, "CANCELLED", location.id)
    except RetractionForbiddenError as e:
        raise HTTPException(status_code=403, detail=e.message)
    except InvalidStateTransitionError as e:
        raise HTTPException(status_code=409, detail=e.message)
    return ReservationResponse.model_validate(result)


@router.post("/reservations/{reservation_id}/confirm")
async def confirm_reservation(
    reservation_id: UUID,
    location: LocationModel = Depends(get_location_context),
    session: AsyncSession = Depends(_get_session),
) -> ReservationResponse:
    """
    Bestätigt eine Reservierung (→ CONFIRMED).
    HTTP 403 wenn X-Location-Id nicht die Zieleinrichtung ist.
    HTTP 409 bei ungültigem Statusübergang.
    """
    repo = SqlReservationRepo(session)
    try:
        result = await repo.confirm(reservation_id, location.id)
    except RetractionForbiddenError as e:
        raise HTTPException(status_code=403, detail=e.message)
    except InvalidStateTransitionError as e:
        raise HTTPException(status_code=409, detail=e.message)
    return ReservationResponse.model_validate(result)


@router.post("/reservations/{reservation_id}/reject")
async def reject_reservation(
    reservation_id: UUID,
    location: LocationModel = Depends(get_location_context),
    session: AsyncSession = Depends(_get_session),
) -> ReservationResponse:
    """
    Lehnt eine Reservierung ab (→ REJECTED).
    HTTP 403 wenn X-Location-Id nicht die Zieleinrichtung ist.
    HTTP 409 bei ungültigem Statusübergang.
    """
    repo = SqlReservationRepo(session)
    try:
        result = await repo.reject(reservation_id, location.id)
    except RetractionForbiddenError as e:
        raise HTTPException(status_code=403, detail=e.message)
    except InvalidStateTransitionError as e:
        raise HTTPException(status_code=409, detail=e.message)
    return ReservationResponse.model_validate(result)
