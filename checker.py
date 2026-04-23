#!/usr/bin/env python3
"""Campsite checker — find and book campsites on recreation.gov."""

import argparse
import sys
import time
from enum import Enum
from pathlib import Path

from availability import AvailabilityFetchError, check_availability
from config import Config, load_config


class Outcome(Enum):
    """Result of a single run_single_attempt call.

    Values double as process exit codes so callers can `sys.exit(outcome.value)`.
    BOOKING_FAILED is distinct from NO_AVAILABILITY so operators can tell
    "keep polling, nothing broken" from "booker is broken, investigate".
    """
    BOOKED = 0
    NO_AVAILABILITY = 1
    BOOKING_FAILED = 2


def _invoke_booker(**kwargs) -> bool:
    """Indirection point so tests can monkeypatch the booker without importing Playwright."""
    from booker import book_site
    return book_site(**kwargs)


def run_single_attempt(cfg: Config, headed: bool) -> Outcome:
    """Run one pass over all reservations. Returns the outcome.

    Returns BOOKED as soon as any site is successfully booked.
    Returns BOOKING_FAILED if any reservation had availability but every
    book_site call returned False and no booking ever succeeded.
    Returns NO_AVAILABILITY if no reservation had availability this pass.
    """
    booking_attempted = False

    for res in cfg.reservations:
        label = res.name or f"facility {res.facility_id}"
        print(f"Checking availability for {label}...")

        try:
            available = check_availability(
                facility_id=res.facility_id,
                arrival_date=res.arrival_date,
                length_of_stay=res.length_of_stay,
                campsite_ids=res.campsite_ids or None,
            )
        except AvailabilityFetchError as e:
            print(f"  Availability check failed for {label}: {e}")
            continue

        if not available:
            print(f"  No available sites for {label}.")
            continue

        print(f"  Found {len(available)} available site(s)!")
        for site in available:
            print(f"    - {site['site_name']} (ID: {site['campsite_id']})")

        booking_attempted = True
        for site in available:
            print(f"  Attempting to book {site['site_name']}...")
            success = _invoke_booker(
                facility_id=res.facility_id,
                campsite_id=site["campsite_id"],
                site_name=site["site_name"],
                arrival_date=res.arrival_date,
                length_of_stay=res.length_of_stay,
                num_occupants=res.num_occupants,
                num_vehicles=res.num_vehicles,
                equipment_type=res.equipment_type,
                username=cfg.account.username,
                password=cfg.account.password,
                headed=headed,
            )
            if success:
                print(f"  Booking successful for {site['site_name']}!")
                return Outcome.BOOKED
            print(f"  Booking failed for {site['site_name']}, trying next...")

    if booking_attempted:
        return Outcome.BOOKING_FAILED
    return Outcome.NO_AVAILABILITY


def main():
    parser = argparse.ArgumentParser(
        description="Check recreation.gov campsite availability and auto-book."
    )
    parser.add_argument(
        "--poll", type=int, default=0, metavar="SECONDS",
        help="Poll interval in seconds (0 = run once and exit)",
    )
    parser.add_argument(
        "--max-retries", type=int, default=0, metavar="N",
        help="Max poll attempts (0 = unlimited, only used with --poll)",
    )
    parser.add_argument(
        "--headed", action="store_true",
        help="Run browser in visible mode for debugging",
    )
    parser.add_argument(
        "--config", type=str, default="checker.yaml",
        help="Path to config file (default: checker.yaml)",
    )
    args = parser.parse_args()

    cfg = load_config(Path(args.config))

    attempt = 0
    while True:
        attempt += 1
        if args.poll:
            print(f"--- Attempt {attempt} ---")

        outcome = run_single_attempt(cfg, headed=args.headed)

        if outcome is Outcome.BOOKED:
            print("\nDone! Complete payment in the browser if needed.")
            sys.exit(Outcome.BOOKED.value)

        if not args.poll:
            if outcome is Outcome.BOOKING_FAILED:
                print("\nAvailability found but booking failed.")
            else:
                print("\nNo sites booked.")
            sys.exit(outcome.value)

        if args.max_retries and attempt >= args.max_retries:
            print(f"\nMax retries ({args.max_retries}) reached. Exiting.")
            sys.exit(outcome.value)

        print(f"\nRetrying in {args.poll} seconds...")
        try:
            time.sleep(args.poll)
        except KeyboardInterrupt:
            print("\nInterrupted.")
            sys.exit(outcome.value)


if __name__ == "__main__":
    main()
