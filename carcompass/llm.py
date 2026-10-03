"""Claude calls, with a deterministic fallback for every one of them.

Every helper returns (result, source) where source is "live" (Claude answered)
or "saved" (demo-safe mode, no key, or the call failed). The demo never breaks.
"""

from __future__ import annotations

import base64
import json
import logging
import re

import anthropic

from .config import MODEL, has_api_key
from .data.catalog import CITIES, MODEL_BASE
from .schemas import (
    BUYER_REQUEST_SCHEMA,
    CONDITION_REPORT_SCHEMA,
    RISK_NOTE_SCHEMA,
    BuyerRequest,
    ConditionReport,
    RiskNote,
)

log = logging.getLogger(__name__)
_client: anthropic.Anthropic | None = None


def client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(timeout=60.0, max_retries=1)
    return _client


class LLMUnavailable(Exception):
    pass


def call_json(system: str, content: list | str, schema: dict, effort: str = "low",
              max_tokens: int = 4000) -> dict:
    """One structured-output call to Claude. Raises LLMUnavailable on any failure."""
    if not has_api_key():
        raise LLMUnavailable("no API key")
    params = dict(
        model=MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": content}],
        output_config={"effort": effort, "format": {"type": "json_schema", "schema": schema}},
    )
    try:
        try:
            # Server-side fallback: if a safety classifier declines, the API reroutes.
            response = client().beta.messages.create(
                **params, betas=["server-side-fallback-2026-07-01"], fallbacks="default")
        except anthropic.BadRequestError as e:
            if "fallback" not in str(e).lower():
                raise
            response = client().messages.create(**params)
    except anthropic.APIError as e:  # auth, rate limit, network, server, bad request
        log.warning("Claude call failed: %s", e)
        raise LLMUnavailable(str(e)) from e
    if response.stop_reason in ("refusal", "max_tokens"):
        raise LLMUnavailable(f"stop_reason={response.stop_reason}")
    text = next((b.text for b in response.content if b.type == "text"), None)
    if not text:
        raise LLMUnavailable("empty response")
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise LLMUnavailable("invalid JSON") from e


# --- 1. Understand the buyer's request ----------------------------------------

REQUEST_SYSTEM = (
    "You turn a car dealer's plain-English buying request into search filters for a "
    "wholesale car marketplace. Use singular model names exactly as manufacturers write "
    "them (Camry, F-150, CR-V). Infer the make from the model when it is not stated. "
    "Prices are per car in USD; '12K' means 12000. 'Clean title' means title=clean; if "
    "the request accepts salvage or rebuilt cars, title=any; otherwise default to clean. "
    "quantity defaults to 1. destination_city must be one of: " + ", ".join(CITIES) +
    " (pick the closest one; default Buffalo). The request may be in any language."
)


def parse_request(text: str, demo_safe: bool) -> tuple[BuyerRequest, str]:
    if not demo_safe:
        try:
            data = call_json(REQUEST_SYSTEM, text, BUYER_REQUEST_SCHEMA, effort="low")
            req = BuyerRequest(**data)
            if req.destination_city not in CITIES:
                req.destination_city = "Buffalo"
            return req, "live"
        except (LLMUnavailable, ValueError) as e:
            log.warning("parse_request fallback: %s", e)
    return rule_parse(text), "saved"


def rule_parse(text: str) -> BuyerRequest:
    """Regex parser used in demo-safe mode. Handles the pitch sentence and close variants."""
    t = text.lower().replace(",", "")
    make = model = None
    for mk, m in sorted(MODEL_BASE, key=lambda k: -len(k[1])):  # longest names first
        pattern = r"\bram\s*1500" if m == "1500" else r"\b" + re.escape(m.lower()) + r"(?:s|es)?\b"
        if re.search(pattern, t):
            make, model = mk, m
            break
    if not make:
        make = next((mk for mk, _ in MODEL_BASE if re.search(r"\b" + mk.lower() + r"s?\b", t)), None)
    qty = re.search(r"(?:need|want|buy|find|looking for|get me|source)\s+(\d+)", t) or re.search(r"^(\d{1,2})\s|\b(\d{1,2})\s+(?:[a-z0-9\-]+\s+){0,2}[a-z0-9\-]+s\b", t)
    years = re.search(r"\b(20[0-2]\d)\s*(?:\+|or newer|and newer|or later)", t)
    year_range = re.search(r"\b(20[0-2]\d)\s*(?:-|to|–)\s*(20[0-2]\d)\b", t)
    price = re.search(r"(?:under|below|less than|max|up to|<)\s*\$?\s*(\d+(?:\.\d+)?)\s*(k)?", t)
    miles = re.search(r"(?:under|below|less than)\s*(\d+)\s*(k)?\s*(?:miles|mi)\b", t)
    deadline = re.search(r"\bby\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday|tomorrow|next week)", t)
    city = next((c for c in CITIES if c.lower() in t), "Buffalo")
    max_price = None
    if price and not (miles and price.start() == miles.start()):
        max_price = int(float(price.group(1)) * (1000 if price.group(2) else 1))
    return BuyerRequest(
        make=make, model=model,
        min_year=int(year_range.group(1)) if year_range else int(years.group(1)) if years else None,
        max_year=int(year_range.group(2)) if year_range else None,
        max_price=max_price,
        max_mileage=int(miles.group(1)) * (1000 if miles.group(2) else 1) if miles else None,
        title="any" if re.search(r"salvage ok|any title|salvage is fine|rebuilt ok", t) else "clean",
        quantity=int(next(g for g in qty.groups() if g)) if qty else 1,
        destination_city=city,
        deadline=deadline.group(1).title() if deadline else None,
    )


# --- 2. Explain a flagged car ---------------------------------------------------

RISK_SYSTEM = (
    "You are a used-car risk analyst for a dealer. You get one car's listing, the joined "
    "ACV + Copart history for its VIN, and the automatic flags. Explain to a busy dealer, "
    "in plain English, what the history shows and whether the current inspection notes "
    "look consistent with a proper repair. Be factual; do not invent events that are not "
    "in the history."
)


def explain_risk(car: dict, passport: dict, demo_safe: bool) -> tuple[RiskNote, str]:
    if not demo_safe:
        payload = {
            "listing": {k: car[k] for k in ("year", "make", "model", "trim", "mileage", "price",
                                            "title_status", "city", "state", "inspection_notes")},
            "history": passport["timeline"],
            "flags": [f["text"] for f in passport["flags"]],
        }
        try:
            data = call_json(RISK_SYSTEM, json.dumps(payload), RISK_NOTE_SCHEMA, effort="low")
            return RiskNote(**data), "live"
        except (LLMUnavailable, ValueError) as e:
            log.warning("explain_risk fallback: %s", e)
    return saved_risk_note(car, passport), "saved"


def saved_risk_note(car: dict, passport: dict) -> RiskNote:
    kinds = {f["type"] for f in passport["flags"]}
    if "hidden_salvage" in kinds:
        loss = next((e for e in passport["timeline"] if "total loss" in e["event"].lower()), None)
        what = loss["event"].split(":")[-1].strip() if loss and ":" in loss["event"] else "damage"
        when = loss["date"][:4] if loss else "the past"
        return RiskNote(
            headline=f"Hidden {what} history: title was washed",
            explanation=(f"Copart sold this {car['year']} {car['model']} as salvage after a {what} "
                         f"total loss in {when}. It was re-titled in another state, and the clean "
                         f"title hides that. Today's inspection notes ('{car['inspection_notes']}') "
                         f"fit a cosmetic cleanup, not a documented repair."),
            recommendation="Skip it, or demand repair records and an underbody inspection before bidding.",
        )
    return RiskNote(
        headline="Odometer reading went backwards",
        explanation=" ".join(f["text"] for f in passport["flags"]) +
                    " That pattern usually means the odometer was rolled back.",
        recommendation="Skip it; a rollback also voids the title's mileage statement.",
    )


# --- 3. Read car photos -----------------------------------------------------------

VISION_SYSTEM = (
    "You are an experienced ACV-style vehicle inspector. From the photos, write the condition "
    "report a dealer would trust. Only describe what you can actually see; say 'Not visible' "
    "when a part is not shown. Grade on a 1-5 scale (5 = like new, 3 = average wholesale, "
    "1 = rough)."
)

SAVED_CONDITION = ConditionReport(
    summary="Clean, straight sedan with good paint overall. Light scuffs on the rear bumper "
            "and a small door ding on the driver side. Ready for retail after a quick detail.",
    visible_damage=["Light scuffs, rear bumper", "Small ding, driver rear door"],
    condition_grade=4.0,
    tires="Matching set, roughly 60-70% tread",
    interior="Not visible in photos",
    detected_vehicle="Silver Toyota Camry, around 2018-2020",
    notes="Check for warning lights on start-up and confirm two keys.",
)


def inspect_photos(images: list[tuple[bytes, str]], vehicle_hint: str,
                   demo_safe: bool) -> tuple[ConditionReport, str]:
    if not demo_safe and images:
        content: list = []
        for data, media_type in images[:4]:
            content.append({"type": "image", "source": {
                "type": "base64", "media_type": media_type,
                "data": base64.standard_b64encode(data).decode("utf-8")}})
        content.append({"type": "text", "text": f"Seller says this is: {vehicle_hint}. Write the condition report."})
        try:
            data = call_json(VISION_SYSTEM, content, CONDITION_REPORT_SCHEMA, effort="low")
            data["condition_grade"] = max(1.0, min(5.0, float(data["condition_grade"])))
            return ConditionReport(**data), "live"
        except (LLMUnavailable, ValueError) as e:
            log.warning("inspect_photos fallback: %s", e)
    return SAVED_CONDITION, "saved"
