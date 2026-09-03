"""Refreshes app/knowledge_base/amfi_category_index.json from AMFI's live
NAVAll.txt - the real, per-scheme SEBI category data that Phase E's E1 step
adds (see ~/.claude/plans, "Phase E - Grounded 'Where Should New Money Go'
Suggestions"). Run monthly by .github/workflows/fund-category-refresh.yml,
which opens a PR with the result rather than pushing directly - this file
feeds real financial-fact claims into the app, unlike the fingerprint-only
commits scripts/check_kb_source_changes.py makes.

Reuses AmfiNavClient's fetch-and-parse logic (app/modules/amfi_nav_client.py)
rather than re-implementing the HTTP/redirect/parsing logic here - this
script's only job is to dedupe the full ISIN-keyed index down to one row per
distinct scheme (Direct Plan, Growth option only - Regular Plan and IDCW
variants of the same underlying scheme are noise for the category-lookup
and future shortlist-ranking use cases this index exists for) and write it
out as compact, committable JSON.

Usage:
    python scripts/refresh_amfi_category_index.py [--out PATH]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Dict

from app.modules.amfi_nav_client import AmfiNavClient, SchemeRecord

DEFAULT_OUT_PATH = (
    Path(__file__).resolve().parent.parent / "app" / "knowledge_base" / "amfi_category_index.json"
)


def _is_direct_growth(scheme_name: str) -> bool:
    """scheme_name is base_name + plan + option joined by ' - ' (see
    _parse_nav_all_text) - plan/option aren't separate fields, so this is a
    substring heuristic, not an exact field match. "direct" reliably
    distinguishes Direct Plan from Regular Plan (AMFI's plan field is
    consistently one of those two strings); "growth" excludes IDCW variants
    but could rarely false-positive on a base fund name that itself
    contains "growth" - an accepted, disclosed limitation, not a certainty."""
    n = scheme_name.lower()
    return "direct" in n and "growth" in n


def build_index(by_isin: Dict[str, SchemeRecord]) -> Dict[str, dict]:
    by_scheme_code: Dict[str, dict] = {}
    for record in by_isin.values():
        if record.scheme_code in by_scheme_code:
            continue  # already captured this scheme via another ISIN key
        if not _is_direct_growth(record.scheme_name):
            continue
        by_scheme_code[record.scheme_code] = {
            "name": record.scheme_name,
            "amc": record.amc,
            "category": record.category,
        }
    # Attach the ISIN each scheme_code resolved from (the growth-plan one,
    # since only Direct-Growth rows survived the filter above).
    for isin, record in by_isin.items():
        entry = by_scheme_code.get(record.scheme_code)
        if entry is not None and "isin" not in entry:
            entry["isin"] = isin
    return by_scheme_code


async def _fetch_index() -> Dict[str, SchemeRecord]:
    client = AmfiNavClient()
    return await client._fetch_and_parse()  # reuses the same fetch/parse AmfiNavClient.lookup() uses


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT_PATH)
    args = parser.parse_args()

    print("Fetching and parsing AMFI NAVAll.txt ...")
    by_isin = asyncio.run(_fetch_index())
    if not by_isin:
        print("FETCH_OR_PARSE_FAILED: no schemes indexed - not writing an empty/stale-looking file.")
        return 1
    print(f"Parsed {len(by_isin)} ISIN entries.")

    index = build_index(by_isin)
    if not index:
        print("No Direct-Growth schemes matched after filtering - refusing to write an empty index.")
        return 1

    with_category = sum(1 for entry in index.values() if entry.get("category"))
    print(f"Deduped to {len(index)} distinct Direct-Growth schemes ({with_category} with a resolved category).")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(index, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
