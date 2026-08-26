import asyncio

import pytest

from app.modules.amfi_nav_client import AmfiNavClient, _parse_nav_all_text

# Real AMFI NAVAll.txt shape (verified against the live file, not just
# documentation): AMC-name and category-header lines (no semicolons) and
# blank-line separators interleaved with data rows in
# Scheme Code;ISIN Growth;ISIN Div Reinvestment;Scheme Name;Plan;Option;NAV;Date order.
SAMPLE_NAV_ALL_TEXT = """Aditya Birla Sun Life Mutual Fund
Open Ended Schemes(Debt Scheme - Banking and PSU Fund)

118989;INF209K01397;INF209K01405;Aditya Birla Sun Life Dividend Yield Fund;Direct Plan;Growth;26.6400;19-Dec-2025
118990;N.A.;INF209K01413;Aditya Birla Sun Life Some Other Fund;Regular Plan;IDCW;15.1200;19-Dec-2025
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


def test_parse_nav_all_text_indexes_both_isin_variants_to_same_scheme():
    index = _parse_nav_all_text(SAMPLE_NAV_ALL_TEXT)
    assert index["INF209K01397"].scheme_code == "118989"
    assert index["INF209K01397"].scheme_name == "Aditya Birla Sun Life Dividend Yield Fund - Direct Plan - Growth"
    assert index["INF209K01397"].latest_nav == pytest.approx(26.64)
    assert index["INF209K01405"].scheme_code == "118989"  # dividend-reinvestment ISIN, same scheme


def test_parse_nav_all_text_skips_na_isin_and_header_lines():
    index = _parse_nav_all_text(SAMPLE_NAV_ALL_TEXT)
    assert "N.A." not in index
    assert len(index) == 3  # two ISINs for scheme 118989, one for 118990


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
