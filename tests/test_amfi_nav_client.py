import asyncio

import pytest

from app.modules.amfi_nav_client import AmfiNavClient, _parse_nav_all_text

# Real AMFI NAVAll.txt shape (verified against the live file, not just
# documentation, most recently via a live GitHub Actions run on 2026-09-03):
# AMC-name and category-header lines (no semicolons) and blank-line
# separators interleaved with data rows in
# Scheme Code;ISIN Growth;ISIN Div Reinvestment;Scheme Name;Plan;Option;NAV;Date order.
# The live file uses both "N.A." and a bare "-" for "no dividend-reinvestment
# ISIN" - the second data row and the Axis Children's Fund category below
# exercise both, plus a second category block to confirm headers reset
# correctly between blocks rather than leaking across them.
SAMPLE_NAV_ALL_TEXT = """Aditya Birla Sun Life Mutual Fund
Open Ended Schemes(Debt Scheme - Banking and PSU Fund)

118989;INF209K01397;INF209K01405;Aditya Birla Sun Life Dividend Yield Fund;Direct Plan;Growth;26.6400;19-Dec-2025
118990;N.A.;INF209K01413;Aditya Birla Sun Life Some Other Fund;Regular Plan;IDCW;15.1200;19-Dec-2025

Axis Mutual Fund
Open Ended Schemes(Children's Fund - Childrens' Fund)

135762;INF846K01WO1;-;Axis Children's Fund;Direct Plan;Growth Option;30.3032;02-Sep-2026
"""


class FakeResponse:
    def __init__(self, status_code=200, text=""):
        self.status_code = status_code
        self.text = text


class FakeHttpClient:
    def __init__(self, response):
        self._response = response

    async def get(self, url, timeout=None):
        return self._response


class CountingSlowHttpClient:
    """Tracks how many times .get() was actually called, and yields control
    (asyncio.sleep(0)) before returning - enough for a real event loop to
    interleave concurrent lookup() calls if they aren't properly guarded."""

    def __init__(self, response):
        self._response = response
        self.call_count = 0

    async def get(self, url, timeout=None):
        self.call_count += 1
        await asyncio.sleep(0)
        return self._response


def test_parse_nav_all_text_indexes_both_isin_variants_to_same_scheme():
    index = _parse_nav_all_text(SAMPLE_NAV_ALL_TEXT)
    assert index["INF209K01397"].scheme_code == "118989"
    assert index["INF209K01397"].scheme_name == "Aditya Birla Sun Life Dividend Yield Fund - Direct Plan - Growth"
    assert index["INF209K01397"].latest_nav == pytest.approx(26.64)
    assert index["INF209K01405"].scheme_code == "118989"  # dividend-reinvestment ISIN, same scheme


def test_parse_nav_all_text_skips_na_isin_and_header_lines():
    index = _parse_nav_all_text(SAMPLE_NAV_ALL_TEXT)
    assert "N.A." not in index
    assert "-" not in index  # regression: a bare "-" used to slip past the old N.A.-only guard
    assert len(index) == 4  # two ISINs for 118989, one for 118990, one for 135762 ("-" variant skipped)


def test_parse_nav_all_text_attaches_category_from_preceding_header():
    index = _parse_nav_all_text(SAMPLE_NAV_ALL_TEXT)
    assert index["INF209K01397"].category == "Debt Scheme - Banking and PSU Fund"
    assert index["INF209K01413"].category == "Debt Scheme - Banking and PSU Fund"


def test_parse_nav_all_text_resets_category_between_header_blocks():
    index = _parse_nav_all_text(SAMPLE_NAV_ALL_TEXT)
    assert index["INF846K01WO1"].category == "Children's Fund - Childrens' Fund"


def test_parse_nav_all_text_attaches_amc_name():
    index = _parse_nav_all_text(SAMPLE_NAV_ALL_TEXT)
    assert index["INF209K01397"].amc == "Aditya Birla Sun Life Mutual Fund"
    assert index["INF846K01WO1"].amc == "Axis Mutual Fund"


def test_parse_nav_all_text_leaves_category_none_when_no_header_seen_yet():
    text = "118989;INF209K01397;N.A.;A Fund With No Header;Direct Plan;Growth;10.0;19-Dec-2025\n"
    index = _parse_nav_all_text(text)
    assert index["INF209K01397"].category is None


def test_lookup_returns_scheme_for_known_isin():
    client = AmfiNavClient(http_client=FakeHttpClient(FakeResponse(text=SAMPLE_NAV_ALL_TEXT)))
    record = asyncio.run(client.lookup("INF209K01397"))
    assert record is not None
    assert record.scheme_code == "118989"


def test_lookup_returns_none_for_unknown_isin():
    client = AmfiNavClient(http_client=FakeHttpClient(FakeResponse(text=SAMPLE_NAV_ALL_TEXT)))
    assert asyncio.run(client.lookup("INF000000000")) is None


def test_lookup_returns_none_when_isin_blank():
    client = AmfiNavClient(http_client=FakeHttpClient(FakeResponse(text=SAMPLE_NAV_ALL_TEXT)))
    assert asyncio.run(client.lookup("")) is None


def test_lookup_degrades_to_none_on_fetch_failure_rather_than_raising():
    client = AmfiNavClient(http_client=FakeHttpClient(FakeResponse(status_code=500, text="")))
    assert asyncio.run(client.lookup("INF209K01397")) is None


def test_concurrent_lookups_on_a_cold_cache_only_fetch_once():
    # holdings_review_engine.py fans out lookups for many funds with
    # asyncio.gather - without the refresh lock, every one of them would
    # see a cold cache at the same time and each fire its own fetch.
    http_client = CountingSlowHttpClient(FakeResponse(text=SAMPLE_NAV_ALL_TEXT))
    client = AmfiNavClient(http_client=http_client)

    async def run_concurrent_lookups():
        # asyncio.gather() must be called from inside a running loop, not
        # passed as a bare argument to asyncio.run() - the latter evaluates
        # gather() before the loop exists.
        return await asyncio.gather(
            client.lookup("INF209K01397"),
            client.lookup("INF209K01405"),
            client.lookup("INF209K01413"),
        )

    results = asyncio.run(run_concurrent_lookups())

    assert http_client.call_count == 1
    assert [r.scheme_code for r in results] == ["118989", "118989", "118990"]
