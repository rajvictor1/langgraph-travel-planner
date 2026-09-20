from __future__ import annotations

import operator
from datetime import datetime, timezone
from typing import Annotated, Any, Literal, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, RetryPolicy, interrupt

from .mock_data import ACTIVITIES, FLIGHTS, STAYS
from .models import TripRequest
from .parser import apply_feedback

MAX_PLANNING_ATTEMPTS = 3


class TravelState(TypedDict, total=False):
    request: dict[str, Any]
    planning_attempt: int
    flight_results: list[dict[str, Any]]
    stay_results: list[dict[str, Any]]
    activity_results: list[dict[str, Any]]
    selected_plan: dict[str, Any]
    evaluation: dict[str, Any]
    retry_targets: list[str]
    status: str
    approved: bool
    feedback: str
    audit_events: Annotated[list[dict[str, Any]], operator.add]
    missing_fields: list[str]
    search_strategy: dict[str, Any]


def event(node: str, message: str, *, status: str = "completed", details: dict | None = None) -> dict:
    return {
        "time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "node": node,
        "status": status,
        "message": message,
        "details": details or {},
    }


def prepare_request(state: TravelState) -> dict:
    attempt = state.get("planning_attempt", 0) or 1
    return {
        "planning_attempt": attempt,
        "status": "searching",
        "audit_events": [event("request_parser", "Trip requirements validated", details={"planning_attempt": attempt})],
    }


def validate_requirements(state: TravelState) -> dict:
    req = state["request"]
    required = ["origin", "destination", "start_date", "duration_days", "travellers", "budget"]
    missing = [field for field in required if req.get(field) in (None, "", 0)]
    return {
        "missing_fields": missing,
        "audit_events": [event("requirements_validator", "Required trip details are complete" if not missing else "Required trip details are missing", details={"missing_fields": missing})],
    }


def route_requirements(state: TravelState) -> Literal["collect_missing_information", "plan_searches"]:
    return "collect_missing_information" if state.get("missing_fields") else "plan_searches"


def collect_missing_information(state: TravelState) -> Command:
    supplied = interrupt({
        "type": "missing_information",
        "message": "Please provide the missing trip details.",
        "missing_fields": state.get("missing_fields", []),
    })
    updated = {**state["request"], **supplied}
    return Command(
        update={"request": updated, "audit_events": [event("missing_information", "Traveller supplied missing requirements", details={"fields": list(supplied)})]},
        goto="validate_requirements",
    )


def plan_searches(state: TravelState) -> dict:
    strategy = {
        "attempt": state["planning_attempt"],
        "parallel_searches": ["flights", "stays", "activities"],
        "retain_valid_results": state["planning_attempt"] > 1,
    }
    return {
        "search_strategy": strategy,
        "status": "searching",
        "audit_events": [event("search_planner", f"Prepared search strategy for attempt {state['planning_attempt']}", details=strategy)],
    }


def _allowed_flights(req: TripRequest, relaxed: bool = False) -> list[dict]:
    origins = {req.origin, *req.alternative_origins}
    candidates = [f for f in FLIGHTS if f["origin"] in origins and f["destination"].lower() == req.destination.lower() and f["class"] == req.flight_class]
    if req.flight_type == "nonstop" and not relaxed:
        candidates = [f for f in candidates if f["stops"] == 0]
    elif req.flight_type == "one_stop" and not relaxed:
        candidates = [f for f in candidates if f["stops"] <= 1]
    candidates = [f for f in candidates if f["layover_hours"] <= req.max_layover_hours]
    return sorted(candidates, key=lambda x: x["price"])


def search_flights(state: TravelState) -> dict:
    req = TripRequest.model_validate(state["request"])
    results = _allowed_flights(req)
    return {"flight_results": results, "audit_events": [event("flight_search", f"Found {len(results)} matching mock flights", details={"retained": [r["id"] for r in results]})]}


def search_stays(state: TravelState) -> dict:
    req = TripRequest.model_validate(state["request"])
    results = [s for s in STAYS if s["destination"].lower() == req.destination.lower() and (req.stay_style == "any" or s["style"] == req.stay_style)]
    results = sorted(results, key=lambda x: x["nightly"])
    return {"stay_results": results, "audit_events": [event("stay_search", f"Found {len(results)} matching mock stays", details={"retained": [r["id"] for r in results]})]}


def search_activities(state: TravelState) -> dict:
    req = TripRequest.model_validate(state["request"])
    wanted = set(req.activities)
    results = [a for a in ACTIVITIES if a["destination"].lower() == req.destination.lower() and (not wanted or wanted.intersection(a["tags"]))]
    return {"activity_results": results, "audit_events": [event("activity_search", f"Found {len(results)} matching mock activities", details={"retained": [r["id"] for r in results]})]}


def compose_itinerary(state: TravelState) -> dict:
    req = TripRequest.model_validate(state["request"])
    flights, stays, activities = state.get("flight_results", []), state.get("stay_results", []), state.get("activity_results", [])
    flight = flights[0] if flights else None
    stay = stays[0] if stays else None
    chosen_activities = activities[: min(3, len(activities))]
    nights = max(req.duration_days - 1, 1)
    flight_total = (flight["price"] * 2 * req.travellers) if flight else 0
    stay_total = (stay["nightly"] * nights) if stay else 0
    activity_total = sum(x["price"] for x in chosen_activities) * req.travellers
    total = flight_total + stay_total + activity_total
    plan = {
        "flight": flight,
        "stay": stay,
        "activities": chosen_activities,
        "costs": {"flights": flight_total, "stay": stay_total, "activities": activity_total, "total": total, "currency": req.currency},
        "nights": nights,
    }
    return {
        "selected_plan": plan,
        "audit_events": [event("itinerary_composer", "Combined retained search results into one itinerary", details={"flight": flight and flight["id"], "stay": stay and stay["id"], "activities": [a["id"] for a in chosen_activities], "total": total})],
    }


def evaluate_plan(state: TravelState) -> dict:
    req = TripRequest.model_validate(state["request"])
    plan = state["selected_plan"]
    failures: list[str] = []
    retry_targets: list[str] = []
    if not plan.get("flight"):
        failures.append("No flight matches the current route and flight constraints")
        retry_targets.append("flights")
    if not plan.get("stay"):
        failures.append("No stay matches the selected accommodation style")
        retry_targets.append("stays")
    if not plan.get("activities"):
        failures.append("No activities match the requested interests")
        retry_targets.append("activities")
    total = plan["costs"]["total"]
    if plan.get("flight") and plan.get("stay") and total > req.budget:
        failures.append(f"Plan exceeds budget by {total - req.budget:,.0f} {req.currency}")
        costs = plan["costs"]
        retry_targets.append("flights" if costs["flights"] >= costs["stay"] else "stays")
    valid = not failures
    evaluation = {"valid": valid, "failures": failures, "budget_remaining": req.budget - total}
    return {
        "evaluation": evaluation,
        "retry_targets": sorted(set(retry_targets)),
        "status": "awaiting_approval" if valid else "needs_replan",
        "audit_events": [event("budget_evaluator", "Plan satisfies all constraints" if valid else "Plan requires targeted replanning", details={"total": total, "budget": req.budget, "failures": failures, "retry_targets": sorted(set(retry_targets))})],
    }


def route_after_evaluation(state: TravelState) -> Literal["human_approval", "targeted_replan", "no_match"]:
    if state["evaluation"]["valid"]:
        return "human_approval"
    if state["planning_attempt"] >= MAX_PLANNING_ATTEMPTS:
        return "no_match"
    return "targeted_replan"


def targeted_replan(state: TravelState) -> dict:
    req = TripRequest.model_validate(state["request"])
    targets = state.get("retry_targets", [])
    attempt = state["planning_attempt"] + 1
    updates: dict[str, Any] = {"planning_attempt": attempt}
    changes: list[str] = []

    if "flights" in targets:
        results = _allowed_flights(req, relaxed=True)
        updates["flight_results"] = results
        changes.append("Expanded flight search while preserving the layover ceiling")
    if "stays" in targets:
        results = [s for s in STAYS if s["destination"].lower() == req.destination.lower()]
        updates["stay_results"] = sorted(results, key=lambda x: x["nightly"])
        changes.append("Expanded accommodation styles and sorted by price")
    if "activities" in targets:
        results = [a for a in ACTIVITIES if a["destination"].lower() == req.destination.lower()]
        updates["activity_results"] = sorted(results, key=lambda x: x["price"])
        changes.append("Expanded activities while retaining valid flight and stay results")
    updates["audit_events"] = [event("replan_strategy", f"Started planning attempt {attempt} of {MAX_PLANNING_ATTEMPTS}", details={"targets": targets, "changes": changes})]
    return updates


def human_approval(state: TravelState) -> Command:
    decision = interrupt({
        "type": "trip_approval",
        "message": "Review the itinerary, approve it, or provide change feedback.",
        "plan": state["selected_plan"],
        "attempt": state["planning_attempt"],
    })
    if decision.get("approved"):
        return Command(update={"approved": True, "status": "approved", "audit_events": [event("human_approval", "Traveller approved the itinerary")]}, goto=END)

    feedback = decision.get("feedback", "Please revise the plan")
    revised = apply_feedback(TripRequest.model_validate(state["request"]), feedback)
    return Command(update={"request": revised.model_dump(), "feedback": feedback, "planning_attempt": 1, "audit_events": [event("human_approval", "Traveller requested changes; a new three-attempt cycle started", details={"feedback": feedback})]}, goto="plan_searches")


def no_match(state: TravelState) -> dict:
    return {"status": "no_match", "approved": False, "audit_events": [event("planning_limit", "Stopped after three total planning attempts", details={"failures": state.get("evaluation", {}).get("failures", [])})]}


def build_graph(checkpointer=None):
    builder = StateGraph(TravelState)
    transient_retry = RetryPolicy(max_attempts=3, initial_interval=0.2, backoff_factor=2)
    builder.add_node("prepare_request", prepare_request)
    builder.add_node("validate_requirements", validate_requirements)
    builder.add_node("collect_missing_information", collect_missing_information)
    builder.add_node("plan_searches", plan_searches)
    builder.add_node("search_flights", search_flights, retry_policy=transient_retry)
    builder.add_node("search_stays", search_stays, retry_policy=transient_retry)
    builder.add_node("search_activities", search_activities, retry_policy=transient_retry)
    builder.add_node("evaluate_plan", evaluate_plan)
    builder.add_node("compose_itinerary", compose_itinerary)
    builder.add_node("targeted_replan", targeted_replan)
    builder.add_node("human_approval", human_approval)
    builder.add_node("no_match", no_match)

    builder.add_edge(START, "prepare_request")
    builder.add_edge("prepare_request", "validate_requirements")
    builder.add_conditional_edges("validate_requirements", route_requirements)
    builder.add_edge("plan_searches", "search_flights")
    builder.add_edge("plan_searches", "search_stays")
    builder.add_edge("plan_searches", "search_activities")
    builder.add_edge(["search_flights", "search_stays", "search_activities"], "compose_itinerary")
    builder.add_edge("compose_itinerary", "evaluate_plan")
    builder.add_conditional_edges("evaluate_plan", route_after_evaluation)
    builder.add_edge("targeted_replan", "compose_itinerary")
    builder.add_edge("no_match", END)
    return builder.compile(checkpointer=checkpointer)
