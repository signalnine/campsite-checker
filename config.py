"""Load and validate checker.yaml configuration."""

import sys
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import List, Optional

import yaml

CONFIG_PATH = Path("checker.yaml")

VALID_EQUIPMENT = {
    "tent", "rv", "trailer", "fifth_wheel", "popup",
    "pickup_camper", "caravan", "none",
}


@dataclass
class Account:
    username: str
    password: str


@dataclass
class Reservation:
    facility_id: str
    arrival_date: date
    length_of_stay: int
    num_occupants: int
    num_vehicles: int
    equipment_type: str
    name: Optional[str] = None
    campsite_ids: List[str] = field(default_factory=list)


@dataclass
class Config:
    account: Account
    reservations: List[Reservation]


def load_config(path: Path = CONFIG_PATH) -> Config:
    """Load and validate the YAML config file."""
    if not path.exists():
        print(f"Error: config file '{path}' not found.")
        print("Copy checker_example.yaml to checker.yaml and edit it.")
        sys.exit(1)

    with open(path) as f:
        raw = yaml.safe_load(f)

    if not isinstance(raw, dict):
        _die("Config file must be a YAML mapping.")

    # Account
    acct = raw.get("account")
    if not acct or not acct.get("username") or not acct.get("password"):
        _die("'account' section must have 'username' and 'password'.")
    account = Account(username=acct["username"], password=acct["password"])

    # Reservations
    raw_reservations = raw.get("reservations")
    if not raw_reservations or not isinstance(raw_reservations, list):
        _die("'reservations' must be a non-empty list.")

    reservations = []
    for i, r in enumerate(raw_reservations, 1):
        label = r.get("name", f"reservation #{i}")
        missing = [
            k for k in ("facility_id", "arrival_date", "length_of_stay",
                         "num_occupants", "num_vehicles", "equipment_type")
            if k not in r
        ]
        if missing:
            _die(f"Reservation '{label}' missing fields: {', '.join(missing)}")

        arv = r["arrival_date"]
        if isinstance(arv, str):
            try:
                arv = datetime.strptime(arv, "%Y-%m-%d").date()
            except ValueError:
                _die(f"Reservation '{label}': arrival_date must be YYYY-MM-DD.")
        elif isinstance(arv, date):
            pass  # YAML may auto-parse dates
        else:
            _die(f"Reservation '{label}': invalid arrival_date.")

        equip = str(r["equipment_type"]).lower().strip()
        if equip not in VALID_EQUIPMENT:
            _die(f"Reservation '{label}': equipment_type '{equip}' not valid. "
                 f"Options: {', '.join(sorted(VALID_EQUIPMENT))}")

        campsite_ids = r.get("campsite_ids", [])
        if not isinstance(campsite_ids, list):
            campsite_ids = [str(campsite_ids)]
        campsite_ids = [str(c) for c in campsite_ids]

        reservations.append(Reservation(
            name=r.get("name"),
            facility_id=str(r["facility_id"]),
            arrival_date=arv,
            length_of_stay=int(r["length_of_stay"]),
            num_occupants=int(r["num_occupants"]),
            num_vehicles=int(r["num_vehicles"]),
            equipment_type=equip,
            campsite_ids=campsite_ids,
        ))

    return Config(account=account, reservations=reservations)


def _die(msg: str):
    print(f"Config error: {msg}")
    sys.exit(1)
