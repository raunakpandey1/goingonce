"""Fleet agent: a rental fleet's big batch of similar cars, distributed at the lowest logistics cost.

LangGraph flow:

    intake_fleet -> forecast_demand -> optimize_distribution -> explain_plan
        -> await_approval  [interrupt: fleet manager approves]
        -> schedule_auctions (stagger by week, book car haulers, alert waiting buyers)

Claude explains the plan in plain English; the optimization is plain code.
"""

from __future__ import annotations

import operator
from collections import Counter
from typing import Annotated, Optional, TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from .. import store
from ..fleet import (
    MARKET_DEMAND,
    PRICE_DROP_PER_EXTRA,
    make_fleet,
    plan_distribution,
    plan_dump_local,
    plan_one_by_one,
    routes,
    total_capacity,
)
from ..llm import fleet_summary
from ..negotiation import acv_fees


class FleetState(TypedDict, total=False):
    fleet_name: str
    count: int
    lots: list[str]
    models: list[list[str]]
    weeks: int
    demo_safe: bool
    cars: list[dict]
    plan: dict
    baselines: dict
    routes: list[dict]
    summary: str
    decision: dict
    schedule: list[dict]
    log: Annotated[list[dict], operator.add]


def _log(icon: str, text: str, detail: Optional[str] = None, ai: Optional[str] = None) -> dict:
    return {"icon": icon, "text": text, "detail": detail, "ai": ai}


def intake_fleet(state: FleetState) -> dict:
    cars = make_fleet(state["count"], state["lots"], [tuple(m) for m in state["models"]])
    by_lot = Counter(c["lot"] for c in cars)
    by_model = Counter(f"{c['make']} {c['model']}" for c in cars)
    return {"cars": cars,
            "log": [_log("✓", f"Received {len(cars)} cars from {state['fleet_name']}",
                         " · ".join(f"{n} at {lot}" for lot, n in by_lot.items()) + " | " +
                         ", ".join(f"{n} {m}" for m, n in by_model.items()) + " (2023, similar condition)")]}


def forecast_demand(state: FleetState) -> dict:
    weeks = state["weeks"]
    cap = total_capacity(weeks)
    return {"log": [_log("✓", f"{len(MARKET_DEMAND)} markets can absorb {cap} similar cars at full price "
                              f"over {weeks} week{'s' * (weeks != 1)}",
                         f"Above a market's demand, each extra similar car lowers the price about "
                         f"{PRICE_DROP_PER_EXTRA:.1%}.")]}


def optimize_distribution(state: FleetState) -> dict:
    cars, weeks = state["cars"], state["weeks"]
    plan = plan_distribution(cars, weeks)
    dump = plan_dump_local(cars)
    single = plan_one_by_one(cars, weeks)
    gain = plan["net"] - dump["net"]
    full_loads = sum(1 for l in plan["loads"] if l["truck"])
    return {"plan": plan, "baselines": {"dump": dump, "single": single}, "routes": routes(plan),
            "log": [_log("✓", f"Planned {full_loads} truckloads to {plan['markets']} markets over {weeks} "
                              f"week{'s' * (weeks != 1)}",
                         f"Transport ${plan['transport_per_car']}/car vs ${single['transport_per_car']}/car shipping "
                         f"one by one ({1 - plan['transport_per_car'] / max(single['transport_per_car'], 1):.0%} less)."),
                    _log("✓", f"+${gain:,} vs dumping everything at the local auctions",
                         f"Average sale ${plan['avg_price']:,} vs ${dump['avg_price']:,} when one market is flooded.")]}


def explain_plan(state: FleetState) -> dict:
    plan, b = state["plan"], state["baselines"]
    context = {"cars": plan["cars"], "markets": plan["markets"], "weeks": state["weeks"],
               "trucks": sum(1 for l in plan["loads"] if l["truck"]),
               "transport_per_car": plan["transport_per_car"],
               "one_by_one_transport_per_car": b["single"]["transport_per_car"],
               "gain_vs_dump": plan["net"] - b["dump"]["net"],
               "avg_price": plan["avg_price"], "dump_avg_price": b["dump"]["avg_price"],
               "top_routes": [{"from": r["from"], "to": r["to"], "cars": r["cars"]} for r in state["routes"][:6]]}
    text, source = fleet_summary(context, state.get("demo_safe", False))
    return {"summary": text, "log": [_log("✓", "Wrote the plan summary for the fleet manager", text, ai=source)]}


def await_approval(state: FleetState) -> dict:
    plan = state["plan"]
    decision = interrupt({"question": f"Approve sending {plan['cars']} cars to {plan['markets']} markets?",
                          "net": plan["net"]})
    if not isinstance(decision, dict):
        decision = {"approved": bool(decision)}
    return {"decision": decision}


def schedule_auctions(state: FleetState) -> dict:
    if not state.get("decision", {}).get("approved"):
        return {"log": [_log("•", "Plan not approved", "Nothing booked.")]}
    plan, weeks = state["plan"], state["weeks"]
    schedule, lines = [], []
    for w in range(1, weeks + 1):
        loads = [l for l in plan["loads"] if l["week"] == w]
        if not loads:
            continue
        markets = sorted({l["to"] for l in loads})
        cars = sum(l["cars"] for l in loads)
        trucks = sum(1 for l in loads if l["truck"])
        schedule.append({"week": w, "cars": cars, "trucks": trucks, "markets": markets})
        lines.append(_log("🗓", f"Week {w}: {cars} cars, {trucks} trucks → {', '.join(markets)}",
                          "Auctions staggered so no lane sees more similar cars than it can absorb."))
    trucks = sum(1 for l in plan["loads"] if l["truck"])
    fees = acv_fees(plan["avg_price"], plan["transport_per_car"])["total"] * plan["cars"]
    lines += [_log("🚚", f"Booked {trucks} car haulers", f"${plan['transport']:,} total transport."),
              _log("📲", f"Alerted waiting buyers in {plan['markets']} markets",
                   "Dealers with matching saved requests see the cars before their auctions."),
              _log("📈", f"ACV earns about ${fees:,} in fees as these {plan['cars']} cars sell",
                   "Fees are earned per sale, so protecting sell-through protects revenue.")]
    store.notify(state["fleet_name"], f"Plan approved: {plan['cars']} cars, {trucks} trucks, "
                                      f"{plan['markets']} markets over {weeks} weeks.", kind="seller")
    return {"schedule": schedule, "log": lines}


def build_fleet_graph(checkpointer=None):
    g = StateGraph(FleetState)
    for name, fn in [("intake_fleet", intake_fleet), ("forecast_demand", forecast_demand),
                     ("optimize_distribution", optimize_distribution), ("explain_plan", explain_plan),
                     ("await_approval", await_approval), ("schedule_auctions", schedule_auctions)]:
        g.add_node(name, fn)
    g.add_edge(START, "intake_fleet")
    g.add_edge("intake_fleet", "forecast_demand")
    g.add_edge("forecast_demand", "optimize_distribution")
    g.add_edge("optimize_distribution", "explain_plan")
    g.add_edge("explain_plan", "await_approval")
    g.add_edge("await_approval", "schedule_auctions")
    g.add_edge("schedule_auctions", END)
    return g.compile(checkpointer=checkpointer or InMemorySaver())
