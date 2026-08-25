import pytest

from app.modules import instrument_catalog


@pytest.mark.parametrize("risk", ["conservative", "moderate", "aggressive"])
def test_get_named_instruments_returns_entries_for_each_risk_tier(risk):
    entries = instrument_catalog.get_named_instruments(risk, total_corpus_inr=1_000_000)
    assert entries
    for entry in entries:
        assert "name" in entry
        assert "suggested_amount_inr" in entry


def test_get_named_instruments_unknown_risk_falls_back_to_moderate():
    unknown = instrument_catalog.get_named_instruments("yolo", total_corpus_inr=1_000_000)
    moderate = instrument_catalog.get_named_instruments("moderate", total_corpus_inr=1_000_000)
    assert [e["name"] for e in unknown] == [e["name"] for e in moderate]


def test_suggested_amount_scales_with_corpus():
    entries = instrument_catalog.get_named_instruments("moderate", total_corpus_inr=1_000_000)
    entry = entries[0]
    expected = round(1_000_000 * entry["suggested_allocation_pct"] / 100, 2)
    assert entry["suggested_amount_inr"] == expected


def test_suggested_amount_is_zero_for_zero_corpus():
    entries = instrument_catalog.get_named_instruments("moderate", total_corpus_inr=0)
    assert all(e["suggested_amount_inr"] == 0 for e in entries)
