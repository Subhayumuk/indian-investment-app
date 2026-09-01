from app.models.user_profile import UserProfile
from app.modules.benchmark_engine import BenchmarkEngine
from app.modules.recommendation_engine import RecommendationEngine


def make_profile(**overrides) -> UserProfile:
    payload = {
        "session_id": "test-001",
        "personal": {
            "age": 35, "marital_status": "single", "dependents": 0,
            "employment_status": "salaried", "income_stability": "stable",
            "citizenship": "indian", "oci_pio_status": False,
        },
        "financial": {
            "monthly_income_inr": 150000,
            "monthly_expenses_inr": 60000,
            "bank_accounts": [{"bank_name": "SBI", "account_type": "NRO", "balance_inr": 200000}],
            "mutual_funds": [{"fund_name": "Parag Parikh Flexi Cap", "current_value_inr": 300000, "isin": "INF879O01027"}],
            "gold_value_inr": 50000,
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
    for key, value in overrides.items():
        section, field = key.split(".", 1)
        payload[section][field] = value
    return UserProfile(**payload)


recommendation_engine = RecommendationEngine()
benchmark_engine = BenchmarkEngine(recommendation_engine)


def test_cohort_description_mentions_risk_country_and_horizon():
    flat = recommendation_engine._flatten_profile(make_profile())
    benchmark = benchmark_engine.build_benchmark(flat)

    assert "Moderate" in benchmark.cohort_description
    assert "Denmark" in benchmark.cohort_description
    assert "10-year" in benchmark.cohort_description


def test_short_and_long_horizons_get_different_labels():
    short = recommendation_engine._flatten_profile(make_profile(**{"investment.investment_horizon_years": 2}))
    long = recommendation_engine._flatten_profile(make_profile(**{"investment.investment_horizon_years": 15}))

    assert "short-term" in benchmark_engine.build_benchmark(short).cohort_description
    assert "long-term" in benchmark_engine.build_benchmark(long).cohort_description


def test_benchmark_reuses_the_same_numbers_as_the_main_recommendation_flow():
    profile = make_profile()
    flat = recommendation_engine._flatten_profile(profile)

    benchmark = benchmark_engine.build_benchmark(flat)
    health = recommendation_engine._build_portfolio_health(flat)

    assert benchmark.recommended_allocation == health.recommended_allocation
    assert benchmark.your_allocation == health.asset_breakdown
