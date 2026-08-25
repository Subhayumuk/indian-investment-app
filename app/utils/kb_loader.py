"""Cached loader for the app/knowledge_base/ YAML reference data."""

from functools import lru_cache
from pathlib import Path
from typing import Any, Dict

import yaml

KB_ROOT = Path(__file__).resolve().parent.parent / "knowledge_base"


@lru_cache(maxsize=None)
def load_kb_file(country: str, filename: str) -> Dict[str, Any]:
    """Load and cache a single knowledge base YAML file.

    Example: load_kb_file("india", "nri_taxation.yaml")
    """
    path = KB_ROOT / country.lower() / filename
    if not path.exists():
        raise FileNotFoundError(f"Knowledge base file not found: {path}")

    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def load_india_kb(filename: str) -> Dict[str, Any]:
    """Convenience wrapper for the india/ knowledge base."""
    return load_kb_file("india", filename)


def load_country_tax_rules(country: str) -> Dict[str, Any]:
    """Load a residency country's tax_rules.yaml.

    Denmark additionally has india_dtaa.yaml; every supported residency
    country has a tax_rules.yaml following this same layout.
    """
    return load_kb_file(country, "tax_rules.yaml")
