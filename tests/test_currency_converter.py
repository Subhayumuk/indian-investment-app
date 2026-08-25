import pytest

from app.utils.currency_converter import CurrencyConverter

converter = CurrencyConverter()


def test_get_currency_for_known_country():
    assert converter.get_currency_for_country("Denmark") == "DKK"


def test_get_currency_for_unknown_country_falls_back_to_usd():
    assert converter.get_currency_for_country("Atlantis") == "USD"


def test_to_inr_uses_known_rate():
    assert converter.to_inr(100, "DKK") == pytest.approx(1210.0)


def test_to_inr_unknown_currency_falls_back_to_usd_rate():
    assert converter.to_inr(100, "XYZ") == pytest.approx(8350.0)


def test_from_inr_and_to_inr_round_trip():
    original = 10_000.0
    converted = converter.from_inr(original, "USD")
    back = converter.to_inr(converted, "USD")
    assert back == pytest.approx(original, rel=1e-3)


def test_convert_same_currency_is_identity():
    assert converter.convert(500, "usd", "USD") == 500


def test_convert_between_two_foreign_currencies():
    result = converter.convert(100, "USD", "DKK")
    assert result == pytest.approx(100 * 83.5 / 12.1, rel=1e-3)


@pytest.mark.parametrize("amount,expected_suffix", [
    (50_00_000, "L"),
    (2_00_00_000, "Cr"),
    (5_000, ""),
])
def test_format_amount_uses_lakh_and_crore_suffixes(amount, expected_suffix):
    formatted = converter.format_amount(amount, "INR")
    if expected_suffix:
        assert formatted.endswith(expected_suffix)
    else:
        assert "L" not in formatted and "Cr" not in formatted
