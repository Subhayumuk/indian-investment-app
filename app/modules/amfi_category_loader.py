"""Cached loader for app/knowledge_base/amfi_category_index.json - the
committed, deduped (Direct-Growth only) AMFI scheme index that
scripts/refresh_amfi_category_index.py regenerates monthly via
.github/workflows/fund-category-refresh.yml.

Same "read a committed data file at process start, no request-time network
call" pattern app/utils/kb_loader.py already uses for the YAML knowledge
base - this file is JSON instead only because its content (thousands of
scheme rows) doesn't fit that module's per-country YAML layout.

Not yet consumed anywhere - this is E1 groundwork for E2's per-category
fund shortlists (see the Phase E plan). Doesn't exist until the first
refresh workflow run commits it, so load_amfi_category_index() returns an
empty dict rather than raising when the file is missing, letting any
future caller degrade gracefully instead of crashing the app.
"""
import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict

INDEX_PATH = Path(__file__).resolve().parent.parent / "knowledge_base" / "amfi_category_index.json"


@lru_cache(maxsize=1)
def load_amfi_category_index() -> Dict[str, Dict[str, Any]]:
    """Returns {scheme_code: {name, amc, category, isin}}, or {} if the
    index hasn't been generated yet (first refresh workflow run pending)."""
    if not INDEX_PATH.exists():
        return {}
    with INDEX_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)
