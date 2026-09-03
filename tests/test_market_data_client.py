import asyncio
from datetime import datetime

from app.models.holdings_review import MatchConfidence
from app.modules.amfi_nav_client import SchemeRecord
from app.modules.market_data_client import MarketDataClient


class FakeAmfiClient:
    def __init__(self, record=None):
        self._record = record

    async def lookup(self, isin):
        return self._record


class FakeMfApiClient:
    def __init__(self, nav_history=None):
        self._nav_history = nav_history or []

    async def get_nav_history(self, scheme_code):
        return self._nav_history


def test_lookup_fund_unmatched_when_isin_not_found_in_amfi():
    client = MarketDataClient(amfi_client=FakeAmfiClient(record=None), mfapi_client=FakeMfApiClient())
    result = asyncio.run(client.lookup_fund("INF000000000", "Some Fund"))
    assert result.match_confidence == MatchConfidence.UNMATCHED
    assert result.data_source == "unavailable"


def test_lookup_fund_unmatched_when_isin_blank():
    client = MarketDataClient(amfi_client=FakeAmfiClient(record=None), mfapi_client=FakeMfApiClient())
    result = asyncio.run(client.lookup_fund("", "Some Fund"))
    assert result.match_confidence == MatchConfidence.UNMATCHED


def test_lookup_fund_matched_with_returns():
    record = SchemeRecord(
        scheme_code="118989",
        scheme_name="Aditya Birla Sun Life Dividend Yield Fund-Growth",
        latest_nav=26.64,
        category="Debt Scheme - Banking and PSU Fund",
    )
    nav_history = [
        {"date": datetime(2025, 1, 1), "nav": 20.0},
        {"date": datetime(2026, 1, 1), "nav": 26.64},
    ]
    client = MarketDataClient(
        amfi_client=FakeAmfiClient(record=record),
        mfapi_client=FakeMfApiClient(nav_history=nav_history),
    )
    result = asyncio.run(client.lookup_fund("INF209K01397", "Aditya Birla Sun"))
    assert result.match_confidence == MatchConfidence.ISIN_MATCH
    assert result.amfi_scheme_code == "118989"
    assert result.matched_scheme_name == "Aditya Birla Sun Life Dividend Yield Fund-Growth"
    assert result.latest_nav == 26.64
    assert result.category == "Debt Scheme - Banking and PSU Fund"
    assert result.trailing_return_1yr_pct is not None
    assert result.data_source == "amfi+mfapi"


def test_lookup_fund_matched_but_no_history_available():
    record = SchemeRecord(scheme_code="118989", scheme_name="Some Fund", latest_nav=10.0)
    client = MarketDataClient(
        amfi_client=FakeAmfiClient(record=record),
        mfapi_client=FakeMfApiClient(nav_history=[]),
    )
    result = asyncio.run(client.lookup_fund("INF209K01397", "Some Fund"))
    assert result.match_confidence == MatchConfidence.ISIN_MATCH
    assert result.data_source == "amfi_only"
    assert result.trailing_return_3yr_pct is None
    assert result.category == ""  # SchemeRecord.category defaults to None -> coerced to "" here
