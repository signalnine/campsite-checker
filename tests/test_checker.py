"""Tests for checker.run_single_attempt outcome classification.

The run_single_attempt helper separates per-attempt behavior from
polling/exit-code logic so the outcome of each attempt can be unit tested.

Three outcomes the caller must distinguish:
- BOOKED: at least one book_site call succeeded
- BOOKING_FAILED: some reservation had availability but every book_site returned False
- NO_AVAILABILITY: every reservation finished with empty availability (or an
  AvailabilityFetchError) and no booking was ever attempted
"""

import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import availability
import checker
from availability import AvailabilityFetchError
from checker import Outcome, run_single_attempt
from config import Account, Config, Reservation


def _reservation(name="alpha", facility_id="1"):
    return Reservation(
        name=name,
        facility_id=facility_id,
        arrival_date=date(2026, 7, 11),
        length_of_stay=2,
        num_occupants=2,
        num_vehicles=1,
        equipment_type="tent",
        campsite_ids=[],
    )


def _config(reservations):
    return Config(
        account=Account(username="u", password="p"),
        reservations=reservations,
    )


def test_no_availability_everywhere_returns_no_availability(monkeypatch):
    monkeypatch.setattr(checker, "check_availability", lambda **_k: [])
    monkeypatch.setattr(checker, "_invoke_booker", lambda **_k: pytest.fail("should not be called"))

    outcome = run_single_attempt(_config([_reservation()]), headed=False)

    assert outcome is Outcome.NO_AVAILABILITY


def test_availability_fetch_error_is_not_booking_failed(monkeypatch):
    def raise_fetch_error(**_k):
        raise AvailabilityFetchError("boom")

    monkeypatch.setattr(checker, "check_availability", raise_fetch_error)
    monkeypatch.setattr(checker, "_invoke_booker", lambda **_k: pytest.fail("should not be called"))

    outcome = run_single_attempt(_config([_reservation()]), headed=False)

    assert outcome is Outcome.NO_AVAILABILITY


def test_availability_found_but_booking_fails_returns_booking_failed(monkeypatch):
    monkeypatch.setattr(
        checker,
        "check_availability",
        lambda **_k: [{"campsite_id": "1234", "site_name": "A-01"}],
    )
    monkeypatch.setattr(checker, "_invoke_booker", lambda **_k: False)

    outcome = run_single_attempt(_config([_reservation()]), headed=False)

    assert outcome is Outcome.BOOKING_FAILED


def test_successful_booking_returns_booked(monkeypatch):
    monkeypatch.setattr(
        checker,
        "check_availability",
        lambda **_k: [{"campsite_id": "1234", "site_name": "A-01"}],
    )
    monkeypatch.setattr(checker, "_invoke_booker", lambda **_k: True)

    outcome = run_single_attempt(_config([_reservation()]), headed=False)

    assert outcome is Outcome.BOOKED


def test_mixed_some_empty_some_booking_failed_returns_booking_failed(monkeypatch):
    """One reservation has no availability, another has availability but booking fails.

    Booking was attempted and failed -- operator needs to investigate the booker,
    so outcome must be BOOKING_FAILED, not NO_AVAILABILITY.
    """
    calls = {"n": 0}

    def fake_check(**kwargs):
        calls["n"] += 1
        if kwargs["facility_id"] == "with-sites":
            return [{"campsite_id": "1234", "site_name": "A-01"}]
        return []

    monkeypatch.setattr(checker, "check_availability", fake_check)
    monkeypatch.setattr(checker, "_invoke_booker", lambda **_k: False)

    outcome = run_single_attempt(
        _config([
            _reservation(name="empty", facility_id="empty"),
            _reservation(name="has-sites", facility_id="with-sites"),
        ]),
        headed=False,
    )

    assert outcome is Outcome.BOOKING_FAILED
    assert calls["n"] == 2


def test_tries_multiple_sites_before_declaring_booking_failed(monkeypatch):
    """Booker should iterate through all available sites before giving up."""
    monkeypatch.setattr(
        checker,
        "check_availability",
        lambda **_k: [
            {"campsite_id": "1234", "site_name": "A-01"},
            {"campsite_id": "5678", "site_name": "B-12"},
        ],
    )
    attempts = []

    def fake_booker(**kwargs):
        attempts.append(kwargs["campsite_id"])
        return False

    monkeypatch.setattr(checker, "_invoke_booker", fake_booker)

    outcome = run_single_attempt(_config([_reservation()]), headed=False)

    assert outcome is Outcome.BOOKING_FAILED
    assert attempts == ["1234", "5678"]


def test_stops_at_first_successful_booking(monkeypatch):
    """Once a site is booked, don't try remaining reservations."""
    monkeypatch.setattr(
        checker,
        "check_availability",
        lambda **_k: [{"campsite_id": "1234", "site_name": "A-01"}],
    )
    booker_calls = []

    def fake_booker(**kwargs):
        booker_calls.append(kwargs["campsite_id"])
        return True

    monkeypatch.setattr(checker, "_invoke_booker", fake_booker)

    outcome = run_single_attempt(
        _config([
            _reservation(name="first", facility_id="one"),
            _reservation(name="second", facility_id="two"),
        ]),
        headed=False,
    )

    assert outcome is Outcome.BOOKED
    assert booker_calls == ["1234"]


def test_outcome_exit_codes():
    """The Outcome enum values are the exit codes the script should emit."""
    assert Outcome.BOOKED.value == 0
    assert Outcome.NO_AVAILABILITY.value == 1
    assert Outcome.BOOKING_FAILED.value == 2
