from pathlib import Path

import pytest

from app.utils.kb_loader import load_country_tax_rules, load_india_kb, load_kb_file

KB_ROOT = Path(__file__).resolve().parent.parent / "app" / "knowledge_base"


def test_all_knowledge_base_yaml_files_parse_as_dicts():
    yaml_files = sorted(KB_ROOT.rglob("*.yaml"))
    assert len(yaml_files) == 14

    for path in yaml_files:
        country = path.parent.name
        data = load_kb_file(country, path.name)
        assert isinstance(data, dict)
        assert data, f"{path} parsed to an empty dict"


def test_load_india_kb_returns_expected_top_level_keys():
    nri_taxation = load_india_kb("nri_taxation.yaml")
    assert "residency_rules" in nri_taxation
    assert "tds_rates" in nri_taxation
    assert "capital_gains" in nri_taxation

    dtaa = load_india_kb("dtaa_provisions.yaml")
    assert "dtaa_countries" in dtaa
    assert "denmark" in dtaa["dtaa_countries"]


@pytest.mark.parametrize(
    "country",
    ["denmark", "uae", "uk", "usa", "singapore", "canada", "germany", "australia"],
)
def test_load_country_tax_rules_for_every_supported_country(country):
    rules = load_country_tax_rules(country)
    assert isinstance(rules, dict)
    assert "version" in rules


def test_load_kb_file_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        load_kb_file("india", "does_not_exist.yaml")


def test_load_kb_file_is_cached():
    first = load_kb_file("india", "fema_rules.yaml")
    second = load_kb_file("india", "fema_rules.yaml")
    assert first is second
