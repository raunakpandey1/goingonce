"""HTTP API for the ACV-style React frontend.

Streams each agent's activity as Server-Sent Events, and serves the built frontend.

    .venv/bin/uvicorn api:app --port 8000
"""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from langgraph.types import Command

from carcompass import store
from carcompass.agents.buyer import build_buyer_graph
from carcompass.agents.deal import build_deal_graph
from carcompass.agents.fleet import build_fleet_graph
from carcompass.agents.seller import build_seller_graph
from carcompass.config import has_api_key

GRAPHS = {
    "buyer": build_buyer_graph(),
    "seller": build_seller_graph(),
    "deal": build_deal_graph(),
    "fleet": build_fleet_graph(),
}
HIDDEN = {"photos"}  # never echo uploaded images back
DEFAULT_PACE = 0.35  # seconds between activity lines, so the audience can follow

app = FastAPI(title="GoingOnce API")


def _sse(event: dict) -> str:
    return f"data: {json.dumps(event, default=str)}\n\n"


def _run(agent: str, payload, thread_id: str, pace: float):
    graph = GRAPHS[agent]
    config = {"configurable": {"thread_id": thread_id}}
    yield _sse({"type": "start", "thread_id": thread_id})
    try:
        for chunk in graph.stream(payload, config, stream_mode="updates"):
            for node, update in chunk.items():
                if node == "__interrupt__":
                    yield _sse({"type": "interrupt", "value": update[0].value})
                    continue
                for line in (update or {}).get("log", []):
                    yield _sse({"type": "log", "line": line})
                    time.sleep(pace)
        state = graph.get_state(config)
        values = {k: v for k, v in state.values.items() if k not in HIDDEN}
        yield _sse({"type": "done", "values": values, "pending": bool(state.next)})
    except Exception as e:  # surface agent errors to the UI instead of a broken stream
        yield _sse({"type": "error", "message": str(e)})


def _stream(gen) -> StreamingResponse:
    return StreamingResponse(gen, media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


def _agent(name: str) -> str:
    if name not in GRAPHS:
        raise HTTPException(404, f"unknown agent {name}")
    return name


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "live_ai": has_api_key()}


@app.post("/api/reset")
def reset() -> dict:
    store.reset()
    return {"ok": True}


@app.post("/api/{agent}/start")
async def start(agent: str, request: Request):
    body = await request.json()
    return _stream(_run(_agent(agent), body.get("payload", {}), uuid.uuid4().hex,
                        float(body.get("pace", DEFAULT_PACE))))


@app.post("/api/{agent}/resume")
async def resume(agent: str, request: Request):
    body = await request.json()
    if not body.get("thread_id"):
        raise HTTPException(400, "thread_id is required")
    return _stream(_run(_agent(agent), Command(resume=body.get("resume")), body["thread_id"],
                        float(body.get("pace", DEFAULT_PACE))))


DIST = Path(__file__).resolve().parent / "acv-frontend" / "dist"
if DIST.exists():
    app.mount("/", StaticFiles(directory=DIST, html=True), name="frontend")
