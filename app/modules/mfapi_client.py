"""
mfapi.in Client

Fetches historical NAV data for a mutual fund scheme from the free,
keyless community API at mfapi.in (which republishes AMFI data with full
NAV history, keyed by the same AMFI scheme code). Used only after
amfi_nav_client.py has resolved an ISIN to a scheme code — mfapi.in itself
has no ISIN-indexed lookup, only name-search or an already-known scheme code.
"""
import asyncio
import logging
import time
from datetime import datetime
from typing import List, Optional, TypedDict

import httpx

logger = logging.getLogger(__name__)

MFAPI_URL_TEMPLATE = "https://api.mfapi.in/mf/{scheme_code}"
REQUEST_TIMEOUT_SECONDS = 8.0

# mfapi.in publishes no documented rate limit, but it's a free, unofficial
# community service (see this module's docstring) - Holdings Review already
# looks up several funds concurrently via asyncio.gather, and Phase E's
# shortlist batch job (scripts/refresh_amfi_category_index.py) will make
# many more calls in a row than any single Holdings Review request does.
# A considerate ~3 requests/second cap costs a real user under a second of
# extra wait for a typical portfolio, and turns a batch job's request burst
# into a steady trickle instead - added after both use cases existed,
# rather than before either needed it.
DEFAULT_MIN_REQUEST_INTERVAL_SECONDS = 0.34


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
    """`http_client` is injectable, same convention as AmfiNavClient.
    `min_request_interval_seconds` is injectable too, mainly so tests don't
    have to wait out the real default."""

    def __init__(
        self,
        http_client: Optional[httpx.AsyncClient] = None,
        min_request_interval_seconds: float = DEFAULT_MIN_REQUEST_INTERVAL_SECONDS,
    ):
        self._http_client = http_client
        self._min_request_interval_seconds = min_request_interval_seconds
        self._throttle_lock = asyncio.Lock()
        self._last_request_at: Optional[float] = None

    async def _throttle(self) -> None:
        """Serializes requests through this client instance to at most one
        every `min_request_interval_seconds` - a global cap on outbound
        request *starts*, not per-call backoff, so concurrent callers (e.g.
        holdings_review_engine.py's asyncio.gather) end up queued rather
        than all firing at once."""
        async with self._throttle_lock:
            now = time.monotonic()
            if self._last_request_at is not None:
                wait = self._min_request_interval_seconds - (now - self._last_request_at)
                if wait > 0:
                    await asyncio.sleep(wait)
            self._last_request_at = time.monotonic()

    async def get_nav_history(self, scheme_code: str) -> List[NavPoint]:
        if not scheme_code:
            return []
        await self._throttle()
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
