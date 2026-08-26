"""
mfapi.in Client

Fetches historical NAV data for a mutual fund scheme from the free,
keyless community API at mfapi.in (which republishes AMFI data with full
NAV history, keyed by the same AMFI scheme code). Used only after
amfi_nav_client.py has resolved an ISIN to a scheme code — mfapi.in itself
has no ISIN-indexed lookup, only name-search or an already-known scheme code.
"""
import logging
from datetime import datetime
from typing import List, Optional, TypedDict

import httpx

logger = logging.getLogger(__name__)

MFAPI_URL_TEMPLATE = "https://api.mfapi.in/mf/{scheme_code}"
REQUEST_TIMEOUT_SECONDS = 8.0


class NavPoint(TypedDict):
    date: datetime
    nav: float


def _parse_nav_history(payload: dict) -> List[NavPoint]:
    points: List[NavPoint] = []
    for row in payload.get("data", []):
        try:
            date = datetime.strptime(row["date"], "%d-%m-%Y")
            nav = float(row["nav"])
        except (KeyError, ValueError, TypeError):
            continue
        points.append({"date": date, "nav": nav})
    return points


def compute_trailing_return(nav_history: List[NavPoint], years: int) -> Optional[float]:
    """Trailing CAGR (%) from the latest NAV point back to the nearest point
    at least `years` earlier. Returns None rather than extrapolating if the
    history doesn't actually go back that far — never guess a return."""
    if not nav_history:
        return None
    sorted_points = sorted(nav_history, key=lambda p: p["date"])
    latest = sorted_points[-1]
    target_days = years * 365
    candidates = [p for p in sorted_points if (latest["date"] - p["date"]).days >= target_days]
    if not candidates:
        return None
    start = candidates[-1]  # closest point that's still at least `years` back
    actual_years = (latest["date"] - start["date"]).days / 365.25
    if actual_years <= 0 or start["nav"] <= 0:
        return None
    cagr_pct = ((latest["nav"] / start["nav"]) ** (1 / actual_years) - 1) * 100
    return round(cagr_pct, 2)


class MfApiClient:
    """`http_client` is injectable, same convention as AmfiNavClient."""

    def __init__(self, http_client: Optional[httpx.AsyncClient] = None):
        self._http_client = http_client

    async def get_nav_history(self, scheme_code: str) -> List[NavPoint]:
        if not scheme_code:
            return []
        url = MFAPI_URL_TEMPLATE.format(scheme_code=scheme_code)
        try:
            if self._http_client is not None:
                response = await self._http_client.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
            else:
                async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
                    response = await client.get(url)
            if response.status_code != 200:
                raise ValueError(f"mfapi.in returned status {response.status_code}")
            return _parse_nav_history(response.json())
        except Exception as e:
            logger.warning(f"mfapi.in NAV history fetch failed for scheme {scheme_code}: {e}")
            return []
