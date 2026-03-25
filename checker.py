#!/usr/bin/env python3
"""Campsite checker — find and book campsites on recreation.gov."""

import argparse
import sys
import time

from availability import check_availability
from config import load_config


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

    from pathlib import Path
    cfg = load_config(Path(args.config))

    attempt = 0
    while True:
        attempt += 1
        if args.poll:
            print(f"--- Attempt {attempt} ---")

        booked_any = False
        for res in cfg.reservations:
            label = res.name or f"facility {res.facility_id}"
            print(f"Checking availability for {label}...")

            available = check_availability(
                facility_id=res.facility_id,
                arrival_date=res.arrival_date,
                length_of_stay=res.length_of_stay,
                campsite_ids=res.campsite_ids or None,
            )

            if not available:
                print(f"  No available sites for {label}.")
                continue

            print(f"  Found {len(available)} available site(s)!")
            for site in available:
                print(f"    - {site['site_name']} (ID: {site['campsite_id']})")

            # Try to book the first available site
            from booker import book_site
            for site in available:
                print(f"  Attempting to book {site['site_name']}...")
                success = book_site(
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
                    headed=args.headed,
                )
                if success:
                    print(f"  Booking successful for {site['site_name']}!")
                    booked_any = True
                    break
                else:
                    print(f"  Booking failed for {site['site_name']}, trying next...")

            if booked_any:
                break

        if booked_any:
            print("\nDone! Complete payment in the browser if needed.")
            sys.exit(0)

        # If not polling, exit
        if not args.poll:
            print("\nNo sites booked.")
            sys.exit(1)

        # Check retry limit
        if args.max_retries and attempt >= args.max_retries:
            print(f"\nMax retries ({args.max_retries}) reached. Exiting.")
            sys.exit(1)

        print(f"\nRetrying in {args.poll} seconds...")
        try:
            time.sleep(args.poll)
        except KeyboardInterrupt:
            print("\nInterrupted.")
            sys.exit(1)


if __name__ == "__main__":
    main()
