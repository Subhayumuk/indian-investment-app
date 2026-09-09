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


# --- Phase E2: real-fund substitution from the generated shortlist ---

FAKE_SHORTLIST_DOCUMENT = {
    "as_of_date": "2026-09-09",
    "methodology_note": "test methodology note",
    "categories": {
        "Liquid Fund": [
            {"name": "Real Liquid Fund", "isin": "INF000L01AAA", "amc": "Real AMC",
             "trailing_return_3yr_pct": 6.3, "trailing_return_5yr_pct": 6.0},
        ],
        "Mid Cap Fund": [
            {"name": "Real Mid Cap Fund One", "isin": "INF000M01AAA", "amc": "AMC One",
             "trailing_return_3yr_pct": 22.1, "trailing_return_5yr_pct": 24.9},
            {"name": "Real Mid Cap Fund Two", "isin": "INF000M01BBB", "amc": "AMC Two",
             "trailing_return_3yr_pct": 19.4, "trailing_return_5yr_pct": None},
        ],
        # No usable "trailing_return_3yr_pct"-bearing entry for this
        # category on purpose, to exercise the "no substitution available"
        # path further below.
        "Corporate Bond Fund": [],
    },
}


def test_get_named_instruments_substitutes_placeholder_funds_with_real_shortlist_data(monkeypatch):
    monkeypatch.setattr(instrument_catalog, "load_fund_category_shortlists", lambda: FAKE_SHORTLIST_DOCUMENT)

    entries = instrument_catalog.get_named_instruments("conservative", total_corpus_inr=1_000_000)
    liquid_entry = next(e for e in entries if e["category"] == "Liquid Fund")

    assert liquid_entry["isin"] == "INF000L01AAA"
    assert "PLACEHOLDER" not in liquid_entry["isin"]
    assert liquid_entry["historical_return_3yr"] == "6.3%"
    assert liquid_entry["historical_return_5yr"] == "6.0%"
    assert "Real AMC" in liquid_entry["name"]


def test_get_named_instruments_falls_back_to_placeholder_when_no_shortlist_exists(monkeypatch):
    monkeypatch.setattr(instrument_catalog, "load_fund_category_shortlists", lambda: {})

    entries = instrument_catalog.get_named_instruments("conservative", total_corpus_inr=1_000_000)
    liquid_entry = next(e for e in entries if e["category"] == "Liquid Fund")

    assert "PLACEHOLDER" in liquid_entry["isin"]


def test_get_named_instruments_falls_back_when_category_has_no_usable_entries(monkeypatch):
    monkeypatch.setattr(instrument_catalog, "load_fund_category_shortlists", lambda: FAKE_SHORTLIST_DOCUMENT)

    entries = instrument_catalog.get_named_instruments("moderate", total_corpus_inr=1_000_000)
    bond_entry = next(e for e in entries if e["category"] == "Debt Mutual Fund")

    # "Corporate Bond Fund" is present in the fake shortlist but empty, and
    # none of _SLOT_CATEGORY_TO_AMFI_CATEGORIES's other candidates for
    # "Debt Mutual Fund" exist in the fake document either - should fall
    # back to the hardcoded placeholder rather than crash or substitute
    # nothing usable.
    assert "PLACEHOLDER" in bond_entry["isin"]


def test_get_named_instruments_never_reuses_the_same_isin_for_two_slots(monkeypatch):
    monkeypatch.setattr(instrument_catalog, "load_fund_category_shortlists", lambda: FAKE_SHORTLIST_DOCUMENT)

    entries = instrument_catalog.get_named_instruments("aggressive", total_corpus_inr=1_000_000)
    mid_cap_entries = [e for e in entries if e["category"] == "Equity Mutual Fund (Mid Cap)"]

    assert len(mid_cap_entries) == 2
    assert mid_cap_entries[0]["isin"] != mid_cap_entries[1]["isin"]
    assert {e["isin"] for e in mid_cap_entries} == {"INF000M01AAA", "INF000M01BBB"}


def test_get_named_instruments_never_touches_already_real_entries(monkeypatch):
    # Parag Parikh Flexi Cap Fund already has a real, hand-verified ISIN
    # (no "-PLACEHOLDER" suffix) - substitution must never overwrite it,
    # even though "Flexi Cap Fund" is one of the mapped AMFI categories for
    # its slot's "Equity Mutual Fund" label.
    fake_flexi_cap_document = {
        "categories": {
            "Flexi Cap Fund": [
                {"name": "Some Other Flexi Cap Fund", "isin": "INF999F01ZZZ", "amc": "Other AMC",
                 "trailing_return_3yr_pct": 30.0, "trailing_return_5yr_pct": 35.0},
            ],
        },
    }
    monkeypatch.setattr(instrument_catalog, "load_fund_category_shortlists", lambda: fake_flexi_cap_document)

    entries = instrument_catalog.get_named_instruments("moderate", total_corpus_inr=1_000_000)
    parag_parikh = next(e for e in entries if e["isin"] == "INF879O01019")

    assert parag_parikh["name"] == "Parag Parikh Flexi Cap Fund (NRI eligible)"
