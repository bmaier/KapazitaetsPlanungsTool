"""
Domain-Regeln für Reservierungsanfragen.
Reine Funktionen — kein I/O, kein FastAPI-Import, kein SQLAlchemy-Import.
"""
import uuid
from typing import TYPE_CHECKING, Optional

from src.domain.capacity.rules import DomainError

if TYPE_CHECKING:
    from src.domain.reservations.entities import ReservationRequest


class RetractionForbiddenError(DomainError):
    """Wird ausgelöst wenn eine nicht-beteiligte Einrichtung eine Reservierung abbricht."""


class InvalidStateTransitionError(DomainError):
    """Wird ausgelöst bei ungültigem Statusübergang."""


class ActiveReservationBlocksError(DomainError):
    """Wird ausgelöst wenn eine aktive Reservation die Aktion verhindert."""


class EinPlatzRuleError(DomainError):
    """Wird ausgelöst wenn die Ein-Platz-Regel verletzt wird (Person bereits in anderer Einrichtung)."""


# Erlaubte Übergänge: current_status → {erlaubte neue Status}
VALID_TRANSITIONS: dict[str, set[str]] = {
    "PENDING": {"CONFIRMED", "REJECTED", "CANCELLED"},
    "CONFIRMED": {"TRANSFERRED", "CANCELLED"},
}


def check_retraction_allowed(
    location_id: Optional[uuid.UUID],
    req: "ReservationRequest",
    is_system_admin: bool = False,
) -> None:
    """
    Prüft ob die anfragende Einrichtung berechtigt ist, die Reservierung abzubrechen.
    system-admin darf immer abbrechen.
    Sonst: nur requester_location_id (nicht target_location_id).
    """
    if is_system_admin:
        return
    if location_id is None or location_id != req.requester_location_id:
        raise RetractionForbiddenError(
            "Nur die anfragende Einrichtung oder ein System-Admin darf Reservierungen stornieren"
        )


def check_no_active_reservation(active_res_id: Optional[uuid.UUID]) -> None:
    """
    Prüft ob eine aktive Reservation die Aktion blockiert.
    Raises ActiveReservationBlocksError wenn active_res_id nicht None ist.
    """
    if active_res_id is not None:
        raise ActiveReservationBlocksError(
            "Aktive Verlegungsanfrage vorhanden — erst stornieren oder abwarten"
        )


def check_single_occupancy(
    existing_location_id: Optional[uuid.UUID],
    target_location_id: uuid.UUID,
) -> None:
    """
    Prüft die Ein-Platz-Regel: Person darf nicht gleichzeitig in zwei verschiedenen
    Einrichtungen aktiv belegt sein. Internes Verlegen (selbe location_id) ist erlaubt.
    """
    if existing_location_id is not None and existing_location_id != target_location_id:
        raise EinPlatzRuleError(
            "Person bereits in einer anderen Einrichtung aktiv belegt (Ein-Platz-Regel)"
        )


def check_state_transition(current: str, new: str) -> None:
    """
    Prüft ob der Statusübergang current → new erlaubt ist.
    Raises InvalidStateTransitionError wenn nicht erlaubt.
    """
    allowed = VALID_TRANSITIONS.get(current, set())
    if new not in allowed:
        raise InvalidStateTransitionError(
            f"Übergang {current} → {new} nicht erlaubt"
        )
