"""CarCompass demo app.

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
from pathlib import Path

import streamlit as st
from langgraph.types import Command
from PIL import Image

from carcompass import store
from carcompass.agents.buyer import build_buyer_graph
from carcompass.agents.deal import build_deal_graph
from carcompass.agents.seller import build_seller_graph
from carcompass.config import MODEL, demo_safe_default, has_api_key
from carcompass.data.catalog import CITIES, MODEL_BASE

PITCH = "Need 5 Camrys, 2018+, under $12K, clean title, delivered to Rochester by Friday."

st.set_page_config(page_title="CarCompass", page_icon="🧭", layout="wide")

st.markdown("""
<style>
:root { --cc-border: rgba(127,127,127,.28); --cc-soft: rgba(127,127,127,.07); --cc-muted: rgba(127,127,127,.95); }
.block-container { padding-top: 2.2rem; max-width: 1250px; }
.cc-hero h1 { font-size: 2.1rem; margin: 0 0 .1rem 0; }
.cc-hero p { margin: 0 0 .6rem 0; opacity: .8; font-size: 1.05rem; }
.cc-log { border: 1px solid var(--cc-border); border-radius: 12px; padding: .5rem .9rem; background: var(--cc-soft); }
.cc-line { display: flex; gap: .65rem; padding: .42rem 0; border-bottom: 1px dashed var(--cc-border); }
.cc-line:last-child { border-bottom: none; }
.cc-icon { width: 1.4rem; text-align: center; font-weight: 700; color: #1a7f37; flex-shrink: 0; }
.cc-icon.warn { color: #cf222e; } .cc-icon.info { color: #8250df; }
.cc-text { font-weight: 600; } .cc-detail { font-size: .86rem; opacity: .75; margin-top: .1rem; }
.cc-ai { font-size: .7rem; font-weight: 700; padding: .05rem .45rem; border-radius: 999px; margin-left: .35rem; vertical-align: middle; }
.cc-ai.live { background: rgba(130,80,223,.16); color: #8250df; } .cc-ai.saved { background: rgba(127,127,127,.16); }
.cc-card { border: 1px solid var(--cc-border); border-radius: 14px; padding: .9rem 1rem; height: 100%; background: var(--cc-soft); }
.cc-card.bad { border: 2px solid #cf222e; background: rgba(207,34,46,.06); }
.cc-badge { font-size: .72rem; font-weight: 800; padding: .12rem .5rem; border-radius: 6px; color: white; }
.cc-badge.ACV { background: #0969da; } .cc-badge.Copart { background: #d4720b; }
.cc-sub { font-size: .78rem; opacity: .7; margin-left: .35rem; }
.cc-title { font-size: 1.12rem; font-weight: 700; margin: .45rem 0 .1rem 0; }
.cc-price { font-size: 1.35rem; font-weight: 800; } .cc-price span { font-size: .8rem; font-weight: 500; opacity: .7; }
.cc-meta { font-size: .86rem; opacity: .85; margin-top: .15rem; }
.cc-ok { color: #1a7f37; font-weight: 700; font-size: .88rem; margin-top: .45rem; }
.cc-bad { color: #cf222e; font-weight: 800; font-size: .88rem; letter-spacing: .02em; }
.cc-bid { margin-top: .5rem; padding-top: .45rem; border-top: 1px dashed var(--cc-border); font-size: .9rem; }
.cc-banner { border-radius: 12px; padding: .75rem 1rem; font-weight: 700; background: rgba(26,127,55,.12); border: 1px solid rgba(26,127,55,.35); }
.cc-ask { border-radius: 12px; padding: .8rem 1rem; font-weight: 700; font-size: 1.05rem; background: rgba(9,105,218,.10); border: 1px solid rgba(9,105,218,.35); margin: .6rem 0; }
.cc-table { width: 100%; border-collapse: collapse; font-size: .92rem; }
.cc-table th, .cc-table td { padding: .45rem .5rem; border-bottom: 1px solid var(--cc-border); text-align: right; }
.cc-table th:first-child, .cc-table td:first-child { text-align: left; white-space: normal; }
.cc-table td, .cc-table th { white-space: nowrap; }
.cc-table tr.best td { font-weight: 800; background: rgba(26,127,55,.12); }
.cc-note { font-size: .8rem; opacity: .7; }
</style>
""", unsafe_allow_html=True)


# --- Shared ------------------------------------------------------------------

@st.cache_resource
def graphs():
    return build_buyer_graph(), build_seller_graph(), build_deal_graph()


BUYER_GRAPH, SELLER_GRAPH, DEAL_GRAPH = graphs()
ss = st.session_state
ss.setdefault("buyer", None)
ss.setdefault("seller", None)
ss.setdefault("buyer_action", None)
ss.setdefault("seller_action", None)
ss.setdefault("deal", None)
ss.setdefault("deal_action", None)


def esc(s) -> str:
    return html.escape(str(s)) if s is not None else ""


def line_html(line: dict) -> str:
    cls = "warn" if line["icon"] == "⚠" else "info" if line["icon"] in ("↻", "👀", "🔔", "📲", "•") else ""
    ai = f'<span class="cc-ai {line["ai"]}">{"live AI" if line["ai"] == "live" else "saved AI"}</span>' if line.get("ai") else ""
    detail = f'<div class="cc-detail">{esc(line["detail"])}</div>' if line.get("detail") else ""
    return (f'<div class="cc-line"><div class="cc-icon {cls}">{esc(line["icon"])}</div>'
            f'<div><div class="cc-text">{esc(line["text"])}{ai}</div>{detail}</div></div>')


def render_log(box, lines: list[dict]) -> None:
    if lines:
        box.markdown('<div class="cc-log">' + "".join(line_html(l) for l in lines) + "</div>", unsafe_allow_html=True)


def run_stream(graph, payload, config, run: dict, box) -> None:
    """Stream graph updates, animating each new activity line into `box`."""
    pace = ss.get("pace", 0.6)
    for chunk in graph.stream(payload, config, stream_mode="updates"):
        for node, update in chunk.items():
            if node == "__interrupt__":
                run["pending"] = update[0].value
                continue
            for line in (update or {}).get("log", []):
                run["log"].append(line)
                render_log(box, run["log"])
                time.sleep(pace)
    state = graph.get_state(config)
    run["values"] = state.values
    if not state.next:
        run["pending"] = None


def stars(grade: float) -> str:
    return f"★ {grade:.1f}"


def timeline_md(timeline: list[dict]) -> str:
    return "\n".join(f"- **{e['date']}** · {e['source']} · {e['event']}: {e['detail']}" for e in timeline)


def shrink(upload) -> dict:
    """Resize a photo to ≤1568px and re-encode as JPEG for the API."""
    img = Image.open(upload)
    img = img.convert("RGB")
    img.thumbnail((1568, 1568))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=85)
    return {"b64": base64.b64encode(buf.getvalue()).decode(), "media_type": "image/jpeg"}


# --- Sidebar -----------------------------------------------------------------

with st.sidebar:
    st.markdown("## 🧭 CarCompass")
    st.caption("ACV + Copart · AI for Good Hackathon")
    ss.setdefault("demo_safe", demo_safe_default())
    st.toggle("Demo-safe mode", key="demo_safe",
              help="Replays saved AI results, so the demo works even if Wi-Fi or the AI service fails.")
    if ss.demo_safe:
        st.info("Using saved AI results (no network).", icon="💾")
    elif has_api_key():
        st.success(f"Live AI: {MODEL}", icon="⚡")
    else:
        st.warning("No API key found. Using saved AI results.", icon="🔑")
    st.slider("Agent step delay (s)", 0.0, 1.5, 0.6, 0.1, key="pace")
    st.divider()
    if st.button("↺ Reset demo", use_container_width=True):
        store.reset()
        for k in ("buyer", "seller", "buyer_action", "seller_action", "deal", "deal_action"):
            ss[k] = None
        st.rerun()
    st.caption("Demo data: 310 synthetic ACV + Copart listings. Bids, trucks and messages are simulated.")


st.markdown('<div class="cc-hero"><h1>🧭 CarCompass</h1>'
            '<p>Every car finds its best buyer, across ACV <b>and</b> Copart.</p></div>', unsafe_allow_html=True)

tab_buy, tab_sell, tab_deal, tab_inbox, tab_how = st.tabs(
    ["🛒 Buyer's Agent", "📸 Sell in one photo", "🤝 Close the gap", "🔔 Agent inbox", "🧠 How it works"])


# --- Buyer tab ---------------------------------------------------------------

def start_buyer():
    ss.buyer_action = "start"


def approve_buyer():
    ss.buyer_action = "approve"


def decline_buyer():
    ss.buyer_action = "decline"


with tab_buy:
    left, right = st.columns([5, 2])
    with left:
        st.text_area("Tell the agent what you need, in plain words (any language)", PITCH, key="buyer_text", height=90)
    with right:
        st.text_input("Your dealership", "Mike's Motors (Rochester)", key="buyer_name")
        st.button("🤖 Send to agent", type="primary", use_container_width=True, on_click=start_buyer)

    action = ss.buyer_action
    ss.buyer_action = None
    if action == "start":
        ss.buyer = {"thread": uuid.uuid4().hex, "log": [], "pending": None, "values": {}}

    run = ss.buyer
    if run:
        st.markdown("#### Agent activity")
        box = st.empty()
        render_log(box, run["log"])
        config = {"configurable": {"thread_id": run["thread"]}}
        if action == "start":
            run_stream(BUYER_GRAPH, {"request_text": ss.buyer_text, "buyer_name": ss.buyer_name,
                                     "demo_safe": ss.demo_safe}, config, run, box)
        elif action in ("approve", "decline") and run["pending"]:
            run_stream(BUYER_GRAPH, Command(resume={"approved": action == "approve"}), config, run, box)

        values = run["values"]
        matches, flagged = values.get("matches", []), values.get("flagged", [])
        if matches or flagged:
            st.markdown("#### Results")
            cards = matches + flagged
            for i in range(0, len(cards), 4):
                cols = st.columns(4)
                for col, car in zip(cols, cards[i:i + 4]):
                    with col:
                        bad = car.get("passport", {}).get("status") == "flagged"
                        head = (f'<span class="cc-badge {car["source"]}">{car["source"]}</span>'
                                f'<span class="cc-sub">{car["id"]} · ends {esc(car["auction_ends"].replace("Today ", ""))}</span>')
                        body = (f'<div class="cc-title">{car["year"]} {car["make"]} {car["model"]} {esc(car["trim"])}</div>'
                                f'<div class="cc-price">${car["price"]:,} <span>market ${car["market_value"]:,}</span></div>'
                                f'<div class="cc-meta">{car["mileage"]:,} mi · {stars(car["condition_grade"])} · '
                                f'{car["city"]}, {car["state"]}</div>')
                        if bad:
                            risk = car.get("risk", {})
                            extra = (f'<div class="cc-bad" style="margin-top:.5rem">⚠ HIDDEN HISTORY CAUGHT</div>'
                                     f'<div class="cc-meta"><b>{esc(risk.get("headline", ""))}</b></div>'
                                     f'<div class="cc-meta">{esc(risk.get("recommendation", ""))}</div>')
                            st.markdown(f'<div class="cc-card bad">{head}{body}{extra}</div>', unsafe_allow_html=True)
                        else:
                            t = car["transport"]
                            n = len(car["passport"]["timeline"])
                            extra = (f'<div class="cc-meta">🚚 ${t["cost"]:,} to {values["request"]["destination_city"]} · '
                                     f'{t["days"]} day{"s" * (t["days"] != 1)}</div>'
                                     f'<div class="cc-ok">✅ History clean ({n} record{"s" * (n != 1)})</div>'
                                     f'<div class="cc-bid">Bid up to <b>${car["recommended_bid"]:,}</b></div>')
                            st.markdown(f'<div class="cc-card">{head}{body}{extra}</div>', unsafe_allow_html=True)
                        with st.expander("Life Passport"):
                            if bad and car.get("risk"):
                                st.markdown(car["risk"]["explanation"])
                            st.markdown(timeline_md(car["passport"]["timeline"]))

        if run["pending"]:
            st.markdown(f'<div class="cc-ask">🤖 {esc(run["pending"]["question"])}</div>', unsafe_allow_html=True)
            a, b, _ = st.columns([2, 1, 3])
            a.button(f"✅ Approve: bid up to ${run['pending']['total']:,}", type="primary",
                     use_container_width=True, on_click=approve_buyer)
            b.button("Not now", use_container_width=True, on_click=decline_buyer)
        elif values.get("result"):
            res = values["result"]
            if res["bids"]:
                st.success(f"Bids placed on {len(res['bids'])} cars · Truck booked · Title checks started", icon="✅")
            if res["remaining"]:
                st.info(f"Watching ACV + Copart for {res['remaining']} more. Try listing a Camry in "
                        "**📸 Sell in one photo**: this buyer will be waiting for it.", icon="👀")


# --- Seller tab --------------------------------------------------------------

def start_seller():
    ss.seller_action = "start"


def list_now():
    ss.seller_action = "list"


def keep_draft():
    ss.seller_action = "draft"


def sold():
    ss.seller_action = "sold"


def no_sale():
    ss.seller_action = "nosale"


with tab_sell:
    form_col, out_col = st.columns([2, 3], gap="large")
    with form_col:
        st.markdown("#### Your car")
        c1, c2 = st.columns(2)
        year = c1.number_input("Year", 2005, 2026, 2019, key="s_year")
        mileage = c2.number_input("Mileage", 0, 400000, 61000, step=1000, key="s_miles")
        model_names = sorted(f"{mk} {m}" for mk, m in MODEL_BASE)
        mm = st.selectbox("Make & model", model_names, index=model_names.index("Toyota Camry"), key="s_model")
        c3, c4 = st.columns(2)
        trim = c3.text_input("Trim", "SE", key="s_trim")
        city = c4.selectbox("Location", list(CITIES), index=0, key="s_city")
        st.text_input("Dealership", "Sarah's Truck Center (Buffalo)", key="s_seller")
        lot_fit = st.checkbox("I usually sell cars like this on my lot", value=False, key="s_fit")
        photos = st.file_uploader("Car photos (2–4 work best)", type=["jpg", "jpeg", "png", "webp"],
                                  accept_multiple_files=True, key="s_photos")
        if photos:
            st.image([p for p in photos[:4]], width=110)
        else:
            st.caption("No photos? The agent uses a saved sample report.")
        st.button("📸 Analyze & find buyers", type="primary", use_container_width=True, on_click=start_seller)

    with out_col:
        action = ss.seller_action
        ss.seller_action = None
        if action == "start":
            make, model = next((mk, m) for mk, m in MODEL_BASE if f"{mk} {m}" == mm)
            ss.seller = {"thread": uuid.uuid4().hex, "log": [], "pending": None, "values": {},
                         "vehicle": {"year": int(year), "make": make, "model": model, "trim": trim,
                                     "mileage": int(mileage), "city": city, "title_status": "clean",
                                     "seller_name": ss.s_seller, "lot_fit": lot_fit},
                         "photos": [shrink(p) for p in (photos or [])[:4]]}
        run = ss.seller
        if not run:
            st.markdown("#### What the agent does")
            st.markdown("1. **Reads your photos** and writes the condition report\n"
                        "2. **Compares every way to sell** with real dollar amounts\n"
                        "3. **Finds buyers already waiting** for a car like yours\n"
                        "4. **Lists it in one tap** and messages those buyers before the auction\n"
                        "5. **If it doesn't sell**, re-offers it to Copart's global buyers")
        else:
            st.markdown("#### Agent activity")
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
                    st.markdown(f"**AI condition report** · grade **{cond['condition_grade']:.1f}/5**"
                                + ("" if values.get("condition_source") == "live" else "  ·  _saved sample_"))
                    st.write(cond["summary"])
                    d1, d2 = st.columns(2)
                    d1.markdown("**Visible damage**\n" + "\n".join(f"- {d}" for d in cond["visible_damage"] or ["None seen"]))
                    d2.markdown(f"**Tires:** {cond['tires']}  \n**Interior:** {cond['interior']}  \n"
                                f"**Looks like:** {cond['detected_vehicle']}")
                    if cond.get("notes"):
                        st.caption(f"Check in person: {cond['notes']}")
            paths = values.get("paths")
            if paths:
                rows = "".join(
                    f'<tr class="{"best" if r["best"] else ""}"><td>{"✅ " if r["best"] else ""}{r["channel"]}'
                    f'<div class="cc-note">{r["note"]}</div></td><td>${r["gross"]:,}</td>'
                    f'<td>−${r["fees"] + r["transport"] + r["holding"]:,}</td><td>{r["days"]} days</td>'
                    f'<td><b>${r["net"]:,}</b></td></tr>' for r in paths["rows"])
                st.markdown("**Where you make the most money**")
                st.markdown(f'<table class="cc-table"><tr><th>Option</th><th>Sale</th><th>Costs</th>'
                            f'<th>Wait</th><th>You keep</th></tr>{rows}</table>'
                            '<div class="cc-note">Costs = fees + transport + $28/day while the car waits to sell.</div>', unsafe_allow_html=True)
            waiting = values.get("waiting_buyers")
            if waiting is not None and "preview" in values:
                if waiting:
                    st.markdown(f'<div class="cc-banner" style="margin-top:.8rem">🔔 {len(waiting)} buyer'
                                f'{"s are" if len(waiting) != 1 else " is"} already waiting for a car like this</div>',
                                unsafe_allow_html=True)
                    for w in waiting:
                        budget = f" · up to ${w['max_price']:,}" if w.get("max_price") else ""
                        st.caption(f"• {w['buyer']} · {w['channel']}{budget}")
            pending = run["pending"]
            if pending and "best" in pending:
                a, b, _ = st.columns([2, 1, 2])
                a.button("🚀 List now", type="primary", use_container_width=True, on_click=list_now,
                         help=f"Lists via {pending['best']}")
                b.button("Save draft", use_container_width=True, on_click=keep_draft)
            elif pending and "listing_id" in pending:
                st.markdown(f'<div class="cc-ask">⏱ {pending["listing_id"]} is live. Simulate the auction result:</div>',
                            unsafe_allow_html=True)
                a, b, _ = st.columns([1, 1, 2])
                a.button("✅ Sold", use_container_width=True, on_click=sold)
                b.button("✖ No sale", use_container_width=True, on_click=no_sale)
            elif values.get("auction", {}).get("sold") is False:
                st.success("No car left unsold: re-offered to Copart's global buyers.", icon="🌍")
            elif values.get("auction", {}).get("sold"):
                st.success("Sold. Transport and title paperwork started.", icon="✅")


# --- Close-the-gap tab -------------------------------------------------------

def start_deal():
    ss.deal_action = "start"


def accept_deal():
    ss.deal_action = "accept"


def walk_away():
    ss.deal_action = "walk"


AVATARS = {"mediator": ("Mediator", "🧭"), "seller": ("Seller's agent", "🏷️"), "buyer": ("Buyer's agent", "💰")}

with tab_deal:
    st.caption("The seller wants more than the top bid. Each side tells its own agent a private limit; "
               "an AI mediator closes the gap with market data, then the deal closes itself.")
    in_col, out_col = st.columns([2, 3], gap="large")
    with in_col:
        with st.expander("Car: 2020 Toyota Camry LE · 52,000 mi · Buffalo", expanded=False):
            c1, c2 = st.columns(2)
            d_year = c1.number_input("Year", 2005, 2026, 2020, key="d_year")
            d_miles = c2.number_input("Mileage", 0, 400000, 52000, step=1000, key="d_miles")
            d_models = sorted(f"{mk} {m}" for mk, m in MODEL_BASE)
            d_mm = st.selectbox("Make & model", d_models, index=d_models.index("Toyota Camry"), key="d_model")
            d_grade = st.slider("Condition grade", 1.0, 5.0, 4.0, 0.1, key="d_grade")
        st.markdown("**🏷️ Seller**")
        a, b = st.columns(2)
        d_ask = a.number_input("Asking price ($)", 1000, 200000, 15000, step=250, key="d_ask")
        d_min = b.number_input("Private minimum ($)", 1000, 200000, 12800, step=250, key="d_min",
                               help="Only the seller's own agent knows this.")
        d_lien = st.number_input("Loan still owed on the car ($)", 0, 100000, 5000, step=500, key="d_lien")
        st.markdown("**💰 Buyer**")
        a, b = st.columns(2)
        d_bid = a.number_input("Top bid ($)", 1000, 200000, 12000, step=250, key="d_bid")
        d_max = b.number_input("Private maximum ($)", 1000, 200000, 13400, step=250, key="d_max",
                               help="Only the buyer's own agent knows this.")
        d_buyer_city = st.selectbox("Buyer location", list(CITIES), index=list(CITIES).index("Rochester"), key="d_city")
        st.button("🤝 Start AI negotiation", type="primary", use_container_width=True, on_click=start_deal)

    with out_col:
        action = ss.deal_action
        ss.deal_action = None
        if action == "start":
            make, model = next((mk, m) for mk, m in MODEL_BASE if f"{mk} {m}" == d_mm)
            ss.deal = {"thread": uuid.uuid4().hex, "log": [], "pending": None, "values": {},
                       "payload": {"car": {"year": int(d_year), "make": make, "model": model, "trim": "",
                                           "mileage": int(d_miles), "grade": float(d_grade), "city": "Buffalo"},
                                   "seller": "Sarah's Truck Center (Buffalo)", "buyer": "Mike's Motors (Rochester)",
                                   "buyer_city": d_buyer_city, "ask": int(d_ask), "seller_min": int(d_min),
                                   "high_bid": int(d_bid), "buyer_max": int(d_max), "lien": int(d_lien),
                                   "demo_safe": ss.demo_safe}}
        run = ss.deal
        if not run:
            st.markdown("#### What the agents do")
            st.markdown("1. **Reality check:** compare the ask with recent sales and the cost of waiting\n"
                        "2. **Negotiate in rounds:** seller's agent and buyer's agent move toward each other, "
                        "never past their private limits\n"
                        "3. **Bridge the last gap:** e.g. a truck already heading that way lowers delivery cost\n"
                        "4. **Close automatically:** escrow payment, transit insurance, loan payoff, e-title, truck, "
                        "seller payout\n\n"
                        "ACV earns its fees **only when the car sells**, so every closed gap is revenue.")
        else:
            st.markdown("#### Agent activity")
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
                st.markdown("**Offers by round** (the gap closing)")
                chart = alt.Chart(df).mark_line(point=True, strokeWidth=3).encode(
                    x=alt.X("round:O", title="Round", axis=alt.Axis(labelAngle=0)),
                    y=alt.Y("offer:Q", title="Offer ($)", scale=alt.Scale(zero=False)),
                    color=alt.Color("side:N", title=None,
                                    scale=alt.Scale(domain=["Seller", "Buyer"], range=["#0969da", "#d4720b"])),
                    tooltip=["side", "round", alt.Tooltip("offer:Q", format="$,")])
                st.altair_chart(chart.properties(height=220), use_container_width=True)
            if values.get("messages"):
                with st.expander("Negotiation chat", expanded=not run["pending"] is None):
                    for m in values["messages"]:
                        name, avatar = AVATARS[m["who"]]
                        with st.chat_message(name, avatar=avatar):
                            st.write(m["text"])
            if run["pending"]:
                st.markdown(f'<div class="cc-ask">🤝 {esc(run["pending"]["question"])}</div>', unsafe_allow_html=True)
                a, b, _ = st.columns([2, 1, 2])
                a.button(f"✅ Both accept ${run['pending']['price']:,}", type="primary",
                         use_container_width=True, on_click=accept_deal)
                b.button("Walk away", use_container_width=True, on_click=walk_away)
            closing = values.get("closing")
            if closing:
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Deal price", f"${closing['price']:,}", f"+${closing['price'] - values['high_bid']:,} vs bid")
                m2.metric("Seller payout", f"${closing['seller_payout']:,}", help="After the seller fee and loan payoff")
                m3.metric("Buyer pays", f"${closing['buyer_pays']:,}",
                          help="All-in: price, buyer fee, transport and insurance, held in escrow")
                m4.metric("ACV earns", f"${closing['acv']['total']:,}", "sale-only fees")
                st.success("Deal closed: payment in escrow, insurance bound, loan paid off, title moving, truck booked.",
                           icon="✅")
            elif values.get("deal") is None and values.get("round") and not run["pending"]:
                st.info("No deal this time. Nobody was pushed past their limit, and the car goes to the next "
                        "best buyers.", icon="↻")


# --- Inbox tab ---------------------------------------------------------------

with tab_inbox:
    state = store.load()
    a, b = st.columns(2)
    with a:
        st.markdown("#### 📲 Messages sent by the agents")
        if not state["notifications"]:
            st.caption("Nothing yet. Run the buyer or seller agent.")
        for n in state["notifications"][:20]:
            icon = {"match": "🔔", "buyer": "🛒", "seller": "📸"}.get(n["kind"], "•")
            st.markdown(f"{icon} **To {n['to']}** · {n['created']}  \n{n['text']}")
    with b:
        st.markdown("#### 👀 Buyer requests the agents are watching")
        for w in reversed(state["wishes"]):
            what = " ".join(p for p in [w.get("make"), w.get("model")] if p) or "any car"
            bits = [f"{w.get('quantity', 1)}× {what}"]
            if w.get("min_year"):
                bits.append(f"{w['min_year']}+")
            if w.get("max_price"):
                bits.append(f"≤ ${w['max_price']:,}")
            st.markdown(f"**{w['buyer']}** · {w.get('channel', 'ACV')}  \n{' · '.join(bits)}")
        if state["bids"]:
            st.markdown("#### 🧾 Proxy bids placed")
            for bid in state["bids"]:
                st.caption(f"{bid['buyer']}: {bid['car_id']} up to ${bid['max_bid']:,}")


# --- How it works tab --------------------------------------------------------

GRAPH_DIR = Path(__file__).resolve().parent / "docs" / "graphs"


def show_graph(name: str, graph) -> None:
    png = GRAPH_DIR / f"{name}.png"
    if png.exists():
        st.image(str(png), width=330)
    else:  # regenerate with scripts/export_graphs.py
        st.code(graph.get_graph().draw_mermaid(), language="text")


with tab_how:
    st.markdown("#### Three LangGraph agents, one shared memory")
    st.markdown(
        "- **Buyer's agent:** understands a plain-English request → searches ACV + Copart → checks every car's "
        "**Life Passport** → explains anything suspicious → ranks and quotes transport → **waits for your approval** "
        "→ bids, books the truck, starts title checks, and keeps watching for the rest.\n"
        "- **Seller's agent:** reads the photos → compares every way to sell → finds **buyers already waiting** → "
        "lists in one tap and messages them → if there's no sale, re-offers to Copart's global buyers.\n"
        "- **Deal agent:** when the ask is above the top bid, a mediator negotiates in rounds between the seller's "
        "and buyer's agents (each keeps its private limit), bridges the last gap, then closes the deal: escrow "
        "payment, transit insurance, loan payoff, e-title, truck, payout. ACV earns only when the car sells.\n"
        "- **Shared memory:** the buyer's unfilled request becomes a saved wish that the seller's agent matches against.")
    st.markdown("**Where AI is used (Claude):** understanding requests in any language · reading car photos · "
                "explaining flagged histories.  \n**Plain code (repeatable):** search, history checks, pricing, "
                "transport, matching.  \n**Safety:** nothing is spent or listed without a human tap; demo-safe mode "
                "replays saved AI results.")
    g1, g2, g3 = st.columns(3)
    with g1:
        st.markdown("**Buyer's agent graph (LangGraph)**")
        show_graph("buyer_agent", BUYER_GRAPH)
    with g2:
        st.markdown("**Seller's agent graph (LangGraph)**")
        show_graph("seller_agent", SELLER_GRAPH)
    with g3:
        st.markdown("**Deal agent graph (LangGraph)**")
        show_graph("deal_agent", DEAL_GRAPH)
    st.caption("Demo data is synthetic. In production the same tools would call ACV and Copart's inventory, "
               "inspection and title systems.")
