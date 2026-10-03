# GoingOnce

**Every car finds its best buyer, across ACV and Copart.**

Four AI agents built with **LangGraph** and **Claude Opus 5.5**, one tab each:

| Tab | What the agent does |
|---|---|
| 🛒 **Buy** | A dealer says what they need in plain words. The agent searches ACV + Copart, checks each car's history, throws out cars with hidden damage, and **asks before bidding**. It keeps watching for anything it couldn't find. |
| 📸 **Sell** | Photos in. AI writes the condition report, shows where the seller keeps the most money, and finds **buyers already waiting**. One tap lists it. No sale → re-offered to Copart's global buyers. |
| 🤝 **Negotiate** | Seller asks $15,000, top bid is $12,000. Each side's agent keeps a private limit; a mediator closes the gap in rounds, then the deal **closes itself**: escrow payment, insurance, loan payoff, title, truck. |
| 🚚 **Fleet** | A rental fleet sells 120 similar cars. The agent spreads them across markets in **full truckloads**, so prices hold and transport stays low. |

---

## Run it

```bash
cd ~/Desktop/hackathon2026/goingonce
.venv/bin/streamlit run app.py
```

Open http://localhost:8501. The sidebar is hidden; click **»** (top left) to open it:
- **Demo-safe mode:** uses saved AI results. Turn on if the Wi-Fi is bad.
- **↺ Reset demo:** press before presenting.

First-time setup on another machine: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`, then `cp .env.example .env` and paste the API key. Never commit `.env`.

---

## 2.5-minute demo

**Before you go on:** Reset demo · open the 📸 Sell tab and upload 1–2 car photos (JPG) · go back to 🛒 Buy.

| Time | Do | Say |
|---|---|---|
| **0:00** | 🛒 **Buy** → **Send to agent** | "A Rochester dealer needs 5 Camrys. Instead of scrolling thousands of listings, he just says it." |
| 0:10 | (log runs ~10 s) point at the red card | "It searched ACV and Copart and checked every car's history. This one looks like the best deal, but it was flooded and sold as salvage on Copart, then re-titled clean. Only ACV + Copart together can see that." |
| 0:35 | **Approve** | "Nothing is spent without the dealer's tap. It found 3 of 5, so it keeps watching for 2 more." |
| **0:45** | 📸 **Sell** → **Analyze & find buyers** | "A Buffalo dealer sells a Camry from photos." |
| 0:55 | (~10 s) table + banner | "AI wrote the condition report. ACV auction keeps her the most money, and 3 buyers are already waiting, including the dealer we just saw." |
| 1:10 | **List now** | "Listed, and the waiting buyers are messaged before the auction starts. More cars sell, and ACV only earns when a car sells." |
| **1:20** | 🤝 **Negotiate** → **Start AI negotiation** | "Seller wants $15,000, the top bid is $12,000. Each side's agent keeps a private limit." |
| 1:30 | (~7 s) point at the chart | "The mediator shows real comparable sales. They meet in 3 rounds, and a truck already on the route closes the last $50." |
| 1:45 | **Both accept** | "Then it closes itself: payment in escrow, insurance, the loan paid off so the title isn't stuck, truck booked, and ACV earns its fee." |
| **2:00** | 🚚 **Fleet** → **Plan distribution** | "A rental fleet sells 120 similar cars. Dump them locally and prices crash; ship one by one and it's $320 a car." |
| 2:10 | (~5 s) metrics | "Full truckloads to 7 markets over 2 weeks: $349K more, $108 a car." |
| **2:25** | stop | |

**Short on time?** Skip 🚚 Fleet and say its one line.
**Wi-Fi bad?** Turn on Demo-safe mode. Everything works the same with saved AI results.

---

## What's real and what's simulated

| Real | Simulated |
|---|---|
| Claude reads requests (any language), car photos, and writes the explanations | 310 ACV + Copart listings and their histories (generated) |
| Four LangGraph agents with human approval steps, loops, and shared memory | Bids, payments, insurance, trucks and messages (saved locally, nothing is sent) |
| History checks: hidden salvage and odometer rollback | Prices, ACV fees, market demand and truck costs (simple, illustrative formulas) |

If a judge asks: *"Demo data. In production the same tools would call ACV and Copart's inventory, inspection and title systems."*

## ACV mentor feedback → what we built

| Mentor said | What we built |
|---|---|
| ACV makes money only when a car sells | Every agent pushes sell-through; the app shows ACV's fee appearing only on a sale |
| Fleets bring big volumes; minimize transport | 🚚 Fleet agent: full truckloads, demand-aware distribution, staggered weeks |
| Seller wants $15K, top bid $12K | 🤝 Negotiate agent: private limits, mediated rounds, backhaul bridge |
| Automate insurance and payment | Deal closing: escrow, transit insurance, loan payoff + e-title, truck, payout |

---

## How it's built

```
app.py                      Streamlit UI (4 tabs)
carcompass/
  agents/buyer.py           Buy agent (pauses for approval before bidding)
  agents/seller.py          Sell agent (pauses for "List now" and the auction result)
  agents/deal.py            Negotiate agent (negotiation loop, backhaul bridge, automated closing)
  agents/fleet.py           Fleet agent (demand check, truckload plan, scheduling)
  llm.py                    Claude calls, each with a saved fallback
  tools.py                  Search, history checks, transport, pricing, matching
  negotiation.py            Offer curves, comparable sales, fees, closing plan
  fleet.py                  Fleet generator, market demand, distribution planner
  store.py                  Shared memory: saved requests, listings, bids, messages
  data/catalog.py           Generated marketplace + hand-placed demo cars
docs/graphs/                Agent diagrams (PNG) for slides
docs/screenshots/           App screenshots for slides
tests/                      21 tests, including a click-through of every tab
```

- Claude is used for language and photos only; search, history checks, prices, negotiation math and logistics are plain code, so results repeat.
- Model: `claude-opus-5-5` (change with `CARCOMPASS_MODEL` in `.env`). If a Claude call fails, that step uses its saved result.

```bash
.venv/bin/python -m pytest -q        # all tests
```

## Troubleshooting
- **iPhone photos won't upload:** HEIC isn't supported. Use JPG or a screenshot.
- **AI slow:** turn on Demo-safe mode.
- **Port in use:** `.venv/bin/streamlit run app.py --server.port 8502`
