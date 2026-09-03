"""Phase E, step E0 spike — NOT production code, delete after use.

Answers two questions before any real Phase E code gets written:
1. Does AMFI's live NAVAll.txt still carry category-header lines like
   "Open Ended Schemes(Debt Scheme - Banking and PSU Fund)" ahead of the
   scheme rows they group? app/modules/amfi_nav_client.py's
   _parse_nav_all_text currently discards these lines (any line with fewer
   than 8 ';'-fields is skipped) rather than attaching them to SchemeRecords.
2. Can this runner (a GitHub Actions runner, when run via the companion
   workflow) reach amfiindia.com at all? Confirmed reachable from Render and
   intermittently from a local machine earlier, but never confirmed from a
   GitHub Actions runner specifically, and NOT reachable from the machine
   this spike was authored on (curl exit 28, connection refused, 3/3
   attempts).

Deliberately does not import anything from app/ or depend on httpx - this
is a throwaway, standalone check, not permanent plumbing.

Usage:
    python scripts/spike_check_amfi_categories.py
"""
from __future__ import annotations

import re
import sys
import urllib.error
import urllib.request

NAV_ALL_URL = "https://www.amfiindia.com/spages/NAVAll.txt"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
TIMEOUT_SECONDS = 30
CATEGORY_HEADER_RE = re.compile(r"^Open Ended Schemes\(.*\)\s*$")


def fetch() -> str:
    request = urllib.request.Request(NAV_ALL_URL, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def main() -> int:
    print(f"Fetching {NAV_ALL_URL} ...")
    try:
        text = fetch()
    except urllib.error.URLError as exc:
        print(f"FETCH_FAILED: {exc}")
        return 1
    except Exception as exc:  # noqa: BLE001 - any failure here is the answer we're looking for
        print(f"FETCH_FAILED (unexpected): {exc}")
        return 1

    lines = text.splitlines()
    print(f"FETCH_OK: {len(lines)} lines, {len(text)} chars")

    category_headers = [ln.strip() for ln in lines if CATEGORY_HEADER_RE.match(ln.strip())]
    distinct_categories = sorted(set(category_headers))
    data_rows = [ln for ln in lines if len(ln.strip().split(";")) >= 8 and ln.strip().split(";")[0].strip().isdigit()]

    print(f"CATEGORY_HEADER_LINES: {len(category_headers)}")
    print(f"DISTINCT_CATEGORY_STRINGS: {len(distinct_categories)}")
    print(f"DATA_ROWS: {len(data_rows)}")

    if distinct_categories:
        print("\nSample category strings (first 15):")
        for cat in distinct_categories[:15]:
            print(f"  {cat}")
    else:
        print("\nNo category-header lines matched the expected pattern - format may have changed.")

    if data_rows:
        print("\nSample data row:")
        print(f"  {data_rows[0]}")

    # Non-zero only on FETCH_FAILED (handled above via early return); a
    # successful fetch with zero category headers is still useful signal,
    # not a script failure - the caller (workflow log) is where a human
    # reads the real verdict.
    return 0


if __name__ == "__main__":
    sys.exit(main())
