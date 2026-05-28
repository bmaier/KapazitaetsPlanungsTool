"""
Port (ABC) für das Reservierungs-Repository.
Definiert die Schnittstelle zwischen Domäne/Anwendung und der DB-Adapter-Schicht.
"""
from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from src.domain.reservations.entities import ReservationRequest


class AbstractReservationRepo(ABC):

    @abstractmethod
    async def create(self, body, requester_location_id: UUID) -> ReservationRequest:
        """Erstellt eine neue Reservierungsanfrage mit Status PENDING."""

    @abstractmethod
    async def get(self, reservation_id: UUID) -> Optional[ReservationRequest]:
        """Gibt eine Reservierungsanfrage nach ID zurück oder None."""

    @abstractmethod
    async def update_status(
        self,
        reservation_id: UUID,
        new_status: str,
        location_id: UUID,
    ) -> ReservationRequest:
        """
        Ändert den Status einer Reservierung (SELECT FOR UPDATE).
        Erstellt Task + Audit in derselben Transaktion.
        """

    @abstractmethod
    async def confirm(
        self, reservation_id: UUID, location_id: UUID, confirmed_bed_id: UUID
    ) -> ReservationRequest:
        """Bestätigt eine Reservierung und weist Bett zu — nur wenn location_id == target_location_id."""

    @abstractmethod
    async def reject(
        self, reservation_id: UUID, location_id: UUID
    ) -> ReservationRequest:
        """Lehnt eine Reservierung ab — nur wenn location_id == target_location_id."""

    @abstractmethod
    async def transfer(
        self, reservation_id: UUID, location_id: UUID
    ) -> ReservationRequest:
        """Checkt Person ein: erstellt Occupant, setzt TRANSFERRED — nur Zieleinrichtung."""

    @abstractmethod
    async def list_pending_for_target(
        self, target_location_id: UUID
    ) -> List[ReservationRequest]:
        """Gibt PENDING-Anfragen für eine Zieleinrichtung sortiert nach created_at ASC zurück."""

    @abstractmethod
    async def list_for_location(
        self, location_id: UUID, status_filter: Optional[str] = None
    ) -> List[ReservationRequest]:
        """Gibt alle Reservierungen zurück bei denen location_id Requester oder Target ist."""
