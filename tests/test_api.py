from api.index import create_plan, health
from travel_agent.models import TripRequest


def test_health_reports_langgraph():
    assert health() == {"status": "ok", "engine": "python-langgraph", "inventory": "mock"}


def test_vercel_api_creates_serializable_plan():
    response = create_plan(TripRequest())
    assert response["thread_id"]
    assert response["state"]["evaluation"]["valid"] is True
    assert response["state"]["selected_plan"]["costs"]["total"] > 0
    assert "__interrupt__" not in response["state"]

