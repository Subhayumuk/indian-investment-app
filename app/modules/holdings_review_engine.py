"""
Holdings Review Engine

For each mutual fund a user reports (from CAS upload or manual entry),
looks up real market data (app/modules/market_data_client.py) and derives
a rule-based verdict against a computed peer benchmark
(app/modules/benchmark_engine.py). No LLM involved yet - Phase C adds a
narrative layer on top of these already-decided verdicts; it never gets
to change them. See HOW_IT_WORKS.md section 9 for the "AI narrates,
never decides" discipline this follows.
"""
import asyncio
import logging
from types import SimpleNamespace
from typing import List, Optional

from app.models.holdings_review import (
    FundHoldingAnalysis,
    FundMarketData,
    HoldingsReviewResponse,
    HoldingVerdictLabel,
    MatchConfidence,
)
from app.models.user_profile import UserProfile
from app.modules import instrument_catalog
from app.modules.benchmark_engine import BenchmarkEngine
from app.modules.market_data_client import MarketDataClient
from app.modules.recommendation_engine import ASSET_CLASS_RETURN, RecommendationEngine
from app.modules.sebi_category_mapping import classify_sebi_category
from app.utils.kb_loader import load_india_kb

logger = logging.getLogger(__name__)

OVERCONCENTRATION_THRESHOLD = 0.25
ALIGNED_TOLERANCE_PP = 2.0
UNDERPERFORMANCE_TOLERANCE_PP = 5.0

# CAS extraction gives us a fund name, not a real category - a mutual
# fund's AMFI scheme name conventionally hints at its category even when
# it doesn't say "equity" outright (e.g. "Flexi Cap", "Bluechip"). This is
# a best-effort keyword guess, not a fact, and is disclosed as such in
# every fund's warnings below.
_DEBT_KEYWORDS = [
    "liquid", "overnight", "money market", "ultra short", "low duration",
    "short duration", "medium duration", "corporate bond", "credit risk",
    "banking", "psu", "gilt", "dynamic bond", "debt fund",
]


def _infer_asset_class(name: str) -> str:
    n = (name or "").lower()
    if "gold" in n:
        return "gold"
    if "hybrid" in n or "balanced advantage" in n:
        return "hybrid"
    if any(keyword in n for keyword in _DEBT_KEYWORDS):
        return "debt"
    return "equity"


def _verdict_for_return_gap(diff_pp: float) -> HoldingVerdictLabel:
    if diff_pp >= -ALIGNED_TOLERANCE_PP:
        return HoldingVerdictLabel.ALIGNED
    if diff_pp >= -UNDERPERFORMANCE_TOLERANCE_PP:
        return HoldingVerdictLabel.WORTH_REVIEWING
    return HoldingVerdictLabel.UNDERPERFORMING_CATEGORY


def _switch_considerations(asset_class: str, capital_gains_kb: dict) -> List[str]:
    """Concrete facts to weigh before deciding whether to switch a fund -
    deliberately facts, not a recommendation (see the 2026-09-02 decision
    to stay comparative rather than move to imperative sell/keep
    language). Only states specific numbers for equity, since that's the
    one capital_gains section actually wired to nri_taxation.yaml and
    confirmed current by the 2026-08-27 audit - debt/gold/hybrid stay
    generic rather than repeating a number the audit already flagged as
    unresolved."""
    considerations = [
        "Check this fund's exit load - many funds charge a fee (often around 1%) for "
        "redeeming within the first year.",
    ]
    if asset_class == "equity":
        cg = capital_gains_kb["equity_mutual_funds"]
        considerations.append(
            f"Selling equity fund units held under {cg['stcg_holding_months']} months is taxed "
            f"at {cg['stcg_rate']}% (STCG); {cg['stcg_holding_months']} months or more, at "
            f"{cg['ltcg_rate']}% above a combined ₹{cg['ltcg_exemption_limit_inr']:,.0f}/year "
            "exemption (LTCG). This doesn't account for your actual purchase price or date, "
            "which this app doesn't have."
        )
    else:
        considerations.append(
            f"{asset_class.title()} fund capital gains rules have changed more than once since "
            "2023 and haven't been independently verified in this app yet - confirm the current "
            "tax treatment before deciding whether to switch."
        )
    return considerations


def _analyze_fund(
    fund: dict, total_corpus_inr: float, market_data: FundMarketData, country: str, capital_gains_kb: dict
) -> FundHoldingAnalysis:
    fund_name = fund.get("fund_name", "")
    isin = fund.get("isin", "")
    value = float(fund.get("current_value_inr", 0) or 0)
    share = (value / total_corpus_inr) if total_corpus_inr > 0 else 0.0
    warnings: List[str] = []

    # Computed regardless of verdict path - what holding or switching a
    # fund means tax-wise doesn't depend on whether we could also compute
    # a return-based verdict for it. Every Holdings Review entry is a
    # mutual fund scheme by definition (that's what AMFI's NAVAll.txt
    # lists), so instrument_catalog's fund-oriented notes apply uniformly;
    # only the equity/debt vs. hybrid distinction (which a few countries'
    # notes, e.g. Denmark's, actually differentiate) comes from the same
    # category (real when AMFI's own data resolved it, guessed otherwise)
    # used for the benchmark comparison below.
    mapped_asset_class = classify_sebi_category(market_data.category)
    category_is_confirmed = mapped_asset_class is not None
    asset_class = mapped_asset_class or _infer_asset_class(market_data.matched_scheme_name or fund_name)
    note_instrument_type = "hybrid_mf" if asset_class == "hybrid" else "equity_mf"
    residence_tax_note = instrument_catalog.residence_tax_note(country, note_instrument_type)
    switch_considerations = _switch_considerations(asset_class, capital_gains_kb)

    benchmark_return_pct: Optional[float] = None
    return_gap_pct: Optional[float] = None
    if market_data.trailing_return_3yr_pct is not None:
        benchmark_return_pct = ASSET_CLASS_RETURN[asset_class] * 100
        return_gap_pct = round(market_data.trailing_return_3yr_pct - benchmark_return_pct, 2)

    if share > OVERCONCENTRATION_THRESHOLD:
        verdict = HoldingVerdictLabel.OVERCONCENTRATED
        warnings.append(
            f"This fund is {round(share * 100, 1)}% of your total corpus - concentrating "
            "this much in one fund adds risk regardless of how it's performed."
        )
    elif market_data.match_confidence == MatchConfidence.UNMATCHED:
        verdict = HoldingVerdictLabel.DATA_UNAVAILABLE
        warnings.append("Couldn't match this fund to AMFI's records by ISIN - no return data available to compare.")
    elif return_gap_pct is None:
        verdict = HoldingVerdictLabel.DATA_UNAVAILABLE
        warnings.append("Matched the fund, but not enough price history was available to compute a 3-year return.")
    else:
        verdict = _verdict_for_return_gap(return_gap_pct)
        if category_is_confirmed:
            warnings.append(
                f"Category matched from AMFI's own scheme data ('{market_data.category}'), mapped to this "
                f"app's '{asset_class}' benchmark bucket for comparison."
            )
        else:
            warnings.append(
                f"Category assumed as '{asset_class}' from the fund name - AMFI's category for this "
                "scheme wasn't available or wasn't recognised, so this is a best-effort guess, not a fact."
            )

    return FundHoldingAnalysis(
        fund_name=fund_name,
        isin=isin,
        current_value_inr=value,
        market_data=market_data,
        verdict=verdict,
        benchmark_return_pct=benchmark_return_pct,
        return_gap_pct=return_gap_pct,
        residence_tax_note=residence_tax_note,
        switch_considerations=switch_considerations,
        warnings=warnings,
    )


class HoldingsReviewEngine:
    def __init__(
        self,
        market_data_client: Optional[MarketDataClient] = None,
        benchmark_engine: Optional[BenchmarkEngine] = None,
        recommendation_engine: Optional[RecommendationEngine] = None,
    ):
        self._recommendation_engine = recommendation_engine or RecommendationEngine()
        self._market_data_client = market_data_client or MarketDataClient()
        self._benchmark_engine = benchmark_engine or BenchmarkEngine(self._recommendation_engine)
        self._capital_gains_kb = load_india_kb("nri_taxation.yaml")["capital_gains"]

    async def _lookup_with_fallback(self, isin: str, fund_name: str) -> FundMarketData:
        try:
            return await self._market_data_client.lookup_fund(isin, fund_name)
        except Exception as e:  # noqa: BLE001 - a lookup failure degrades this one fund, not the whole review
            logger.warning(f"Market data lookup failed for '{fund_name}' ({isin}): {e}")
            return FundMarketData(isin=isin, match_confidence=MatchConfidence.UNMATCHED, data_source="unavailable")

    async def review(self, profile: UserProfile) -> HoldingsReviewResponse:
        # Reuses _flatten_profile (leading-underscore, "private") rather
        # than re-deriving the same nested-to-flat adaptation a second
        # time - same reasoning as BenchmarkEngine.
        flat: SimpleNamespace = self._recommendation_engine._flatten_profile(profile)
        benchmark = self._benchmark_engine.build_benchmark(flat)

        total_corpus = flat.total_corpus_inr or 0.0
        funds = flat.mutual_funds

        # Concurrent, not sequential: with N funds this is bounded by the
        # slowest single lookup instead of the sum of all of them.
        # AmfiNavClient's own lock (see amfi_nav_client.py) keeps this from
        # triggering N simultaneous full-file refetches on a cold cache.
        market_data_results = await asyncio.gather(
            *(self._lookup_with_fallback(f.get("isin", ""), f.get("fund_name", "")) for f in funds)
        )

        fund_analyses: List[FundHoldingAnalysis] = []
        unmatched_count = 0
        for fund, market_data in zip(funds, market_data_results):
            if market_data.match_confidence == MatchConfidence.UNMATCHED:
                unmatched_count += 1
            fund_analyses.append(
                _analyze_fund(fund, total_corpus, market_data, flat.tax_residency_country, self._capital_gains_kb)
            )

        disclaimers = [
            "This is educational, comparative information, not personalized investment advice.",
            "Verdicts are computed from public AMFI/mfapi.in data against a simplified flat "
            "asset-class benchmark, not true category-peer rankings.",
            "Fund categories come from AMFI's own scheme data when recognised; otherwise guessed "
            "from the fund name, since CAS uploads don't include a category field.",
            "Switch considerations describe general tax/cost rules to weigh, not your actual gain, "
            "loss, or tax owed - this app doesn't know your purchase price or purchase date.",
            "Nothing you upload or enter here is stored.",
        ]

        return HoldingsReviewResponse(
            llm_available=False,
            peer_benchmark=benchmark,
            fund_analyses=fund_analyses,
            unmatched_fund_count=unmatched_count,
            disclaimers=disclaimers,
        )
