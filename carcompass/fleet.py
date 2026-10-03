"""Fleet remarketing: distribute a big batch of similar cars at the lowest logistics cost.

A rental fleet sells hundreds of 2–3-year-old cars at once. Two things lose money:
  * flooding one market (every extra similar car above what it can absorb lowers the price)
  * shipping cars one by one (a car hauler carries 9; a single-car move costs far more per car)
The planner sends full truckloads to nearby markets that still have demand,
spreads volume over the weeks, and compares against the two naive plans.
"""

from __future__ import annotations

import math
import random

from .data.catalog import CITIES, market_value
from .tools import _miles, condition_factor, transport_quote

FLEET_MODELS = [("Nissan", "Altima"), ("Toyota", "Corolla"), ("Chevrolet", "Malibu"),
                ("Hyundai", "Elantra"), ("Nissan", "Rogue"), ("Ford", "Escape")]

# city: (similar cars it absorbs per week at full price, local price index)
MARKET_DEMAND = {
    "New York": (14, 1.04), "Philadelphia": (12, 1.03), "Detroit": (10, 0.98), "Columbus": (9, 1.01),
    "Cleveland": (9, 1.00), "Pittsburgh": (8, 1.01), "Buffalo": (6, 0.99), "Rochester": (5, 1.00),
    "Albany": (5, 1.02), "Syracuse": (4, 1.00), "Toledo": (4, 0.98), "Harrisburg": (4, 1.02),
    "Akron": (3, 0.99), "Scranton": (3, 1.01), "Erie": (3, 0.99), "Binghamton": (2, 1.00),
}

TRUCK_CAPACITY = 9
TRUCK_BASE = 150
TRUCK_PER_MILE = 2.4
LOCAL_LANE_COST = 75          # drive a car to the local auction lane
PRICE_DROP_PER_EXTRA = 0.015  # each similar car above weekly demand lowers the price 1.5%
PRICE_FLOOR = 0.75


def make_fleet(n: int, lots: list[str], models: list[tuple[str, str]], seed: int = 7) -> list[dict]:
    rng = random.Random(seed)
    cars = []
    for i in range(n):
        make, model = models[i % len(models)]
        mileage = rng.randint(31000, 46000)
        grade = round(rng.uniform(3.5, 4.3), 1)
        value = int(market_value(make, model, 2023, mileage) * condition_factor(grade))
        cars.append({"id": f"FLT-{1000 + i}", "year": 2023, "make": make, "model": model,
                     "mileage": mileage, "grade": grade, "lot": lots[i % len(lots)], "value": value})
    return cars


def _city_miles(a: str, b: str) -> float:
    _, la, lo = CITIES[a]
    _, lb, lob = CITIES[b]
    return 0.0 if a == b else _miles(la, lo, lb, lob)


def _price(value: int, market: str, nth: int, capacity: int) -> float:
    """Price of the nth similar car sent to a market that absorbs `capacity` at full price."""
    _, index = MARKET_DEMAND[market]
    drop = max(0, nth - capacity) * PRICE_DROP_PER_EXTRA
    return value * index * max(PRICE_FLOOR, 1 - drop)


def plan_distribution(cars: list[dict], weeks: int) -> dict:
    """Greedy: repeatedly send the truckload with the best net per car."""
    remaining = {lot: sorted([c for c in cars if c["lot"] == lot], key=lambda c: -c["value"])
                 for lot in sorted({c["lot"] for c in cars})}
    counts = {m: 0 for m in MARKET_DEMAND}
    caps = {m: MARKET_DEMAND[m][0] * weeks for m in MARKET_DEMAND}
    loads = []
    while any(remaining.values()):
        best = None
        for lot, todo in remaining.items():
            if not todo:
                continue
            batch = todo[:TRUCK_CAPACITY]
            for m in MARKET_DEMAND:
                miles = _city_miles(lot, m)
                cost = LOCAL_LANE_COST * len(batch) if m == lot else TRUCK_BASE + TRUCK_PER_MILE * miles
                revenue = sum(_price(c["value"], m, counts[m] + j + 1, caps[m]) for j, c in enumerate(batch))
                per_car = (revenue - cost) / len(batch)
                if best is None or per_car > best[0]:
                    best = (per_car, lot, m, batch, cost, revenue, miles)
        _, lot, m, batch, cost, revenue, miles = best
        first_week = counts[m] // max(MARKET_DEMAND[m][0], 1) + 1
        counts[m] += len(batch)
        loads.append({"from": lot, "to": m, "cars": len(batch), "miles": int(miles),
                      "transport": int(cost), "revenue": int(revenue), "week": min(first_week, weeks),
                      "truck": m != lot, "car_ids": [c["id"] for c in batch]})
        remaining[lot] = remaining[lot][len(batch):]
    return _summarize("CarCompass plan", loads)


def plan_dump_local(cars: list[dict]) -> dict:
    """Naive 1: every car goes to the auction lane next to its lot, all at once."""
    loads, counts = [], {}
    for c in cars:
        counts[c["lot"]] = counts.get(c["lot"], 0) + 1
        rev = _price(c["value"], c["lot"], counts[c["lot"]], MARKET_DEMAND[c["lot"]][0])
        loads.append({"from": c["lot"], "to": c["lot"], "cars": 1, "miles": 0, "transport": LOCAL_LANE_COST,
                      "revenue": int(rev), "week": 1, "truck": False, "car_ids": [c["id"]]})
    return _summarize("Dump at the local auction", loads)


def plan_one_by_one(cars: list[dict], weeks: int) -> dict:
    """Naive 2: each car shipped alone to wherever it sells best."""
    counts = {m: 0 for m in MARKET_DEMAND}
    caps = {m: MARKET_DEMAND[m][0] * weeks for m in MARKET_DEMAND}
    loads = []
    for c in sorted(cars, key=lambda c: -c["value"]):
        _, lat, lon = CITIES[c["lot"]]
        best = None
        for m in MARKET_DEMAND:
            cost = LOCAL_LANE_COST if m == c["lot"] else transport_quote({"lat": lat, "lon": lon}, m)["cost"]
            net = _price(c["value"], m, counts[m] + 1, caps[m]) - cost
            if best is None or net > best[0]:
                best = (net, m, cost)
        _, m, cost = best
        counts[m] += 1
        loads.append({"from": c["lot"], "to": m, "cars": 1, "miles": int(_city_miles(c["lot"], m)),
                      "transport": int(cost), "revenue": int(_price(c["value"], m, counts[m], caps[m])),
                      "week": 1, "truck": m != c["lot"], "car_ids": [c["id"]]})
    return _summarize("Ship one by one", loads)


def _summarize(name: str, loads: list[dict]) -> dict:
    cars = sum(l["cars"] for l in loads)
    revenue = sum(l["revenue"] for l in loads)
    transport = sum(l["transport"] for l in loads)
    return {"name": name, "loads": loads, "cars": cars, "revenue": revenue, "transport": transport,
            "net": revenue - transport, "transport_per_car": transport // max(cars, 1),
            "avg_price": revenue // max(cars, 1), "trucks": sum(1 for l in loads if l["truck"]),
            "markets": len({l["to"] for l in loads})}


def routes(plan: dict) -> list[dict]:
    """Group a plan's loads into lot → market routes for display."""
    grouped: dict[tuple, dict] = {}
    for l in plan["loads"]:
        key = (l["from"], l["to"])
        g = grouped.setdefault(key, {"from": l["from"], "to": l["to"], "cars": 0, "trucks": 0, "miles": l["miles"],
                                     "transport": 0, "revenue": 0, "weeks": set()})
        g["cars"] += l["cars"]
        g["trucks"] += 1 if l["truck"] else 0
        g["transport"] += l["transport"]
        g["revenue"] += l["revenue"]
        g["weeks"].add(l["week"])
    out = []
    for g in grouped.values():
        out.append({**g, "per_car": g["transport"] // g["cars"], "weeks": ", ".join(f"wk {w}" for w in sorted(g["weeks"]))})
    return sorted(out, key=lambda r: -r["cars"])


def total_capacity(weeks: int) -> int:
    return sum(c for c, _ in MARKET_DEMAND.values()) * weeks


def trucks_needed(n: int) -> int:
    return math.ceil(n / TRUCK_CAPACITY)
