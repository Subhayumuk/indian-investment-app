import pytest

from app.models.user_profile import UserProfile
from app.modules.recommendation_engine import RecommendationEngine

engine = RecommendationEngine()


def make_profile(**overrides) -> UserProfile:
    payload = {
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
            "mutual_funds": [{"fund_name": "Parag Parikh Flexi Cap", "current_value_inr": 300000}],
            "gold_value_inr": 50000,
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
    for key, value in overrides.items():
        section, field = key.split(".", 1)
        payload[section][field] = value
    return UserProfile(**payload)


def test_generate_returns_a_fully_populated_response():
    result = engine.generate(make_profile())

    assert result.investable_amount_inr == pytest.approx(550_000.0)
    total_pct = (
        result.allocation.equity_pct + result.allocation.debt_pct + result.allocation.real_estate_pct
        + result.allocation.gold_pct + result.allocation.cash_pct + result.allocation.hybrid_pct
    )
    assert total_pct == pytest.approx(100.0, abs=0.1)
    assert result.portfolio_health.total_corpus_inr == pytest.approx(550_000.0)
    assert result.instruments
    assert all(instrument.nri_eligible for instrument in result.instruments)
    assert result.tax_summary.foreign_country == "denmark"
    assert result.compliance.fema_compliant is True
    assert result.compliance.fatca_applicable is False
    assert 0.0 <= result.confidence_overall <= 1.0
    assert len(result.projections) == 1
    assert result.projections[0].years == 10


def test_generate_recognizes_held_account_types_for_fema_compliance():
    # Regression test: _flatten_profile used to compare str(AccountType.NRO)
    # (which renders as "AccountType.NRO") against "NRO", so has_nro_account
    # was always False and fema_compliant could never be True.
    result = engine.generate(make_profile())
    assert result.compliance.fema_compliant is True


def test_generate_marks_nri_in_profile_summary_for_non_resident_status():
    result = engine.generate(make_profile(**{"residency.indian_residential_status": "non_resident"}))
    assert "NRI" in result.profile_summary


def test_generate_omits_nri_from_summary_for_resident_status():
    result = engine.generate(make_profile(**{"residency.indian_residential_status": "resident"}))
    assert "NRI" not in result.profile_summary


def test_generate_uses_the_actual_goal_value_not_its_enum_repr():
    # Regression test: _flatten_profile used to pass str(primary_goal)
    # ("InvestmentGoal.RETIREMENT") instead of primary_goal.value
    # ("retirement"), which both broke goal-based allocation adjustments
    # and leaked the raw enum repr into the profile summary text.
    result = engine.generate(make_profile(**{"investment.primary_goal": "retirement"}))
    assert "InvestmentGoal" not in result.profile_summary
    assert "retirement" in result.profile_summary


def test_generate_retirement_goal_allocates_less_equity_than_wealth_creation():
    wealth_creation = engine.generate(make_profile(**{"investment.primary_goal": "wealth_creation"}))
    retirement = engine.generate(make_profile(**{"investment.primary_goal": "retirement"}))
    assert retirement.allocation.equity_pct < wealth_creation.allocation.equity_pct


def test_generate_zero_assets_gives_poor_portfolio_health():
    profile = make_profile(**{
        "financial.bank_accounts": [],
        "financial.mutual_funds": [],
        "financial.gold_value_inr": 0.0,
    })
    result = engine.generate(profile)

    assert result.investable_amount_inr == 0.0
    assert result.portfolio_health.overall_score == 0
    assert result.portfolio_health.score_label == "Poor"
    assert any("No assets recorded" in flag for flag in result.portfolio_health.health_flags)


def test_generate_usa_resident_triggers_fatca():
    profile = make_profile(**{"residency.tax_residency_country": "usa"})
    result = engine.generate(profile)
    assert result.compliance.fatca_applicable is True
    assert "fatca" in result.compliance.form_required


def test_generate_gives_usa_resident_a_pfic_note_not_a_danish_one():
    # Regression guard for the 2026-09-01 bug: every instrument used to
    # carry a Denmark-specific "danish_tax_note" regardless of the user's
    # actual country.
    profile = make_profile(**{"residency.tax_residency_country": "usa"})
    result = engine.generate(profile)
    fund_instruments = [i for i in result.instruments if i.instrument_type in ("equity_mf", "debt_mf", "etf")]
    assert fund_instruments
    for instrument in fund_instruments:
        assert "PFIC" in instrument.residence_tax_note
        assert "lagerbeskatning" not in instrument.residence_tax_note.lower()


def test_generate_denmark_resident_still_gets_the_original_lagerbeskatning_note():
    profile = make_profile(**{"residency.tax_residency_country": "denmark"})
    result = engine.generate(profile)
    equity_instruments = [i for i in result.instruments if i.instrument_type == "equity_mf"]
    assert equity_instruments
    assert all("lagerbeskatning" in i.residence_tax_note.lower() for i in equity_instruments)


def test_generate_projection_scenarios_are_ordered():
    result = engine.generate(make_profile())
    projection = result.projections[0]
    assert (
        projection.projected_value_conservative
        <= projection.projected_value_moderate
        <= projection.projected_value_optimistic
    )
