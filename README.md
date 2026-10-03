# CarCompass

**Every car finds its best buyer, across ACV and Copart.**

Four AI agents built with **LangGraph** and **Claude Opus 5.5**:

- **Buyer's agent:** a dealer types what they need in plain words (any language). The agent searches ACV and Copart, checks each car's **Life Passport** (ACV + Copart records joined by VIN), catches hidden salvage history, ranks the cars, quotes transport, and **waits for the dealer's approval** before bidding. Anything it can't fill now becomes a saved request it keeps watching.
- **Seller's agent:** a dealer uploads photos. Claude writes the condition report. The agent compares every way to sell (lot, ACV, Copart, export) in dollars, finds **buyers already waiting** (including the buyer agent's saved requests), lists in one tap, and messages those buyers before the auction. If the car doesn't sell, it's re-offered to Copart's global buyers.
- **Deal agent:** when the seller asks $15,000 but the top bid is $12,000, each side tells its own agent a private limit. A mediator (Claude writes the reality check from comparable sales) negotiates in rounds, closes a small last gap with a backhaul truck, and then **closes the deal automatically**: escrow payment, transit insurance, loan payoff straight to the lender (e-title, no title delay), truck, seller payout, and ACV's fees.
- **Fleet agent:** a rental fleet sells 120 similar cars at once. The agent forecasts what each market absorbs at full price and sends **full truckloads to nearby markets over the weeks**, compared against dumping everything locally (+22% net) and shipping one by one (−66% transport per car).

## ACV mentor feedback → what we built

| Mentor said | What we changed |
|---|---|
| "ACV makes money only once the car is sold." | Every agent pushes sell-through, and the app shows ACV's fees appearing only on a completed sale ("ACV earns $876, only because the car sold"). |
| "Fleets like rental companies bring huge volumes of similar cars. Distribute them so transport and logistics costs are minimized." | New **Fleet agent**: full car-hauler loads, demand-aware distribution across 16 markets, staggered weeks. |
| "Seller wants $15,000, highest bid is $12,000. How do they connect and agree?" | New **Deal agent**: private limits, mediated rounds, backhaul bridge, human approval. |
| "Automate insurance and payment." | Deal closing automates escrow payment, transit insurance, loan payoff + e-title, truck and payout. |

Pitch line: *"After talking with [mentor name] from ACV, we added a negotiation agent, a fleet logistics agent, and automated closing, because ACV only earns when the car actually sells."*

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

## Demo script (about 3 minutes; cut steps 5–7 for a 2-minute version)

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
4. **🤝 Close the gap** → keep the defaults (ask $15,000, top bid $12,000) → **Start AI negotiation**.
   - *"Each side tells its own agent a private limit. The mediator shows the seller what similar cars actually sold for."*
   - Point at the chart: *"The gap closes in 3 rounds, and a truck already heading that way closes the last $50."*
   - **Both accept** → *"Payment goes into escrow, insurance is bound, the loan is paid off so the title isn't stuck, the truck is booked, and ACV earns its fee because the car sold."*
5. **🚚 Fleet** → **Plan distribution** → *"A rental fleet sells 120 similar cars. Dumping them locally crashes the price. Shipping one by one costs $320 a car. Full truckloads to 7 markets over 2 weeks: +$349K and $108 a car."* → **Approve plan**.
6. **🔔 Agent inbox**: show the messages the agents sent.
7. **🧠 How it works**: the four LangGraph diagrams (also in `docs/graphs/*.png` for slides).

**Wildcard:** let a judge type their own request, for example *"Need 3 Accords under 15K delivered to Buffalo"*. Requests in any language work in live mode.

---

## What's real and what's simulated

| Real | Simulated |
|---|---|
| Claude reads requests (any language), car photos, and explains flagged histories | 310 synthetic ACV + Copart listings and their histories |
| Four LangGraph agents with human-in-the-loop approval, loops, and shared memory | Bids, truck bookings, payments, insurance, title checks and messages (saved locally, nothing is sent) |
| Life Passport checks: hidden salvage and odometer rollback | Prices, ACV fees, market demand and truck costs use simple, illustrative formulas |
| Negotiation and fleet optimization logic | Fleet cars and comparable sales are generated |

Say this plainly if a judge asks: *"Demo data. In production the same tools would call ACV and Copart's inventory, inspection and title systems."*

---

## How it's built

```
app.py                      Streamlit UI (6 tabs)
carcompass/
  agents/buyer.py           LangGraph buyer's agent (interrupt before bidding)
  agents/seller.py          LangGraph seller's agent (interrupts: list now, auction result)
  agents/deal.py            LangGraph deal agent (negotiation loop, backhaul bridge, automated closing)
  agents/fleet.py           LangGraph fleet agent (demand forecast, truckload optimization, scheduling)
  negotiation.py            Offer curves, comparable sales, fees, closing plan
  fleet.py                  Fleet generator, market demand, distribution planner + naive baselines
  llm.py                    Claude calls (structured output + vision), each with a saved fallback
  tools.py                  Search, Life Passport, transport, ranking, best-path math, matching
  store.py                  JSON memory: saved requests, listings, bids, messages
  data/catalog.py           Synthetic marketplace + hand-placed demo cars
scripts/buyer_cli.py        Run the buyer agent in the terminal
scripts/export_graphs.py    Re-render docs/graphs/*.png
tests/                      21 tests, including a full click-through of every tab
```

- **AI is used in 5 places:** understanding requests, reading photos, explaining flagged cars, the negotiation reality check, and the fleet plan summary. Search, history checks, prices, negotiation math, logistics and matching are plain code, so the results are repeatable.
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
