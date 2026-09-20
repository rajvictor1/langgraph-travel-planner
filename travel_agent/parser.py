from __future__ import annotations

import json
import os
import re

from .models import TripRequest


def interpret_request(text: str, defaults: TripRequest) -> tuple[TripRequest, str]:
    """Return structured requirements and a transparent interpretation mode."""
    if not text.strip() or not os.getenv("OPENAI_API_KEY"):
        return defaults.model_copy(update={"raw_request": text}), "editable_fields"

    try:
        from langchain_openai import ChatOpenAI

        model = ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"), temperature=0)
        structured = model.with_structured_output(TripRequest)
        parsed = structured.invoke(
            "Extract travel requirements into the supplied schema. Preserve a supplied default when the request "
            "does not explicitly change it. Never invent allergies, dietary restrictions, dates, airports, or "
            "preferences. Budget is the total-trip ceiling. Return only structured data.\n"
            f"Editable defaults: {json.dumps(defaults.model_dump())}\nTraveller request: {text}"
        )
        return parsed.model_copy(update={"raw_request": text}), "openai_structured_output"
    except Exception:
        # The planner remains usable when the provider is unavailable or misconfigured.
        return defaults.model_copy(update={"raw_request": text}), "editable_fields_fallback"


def parse_with_openai(text: str, defaults: TripRequest) -> TripRequest:
    """Backward-compatible helper used by the Streamlit interface."""
    return interpret_request(text, defaults)[0]


def apply_feedback(request: TripRequest, feedback: str) -> TripRequest:
    """Small deterministic feedback interpreter for the mock-learning workflow."""
    updates: dict = {"raw_request": f"{request.raw_request}\nFeedback: {feedback}".strip()}
    lower = feedback.lower()
    budget = re.search(r"(?:budget|under|max(?:imum)?)\D{0,8}([\d,]+)", lower)
    if budget:
        updates["budget"] = float(budget.group(1).replace(",", ""))
    if "nonstop" in lower or "direct" in lower:
        updates["flight_type"] = "nonstop"
    if "hostel" in lower:
        updates["stay_style"] = "hostel"
    elif "airbnb" in lower:
        updates["stay_style"] = "airbnb"
    elif "luxury" in lower:
        updates["stay_style"] = "luxury"
    elif "hotel" in lower:
        updates["stay_style"] = "hotel"
    return request.model_copy(update=updates)
