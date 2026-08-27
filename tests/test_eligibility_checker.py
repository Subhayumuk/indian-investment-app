from types import SimpleNamespace

import pytest

from app.modules.eligibility_checker import EligibilityChecker
from app.utils.kb_loader import load_india_kb

checker = EligibilityChecker()


def make_profile(tax_residency_country="Denmark"):
    return SimpleNamespace(tax_residency_country=tax_residency_country)


def test_eligible_instrument_has_no_warnings_for_unrestricted_country():
    result = checker.check_instrument_eligibility("equity_mf", make_profile("Denmark"))
    assert result["eligible"] is True
    assert result["warnings"] == []


def test_equity_mf_flagged_for_usa_resident():
    result = checker.check_instrument_eligibility("equity_mf", make_profile("USA"))
    assert result["eligible"] is True
    assert result["warnings"]
    assert "FATCA" in result["warnings"][0]


def test_equity_mf_flagged_for_canada_resident():
    result = checker.check_instrument_eligibility("equity_mf", make_profile("Canada"))
    assert result["warnings"]


def test_ppf_not_eligible_for_nri():
    result = checker.check_instrument_eligibility("ppf", make_profile("Denmark"))
    assert result["eligible"] is False
    assert "PPF" in result["warnings"][0]


def test_unknown_instrument_defaults_to_eligible():
    result = checker.check_instrument_eligibility("some_new_thing", make_profile("Denmark"))
    assert result["eligible"] is True


def test_check_all_eligibility_covers_full_catalog():
    results = checker.check_all_eligibility(make_profile("Denmark"))
    assert set(results.keys()) == set(checker.nri_eligible_instruments.keys())


def test_compliance_requirements_base_fields_always_present():
    reqs = checker.get_compliance_requirements(make_profile("Denmark"))
    for key in ["pan_card", "kyc", "nre_nro_account", "fema_declaration"]:
        assert reqs[key]["required"] is True


def test_compliance_requirements_usa_adds_fatca_and_fbar():
    reqs = checker.get_compliance_requirements(make_profile("USA"))
    assert "fatca" in reqs
    assert "fbar" in reqs


def test_compliance_requirements_canada_adds_t1135():
    reqs = checker.get_compliance_requirements(make_profile("Canada"))
    assert "t1135" in reqs


@pytest.mark.parametrize("country", ["uk", "germany", "denmark", "australia"])
def test_compliance_requirements_adds_foreign_income_reporting(country):
    reqs = checker.get_compliance_requirements(make_profile(country))
    assert "foreign_income_reporting" in reqs


def test_fema_summary_uses_country_specific_currency_and_rate():
    summary = checker.get_fema_summary(make_profile("Denmark"))
    assert summary["currency"] == "DKK"
    assert "USD 250,000" in summary["annual_outward_remittance_limit"]


def test_fema_summary_unknown_country_falls_back_to_usd():
    summary = checker.get_fema_summary(make_profile("Atlantis"))
    assert summary["currency"] == "USD"


def test_sgb_is_not_eligible_for_new_nri_subscriptions():
    # Real bug found 2026-08-27: this was hardcoded eligible=True, directly
    # contradicting product_rules.yaml (NRIs can't subscribe to new SGB
    # issuances, only hold ones bought before becoming NRI) - and reachable
    # by every real user via check_all_eligibility. Now sourced from the
    # YAML, so it can't silently drift from it again.
    result = checker.check_instrument_eligibility("sgb", make_profile("Denmark"))
    assert result["eligible"] is False


def test_etf_is_restricted_for_usa_and_canada():
    # Previously the hardcoded country_restrictions list only named
    # equity_mf/debt_mf, missing "etf" despite product_rules.yaml already
    # flagging it (us_canada_restriction: true). Now derived from that flag.
    assert "etf" in checker.country_restrictions["usa"]
    assert "etf" in checker.country_restrictions["canada"]


def test_nro_fd_account_type_is_read_from_the_yaml_not_hardcoded():
    kb_account_types = load_india_kb("product_rules.yaml")["products"]["nro_fixed_deposit"]["account_types_allowed"]
    assert checker.nri_eligible_instruments["nro_fd"]["account_type"] == kb_account_types


def test_nro_repatriation_limit_is_read_from_the_yaml_not_hardcoded():
    kb_limit = load_india_kb("fema_rules.yaml")["repatriation_rules"]["nro_account"]["annual_limit_usd"]
    assert checker.fema_limits["nro_repatriation_usd"] == kb_limit
