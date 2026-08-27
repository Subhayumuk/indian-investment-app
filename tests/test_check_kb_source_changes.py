import json
from pathlib import Path

from scripts.check_kb_source_changes import check_all, fingerprint


def _write_yaml(dir_path: Path, name: str, source_url: str | None) -> Path:
    path = dir_path / name
    body = f'version: "2025"\n'
    if source_url:
        body += f'source_url: "{source_url}"\n'
    body += "some_field: 1\n"
    path.write_text(body, encoding="utf-8")
    return path


def test_first_run_reports_new_and_records_baseline(tmp_path):
    kb_root = tmp_path / "kb"
    kb_root.mkdir()
    _write_yaml(kb_root, "a.yaml", "https://example.com/a")
    state_path = tmp_path / "state.json"

    results = check_all(kb_root=kb_root, state_path=state_path, fetch=lambda url: "<html>hello</html>")

    assert len(results) == 1
    assert results[0].status == "NEW"
    saved = json.loads(state_path.read_text(encoding="utf-8"))
    assert "a.yaml" in saved


def test_unchanged_content_is_reported_unchanged(tmp_path):
    kb_root = tmp_path / "kb"
    kb_root.mkdir()
    _write_yaml(kb_root, "a.yaml", "https://example.com/a")
    state_path = tmp_path / "state.json"

    check_all(kb_root=kb_root, state_path=state_path, fetch=lambda url: "<html>hello</html>")
    results = check_all(kb_root=kb_root, state_path=state_path, fetch=lambda url: "<html>hello</html>")

    assert results[0].status == "UNCHANGED"


def test_changed_content_is_flagged(tmp_path):
    kb_root = tmp_path / "kb"
    kb_root.mkdir()
    _write_yaml(kb_root, "a.yaml", "https://example.com/a")
    state_path = tmp_path / "state.json"

    check_all(kb_root=kb_root, state_path=state_path, fetch=lambda url: "<html>old rate 15%</html>")
    results = check_all(kb_root=kb_root, state_path=state_path, fetch=lambda url: "<html>new rate 20%</html>")

    assert results[0].status == "CHANGED"


def test_irrelevant_html_noise_does_not_trigger_a_false_change(tmp_path):
    # Script/style content and whitespace/formatting differences shouldn't
    # count as a real change - only visible text does.
    kb_root = tmp_path / "kb"
    kb_root.mkdir()
    _write_yaml(kb_root, "a.yaml", "https://example.com/a")
    state_path = tmp_path / "state.json"

    first = "<html><head><script>var x = Math.random();</script></head><body>  Rate: 20%  </body></html>"
    second = "<html><head><script>var x = 999;</script></head><body>Rate: 20%</body></html>"

    check_all(kb_root=kb_root, state_path=state_path, fetch=lambda url: first)
    results = check_all(kb_root=kb_root, state_path=state_path, fetch=lambda url: second)

    assert results[0].status == "UNCHANGED"


def test_fetch_failure_is_reported_not_treated_as_change(tmp_path):
    kb_root = tmp_path / "kb"
    kb_root.mkdir()
    _write_yaml(kb_root, "a.yaml", "https://example.com/a")
    state_path = tmp_path / "state.json"

    def broken_fetch(url):
        raise TimeoutError("simulated network failure")

    results = check_all(kb_root=kb_root, state_path=state_path, fetch=broken_fetch)

    assert results[0].status == "FETCH_FAILED"
    assert not state_path.exists() or "a.yaml" not in json.loads(state_path.read_text(encoding="utf-8"))


def test_file_without_source_url_is_reported_separately(tmp_path):
    kb_root = tmp_path / "kb"
    kb_root.mkdir()
    _write_yaml(kb_root, "a.yaml", None)
    state_path = tmp_path / "state.json"

    results = check_all(kb_root=kb_root, state_path=state_path, fetch=lambda url: "<html></html>")

    assert results[0].status == "NO_SOURCE_URL"


def test_fingerprint_ignores_tag_structure_around_same_text():
    a = fingerprint("<div><p>Rate: 20%</p></div>")
    b = fingerprint("<span>Rate: 20%</span>")
    assert a == b


def test_monitor_url_is_fetched_instead_of_blocked_source_url(tmp_path):
    kb_root = tmp_path / "kb"
    kb_root.mkdir()
    path = kb_root / "a.yaml"
    path.write_text(
        'version: "2025"\n'
        'source_url: "https://blocked.example.com/law"\n'
        'monitor_url: "https://news.example.com/feed"\n',
        encoding="utf-8",
    )
    state_path = tmp_path / "state.json"

    fetched_urls = []

    def fake_fetch(url):
        fetched_urls.append(url)
        return "<html>news</html>"

    results = check_all(kb_root=kb_root, state_path=state_path, fetch=fake_fetch)

    assert fetched_urls == ["https://news.example.com/feed"]
    assert results[0].source_url == "https://news.example.com/feed"
