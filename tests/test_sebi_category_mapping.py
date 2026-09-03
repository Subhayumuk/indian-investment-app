from app.modules.sebi_category_mapping import classify_sebi_category


def test_classify_debt_scheme_categories_as_debt():
    assert classify_sebi_category("Debt Scheme - Banking and PSU Fund") == "debt"
    assert classify_sebi_category("Debt Scheme - Gilt Fund") == "debt"


def test_classify_liquid_and_overnight_as_debt_matching_existing_keyword_guess():
    # holdings_review_engine.py's _infer_asset_class already treats these
    # fund names as "debt" via _DEBT_KEYWORDS - a real AMFI category match
    # should agree, not introduce a new asset class this codepath doesn't
    # otherwise use.
    assert classify_sebi_category("Open Ended Schemes(Liquid Fund)") == "debt"
    assert classify_sebi_category("Overnight Fund") == "debt"


def test_classify_gold_before_generic_etf_rule():
    assert classify_sebi_category("Other Scheme - Gold ETF") == "gold"


def test_classify_hybrid_variants():
    assert classify_sebi_category("Hybrid Scheme - Balanced Advantage Fund") == "hybrid"
    assert classify_sebi_category("Hybrid Scheme - Arbitrage Fund") == "hybrid"


def test_classify_solution_oriented_funds_as_hybrid():
    assert classify_sebi_category("Children's Fund - Childrens' Fund") == "hybrid"
    assert classify_sebi_category("Solution Oriented Scheme - Retirement Fund") == "hybrid"


def test_classify_equity_scheme_categories_as_equity():
    assert classify_sebi_category("Equity Scheme - Large Cap Fund") == "equity"


def test_classify_returns_none_for_unrecognised_category():
    assert classify_sebi_category("Some Brand New Category Nobody Has Seen") is None


def test_classify_returns_none_for_empty_or_missing_category():
    assert classify_sebi_category("") is None
    assert classify_sebi_category(None) is None
