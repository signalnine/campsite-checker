"""Automate the recreation.gov booking flow with Playwright."""

import sys
from datetime import date
from pathlib import Path
from typing import Dict

from playwright.sync_api import sync_playwright, Page, TimeoutError as PwTimeout

SCREENSHOTS_DIR = Path("screenshots")

# Map friendly equipment names to recreation.gov select values
EQUIPMENT_MAP = {
    "tent": "Tent",
    "rv": "RV/Motorhome",
    "trailer": "Trailer",
    "fifth_wheel": "Fifth Wheel",
    "popup": "Pop up",
    "pickup_camper": "Pickup Camper",
    "caravan": "Caravan/Camper Van",
    "none": "",
}


def book_site(
    facility_id: str,
    campsite_id: str,
    site_name: str,
    arrival_date: date,
    length_of_stay: int,
    num_occupants: int,
    num_vehicles: int,
    equipment_type: str,
    username: str,
    password: str,
    headed: bool = False,
) -> bool:
    """Attempt to book a campsite. Returns True if checkout was reached."""
    SCREENSHOTS_DIR.mkdir(exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not headed)
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()

        try:
            success = _run_booking_flow(
                page=page,
                facility_id=facility_id,
                campsite_id=campsite_id,
                site_name=site_name,
                arrival_date=arrival_date,
                length_of_stay=length_of_stay,
                num_occupants=num_occupants,
                num_vehicles=num_vehicles,
                equipment_type=equipment_type,
                username=username,
                password=password,
            )
            return success
        except PwTimeout as e:
            print(f"  Timeout during booking: {e}")
            _screenshot(page, "timeout")
            return False
        except Exception as e:
            print(f"  Booking error: {e}")
            _screenshot(page, "error")
            return False
        finally:
            if headed and page:
                print("  Browser left open — complete payment manually.")
                print("  Press Enter to close the browser when done.")
                try:
                    input()
                except (EOFError, KeyboardInterrupt):
                    pass
            browser.close()


def _run_booking_flow(
    page: Page,
    facility_id: str,
    campsite_id: str,
    site_name: str,
    arrival_date: date,
    length_of_stay: int,
    num_occupants: int,
    num_vehicles: int,
    equipment_type: str,
    username: str,
    password: str,
) -> bool:
    """Execute the step-by-step booking flow. Returns True on success."""
    departure_date = arrival_date + __import__("datetime").timedelta(days=length_of_stay)

    # Step 1: Navigate to the campsite page with dates
    arv_str = arrival_date.strftime("%Y-%m-%d")
    dep_str = departure_date.strftime("%Y-%m-%d")
    url = (
        f"https://www.recreation.gov/camping/campsites/{campsite_id}"
        f"?startDate={arv_str}&endDate={dep_str}"
    )
    print(f"  Navigating to {site_name} (campsite {campsite_id})...")
    page.goto(url, wait_until="networkidle", timeout=30000)

    # Step 2: Click "Book Now" or "Add to Cart"
    print("  Looking for booking button...")
    book_btn = page.locator("button:has-text('Book Now'), button:has-text('Add to Cart')")
    book_btn.first.click(timeout=15000)
    page.wait_for_load_state("networkidle", timeout=15000)

    # Step 3: Handle login if prompted
    if _needs_login(page):
        print("  Logging in...")
        _do_login(page, username, password)

    # Step 4: Fill booking details if form is present
    _fill_booking_details(page, num_occupants, num_vehicles, equipment_type)

    # Step 5: Accept agreements if present
    _accept_agreements(page)

    # Step 6: Proceed to cart / checkout
    _proceed_to_checkout(page)

    print("  Booking reached checkout!")
    return True


def _needs_login(page: Page) -> bool:
    """Check if the page is showing a login form."""
    try:
        page.locator("input[type='email'], #email, input[name='email']").wait_for(
            state="visible", timeout=3000
        )
        return True
    except PwTimeout:
        return False


def _do_login(page: Page, username: str, password: str):
    """Fill and submit the login form."""
    # Email field
    email_input = page.locator(
        "input[type='email'], #email, input[name='email']"
    ).first
    email_input.fill(username)

    # Some flows have a "next" button before the password field
    next_btn = page.locator("button:has-text('Next'), button:has-text('Continue')")
    if next_btn.count() > 0:
        next_btn.first.click()
        page.wait_for_load_state("networkidle", timeout=10000)

    # Password field
    pw_input = page.locator(
        "input[type='password'], #password, input[name='password']"
    ).first
    pw_input.wait_for(state="visible", timeout=10000)
    pw_input.fill(password)

    # Submit
    submit_btn = page.locator(
        "button[type='submit'], button:has-text('Log In'), button:has-text('Sign In')"
    ).first
    submit_btn.click()
    page.wait_for_load_state("networkidle", timeout=15000)


def _fill_booking_details(page: Page, num_occupants: int, num_vehicles: int, equipment_type: str):
    """Fill in occupants, vehicles, and equipment if the form is present."""
    # Occupants
    occ = page.locator("#num-occupants, [name='numOccupants'], [data-testid='num-occupants']")
    if occ.count() > 0:
        occ.first.fill(str(num_occupants))

    # Vehicles
    veh = page.locator("#num-vehicles, [name='numVehicles'], [data-testid='num-vehicles']")
    if veh.count() > 0:
        veh.first.fill(str(num_vehicles))

    # Equipment type
    equip_label = EQUIPMENT_MAP.get(equipment_type, "")
    if equip_label:
        equip = page.locator("select#equipment, select[name='equipment']")
        if equip.count() > 0:
            equip.first.select_option(label=equip_label)


def _accept_agreements(page: Page):
    """Check any agreement checkboxes."""
    checkboxes = page.locator(
        "input[type='checkbox'][id*='agree'], "
        "input[type='checkbox'][name*='agree'], "
        "input[type='checkbox'][data-testid*='agree']"
    )
    for i in range(checkboxes.count()):
        if not checkboxes.nth(i).is_checked():
            checkboxes.nth(i).check()


def _proceed_to_checkout(page: Page):
    """Click through to checkout."""
    checkout_btn = page.locator(
        "button:has-text('Continue to Shopping Cart'), "
        "button:has-text('Proceed to Cart'), "
        "button:has-text('Continue'), "
        "button:has-text('Checkout')"
    )
    if checkout_btn.count() > 0:
        checkout_btn.first.click()
        page.wait_for_load_state("networkidle", timeout=15000)


def _screenshot(page: Page, label: str):
    """Save a debug screenshot."""
    path = SCREENSHOTS_DIR / f"{label}.png"
    try:
        page.screenshot(path=str(path))
        print(f"  Screenshot saved: {path}")
    except Exception:
        pass
