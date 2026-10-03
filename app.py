"""GoingOnce demo app.

    .venv/bin/streamlit run app.py
"""

from __future__ import annotations

import base64
import html
import io
import time
import uuid

import altair as alt
import pandas as pd
import streamlit as st
from langgraph.types import Command
from PIL import Image

from carcompass import store
from carcompass.agents.buyer import build_buyer_graph
from carcompass.agents.deal import build_deal_graph
from carcompass.agents.fleet import build_fleet_graph
from carcompass.agents.seller import build_seller_graph
from carcompass.config import demo_safe_default
from carcompass.data.catalog import CITIES, MODEL_BASE
from carcompass.fleet import FLEET_MODELS

PITCH = "Need 5 Camrys, 2018+, under $12K, clean title, delivered to Rochester by Friday."
BUYER = "Mike's Motors (Rochester)"
SELLER = "Sarah's Truck Center (Buffalo)"
PACE = 0.35  # seconds between activity-log lines, so the audience can follow

st.set_page_config(page_title="GoingOnce", page_icon="🔨", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
:root { --cc-border: rgba(127,127,127,.28); --cc-soft: rgba(127,127,127,.07); }
.block-container { padding-top: 2rem; max-width: 1250px; }
.cc-hero h1 { font-size: 2.1rem; margin: 0; }
.cc-hero p { margin: 0 0 .5rem 0; opacity: .75; font-size: 1.05rem; }
.cc-log { border: 1px solid var(--cc-border); border-radius: 12px; padding: .4rem .9rem; background: var(--cc-soft); margin-bottom: .8rem; }
.cc-line { display: flex; gap: .65rem; padding: .38rem 0; border-bottom: 1px dashed var(--cc-border); }
.cc-line:last-child { border-bottom: none; }
.cc-icon { width: 1.4rem; text-align: center; font-weight: 700; color: #1a7f37; flex-shrink: 0; }
.cc-icon.warn { color: #cf222e; } .cc-icon.info { color: #8250df; }
.cc-text { font-weight: 600; } .cc-detail { font-size: .86rem; opacity: .75; margin-top: .1rem; }
.cc-ai { font-size: .68rem; font-weight: 800; padding: .05rem .45rem; border-radius: 999px; margin-left: .35rem;
         vertical-align: middle; background: rgba(130,80,223,.16); color: #8250df; }
.cc-card { border: 1px solid var(--cc-border); border-radius: 14px; padding: .9rem 1rem; background: var(--cc-soft); }
.cc-card.bad { border: 2px solid #cf222e; background: rgba(207,34,46,.06); }
.cc-badge { font-size: .72rem; font-weight: 800; padding: .12rem .5rem; border-radius: 6px; color: white; }
.cc-badge.ACV { background: #0969da; } .cc-badge.Copart { background: #d4720b; }
.cc-title { font-size: 1.08rem; font-weight: 700; margin: .45rem 0 .1rem 0; }
.cc-price { font-size: 1.35rem; font-weight: 800; } .cc-price span { font-size: .8rem; font-weight: 500; opacity: .7; }
.cc-meta { font-size: .86rem; opacity: .85; margin-top: .15rem; }
.cc-ok { color: #1a7f37; font-weight: 700; font-size: .88rem; margin-top: .45rem; }
.cc-bad { color: #cf222e; font-weight: 800; font-size: .88rem; margin-top: .5rem; }
.cc-banner { border-radius: 12px; padding: .7rem 1rem; font-weight: 700; background: rgba(26,127,55,.12);
             border: 1px solid rgba(26,127,55,.35); margin: .8rem 0 .3rem 0; }
.cc-ask { border-radius: 12px; padding: .75rem 1rem; font-weight: 700; font-size: 1.05rem;
          background: rgba(9,105,218,.10); border: 1px solid rgba(9,105,218,.35); margin: .6rem 0; }
.cc-table { width: 100%; border-collapse: collapse; font-size: .92rem; margin-top: .3rem; }
.cc-table th, .cc-table td { padding: .45rem .5rem; border-bottom: 1px solid var(--cc-border); text-align: right; white-space: nowrap; }
.cc-table th:first-child, .cc-table td:first-child { text-align: left; white-space: normal; }
.cc-table tr.best td { font-weight: 800; background: rgba(26,127,55,.12); }
</style>
""", unsafe_allow_html=True)


# --- Shared ------------------------------------------------------------------

@st.cache_resource
def graphs():
    return build_buyer_graph(), build_seller_graph(), build_deal_graph(), build_fleet_graph()


BUYER_GRAPH, SELLER_GRAPH, DEAL_GRAPH, FLEET_GRAPH = graphs()
ss = st.session_state
RUNS = ("buyer", "seller", "deal", "fleet")
for k in RUNS:
    ss.setdefault(k, None)
    ss.setdefault(f"{k}_action", None)


def esc(s) -> str:
    return html.escape(str(s)) if s is not None else ""


def line_html(line: dict) -> str:
    cls = "warn" if line["icon"] == "⚠" else "info" if line["icon"] in ("↻", "👀", "🔔", "📲", "•", "↔") else ""
    ai = '<span class="cc-ai">AI</span>' if line.get("ai") else ""
    detail = f'<div class="cc-detail">{esc(line["detail"])}</div>' if line.get("detail") else ""
    return (f'<div class="cc-line"><div class="cc-icon {cls}">{esc(line["icon"])}</div>'
            f'<div><div class="cc-text">{esc(line["text"])}{ai}</div>{detail}</div></div>')


def render_log(box, lines: list[dict]) -> None:
    if lines:
        box.markdown('<div class="cc-log">' + "".join(line_html(l) for l in lines) + "</div>", unsafe_allow_html=True)


def run_stream(graph, payload, config, run: dict, box) -> None:
    """Stream graph updates, animating each new activity line into `box`."""
    for chunk in graph.stream(payload, config, stream_mode="updates"):
        for node, update in chunk.items():
            if node == "__interrupt__":
                run["pending"] = update[0].value
                continue
            for line in (update or {}).get("log", []):
                run["log"].append(line)
                render_log(box, run["log"])
                time.sleep(ss.get("pace", PACE))
    state = graph.get_state(config)
    run["values"] = state.values
    if not state.next:
        run["pending"] = None


def setter(key: str, value: str):
    def _set():
        ss[key] = value
    return _set


def take_action(name: str):
    action = ss[f"{name}_action"]
    ss[f"{name}_action"] = None
    return action


def shrink(upload) -> dict:
    """Resize a photo to ≤1568px and re-encode as JPEG for the API."""
    img = Image.open(upload).convert("RGB")
    img.thumbnail((1568, 1568))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=85)
    return {"b64": base64.b64encode(buf.getvalue()).decode(), "media_type": "image/jpeg"}


def timeline_md(timeline: list[dict]) -> str:
    return "\n".join(f"- **{e['date']}** · {e['source']} · {e['event']}" for e in timeline)


MODEL_NAMES = sorted(f"{mk} {m}" for mk, m in MODEL_BASE)


def split_model(label: str) -> tuple[str, str]:
    return next((mk, m) for mk, m in MODEL_BASE if f"{mk} {m}" == label)


# --- Sidebar (presenter controls only) ----------------------------------------

with st.sidebar:
    ss.setdefault("demo_safe", demo_safe_default())
    st.toggle("Demo-safe mode", key="demo_safe", help="Uses saved AI results. Turn on if the Wi-Fi is bad.")
    if st.button("↺ Reset demo", use_container_width=True):
        store.reset()
        for k in RUNS:
            ss[k] = None
            ss[f"{k}_action"] = None
        st.rerun()

st.markdown('<div class="cc-hero"><h1>🔨 GoingOnce</h1>'
            '<p>Every car finds its best buyer, across ACV and Copart.</p></div>', unsafe_allow_html=True)

tab_buy, tab_sell, tab_deal, tab_fleet = st.tabs(["🛒 Buy", "📸 Sell", "🤝 Negotiate", "🚚 Fleet"])


# --- Buy -----------------------------------------------------------------------

with tab_buy:
    left, right = st.columns([5, 1.4])
    left.text_area("What do you need?", PITCH, key="buyer_text", height=80)
    right.markdown("<div style='height:1.75rem'></div>", unsafe_allow_html=True)
    right.button("▶ Send to agent", type="primary", use_container_width=True, on_click=setter("buyer_action", "start"))

    action = take_action("buyer")
    if action == "start":
        ss.buyer = {"thread": uuid.uuid4().hex, "log": [], "pending": None, "values": {}}
    run = ss.buyer
    if run:
        box = st.empty()
        render_log(box, run["log"])
        config = {"configurable": {"thread_id": run["thread"]}}
        if action == "start":
            run_stream(BUYER_GRAPH, {"request_text": ss.buyer_text, "buyer_name": BUYER, "demo_safe": ss.demo_safe},
                       config, run, box)
        elif action in ("approve", "decline") and run["pending"]:
            run_stream(BUYER_GRAPH, Command(resume={"approved": action == "approve"}), config, run, box)

        values = run["values"]
        cards = values.get("matches", []) + values.get("flagged", [])
        for i in range(0, len(cards), 4):
            for col, car in zip(st.columns(4), cards[i:i + 4]):
                with col:
                    bad = car["passport"]["status"] == "flagged"
                    body = (f'<span class="cc-badge {car["source"]}">{car["source"]}</span>'
                            f'<div class="cc-title">{car["year"]} {car["make"]} {car["model"]}</div>'
                            f'<div class="cc-price">${car["price"]:,} <span>market ${car["market_value"]:,}</span></div>'
                            f'<div class="cc-meta">{car["mileage"]:,} mi · ★ {car["condition_grade"]:.1f} · {car["city"]}</div>')
                    if bad:
                        body += (f'<div class="cc-bad">⚠ HIDDEN HISTORY CAUGHT</div>'
                                 f'<div class="cc-meta">{esc(car.get("risk", {}).get("headline", ""))}</div>')
                    else:
                        t = car["transport"]
                        body += (f'<div class="cc-meta">🚚 ${t["cost"]:,} · {t["days"]} day{"s" * (t["days"] != 1)}</div>'
                                 f'<div class="cc-ok">✅ History clean</div>'
                                 f'<div class="cc-meta">Bid up to <b>${car["recommended_bid"]:,}</b></div>')
                    st.markdown(f'<div class="cc-card{" bad" if bad else ""}">{body}</div>', unsafe_allow_html=True)
                    with st.expander("History"):
                        st.markdown(timeline_md(car["passport"]["timeline"]))

        if run["pending"]:
            st.markdown(f'<div class="cc-ask">💬 {esc(run["pending"]["question"])}</div>', unsafe_allow_html=True)
            a, b, _ = st.columns([2, 1, 3])
            a.button(f"✅ Approve: bid up to ${run['pending']['total']:,}", type="primary", use_container_width=True,
                     on_click=setter("buyer_action", "approve"))
            b.button("Not now", use_container_width=True, on_click=setter("buyer_action", "decline"))
        elif values.get("result", {}).get("bids"):
            st.success(f"Bids placed on {len(values['result']['bids'])} cars · Truck booked · Title checks started",
                       icon="✅")


# --- Sell ----------------------------------------------------------------------

with tab_sell:
    form_col, out_col = st.columns([2, 3], gap="large")
    with form_col:
        c1, c2 = st.columns(2)
        year = c1.number_input("Year", 2005, 2026, 2019, key="s_year")
        mileage = c2.number_input("Mileage", 0, 400000, 61000, step=1000, key="s_miles")
        mm = st.selectbox("Make & model", MODEL_NAMES, index=MODEL_NAMES.index("Toyota Camry"), key="s_model")
        city = st.selectbox("Location", list(CITIES), index=0, key="s_city")
        photos = st.file_uploader("Car photos", type=["jpg", "jpeg", "png", "webp"], accept_multiple_files=True,
                                  key="s_photos")
        if photos:
            st.image(list(photos[:4]), width=100)
        st.button("📸 Analyze & find buyers", type="primary", use_container_width=True,
                  on_click=setter("seller_action", "start"))

    with out_col:
        action = take_action("seller")
        if action == "start":
            make, model = split_model(mm)
            ss.seller = {"thread": uuid.uuid4().hex, "log": [], "pending": None, "values": {},
                         "vehicle": {"year": int(year), "make": make, "model": model, "trim": "",
                                     "mileage": int(mileage), "city": city, "title_status": "clean",
                                     "seller_name": SELLER, "lot_fit": False},
                         "photos": [shrink(p) for p in (photos or [])[:4]]}
        run = ss.seller
        if run:
            box = st.empty()
            render_log(box, run["log"])
            config = {"configurable": {"thread_id": run["thread"]}}
            if action == "start":
                run_stream(SELLER_GRAPH, {"vehicle": run["vehicle"], "photos": run["photos"],
                                          "demo_safe": ss.demo_safe}, config, run, box)
            elif action in ("list", "draft") and run["pending"]:
                run_stream(SELLER_GRAPH, Command(resume={"list": action == "list"}), config, run, box)
            elif action in ("sold", "nosale") and run["pending"]:
                run_stream(SELLER_GRAPH, Command(resume={"sold": action == "sold"}), config, run, box)

            values = run["values"]
            cond = values.get("condition")
            if cond:
                with st.container(border=True):
                    st.markdown(f"**AI condition report · {cond['condition_grade']:.1f}/5**")
                    st.write(cond["summary"])
                    if cond["visible_damage"]:
                        st.caption("Damage: " + " · ".join(cond["visible_damage"]))
            paths = values.get("paths")
            if paths:
                rows = "".join(
                    f'<tr class="{"best" if r["best"] else ""}"><td>{"✅ " if r["best"] else ""}{r["channel"]}</td>'
                    f'<td>${r["gross"]:,}</td><td>−${r["fees"] + r["transport"] + r["holding"]:,}</td>'
                    f'<td>{r["days"]} days</td><td><b>${r["net"]:,}</b></td></tr>' for r in paths["rows"])
                st.markdown(f'<table class="cc-table"><tr><th>Option</th><th>Sale</th><th>Costs</th><th>Wait</th>'
                            f'<th>You keep</th></tr>{rows}</table>', unsafe_allow_html=True)
            waiting = values.get("waiting_buyers")
            if waiting:
                st.markdown(f'<div class="cc-banner">🔔 {len(waiting)} buyer{"s" if len(waiting) != 1 else ""} '
                            f'already waiting for this car</div>', unsafe_allow_html=True)
                st.caption(" · ".join(w["buyer"] for w in waiting))
            pending = run["pending"]
            if pending and "best" in pending:
                a, b, _ = st.columns([2, 1, 2])
                a.button("🚀 List now", type="primary", use_container_width=True, on_click=setter("seller_action", "list"))
                b.button("Save draft", use_container_width=True, on_click=setter("seller_action", "draft"))
            elif pending and "listing_id" in pending:
                st.markdown('<div class="cc-ask">⏱ Auction result?</div>', unsafe_allow_html=True)
                a, b, _ = st.columns([1, 1, 2])
                a.button("✅ Sold", use_container_width=True, on_click=setter("seller_action", "sold"))
                b.button("✖ No sale", use_container_width=True, on_click=setter("seller_action", "nosale"))
            elif values.get("auction", {}).get("sold") is False:
                st.success("No car left unsold: re-offered to Copart's global buyers.", icon="🌍")
            elif values.get("auction", {}).get("sold"):
                st.success("Sold. Transport and title paperwork started.", icon="✅")


# --- Negotiate -------------------------------------------------------------------

with tab_deal:
    in_col, out_col = st.columns([2, 3], gap="large")
    with in_col:
        st.markdown("**2020 Toyota Camry · 52,000 mi**")
        st.markdown("🏷️ **Seller**")
        a, b = st.columns(2)
        d_ask = a.number_input("Asking price", 1000, 200000, 15000, step=250, key="d_ask")
        d_min = b.number_input("Lowest OK (private)", 1000, 200000, 12800, step=250, key="d_min")
        d_lien = st.number_input("Loan still owed", 0, 100000, 5000, step=500, key="d_lien")
        st.markdown("💰 **Buyer**")
        a, b = st.columns(2)
        d_bid = a.number_input("Top bid", 1000, 200000, 12000, step=250, key="d_bid")
        d_max = b.number_input("Highest OK (private)", 1000, 200000, 13400, step=250, key="d_max")
        st.button("🤝 Start AI negotiation", type="primary", use_container_width=True,
                  on_click=setter("deal_action", "start"))

    with out_col:
        action = take_action("deal")
        if action == "start":
            ss.deal = {"thread": uuid.uuid4().hex, "log": [], "pending": None, "values": {},
                       "payload": {"car": {"year": 2020, "make": "Toyota", "model": "Camry", "trim": "",
                                           "mileage": 52000, "grade": 4.0, "city": "Buffalo"},
                                   "seller": SELLER, "buyer": BUYER, "buyer_city": "Rochester",
                                   "ask": int(d_ask), "seller_min": int(d_min), "high_bid": int(d_bid),
                                   "buyer_max": int(d_max), "lien": int(d_lien), "demo_safe": ss.demo_safe}}
        run = ss.deal
        if run:
            box = st.empty()
            render_log(box, run["log"])
            config = {"configurable": {"thread_id": run["thread"]}}
            if action == "start":
                run_stream(DEAL_GRAPH, run["payload"], config, run, box)
            elif action in ("accept", "walk") and run["pending"]:
                run_stream(DEAL_GRAPH, Command(resume={"accepted": action == "accept"}), config, run, box)

            values = run["values"]
            rounds = values.get("rounds", [])
            if len(rounds) > 1:
                df = pd.DataFrame(rounds).rename(columns={"seller": "Seller", "buyer": "Buyer"})
                df = df.melt("round", var_name="side", value_name="offer")
                chart = alt.Chart(df).mark_line(point=True, strokeWidth=3).encode(
                    x=alt.X("round:O", title="Round", axis=alt.Axis(labelAngle=0)),
                    y=alt.Y("offer:Q", title=None, scale=alt.Scale(zero=False), axis=alt.Axis(format="$,.0f")),
                    color=alt.Color("side:N", title=None,
                                    scale=alt.Scale(domain=["Seller", "Buyer"], range=["#0969da", "#d4720b"])))
                st.altair_chart(chart.properties(height=200), use_container_width=True)
            if run["pending"]:
                st.markdown(f'<div class="cc-ask">🤝 {esc(run["pending"]["question"])}</div>', unsafe_allow_html=True)
                a, b, _ = st.columns([2, 1, 2])
                a.button(f"✅ Both accept ${run['pending']['price']:,}", type="primary", use_container_width=True,
                         on_click=setter("deal_action", "accept"))
                b.button("Walk away", use_container_width=True, on_click=setter("deal_action", "walk"))
            closing = values.get("closing")
            if closing:
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Deal price", f"${closing['price']:,}", f"+${closing['price'] - values['high_bid']:,} vs bid")
                m2.metric("Seller gets", f"${closing['seller_payout']:,}")
                m3.metric("Buyer pays", f"${closing['buyer_pays']:,}")
                m4.metric("ACV earns", f"${closing['acv']['total']:,}")
                st.success("Deal closed: payment, insurance, loan payoff, title and truck handled.", icon="✅")
            elif values.get("round") and values.get("deal") is None and not run["pending"]:
                st.info("No deal. Nobody was pushed past their limit.", icon="↻")


# --- Fleet -----------------------------------------------------------------------

with tab_fleet:
    in_col, out_col = st.columns([2, 3], gap="large")
    with in_col:
        f_count = st.slider("Cars to sell", 30, 240, 120, 10, key="f_count")
        f_lots = st.multiselect("Fleet lots", list(CITIES), default=["Buffalo", "Rochester", "Albany"], key="f_lots")
        f_weeks = st.slider("Weeks", 1, 4, 2, key="f_weeks")
        st.button("🚚 Plan distribution", type="primary", use_container_width=True,
                  on_click=setter("fleet_action", "start"), disabled=not f_lots)

    with out_col:
        action = take_action("fleet")
        if action == "start":
            ss.fleet = {"thread": uuid.uuid4().hex, "log": [], "pending": None, "values": {},
                        "payload": {"fleet_name": "Rental fleet", "count": int(f_count), "lots": list(f_lots),
                                    "models": [list(m) for m in FLEET_MODELS[:3]], "weeks": int(f_weeks),
                                    "demo_safe": ss.demo_safe}}
        run = ss.fleet
        if run:
            box = st.empty()
            render_log(box, run["log"])
            config = {"configurable": {"thread_id": run["thread"]}}
            if action == "start":
                run_stream(FLEET_GRAPH, run["payload"], config, run, box)
            elif action in ("approve", "reject") and run["pending"]:
                run_stream(FLEET_GRAPH, Command(resume={"approved": action == "approve"}), config, run, box)

            values = run["values"]
            plan, base = values.get("plan"), values.get("baselines")
            if plan and base:
                gain = plan["net"] - base["dump"]["net"]
                trucks = sum(1 for l in plan["loads"] if l["truck"])
                m1, m2, m3 = st.columns(3)
                m1.metric("Extra vs dumping", f"+${gain / 1000:,.0f}K", f"+{plan['net'] / base['dump']['net'] - 1:.0%}")
                m2.metric("Transport / car", f"${plan['transport_per_car']}",
                          f"-${base['single']['transport_per_car'] - plan['transport_per_car']} vs 1-by-1",
                          delta_color="inverse")
                m3.metric("Truckloads", trucks)
                rows = "".join(
                    f'<tr class="{"best" if p is plan else ""}"><td>{"✅ " if p is plan else ""}{p["name"]}</td>'
                    f'<td>${p["avg_price"]:,}</td><td>${p["transport_per_car"]:,}</td><td><b>${p["net"]:,}</b></td></tr>'
                    for p in (base["dump"], base["single"], plan))
                st.markdown(f'<table class="cc-table"><tr><th>Plan</th><th>Avg sale</th><th>Transport/car</th>'
                            f'<th>Net</th></tr>{rows}</table>', unsafe_allow_html=True)
                bars = pd.DataFrame([{"market": l["to"], "week": f"Week {l['week']}", "cars": l["cars"]}
                                     for l in plan["loads"]])
                st.altair_chart(alt.Chart(bars).mark_bar().encode(
                    x=alt.X("sum(cars):Q", title="Cars"),
                    y=alt.Y("market:N", sort="-x", title=None, axis=alt.Axis(labelOverlap=False, labelLimit=140)),
                    color=alt.Color("week:N", title=None,
                                    scale=alt.Scale(range=["#0969da", "#d4720b", "#8250df", "#1a7f37"]))
                ).properties(height=240), use_container_width=True)
            if run["pending"]:
                a, b, _ = st.columns([2, 1, 2])
                a.button("✅ Approve plan", type="primary", use_container_width=True,
                         on_click=setter("fleet_action", "approve"))
                b.button("Not now", use_container_width=True, on_click=setter("fleet_action", "reject"))
            elif values.get("schedule"):
                st.success("Approved: auctions staggered, car haulers booked, buyers alerted.", icon="✅")
