"""Cached loader for app/knowledge_base/fund_category_shortlists.json -
Phase E2's committed, per-AMFI-category shortlist of real named funds (with
real mfapi.in trailing returns), regenerated monthly by
scripts/refresh_fund_category_shortlists.py via
.github/workflows/fund-category-refresh.yml.

Same "read a committed data file at process start, no request-time network
call" pattern as amfi_category_loader.py (E1's own loader) and
app/utils/kb_loader.py before it.

Doesn't exist until the first refresh workflow run commits it, so
load_fund_category_shortlists() returns {} rather than raising when the
file is missing - instrument_catalog.py falls back to its own hardcoded
placeholder fund entries in that case, the same graceful-degradation
discipline as the rest of this app's external-data integrations.
"""
import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict

SHORTLIST_PATH = Path(__file__).resolve().parent.parent / "knowledge_base" / "fund_category_shortlists.json"


@lru_cache(maxsize=1)
def load_fund_category_shortlists() -> Dict[str, Any]:
    """Returns {"as_of_date": ..., "methodology_note": ..., "categories":
    {<AMFI category string>: [{"name", "isin", "amc",
    "trailing_return_3yr_pct", "trailing_return_5yr_pct"}, ...]}}, or {} if
    the shortlist hasn't been generated yet."""
    if not SHORTLIST_PATH.exists():
        return {}
    with SHORTLIST_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)
