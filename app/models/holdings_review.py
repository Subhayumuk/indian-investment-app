from enum import Enum
from typing import List, Optional

from pydantic import BaseModel

from app.models.recommendation import AssetBreakdown, RecommendedAllocation


class MatchConfidence(str, Enum):
    ISIN_MATCH = "isin_match"
    UNMATCHED = "unmatched"


class FundMarketData(BaseModel):
    isin: str = ""
    matched_scheme_name: str = ""
    amfi_scheme_code: str = ""
    latest_nav: Optional[float] = None
    trailing_return_1yr_pct: Optional[float] = None
    trailing_return_3yr_pct: Optional[float] = None
    trailing_return_5yr_pct: Optional[float] = None
    match_confidence: MatchConfidence
    data_source: str = ""  # "amfi+mfapi" | "amfi_only" | "unavailable"


class HoldingVerdictLabel(str, Enum):
    ALIGNED = "aligned"
    WORTH_REVIEWING = "worth_reviewing"
    UNDERPERFORMING_CATEGORY = "underperforming_category"
    OVERCONCENTRATED = "overconcentrated"
    DATA_UNAVAILABLE = "data_unavailable"


class FundHoldingAnalysis(BaseModel):
    fund_name: str
    isin: str = ""
    current_value_inr: float = 0.0
    market_data: FundMarketData
    verdict: HoldingVerdictLabel
    residence_tax_note: str = ""  # what keeping/switching this fund means in the user's country
    commentary: str = ""  # filled in by Phase C's LLM layer; empty until then
    warnings: List[str] = []


class PeerBenchmark(BaseModel):
    cohort_description: str
    recommended_allocation: RecommendedAllocation
    your_allocation: AssetBreakdown
    narrative: str = ""  # filled in by Phase C's LLM layer; empty until then


class HoldingsReviewResponse(BaseModel):
    llm_available: bool = False
    peer_benchmark: PeerBenchmark
    fund_analyses: List[FundHoldingAnalysis] = []
    unmatched_fund_count: int = 0
    overall_commentary: str = ""  # filled in by Phase C's LLM layer; empty until then
    disclaimers: List[str] = []
