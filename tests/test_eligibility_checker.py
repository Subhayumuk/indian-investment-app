from types import SimpleNamespace

import pytest

from app.modules.eligibility_checker import EligibilityChecker

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
