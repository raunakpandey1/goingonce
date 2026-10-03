"""Render both agent graphs to docs/graphs/ (Mermaid source + PNG for slides and the app).

    .venv/bin/python scripts/export_graphs.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from carcompass.agents.buyer import build_buyer_graph  # noqa: E402
from carcompass.agents.deal import build_deal_graph  # noqa: E402
from carcompass.agents.fleet import build_fleet_graph  # noqa: E402
from carcompass.agents.seller import build_seller_graph  # noqa: E402

OUT = ROOT / "docs" / "graphs"
OUT.mkdir(parents=True, exist_ok=True)

for name, graph in [("buyer_agent", build_buyer_graph()), ("seller_agent", build_seller_graph()),
                    ("deal_agent", build_deal_graph()), ("fleet_agent", build_fleet_graph())]:
    g = graph.get_graph()
    (OUT / f"{name}.mmd").write_text(g.draw_mermaid())
    try:
        (OUT / f"{name}.png").write_bytes(g.draw_mermaid_png())  # renders via mermaid.ink (needs internet)
        print(f"wrote {name}.png")
    except Exception as e:  # offline: the .mmd file still works in mermaid.live
        print(f"PNG skipped for {name}: {e}")
