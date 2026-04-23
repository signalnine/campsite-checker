"""Tests for config.load_config validation."""

import sys
from pathlib import Path
from textwrap import dedent

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import load_config


def _write_config(tmp_path, body):
    path = tmp_path / "checker.yaml"
    path.write_text(dedent(body))
    return path


VALID_BODY = """
    account:
      username: u
      password: p
    reservations:
      - name: test
        facility_id: 232447
        arrival_date: "2026-07-11"
        length_of_stay: {length_of_stay}
        num_occupants: {num_occupants}
        num_vehicles: {num_vehicles}
        equipment_type: tent
"""


def test_rejects_zero_length_of_stay(tmp_path):
    path = _write_config(tmp_path, VALID_BODY.format(
        length_of_stay=0, num_occupants=2, num_vehicles=1,
    ))
    with pytest.raises(SystemExit):
        load_config(path)


def test_rejects_negative_length_of_stay(tmp_path):
    path = _write_config(tmp_path, VALID_BODY.format(
        length_of_stay=-1, num_occupants=2, num_vehicles=1,
    ))
    with pytest.raises(SystemExit):
        load_config(path)


def test_rejects_zero_num_occupants(tmp_path):
    path = _write_config(tmp_path, VALID_BODY.format(
        length_of_stay=3, num_occupants=0, num_vehicles=1,
    ))
    with pytest.raises(SystemExit):
        load_config(path)


def test_rejects_negative_num_vehicles(tmp_path):
    path = _write_config(tmp_path, VALID_BODY.format(
        length_of_stay=3, num_occupants=2, num_vehicles=-1,
    ))
    with pytest.raises(SystemExit):
        load_config(path)


def test_accepts_zero_num_vehicles(tmp_path):
    """Walk-in campers legitimately have zero vehicles."""
    path = _write_config(tmp_path, VALID_BODY.format(
        length_of_stay=3, num_occupants=2, num_vehicles=0,
    ))
    cfg = load_config(path)
    assert cfg.reservations[0].num_vehicles == 0


def test_accepts_valid_config(tmp_path):
    path = _write_config(tmp_path, VALID_BODY.format(
        length_of_stay=3, num_occupants=2, num_vehicles=1,
    ))
    cfg = load_config(path)
    assert cfg.reservations[0].length_of_stay == 3
    assert cfg.reservations[0].num_occupants == 2
    assert cfg.reservations[0].num_vehicles == 1
