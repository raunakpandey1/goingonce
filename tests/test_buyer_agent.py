import uuid

import pytest
from langgraph.types import Command

from carcompass import store
from carcompass.agents.buyer import build_buyer_graph

PITCH = "Need 5 Camrys, 2018+, under $12K, clean title, delivered to Rochester by Friday."


@pytest.fixture(autouse=True)
def temp_store(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "STATE_FILE", tmp_path / "state.json")
    monkeypatch.setattr(store, "RUNTIME_DIR", tmp_path)


def run_until_interrupt(graph, text):
    config = {"configurable": {"thread_id": uuid.uuid4().hex}}
    interrupt_value = None
    for chunk in graph.stream({"request_text": text, "buyer_name": "Test Buyer", "demo_safe": True},
                              config, stream_mode="updates"):
        if "__interrupt__" in chunk:
            interrupt_value = chunk["__interrupt__"][0].value
    return config, interrupt_value


def test_pitch_flow_pauses_for_approval_then_bids():
    graph = build_buyer_graph()
    config, pending = run_until_interrupt(graph, PITCH)
    assert pending and set(pending["matches"]) == {"ACV-20418", "ACV-20561", "CPRT-51207"}
    state = graph.get_state(config)
    assert state.next == ("await_approval",)
    assert [c["id"] for c in state.values["flagged"]] == ["ACV-20733"]
    assert store.load()["bids"] == []  # nothing spent before approval

    for _ in graph.stream(Command(resume={"approved": True}), config, stream_mode="updates"):
        pass
    result = graph.get_state(config).values["result"]
    assert len(result["bids"]) == 3 and result["remaining"] == 2
    assert len(store.load()["bids"]) == 3
    assert any(w["id"] == result["wish_id"] and w["quantity"] == 2 for w in store.wishes())


def test_decline_places_no_bids_but_keeps_watching():
    graph = build_buyer_graph()
    config, _ = run_until_interrupt(graph, PITCH)
    for _ in graph.stream(Command(resume={"approved": False}), config, stream_mode="updates"):
        pass
    result = graph.get_state(config).values["result"]
    assert result["bids"] == [] and result["remaining"] == 5
    assert store.load()["bids"] == []


def test_impossible_request_widens_once_then_watches():
    graph = build_buyer_graph()
    config, pending = run_until_interrupt(graph, "need 2 Tesla Model 3 2025 or newer under 5k to Buffalo")
    assert pending is None
    values = graph.get_state(config).values
    assert values["widened"] is True and values["result"]["remaining"] == 2
