from datetime import date
from pathlib import Path

from scripts.check_kb_freshness import check_all, check_file


def _write(tmp_path: Path, name: str, content: str) -> Path:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


def test_recently_verified_file_is_ok(tmp_path):
    path = _write(
        tmp_path,
        "fresh.yaml",
        'version: "2025-2026"\nlast_updated: "2025-06-01"\nsource: "Test Act"\n',
    )
    result = check_file(path, today=date(2025, 12, 1), max_age_months=12)

    assert result.status == "OK"
    assert result.age_months == 6
    assert result.source == "Test Act"


def test_file_older_than_threshold_is_stale(tmp_path):
    path = _write(
        tmp_path,
        "old.yaml",
        'version: "2020-2021"\nlast_updated: "2020-01-01"\nsource: "Test Act"\n',
    )
    result = check_file(path, today=date(2025, 12, 1), max_age_months=12)

    assert result.status == "STALE"
    assert result.age_months > 12


def test_file_exactly_at_threshold_is_not_yet_stale(tmp_path):
    path = _write(
        tmp_path,
        "boundary.yaml",
        'version: "2025"\nlast_updated: "2024-12-01"\n',
    )
    result = check_file(path, today=date(2025, 12, 1), max_age_months=12)

    assert result.status == "OK"
    assert result.age_months == 12


def test_missing_last_updated_is_flagged_not_guessed(tmp_path):
    path = _write(tmp_path, "no_date.yaml", 'version: "2024-2025"\n')
    result = check_file(path, today=date(2025, 12, 1), max_age_months=12)

    assert result.status == "MISSING_METADATA"
    assert result.last_updated is None


def test_check_all_classifies_every_real_knowledge_base_file():
    # This intentionally does not assert every file is "OK" - real tax rules
    # legitimately go stale over time, and several files are already missing
    # last_updated today. This just proves the checker runs cleanly end to
    # end against the real knowledge base and gives every file a verdict.
    results = check_all()

    assert len(results) == 14
    assert {r.status for r in results} <= {"OK", "STALE", "MISSING_METADATA"}
