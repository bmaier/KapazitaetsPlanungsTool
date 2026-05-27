"""Unit-Tests für src/domain/capacity/rules.py — keine DB, kein HTTP."""
import pytest
from datetime import date

from src.domain.capacity.rules import (
    DomainError,
    check_bed_available,
    check_eu_quota,
    check_notbett_duration,
    check_12_weeks,
)
from src.domain.capacity.value_objects import BedType


TODAY = date(2026, 1, 1)


# ---------------------------------------------------------------------------
# check_notbett_duration
# ---------------------------------------------------------------------------

def test_notbett_1_day_ok():
    check_notbett_duration(BedType.NOTBETT, TODAY, date(2026, 1, 2))


def test_notbett_2_days_raises():
    with pytest.raises(DomainError, match="Notbett"):
        check_notbett_duration(BedType.NOTBETT, TODAY, date(2026, 1, 3))


def test_notbett_many_days_raises():
    with pytest.raises(DomainError):
        check_notbett_duration(BedType.NOTBETT, TODAY, date(2026, 1, 10))


def test_kontingent_long_stay_ok():
    check_notbett_duration(BedType.KONTINGENT, TODAY, date(2026, 6, 1))


# ---------------------------------------------------------------------------
# check_12_weeks
# ---------------------------------------------------------------------------

def test_exactly_84_days_no_warning():
    assert check_12_weeks(TODAY, date(2026, 3, 26)) is False


def test_85_days_triggers_warning():
    assert check_12_weeks(TODAY, date(2026, 3, 27)) is True


def test_short_stay_no_warning():
    assert check_12_weeks(TODAY, date(2026, 1, 15)) is False


def test_one_year_triggers_warning():
    assert check_12_weeks(TODAY, date(2027, 1, 1)) is True


# ---------------------------------------------------------------------------
# check_eu_quota
# ---------------------------------------------------------------------------

def test_quota_zero_means_disabled():
    check_eu_quota(9999, 9999, 0)


def test_quota_exactly_at_limit_ok():
    check_eu_quota(170, 30, 200)  # 200 == 200 → ok


def test_quota_one_over_raises():
    with pytest.raises(DomainError, match="EU-Gesamtquote"):
        check_eu_quota(180, 21, 200)  # 201 > 200


def test_quota_well_under_ok():
    check_eu_quota(50, 30, 200)


# ---------------------------------------------------------------------------
# check_bed_available
# ---------------------------------------------------------------------------

def test_free_bed_ok():
    check_bed_available(None)


def test_occupied_bed_raises():
    with pytest.raises(DomainError, match="bereits belegt"):
        check_bed_available("some-occupancy-object")


def test_occupied_bed_with_object_raises():
    with pytest.raises(DomainError):
        check_bed_available({"id": "abc"})
