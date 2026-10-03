"""Plain-code tools the agents call: search, Life Passport checks, transport, pricing.

These are deterministic on purpose, so the demo gives the same answer every time.
The LLM only handles language and photos; the money math lives here.
"""

from __future__ import annotations

import math
import re
from collections import Counter

from .data.catalog import CITIES, all_cars, car_history, market_value
from .schemas import BuyerRequest

EXPORT_FRIENDLY = {"Camry", "Corolla", "Accord", "Civic", "RAV4", "CR-V", "Highlander", "Tacoma"}


# --- Search ------------------------------------------------------------------

def search_marketplace(source: str, req: BuyerRequest) -> dict:
    """Search one marketplace. Returns the live count, candidates, and skip reasons."""
    live = [c for c in all_cars() if c["source"] == source]
    skipped: Counter = Counter()
    candidates = []
    for car in live:
        if req.make and car["make"].lower() != req.make.lower():
            continue
        if req.model and _norm(car["model"]) != _norm(req.model):
            continue
        if req.min_year and car["year"] < req.min_year:
            skipped["too old"] += 1
        elif req.max_year and car["year"] > req.max_year:
            skipped["too new"] += 1
        elif req.max_price and car["price"] > req.max_price:
            skipped["over budget"] += 1
        elif req.max_mileage and car["mileage"] > req.max_mileage:
            skipped["too many miles"] += 1
        elif req.title == "clean" and car["title_status"] != "clean":
            skipped["salvage title"] += 1
        else:
            candidates.append(car)
    return {"source": source, "live_count": len(live), "candidates": candidates, "skipped": dict(skipped)}


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


# --- Life Passport -----------------------------------------------------------

def check_passport(car: dict) -> dict:
    """Join ACV + Copart records for one VIN and flag anything the listing hides."""
    timeline = sorted(car_history(car["vin"]), key=lambda e: e["date"])
    flags = []
    if car["title_status"] == "clean":
        for e in timeline:
            text = (e["event"] + " " + e["detail"]).lower()
            if e["source"] == "Copart" and ("total loss" in text or "salvage" in text):
                damage = e["event"].split(":")[-1].strip() if ":" in e["event"] else "damage"
                flags.append({
                    "type": "hidden_salvage",
                    "text": f"Sold as salvage on Copart in {e['date'][:4]} ({damage}). "
                            f"Listing shows a clean title.",
                })
                break
    for e in timeline:
        if e.get("mileage") and e["mileage"] > car["mileage"] + 1000:
            flags.append({
                "type": "odometer_rollback",
                "text": f"Odometer read {e['mileage']:,} mi in {e['date'][:4]}; "
                        f"now it reads {car['mileage']:,} mi.",
            })
            break
    return {"car_id": car["id"], "status": "flagged" if flags else "clean", "flags": flags,
            "timeline": timeline}


# --- Transport ---------------------------------------------------------------

def _miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 3958.8
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a)) * 1.18  # road-distance fudge factor


def transport_quote(car: dict, dest_city: str) -> dict:
    _, lat, lon = CITIES.get(dest_city, CITIES["Buffalo"])
    miles = _miles(car["lat"], car["lon"], lat, lon)
    cost = int(round((125 + 0.95 * miles) / 5) * 5)
    days = 1 if miles <= 150 else 2 if miles <= 400 else 3
    return {"miles": int(miles), "cost": cost, "days": days}


# --- Ranking + bids ----------------------------------------------------------

def rank_matches(cars: list[dict], req: BuyerRequest) -> list[dict]:
    """Best value first: price under market, condition, and delivery cost."""
    ranked = []
    for car in cars:
        quote = transport_quote(car, req.destination_city)
        discount = (car["market_value"] - car["price"]) / max(car["market_value"], 1)
        score = discount * 100 + car["condition_grade"] * 6 - quote["cost"] / 40
        # Bid up to ~95% of market value, never above the buyer's budget.
        bid = max(car["price"], int(car["market_value"] * 0.95 // 100 * 100))
        if req.max_price:
            bid = min(bid, req.max_price)
        ranked.append({**car, "transport": quote, "score": round(score, 1), "recommended_bid": bid})
    return sorted(ranked, key=lambda c: c["score"], reverse=True)


# --- Seller: best path -------------------------------------------------------

def condition_factor(grade: float) -> float:
    return {5: 1.05, 4: 1.0, 3: 0.9, 2: 0.72, 1: 0.5}[max(1, min(5, round(grade)))]


def best_paths(make: str, model: str, year: int, mileage: int, grade: float,
               lot_fit: bool = False) -> dict:
    """Net money from each way to sell one car, after fees, transport and waiting."""
    value = int(market_value(make, model, year, mileage) * condition_factor(grade))
    holding_per_day = 28
    retail_days = 30 if lot_fit else 55  # a Camry on a truck lot sits longer
    export_factor = 0.88 if model in EXPORT_FRIENDLY else 0.75
    rows = [
        {"channel": "Keep & retail on your lot", "gross": int(value * 1.08), "fees": 600,
         "transport": 0, "days": retail_days, "note": "Recon + waiting for a walk-in buyer"},
        {"channel": "ACV dealer auction", "gross": int(value * 0.95), "fees": 350,
         "transport": 0, "days": 3, "note": "20-minute auction, buyer pays transport"},
        {"channel": "Copart as-is", "gross": int(value * 0.78), "fees": 250,
         "transport": 0, "days": 7, "note": "Global buyers, priced as-is"},
        {"channel": "Export via Copart buyers", "gross": int(value * export_factor), "fees": 300,
         "transport": 450, "days": 14, "note": "Truck to port, overseas buyer"},
    ]
    for r in rows:
        r["holding"] = r["days"] * holding_per_day
        r["net"] = r["gross"] - r["fees"] - r["transport"] - r["holding"]
    best = max(rows, key=lambda r: r["net"])
    for r in rows:
        r["best"] = r is best
    return {"market_value": value, "rows": rows, "best": best["channel"]}


# --- Matching (used by early pre-match) --------------------------------------

def wish_matches(wish: dict, car: dict) -> tuple[bool, str]:
    if wish.get("make") and wish["make"].lower() != car["make"].lower():
        return False, "different make"
    if wish.get("model") and _norm(wish["model"]) != _norm(car["model"]):
        return False, "different model"
    if wish.get("min_year") and car["year"] < wish["min_year"]:
        return False, "too old"
    if wish.get("max_year") and car["year"] > wish["max_year"]:
        return False, "too new"
    if wish.get("max_price") and car["price"] > wish["max_price"]:
        return False, "over budget"
    if wish.get("max_mileage") and car["mileage"] > wish["max_mileage"]:
        return False, "too many miles"
    if wish.get("title", "clean") == "clean" and car.get("title_status", "clean") != "clean":
        return False, "not a clean title"
    return True, "match"
