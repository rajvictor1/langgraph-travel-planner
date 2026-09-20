from __future__ import annotations

import json
import os
import re

from .models import TripRequest


def parse_with_openai(text: str, defaults: TripRequest) -> TripRequest:
    """Use OpenAI when configured; otherwise preserve editable form values."""
    if not text.strip() or not os.getenv("OPENAI_API_KEY"):
        return defaults.model_copy(update={"raw_request": text})

    from langchain_openai import ChatOpenAI

    model = ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"), temperature=0)
    structured = model.with_structured_output(TripRequest)
    parsed = structured.invoke(
        "Extract travel requirements. Use the supplied defaults when a field is not stated. "
        "Never invent allergies. Budget means total-trip budget.\n"
        f"Defaults: {json.dumps(defaults.model_dump())}\nRequest: {text}"
    )
    return parsed.model_copy(update={"raw_request": text})


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

