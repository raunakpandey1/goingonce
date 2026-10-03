"""Run the buyer's agent in the terminal.

    .venv/bin/python scripts/buyer_cli.py "Need 5 Camrys, 2018+, under $12K ..." [--demo-safe] [--yes]
"""

import argparse
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langgraph.types import Command  # noqa: E402

from carcompass.agents.buyer import build_buyer_graph  # noqa: E402

PITCH = "Need 5 Camrys, 2018+, under $12K, clean title, delivered to Rochester by Friday."


def show(chunk: dict) -> dict | None:
    for node, update in chunk.items():
        if node == "__interrupt__":
            return update[0].value
        for line in (update or {}).get("log", []):
            tag = f" [{line['ai']} AI]" if line.get("ai") else ""
            print(f"{line['icon']} {line['text']}{tag}")
            if line.get("detail"):
                print(f"    {line['detail']}")
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("request", nargs="?", default=PITCH)
    ap.add_argument("--demo-safe", action="store_true")
    ap.add_argument("--yes", action="store_true", help="approve without asking")
    args = ap.parse_args()

    graph = build_buyer_graph()
    config = {"configurable": {"thread_id": uuid.uuid4().hex}}
    inputs = {"request_text": args.request, "buyer_name": "Mike's Motors (Rochester)",
              "demo_safe": args.demo_safe}
    pending = None
    for chunk in graph.stream(inputs, config, stream_mode="updates"):
        pending = show(chunk) or pending
    if pending:
        print(f"\n🤖 {pending['question']}")
        ok = args.yes or input("Approve? [y/N] ").strip().lower() == "y"
        for chunk in graph.stream(Command(resume={"approved": ok}), config, stream_mode="updates"):
            show(chunk)


if __name__ == "__main__":
    main()
