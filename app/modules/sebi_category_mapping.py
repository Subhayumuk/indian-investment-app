"""
Maps AMFI's official SEBI scheme-category strings (captured from
NAVAll.txt's category-header lines - see amfi_nav_client.py's
_CATEGORY_HEADER_RE) onto this app's own asset-class buckets: the same
equity/debt/gold/hybrid values app/modules/holdings_review_engine.py's
_infer_asset_class already produces from a name-keyword guess, and that
ASSET_CLASS_RETURN in app/modules/recommendation_engine.py already has
benchmark returns for.

AMFI's own taxonomy has ~36+ granular SEBI categories (Large Cap Fund,
Debt Scheme - Banking and PSU Fund, Children's Fund, ...) - collapsing
that onto four buckets is this app's own judgment call, same spirit as
ASSET_CLASS_RETURN's benchmark numbers already being disclosed as such,
not something SEBI itself defines. Only 15 of the 98 live category
strings confirmed on 2026-09-03 (a spike run's sample output) were seen
directly; the rest of this table is built from the well-documented 2017
SEBI mutual fund recategorisation taxonomy, not independently re-verified
line-by-line against the live file - refine against
app/knowledge_base/amfi_category_index.json (see
scripts/refresh_amfi_category_index.py) once E1 ships and captures the
real, complete set of 98 strings.

classify_sebi_category() returns None for a category string it doesn't
recognise, rather than guessing - callers should fall back to the
existing name-keyword heuristic in that case, never invent false
confidence from an unmapped string.
"""
from typing import List, Optional, Tuple

# Order matters: checked top to bottom, first match wins. More specific
# phrases (e.g. "balanced advantage") are listed before broader ones
# (e.g. "hybrid") only where both could otherwise match the same string.
_KEYWORD_RULES: List[Tuple[str, str]] = [
    ("gold", "gold"),
    ("silver", "gold"),  # AMFI groups precious-metal ETFs/FoFs together; no separate bucket here
    ("balanced advantage", "hybrid"),
    ("balanced hybrid", "hybrid"),
    ("conservative hybrid", "hybrid"),
    ("aggressive hybrid", "hybrid"),
    ("equity savings", "hybrid"),
    ("arbitrage", "hybrid"),
    ("multi asset", "hybrid"),
    ("hybrid", "hybrid"),
    ("children", "hybrid"),  # solution-oriented children's funds are typically equity+debt mixes
    ("retirement", "hybrid"),  # same reasoning as children's funds above
    # Liquid/overnight/money-market funds map to "debt" (not a separate
    # "cash" bucket) to match _infer_asset_class's existing keyword-guess
    # output space exactly - see holdings_review_engine.py's _DEBT_KEYWORDS,
    # which already treats these as debt for the same reason.
    ("debt scheme", "debt"),
    ("liquid fund", "debt"),
    ("overnight fund", "debt"),
    ("money market fund", "debt"),
    ("gilt", "debt"),
    ("equity scheme", "equity"),
    ("index fund", "equity"),  # most AMFI index funds track equity indices; a debt/gold index fund would be misclassified here - unconfirmed edge case, see module docstring
    ("etf", "equity"),  # same caveat as index funds above; gold/silver ETFs are caught by the "gold"/"silver" rules earlier since order matters
]


def classify_sebi_category(category: Optional[str]) -> Optional[str]:
    """Best-effort mapping from an AMFI SEBI category string to this app's
    asset-class bucket. Returns None (never a guess) for anything
    unrecognised - the caller decides the fallback."""
    if not category:
        return None
    c = category.lower()
    for keyword, asset_class in _KEYWORD_RULES:
        if keyword in c:
            return asset_class
    return None
