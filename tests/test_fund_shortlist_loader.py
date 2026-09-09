import json

from app.modules import fund_shortlist_loader


def test_load_fund_category_shortlists_returns_empty_dict_when_file_missing(tmp_path, monkeypatch):
    fund_shortlist_loader.load_fund_category_shortlists.cache_clear()
    monkeypatch.setattr(fund_shortlist_loader, "SHORTLIST_PATH", tmp_path / "does_not_exist.json")

    assert fund_shortlist_loader.load_fund_category_shortlists() == {}
    fund_shortlist_loader.load_fund_category_shortlists.cache_clear()


def test_load_fund_category_shortlists_reads_committed_json(tmp_path, monkeypatch):
    fund_shortlist_loader.load_fund_category_shortlists.cache_clear()
    path = tmp_path / "fund_category_shortlists.json"
    payload = {
        "as_of_date": "2026-09-09",
        "methodology_note": "test note",
        "categories": {
            "Liquid Fund": [
                {"name": "Some Liquid Fund", "isin": "INF209K01397", "amc": "Some AMC",
                 "trailing_return_3yr_pct": 6.1, "trailing_return_5yr_pct": 5.9},
            ],
        },
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(fund_shortlist_loader, "SHORTLIST_PATH", path)

    result = fund_shortlist_loader.load_fund_category_shortlists()

    assert result == payload
    fund_shortlist_loader.load_fund_category_shortlists.cache_clear()
