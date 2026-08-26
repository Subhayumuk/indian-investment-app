"""
AMFI NAV Client

Fetches and parses AMFI's free, keyless daily NAV file (NAVAll.txt) to
resolve a mutual fund's ISIN to its AMFI scheme code, name, and latest NAV.
This is the only free source with ISIN as a native field: mfapi.in (used
for historical returns, see mfapi_client.py) has no ISIN-indexed lookup,
and fund names extracted from CAS PDFs are often truncated/inconsistent
(see app/api/cas_parser.py), so ISIN is the only reliable matching key.
"""
import logging
import time
from dataclasses import dataclass
from typing import Dict, Optional

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

NAV_ALL_URL = "https://www.amfiindia.com/spages/NAVAll.txt"
REQUEST_TIMEOUT_SECONDS = 15.0  # the file is ~9-12MB


@dataclass
class SchemeRecord:
    scheme_code: str
    scheme_name: str
    latest_nav: Optional[float]


def _parse_nav_all_text(text: str) -> Dict[str, SchemeRecord]:
    """Best-effort line-based parse of AMFI's semicolon-delimited NAVAll.txt.
    The file interleaves AMC-name and category-header lines (no semicolons)
    and blank-line separators among the actual data rows, so each line is
    validated independently (field count + numeric scheme code) rather than
    assumed to be data. Live columns (verified against the real file, not
    just documentation — AMFI has changed this layout over time): Scheme
    Code; ISIN Div Payout/ISIN Growth; ISIN Div Reinvestment; Scheme Name;
    Plan; Option; Net Asset Value; Date. A scheme can have two ISIN variants
    (growth / dividend-reinvestment) sharing the same scheme code/NAV — both
    are indexed to the same record.
    """
    index: Dict[str, SchemeRecord] = {}
    for line in text.splitlines():
        parts = line.strip().split(";")
        if len(parts) < 8:
            continue
        scheme_code = parts[0].strip()
        if not scheme_code.isdigit():
            continue
        isin_growth = parts[1].strip()
        isin_div_reinvestment = parts[2].strip()
        base_name = parts[3].strip()
        plan = parts[4].strip()
        option = parts[5].strip()
        scheme_name = " - ".join(p for p in (base_name, plan, option) if p)
        try:
            latest_nav = float(parts[6].strip())
        except ValueError:
            latest_nav = None
        record = SchemeRecord(scheme_code=scheme_code, scheme_name=scheme_name, latest_nav=latest_nav)
        for isin in (isin_growth, isin_div_reinvestment):
            if isin and isin.upper() != "N.A.":
                index[isin] = record
    return index


class AmfiNavClient:
    """`http_client` is injectable (any object exposing an async `.get(url,
    timeout=...)` returning something with `.status_code`/`.text`) so tests
    can supply a fake without a real network call."""

    def __init__(self, http_client: Optional[httpx.AsyncClient] = None):
        self._http_client = http_client
        self._cache: Dict[str, SchemeRecord] = {}
        self._cached_at: float = 0.0

    def _is_cache_fresh(self) -> bool:
        ttl = get_settings().AMFI_NAV_CACHE_TTL_SECONDS
        return bool(self._cache) and (time.monotonic() - self._cached_at) < ttl

    async def _fetch_and_parse(self) -> Dict[str, SchemeRecord]:
        try:
            if self._http_client is not None:
                response = await self._http_client.get(NAV_ALL_URL, timeout=REQUEST_TIMEOUT_SECONDS)
            else:
                # AMFI redirects www.amfiindia.com -> portal.amfiindia.com for
                # this file (confirmed against the live endpoint); httpx does
                # not follow redirects by default.
                async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS, follow_redirects=True) as client:
                    response = await client.get(NAV_ALL_URL)
            if response.status_code != 200:
                raise ValueError(f"AMFI NAVAll.txt returned status {response.status_code}")
            return _parse_nav_all_text(response.text)
        except Exception as e:
            logger.warning(f"AMFI NAV fetch failed: {e}")
            return {}

    async def lookup(self, isin: str) -> Optional[SchemeRecord]:
        if not isin:
            return None
        if not self._is_cache_fresh():
            fresh = await self._fetch_and_parse()
            if fresh:
                self._cache = fresh
                self._cached_at = time.monotonic()
            # If the fetch failed and nothing was ever cached, fall through
            # to the (empty) cache lookup below rather than raising.
        return self._cache.get(isin)
