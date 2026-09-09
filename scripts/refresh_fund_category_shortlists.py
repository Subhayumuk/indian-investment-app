"""Generates app/knowledge_base/fund_category_shortlists.json - Phase E2's
per-AMFI-category shortlist of real, named funds with real mfapi.in
trailing returns, built on top of E1's committed
app/knowledge_base/amfi_category_index.json (see
scripts/refresh_amfi_category_index.py, which this script assumes has
already run). Intended to run monthly, right after that script, from the
same .github/workflows/fund-category-refresh.yml job, which opens a PR
with the result rather than pushing directly - same reasoning as E1's own
script, just for a higher-stakes artifact (real named funds that
instrument_catalog.py shows as *new*-money suggestions, not just a
category label used internally by Holdings Review).

Design choices worth being explicit about (see the Phase E plan under
~/.claude/plans, "E2 - Generic named-fund category shortlists"):

- The shortlist is generic for every user - the same funds appear for
  everyone in a given category, never filtered by an individual's
  profile. Personalization stays where it already lives: AllocationEngine
  still decides *how much* goes to each asset class.
- Selection is capped, not ranked. Neither AMFI's NAVAll.txt nor
  mfapi.in exposes AUM or expense-ratio data - the two things a real
  screener would actually rank on - so there's no honest signal to sort
  by. Candidates are deduped to Direct Plan/Growth schemes (via E1's
  index), capped at MAX_PER_AMC_PER_CATEGORY per fund house so one AMC
  can't dominate a category, and otherwise ordered alphabetically -
  arbitrary but deterministic, and disclosed as such in the output's own
  methodology_note rather than only in this comment.
- A scheme is dropped (not included with a blank return) if mfapi.in's
  NAV history isn't long enough for a real 3-year trailing return -
  matching compute_trailing_return's own "never extrapolate" rule.

Usage:
    python -m scripts.refresh_fund_category_shortlists [--out PATH]
"""
from __future__ import annotations

import argparse
import asyncio
import datetime
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    # See refresh_amfi_category_index.py's identical guard: a bare
    # `python scripts/refresh_fund_category_shortlists.py` invocation only
    # puts scripts/ on sys.path, not the repo root.
    sys.path.insert(0, str(_REPO_ROOT))

from app.modules.amfi_category_loader import load_amfi_category_index  # noqa: E402
from app.modules.mfapi_client import MfApiClient, compute_trailing_return  # noqa: E402

DEFAULT_OUT_PATH = (
    Path(__file__).resolve().parent.parent / "app" / "knowledge_base" / "fund_category_shortlists.json"
)

MAX_PER_AMC_PER_CATEGORY = 1
MAX_FUNDS_PER_CATEGORY = 8

METHODOLOGY_NOTE = (
    f"Each category lists up to {MAX_FUNDS_PER_CATEGORY} real, AMFI-listed "
    f"Direct Plan/Growth schemes, capped at {MAX_PER_AMC_PER_CATEGORY} per "
    "fund house (AMC) so no single AMC dominates a category. This is a "
    "shortlist, not a ranking: neither AMFI nor mfapi.in (this app's two "
    "free data sources) exposes AUM or expense-ratio data, so funds are "
    "ordered alphabetically, not by trailing return or any other quality "
    "signal. Trailing returns shown are real, computed from mfapi.in's "
    "published NAV history as of the date below - not a claim that one "
    "listed fund is better than another. The same list is shown to every "
    "user; nothing here is personalized to an individual's profile."
)


def select_candidates(index: Dict[str, dict]) -> Dict[str, List[dict]]:
    """Groups E1's committed index ({scheme_code: {name, amc, category,
    isin}}) by AMFI category string, capping how many schemes from the
    same AMC survive into one category's shortlist. Deterministic
    (alphabetical by name) rather than ranked - see module docstring."""
    by_category: Dict[str, List[dict]] = defaultdict(list)
    for scheme_code, entry in index.items():
        category = entry.get("category")
        isin = entry.get("isin")
        name = entry.get("name")
        if not category or not isin or not name:
            continue
        by_category[category].append({
            "scheme_code": scheme_code,
            "name": name,
            "isin": isin,
            "amc": entry.get("amc") or "",
        })

    result: Dict[str, List[dict]] = {}
    for category, candidates in by_category.items():
        candidates.sort(key=lambda c: c["name"])
        per_amc_count: Dict[str, int] = defaultdict(int)
        capped: List[dict] = []
        for candidate in candidates:
            if per_amc_count[candidate["amc"]] >= MAX_PER_AMC_PER_CATEGORY:
                continue
            capped.append(candidate)
            per_amc_count[candidate["amc"]] += 1
            if len(capped) >= MAX_FUNDS_PER_CATEGORY:
                break
        result[category] = capped
    return result


async def attach_trailing_returns(
    candidates_by_category: Dict[str, List[dict]],
    client: Optional[MfApiClient] = None,
) -> Dict[str, List[dict]]:
    """For each capped candidate, fetches real NAV history and computes
    real trailing returns - dropping any candidate without a real 3-year
    figure rather than showing a blank one. `client` is injectable so
    tests never make a real network call; MfApiClient's own throttling
    (see mfapi_client.py) keeps this considerate of mfapi.in regardless of
    how many candidates there are in total."""
    client = client or MfApiClient()
    output: Dict[str, List[dict]] = {}
    for category, candidates in candidates_by_category.items():
        funds: List[dict] = []
        for candidate in candidates:
            history = await client.get_nav_history(candidate["scheme_code"])
            return_3yr = compute_trailing_return(history, 3)
            if return_3yr is None:
                continue
            funds.append({
                "name": candidate["name"],
                "isin": candidate["isin"],
                "amc": candidate["amc"],
                "trailing_return_3yr_pct": return_3yr,
                "trailing_return_5yr_pct": compute_trailing_return(history, 5),
            })
        if funds:
            output[category] = funds
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT_PATH)
    args = parser.parse_args()

    index = load_amfi_category_index()
    if not index:
        print("AMFI_CATEGORY_INDEX_MISSING: run scripts/refresh_amfi_category_index.py first.")
        return 1
    print(f"Loaded {len(index)} schemes from the committed AMFI category index.")

    candidates_by_category = select_candidates(index)
    candidate_count = sum(len(v) for v in candidates_by_category.values())
    print(f"Selected {candidate_count} candidates across {len(candidates_by_category)} categories (pre-return-check).")

    print("Fetching trailing returns from mfapi.in for each shortlisted scheme (throttled, this takes a while) ...")
    shortlists = asyncio.run(attach_trailing_returns(candidates_by_category))
    if not shortlists:
        print("NO_SHORTLISTS_WITH_RETURNS: refusing to write an empty file.")
        return 1
    total_funds = sum(len(v) for v in shortlists.values())
    print(f"Built shortlists for {len(shortlists)} categories, {total_funds} funds total.")

    document = {
        "as_of_date": datetime.date.today().isoformat(),
        "methodology_note": METHODOLOGY_NOTE,
        "categories": shortlists,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
