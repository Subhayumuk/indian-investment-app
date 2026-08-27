"""Reports how long ago each knowledge base YAML file's data was last verified.

Every file under app/knowledge_base/ can carry `version`, `last_updated`, and
`source` fields, but nothing checks them automatically today — a tax rate can
sit there quietly out of date for years. This script is that check: run it
by hand, or wire it into a scheduled job (e.g. every year ahead of India's
April 1 new tax year), to get a report of what needs a human to go re-verify
it against current law.

It does NOT fetch or guess real-world tax rates itself — figuring out what
changed is a job for a person reading the actual legislation, same as the
existing YAML files were written. This just stops that need from going
unnoticed.

Usage:
    python scripts/check_kb_freshness.py
    python scripts/check_kb_freshness.py --max-age-months 6
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Optional

import yaml

KB_ROOT = Path(__file__).resolve().parent.parent / "app" / "knowledge_base"
DEFAULT_MAX_AGE_MONTHS = 12


@dataclass
class FreshnessResult:
    path: Path
    version: Optional[str]
    source: Optional[str]
    last_updated: Optional[date]
    age_months: Optional[int]
    status: str  # "OK", "STALE", or "MISSING_METADATA"


def _parse_last_updated(raw: object) -> Optional[date]:
    if raw is None:
        return None
    if isinstance(raw, date):
        return raw
    return date.fromisoformat(str(raw))


def _months_between(earlier: date, later: date) -> int:
    return (later.year - earlier.year) * 12 + (later.month - earlier.month)


def check_file(path: Path, today: date, max_age_months: int) -> FreshnessResult:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    version = data.get("version")
    source = data.get("source")
    last_updated = _parse_last_updated(data.get("last_updated"))

    if last_updated is None:
        return FreshnessResult(path, version, source, None, None, "MISSING_METADATA")

    age_months = _months_between(last_updated, today)
    status = "STALE" if age_months > max_age_months else "OK"
    return FreshnessResult(path, version, source, last_updated, age_months, status)


def check_all(
    max_age_months: int = DEFAULT_MAX_AGE_MONTHS, today: Optional[date] = None
) -> list[FreshnessResult]:
    today = today or date.today()
    return [
        check_file(path, today, max_age_months)
        for path in sorted(KB_ROOT.rglob("*.yaml"))
    ]


def _print_report(results: list[FreshnessResult]) -> None:
    width = max(len(str(r.path.relative_to(KB_ROOT))) for r in results)
    for r in results:
        rel = str(r.path.relative_to(KB_ROOT)).ljust(width)
        if r.status == "MISSING_METADATA":
            print(f"  ?  {rel}  no last_updated field - freshness unknown")
        elif r.status == "STALE":
            print(f"  !  {rel}  last verified {r.last_updated} ({r.age_months} months ago) - STALE")
        else:
            print(f"  ok {rel}  last verified {r.last_updated} ({r.age_months} months ago)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--max-age-months",
        type=int,
        default=DEFAULT_MAX_AGE_MONTHS,
        help=f"Flag files older than this many months (default: {DEFAULT_MAX_AGE_MONTHS}).",
    )
    args = parser.parse_args()

    results = check_all(max_age_months=args.max_age_months)
    _print_report(results)

    problems = [r for r in results if r.status != "OK"]
    print()
    if problems:
        print(f"{len(problems)} of {len(results)} knowledge base files need review.")
        return 1

    print(f"All {len(results)} knowledge base files are within {args.max_age_months} months.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
