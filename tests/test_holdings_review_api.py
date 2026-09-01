from fastapi.testclient import TestClient

import app.api.holdings_review as holdings_review_module
from app.main import create_app
from app.models.holdings_review import FundMarketData, MatchConfidence

VALID_PAYLOAD = {
    "session_id": "test-001",
    "personal": {
        "age": 35, "marital_status": "single", "dependents": 0,
        "employment_status": "salaried", "income_stability": "stable",
        "citizenship": "indian", "oci_pio_status": False,
    },
    "financial": {
        "monthly_income_inr": 150000,
        "monthly_expenses_inr": 60000,
        "mutual_funds": [{"fund_name": "Parag Parikh Flexi Cap", "current_value_inr": 300000, "isin": "INF879O01027"}],
        "gold_value_inr": 700000,
    },
    "residency": {
        "country_of_stay": "denmark", "tax_residency_country": "denmark",
        "days_in_india_current_fy": 0, "days_in_india_last_4_fy": 0,
        "indian_residential_status": "non_resident", "has_indian_bank_accounts": True,
        "account_types_held": ["NRO"], "has_pan": True, "has_kyc": True,
    },
    "investment": {
        "risk_tolerance": "moderate", "investment_horizon_years": 10,
        "liquidity_need": "medium", "primary_goal": "wealth_creation",
        "monthly_investable_inr": 90000, "lump_sum_investable_inr": 500000,
        "preferred_currency": "INR",
    },
}


class FakeMarketDataClient:
    async def lookup_fund(self, isin: str, fund_name: str = "") -> FundMarketData:
        return FundMarketData(
            isin=isin, matched_scheme_name=fund_name, trailing_return_3yr_pct=13.0,
            match_confidence=MatchConfidence.ISIN_MATCH, data_source="amfi+mfapi",
        )


def test_holdings_review_returns_200_with_verdicts_and_no_llm(monkeypatch):
    # Swaps the router's module-level engine for one backed by a fake
    # market-data client, so this test never makes a real network call to
    # AMFI/mfapi.in - same no-network-in-tests discipline as
    # test_market_data_client.py.
    from app.modules.holdings_review_engine import HoldingsReviewEngine
    monkeypatch.setattr(
        holdings_review_module, "engine",
        HoldingsReviewEngine(market_data_client=FakeMarketDataClient()),
    )

    client = TestClient(create_app())
    response = client.post("/api/holdings-review", json=VALID_PAYLOAD)

    assert response.status_code == 200
    data = response.json()
    assert data["llm_available"] is False
    assert len(data["fund_analyses"]) == 1
    assert data["fund_analyses"][0]["verdict"] in {
        "aligned", "worth_reviewing", "underperforming_category", "overconcentrated", "data_unavailable",
    }
    assert data["peer_benchmark"]["cohort_description"]
    assert data["disclaimers"]


def test_holdings_review_with_no_mutual_funds_returns_empty_list(monkeypatch):
    from app.modules.holdings_review_engine import HoldingsReviewEngine
    monkeypatch.setattr(
        holdings_review_module, "engine",
        HoldingsReviewEngine(market_data_client=FakeMarketDataClient()),
    )

    payload = {**VALID_PAYLOAD, "financial": {**VALID_PAYLOAD["financial"], "mutual_funds": []}}
    client = TestClient(create_app())
    response = client.post("/api/holdings-review", json=payload)

    assert response.status_code == 200
    assert response.json()["fund_analyses"] == []


def test_recommend_endpoint_still_works_unchanged_alongside_holdings_review():
    # Regression guard: adding this router must not disturb /api/recommend.
    client = TestClient(create_app())
    response = client.post("/api/recommend", json=VALID_PAYLOAD)
    assert response.status_code == 200
