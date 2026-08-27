"""Detects when a knowledge base file's cited source has actually changed.

Unlike scripts/check_kb_freshness.py (which fires on a fixed calendar), this
fetches every source_url under app/knowledge_base/ and compares a fingerprint
of its visible text against what was recorded on the previous run. It only
flags a file when its source page plausibly changed - not on a schedule.

This can't tell you WHAT changed, or whether the change is even relevant to
the numbers we care about (a cookie banner or an unrelated news item on the
same page can trigger a false positive) - it only tells you a page moved
since last time, so you know where to go look. A human still decides what,
if anything, to edit in the YAML - same reasoning as check_kb_freshness.py.

State (the last-seen fingerprint per file) lives in
scripts/kb_source_state.json and must be committed back to the repo after
each run, or every run looks like a false "NEW" baseline forever.

Usage:
    python scripts/check_kb_source_changes.py
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Optional

import yaml

KB_ROOT = Path(__file__).resolve().parent.parent / "app" / "knowledge_base"
STATE_PATH = Path(__file__).resolve().parent / "kb_source_state.json"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
TIMEOUT_SECONDS = 20


class _TextExtractor(HTMLParser):
    """Strips tags/scripts/styles down to visible text, for fingerprinting."""

    def __init__(self):
        super().__init__()
        self._skip_depth = 0
        self.chunks: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self._skip_depth += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript") and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data):
        if not self._skip_depth:
            text = data.strip()
            if text:
                self.chunks.append(text)


def fingerprint(html: str) -> str:
    extractor = _TextExtractor()
    extractor.feed(html)
    text = " ".join(extractor.chunks)
    text = re.sub(r"\s+", " ", text).strip()
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass
class SourceCheckResult:
    path: str
    source_url: Optional[str]
    status: str  # NO_SOURCE_URL, FETCH_FAILED, NEW, UNCHANGED, CHANGED
    detail: str = ""


def _load_state(state_path: Path) -> dict:
    if state_path.exists():
        return json.loads(state_path.read_text(encoding="utf-8"))
    return {}


def _save_state(state_path: Path, state: dict) -> None:
    state_path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _fetch(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def check_all(
    kb_root: Path = KB_ROOT, state_path: Path = STATE_PATH, fetch=_fetch
) -> list[SourceCheckResult]:
    state = _load_state(state_path)
    results: list[SourceCheckResult] = []

    for yaml_path in sorted(kb_root.rglob("*.yaml")):
        rel = str(yaml_path.relative_to(kb_root))
        data = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
        source_url = data.get("source_url")

        if not source_url:
            results.append(SourceCheckResult(rel, None, "NO_SOURCE_URL"))
            continue

        try:
            html = fetch(source_url)
        except Exception as exc:  # noqa: BLE001 - any fetch failure is reportable, not fatal
            results.append(SourceCheckResult(rel, source_url, "FETCH_FAILED", str(exc)))
            continue

        fp = fingerprint(html)
        previous = state.get(rel)
        checked_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

        if previous is None:
            status = "NEW"
        elif previous["fingerprint"] != fp:
            status = "CHANGED"
        else:
            status = "UNCHANGED"

        state[rel] = {
            "source_url": source_url,
            "fingerprint": fp,
            "last_checked": checked_at,
            "last_changed": checked_at if status == "CHANGED" else (previous or {}).get("last_changed"),
        }
        results.append(SourceCheckResult(rel, source_url, status))

    _save_state(state_path, state)
    return results


def _print_report(results: list[SourceCheckResult]) -> None:
    width = max(len(r.path) for r in results)
    marker = {
        "CHANGED": "!",
        "FETCH_FAILED": "?",
        "NEW": "+",
        "UNCHANGED": "ok",
        "NO_SOURCE_URL": "-",
    }
    for r in results:
        line = f"  {marker[r.status]:>4} {r.path.ljust(width)}  {r.status}"
        if r.detail:
            line += f"  ({r.detail})"
        print(line)


def main() -> int:
    results = check_all()
    _print_report(results)

    changed = [r for r in results if r.status == "CHANGED"]
    failed = [r for r in results if r.status == "FETCH_FAILED"]
    new = [r for r in results if r.status == "NEW"]

    print()
    print(
        f"{len(changed)} changed, {len(failed)} fetch failed, {len(new)} new baseline, "
        f"{len(results) - len(changed) - len(failed) - len(new)} unchanged."
    )

    if changed:
        print("\nA source page changed - go compare it against the YAML by hand.")

    # Fetch failures are common (bot-blocking, transient network issues) and
    # not evidence anything changed, so they're reported but don't fail the
    # run - only a confirmed content change does.
    return 1 if changed else 0


if __name__ == "__main__":
    sys.exit(main())
