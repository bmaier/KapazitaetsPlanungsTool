"""
Domain-Regeln für Reservierungsanfragen.
Reine Funktionen — kein I/O, kein FastAPI-Import, kein SQLAlchemy-Import.
"""
import uuid
from typing import TYPE_CHECKING

from src.domain.capacity.rules import DomainError

if TYPE_CHECKING:
    from src.domain.reservations.entities import ReservationRequest


class RetractionForbiddenError(DomainError):
    """Wird ausgelöst wenn eine nicht-beteiligte Einrichtung eine Reservierung abbricht."""


class InvalidStateTransitionError(DomainError):
    """Wird ausgelöst bei ungültigem Statusübergang."""


# Erlaubte Übergänge: current_status → {erlaubte neue Status}
VALID_TRANSITIONS: dict[str, set[str]] = {
    "PENDING": {"CONFIRMED", "REJECTED", "CANCELLED"},
    "CONFIRMED": {"TRANSFERRED", "CANCELLED"},
}


def check_retraction_allowed(
    location_id: uuid.UUID, req: "ReservationRequest"
) -> None:
    """
    Prüft ob die anfragende Einrichtung berechtigt ist, die Reservierung abzubrechen.
    Nur requester_location_id oder target_location_id dürfen abbrechen.
    Raises RetractionForbiddenError wenn nicht berechtigt.
    """
    if location_id not in (req.requester_location_id, req.target_location_id):
        raise RetractionForbiddenError(
            "Nur beteiligte Einrichtungen dürfen Reservierungen abbrechen"
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
