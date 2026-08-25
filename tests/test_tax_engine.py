import pytest

from app.modules.tax_engine import TaxEngine

engine = TaxEngine()


@pytest.mark.parametrize("instrument_type,months,expected_rate", [
    ("equity_mf", 6, 0.20),
    ("equity_mf", 13, 0.125),
    ("stocks", 24, 0.125),
    ("debt_mf", 12, None),
    ("debt_mf", 30, 0.125),
    ("fd", 100, None),
    ("sgb", 1, 0.0),
    ("nps", 1, 0.0),
    ("ppf", 1, 0.0),
])
def test_get_india_tax_rate_by_instrument_and_holding_period(instrument_type, months, expected_rate):
    rule = engine.get_india_tax(instrument_type, holding_period_months=months)
    assert rule["rate"] == expected_rate


def test_get_india_tax_unknown_instrument_defaults_to_slab():
    rule = engine.get_india_tax("crypto")
    assert rule["rate"] is None
    assert rule["slab"] is True


def test_get_dtaa_benefit_known_country_dividend():
    result = engine.get_dtaa_benefit("Denmark", "dividend")
    assert result["applicable"] is True
    assert result["rate"] == 0.15


def test_get_dtaa_benefit_unknown_country():
    result = engine.get_dtaa_benefit("Brazil", "dividend")
    assert result["applicable"] is False
    assert result["rate"] is None


def test_get_dtaa_benefit_capital_gains_residence_country_for_uae():
    result = engine.get_dtaa_benefit("uae", "capital_gains")
    assert result["rate"] == 0.0


def test_get_dtaa_benefit_capital_gains_source_country_for_denmark():
    result = engine.get_dtaa_benefit("denmark", "capital_gains")
    assert result["rate"] is None
    assert "source country" in result["benefit"].lower()


def test_calculate_effective_tax_uses_residence_only_when_dtaa_zero_rated():
    result = engine.calculate_effective_tax("uae", "equity_mf", india_tax_rate=0.125, foreign_tax_rate=0.0)
    assert result["effective_rate"] == 0.0
    assert result["dtaa_used"] is True


def test_calculate_effective_tax_uses_higher_of_india_and_foreign():
    result = engine.calculate_effective_tax("denmark", "equity_mf", india_tax_rate=0.125, foreign_tax_rate=0.42)
    assert result["effective_rate"] == 0.42


def test_calculate_effective_tax_single_jurisdiction_when_one_rate_missing():
    result = engine.calculate_effective_tax("brazil", "equity_mf", india_tax_rate=0.125, foreign_tax_rate=0.0)
    assert result["effective_rate"] == 0.125
    assert result["dtaa_used"] is False


def test_get_foreign_tax_summary_known_country():
    summary = engine.get_foreign_tax_summary("Singapore")
    assert summary["currency"] == "SGD"
    assert summary["capital_gains_rate"] == 0.0


def test_get_foreign_tax_summary_unknown_country_falls_back():
    summary = engine.get_foreign_tax_summary("Brazil")
    assert summary["currency"] == "USD"
    assert summary["capital_gains_rate"] == 0.20
