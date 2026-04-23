"""Tests for booker helpers that do not require a real browser.

booker.py imports playwright at module scope, so we stub the module in
sys.modules before the first import. This lets the test run in CI or any
environment where playwright (and the chromium binary) are not installed.
"""

import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if "playwright" not in sys.modules:
    _fake_pw = types.ModuleType("playwright")
    _fake_pw_sync = types.ModuleType("playwright.sync_api")
    _fake_pw_sync.sync_playwright = MagicMock()
    _fake_pw_sync.Page = object

    class _FakeTimeout(Exception):
        pass

    _fake_pw_sync.TimeoutError = _FakeTimeout
    _fake_pw.sync_api = _fake_pw_sync
    sys.modules["playwright"] = _fake_pw
    sys.modules["playwright.sync_api"] = _fake_pw_sync

import booker  # noqa: E402


def _page_with_button_count(count):
    page = MagicMock()
    locator = MagicMock()
    locator.count.return_value = count
    page.locator.return_value = locator
    return page, locator


def test_proceed_to_checkout_raises_when_no_button_present():
    """Regression: the booker used to silently skip when no 'Continue/Checkout'
    button matched, then _run_booking_flow returned True and the caller
    recorded a successful booking that never happened."""
    page, locator = _page_with_button_count(0)

    with pytest.raises(RuntimeError):
        booker._proceed_to_checkout(page)

    locator.first.click.assert_not_called()
    page.wait_for_load_state.assert_not_called()


def test_proceed_to_checkout_clicks_when_button_present():
    page, locator = _page_with_button_count(1)

    booker._proceed_to_checkout(page)

    locator.first.click.assert_called_once()
    page.wait_for_load_state.assert_called_once()
