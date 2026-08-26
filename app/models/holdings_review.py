from enum import Enum
from typing import Optional

from pydantic import BaseModel


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
