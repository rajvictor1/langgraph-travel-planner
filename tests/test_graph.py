from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from travel_agent.graph import build_graph
from travel_agent.models import TripRequest


def run(request: TripRequest, thread: str):
    graph = build_graph(InMemorySaver())
    return graph.invoke(
        {"request": request.model_dump(), "planning_attempt": 1, "audit_events": []},
        {"configurable": {"thread_id": thread}},
    )


def test_valid_plan_pauses_for_human_approval():
    result = run(TripRequest(), "valid")
    assert result["status"] == "awaiting_approval"
    assert result["evaluation"]["valid"] is True
    assert result["planning_attempt"] == 1
    assert result["__interrupt__"]


def test_budget_failure_stops_after_three_total_attempts():
    result = run(TripRequest(budget=1000), "budget")
    assert result["status"] == "no_match"
    assert result["planning_attempt"] == 3
    assert result["evaluation"]["valid"] is False


def test_targeted_replan_retains_valid_results():
    result = run(TripRequest(stay_style="luxury", budget=45000), "targeted")
    assert result["planning_attempt"] <= 3
    assert result["flight_results"]
    replan_events = [e for e in result["audit_events"] if e["node"] == "replan_strategy"]
    assert replan_events
    assert "stays" in replan_events[0]["details"]["targets"]


def test_missing_information_pauses_before_search():
    graph = build_graph(InMemorySaver())
    result = graph.invoke(
        {"request": {"origin": "", "destination": "Goa"}, "planning_attempt": 1, "audit_events": []},
        {"configurable": {"thread_id": "missing"}},
    )
    assert result["missing_fields"]
    assert result["__interrupt__"][0].value["type"] == "missing_information"
    assert not result.get("flight_results")


def test_rejection_feedback_starts_fresh_attempt_cycle():
    graph = build_graph(InMemorySaver())
    config = {"configurable": {"thread_id": "feedback"}}
    first = graph.invoke({"request": TripRequest().model_dump(), "planning_attempt": 1, "audit_events": []}, config)
    assert first["__interrupt__"]
    second = graph.invoke(Command(resume={"approved": False, "feedback": "Use an Airbnb"}), config)
    assert second["planning_attempt"] == 1
    assert second["request"]["stay_style"] == "airbnb"
    assert second["__interrupt__"]
