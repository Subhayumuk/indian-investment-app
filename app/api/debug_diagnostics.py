"""
TEMPORARY diagnostic endpoint.

Purpose: check whether Render's servers can reach amfiindia.com — the
user's home network (Denmark) cannot (confirmed via two independent HTTP
stacks), but that doesn't tell us whether the deployed backend's network
path is equally blocked. Delete this file and its one-line registration in
app/main.py once that question is answered either way.
"""
import logging

import httpx
from fastapi import APIRouter

from app.modules.market_data_client import MarketDataClient

logger = logging.getLogger(__name__)
router = APIRouter()

# Real ISIN from the user's actual CAS statement (Tata ELSS Fund) - used only
# to prove the full AMFI -> mfapi.in lookup chain works against live data
# from Render's own network path, not just against synthetic test fixtures.
SAMPLE_ISIN = "INF277K01I60"


@router.get("/debug/amfi-check")
async def amfi_check():
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            response = await client.get("https://www.amfiindia.com/spages/NAVAll.txt")
        return {
            "reachable": True,
            "status_code": response.status_code,
            "final_url": str(response.url),
            "redirect_chain": [str(r.url) for r in response.history],
            "content_length": len(response.text),
            "content_preview": response.text[:300],
        }
    except Exception as e:
        logger.warning(f"AMFI diagnostic check failed: {e}")
        return {
            "reachable": False,
            "error_type": type(e).__name__,
            "error": str(e),
        }


@router.get("/debug/fund-lookup-check")
async def fund_lookup_check():
    try:
        client = MarketDataClient()
        result = await client.lookup_fund(SAMPLE_ISIN, "Tata ELSS Fund")
        return result.model_dump()
    except Exception as e:
        logger.warning(f"Fund lookup diagnostic check failed: {e}")
        return {"error_type": type(e).__name__, "error": str(e)}
