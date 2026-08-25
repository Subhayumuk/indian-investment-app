from types import SimpleNamespace

import pytest

from app.modules.confidence_scorer import ConfidenceScorer

scorer = ConfidenceScorer()

FULL_PROFILE = SimpleNamespace(
    age=35,
    annual_income_inr=1_800_000,
    monthly_expenses_inr=60_000,
    existing_investments_inr=500_000,
    risk_tolerance="moderate",
    investment_goal="wealth_creation",
    investment_horizon_years=10,
    tax_residency_country="Denmark",
    nri_status=True,
    has_nre_account=True,
    has_nro_account=True,
    has_pan=True,
)


def test_full_profile_scores_high():
    result = scorer.score_profile(FULL_PROFILE)
    assert result["score"] == 1.0
    assert result["level"] == "high"
    assert result["missing_fields"] == []


def test_missing_fields_are_reported_and_lower_the_score():
    sparse = SimpleNamespace(age=35, risk_tolerance="moderate")
    result = scorer.score_profile(sparse)
    assert result["score"] < 1.0
    assert "tax_residency_country" in result["missing_fields"]


def test_score_below_half_is_low_confidence():
    empty = SimpleNamespace()
    result = scorer.score_profile(empty)
    assert result["score"] == 0.0
    assert result["level"] == "low"


def test_score_instrument_penalizes_equity_mf_for_usa_resident():
    profile = SimpleNamespace(tax_residency_country="USA", risk_tolerance="moderate")
    score = scorer.score_instrument("equity_mf", profile)
    assert score == pytest.approx(0.5)


def test_score_instrument_ppf_is_always_low():
    profile = SimpleNamespace(tax_residency_country="Denmark", risk_tolerance="moderate")
    score = scorer.score_instrument("ppf", profile)
    assert score == pytest.approx(0.3)


def test_score_instrument_conservative_penalizes_equity():
    profile = SimpleNamespace(tax_residency_country="Denmark", risk_tolerance="conservative")
    score = scorer.score_instrument("equity_mf", profile)
    assert score == pytest.approx(0.55)


def test_score_instrument_aggressive_penalizes_fixed_deposits():
    profile = SimpleNamespace(tax_residency_country="Denmark", risk_tolerance="aggressive")
    score = scorer.score_instrument("nre_fd", profile)
    assert score == pytest.approx(0.6)


def test_score_instrument_stacks_country_and_risk_penalties():
    profile = SimpleNamespace(tax_residency_country="USA", risk_tolerance="conservative")
    score = scorer.score_instrument("equity_mf", profile)
    assert score == pytest.approx(0.35)
