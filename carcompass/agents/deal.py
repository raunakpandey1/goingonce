"""Deal agent: closes the gap between a seller's ask and the top bid, then closes the deal.

LangGraph flow:

    assess_gap -> negotiate_round (loops, up to 4 rounds)
        -> find_bridge   (a backhaul truck closes a small last gap)
        -> propose_deal  [interrupt: both sides accept]
        -> close_deal    (escrow payment, transit insurance, loan payoff, e-title,
                          truck, seller payout, ACV revenue)
        or -> no_deal    (best alternative: waiting buyers / Copart global)

Each side's private limit stays inside its own agent. Claude writes the
mediator's reality check; the numbers come from plain code.
"""

from __future__ import annotations

import operator
from typing import Annotated, Optional, TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from .. import store
from ..data.catalog import CITIES
from ..llm import mediation_brief
from ..negotiation import (
    MAX_ROUNDS,
    buyer_offer,
    closing_plan,
    comparable_sales,
    fair_value,
    seller_offer,
    waiting_cost_per_week,
)
from ..tools import transport_quote


class DealState(TypedDict, total=False):
    car: dict          # year, make, model, trim, mileage, grade, city
    seller: str
    buyer: str
    buyer_city: str
    ask: int
    seller_min: int    # private to the seller's agent
    high_bid: int
    buyer_max: int     # private to the buyer's agent
    lien: int
    demo_safe: bool
    market_value: int
    comps: list[dict]
    transport: dict
    round: int
    seller_now: int
    buyer_now: int
    rounds: list[dict]
    messages: Annotated[list[dict], operator.add]
    bridge: Optional[dict]
    deal: Optional[dict]
    decision: dict
    closing: dict
    log: Annotated[list[dict], operator.add]


def _log(icon: str, text: str, detail: Optional[str] = None, ai: Optional[str] = None) -> dict:
    return {"icon": icon, "text": text, "detail": detail, "ai": ai}


def _msg(who: str, text: str) -> dict:
    return {"who": who, "text": text}


def assess_gap(state: DealState) -> dict:
    c = state["car"]
    fv = fair_value(c["make"], c["model"], c["year"], c["mileage"], c["grade"])
    comps = comparable_sales(c["make"], c["model"], c["year"], c["mileage"], c["grade"])
    weekly = waiting_cost_per_week(state["ask"])
    _, lat, lon = CITIES.get(c.get("city", "Buffalo"), CITIES["Buffalo"])
    quote = transport_quote({"lat": lat, "lon": lon}, state.get("buyer_city", "Rochester"))
    brief, source = mediation_brief({"car": f"{c['year']} {c['make']} {c['model']}", "ask": state["ask"],
                                     "top_bid": state["high_bid"], "market_value": fv,
                                     "comparable_sales": comps, "waiting_cost_per_week": weekly},
                                    state.get("demo_safe", False))
    gap = state["ask"] - state["high_bid"]
    return {
        "market_value": fv, "comps": comps, "transport": quote, "round": 0,
        "seller_now": state["ask"], "buyer_now": state["high_bid"], "bridge": None, "deal": None,
        "rounds": [{"round": 0, "seller": state["ask"], "buyer": state["high_bid"]}],
        "messages": [_msg("mediator", f"To seller: {brief['to_seller']}"),
                     _msg("mediator", f"To buyer: {brief['to_buyer']}")],
        "log": [_log("✓", f"Gap is ${gap:,}: seller asks ${state['ask']:,}, top bid is ${state['high_bid']:,}",
                     f"Market value ${fv:,} from 3 comparable sales "
                     f"(${min(x['price'] for x in comps):,}–${max(x['price'] for x in comps):,})."),
                _log("✓", "Sent both sides a market reality check", brief["to_seller"], ai=source)],
    }


def negotiate_round(state: DealState) -> dict:
    t = state["round"] + 1
    s = seller_offer(state["ask"], state["seller_min"], t)
    b = buyer_offer(state["high_bid"], state["buyer_max"], t)
    gap = s - b
    msgs = [_msg("seller", f"Seller's agent: I can do ${s:,}."),
            _msg("buyer", f"Buyer's agent: We can go to ${b:,}.")]
    status = f"gap ${gap:,}" if gap > 0 else "offers crossed"
    return {"round": t, "seller_now": s, "buyer_now": b,
            "rounds": state["rounds"] + [{"round": t, "seller": s, "buyer": b}],
            "messages": msgs,
            "log": [_log("↔", f"Round {t}: seller ${s:,} ↓ · buyer ${b:,} ↑ · {status}")]}


def backhaul_saving(quote: dict) -> int:
    """A truck already returning on this route charges ~45% less."""
    return int(quote["cost"] * 0.45 // 5 * 5)


def find_bridge(state: DealState) -> dict:
    gap = state["seller_now"] - state["buyer_now"]
    saving = backhaul_saving(state["transport"])
    bridge = {"type": "backhaul", "saving": saving, "gap": gap}
    return {"bridge": bridge,
            "messages": [_msg("mediator", f"Mediator: only ${gap:,} apart. A truck is already returning on this "
                                          f"route, which saves the buyer ${saving:,} on delivery. The buyer can "
                                          f"meet the seller's ${state['seller_now']:,} and still come out ahead.")],
            "log": [_log("💡", f"Closed the last ${gap:,} with a backhaul truck",
                         f"A truck already heading that way saves the buyer ${saving:,} on transport.")]}


def propose_deal(state: DealState) -> dict:
    s, b = state["seller_now"], state["buyer_now"]
    price = s if state.get("bridge") else int(round((s + b) / 2 / 50) * 50)
    deal = {"price": price, "rounds": state["round"], "from_ask": state["ask"] - price,
            "from_bid": price - state["high_bid"], "bridge": state.get("bridge")}
    decision = interrupt({"question": f"Deal at ${price:,}. Do both sides accept?", "price": price})
    if not isinstance(decision, dict):
        decision = {"accepted": bool(decision)}
    return {"deal": deal, "decision": decision,
            "log": [_log("🤝", f"Proposed deal: ${price:,}",
                         f"${deal['from_ask']:,} below the ask, ${deal['from_bid']:,} above the first bid, "
                         f"in {state['round']} round{'s' * (state['round'] != 1)}.")]}


def close_deal(state: DealState) -> dict:
    deal = state["deal"]
    if not state.get("decision", {}).get("accepted"):
        return {"log": [_log("•", "Deal not accepted", "Car goes back to the waiting buyers and the next auction.")]}
    bridge = state.get("bridge") or {}
    transport = max(0, state["transport"]["cost"] - bridge.get("saving", 0))
    plan = closing_plan(deal["price"], transport, state.get("lien", 0))
    lines = [
        _log("💳", f"Buyer payment held in escrow: ${plan['buyer_pays']:,}",
             f"Price ${plan['price']:,} + buyer fee ${plan['acv']['buyer_fee']:,} + transport ${transport:,} + "
             f"insurance ${plan['insurance_premium']:,}. Released only when title and delivery are confirmed."),
        _log("🛡", f"Transit insurance bound: ${plan['price']:,} coverage",
             f"Premium ${plan['insurance_premium']:,}, covers the car from pickup to delivery."),
    ]
    if plan["lien_payoff"]:
        lines.append(_log("🏦", f"Loan payoff of ${plan['lien_payoff']:,} sent straight to the seller's lender",
                          "The lender releases the title electronically, so it isn't stuck for weeks."))
    lines += [
        _log("📄", "E-title transfer started", "Buyer gets the title before the car arrives."),
        _log("🚚", f"Truck booked to {state.get('buyer_city', 'Rochester')}: ${transport:,}",
             "Pickup tomorrow morning." + (" Uses the backhaul truck." if bridge else "")),
        _log("💵", f"Seller payout scheduled: ${plan['seller_payout']:,}",
             f"After the ${plan['acv']['seller_fee']:,} seller fee" +
             (f" and the ${plan['lien_payoff']:,} loan payoff." if plan["lien_payoff"] else ".")),
        _log("📈", f"ACV earns ${plan['acv']['total']:,}, only because the car sold",
             f"Buyer fee ${plan['acv']['buyer_fee']:,} + seller fee ${plan['acv']['seller_fee']:,} + "
             f"transport margin ${plan['acv']['transport_margin']:,}. Without a deal: $0."),
    ]
    store.notify(state.get("seller", "Seller"), f"Deal closed at ${deal['price']:,}. Payout "
                                                f"${plan['seller_payout']:,} after title release.", kind="seller")
    store.notify(state.get("buyer", "Buyer"), f"You bought the {state['car']['year']} {state['car']['model']} "
                                              f"for ${deal['price']:,}. Delivery booked, insurance bound.",
                 kind="buyer")
    return {"closing": plan, "log": lines}


def no_deal(state: DealState) -> dict:
    gap = state["seller_now"] - state["buyer_now"]
    return {"messages": [_msg("mediator", f"Mediator: still ${gap:,} apart after {state['round']} rounds. "
                                          "Neither side was pushed past its limit.")],
            "log": [_log("•", f"No deal: still ${gap:,} apart", "Nobody was pushed past their private limit."),
                    _log("↻", "Next best options lined up",
                         f"Re-offer to waiting buyers and Copart global buyers, with a suggested "
                         f"price of ${state['market_value']:,}.")]}


def after_round(state: DealState) -> str:
    gap = state["seller_now"] - state["buyer_now"]
    if gap <= 0:
        return "propose_deal"
    if gap <= backhaul_saving(state["transport"]) and not state.get("bridge"):
        return "find_bridge"
    return "negotiate_round" if state["round"] < MAX_ROUNDS else "no_deal"


def build_deal_graph(checkpointer=None):
    g = StateGraph(DealState)
    for name, fn in [("assess_gap", assess_gap), ("negotiate_round", negotiate_round),
                     ("find_bridge", find_bridge), ("propose_deal", propose_deal),
                     ("close_deal", close_deal), ("no_deal", no_deal)]:
        g.add_node(name, fn)
    g.add_edge(START, "assess_gap")
    g.add_edge("assess_gap", "negotiate_round")
    g.add_conditional_edges("negotiate_round", after_round,
                            ["propose_deal", "find_bridge", "negotiate_round", "no_deal"])
    g.add_edge("find_bridge", "propose_deal")
    g.add_edge("propose_deal", "close_deal")
    g.add_edge("close_deal", END)
    g.add_edge("no_deal", END)
    return g.compile(checkpointer=checkpointer or InMemorySaver())
