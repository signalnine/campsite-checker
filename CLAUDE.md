# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A Python script that checks recreation.gov for campsite availability via their undocumented frontend API, then auto-books using Playwright browser automation. Payment is completed manually by the user.

## Setup

```bash
pip install -r requirements.txt
playwright install chromium
```

## Running

```bash
python3 checker.py                              # check once
python3 checker.py --poll 60                    # poll every 60s
python3 checker.py --poll 60 --max-retries 50   # with retry limit
python3 checker.py --headed                     # visible browser for debugging
python3 checker.py --config my-config.yaml      # custom config file
```

There are no tests, linter, or build system configured.

## Architecture

Two-layer design:

1. **Availability layer** (`availability.py`) — Pure HTTP requests to `recreation.gov/api/camps/availability/campground/{facility_id}/month`. No auth needed. Fetches monthly availability data, checks that all dates in the stay window show "Available".

2. **Booking layer** (`booker.py`) — Playwright browser automation. Navigates to campsite page, logs in, fills booking details, proceeds to checkout. Saves screenshots to `screenshots/` on failure.

**Orchestration** (`checker.py`) — CLI entry point. Loads config, loops through reservations, calls availability check then booker. Handles polling/retry logic.

**Config** (`config.py`) — Loads `checker.yaml` (YAML format) into dataclasses (`Config`, `Account`, `Reservation`). Validates required fields, date formats, and equipment types.

## Config

User config goes in `checker.yaml` (gitignored). See `checker_example.yaml` for the format. Key fields: `account` (username/password), `reservations` list with `facility_id`, `arrival_date`, `length_of_stay`, optional `campsite_ids` to target specific sites.

## Exit Codes

- 0: Booking reached checkout
- 1: No availability / retries exhausted
- 2: Availability was found but every booking attempt failed
