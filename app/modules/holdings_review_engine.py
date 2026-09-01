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
from app.modules.benchmark_engine import BenchmarkEngine
from app.modules.market_data_client import MarketDataClient
from app.modules.recommendation_engine import ASSET_CLASS_RETURN, RecommendationEngine

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


def _analyze_fund(fund: dict, total_corpus_inr: float, market_data: FundMarketData) -> FundHoldingAnalysis:
    fund_name = fund.get("fund_name", "")
    isin = fund.get("isin", "")
    value = float(fund.get("current_value_inr", 0) or 0)
    share = (value / total_corpus_inr) if total_corpus_inr > 0 else 0.0
    warnings: List[str] = []

    if share > OVERCONCENTRATION_THRESHOLD:
        verdict = HoldingVerdictLabel.OVERCONCENTRATED
        warnings.append(
            f"This fund is {round(share * 100, 1)}% of your total corpus - concentrating "
            "this much in one fund adds risk regardless of how it's performed."
        )
    elif market_data.match_confidence == MatchConfidence.UNMATCHED:
        verdict = HoldingVerdictLabel.DATA_UNAVAILABLE
        warnings.append("Couldn't match this fund to AMFI's records by ISIN - no return data available to compare.")
    elif market_data.trailing_return_3yr_pct is None:
        verdict = HoldingVerdictLabel.DATA_UNAVAILABLE
        warnings.append("Matched the fund, but not enough price history was available to compute a 3-year return.")
    else:
        asset_class = _infer_asset_class(market_data.matched_scheme_name or fund_name)
        benchmark_pct = ASSET_CLASS_RETURN[asset_class] * 100
        diff = market_data.trailing_return_3yr_pct - benchmark_pct
        verdict = _verdict_for_return_gap(diff)
        warnings.append(
            f"Category assumed as '{asset_class}' from the fund name - CAS uploads don't "
            "include a real category field, so this is a best-effort guess, not a fact."
        )

    return FundHoldingAnalysis(
        fund_name=fund_name,
        isin=isin,
        current_value_inr=value,
        market_data=market_data,
        verdict=verdict,
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
            fund_analyses.append(_analyze_fund(fund, total_corpus, market_data))

        disclaimers = [
            "This is educational, comparative information, not personalized investment advice.",
            "Verdicts are computed from public AMFI/mfapi.in data against a simplified flat "
            "asset-class benchmark, not true category-peer rankings.",
            "Fund categories are guessed from the fund name, since CAS uploads don't include one.",
            "Nothing you upload or enter here is stored.",
        ]

        return HoldingsReviewResponse(
            llm_available=False,
            peer_benchmark=benchmark,
            fund_analyses=fund_analyses,
            unmatched_fund_count=unmatched_count,
            disclaimers=disclaimers,
        )
