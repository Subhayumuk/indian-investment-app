import asyncio

import pytest

from app.models.holdings_review import FundMarketData, HoldingVerdictLabel, MatchConfidence
from app.models.user_profile import UserProfile
from app.modules.holdings_review_engine import HoldingsReviewEngine


class FakeMarketDataClient:
    """Returns a preconfigured FundMarketData per ISIN, or an UNMATCHED
    result for any ISIN not in the map - no real network call, matching
    the fake-client convention already used in test_market_data_client.py."""

    def __init__(self, by_isin: dict):
        self._by_isin = by_isin

    async def lookup_fund(self, isin: str, fund_name: str = "") -> FundMarketData:
        if isin in self._by_isin:
            return self._by_isin[isin]
        return FundMarketData(isin=isin, match_confidence=MatchConfidence.UNMATCHED, data_source="unavailable")


def make_profile(mutual_funds, gold_value_inr=0, country="denmark") -> UserProfile:
    payload = {
        "session_id": "test-001",
        "personal": {
            "age": 35, "marital_status": "single", "dependents": 0,
            "employment_status": "salaried", "income_stability": "stable",
            "citizenship": "indian", "oci_pio_status": False,
        },
        "financial": {
            "monthly_income_inr": 150000,
            "monthly_expenses_inr": 60000,
            "mutual_funds": mutual_funds,
            "gold_value_inr": gold_value_inr,
        },
        "residency": {
            "country_of_stay": country, "tax_residency_country": country,
            "days_in_india_current_fy": 0, "days_in_india_last_4_fy": 0,
            "indian_residential_status": "non_resident", "has_indian_bank_accounts": True,
            "account_types_held": ["NRO"], "has_pan": True, "has_kyc": True,
        },
        "investment": {
            "risk_tolerance": "moderate", "investment_horizon_years": 10,
            "liquidity_need": "medium", "primary_goal": "wealth_creation",
            "monthly_investable_inr": 90000, "lump_sum_investable_inr": 500000,
            "preferred_currency": "INR",
        },
    }
    return UserProfile(**payload)


def test_fund_matching_or_beating_benchmark_is_aligned():
    fund = {"fund_name": "Aligned Equity Fund", "current_value_inr": 100000, "isin": "INF001"}
    market_data = {"INF001": FundMarketData(
        isin="INF001", matched_scheme_name="Aligned Equity Fund",
        trailing_return_3yr_pct=12.5, match_confidence=MatchConfidence.ISIN_MATCH, data_source="amfi+mfapi",
    )}
    engine = HoldingsReviewEngine(market_data_client=FakeMarketDataClient(market_data))
    profile = make_profile([fund], gold_value_inr=900000)  # keeps this fund's share under 25%

    result = asyncio.run(engine.review(profile))

    assert result.fund_analyses[0].verdict == HoldingVerdictLabel.ALIGNED


def test_fund_mildly_below_benchmark_is_worth_reviewing():
    fund = {"fund_name": "Mild Equity Fund", "current_value_inr": 100000, "isin": "INF002"}
    market_data = {"INF002": FundMarketData(
        isin="INF002", matched_scheme_name="Mild Equity Fund",
        trailing_return_3yr_pct=8.5,  # 3.5pp below the 12% equity benchmark
        match_confidence=MatchConfidence.ISIN_MATCH, data_source="amfi+mfapi",
    )}
    engine = HoldingsReviewEngine(market_data_client=FakeMarketDataClient(market_data))
    profile = make_profile([fund], gold_value_inr=900000)

    result = asyncio.run(engine.review(profile))

    assert result.fund_analyses[0].verdict == HoldingVerdictLabel.WORTH_REVIEWING


def test_fund_well_below_benchmark_is_underperforming():
    fund = {"fund_name": "Lagging Equity Fund", "current_value_inr": 100000, "isin": "INF003"}
    market_data = {"INF003": FundMarketData(
        isin="INF003", matched_scheme_name="Lagging Equity Fund",
        trailing_return_3yr_pct=3.0,  # 9pp below the 12% equity benchmark
        match_confidence=MatchConfidence.ISIN_MATCH, data_source="amfi+mfapi",
    )}
    engine = HoldingsReviewEngine(market_data_client=FakeMarketDataClient(market_data))
    profile = make_profile([fund], gold_value_inr=900000)

    result = asyncio.run(engine.review(profile))

    assert result.fund_analyses[0].verdict == HoldingVerdictLabel.UNDERPERFORMING_CATEGORY


def test_large_share_of_corpus_is_overconcentrated_regardless_of_return():
    fund = {"fund_name": "Big Fund", "current_value_inr": 800000, "isin": "INF004"}
    market_data = {"INF004": FundMarketData(
        isin="INF004", matched_scheme_name="Big Fund",
        trailing_return_3yr_pct=20.0,  # beats benchmark handily, but overconcentration still wins
        match_confidence=MatchConfidence.ISIN_MATCH, data_source="amfi+mfapi",
    )}
    engine = HoldingsReviewEngine(market_data_client=FakeMarketDataClient(market_data))
    profile = make_profile([fund], gold_value_inr=200000)  # fund is 80% of a 1,000,000 corpus

    result = asyncio.run(engine.review(profile))

    assert result.fund_analyses[0].verdict == HoldingVerdictLabel.OVERCONCENTRATED


def test_unmatched_fund_is_data_unavailable_and_counted():
    fund = {"fund_name": "Unknown Fund", "current_value_inr": 100000, "isin": "INF_UNKNOWN"}
    engine = HoldingsReviewEngine(market_data_client=FakeMarketDataClient({}))
    profile = make_profile([fund], gold_value_inr=900000)

    result = asyncio.run(engine.review(profile))

    assert result.fund_analyses[0].verdict == HoldingVerdictLabel.DATA_UNAVAILABLE
    assert result.unmatched_fund_count == 1


def test_matched_fund_without_enough_history_is_data_unavailable():
    fund = {"fund_name": "New Fund", "current_value_inr": 100000, "isin": "INF005"}
    market_data = {"INF005": FundMarketData(
        isin="INF005", matched_scheme_name="New Fund", trailing_return_3yr_pct=None,
        match_confidence=MatchConfidence.ISIN_MATCH, data_source="amfi_only",
    )}
    engine = HoldingsReviewEngine(market_data_client=FakeMarketDataClient(market_data))
    profile = make_profile([fund], gold_value_inr=900000)

    result = asyncio.run(engine.review(profile))

    assert result.fund_analyses[0].verdict == HoldingVerdictLabel.DATA_UNAVAILABLE
    assert result.unmatched_fund_count == 0  # matched, just missing history - different from UNMATCHED


def test_debt_fund_name_is_compared_against_the_debt_benchmark_not_equity():
    # 7.5% is above the 7% debt benchmark (aligned) but would be a heavy
    # underperformer against the 12% equity benchmark - proves the verdict
    # actually depends on the inferred category, not always "equity".
    fund = {"fund_name": "Corporate Bond Fund", "current_value_inr": 100000, "isin": "INF006"}
    market_data = {"INF006": FundMarketData(
        isin="INF006", matched_scheme_name="Corporate Bond Fund",
        trailing_return_3yr_pct=7.5, match_confidence=MatchConfidence.ISIN_MATCH, data_source="amfi+mfapi",
    )}
    engine = HoldingsReviewEngine(market_data_client=FakeMarketDataClient(market_data))
    profile = make_profile([fund], gold_value_inr=900000)

    result = asyncio.run(engine.review(profile))

    assert result.fund_analyses[0].verdict == HoldingVerdictLabel.ALIGNED


def test_review_includes_peer_benchmark_and_disclaimers():
    fund = {"fund_name": "Some Fund", "current_value_inr": 100000, "isin": "INF007"}
    engine = HoldingsReviewEngine(market_data_client=FakeMarketDataClient({}))
    profile = make_profile([fund], gold_value_inr=900000)

    result = asyncio.run(engine.review(profile))

    assert result.peer_benchmark.cohort_description
    assert result.disclaimers
    assert result.llm_available is False


def test_multiple_funds_are_matched_to_the_correct_analysis_in_order():
    # Lookups run concurrently (asyncio.gather) - this proves each result
    # still lands on the right fund rather than getting shuffled.
    funds = [
        {"fund_name": "Fund A", "current_value_inr": 50000, "isin": "INF_A"},
        {"fund_name": "Fund B", "current_value_inr": 50000, "isin": "INF_B"},
        {"fund_name": "Fund C", "current_value_inr": 50000, "isin": "INF_C"},
    ]
    market_data = {
        "INF_A": FundMarketData(isin="INF_A", matched_scheme_name="Fund A", trailing_return_3yr_pct=12.0, match_confidence=MatchConfidence.ISIN_MATCH, data_source="amfi+mfapi"),
        "INF_B": FundMarketData(isin="INF_B", matched_scheme_name="Fund B", trailing_return_3yr_pct=1.0, match_confidence=MatchConfidence.ISIN_MATCH, data_source="amfi+mfapi"),
        # INF_C intentionally missing -> unmatched
    }
    engine = HoldingsReviewEngine(market_data_client=FakeMarketDataClient(market_data))
    profile = make_profile(funds, gold_value_inr=850000)

    result = asyncio.run(engine.review(profile))

    assert [fa.fund_name for fa in result.fund_analyses] == ["Fund A", "Fund B", "Fund C"]
    assert result.fund_analyses[0].verdict == HoldingVerdictLabel.ALIGNED
    assert result.fund_analyses[1].verdict == HoldingVerdictLabel.UNDERPERFORMING_CATEGORY
    assert result.fund_analyses[2].verdict == HoldingVerdictLabel.DATA_UNAVAILABLE
    assert result.unmatched_fund_count == 1


def test_fund_analysis_carries_a_country_specific_residence_tax_note():
    fund = {"fund_name": "Some Equity Fund", "current_value_inr": 100000, "isin": "INF008"}
    market_data = {"INF008": FundMarketData(
        isin="INF008", matched_scheme_name="Some Equity Fund", trailing_return_3yr_pct=12.0,
        match_confidence=MatchConfidence.ISIN_MATCH, data_source="amfi+mfapi",
    )}
    engine = HoldingsReviewEngine(market_data_client=FakeMarketDataClient(market_data))
    profile = make_profile([fund], gold_value_inr=900000, country="usa")

    result = asyncio.run(engine.review(profile))

    assert "PFIC" in result.fund_analyses[0].residence_tax_note


def test_residence_tax_note_is_present_even_when_verdict_is_data_unavailable():
    # Tax treatment of a fund doesn't depend on whether we could also
    # compute a return-based verdict for it.
    fund = {"fund_name": "Unknown Fund", "current_value_inr": 100000, "isin": "INF_UNKNOWN2"}
    engine = HoldingsReviewEngine(market_data_client=FakeMarketDataClient({}))
    profile = make_profile([fund], gold_value_inr=900000, country="uk")

    result = asyncio.run(engine.review(profile))

    assert result.fund_analyses[0].verdict == HoldingVerdictLabel.DATA_UNAVAILABLE
    assert result.fund_analyses[0].residence_tax_note
    assert "offshore fund" in result.fund_analyses[0].residence_tax_note.lower()


def test_residence_tax_note_is_present_even_when_overconcentrated():
    fund = {"fund_name": "Big Fund", "current_value_inr": 800000, "isin": "INF009"}
    market_data = {"INF009": FundMarketData(
        isin="INF009", matched_scheme_name="Big Fund", trailing_return_3yr_pct=20.0,
        match_confidence=MatchConfidence.ISIN_MATCH, data_source="amfi+mfapi",
    )}
    engine = HoldingsReviewEngine(market_data_client=FakeMarketDataClient(market_data))
    profile = make_profile([fund], gold_value_inr=200000, country="denmark")

    result = asyncio.run(engine.review(profile))

    assert result.fund_analyses[0].verdict == HoldingVerdictLabel.OVERCONCENTRATED
    assert "lagerbeskatning" in result.fund_analyses[0].residence_tax_note.lower()


def test_hybrid_fund_gets_the_same_denmark_fund_note_as_equity():
    # As of 2026-09-02, equity/debt/hybrid Indian funds share one Denmark
    # note (see instrument_catalog.py) - the fund's own equity/debt mix
    # doesn't change whether lagerbeskatning applies for an unlisted
    # foreign fund, so hybrid no longer gets a "different" note.
    hybrid_fund = {"fund_name": "HDFC Balanced Advantage Fund", "current_value_inr": 100000, "isin": "INF010"}
    equity_fund = {"fund_name": "Some Equity Fund", "current_value_inr": 100000, "isin": "INF011"}
    market_data = {
        "INF010": FundMarketData(isin="INF010", matched_scheme_name="HDFC Balanced Advantage Fund", trailing_return_3yr_pct=9.0, match_confidence=MatchConfidence.ISIN_MATCH, data_source="amfi+mfapi"),
        "INF011": FundMarketData(isin="INF011", matched_scheme_name="Some Equity Fund", trailing_return_3yr_pct=9.0, match_confidence=MatchConfidence.ISIN_MATCH, data_source="amfi+mfapi"),
    }
    engine = HoldingsReviewEngine(market_data_client=FakeMarketDataClient(market_data))
    profile = make_profile([hybrid_fund, equity_fund], gold_value_inr=800000, country="denmark")

    result = asyncio.run(engine.review(profile))

    assert result.fund_analyses[0].residence_tax_note == result.fund_analyses[1].residence_tax_note
    assert "classification" in result.fund_analyses[0].residence_tax_note.lower()


def test_return_gap_and_benchmark_are_reported_alongside_the_verdict():
    fund = {"fund_name": "Some Equity Fund", "current_value_inr": 100000, "isin": "INF011"}
    market_data = {"INF011": FundMarketData(
        isin="INF011", matched_scheme_name="Some Equity Fund", trailing_return_3yr_pct=8.5,
        match_confidence=MatchConfidence.ISIN_MATCH, data_source="amfi+mfapi",
    )}
    engine = HoldingsReviewEngine(market_data_client=FakeMarketDataClient(market_data))
    profile = make_profile([fund], gold_value_inr=900000)

    result = asyncio.run(engine.review(profile))
    fa = result.fund_analyses[0]

    assert fa.benchmark_return_pct == 12.0  # equity benchmark from ASSET_CLASS_RETURN
    assert fa.return_gap_pct == pytest.approx(-3.5)


def test_return_gap_is_none_when_no_return_data_available():
    fund = {"fund_name": "Unknown Fund", "current_value_inr": 100000, "isin": "INF_UNKNOWN3"}
    engine = HoldingsReviewEngine(market_data_client=FakeMarketDataClient({}))
    profile = make_profile([fund], gold_value_inr=900000)

    result = asyncio.run(engine.review(profile))
    fa = result.fund_analyses[0]

    assert fa.return_gap_pct is None
    assert fa.benchmark_return_pct is None


def test_switch_considerations_quote_real_equity_capital_gains_rates():
    fund = {"fund_name": "Some Equity Fund", "current_value_inr": 100000, "isin": "INF012"}
    market_data = {"INF012": FundMarketData(
        isin="INF012", matched_scheme_name="Some Equity Fund", trailing_return_3yr_pct=12.0,
        match_confidence=MatchConfidence.ISIN_MATCH, data_source="amfi+mfapi",
    )}
    engine = HoldingsReviewEngine(market_data_client=FakeMarketDataClient(market_data))
    profile = make_profile([fund], gold_value_inr=900000)

    result = asyncio.run(engine.review(profile))
    considerations = " ".join(result.fund_analyses[0].switch_considerations)

    # These must match whatever nri_taxation.yaml actually says, not a
    # hardcoded copy - reads the real values it's asserting against.
    from app.utils.kb_loader import load_india_kb
    cg = load_india_kb("nri_taxation.yaml")["capital_gains"]["equity_mutual_funds"]
    assert f"{cg['stcg_rate']}%" in considerations
    assert f"{cg['ltcg_rate']}%" in considerations
    assert "exit load" in considerations.lower()


def test_switch_considerations_for_non_equity_avoid_stating_unverified_numbers():
    fund = {"fund_name": "Corporate Bond Fund", "current_value_inr": 100000, "isin": "INF013"}
    market_data = {"INF013": FundMarketData(
        isin="INF013", matched_scheme_name="Corporate Bond Fund", trailing_return_3yr_pct=7.0,
        match_confidence=MatchConfidence.ISIN_MATCH, data_source="amfi+mfapi",
    )}
    engine = HoldingsReviewEngine(market_data_client=FakeMarketDataClient(market_data))
    profile = make_profile([fund], gold_value_inr=900000)

    result = asyncio.run(engine.review(profile))
    considerations = " ".join(result.fund_analyses[0].switch_considerations)

    assert "STCG" not in considerations
    assert "LTCG" not in considerations
    assert "confirm" in considerations.lower()


def test_verdict_language_stays_comparative_not_imperative():
    # Regression guard for the 2026-09-02 decision: verdicts describe a
    # comparison, they never instruct an action.
    for label in HoldingVerdictLabel:
        value = label.value
        assert "sell" not in value
        assert "buy" not in value
        assert "switch" not in value


def test_real_amfi_category_is_preferred_over_name_guess():
    # Fund name alone would guess "equity" (no debt/gold/hybrid keyword),
    # but a real AMFI category of "Debt Scheme - Gilt Fund" should win -
    # proven by comparing against the debt benchmark (7%), not equity (12%).
    fund = {"fund_name": "Ambiguous Fund Name", "current_value_inr": 100000, "isin": "INF014"}
    market_data = {"INF014": FundMarketData(
        isin="INF014", matched_scheme_name="Ambiguous Fund Name", category="Debt Scheme - Gilt Fund",
        trailing_return_3yr_pct=7.5, match_confidence=MatchConfidence.ISIN_MATCH, data_source="amfi+mfapi",
    )}
    engine = HoldingsReviewEngine(market_data_client=FakeMarketDataClient(market_data))
    profile = make_profile([fund], gold_value_inr=900000)

    result = asyncio.run(engine.review(profile))
    fa = result.fund_analyses[0]

    assert fa.benchmark_return_pct == pytest.approx(7.0)  # debt benchmark, not the 12% equity default
    assert fa.verdict == HoldingVerdictLabel.ALIGNED
    assert any("AMFI's own scheme data" in w for w in fa.warnings)
    assert not any("best-effort guess" in w for w in fa.warnings)


def test_falls_back_to_name_guess_when_category_unrecognised():
    fund = {"fund_name": "Corporate Bond Fund", "current_value_inr": 100000, "isin": "INF015"}
    market_data = {"INF015": FundMarketData(
        isin="INF015", matched_scheme_name="Corporate Bond Fund", category="Some Brand New Category",
        trailing_return_3yr_pct=7.5, match_confidence=MatchConfidence.ISIN_MATCH, data_source="amfi+mfapi",
    )}
    engine = HoldingsReviewEngine(market_data_client=FakeMarketDataClient(market_data))
    profile = make_profile([fund], gold_value_inr=900000)

    result = asyncio.run(engine.review(profile))
    fa = result.fund_analyses[0]

    assert fa.benchmark_return_pct == pytest.approx(7.0)  # falls back to the "Corporate Bond Fund" name-keyword guess
    assert any("best-effort guess" in w for w in fa.warnings)


def test_review_with_no_mutual_funds_returns_empty_analysis_list():
    engine = HoldingsReviewEngine(market_data_client=FakeMarketDataClient({}))
    profile = make_profile([], gold_value_inr=100000)

    result = asyncio.run(engine.review(profile))

    assert result.fund_analyses == []
    assert result.unmatched_fund_count == 0
