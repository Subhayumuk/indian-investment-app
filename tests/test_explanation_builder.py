from types import SimpleNamespace

import pytest

from app.modules.explanation_builder import ExplanationBuilder

builder = ExplanationBuilder()


def make_flat(**overrides):
    base = dict(
        age=35,
        nri_status=True,
        tax_residency_country="Denmark",
        risk_tolerance="moderate",
        investment_goal="wealth_creation",
        investment_horizon_years=10,
        has_nre_account=True,
        has_nro_account=True,
        has_pan=True,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def test_build_profile_summary_includes_key_facts():
    summary = builder.build_profile_summary(make_flat())
    assert "35-year-old" in summary
    assert "NRI" in summary
    assert "Denmark" in summary
    assert "moderate risk appetite" in summary
    assert "10 years" in summary


def test_build_profile_summary_falls_back_when_empty():
    empty = SimpleNamespace(
        age=None, nri_status=False, tax_residency_country=None,
        risk_tolerance=None, investment_goal=None, investment_horizon_years=None,
    )
    assert builder.build_profile_summary(empty) == "NRI investor"


def test_key_insights_mention_dtaa_when_applicable():
    tax_summary = SimpleNamespace(dtaa_applicable=True)
    insights = builder.build_key_insights(make_flat(), allocation=None, tax_summary=tax_summary)
    assert any("dtaa" in i.lower() for i in insights)


def test_key_insights_flags_zero_cgt_countries():
    profile = make_flat(tax_residency_country="UAE")
    insights = builder.build_key_insights(profile, allocation=None, tax_summary=None)
    assert any("zero capital gains tax" in i.lower() for i in insights)


def test_key_insights_flags_insurance_cover_below_ten_times_income():
    profile = make_flat(annual_income_inr=1_200_000, insurance_sum_assured_inr=500_000)
    insights = builder.build_key_insights(profile, allocation=None, tax_summary=None)
    assert any("insurance" in i.lower() for i in insights)


def test_key_insights_does_not_flag_adequate_insurance_cover():
    profile = make_flat(annual_income_inr=1_200_000, insurance_sum_assured_inr=15_000_000)
    insights = builder.build_key_insights(profile, allocation=None, tax_summary=None)
    assert not any("insurance" in i.lower() for i in insights)


def test_key_insights_skips_insurance_check_when_no_cover_recorded():
    # Absence of any insurance data shouldn't be treated as "underinsured" here —
    # that case is handled by build_action_steps instead (get a policy at all).
    profile = make_flat(annual_income_inr=1_200_000, insurance_sum_assured_inr=0)
    insights = builder.build_key_insights(profile, allocation=None, tax_summary=None)
    assert not any("insurance" in i.lower() for i in insights)


def test_key_insights_capped_at_five():
    profile = make_flat(risk_tolerance="aggressive", tax_residency_country="uae", investment_horizon_years=15, age=25)
    tax_summary = SimpleNamespace(dtaa_applicable=True)
    insights = builder.build_key_insights(profile, allocation=None, tax_summary=tax_summary)
    assert len(insights) <= 5


def test_action_steps_flag_missing_pan_and_bank_account():
    profile = make_flat(has_pan=False, has_nre_account=False, has_nro_account=False)
    steps = builder.build_action_steps(profile, instruments=[])
    joined = " ".join(steps)
    assert "PAN card" in joined
    assert "NRE/NRO" in joined


def test_action_steps_flag_missing_life_insurance():
    profile = make_flat(insurance_sum_assured_inr=0)
    steps = builder.build_action_steps(profile, instruments=[])
    assert any("term life insurance" in s.lower() for s in steps)


def test_action_steps_do_not_flag_when_insurance_present():
    profile = make_flat(insurance_sum_assured_inr=1_000_000)
    steps = builder.build_action_steps(profile, instruments=[])
    assert not any("term life insurance" in s.lower() for s in steps)


def test_action_steps_flag_fbar_for_usa():
    profile = make_flat(tax_residency_country="USA")
    steps = builder.build_action_steps(profile, instruments=[])
    assert any("FBAR" in s for s in steps)


@pytest.mark.parametrize("country,expected_substring", [
    ("denmark", "danish"),
    ("usa", "pfic"),
    ("uk", "cgt"),
    ("singapore", "no capital gains tax"),
    ("uae", "zero personal income tax"),
])
def test_tax_saving_tip_is_country_specific(country, expected_substring):
    tip = builder.build_tax_saving_tip(make_flat(tax_residency_country=country))
    assert expected_substring in tip.lower()


def test_tax_saving_tip_falls_back_for_unknown_country():
    tip = builder.build_tax_saving_tip(make_flat(tax_residency_country="Brazil"))
    assert "long-term capital gains rates" in tip.lower()
