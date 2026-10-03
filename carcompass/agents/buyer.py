"""Buyer's agent: a plain-English wish in, approved bids out.

LangGraph flow:

    understand_request -> search_marketplaces -> check_life_passports
        -> (explain_flags if anything was flagged) -> rank_and_quote
        -> (widen_search -> search again, once, if nothing matched)
        -> await_approval  [human-in-the-loop interrupt]
        -> execute (bids, transport, title checks, keep watching for the rest)

Claude is used to understand the request and to explain flagged cars. Search,
history checks and money math are plain code, so results are repeatable.
"""

from __future__ import annotations

import operator
from typing import Annotated, Optional, TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from .. import store
from ..llm import explain_risk, parse_request
from ..schemas import BuyerRequest
from ..tools import check_passport, rank_matches, search_marketplace


class BuyerState(TypedDict, total=False):
    request_text: str
    buyer_name: str
    demo_safe: bool
    request: dict
    searches: list[dict]
    candidates: list[dict]
    flagged: list[dict]
    clean: list[dict]
    matches: list[dict]
    widened: bool
    decision: dict
    result: dict
    log: Annotated[list[dict], operator.add]


def _log(icon: str, text: str, detail: Optional[str] = None, ai: Optional[str] = None) -> dict:
    return {"icon": icon, "text": text, "detail": detail, "ai": ai}


def _skips(skipped: dict) -> str:
    return ", ".join(f"{n} {why}" for why, n in skipped.items()) or "none"


# --- Nodes -------------------------------------------------------------------

def understand_request(state: BuyerState) -> dict:
    req, source = parse_request(state["request_text"], state.get("demo_safe", False))
    return {"request": req.model_dump(), "widened": False,
            "log": [_log("✓", "Understood the request", req.summary(), ai=source)]}


def search_marketplaces(state: BuyerState) -> dict:
    req = BuyerRequest(**state["request"])
    searches, candidates, lines = [], [], []
    for source in ("ACV", "Copart"):
        res = search_marketplace(source, req)
        searches.append({k: res[k] for k in ("source", "live_count", "skipped")} |
                        {"found": len(res["candidates"])})
        candidates += res["candidates"]
        what = " ".join(p for p in [req.make, req.model] if p) or "car"
        lines.append(_log("✓", f"Searched {source}: {res['live_count']} live listings → "
                               f"{len(res['candidates'])} {what} candidates",
                          f"Skipped: {_skips(res['skipped'])}"))
    return {"searches": searches, "candidates": candidates, "log": lines}


def check_life_passports(state: BuyerState) -> dict:
    flagged, clean = [], []
    for car in state["candidates"]:
        passport = check_passport(car)
        (flagged if passport["status"] == "flagged" else clean).append({**car, "passport": passport})
    n = len(state["candidates"])
    return {"flagged": flagged, "clean": clean,
            "log": [_log("✓", f"Checked the Life Passport of {n} car{'s' * (n != 1)}",
                         "Joined ACV inspections, Copart sales and title records by VIN. "
                         f"{len(flagged)} flagged.")]}


def explain_flags(state: BuyerState) -> dict:
    explained, lines = [], []
    for car in state["flagged"]:
        note, source = explain_risk(car, car["passport"], state.get("demo_safe", False))
        explained.append({**car, "risk": note.model_dump(), "risk_source": source})
        lines.append(_log("⚠", f"Excluded {car['year']} {car['make']} {car['model']} ({car['id']}): "
                               f"{note.headline}", note.explanation, ai=source))
    return {"flagged": explained, "log": lines}


def rank_and_quote(state: BuyerState) -> dict:
    req = BuyerRequest(**state["request"])
    ranked = rank_matches(state["clean"], req)
    matches = ranked[: req.quantity]
    if not matches:
        return {"matches": [], "log": [_log("•", "No clean matches yet")]}
    costs = [m["transport"]["cost"] for m in matches]
    days = max(m["transport"]["days"] for m in matches)
    when = f"all arrive within {days} day{'s' * (days != 1)}"
    if req.deadline:
        when += f" (before {req.deadline})"
    cost_text = f"${min(costs):,}" if min(costs) == max(costs) else f"${min(costs):,}–${max(costs):,}"
    return {"matches": matches,
            "log": [_log("✓", f"Found {len(matches)} of {req.quantity} · transport to "
                              f"{req.destination_city} {cost_text} each",
                         f"Ranked by price vs. market value, condition and delivery cost; {when}.")]}


def widen_search(state: BuyerState) -> dict:
    req = BuyerRequest(**state["request"])
    changes = []
    if req.max_price:
        req.max_price = int(req.max_price * 1.1 // 100 * 100)
        changes.append(f"budget ≤ ${req.max_price:,}")
    if req.min_year:
        req.min_year -= 1
        changes.append(f"{req.min_year}+")
    if req.max_mileage:
        req.max_mileage = int(req.max_mileage * 1.15)
        changes.append(f"≤ {req.max_mileage:,} mi")
    return {"request": req.model_dump(), "widened": True,
            "log": [_log("↻", "No exact matches, so I widened the search once",
                         ", ".join(changes) or "same filters")]}


def await_approval(state: BuyerState) -> dict:
    req = BuyerRequest(**state["request"])
    matches = state["matches"]
    total = sum(m["recommended_bid"] for m in matches)
    question = (f"Found {len(matches)} good {req.model or 'car'}{'s' * (len(matches) != 1)}. "
                f"Bid up to ${total:,} in total and book transport to {req.destination_city}?")
    decision = interrupt({"question": question, "matches": [m["id"] for m in matches], "total": total})
    if not isinstance(decision, dict):
        decision = {"approved": bool(decision)}
    return {"decision": decision}


def execute(state: BuyerState) -> dict:
    req = BuyerRequest(**state["request"])
    buyer = state.get("buyer_name", "Your dealership")
    decision = state.get("decision", {"approved": False})
    chosen_ids = set(decision.get("car_ids") or [m["id"] for m in state.get("matches", [])])
    chosen = [m for m in state.get("matches", []) if m["id"] in chosen_ids] if decision.get("approved") else []
    lines = []
    if chosen:
        store.add_bids([{"buyer": buyer, "car_id": m["id"], "max_bid": m["recommended_bid"],
                         "transport": m["transport"]} for m in chosen])
        lines.append(_log("✓", f"Placed {len(chosen)} proxy bid{'s' * (len(chosen) != 1)}",
                          " · ".join(f"{m['id']} up to ${m['recommended_bid']:,}" for m in chosen)))
        lines.append(_log("✓", f"Booked transport to {req.destination_city}",
                          f"${sum(m['transport']['cost'] for m in chosen):,} total"))
        lines.append(_log("✓", "Started title checks", "Sellers asked to upload titles now, so cars can leave on time."))
    elif not state.get("matches"):
        lines.append(_log("•", "Nothing matches right now", "No bids placed."))
    else:
        lines.append(_log("•", "No bids placed", "You declined, so nothing was spent."))

    remaining = req.quantity - len(chosen)
    wish = None
    if remaining > 0:
        wish = store.add_wish({"buyer": buyer, "buyer_city": req.destination_city, "channel": "ACV",
                               "make": req.make, "model": req.model, "min_year": req.min_year,
                               "max_year": req.max_year, "max_price": req.max_price,
                               "max_mileage": req.max_mileage, "title": req.title, "quantity": remaining})
        lines.append(_log("👀", f"Watching ACV + Copart for {remaining} more",
                          "You'll get a message the moment a matching car is listed, before its auction starts."))
    store.notify(buyer, f"{len(chosen)} bids placed" + (f"; watching for {remaining} more" if remaining > 0 else ""),
                 kind="buyer")
    return {"result": {"bids": [m["id"] for m in chosen], "remaining": remaining,
                       "wish_id": wish["id"] if wish else None},
            "log": lines}


# --- Routing -----------------------------------------------------------------

def after_passports(state: BuyerState) -> str:
    return "explain_flags" if state.get("flagged") else "rank_and_quote"


def after_rank(state: BuyerState) -> str:
    if state.get("matches"):
        return "await_approval"
    return "execute" if state.get("widened") else "widen_search"


def build_buyer_graph(checkpointer=None):
    g = StateGraph(BuyerState)
    g.add_node("understand_request", understand_request)
    g.add_node("search_marketplaces", search_marketplaces)
    g.add_node("check_life_passports", check_life_passports)
    g.add_node("explain_flags", explain_flags)
    g.add_node("rank_and_quote", rank_and_quote)
    g.add_node("widen_search", widen_search)
    g.add_node("await_approval", await_approval)
    g.add_node("execute", execute)

    g.add_edge(START, "understand_request")
    g.add_edge("understand_request", "search_marketplaces")
    g.add_edge("search_marketplaces", "check_life_passports")
    g.add_conditional_edges("check_life_passports", after_passports, ["explain_flags", "rank_and_quote"])
    g.add_edge("explain_flags", "rank_and_quote")
    g.add_conditional_edges("rank_and_quote", after_rank, ["await_approval", "widen_search", "execute"])
    g.add_edge("widen_search", "search_marketplaces")
    g.add_edge("await_approval", "execute")
    g.add_edge("execute", END)
    return g.compile(checkpointer=checkpointer or InMemorySaver())
