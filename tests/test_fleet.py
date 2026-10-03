import uuid

import pytest
from langgraph.types import Command

from carcompass import store
from carcompass.agents.fleet import build_fleet_graph
from carcompass.fleet import (
    FLEET_MODELS,
    MARKET_DEMAND,
    TRUCK_CAPACITY,
    make_fleet,
    plan_distribution,
    plan_dump_local,
    plan_one_by_one,
)

LOTS = ["Buffalo", "Rochester", "Albany"]


@pytest.fixture(autouse=True)
def temp_store(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "STATE_FILE", tmp_path / "state.json")
    monkeypatch.setattr(store, "RUNTIME_DIR", tmp_path)


def test_plan_beats_both_naive_plans():
    cars = make_fleet(120, LOTS, FLEET_MODELS[:3])
    plan, dump, single = plan_distribution(cars, 2), plan_dump_local(cars), plan_one_by_one(cars, 2)
    assert plan["cars"] == dump["cars"] == single["cars"] == 120
    assert plan["net"] > dump["net"] and plan["net"] > single["net"]
    assert plan["transport_per_car"] < single["transport_per_car"]


def test_every_car_assigned_once_and_trucks_hold_nine():
    cars = make_fleet(75, LOTS, FLEET_MODELS)
    plan = plan_distribution(cars, 2)
    ids = [cid for load in plan["loads"] for cid in load["car_ids"]]
    assert sorted(ids) == sorted(c["id"] for c in cars)
    assert all(load["cars"] <= TRUCK_CAPACITY for load in plan["loads"])
    assert all(load["to"] in MARKET_DEMAND for load in plan["loads"])


def test_fleet_agent_waits_for_approval_then_schedules():
    graph = build_fleet_graph()
    config = {"configurable": {"thread_id": uuid.uuid4().hex}}
    payload = {"fleet_name": "Rental fleet", "count": 60, "lots": LOTS,
               "models": [list(m) for m in FLEET_MODELS[:3]], "weeks": 2, "demo_safe": True}
    pending = None
    for chunk in graph.stream(payload, config, stream_mode="updates"):
        if "__interrupt__" in chunk:
            pending = chunk["__interrupt__"][0].value
    assert pending and store.notifications() == []
    for _ in graph.stream(Command(resume={"approved": True}), config, stream_mode="updates"):
        pass
    values = graph.get_state(config).values
    assert sum(w["cars"] for w in values["schedule"]) == 60
    assert store.notifications()[0]["to"] == "Rental fleet"
