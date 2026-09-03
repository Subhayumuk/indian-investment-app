"""
Market Data Client

Thin facade combining amfi_nav_client.py (ISIN -> scheme code/name/NAV) and
mfapi_client.py (scheme code -> historical NAV -> trailing returns) into a
single per-fund lookup. Both sub-clients are constructor-injectable so
tests can supply fakes without any real network call.
"""
import logging
from typing import Optional

from app.models.holdings_review import FundMarketData, MatchConfidence
from app.modules.amfi_nav_client import AmfiNavClient
from app.modules.mfapi_client import MfApiClient, compute_trailing_return

logger = logging.getLogger(__name__)


class MarketDataClient:
    def __init__(
        self,
        amfi_client: Optional[AmfiNavClient] = None,
        mfapi_client: Optional[MfApiClient] = None,
    ):
        self.amfi_client = amfi_client or AmfiNavClient()
        self.mfapi_client = mfapi_client or MfApiClient()

    async def lookup_fund(self, isin: str, fund_name: str = "") -> FundMarketData:
        scheme = await self.amfi_client.lookup(isin) if isin else None
        if scheme is None:
            return FundMarketData(
                isin=isin,
                match_confidence=MatchConfidence.UNMATCHED,
                data_source="unavailable",
            )

        nav_history = await self.mfapi_client.get_nav_history(scheme.scheme_code)
        return FundMarketData(
            isin=isin,
            matched_scheme_name=scheme.scheme_name,
            amfi_scheme_code=scheme.scheme_code,
            category=scheme.category or "",
            latest_nav=scheme.latest_nav,
            trailing_return_1yr_pct=compute_trailing_return(nav_history, 1),
            trailing_return_3yr_pct=compute_trailing_return(nav_history, 3),
            trailing_return_5yr_pct=compute_trailing_return(nav_history, 5),
            match_confidence=MatchConfidence.ISIN_MATCH,
            data_source="amfi+mfapi" if nav_history else "amfi_only",
        )
