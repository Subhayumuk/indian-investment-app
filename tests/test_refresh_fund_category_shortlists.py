import asyncio
from datetime import datetime

from scripts.refresh_fund_category_shortlists import (
    MAX_FUNDS_PER_CATEGORY,
    attach_trailing_returns,
    select_candidates,
)

SAMPLE_INDEX = {
    "100001": {"name": "Alpha Mid Cap Fund", "amc": "Alpha AMC", "category": "Mid Cap Fund", "isin": "INF100001AAA"},
    "100002": {"name": "Beta Mid Cap Fund", "amc": "Alpha AMC", "category": "Mid Cap Fund", "isin": "INF100002AAA"},
    "100003": {"name": "Gamma Mid Cap Fund", "amc": "Gamma AMC", "category": "Mid Cap Fund", "isin": "INF100003AAA"},
    "100004": {"name": "Delta Liquid Fund", "amc": "Delta AMC", "category": "Liquid Fund", "isin": "INF100004AAA"},
    "100005": {"name": "No Category Fund", "amc": "Some AMC", "category": None, "isin": "INF100005AAA"},
    "100006": {"name": "No ISIN Fund", "amc": "Some AMC", "category": "Liquid Fund", "isin": None},
}


def test_select_candidates_caps_one_per_amc_per_category():
    result = select_candidates(SAMPLE_INDEX)

    mid_cap = result["Mid Cap Fund"]
    # Alpha AMC has two Mid Cap schemes (Alpha, Beta) - only one may survive.
    amcs = [c["amc"] for c in mid_cap]
    assert amcs.count("Alpha AMC") == 1
    assert "Gamma AMC" in amcs


def test_select_candidates_orders_alphabetically_by_name():
    result = select_candidates(SAMPLE_INDEX)
    mid_cap_names = [c["name"] for c in result["Mid Cap Fund"]]
    assert mid_cap_names == sorted(mid_cap_names)


def test_select_candidates_skips_rows_missing_category_or_isin():
    result = select_candidates(SAMPLE_INDEX)
    all_names = {c["name"] for candidates in result.values() for c in candidates}
    assert "No Category Fund" not in all_names
    assert "No ISIN Fund" not in all_names


def test_select_candidates_respects_max_funds_per_category():
    big_index = {
        str(i): {"name": f"Fund {i:03d}", "amc": f"AMC {i}", "category": "Mid Cap Fund", "isin": f"INF{i:06d}AAA"}
        for i in range(MAX_FUNDS_PER_CATEGORY + 5)
    }
    result = select_candidates(big_index)
    assert len(result["Mid Cap Fund"]) == MAX_FUNDS_PER_CATEGORY


class FakeMfApiClient:
    """Returns canned NAV history keyed by scheme_code, no network call."""

    def __init__(self, histories):
        self._histories = histories

    async def get_nav_history(self, scheme_code):
        return self._histories.get(scheme_code, [])


def test_attach_trailing_returns_drops_schemes_without_enough_history():
    candidates_by_category = {
        "Liquid Fund": [
            {"scheme_code": "1", "name": "Has History", "isin": "INF1", "amc": "AMC A"},
            {"scheme_code": "2", "name": "No History", "isin": "INF2", "amc": "AMC B"},
        ],
    }
    histories = {
        "1": [
            {"date": datetime(2022, 1, 1), "nav": 10.0},
            {"date": datetime(2026, 1, 1), "nav": 12.0},
        ],
        "2": [
            {"date": datetime(2026, 1, 1), "nav": 10.0},  # only one point - no 3yr figure possible
        ],
    }
    client = FakeMfApiClient(histories)

    result = asyncio.run(attach_trailing_returns(candidates_by_category, client=client))

    names = [f["name"] for f in result["Liquid Fund"]]
    assert names == ["Has History"]
    assert result["Liquid Fund"][0]["trailing_return_3yr_pct"] is not None


def test_attach_trailing_returns_omits_category_with_nothing_usable():
    candidates_by_category = {
        "Liquid Fund": [{"scheme_code": "1", "name": "No History", "isin": "INF1", "amc": "AMC A"}],
    }
    client = FakeMfApiClient(histories={})

    result = asyncio.run(attach_trailing_returns(candidates_by_category, client=client))

    assert result == {}
