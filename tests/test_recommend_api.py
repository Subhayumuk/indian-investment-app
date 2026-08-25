import pytest
from fastapi.testclient import TestClient

from app.main import create_app

VALID_PAYLOAD = {
    "session_id": "test-001",
    "personal": {
        "age": 35,
        "marital_status": "single",
        "dependents": 0,
        "employment_status": "salaried",
        "income_stability": "stable",
        "citizenship": "indian",
        "oci_pio_status": False,
    },
    "financial": {
        "monthly_income_inr": 150000,
        "monthly_expenses_inr": 60000,
        "bank_accounts": [{"bank_name": "SBI", "account_type": "NRO", "balance_inr": 200000}],
    },
    "residency": {
        "country_of_stay": "denmark",
        "tax_residency_country": "denmark",
        "days_in_india_current_fy": 0,
        "days_in_india_last_4_fy": 0,
        "indian_residential_status": "non_resident",
        "has_indian_bank_accounts": True,
        "account_types_held": ["NRO"],
        "has_pan": True,
        "has_kyc": True,
    },
    "investment": {
        "risk_tolerance": "moderate",
        "investment_horizon_years": 10,
        "liquidity_need": "medium",
        "primary_goal": "wealth_creation",
        "monthly_investable_inr": 90000,
        "lump_sum_investable_inr": 500000,
        "preferred_currency": "INR",
    },
}


@pytest.fixture
def client():
    return TestClient(create_app())


def test_recommend_returns_200_for_valid_payload(client):
    response = client.post("/api/recommend", json=VALID_PAYLOAD)

    assert response.status_code == 200
    data = response.json()
    assert data["risk_profile"] == "moderate"
    assert "allocation" in data
    assert "instruments" in data
    assert "tax_summary" in data
    assert "compliance" in data
    assert "projections" in data
    assert data["disclaimers"]


def test_recommend_returns_422_for_missing_required_fields(client):
    response = client.post("/api/recommend", json={"session_id": "incomplete"})
    assert response.status_code == 422


def test_list_instruments_returns_static_catalog(client):
    response = client.get("/api/instruments")
    assert response.status_code == 200
    data = response.json()
    assert "instruments" in data
    assert len(data["instruments"]) > 0


def test_recommendations_router_health_route_is_shadowed_by_app_health_route(client):
    # app/api/recommendations.py defines GET /health (mounted at /api/health),
    # but app/routes/health.py registers the same path first in app/main.py,
    # so Starlette's first-match routing always serves the app-level health
    # check here and the recommendations one is unreachable dead code.
    response = client.get("/api/health")
    assert response.status_code == 200
    assert "service" not in response.json()
