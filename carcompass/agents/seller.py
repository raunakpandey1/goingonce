"""Seller's agent: photos in, the best way to sell, buyers lined up before the auction.

LangGraph flow:

    inspect_photos -> price_paths -> pre_match
        -> await_listing          [interrupt: seller taps "List now"]
        -> publish_listing        (waiting buyers get notified before the auction)
        -> await_auction_result   [interrupt: sold / no sale]
        -> (reoffer_unsold if no sale: Copart's global buyers get it next)

Claude reads the photos. Pricing, matching and notifications are plain code.
"""

from __future__ import annotations

import base64
import operator
from typing import Annotated, Optional, TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from .. import store
from ..llm import inspect_photos as llm_inspect_photos
from ..tools import best_paths, wish_matches


class SellerState(TypedDict, total=False):
    vehicle: dict
    photos: list[dict]  # [{"b64": str, "media_type": str}]
    demo_safe: bool
    condition: dict
    condition_source: str
    paths: dict
    preview: dict
    waiting_buyers: list[dict]
    decision: dict
    listing: dict
    auction: dict
    log: Annotated[list[dict], operator.add]


def _log(icon: str, text: str, detail: Optional[str] = None, ai: Optional[str] = None) -> dict:
    return {"icon": icon, "text": text, "detail": detail, "ai": ai}


def _name(v: dict) -> str:
    return f"{v['year']} {v['make']} {v['model']}" + (f" {v['trim']}" if v.get("trim") else "")


# --- Nodes -------------------------------------------------------------------

def inspect_photos(state: SellerState) -> dict:
    v = state["vehicle"]
    images = [(base64.b64decode(p["b64"]), p["media_type"]) for p in state.get("photos", [])]
    hint = f"{_name(v)}, {v['mileage']:,} miles"
    report, source = llm_inspect_photos(images, hint, state.get("demo_safe", False))
    n = len(images)
    what = f"{n} photo{'s' * (n != 1)}" if n else "the sample photos"
    return {"condition": report.model_dump(), "condition_source": source,
            "log": [_log("✓", f"Wrote the condition report from {what}: grade {report.condition_grade:.1f}/5",
                         report.summary, ai=source)]}


def price_paths(state: SellerState) -> dict:
    v = state["vehicle"]
    result = best_paths(v["make"], v["model"], v["year"], v["mileage"],
                        state["condition"]["condition_grade"], lot_fit=v.get("lot_fit", False))
    best = next(r for r in result["rows"] if r["best"])
    runner_up = sorted(result["rows"], key=lambda r: r["net"], reverse=True)[1]
    return {"paths": result,
            "log": [_log("✓", f"Compared 4 ways to sell → best: {best['channel']} "
                              f"(${best['net']:,} in your pocket)",
                         f"${best['net'] - runner_up['net']:,} more than {runner_up['channel'].lower()}, "
                         "after fees, transport and days waiting.")]}


def pre_match(state: SellerState) -> dict:
    v = state["vehicle"]
    acv = next(r for r in state["paths"]["rows"] if r["channel"] == "ACV dealer auction")
    preview = {"year": v["year"], "make": v["make"], "model": v["model"], "trim": v.get("trim", ""),
               "mileage": v["mileage"], "price": int(acv["gross"] // 50 * 50),
               "title_status": v.get("title_status", "clean"), "city": v.get("city", "Buffalo"),
               "condition_grade": state["condition"]["condition_grade"]}
    waiting = []
    for wish in store.wishes():
        ok, _ = wish_matches(wish, preview)
        if ok:
            waiting.append({"wish_id": wish["id"], "buyer": wish["buyer"], "city": wish.get("buyer_city", ""),
                            "channel": wish.get("channel", "ACV"), "max_price": wish.get("max_price"),
                            "quantity": wish.get("quantity", 1)})
    n = len(waiting)
    if n:
        line = _log("🔔", f"{n} buyer{'s are' if n != 1 else ' is'} already waiting for a car like this",
                    " · ".join(f"{w['buyer']} (up to ${w['max_price']:,})" if w.get("max_price") else w["buyer"]
                               for w in waiting))
    else:
        line = _log("•", "No saved buyer requests match yet", "The auction will run as normal.")
    return {"preview": preview, "waiting_buyers": waiting, "log": [line]}


def await_listing(state: SellerState) -> dict:
    best = state["paths"]["best"]
    decision = interrupt({"question": f"List it now via {best}?", "best": best,
                          "waiting": len(state.get("waiting_buyers", []))})
    if not isinstance(decision, dict):
        decision = {"list": bool(decision)}
    return {"decision": decision}


def publish_listing(state: SellerState) -> dict:
    if not state.get("decision", {}).get("list"):
        return {"log": [_log("•", "Not listed", "Saved as a draft. Nothing was published.")]}
    v, preview = state["vehicle"], state["preview"]
    listing = store.add_listing({**preview, "seller": v.get("seller_name", "Seller"),
                                 "channel": state["paths"]["best"], "condition": state["condition"],
                                 "auction_starts": "Today 2:00 PM", "status": "live"})
    lines = [_log("✓", f"Listed {listing['id']} on ACV", f"Auction starts {listing['auction_starts']} · "
                                                         f"expected ${preview['price']:,}")]
    acv_buyers = [w for w in state.get("waiting_buyers", []) if w["channel"] == "ACV"]
    for w in acv_buyers:
        store.notify(w["buyer"], f"A {_name(v)} ({v['mileage']:,} mi, grade "
                                 f"{preview['condition_grade']:.1f}) matching your request goes live at 2:00 PM: "
                                 f"{listing['id']}", kind="match")
    if acv_buyers:
        lines.append(_log("📲", f"Messaged {len(acv_buyers)} waiting buyer{'s' * (len(acv_buyers) != 1)} "
                                "before the auction starts",
                          ", ".join(w["buyer"] for w in acv_buyers)))
    return {"listing": listing, "log": lines}


def await_auction_result(state: SellerState) -> dict:
    if not state.get("listing"):
        return {"auction": {"sold": None}}
    outcome = interrupt({"question": "Auction result?", "listing_id": state["listing"]["id"]})
    if not isinstance(outcome, dict):
        outcome = {"sold": bool(outcome)}
    return {"auction": outcome}


def record_sale(state: SellerState) -> dict:
    price = state["auction"].get("price") or state["preview"]["price"]
    store.notify(state["vehicle"].get("seller_name", "Seller"), f"{state['listing']['id']} sold for ${price:,}",
                 kind="seller")
    return {"log": [_log("✓", f"Sold for ${price:,}", "Transport and title paperwork start automatically.")]}


def reoffer_unsold(state: SellerState) -> dict:
    v, listing = state["vehicle"], state["listing"]
    global_buyers = [w for w in state.get("waiting_buyers", []) if w["channel"] != "ACV"]
    for w in global_buyers:
        store.notify(w["buyer"], f"Re-offered: {_name(v)} ({listing['id']}) did not sell on ACV and is "
                                 f"available to Copart global buyers.", kind="match")
    who = ", ".join(w["buyer"] for w in global_buyers) or "Copart's buyers in 185+ countries"
    return {"log": [_log("↻", "No sale on ACV, so it was re-offered to Copart's global buyers", who),
                    _log("✓", "No car left unsold", "Next stop: Copart auction plus export buyers.")]}


# --- Routing -----------------------------------------------------------------

def after_auction(state: SellerState) -> str:
    sold = state.get("auction", {}).get("sold")
    if sold is None:
        return END
    return "record_sale" if sold else "reoffer_unsold"


def build_seller_graph(checkpointer=None):
    g = StateGraph(SellerState)
    for name, fn in [("inspect_photos", inspect_photos), ("price_paths", price_paths),
                     ("pre_match", pre_match), ("await_listing", await_listing),
                     ("publish_listing", publish_listing), ("await_auction_result", await_auction_result),
                     ("record_sale", record_sale), ("reoffer_unsold", reoffer_unsold)]:
        g.add_node(name, fn)
    g.add_edge(START, "inspect_photos")
    g.add_edge("inspect_photos", "price_paths")
    g.add_edge("price_paths", "pre_match")
    g.add_edge("pre_match", "await_listing")
    g.add_edge("await_listing", "publish_listing")
    g.add_edge("publish_listing", "await_auction_result")
    g.add_conditional_edges("await_auction_result", after_auction, ["record_sale", "reoffer_unsold", END])
    g.add_edge("record_sale", END)
    g.add_edge("reoffer_unsold", END)
    return g.compile(checkpointer=checkpointer or InMemorySaver())
