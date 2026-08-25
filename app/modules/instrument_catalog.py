"""
Named Instrument Catalog

Hardcoded, risk-tier-scoped catalog of real-world-named Indian investment
instruments shown to NRI users. Most entries carry placeholder-flagged
ISIN/return/platform data (see PLACEHOLDER_DISCLAIMER) since we have no
verified live source for them — only Parag Parikh Flexi Cap Fund uses real,
user-confirmed figures. Danish tax notes reflect the real content already
in app/knowledge_base/denmark/tax_rules.yaml (lagerbeskatning, DTAA).

Intentionally a plain Python module, not YAML: it isn't country-scoped like
the rest of app/knowledge_base/, so it doesn't fit app/utils/kb_loader.py's
loading contract, and adding a new YAML file would break
tests/test_kb_loader.py's hardcoded knowledge-base file count.
"""
from typing import Dict, List

PLACEHOLDER_DISCLAIMER = (
    "ILLUSTRATIVE DATA — ISIN, historical returns and platform details for "
    "most instruments below are placeholders and have not been verified "
    "against a live data source. Confirm actual ISIN, NAV, expense ratio "
    "and returns with the fund house or your broker before investing."
)

LAGERBESKATNING_NOTE = (
    "Gains taxed annually under Danish lagerbeskatning rules. "
    "Report in SKAT Rubrik 38 each year."
)
FD_BOND_TAX_NOTE = (
    "Interest is taxed as Danish capital income (~37-42%) in the year it "
    "accrues. Use the DTAA credit for Indian TDS withheld to avoid double tax."
)
SGB_TAX_NOTE = (
    "SGB interest is taxable Danish capital income each year; confirm "
    "treatment of the maturity/redemption gain with a Danish tax adviser."
)
HYBRID_DEBT_TAX_NOTE = (
    "Likely subject to lagerbeskatning (mark-to-market) as a foreign fund "
    "not on SKAT's approved list — report unrealised gains in Rubrik 38 "
    "each year; confirm classification with a Danish tax adviser."
)

CATALOG: Dict[str, List[dict]] = {
    "conservative": [
        {"name": "SBI/HDFC NRE Fixed Deposit (1-3 year)", "isin": "N/A (bank deposit)",
         "category": "Fixed Deposit", "instrument_type": "nre_fd",
         "suggested_allocation_pct": 40.0, "historical_return_3yr": "6.7%", "historical_return_5yr": "6.9%",
         "risk_level_label": "Low", "min_investment_inr": 10000,
         "liquidity": "Medium (premature withdrawal penalty applies)",
         "why_nri_suitable": "Interest fully tax-exempt in India under Section 10(4); principal and interest freely repatriable.",
         "platform_to_invest": "SBI NRI Banking / HDFC / ICICI",
         "danish_tax_note": FD_BOND_TAX_NOTE},
        {"name": "RBI Floating Rate Savings Bond", "isin": "N/A (RBI bond, not ISIN-listed)",
         "category": "Government Bond", "instrument_type": "bonds",
         "suggested_allocation_pct": 20.0, "historical_return_3yr": "7.4%", "historical_return_5yr": "7.6%",
         "risk_level_label": "Low", "min_investment_inr": 1000,
         "liquidity": "Low (7-year lock-in, no premature exit except for seniors)",
         "why_nri_suitable": "Sovereign-guaranteed, rate resets every 6 months tracking NSC yield — a hedge against rate-cut risk on fixed FDs.",
         "platform_to_invest": "RBI Retail Direct",
         "danish_tax_note": FD_BOND_TAX_NOTE},
        {"name": "Nippon India Liquid Fund", "isin": "INF204K01UN3-PLACEHOLDER",
         "category": "Liquid Fund", "instrument_type": "debt_mf",
         "suggested_allocation_pct": 15.0, "historical_return_3yr": "6.1%", "historical_return_5yr": "5.8%",
         "risk_level_label": "Low", "min_investment_inr": 500,
         "liquidity": "High (T+1 redemption)",
         "why_nri_suitable": "Near-cash liquidity with better post-tax yield than a savings account for money needed within months.",
         "platform_to_invest": "Nippon India MF direct / Kuvera",
         "danish_tax_note": LAGERBESKATNING_NOTE},
        {"name": "Sovereign Gold Bond (SGB) Series", "isin": "IN0020230012-PLACEHOLDER (series-specific)",
         "category": "Gold", "instrument_type": "sgb",
         "suggested_allocation_pct": 15.0, "historical_return_3yr": "9.5%", "historical_return_5yr": "11.2%",
         "risk_level_label": "Low-Moderate", "min_investment_inr": 5000,
         "liquidity": "Low (8-year tenor; tradeable on exchange after 5 years)",
         "why_nri_suitable": "Sovereign-backed gold exposure without storage risk; note NRIs can hold but not newly subscribe to SGBs — confirm current eligibility.",
         "platform_to_invest": "RBI Retail Direct / NSE-BSE secondary market",
         "danish_tax_note": SGB_TAX_NOTE},
        {"name": "HDFC Short Duration Debt Fund", "isin": "INF179K01VW7-PLACEHOLDER",
         "category": "Debt Mutual Fund", "instrument_type": "debt_mf",
         "suggested_allocation_pct": 10.0, "historical_return_3yr": "7.2%", "historical_return_5yr": "7.5%",
         "risk_level_label": "Low-Moderate", "min_investment_inr": 5000,
         "liquidity": "High (open-ended)",
         "why_nri_suitable": "Modest yield pickup over an FD with 1-3 year duration risk, suited to near-term goals.",
         "platform_to_invest": "HDFC Securities / Kuvera",
         "danish_tax_note": LAGERBESKATNING_NOTE},
    ],
    "moderate": [
        {"name": "Parag Parikh Flexi Cap Fund (NRI eligible)", "isin": "INF879O01019",
         "category": "Equity Mutual Fund", "instrument_type": "equity_mf",
         "suggested_allocation_pct": 25.0, "historical_return_3yr": "18.5%", "historical_return_5yr": "22.1%",
         "risk_level_label": "Moderate-High", "min_investment_inr": 1000,
         "liquidity": "High (open-ended, T+3 redemption)",
         "why_nri_suitable": "Accepts NRI investments, no US/Canada restriction",
         "platform_to_invest": "MF Central / Parag Parikh AMC website",
         "danish_tax_note": LAGERBESKATNING_NOTE},
        {"name": "HDFC Balanced Advantage Fund", "isin": "INF179K01Y61-PLACEHOLDER",
         "category": "Hybrid Mutual Fund", "instrument_type": "hybrid_mf",
         "suggested_allocation_pct": 20.0, "historical_return_3yr": "13.4%", "historical_return_5yr": "14.9%",
         "risk_level_label": "Moderate", "min_investment_inr": 5000,
         "liquidity": "High (open-ended)",
         "why_nri_suitable": "Dynamically shifts equity-debt mix, smoothing volatility for NRIs who can't actively monitor Indian markets.",
         "platform_to_invest": "HDFC Securities / Kuvera",
         "danish_tax_note": HYBRID_DEBT_TAX_NOTE},
        {"name": "SBI/HDFC NRE Fixed Deposit", "isin": "N/A (bank deposit)",
         "category": "Fixed Deposit", "instrument_type": "nre_fd",
         "suggested_allocation_pct": 15.0, "historical_return_3yr": "6.7%", "historical_return_5yr": "6.9%",
         "risk_level_label": "Low", "min_investment_inr": 10000,
         "liquidity": "Medium (premature withdrawal penalty applies)",
         "why_nri_suitable": "Tax-free, fully repatriable safety allocation and emergency buffer.",
         "platform_to_invest": "SBI NRI Banking / HDFC / ICICI",
         "danish_tax_note": FD_BOND_TAX_NOTE},
        {"name": "Sovereign Gold Bond (SGB)", "isin": "IN0020230012-PLACEHOLDER (series-specific)",
         "category": "Gold", "instrument_type": "sgb",
         "suggested_allocation_pct": 15.0, "historical_return_3yr": "9.5%", "historical_return_5yr": "11.2%",
         "risk_level_label": "Low-Moderate", "min_investment_inr": 5000,
         "liquidity": "Low (8-year tenor; tradeable on exchange after 5 years)",
         "why_nri_suitable": "Inflation-hedging diversifier, low correlation to Indian equities.",
         "platform_to_invest": "RBI Retail Direct / NSE-BSE secondary market",
         "danish_tax_note": SGB_TAX_NOTE},
        {"name": "ICICI Pru Corporate Bond Fund", "isin": "INF109K01VV9-PLACEHOLDER",
         "category": "Debt Mutual Fund", "instrument_type": "debt_mf",
         "suggested_allocation_pct": 15.0, "historical_return_3yr": "7.6%", "historical_return_5yr": "7.9%",
         "risk_level_label": "Low-Moderate", "min_investment_inr": 5000,
         "liquidity": "High (open-ended)",
         "why_nri_suitable": "High-quality AAA corporate exposure adds yield over gilts while staying low-volatility.",
         "platform_to_invest": "ICICI Direct / Kuvera",
         "danish_tax_note": LAGERBESKATNING_NOTE},
        {"name": "Nippon India ETF Nifty 50", "isin": "INF204KA1S54-PLACEHOLDER",
         "category": "Equity ETF", "instrument_type": "etf",
         "suggested_allocation_pct": 10.0, "historical_return_3yr": "12.8%", "historical_return_5yr": "14.1%",
         "risk_level_label": "Moderate-High", "min_investment_inr": 1000,
         "liquidity": "High (exchange-traded)",
         "why_nri_suitable": "Low-cost, broad-market index exposure via a PIS-enabled demat account.",
         "platform_to_invest": "Any NSE/BSE-enabled NRI demat broker",
         "danish_tax_note": LAGERBESKATNING_NOTE},
    ],
    "aggressive": [
        {"name": "Mirae Asset Large Cap Fund", "isin": "INF769K01AX1-PLACEHOLDER",
         "category": "Equity Mutual Fund", "instrument_type": "equity_mf",
         "suggested_allocation_pct": 20.0, "historical_return_3yr": "15.2%", "historical_return_5yr": "17.8%",
         "risk_level_label": "Moderate-High", "min_investment_inr": 5000,
         "liquidity": "High (open-ended, T+3 redemption)",
         "why_nri_suitable": "Large-cap tilt lowers volatility versus broader flexi/mid-cap funds while capturing India's growth.",
         "platform_to_invest": "Mirae Asset direct / Kuvera",
         "danish_tax_note": LAGERBESKATNING_NOTE},
        {"name": "Parag Parikh Flexi Cap Fund", "isin": "INF879O01019",
         "category": "Equity Mutual Fund", "instrument_type": "equity_mf",
         "suggested_allocation_pct": 20.0, "historical_return_3yr": "18.5%", "historical_return_5yr": "22.1%",
         "risk_level_label": "Moderate-High", "min_investment_inr": 1000,
         "liquidity": "High (open-ended, T+3 redemption)",
         "why_nri_suitable": "Accepts NRI investments, no US/Canada restriction; built-in US equity diversification.",
         "platform_to_invest": "MF Central / Parag Parikh AMC website",
         "danish_tax_note": LAGERBESKATNING_NOTE},
        {"name": "Axis Midcap Fund", "isin": "INF846K01EW2-PLACEHOLDER",
         "category": "Equity Mutual Fund (Mid Cap)", "instrument_type": "equity_mf",
         "suggested_allocation_pct": 15.0, "historical_return_3yr": "20.6%", "historical_return_5yr": "23.4%",
         "risk_level_label": "High", "min_investment_inr": 5000,
         "liquidity": "High (open-ended, T+3 redemption)",
         "why_nri_suitable": "Higher-growth mid-cap exposure for long-horizon, high-risk-tolerance investors.",
         "platform_to_invest": "Axis MF direct / Kuvera",
         "danish_tax_note": LAGERBESKATNING_NOTE},
        {"name": "HDFC Mid-Cap Opportunities Fund", "isin": "INF179K01Y87-PLACEHOLDER",
         "category": "Equity Mutual Fund (Mid Cap)", "instrument_type": "equity_mf",
         "suggested_allocation_pct": 15.0, "historical_return_3yr": "21.3%", "historical_return_5yr": "24.0%",
         "risk_level_label": "High", "min_investment_inr": 5000,
         "liquidity": "High (open-ended, T+3 redemption)",
         "why_nri_suitable": "One of India's largest mid-cap funds by AUM; broad diversification within the mid-cap segment.",
         "platform_to_invest": "HDFC Securities / Kuvera",
         "danish_tax_note": LAGERBESKATNING_NOTE},
        {"name": "Nippon India ETF Nifty 50", "isin": "INF204KA1S54-PLACEHOLDER",
         "category": "Equity ETF", "instrument_type": "etf",
         "suggested_allocation_pct": 10.0, "historical_return_3yr": "12.8%", "historical_return_5yr": "14.1%",
         "risk_level_label": "Moderate-High", "min_investment_inr": 1000,
         "liquidity": "High (exchange-traded)",
         "why_nri_suitable": "Low-cost core index holding to anchor an otherwise high-conviction, high-risk book.",
         "platform_to_invest": "Any NSE/BSE-enabled NRI demat broker",
         "danish_tax_note": LAGERBESKATNING_NOTE},
        {"name": "Sovereign Gold Bond (SGB)", "isin": "IN0020230012-PLACEHOLDER (series-specific)",
         "category": "Gold", "instrument_type": "sgb",
         "suggested_allocation_pct": 10.0, "historical_return_3yr": "9.5%", "historical_return_5yr": "11.2%",
         "risk_level_label": "Low-Moderate", "min_investment_inr": 5000,
         "liquidity": "Low (8-year tenor; tradeable on exchange after 5 years)",
         "why_nri_suitable": "Even aggressive portfolios benefit from a small uncorrelated ballast against equity drawdowns.",
         "platform_to_invest": "RBI Retail Direct / NSE-BSE secondary market",
         "danish_tax_note": SGB_TAX_NOTE},
        {"name": "ICICI Pru Corporate Bond Fund", "isin": "INF109K01VV9-PLACEHOLDER",
         "category": "Debt Mutual Fund", "instrument_type": "debt_mf",
         "suggested_allocation_pct": 10.0, "historical_return_3yr": "7.6%", "historical_return_5yr": "7.9%",
         "risk_level_label": "Low-Moderate", "min_investment_inr": 5000,
         "liquidity": "High (open-ended)",
         "why_nri_suitable": "A minimal debt sleeve to fund near-term liquidity needs without breaking equity positions in a downturn.",
         "platform_to_invest": "ICICI Direct / Kuvera",
         "danish_tax_note": LAGERBESKATNING_NOTE},
    ],
}


def get_named_instruments(risk_tolerance: str, total_corpus_inr: float) -> List[dict]:
    """Returns the risk-tier catalog with suggested_amount_inr computed from
    total_corpus_inr. Falls back to 'moderate' for unrecognised risk tiers."""
    tier = (risk_tolerance or "moderate").lower()
    entries = CATALOG.get(tier, CATALOG["moderate"])
    result = []
    for entry in entries:
        item = dict(entry)
        item["suggested_amount_inr"] = round(total_corpus_inr * item["suggested_allocation_pct"] / 100, 2)
        result.append(item)
    return result
