"""Tiny JSON store for the agents' memory: saved buyer wishes, listings, notifications.

One file, single user, good enough for a local demo. `reset()` restores the seed.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime

from .config import RUNTIME_DIR

STATE_FILE = RUNTIME_DIR / "state.json"

SEED_WISHES = [
    {"id": "wish-seed-1", "buyer": "Niagara Auto Group", "buyer_city": "Buffalo",
     "channel": "ACV", "make": "Toyota", "model": "Camry", "min_year": 2017, "max_year": None,
     "max_price": 12500, "max_mileage": 90000, "title": "clean", "quantity": 2,
     "created": "2026-10-01 09:12", "source": "seed"},
    {"id": "wish-seed-2", "buyer": "Gulf Coast Exports (Dubai)", "buyer_city": "Dubai",
     "channel": "Copart global", "make": "Toyota", "model": None, "min_year": 2016, "max_year": None,
     "max_price": 11500, "max_mileage": 120000, "title": "clean", "quantity": 10,
     "created": "2026-09-29 16:40", "source": "seed"},
]


def _empty() -> dict:
    return {"wishes": [dict(w) for w in SEED_WISHES], "listings": [], "notifications": [], "bids": []}


def load() -> dict:
    if not STATE_FILE.exists():
        return _empty()
    try:
        return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return _empty()


def save(state: dict) -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def reset() -> None:
    save(_empty())


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def add_wish(wish: dict) -> dict:
    state = load()
    wish = {"id": f"wish-{uuid.uuid4().hex[:6]}", "created": _now(), "source": "agent", **wish}
    state["wishes"].append(wish)
    save(state)
    return wish


def wishes() -> list[dict]:
    return load()["wishes"]


def add_listing(listing: dict) -> dict:
    state = load()
    listing = {"id": f"ACV-{30000 + len(state['listings'])}", "created": _now(), **listing}
    state["listings"].append(listing)
    save(state)
    return listing


def listings() -> list[dict]:
    return load()["listings"]


def add_bids(bids: list[dict]) -> None:
    state = load()
    state["bids"].extend({"created": _now(), **b} for b in bids)
    save(state)


def notify(to: str, text: str, kind: str = "info") -> dict:
    state = load()
    note = {"id": uuid.uuid4().hex[:8], "to": to, "text": text, "kind": kind, "created": _now()}
    state["notifications"].insert(0, note)
    save(state)
    return note


def notifications() -> list[dict]:
    return load()["notifications"]
