import asyncio
from datetime import datetime

from app.modules.mfapi_client import (
    MfApiClient,
    _parse_nav_history,
    compute_trailing_return,
)


class FakeResponse:
    def __init__(self, status_code=200, json_data=None):
        self.status_code = status_code
        self._json_data = json_data or {}

    def json(self):
        return self._json_data


class FakeHttpClient:
    def __init__(self, response):
        self._response = response

    async def get(self, url, timeout=None):
        return self._response


def test_parse_nav_history_skips_malformed_rows():
    payload = {
        "data": [
            {"date": "01-01-2026", "nav": "100.00"},
            {"date": "not-a-date", "nav": "50.00"},
            {"date": "01-01-2025", "nav": "not-a-number"},
            {"nav": "10.00"},  # missing date entirely
        ]
    }
    points = _parse_nav_history(payload)
    assert len(points) == 1
    assert points[0]["nav"] == 100.0
    assert points[0]["date"] == datetime(2026, 1, 1)


def test_compute_trailing_return_none_for_empty_history():
    assert compute_trailing_return([], years=3) is None


def test_compute_trailing_return_none_when_history_too_short():
    # Only ~6 months of data — asking for a 3yr return shouldn't extrapolate.
    history = [
        {"date": datetime(2025, 7, 1), "nav": 10.0},
        {"date": datetime(2026, 1, 1), "nav": 11.0},
    ]
    assert compute_trailing_return(history, years=3) is None


def test_compute_trailing_return_computes_cagr_for_sufficient_history():
    # NAV doubled over ~1 year -> CAGR should be roughly +100%, not exact
    # (day-count rounding), so assert a range rather than a precise value.
    history = [
        {"date": datetime(2025, 1, 1), "nav": 50.0},
        {"date": datetime(2026, 1, 1), "nav": 100.0},
    ]
    result = compute_trailing_return(history, years=1)
    assert result is not None
    assert 90.0 < result < 110.0


def test_get_nav_history_returns_empty_list_on_bad_status():
    client = MfApiClient(http_client=FakeHttpClient(FakeResponse(status_code=500)))
    assert asyncio.run(client.get_nav_history("118989")) == []


def test_get_nav_history_returns_empty_list_for_blank_scheme_code():
    client = MfApiClient(http_client=FakeHttpClient(FakeResponse()))
    assert asyncio.run(client.get_nav_history("")) == []


def test_get_nav_history_parses_real_shaped_payload():
    payload = {"data": [{"date": "01-01-2026", "nav": "42.50"}]}
    client = MfApiClient(http_client=FakeHttpClient(FakeResponse(json_data=payload)))
    points = asyncio.run(client.get_nav_history("118989"))
    assert len(points) == 1
    assert points[0]["nav"] == 42.5
