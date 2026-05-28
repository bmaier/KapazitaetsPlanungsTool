"""
SQLAlchemy-Implementierung des Reservierungs-Repositories.
Kritisch: update_status() nutzt SELECT FOR UPDATE für concurrent-safe Statusübergänge.
Jede Statusänderung erzeugt atomisch Task + Audit-Eintrag in derselben Session.
"""
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID, uuid4

import json

from fastapi import HTTPException
from sqlalchemy import or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.adapters.db.models import OccupantModel, ReservationRequestModel, TaskModel
from src.domain.reservations.entities import ReservationRequest, ReservationStatus
from src.domain.reservations.rules import (
    InvalidStateTransitionError,
    RetractionForbiddenError,
    check_retraction_allowed,
    check_state_transition,
)
from src.domain.tasks.entities import TaskPriority, TaskStatus, TaskType
from src.ports.reservations.repository import AbstractReservationRepo


def _to_entity(model: ReservationRequestModel) -> ReservationRequest:
    return ReservationRequest(
        id=model.id,
        requester_location_id=model.requester_location_id,
        target_location_id=model.target_location_id,
        azr_id=model.azr_id,
        geschlecht=model.geschlecht,
        geburtsjahr=model.geburtsjahr,
        herkunftsland=model.herkunftsland,
        belegung_start=model.belegung_start,
        belegung_ende=model.belegung_ende,
        status=ReservationStatus(model.status),
        confirmed_bed_id=model.confirmed_bed_id,
        confirmed_at=model.confirmed_at,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


class SqlReservationRepo(AbstractReservationRepo):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, body, requester_location_id: UUID) -> ReservationRequest:
        """
        Erstellt eine Reservierung mit Status PENDING.
        Erzeugt Task für target_location (RESERVATION_RECEIVED, HIGH) und Audit-Eintrag.
        """
        now = datetime.now(timezone.utc)
        model = ReservationRequestModel(
            id=uuid4(),
            requester_location_id=requester_location_id,
            target_location_id=body.target_location_id,
            azr_id=body.azr_id,
            geschlecht=body.geschlecht,
            geburtsjahr=body.geburtsjahr,
            herkunftsland=body.herkunftsland,
            belegung_start=body.belegung_start,
            belegung_ende=body.belegung_ende,
            status="PENDING",
            confirmed_bed_id=None,
            created_at=now,
            updated_at=now,
        )
        self._session.add(model)
        await self._session.flush()

        # Task für Zieleinrichtung
        await self._create_task(
            location_id=body.target_location_id,
            reservation_id=model.id,
            task_type=TaskType.RESERVATION_RECEIVED,
            priority=TaskPriority.HIGH,
            title="Neue Reservierungsanfrage",
            body=f"Einrichtung hat eine Reservierungsanfrage für AZR-ID {body.azr_id} gestellt.",
        )

        # Audit
        await self._write_audit(model.id, "CREATED", None)

        return _to_entity(model)

    async def get(self, reservation_id: UUID) -> Optional[ReservationRequest]:
        result = await self._session.execute(
            select(ReservationRequestModel).where(
                ReservationRequestModel.id == reservation_id
            )
        )
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def list_all(self, status_filter: Optional[str] = None) -> List[ReservationRequest]:
        """Alle Reservierungen aller Einrichtungen — nur für system-admin."""
        q = select(ReservationRequestModel)
        if status_filter:
            q = q.where(ReservationRequestModel.status == status_filter)
        q = q.order_by(ReservationRequestModel.created_at.asc())
        result = await self._session.execute(q)
        return [_to_entity(m) for m in result.scalars().all()]

    async def update_status(
        self,
        reservation_id: UUID,
        new_status: str,
        location_id: Optional[UUID] = None,
        is_system_admin: bool = False,
    ) -> ReservationRequest:
        """
        SELECT FOR UPDATE verhindert gleichzeitige Doppel-Bestätigungen.
        Prüft Retraktionsberechtigung und Statusübergang.
        """
        result = await self._session.execute(
            select(ReservationRequestModel)
            .where(ReservationRequestModel.id == reservation_id)
            .with_for_update()
        )
        model = result.scalar_one_or_none()
        if model is None:
            raise HTTPException(status_code=404, detail="Reservierung nicht gefunden")

        # Für CANCELLED: Retraktionsberechtigung prüfen
        if new_status == "CANCELLED":
            entity = _to_entity(model)
            check_retraction_allowed(location_id, entity, is_system_admin=is_system_admin)

        check_state_transition(model.status, new_status)

        model.status = new_status
        model.updated_at = datetime.now(timezone.utc)

        await self._create_task_and_audit(model, new_status, location_id)
        await self._session.flush()
        return _to_entity(model)

    async def confirm(
        self, reservation_id: UUID, location_id: UUID, confirmed_bed_id: UUID
    ) -> ReservationRequest:
        """
        Bestätigt eine Reservierung und weist ein Bett zu (VORGEMERKT).
        Prüft: location_id == target_location_id, Bett gehört zur Einrichtung, keine Überschneidung.
        """
        result = await self._session.execute(
            select(ReservationRequestModel)
            .where(ReservationRequestModel.id == reservation_id)
            .with_for_update()
        )
        model = result.scalar_one_or_none()
        if model is None:
            raise HTTPException(status_code=404, detail="Reservierung nicht gefunden")

        if model.target_location_id != location_id:
            raise RetractionForbiddenError(
                "Nur die Zieleinrichtung kann eine Reservierung bestätigen"
            )

        check_state_transition(model.status, "CONFIRMED")

        # Bett gehört zur Zieleinrichtung und ist aktiv?
        bed_row = await self._session.execute(
            text(
                "SELECT b.id FROM capacity.beds b "
                "JOIN capacity.rooms r ON r.id = b.room_id "
                "WHERE b.id = :bed_id AND r.location_id = :loc_id AND b.is_active = true"
            ),
            {"bed_id": str(confirmed_bed_id), "loc_id": str(location_id)},
        )
        if bed_row.fetchone() is None:
            raise HTTPException(
                status_code=422,
                detail="Bett gehört nicht zu dieser Einrichtung oder ist inaktiv",
            )

        # Kein Occupant im Zeitraum?
        occupant_overlap = await self._session.execute(
            select(OccupantModel).where(
                OccupantModel.bed_id == confirmed_bed_id,
                OccupantModel.belegung_start < model.belegung_ende,
                OccupantModel.belegung_ende > model.belegung_start,
            )
        )
        if occupant_overlap.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=409, detail="Bett ist im gewünschten Zeitraum bereits belegt"
            )

        # Keine andere CONFIRMED-Reservierung für dasselbe Bett im Zeitraum?
        res_overlap = await self._session.execute(
            select(ReservationRequestModel).where(
                ReservationRequestModel.confirmed_bed_id == confirmed_bed_id,
                ReservationRequestModel.status == "CONFIRMED",
                ReservationRequestModel.id != reservation_id,
                ReservationRequestModel.belegung_start < model.belegung_ende,
                ReservationRequestModel.belegung_ende > model.belegung_start,
            )
        )
        if res_overlap.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=409,
                detail="Bett ist bereits für eine andere Reservierung vorgemerkt",
            )

        now = datetime.now(timezone.utc)
        model.status = "CONFIRMED"
        model.confirmed_bed_id = confirmed_bed_id
        model.confirmed_at = now
        model.updated_at = now

        await self._create_task_and_audit(model, "CONFIRMED", location_id)
        await self._session.flush()
        return _to_entity(model)

    async def reject(
        self, reservation_id: UUID, location_id: UUID
    ) -> ReservationRequest:
        """Lehnt eine Reservierung ab — prüft ob location_id == target_location_id."""
        result = await self._session.execute(
            select(ReservationRequestModel)
            .where(ReservationRequestModel.id == reservation_id)
            .with_for_update()
        )
        model = result.scalar_one_or_none()
        if model is None:
            raise HTTPException(status_code=404, detail="Reservierung nicht gefunden")

        if model.target_location_id != location_id:
            raise RetractionForbiddenError(
                "Nur die Zieleinrichtung kann eine Reservierung ablehnen"
            )

        check_state_transition(model.status, "REJECTED")

        model.status = "REJECTED"
        model.updated_at = datetime.now(timezone.utc)

        await self._create_task_and_audit(model, "REJECTED", location_id)
        await self._session.flush()
        return _to_entity(model)

    async def transfer(
        self, reservation_id: UUID, location_id: UUID
    ) -> ReservationRequest:
        """
        Zieleinrichtung checkt Person ein: erstellt Occupant am confirmed_bed_id, setzt TRANSFERRED.
        Source-Einrichtung erhält Task zur manuellen Ausbuchung.
        """
        result = await self._session.execute(
            select(ReservationRequestModel)
            .where(ReservationRequestModel.id == reservation_id)
            .with_for_update()
        )
        model = result.scalar_one_or_none()
        if model is None:
            raise HTTPException(status_code=404, detail="Reservierung nicht gefunden")

        if model.target_location_id != location_id:
            raise RetractionForbiddenError(
                "Nur die Zieleinrichtung kann den Transfer durchführen"
            )

        check_state_transition(model.status, "TRANSFERRED")

        if model.confirmed_bed_id is None:
            raise HTTPException(
                status_code=409,
                detail="Kein Bett zugewiesen — Reservierung erst bestätigen",
            )

        # Nochmals auf Doppelbelegung prüfen (Absicherung)
        overlap = await self._session.execute(
            select(OccupantModel).where(
                OccupantModel.bed_id == model.confirmed_bed_id,
                OccupantModel.belegung_start < model.belegung_ende,
                OccupantModel.belegung_ende > model.belegung_start,
            )
        )
        if overlap.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=409, detail="Bett ist im Zeitraum bereits belegt"
            )

        now = datetime.now(timezone.utc)
        occupant = OccupantModel(
            id=uuid4(),
            bed_id=model.confirmed_bed_id,
            azr_id=model.azr_id,
            alias_id=None,
            geschlecht=model.geschlecht,
            belegung_start=model.belegung_start,
            belegung_ende=model.belegung_ende,
            labels=[],
            extended_once=False,
            created_at=now,
        )
        self._session.add(occupant)

        model.status = "TRANSFERRED"
        model.updated_at = now

        await self._create_task_and_audit(model, "TRANSFERRED", location_id)
        await self._session.flush()
        return _to_entity(model)

    async def list_pending_for_target(
        self, target_location_id: UUID
    ) -> List[ReservationRequest]:
        """Aktionspflichtige Anfragen für die Zieleinrichtung: PENDING (bestätigen) + CONFIRMED (einchecken)."""
        result = await self._session.execute(
            select(ReservationRequestModel)
            .where(
                ReservationRequestModel.target_location_id == target_location_id,
                ReservationRequestModel.status.in_(["PENDING", "CONFIRMED"]),
            )
            .order_by(ReservationRequestModel.created_at.asc())
        )
        return [_to_entity(m) for m in result.scalars().all()]

    async def list_for_location(
        self, location_id: UUID, status_filter: Optional[str] = None
    ) -> List[ReservationRequest]:
        """Alle Reservierungen bei denen die Einrichtung Requester oder Target ist."""
        q = select(ReservationRequestModel).where(
            or_(
                ReservationRequestModel.requester_location_id == location_id,
                ReservationRequestModel.target_location_id == location_id,
            )
        )
        if status_filter:
            q = q.where(ReservationRequestModel.status == status_filter)
        q = q.order_by(ReservationRequestModel.created_at.asc())
        result = await self._session.execute(q)
        return [_to_entity(m) for m in result.scalars().all()]

    # ---------------------------------------------------------------------------
    # Interne Hilfsmethoden
    # ---------------------------------------------------------------------------

    async def _create_task(
        self,
        location_id: UUID,
        reservation_id: UUID,
        task_type: TaskType,
        priority: TaskPriority,
        title: str,
        body: str = "",
    ) -> None:
        now = datetime.now(timezone.utc)
        task = TaskModel(
            id=uuid4(),
            location_id=location_id,
            related_reservation_id=reservation_id,
            task_type=task_type.value,
            priority=priority.value,
            status=TaskStatus.OPEN.value,
            title=title,
            body=body,
            created_at=now,
            updated_at=now,
        )
        self._session.add(task)

    async def _write_audit(
        self, reservation_id: UUID, action: str, actor_id: Optional[UUID]
    ) -> None:
        payload = json.dumps({"reservation_id": str(reservation_id), "action": action})
        await self._session.execute(
            text(
                "INSERT INTO audit.events (id, event_type, payload, created_at) "
                "VALUES (:id, :event_type, :payload, :created_at)"
            ),
            {
                "id": str(uuid4()),
                "event_type": f"reservation.{action.lower()}",
                "payload": payload,
                "created_at": datetime.now(timezone.utc),
            },
        )

    async def _create_task_and_audit(
        self,
        model: ReservationRequestModel,
        new_status: str,
        location_id: UUID,
    ) -> None:
        """
        Erzeugt Task(s) und Audit-Eintrag für einen Statusübergang.
        Wird in derselben Session/Transaktion wie der Status-Update aufgerufen.
        """
        if new_status == "CONFIRMED":
            await self._create_task(
                location_id=model.requester_location_id,
                reservation_id=model.id,
                task_type=TaskType.RESERVATION_CONFIRMED,
                priority=TaskPriority.HIGH,
                title="Reservierung bestätigt",
                body=f"Ihre Reservierungsanfrage für AZR-ID {model.azr_id} wurde bestätigt.",
            )
        elif new_status == "REJECTED":
            await self._create_task(
                location_id=model.requester_location_id,
                reservation_id=model.id,
                task_type=TaskType.RESERVATION_REJECTED,
                priority=TaskPriority.HIGH,
                title="Reservierung abgelehnt",
                body=f"Ihre Reservierungsanfrage für AZR-ID {model.azr_id} wurde abgelehnt.",
            )
        elif new_status == "CANCELLED":
            # Task für beide beteiligten Einrichtungen
            await self._create_task(
                location_id=model.requester_location_id,
                reservation_id=model.id,
                task_type=TaskType.RESERVATION_CANCELLED,
                priority=TaskPriority.MEDIUM,
                title="Reservierung abgebrochen",
                body=f"Reservierungsanfrage für AZR-ID {model.azr_id} wurde abgebrochen.",
            )
            await self._create_task(
                location_id=model.target_location_id,
                reservation_id=model.id,
                task_type=TaskType.RESERVATION_CANCELLED,
                priority=TaskPriority.MEDIUM,
                title="Reservierung abgebrochen",
                body=f"Reservierungsanfrage für AZR-ID {model.azr_id} wurde abgebrochen.",
            )
        elif new_status == "TRANSFERRED":
            await self._create_task(
                location_id=model.requester_location_id,
                reservation_id=model.id,
                task_type=TaskType.RESERVATION_TRANSFERRED,
                priority=TaskPriority.HIGH,
                title="Person transferiert — Ausbuchung prüfen",
                body=f"AZR-ID {model.azr_id} wurde zur Zieleinrichtung transferiert. Bitte prüfen, ob die Person noch manuell ausgebucht werden muss.",
            )
            await self._create_task(
                location_id=model.target_location_id,
                reservation_id=model.id,
                task_type=TaskType.RESERVATION_TRANSFERRED,
                priority=TaskPriority.MEDIUM,
                title="Einchecken bestätigt",
                body=f"AZR-ID {model.azr_id} wurde erfolgreich eingecheckt und einem Bett zugewiesen.",
            )

        await self._write_audit(model.id, new_status, location_id)
