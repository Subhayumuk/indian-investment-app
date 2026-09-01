"""
Benchmark Engine

Builds the PeerBenchmark half of a Holdings Review by reusing
RecommendationEngine._build_portfolio_health rather than recomputing the
asset-breakdown/recommended-allocation numbers a second time - that
scoring logic already exists, is tested, and drives the main
recommendation flow's PortfolioHealthCard; duplicating it here would be
two places that could silently drift apart.
"""
from types import SimpleNamespace
from typing import Optional

from app.models.holdings_review import PeerBenchmark
from app.modules.recommendation_engine import RecommendationEngine

_HORIZON_LABELS = [
    (3, "short-term"),
    (7, "medium-term"),
]


def _horizon_label(years: int) -> str:
    for threshold, label in _HORIZON_LABELS:
        if years <= threshold:
            return label
    return "long-term"


def _cohort_description(flat: SimpleNamespace) -> str:
    risk = (flat.risk_tolerance or "moderate").capitalize()
    years = flat.investment_horizon_years or 0
    country = (flat.tax_residency_country or "your country").title()
    return f"{risk}-risk NRIs in {country} with a {_horizon_label(years)} ({years}-year) horizon"


class BenchmarkEngine:
    def __init__(self, recommendation_engine: Optional[RecommendationEngine] = None):
        # Deliberately reaches into RecommendationEngine's "private"
        # (leading-underscore) _build_portfolio_health rather than
        # re-deriving the scoring logic - see module docstring.
        self._recommendation_engine = recommendation_engine or RecommendationEngine()

    def build_benchmark(self, flat: SimpleNamespace) -> PeerBenchmark:
        health = self._recommendation_engine._build_portfolio_health(flat)
        return PeerBenchmark(
            cohort_description=_cohort_description(flat),
            recommended_allocation=health.recommended_allocation,
            your_allocation=health.asset_breakdown,
        )
