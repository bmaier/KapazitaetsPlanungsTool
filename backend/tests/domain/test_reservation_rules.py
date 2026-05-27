"""Unit-Tests für src/domain/reservations/rules.py — keine DB, kein HTTP."""
import uuid
from unittest.mock import MagicMock

import pytest

from src.domain.reservations.rules import (
    InvalidStateTransitionError,
    RetractionForbiddenError,
    check_retraction_allowed,
    check_state_transition,
)


LOC_A = uuid.uuid4()
LOC_B = uuid.uuid4()


def _make_request(requester_id: uuid.UUID) -> MagicMock:
    req = MagicMock()
    req.requester_location_id = requester_id
    return req


# ---------------------------------------------------------------------------
# check_retraction_allowed
# ---------------------------------------------------------------------------

def test_requester_may_retract():
    check_retraction_allowed(LOC_A, _make_request(LOC_A), is_system_admin=False)


def test_third_party_cannot_retract():
    with pytest.raises(RetractionForbiddenError):
        check_retraction_allowed(LOC_B, _make_request(LOC_A), is_system_admin=False)


def test_system_admin_may_always_retract():
    check_retraction_allowed(None, _make_request(LOC_A), is_system_admin=True)


def test_none_location_non_admin_cannot_retract():
    with pytest.raises(RetractionForbiddenError):
        check_retraction_allowed(None, _make_request(LOC_A), is_system_admin=False)


# ---------------------------------------------------------------------------
# check_state_transition
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("current,new", [
    ("PENDING", "CONFIRMED"),
    ("PENDING", "REJECTED"),
    ("PENDING", "CANCELLED"),
    ("CONFIRMED", "TRANSFERRED"),
    ("CONFIRMED", "CANCELLED"),
])
def test_valid_transitions(current, new):
    check_state_transition(current, new)


@pytest.mark.parametrize("current,new", [
    ("PENDING", "TRANSFERRED"),
    ("CONFIRMED", "PENDING"),
    ("CONFIRMED", "REJECTED"),
    ("REJECTED", "PENDING"),
    ("CANCELLED", "CONFIRMED"),
    ("TRANSFERRED", "CONFIRMED"),
])
def test_invalid_transitions(current, new):
    with pytest.raises(InvalidStateTransitionError):
        check_state_transition(current, new)
