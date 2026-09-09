"""Throwaway diagnostic (same pattern as the original E0 spike that
confirmed AMFI's category headers on 2026-09-03 - see git history for
spike_check_amfi_categories.py, since removed). Re-run because the
2026-09-09 fund-category-refresh run captured a category for only 2 of
1814 committed schemes, versus 98 categories across 14,332 rows on
2026-09-03 - something about the live file's header format likely
changed, and this sandbox can't reach amfiindia.com to inspect it
directly, so the diagnosis has to run from GitHub Actions.

Fetches the live NAVAll.txt and reports, without relying on the current
_CATEGORY_HEADER_RE at all: how many lines look like data rows, how many
non-data lines contain both "schemes" and "(" (candidate headers), how
many of those the *current* regex actually matches, and a sample of the
ones it misses - so the actual format drift is visible instead of guessed
at.

Meant to be deleted once its question is answered, same as the original
E0 spike was deleted once E1 shipped.
"""
import asyncio
import re
import sys

import httpx

URL = "https://www.amfiindia.com/spages/NAVAll.txt"
CURRENT_RE = re.compile(r"^.*Schemes\((.+)\)\s*$")


async def main() -> int:
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        response = await client.get(URL)
    print(f"status={response.status_code} content_length={len(response.text)}")
    if response.status_code != 200:
        return 1

    lines = response.text.splitlines()
    print(f"total_lines={len(lines)}")

    data_rows = 0
    candidate_headers = 0
    matched_by_current_regex = 0
    unmatched_samples = []

    for line in lines:
        stripped = line.strip()
        parts = stripped.split(";")
        if len(parts) >= 8 and parts[0].strip().isdigit():
            data_rows += 1
            continue
        if not stripped:
            continue
        if "schemes" in stripped.lower() and "(" in stripped:
            candidate_headers += 1
            if CURRENT_RE.match(stripped):
                matched_by_current_regex += 1
            elif len(unmatched_samples) < 25:
                unmatched_samples.append(stripped)

    print(f"data_rows={data_rows}")
    print(f"candidate_header_lines={candidate_headers}")
    print(f"matched_by_current_regex={matched_by_current_regex}")
    print(f"unmatched_candidate_count={candidate_headers - matched_by_current_regex}")
    print("Sample candidate header lines the CURRENT regex did NOT match:")
    for sample in unmatched_samples:
        print(f"  {sample!r}")

    print("First 15 non-blank, non-data lines in the file (raw, for eyeballing structure):")
    shown = 0
    for line in lines:
        stripped = line.strip()
        parts = stripped.split(";")
        if len(parts) >= 8 and parts[0].strip().isdigit():
            continue
        if not stripped:
            continue
        print(f"  {stripped!r}")
        shown += 1
        if shown >= 15:
            break

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
