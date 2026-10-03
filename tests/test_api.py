import json

import pytest
from fastapi.testclient import TestClient

from carcompass import store


@pytest.fixture(autouse=True)
def temp_store(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "STATE_FILE", tmp_path / "state.json")
    monkeypatch.setattr(store, "RUNTIME_DIR", tmp_path)


@pytest.fixture
def client():
    from api import app
    return TestClient(app)


def events(response):
    return [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]


def test_health(client):
    assert client.get("/api/health").json()["ok"] is True


def test_buyer_streams_then_resumes(client):
    payload = {"request_text": "Need 5 Camrys, 2018+, under $12K, clean title, delivered to Rochester by Friday.",
               "buyer_name": "Test", "demo_safe": True}
    evs = events(client.post("/api/buyer/start", json={"payload": payload, "pace": 0}))
    assert evs[0]["type"] == "start" and any(e["type"] == "log" for e in evs)
    assert any(e["type"] == "interrupt" for e in evs)
    done = evs[-1]
    assert done["type"] == "done" and done["pending"] is True
    assert {c["id"] for c in done["values"]["matches"]} == {"ACV-20418", "ACV-20561", "CPRT-51207"}

    evs = events(client.post("/api/buyer/resume", json={"thread_id": evs[0]["thread_id"], "resume": {"approved": True}, "pace": 0}))
    assert evs[-1]["values"]["result"]["remaining"] == 2


def test_unknown_agent_is_404(client):
    assert client.post("/api/nope/start", json={"payload": {}}).status_code == 404
