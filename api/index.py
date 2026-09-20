from __future__ import annotations

from datetime import datetime, timezone
import os
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from pydantic import BaseModel

from travel_agent.graph import build_graph
from travel_agent.models import TripRequest
from travel_agent.parser import interpret_request

app = FastAPI(title="Atlas LangGraph Travel Planner", version="0.1.0")
graph = build_graph(InMemorySaver())


class ApprovalInput(BaseModel):
    thread_id: str
    approved: bool
    feedback: str = ""


def clean(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: clean(item) for key, item in value.items() if key != "__interrupt__"}
    if isinstance(value, (list, tuple)):
        return [clean(item) for item in value]
    if hasattr(value, "value"):
        return clean(value.value)
    return value


@app.get("/api/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "engine": "python-langgraph",
        "inventory": "mock",
        "llm": "openai" if os.getenv("OPENAI_API_KEY") else "not_configured",
    }


@app.post("/api/plan")
def create_plan(request: TripRequest) -> dict[str, Any]:
    thread_id = str(uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    interpreted, mode = interpret_request(request.raw_request, request)
    interpretation_event = {
        "time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "node": "interpret_request",
        "status": "completed",
        "message": "Request interpreted with OpenAI structured output" if mode == "openai_structured_output" else "Request interpreted from editable fields",
        "details": {"mode": mode, "model": os.getenv("OPENAI_MODEL", "gpt-4.1-mini") if mode == "openai_structured_output" else None},
    }
    state = graph.invoke(
        {"request": interpreted.model_dump(), "planning_attempt": 1, "audit_events": [interpretation_event]},
        config,
    )
    return {"thread_id": thread_id, "state": clean(state)}


@app.post("/api/approval")
def approve_plan(decision: ApprovalInput) -> dict[str, Any]:
    config = {"configurable": {"thread_id": decision.thread_id}}
    try:
        state = graph.invoke(
            Command(resume={"approved": decision.approved, "feedback": decision.feedback}),
            config,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=409,
            detail="This short-lived demo session expired. Create the plan again before approving it.",
        ) from exc
    return {"thread_id": decision.thread_id, "state": clean(state)}
