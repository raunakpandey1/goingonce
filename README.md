# CarCompass

**Every car finds its best buyer, across ACV and Copart.**

Two AI agents built with **LangGraph** and **Claude Opus 5.5**:

- **Buyer's agent:** a dealer types what they need in plain words (any language). The agent searches ACV and Copart, checks each car's **Life Passport** (ACV + Copart records joined by VIN), catches hidden salvage history, ranks the cars, quotes transport, and **waits for the dealer's approval** before bidding. Anything it can't fill now becomes a saved request it keeps watching.
- **Seller's agent:** a dealer uploads photos. Claude writes the condition report. The agent compares every way to sell (lot, ACV, Copart, export) in dollars, finds **buyers already waiting** (including the buyer agent's saved requests), lists in one tap, and messages those buyers before the auction. If the car doesn't sell, it's re-offered to Copart's global buyers.

---

## Run it

```bash
cd ~/Desktop/hackathon2026/goingonce
.venv/bin/streamlit run app.py
```

Open http://localhost:8501.

First-time setup on another machine:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env      # then paste the API key into .env
```

Never commit `.env` (it's git-ignored).

### Sidebar controls
| Control | What it does |
|---|---|
| **Demo-safe mode** | Replays saved AI results, so the demo works with no Wi-Fi. Turn it **on** if the network looks shaky. |
| **Agent step delay** | Pause between activity-log lines (0.6 s looks good on a projector). |
| **Reset demo** | Clears bids, listings, messages and saved requests. **Press it before you present.** |

---

## 2-minute demo script

1. **Reset demo** in the sidebar.
2. **🛒 Buyer's Agent** → leave the pre-filled request → **Send to agent**.
   - Narrate the log: *"It understood the request… searched ACV and Copart… checked every car's Life Passport…"*
   - Point at the **red card**: *"This Camry looks like the best deal, but it was flooded and sold as salvage on Copart in 2023, then re-titled clean. Only the combined company can see that."*
   - Click **Approve**: *"Nothing is spent without the dealer's tap. It found 3 of 5, so it keeps watching for 2 more."*
3. **📸 Sell in one photo** → upload 2–3 photos of a teammate's car (JPG/PNG) → **Analyze & find buyers**.
   - *"Claude wrote this condition report from the photos."*
   - *"Here's what she'd actually pocket from each option, and ACV wins."*
   - *"3 buyers are already waiting, including the dealer from the first tab."*
   - **List now** → **No sale** → *"No car left unsold: it goes straight to Copart's global buyers."*
4. **🔔 Agent inbox**: show the messages the agents sent.
5. **🧠 How it works**: the two LangGraph diagrams (also in `docs/graphs/*.png` for slides).

**Wildcard:** let a judge type their own request, for example *"Need 3 Accords under 15K delivered to Buffalo"*. Requests in any language work in live mode.

---

## What's real and what's simulated

| Real | Simulated |
|---|---|
| Claude reads requests (any language), car photos, and explains flagged histories | 310 synthetic ACV + Copart listings and their histories |
| LangGraph agents with human-in-the-loop approval, a retry loop, and shared memory | Bids, truck bookings, title checks and messages (saved locally, nothing is sent) |
| Life Passport checks: hidden salvage and odometer rollback | Prices and fees use simple formulas |

Say this plainly if a judge asks: *"Demo data. In production the same tools would call ACV and Copart's inventory, inspection and title systems."*

---

## How it's built

```
app.py                      Streamlit UI (4 tabs)
carcompass/
  agents/buyer.py           LangGraph buyer's agent (interrupt before bidding)
  agents/seller.py          LangGraph seller's agent (interrupts: list now, auction result)
  llm.py                    Claude calls (structured output + vision), each with a saved fallback
  tools.py                  Search, Life Passport, transport, ranking, best-path math, matching
  store.py                  JSON memory: saved requests, listings, bids, messages
  data/catalog.py           Synthetic marketplace + hand-placed demo cars
scripts/buyer_cli.py        Run the buyer agent in the terminal
scripts/export_graphs.py    Re-render docs/graphs/*.png
tests/                      15 tests, including a full click-through of the app
```

- **AI is used in 3 places only:** understanding the request, reading photos, explaining flagged cars. Search, history checks, prices and matching are plain code, so the results are repeatable.
- **Model:** `claude-opus-5-5` at low effort with the server-side refusal fallback enabled. Change it with `CARCOMPASS_MODEL` in `.env`.
- **If a Claude call fails** (no key, no network, or an error), that step falls back to its saved result and the log shows a *saved AI* badge instead of *live AI*.

```bash
.venv/bin/python -m pytest -q                       # all tests
.venv/bin/python scripts/buyer_cli.py --yes         # buyer agent in the terminal (live AI)
.venv/bin/python scripts/buyer_cli.py --demo-safe   # same, saved AI results
```

## Troubleshooting
- **iPhone photos won't upload:** HEIC isn't supported. Send them as JPG (Settings → Camera → Formats → Most Compatible), or screenshot them.
- **AI seems slow or failing:** switch on **Demo-safe mode**.
- **Port already in use:** `.venv/bin/streamlit run app.py --server.port 8502`
