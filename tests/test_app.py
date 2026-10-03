"""Click through the whole demo in demo-safe mode, exactly as on stage."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from carcompass import store


@pytest.fixture(autouse=True)
def temp_store(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "STATE_FILE", tmp_path / "state.json")
    monkeypatch.setattr(store, "RUNTIME_DIR", tmp_path)


def click(at, label):
    next(b for b in at.button if label in b.label).click().run()
    assert not at.exception, at.exception


def test_full_demo_click_through():
    at = AppTest.from_file(str(Path(__file__).resolve().parent.parent / "app.py"), default_timeout=120)
    at.session_state["pace"] = 0.0
    at.session_state["demo_safe"] = True
    at.run()
    assert not at.exception

    click(at, "Send to agent")
    page = " ".join(m.value for m in at.markdown)
    assert "HIDDEN HISTORY CAUGHT" in page and "Bid up to $33,000" in page

    click(at, "✅ Approve")
    assert any("Bids placed on 3 cars" in s.value for s in at.success)

    click(at, "Analyze")
    waiting = [c.value for c in at.caption if c.value.startswith("•")]
    assert any("Mike's Motors" in w for w in waiting)  # the buyer tab's unfilled request is waiting

    click(at, "🚀 List now")
    click(at, "No sale")
    assert any("No car left unsold" in s.value for s in at.success)

    click(at, "Start AI negotiation")
    assert any("Both accept $13,150" in b.label for b in at.button)
    click(at, "Both accept")
    assert any("Deal closed" in s.value for s in at.success)
