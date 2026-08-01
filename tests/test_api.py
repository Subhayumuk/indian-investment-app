import pytest
from fastapi.testclient import TestClient

from app.main import create_app

SAMPLE_PAYLOAD = {
    "tax_resident_denmark": True,
    "has_nro_account": True,
    "india_principal_inr": 500_000,
    "india_annual_interest_inr": 30_000,
    "risk_profile": "moderate",
    "investment_horizon_years": 5,
}


@pytest.fixture
def client():
    return TestClient(create_app())


def assert_planner_response_shape(data: dict) -> None:
    assert "output" in data
    assert data["output"]
    assert "structured_result" in data or "result" in data


def test_root_page_loads_successfully(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Danish Resident NRI" in response.text


def test_planner_api_returns_200_for_valid_sample(client):
    response = client.post("/api/agent", json=SAMPLE_PAYLOAD)

    assert response.status_code == 200


def test_planner_response_contains_output(client):
    response = client.post("/api/agent", json=SAMPLE_PAYLOAD)
    data = response.json()

    assert response.status_code == 200
    assert "output" in data
    assert isinstance(data["output"], str)
    assert len(data["output"]) > 0


def test_planner_response_contains_structured_result_or_result(client):
    response = client.post("/api/agent", json=SAMPLE_PAYLOAD)
    data = response.json()

    assert response.status_code == 200
    assert "structured_result" in data or "result" in data

    structured = data.get("structured_result") or data.get("result")
    assert isinstance(structured, dict)
    assert "liquidity_plan" in structured


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"tax_resident_denmark": True},
        {"india_principal_inr": None, "india_annual_interest_inr": None},
        {"risk_profile": "unknown-profile", "investment_horizon_years": 0},
        {"india_principal_inr": 0, "monthly_expenses_dkk": 0},
        {"notes": "", "has_aadhaar": None},
    ],
    ids=[
        "empty-body",
        "single-field",
        "null-optionals",
        "unknown-risk-and-zero-horizon",
        "zero-amounts",
        "empty-string-and-null-bool",
    ],
)
def test_missing_or_invalid_optional_values_do_not_crash_api(client, payload):
    response = client.post("/api/agent", json=payload)

    assert response.status_code == 200
    assert_planner_response_shape(response.json())


def test_analyze_endpoint_matches_planner_contract(client):
    response = client.post("/analyze", json=SAMPLE_PAYLOAD)

    assert response.status_code == 200
    assert_planner_response_shape(response.json())
