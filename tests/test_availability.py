"""Tests for availability.check_availability failure modes."""

import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import availability
from availability import (
    AvailabilityFetchError,
    check_availability,
)


def _jul_aug_payloads():
    """Return fake API payloads for July and August where site 1234 is
    fully available across the boundary Jul 30 -- Aug 3."""
    jul = {
        "campsites": {
            "1234": {
                "site": "Loop A Site 001",
                "availabilities": {
                    "2026-07-30T00:00:00Z": "Available",
                    "2026-07-31T00:00:00Z": "Available",
                },
            }
        }
    }
    aug = {
        "campsites": {
            "1234": {
                "site": "Loop A Site 001",
                "availabilities": {
                    "2026-08-01T00:00:00Z": "Available",
                    "2026-08-02T00:00:00Z": "Available",
                    "2026-08-03T00:00:00Z": "Available",
                },
            }
        }
    }
    return jul, aug


def test_returns_site_when_all_months_succeed(monkeypatch):
    jul, aug = _jul_aug_payloads()

    def fake_fetch(facility_id, month_start):
        if month_start == date(2026, 7, 1):
            return jul
        if month_start == date(2026, 8, 1):
            return aug
        raise AssertionError(f"unexpected month {month_start}")

    monkeypatch.setattr(availability, "_fetch_month", fake_fetch)

    result = check_availability(
        facility_id="232447",
        arrival_date=date(2026, 7, 30),
        length_of_stay=5,
    )
    assert result == [{"campsite_id": "1234", "site_name": "Loop A Site 001"}]


def test_raises_when_one_required_month_fails(monkeypatch):
    jul, _ = _jul_aug_payloads()

    def fake_fetch(facility_id, month_start):
        if month_start == date(2026, 7, 1):
            return jul
        return None  # August fetch fails

    monkeypatch.setattr(availability, "_fetch_month", fake_fetch)

    with pytest.raises(AvailabilityFetchError):
        check_availability(
            facility_id="232447",
            arrival_date=date(2026, 7, 30),
            length_of_stay=5,
        )


def test_raises_when_all_months_fail(monkeypatch):
    monkeypatch.setattr(availability, "_fetch_month", lambda *_args, **_kw: None)

    with pytest.raises(AvailabilityFetchError):
        check_availability(
            facility_id="232447",
            arrival_date=date(2026, 7, 11),
            length_of_stay=3,
        )


def test_rejects_zero_length_of_stay(monkeypatch):
    """length_of_stay=0 must raise rather than silently match every site.

    Regression: empty needed_dates made _is_available return True for every
    campsite in the API response, triggering a random booking attempt.
    """
    monkeypatch.setattr(availability, "_fetch_month", lambda *_a, **_kw: {})

    with pytest.raises(ValueError):
        check_availability(
            facility_id="232447",
            arrival_date=date(2026, 7, 11),
            length_of_stay=0,
        )


def test_rejects_negative_length_of_stay(monkeypatch):
    monkeypatch.setattr(availability, "_fetch_month", lambda *_a, **_kw: {})

    with pytest.raises(ValueError):
        check_availability(
            facility_id="232447",
            arrival_date=date(2026, 7, 11),
            length_of_stay=-3,
        )


def test_single_month_success_unchanged(monkeypatch):
    payload = {
        "campsites": {
            "5678": {
                "site": "B-12",
                "availabilities": {
                    "2026-07-11T00:00:00Z": "Available",
                    "2026-07-12T00:00:00Z": "Available",
                    "2026-07-13T00:00:00Z": "Available",
                },
            },
            "9999": {
                "site": "C-05",
                "availabilities": {
                    "2026-07-11T00:00:00Z": "Reserved",
                    "2026-07-12T00:00:00Z": "Available",
                    "2026-07-13T00:00:00Z": "Available",
                },
            },
        }
    }

    monkeypatch.setattr(availability, "_fetch_month", lambda *_a, **_kw: payload)

    result = check_availability(
        facility_id="232447",
        arrival_date=date(2026, 7, 11),
        length_of_stay=3,
    )
    assert result == [{"campsite_id": "5678", "site_name": "B-12"}]


def test_preserves_user_campsite_ids_order(monkeypatch):
    """When a user lists preferred campsite_ids, results follow that order.

    The first site in campsite_ids is the user's top preference and must be
    attempted first by the booker when multiple preferred sites are available.
    Regression guard: the API may return sites in any order, so the merge
    must re-order to match the user's priority list.
    """
    # API returns sites in opposite order from what the user asked for.
    payload = {
        "campsites": {
            "5678": {
                "site": "B-12",
                "availabilities": {
                    "2026-07-11T00:00:00Z": "Available",
                    "2026-07-12T00:00:00Z": "Available",
                },
            },
            "1234": {
                "site": "A-01",
                "availabilities": {
                    "2026-07-11T00:00:00Z": "Available",
                    "2026-07-12T00:00:00Z": "Available",
                },
            },
        }
    }

    monkeypatch.setattr(availability, "_fetch_month", lambda *_a, **_kw: payload)

    result = check_availability(
        facility_id="232447",
        arrival_date=date(2026, 7, 11),
        length_of_stay=2,
        campsite_ids=["1234", "5678"],
    )
    assert result == [
        {"campsite_id": "1234", "site_name": "A-01"},
        {"campsite_id": "5678", "site_name": "B-12"},
    ]


def test_campsite_ids_order_skips_unavailable(monkeypatch):
    """User priority order is preserved even when some preferred sites are unavailable."""
    payload = {
        "campsites": {
            "5678": {
                "site": "B-12",
                "availabilities": {
                    "2026-07-11T00:00:00Z": "Available",
                    "2026-07-12T00:00:00Z": "Available",
                },
            },
            "1234": {
                "site": "A-01",
                "availabilities": {
                    "2026-07-11T00:00:00Z": "Reserved",
                    "2026-07-12T00:00:00Z": "Available",
                },
            },
            "9999": {
                "site": "C-05",
                "availabilities": {
                    "2026-07-11T00:00:00Z": "Available",
                    "2026-07-12T00:00:00Z": "Available",
                },
            },
        }
    }

    monkeypatch.setattr(availability, "_fetch_month", lambda *_a, **_kw: payload)

    result = check_availability(
        facility_id="232447",
        arrival_date=date(2026, 7, 11),
        length_of_stay=2,
        campsite_ids=["1234", "9999", "5678"],
    )
    # 1234 is unavailable and must be dropped; 9999 then 5678 stay in user order.
    assert result == [
        {"campsite_id": "9999", "site_name": "C-05"},
        {"campsite_id": "5678", "site_name": "B-12"},
    ]
