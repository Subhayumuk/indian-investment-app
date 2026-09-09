from app.modules.amfi_nav_client import _parse_nav_all_text
from scripts.refresh_amfi_category_index import build_index

# Real order (see test_amfi_nav_client.py's SAMPLE_NAV_ALL_TEXT docstring
# for the full 2026-09-09 regression story): a category header is followed
# by SEVERAL AMC blocks in a row (Aditya Birla, then Franklin Templeton,
# both still "Debt Scheme - Banking and PSU Fund") before the next header.
SAMPLE_TEXT = """Open Ended Schemes(Debt Scheme - Banking and PSU Fund)

Aditya Birla Sun Life Mutual Fund
118989;INF209K01397;INF209K01405;Aditya Birla Sun Life Dividend Yield Fund;Direct Plan;Growth;26.6400;19-Dec-2025
118990;INF209K01AAA;N.A.;Aditya Birla Sun Life Dividend Yield Fund;Direct Plan;IDCW;15.1200;19-Dec-2025
118991;INF209K01BBB;N.A.;Aditya Birla Sun Life Dividend Yield Fund;Regular Plan;Growth;24.0000;19-Dec-2025

Franklin Templeton Mutual Fund
118995;INF090K01AAA;-;Franklin Templeton Corporate Bond Fund;Direct Plan;Growth;20.0000;19-Dec-2025

Open Ended Schemes(Children's Fund - Childrens' Fund)

Axis Mutual Fund
135762;INF846K01WO1;-;Axis Children's Fund;Direct Plan;Growth Option;30.3032;02-Sep-2026
"""


def test_build_index_keeps_only_direct_growth_rows():
    by_isin = _parse_nav_all_text(SAMPLE_TEXT)
    index = build_index(by_isin)

    # 118989 (Direct/Growth) kept; 118990 (Direct/IDCW) and 118991
    # (Regular/Growth) dropped - only the Direct+Growth variant survives.
    # 118995 (Franklin, Direct/Growth) and 135762 (Axis) also kept.
    assert set(index.keys()) == {"118989", "118995", "135762"}


def test_build_index_category_persists_across_multiple_amc_blocks():
    # End-to-end regression for the 2026-09-09 bug: Franklin Templeton's
    # scheme is a second AMC block under the SAME category header as
    # Aditya Birla's, not a fresh, uncategorized block.
    by_isin = _parse_nav_all_text(SAMPLE_TEXT)
    index = build_index(by_isin)

    assert index["118995"]["category"] == "Debt Scheme - Banking and PSU Fund"
    assert index["118995"]["amc"] == "Franklin Templeton Mutual Fund"


def test_build_index_dedupes_multi_isin_scheme_to_one_entry():
    by_isin = _parse_nav_all_text(SAMPLE_TEXT)
    index = build_index(by_isin)

    assert index["118989"]["name"] == "Aditya Birla Sun Life Dividend Yield Fund - Direct Plan - Growth"
    assert index["118989"]["isin"] == "INF209K01397"


def test_build_index_carries_category_and_amc():
    by_isin = _parse_nav_all_text(SAMPLE_TEXT)
    index = build_index(by_isin)

    assert index["118989"]["category"] == "Debt Scheme - Banking and PSU Fund"
    assert index["118989"]["amc"] == "Aditya Birla Sun Life Mutual Fund"
    assert index["135762"]["category"] == "Children's Fund - Childrens' Fund"
    assert index["135762"]["amc"] == "Axis Mutual Fund"


def test_build_index_empty_when_nothing_matches():
    assert build_index({}) == {}
