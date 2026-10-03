"""Negotiation and deal-closing math (deterministic; the LLM only writes the words).

Each side tells its own agent a private limit (seller minimum, buyer maximum).
The mediator never reveals those limits; it moves both sides toward market value
in rounds, and can close a small last gap with a non-price lever: a truck that is
already heading that way (backhaul), which lowers the buyer's delivery cost.
"""

from __future__ import annotations

from .data.catalog import market_value
from .tools import condition_factor

HOLDING_PER_DAY = 28
DEPRECIATION_PER_MONTH = 0.012
MAX_ROUNDS = 4


def round50(x: float) -> int:
    return int(round(x / 50.0) * 50)


def fair_value(make: str, model: str, year: int, mileage: int, grade: float) -> int:
    return round50(market_value(make, model, year, mileage) * condition_factor(grade))


def comparable_sales(make: str, model: str, year: int, mileage: int, grade: float) -> list[dict]:
    """Three recent comparable sales around fair value (demo data)."""
    fv = fair_value(make, model, year, mileage, grade)
    rows = [(year, mileage - 8000, 1.03, 6), (year, mileage + 5000, 0.98, 11), (year - 1, mileage + 12000, 0.95, 19)]
    return [{"desc": f"{y} {make} {model}, {max(m, 1000):,} mi", "price": round50(fv * f), "days_ago": d}
            for y, m, f, d in rows]


def seller_offer(ask: int, floor: int, t: int) -> int:
    """Seller concedes quickly at first, then slowly toward their private minimum."""
    return max(floor, round50(floor + (ask - floor) * (0.55 ** t)))


def buyer_offer(bid: int, cap: int, t: int) -> int:
    """Buyer raises toward their private maximum, a bit less each round."""
    return min(cap, round50(bid + (cap - bid) * (1 - 0.6 ** t)))


def waiting_cost_per_week(price: int) -> int:
    return int(HOLDING_PER_DAY * 7 + price * DEPRECIATION_PER_MONTH / 4.3)


def acv_fees(price: int, transport: int) -> dict:
    """Illustrative fee model: ACV earns only when the car actually sells."""
    buyer_fee = min(650, 250 + round(price * 0.02 / 10) * 10)
    seller_fee = 350
    transport_margin = int(transport * 0.15)
    return {"buyer_fee": buyer_fee, "seller_fee": seller_fee, "transport_margin": transport_margin,
            "total": buyer_fee + seller_fee + transport_margin}


def closing_plan(price: int, transport: int, lien: int) -> dict:
    fees = acv_fees(price, transport)
    insurance = max(25, round(price * 0.0025))
    return {
        "price": price,
        "buyer_pays": price + fees["buyer_fee"] + transport + insurance,
        "insurance_premium": insurance,
        "transport": transport,
        "lien_payoff": lien,
        "seller_payout": price - fees["seller_fee"] - lien,
        "acv": fees,
    }
