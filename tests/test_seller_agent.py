import uuid

import pytest
from langgraph.types import Command

from carcompass import store
from carcompass.agents.seller import build_seller_graph

SARAH_CAMRY = {"year": 2019, "make": "Toyota", "model": "Camry", "trim": "SE", "mileage": 61000,
               "city": "Buffalo", "title_status": "clean", "seller_name": "Sarah's Truck Center",
               "lot_fit": False}


@pytest.fixture(autouse=True)
def temp_store(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "STATE_FILE", tmp_path / "state.json")
    monkeypatch.setattr(store, "RUNTIME_DIR", tmp_path)


def stream(graph, payload, config):
    pending = None
    for chunk in graph.stream(payload, config, stream_mode="updates"):
        if "__interrupt__" in chunk:
            pending = chunk["__interrupt__"][0].value
    return pending


def start(graph):
    config = {"configurable": {"thread_id": uuid.uuid4().hex}}
    pending = stream(graph, {"vehicle": SARAH_CAMRY, "photos": [], "demo_safe": True}, config)
    return config, pending


def test_listing_flow_finds_waiting_buyers_and_notifies_them():
    graph = build_seller_graph()
    config, pending = start(graph)
    values = graph.get_state(config).values
    assert values["paths"]["best"] == "ACV dealer auction"
    assert pending["waiting"] == 2  # the two seeded wishes
    assert store.listings() == []  # nothing published before approval

    pending = stream(graph, Command(resume={"list": True}), config)
    assert pending["listing_id"].startswith("ACV-")
    assert len(store.listings()) == 1
    assert any(n["kind"] == "match" and n["to"] == "Niagara Auto Group" for n in store.notifications())


def test_no_sale_reoffers_to_global_buyers():
    graph = build_seller_graph()
    config, _ = start(graph)
    stream(graph, Command(resume={"list": True}), config)
    stream(graph, Command(resume={"sold": False}), config)
    notes = store.notifications()
    assert any(n["to"] == "Gulf Coast Exports (Dubai)" and "Re-offered" in n["text"] for n in notes)
    assert graph.get_state(config).next == ()


def test_declining_publishes_nothing():
    graph = build_seller_graph()
    config, _ = start(graph)
    stream(graph, Command(resume={"list": False}), config)
    assert store.listings() == []
    assert graph.get_state(config).next == ()
