"""Check campsite availability via recreation.gov's frontend API."""

from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple

import requests

BASE_URL = "https://www.recreation.gov/api/camps/availability/campground"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}


def check_availability(
    facility_id: str,
    arrival_date: date,
    length_of_stay: int,
    campsite_ids: Optional[List[str]] = None,
) -> List[Dict]:
    """Check availability for a campground.

    Returns a list of dicts with keys: campsite_id, site_name, for each
    site that is fully available for the requested dates.
    """
    needed_dates = [
        arrival_date + timedelta(days=d) for d in range(length_of_stay)
    ]

    # Determine which months we need to query
    months = _months_covering(needed_dates)

    # Fetch availability for each month and merge
    all_sites: Dict[str, Dict[str, str]] = {}  # campsite_id -> {date_str: status}
    site_names: Dict[str, str] = {}

    for month_start in months:
        data = _fetch_month(facility_id, month_start)
        if data is None:
            continue

        campsites = data.get("campsites", {})
        for cid, site_info in campsites.items():
            if cid not in all_sites:
                all_sites[cid] = {}
                site_names[cid] = site_info.get("site", cid)
            availabilities = site_info.get("availabilities", {})
            for date_str, status in availabilities.items():
                all_sites[cid][date_str] = status

    # Filter to requested campsite_ids if specified
    if campsite_ids:
        all_sites = {k: v for k, v in all_sites.items() if k in campsite_ids}

    # Check which sites are fully available
    available = []
    for cid, avails in all_sites.items():
        if _is_available(avails, needed_dates):
            available.append({
                "campsite_id": cid,
                "site_name": site_names.get(cid, cid),
            })

    return available


def _fetch_month(facility_id: str, month_start: date) -> Optional[Dict]:
    """Fetch availability data for a single month."""
    start_str = f"{month_start.strftime('%Y-%m-%d')}T00:00:00.000Z"
    url = f"{BASE_URL}/{facility_id}/month"
    params = {"start_date": start_str}

    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        print(f"  Warning: API request failed for facility {facility_id}, "
              f"month {month_start}: {e}")
        return None


def _months_covering(dates: List[date]) -> List[date]:
    """Return the first-of-month dates needed to cover all requested dates."""
    months = set()
    for d in dates:
        months.add(d.replace(day=1))
    return sorted(months)


def _is_available(avails: Dict[str, str], needed_dates: List[date]) -> bool:
    """Check if all needed dates show as Available."""
    for d in needed_dates:
        # The API returns keys like "2026-07-11T00:00:00Z"
        key = f"{d.strftime('%Y-%m-%d')}T00:00:00Z"
        status = avails.get(key, "")
        if status != "Available":
            return False
    return True
