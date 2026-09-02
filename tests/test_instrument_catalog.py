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


SUPPORTED_COUNTRIES = ["denmark", "usa", "uk", "germany", "australia", "singapore", "canada", "uae"]


@pytest.mark.parametrize("country", SUPPORTED_COUNTRIES)
def test_residence_tax_note_is_non_empty_for_every_supported_country(country):
    note = instrument_catalog.residence_tax_note(country, "equity_mf")
    assert note


def test_residence_tax_note_is_case_insensitive_on_country():
    assert instrument_catalog.residence_tax_note("USA", "equity_mf") == instrument_catalog.residence_tax_note("usa", "equity_mf")


def test_residence_tax_note_differs_by_country_not_just_denmark():
    # Regression guard for the 2026-09-01 bug: this used to always return
    # (and the frontend always labelled) a Danish-specific note regardless
    # of the user's actual country.
    denmark = instrument_catalog.residence_tax_note("denmark", "equity_mf")
    usa = instrument_catalog.residence_tax_note("usa", "equity_mf")
    uk = instrument_catalog.residence_tax_note("uk", "equity_mf")
    assert len({denmark, usa, uk}) == 3
    assert "lagerbeskatning" not in usa.lower()
    assert "lagerbeskatning" not in uk.lower()


def test_residence_tax_note_flags_pfic_for_us_funds_but_not_fds():
    fund_note = instrument_catalog.residence_tax_note("usa", "equity_mf")
    fd_note = instrument_catalog.residence_tax_note("usa", "nre_fd")
    assert "PFIC" in fund_note
    assert "PFIC" not in fd_note


def test_residence_tax_note_unknown_country_falls_back_to_generic_pointer():
    note = instrument_catalog.residence_tax_note("atlantis", "equity_mf")
    assert "tax adviser" in note.lower()


def test_residence_tax_note_denmark_distinguishes_funds_from_interest_bearing_instruments():
    # fd/bonds and sgb are genuinely different income types (interest, not
    # fund gains) and keep their own notes. Fund types (equity/debt/hybrid)
    # deliberately share ONE note as of 2026-09-02 - researched correction:
    # Danish lagerbeskatning applies annually to a foreign, SKAT-unlisted
    # fund regardless of its own equity/debt composition, so equity being
    # "exempt" (the pre-fix assumption) was wrong. See instrument_catalog.py
    # for sources.
    fd = instrument_catalog.residence_tax_note("denmark", "nre_fd")
    sgb = instrument_catalog.residence_tax_note("denmark", "sgb")
    equity = instrument_catalog.residence_tax_note("denmark", "equity_mf")
    debt = instrument_catalog.residence_tax_note("denmark", "debt_mf")
    hybrid = instrument_catalog.residence_tax_note("denmark", "hybrid_mf")

    assert len({fd, sgb, equity}) == 3
    assert equity == debt == hybrid
    assert "lagerbeskatning" in equity.lower()
    assert "rubrik 38" in equity.lower()
    assert "positive list" in equity.lower()
