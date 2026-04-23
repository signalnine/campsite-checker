# Contract: Distinguish "booking failed" from "no availability" exit codes

Tracking: bd issue campsite-checker-7y0

## Behavior

- [ ] When all reservations complete with no availability found, exit 1.
  Test: `run_single_attempt` returns `Outcome.NO_AVAILABILITY` when `check_availability` returns empty for every reservation.

- [ ] When availability is found but every booking attempt returns False, exit 2.
  Test: `run_single_attempt` returns `Outcome.BOOKING_FAILED` when `check_availability` returns sites but `book_site` returns False for all.

- [ ] When any booking succeeds, exit 0.
  Test: `run_single_attempt` returns `Outcome.BOOKED` when `book_site` returns True.

- [ ] `AvailabilityFetchError` from a reservation does not by itself count as "booking failed".
  Test: If every reservation either raises `AvailabilityFetchError` or returns no availability, outcome is `NO_AVAILABILITY`.

- [ ] Mixed reservations: one finds availability and booking fails, another finds none -> outcome is `BOOKING_FAILED`.
  Test: Reservation A returns sites, all book_site calls return False; reservation B returns empty list. Outcome: `BOOKING_FAILED`.

- [ ] Polling-mode exit code reflects the LAST attempt's outcome on max_retries.
  Test: With `--poll` and `--max-retries`, final exit code is 1 if last attempt found nothing, 2 if last attempt booked-failed.

- [ ] README exit-codes table documents code 2.
  Test: grep README.md for "| 2 " produces a match.

## Verification

- `pytest tests/ -v` passes all existing and new tests.
- New tests cover each outcome of `run_single_attempt`.
- README.md lists exit code 2.
