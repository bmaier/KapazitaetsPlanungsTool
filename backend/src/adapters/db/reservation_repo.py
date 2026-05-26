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

from src.adapters.db.models import ReservationRequestModel, TaskModel
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
        self, reservation_id: UUID, location_id: UUID
    ) -> ReservationRequest:
        """Bestätigt eine Reservierung — prüft ob location_id == target_location_id."""
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

        model.status = "CONFIRMED"
        model.updated_at = datetime.now(timezone.utc)

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

    async def list_pending_for_target(
        self, target_location_id: UUID
    ) -> List[ReservationRequest]:
        """FCFS: PENDING-Anfragen für eine Zieleinrichtung, sortiert nach created_at ASC."""
        result = await self._session.execute(
            select(ReservationRequestModel)
            .where(
                ReservationRequestModel.target_location_id == target_location_id,
                ReservationRequestModel.status == "PENDING",
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
                title="Transfer abgeschlossen",
                body=f"Transfer für AZR-ID {model.azr_id} wurde abgeschlossen.",
            )

        await self._write_audit(model.id, new_status, location_id)
