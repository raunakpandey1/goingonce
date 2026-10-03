"""Typed shapes shared by the agents, tools, and UI."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class BuyerRequest(BaseModel):
    make: Optional[str] = None
    model: Optional[str] = None
    min_year: Optional[int] = None
    max_year: Optional[int] = None
    max_price: Optional[int] = None
    max_mileage: Optional[int] = None
    title: Literal["clean", "any"] = "clean"
    quantity: int = Field(default=1, ge=1, le=50)
    destination_city: str = "Buffalo"
    deadline: Optional[str] = None

    def summary(self) -> str:
        parts = [f"{self.quantity}×", " ".join(p for p in [self.make, self.model] if p) or "any car"]
        if self.min_year:
            parts.append(f"{self.min_year}+" if not self.max_year else f"{self.min_year}–{self.max_year}")
        if self.max_price:
            parts.append(f"≤ ${self.max_price:,}")
        if self.max_mileage:
            parts.append(f"≤ {self.max_mileage:,} mi")
        parts.append("clean title" if self.title == "clean" else "any title")
        parts.append(f"→ {self.destination_city}")
        if self.deadline:
            parts.append(f"by {self.deadline}")
        return " · ".join(parts)


class ConditionReport(BaseModel):
    summary: str
    visible_damage: list[str] = []
    condition_grade: float = Field(ge=1, le=5)
    tires: str = "Not visible"
    interior: str = "Not visible"
    detected_vehicle: str = ""
    notes: str = ""


class RiskNote(BaseModel):
    headline: str
    explanation: str
    recommendation: str


BUYER_REQUEST_SCHEMA = {
    "type": "object",
    "properties": {
        "make": {"type": ["string", "null"], "description": "Manufacturer, e.g. Toyota"},
        "model": {"type": ["string", "null"], "description": "Model, singular, e.g. Camry"},
        "min_year": {"type": ["integer", "null"]},
        "max_year": {"type": ["integer", "null"]},
        "max_price": {"type": ["integer", "null"], "description": "Max price per car in USD"},
        "max_mileage": {"type": ["integer", "null"]},
        "title": {"type": "string", "enum": ["clean", "any"]},
        "quantity": {"type": "integer"},
        "destination_city": {"type": "string"},
        "deadline": {"type": ["string", "null"], "description": "e.g. Friday"},
    },
    "required": ["make", "model", "min_year", "max_year", "max_price", "max_mileage",
                 "title", "quantity", "destination_city", "deadline"],
    "additionalProperties": False,
}

CONDITION_REPORT_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string", "description": "2-3 plain-English sentences a dealer would write"},
        "visible_damage": {"type": "array", "items": {"type": "string"}},
        "condition_grade": {"type": "number", "description": "1 (rough) to 5 (like new), ACV style"},
        "tires": {"type": "string"},
        "interior": {"type": "string"},
        "detected_vehicle": {"type": "string", "description": "Best guess of year/make/model/color"},
        "notes": {"type": "string", "description": "Anything a buyer should check in person"},
    },
    "required": ["summary", "visible_damage", "condition_grade", "tires", "interior",
                 "detected_vehicle", "notes"],
    "additionalProperties": False,
}

RISK_NOTE_SCHEMA = {
    "type": "object",
    "properties": {
        "headline": {"type": "string", "description": "Under 12 words"},
        "explanation": {"type": "string", "description": "2-3 short sentences, plain English"},
        "recommendation": {"type": "string", "description": "One sentence: what the buyer should do"},
    },
    "required": ["headline", "explanation", "recommendation"],
    "additionalProperties": False,
}


MEDIATION_SCHEMA = {
    "type": "object",
    "properties": {
        "to_seller": {"type": "string", "description": "2-3 sentences to the seller, plain English"},
        "to_buyer": {"type": "string", "description": "1-2 sentences to the buyer, plain English"},
    },
    "required": ["to_seller", "to_buyer"],
    "additionalProperties": False,
}


FLEET_SUMMARY_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string", "description": "3 short sentences for a fleet manager, plain English"},
    },
    "required": ["summary"],
    "additionalProperties": False,
}
