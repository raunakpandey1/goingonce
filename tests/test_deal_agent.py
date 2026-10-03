import uuid

import pytest
from langgraph.types import Command

from carcompass import store
from carcompass.agents.deal import build_deal_graph
from carcompass.negotiation import buyer_offer, seller_offer

CAMRY = {"year": 2020, "make": "Toyota", "model": "Camry", "trim": "LE", "mileage": 52000, "grade": 4.0,
         "city": "Buffalo"}


@pytest.fixture(autouse=True)
def temp_store(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "STATE_FILE", tmp_path / "state.json")
    monkeypatch.setattr(store, "RUNTIME_DIR", tmp_path)


def start(graph, seller_min, buyer_max):
    config = {"configurable": {"thread_id": uuid.uuid4().hex}}
    payload = {"car": CAMRY, "seller": "Seller", "buyer": "Buyer", "buyer_city": "Rochester", "ask": 15000,
               "seller_min": seller_min, "high_bid": 12000, "buyer_max": buyer_max, "lien": 5000,
               "demo_safe": True}
    pending = None
    for chunk in graph.stream(payload, config, stream_mode="updates"):
        if "__interrupt__" in chunk:
            pending = chunk["__interrupt__"][0].value
    return config, pending


def test_offers_never_cross_private_limits():
    for t in range(1, 6):
        assert seller_offer(15000, 12800, t) >= 12800
        assert buyer_offer(12000, 13400, t) <= 13400


def test_mentor_scenario_closes_between_bid_and_ask():
    graph = build_deal_graph()
    config, pending = start(graph, seller_min=12800, buyer_max=13400)
    assert pending and 12800 <= pending["price"] <= 13400
    for _ in graph.stream(Command(resume={"accepted": True}), config, stream_mode="updates"):
        pass
    closing = graph.get_state(config).values["closing"]
    assert closing["seller_payout"] == closing["price"] - 350 - 5000
    assert closing["acv"]["total"] > 0
    assert {n["to"] for n in store.notifications()} == {"Seller", "Buyer"}


def test_no_overlap_ends_without_a_deal():
    graph = build_deal_graph()
    config, pending = start(graph, seller_min=13900, buyer_max=13000)
    values = graph.get_state(config).values
    assert pending is None and values["deal"] is None and values["round"] == 4
    assert store.notifications() == []
