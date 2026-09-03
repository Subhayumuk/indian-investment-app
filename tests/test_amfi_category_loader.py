import json

from app.modules import amfi_category_loader


def test_load_amfi_category_index_returns_empty_dict_when_file_missing(tmp_path, monkeypatch):
    amfi_category_loader.load_amfi_category_index.cache_clear()
    monkeypatch.setattr(amfi_category_loader, "INDEX_PATH", tmp_path / "does_not_exist.json")

    assert amfi_category_loader.load_amfi_category_index() == {}
    amfi_category_loader.load_amfi_category_index.cache_clear()


def test_load_amfi_category_index_reads_committed_json(tmp_path, monkeypatch):
    amfi_category_loader.load_amfi_category_index.cache_clear()
    index_path = tmp_path / "amfi_category_index.json"
    payload = {"118989": {"name": "Some Fund - Direct Plan - Growth", "amc": "Some AMC",
                           "category": "Debt Scheme - Gilt Fund", "isin": "INF209K01397"}}
    index_path.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(amfi_category_loader, "INDEX_PATH", index_path)

    result = amfi_category_loader.load_amfi_category_index()

    assert result == payload
    amfi_category_loader.load_amfi_category_index.cache_clear()
