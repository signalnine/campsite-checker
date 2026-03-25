# Modernize Campsite Checker

## Summary

Rewrite the campsite-checker from Python 2 + Selenium to Python 3 + requests + Playwright. Use recreation.gov's undocumented frontend API for availability checking (no browser needed), and Playwright for automated booking.

## Architecture

Two layers:
- **Availability checker** — HTTP requests to recreation.gov's frontend API
- **Auto-booker** — Playwright browser automation for the booking flow

Dependencies: `requests`, `playwright`, `pyyaml`

## Config Format

Switch from INI to YAML (`checker.yaml`):

```yaml
account:
  username: myuser@email.com
  password: mypassword

reservations:
  - name: "Yosemite Upper Pines"
    facility_id: "232447"
    campsite_ids:            # optional — omit to accept any available site
      - "1234"
      - "5678"
    arrival_date: "2026-07-11"
    length_of_stay: 5
    num_occupants: 4
    num_vehicles: 2
    equipment_type: "tent"
```

Changes from original:
- `facility_id` replaces `park_id` (current recreation.gov identifier)
- `campsite_ids` optional — if omitted, books first available site
- `equipment_type` is a readable string, not a magic number
- Dates use ISO format (YYYY-MM-DD)

## Availability Checking

Endpoint:
```
GET https://www.recreation.gov/api/camps/availability/campground/{facility_id}/month
    ?start_date=2026-07-01T00:00:00.000Z
```

Logic:
1. For each reservation, fetch month(s) covering the stay
2. Filter to requested `campsite_ids` (or all sites if omitted)
3. Check that all dates in stay window show "Available"
4. Return first matching site

Headers mimic browser User-Agent. No auth needed for this endpoint.

With `--poll`, sleeps for interval and repeats until match or `--max-retries` exhausted.

## Booking Flow (Playwright)

1. Launch headless Chromium (visible with `--headed` flag)
2. Navigate to campsite details page
3. Log in (handle multi-step login flow)
4. Set dates, fill arrival date and length of stay
5. Add to cart, fill occupants/vehicles/equipment, accept agreements
6. Stop at checkout — user completes payment manually

On failure: screenshot saved to `screenshots/`, fall back to next available site.

## CLI Interface

```
python checker.py                              # run once
python checker.py --poll 60                    # check every 60s
python checker.py --poll 60 --max-retries 50   # with retry limit
python checker.py --headed                     # visible browser for debugging
```

Exit codes:
- 0: booking reached checkout
- 1: no availability found
- 2: availability found but booking failed

## Project Structure

```
checker.py              # main entry point (CLI + orchestration)
availability.py         # API-based availability checking
booker.py               # Playwright booking automation
config.py               # YAML config loading + validation
checker.yaml            # user config (gitignored)
checker_example.yaml    # example config (committed)
requirements.txt        # requests, playwright, pyyaml
screenshots/            # failure screenshots (gitignored)
README.md               # updated docs
```

## Implementation Order

1. `config.py` — YAML loading + validation
2. `availability.py` — API availability checker
3. `booker.py` — Playwright booking automation
4. `checker.py` — CLI entry point wiring it all together
5. `checker_example.yaml` + `requirements.txt` + `.gitignore` updates
6. `README.md` — updated documentation
