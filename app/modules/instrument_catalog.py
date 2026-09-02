"""
Named Instrument Catalog

Hardcoded, risk-tier-scoped catalog of real-world-named Indian investment
instruments shown to NRI users. Most entries carry placeholder-flagged
ISIN/return/platform data (see PLACEHOLDER_DISCLAIMER) since we have no
verified live source for them — only Parag Parikh Flexi Cap Fund uses real,
user-confirmed figures.

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

# Instrument types that are actually funds (as opposed to a bank deposit,
# government bond, or SGB) - several countries' tax treatment of Indian
# mutual funds specifically (PFIC, offshore-fund rules, lagerbeskatning)
# doesn't apply the same way to a plain FD or sovereign bond.
_FUND_INSTRUMENT_TYPES = {"equity_mf", "debt_mf", "hybrid_mf", "etf"}

# Denmark's fund note - revised 2026-09-02 after the original version
# incorrectly implied equity-vs-debt composition changes whether annual
# mark-to-market tax applies. Researched (not assumed) against skat.dk and
# corroborating sources: Danish tax law's realisationsprincip/aktieindkomst
# treatment only applies to funds on Skattestyrelsen's "positive list" of
# approved equity-based investment companies (>=50% equity, self-notified
# to SKAT) - Indian AMC funds are not on that list. Absent that listing,
# lagerbeskatning (annual mark-to-market) as kapitalindkomst is the default
# for a foreign investeringsselskab REGARDLESS of its own equity/debt mix -
# so the same note now applies to equity, debt, and hybrid funds alike,
# rather than treating equity as exempt. This is still secondary research,
# not a primary legal reading - the note says so and points to a Danish
# adviser rather than asserting a specific rate/classification.
_DENMARK_FUND_NOTE = (
    "Indian mutual funds aren't on Skattestyrelsen's 'positive list' of approved "
    "equity-based investment companies, so gains are very likely taxed annually "
    "under lagerbeskatning (mark-to-market, whether or not you sell) as "
    "kapitalindkomst - this generally applies the same way whether the fund is "
    "equity, debt, or a mix internally, since the listing (not the fund's own "
    "composition) is what normally unlocks the more favourable aktieindkomst/"
    "realisation treatment. Report in SKAT Rubrik 38 each year. Confirm your "
    "specific fund's classification with a Danish tax adviser - this area of "
    "Danish tax law has real edge cases."
)
_DENMARK_FD_BOND_NOTE = (
    "Interest is taxed as Danish capital income (~37-42%) in the year it "
    "accrues. Use the DTAA credit for Indian TDS withheld to avoid double tax."
)
_DENMARK_SGB_NOTE = (
    "SGB interest is taxable Danish capital income each year; confirm "
    "treatment of the maturity/redemption gain with a Danish tax adviser."
)


def _denmark_note(instrument_type: str) -> str:
    if instrument_type in ("nre_fd", "nro_fd", "bonds"):
        return _DENMARK_FD_BOND_NOTE
    if instrument_type == "sgb":
        return _DENMARK_SGB_NOTE
    return _DENMARK_FUND_NOTE


def _usa_note(is_fund: bool) -> str:
    # Informed by app/knowledge_base/usa/tax_rules.yaml's critical_warnings
    # (PFIC/FBAR/FATCA) - written as static prose here, not read live, same
    # as the other _*_note functions below (see residence_tax_note's
    # docstring for why).
    if is_fund:
        return (
            "Indian mutual funds are classified as PFICs under US tax law — taxation is "
            "punitive (excess distribution method or a mark-to-market election), and most "
            "Indian AMCs won't accept US-resident investments at all. Consider US-listed "
            "India ETFs (e.g. INDA, INDY) or direct equity via a PIS account instead."
        )
    return (
        "Report Indian accounts over $10,000 aggregate on FBAR (FinCEN 114), and assets "
        "over $50,000 on Form 8938 (FATCA)."
    )


def _uk_note(is_fund: bool) -> str:
    # Informed by app/knowledge_base/uk/tax_rules.yaml (offshore-fund note,
    # DTAA rate). The 15% is the DTAA treaty withholding rate, not an
    # Indian domestic capital-gains rate - treaty rates change only when
    # the treaty itself is renegotiated, unlike India's Budget-driven
    # domestic rates (which the 2026-08-27 audit already found stale
    # elsewhere) - deliberately not quoting any of those here.
    if is_fund:
        return (
            "May fall under HMRC's 'offshore fund' rules, which can tax gains as income "
            "rather than capital gains — this is genuinely complex; get specific advice "
            "before investing via a fund structure."
        )
    return (
        "NRE/NRO interest is taxable in the UK; a DTAA credit is available for the "
        "Indian TDS withheld (up to 15%)."
    )


def _germany_note() -> str:
    # Informed by app/knowledge_base/germany/tax_rules.yaml (Abgeltungsteuer
    # is German domestic law, stable; the 10% DTAA rate is treaty-fixed).
    return (
        "Taxed under Germany's flat Abgeltungsteuer (~26.375% incl. solidarity surcharge) "
        "as investment income; a DTAA credit is available for Indian TDS withheld "
        "(10% on NRO interest)."
    )


def _australia_note(is_fund: bool) -> str:
    # Informed by app/knowledge_base/australia/tax_rules.yaml (CGT discount
    # is Australian domestic law; the 15% DTAA rate is treaty-fixed).
    note = (
        "Taxable in Australia; a DTAA credit is available for Indian TDS withheld "
        "(15% on NRO interest)."
    )
    if is_fund:
        note += " Assets held over 12 months may qualify for Australia's 50% CGT discount."
    return note


def _singapore_note() -> str:
    # Informed by app/knowledge_base/singapore/tax_rules.yaml.
    return (
        "Singapore has no capital gains tax, and foreign-sourced income not remitted to "
        "Singapore is generally not taxable — typically the most tax-efficient of your "
        "residence options for this. NRO interest may be taxable if remitted; confirm with "
        "a Singapore tax adviser."
    )


def _canada_note(is_fund: bool) -> str:
    # Informed by app/knowledge_base/canada/tax_rules.yaml's critical_warnings.
    if is_fund:
        return (
            "Indian mutual funds face PFIC-like foreign investment entity rules in Canada, "
            "and most AMCs restrict Canadian-resident investment. NRE FD, FCNR, or direct "
            "equity via a PIS account are the recommended alternatives. Report foreign "
            "assets over CAD 100,000 on Form T1135."
        )
    return "Report foreign assets over CAD 100,000 on Form T1135; a DTAA credit is generally available."


def _uae_note() -> str:
    # Informed by app/knowledge_base/uae/tax_rules.yaml.
    return (
        "UAE has no personal income tax — India's TDS is your final tax on this "
        "investment, with no additional UAE tax on top."
    )


def residence_tax_note(country: str, instrument_type: str) -> str:
    """What this investment means in the user's *country of residence*'s tax
    system — one static, hand-written note per country (informed by that
    country's app/knowledge_base/<country>/tax_rules.yaml, not read from it
    live), covering all 8 supported residence countries instead of only
    Denmark. Deliberately avoids quoting India-side domestic rates (capital
    gains/TDS %), since those are the volatile, Budget-driven numbers the
    2026-08-27 audit already found stale in one file and never checked in
    the other 8 - only destination-country domestic rates and DTAA treaty
    rates (which move far less often) appear here. Falls back to a generic
    pointer for any country not modeled below."""
    c = (country or "").lower()
    is_fund = instrument_type in _FUND_INSTRUMENT_TYPES

    if c == "denmark":
        return _denmark_note(instrument_type)
    if c == "usa":
        return _usa_note(is_fund)
    if c == "uk":
        return _uk_note(is_fund)
    if c == "germany":
        return _germany_note()
    if c == "australia":
        return _australia_note(is_fund)
    if c == "singapore":
        return _singapore_note()
    if c == "canada":
        return _canada_note(is_fund)
    if c == "uae":
        return _uae_note()
    return "Confirm the tax treatment of this investment with a tax adviser in your country of residence."

CATALOG: Dict[str, List[dict]] = {
    "conservative": [
        {"name": "SBI/HDFC NRE Fixed Deposit (1-3 year)", "isin": "N/A (bank deposit)",
         "category": "Fixed Deposit", "instrument_type": "nre_fd",
         "suggested_allocation_pct": 40.0, "historical_return_3yr": "6.7%", "historical_return_5yr": "6.9%",
         "risk_level_label": "Low", "min_investment_inr": 10000,
         "liquidity": "Medium (premature withdrawal penalty applies)",
         "why_nri_suitable": "Interest fully tax-exempt in India under Section 10(4); principal and interest freely repatriable.",
         "platform_to_invest": "SBI NRI Banking / HDFC / ICICI"},
        {"name": "RBI Floating Rate Savings Bond", "isin": "N/A (RBI bond, not ISIN-listed)",
         "category": "Government Bond", "instrument_type": "bonds",
         "suggested_allocation_pct": 20.0, "historical_return_3yr": "7.4%", "historical_return_5yr": "7.6%",
         "risk_level_label": "Low", "min_investment_inr": 1000,
         "liquidity": "Low (7-year lock-in, no premature exit except for seniors)",
         "why_nri_suitable": "Sovereign-guaranteed, rate resets every 6 months tracking NSC yield — a hedge against rate-cut risk on fixed FDs.",
         "platform_to_invest": "RBI Retail Direct"},
        {"name": "Nippon India Liquid Fund", "isin": "INF204K01UN3-PLACEHOLDER",
         "category": "Liquid Fund", "instrument_type": "debt_mf",
         "suggested_allocation_pct": 15.0, "historical_return_3yr": "6.1%", "historical_return_5yr": "5.8%",
         "risk_level_label": "Low", "min_investment_inr": 500,
         "liquidity": "High (T+1 redemption)",
         "why_nri_suitable": "Near-cash liquidity with better post-tax yield than a savings account for money needed within months.",
         "platform_to_invest": "Nippon India MF direct / Kuvera"},
        {"name": "Sovereign Gold Bond (SGB) Series", "isin": "IN0020230012-PLACEHOLDER (series-specific)",
         "category": "Gold", "instrument_type": "sgb",
         "suggested_allocation_pct": 15.0, "historical_return_3yr": "9.5%", "historical_return_5yr": "11.2%",
         "risk_level_label": "Low-Moderate", "min_investment_inr": 5000,
         "liquidity": "Low (8-year tenor; tradeable on exchange after 5 years)",
         "why_nri_suitable": "Sovereign-backed gold exposure without storage risk; note NRIs can hold but not newly subscribe to SGBs — confirm current eligibility.",
         "platform_to_invest": "RBI Retail Direct / NSE-BSE secondary market"},
        {"name": "HDFC Short Duration Debt Fund", "isin": "INF179K01VW7-PLACEHOLDER",
         "category": "Debt Mutual Fund", "instrument_type": "debt_mf",
         "suggested_allocation_pct": 10.0, "historical_return_3yr": "7.2%", "historical_return_5yr": "7.5%",
         "risk_level_label": "Low-Moderate", "min_investment_inr": 5000,
         "liquidity": "High (open-ended)",
         "why_nri_suitable": "Modest yield pickup over an FD with 1-3 year duration risk, suited to near-term goals.",
         "platform_to_invest": "HDFC Securities / Kuvera"},
    ],
    "moderate": [
        {"name": "Parag Parikh Flexi Cap Fund (NRI eligible)", "isin": "INF879O01019",
         "category": "Equity Mutual Fund", "instrument_type": "equity_mf",
         "suggested_allocation_pct": 25.0, "historical_return_3yr": "18.5%", "historical_return_5yr": "22.1%",
         "risk_level_label": "Moderate-High", "min_investment_inr": 1000,
         "liquidity": "High (open-ended, T+3 redemption)",
         "why_nri_suitable": "Accepts NRI investments, no US/Canada restriction",
         "platform_to_invest": "MF Central / Parag Parikh AMC website"},
        {"name": "HDFC Balanced Advantage Fund", "isin": "INF179K01Y61-PLACEHOLDER",
         "category": "Hybrid Mutual Fund", "instrument_type": "hybrid_mf",
         "suggested_allocation_pct": 20.0, "historical_return_3yr": "13.4%", "historical_return_5yr": "14.9%",
         "risk_level_label": "Moderate", "min_investment_inr": 5000,
         "liquidity": "High (open-ended)",
         "why_nri_suitable": "Dynamically shifts equity-debt mix, smoothing volatility for NRIs who can't actively monitor Indian markets.",
         "platform_to_invest": "HDFC Securities / Kuvera"},
        {"name": "SBI/HDFC NRE Fixed Deposit", "isin": "N/A (bank deposit)",
         "category": "Fixed Deposit", "instrument_type": "nre_fd",
         "suggested_allocation_pct": 15.0, "historical_return_3yr": "6.7%", "historical_return_5yr": "6.9%",
         "risk_level_label": "Low", "min_investment_inr": 10000,
         "liquidity": "Medium (premature withdrawal penalty applies)",
         "why_nri_suitable": "Tax-free, fully repatriable safety allocation and emergency buffer.",
         "platform_to_invest": "SBI NRI Banking / HDFC / ICICI"},
        {"name": "Sovereign Gold Bond (SGB)", "isin": "IN0020230012-PLACEHOLDER (series-specific)",
         "category": "Gold", "instrument_type": "sgb",
         "suggested_allocation_pct": 15.0, "historical_return_3yr": "9.5%", "historical_return_5yr": "11.2%",
         "risk_level_label": "Low-Moderate", "min_investment_inr": 5000,
         "liquidity": "Low (8-year tenor; tradeable on exchange after 5 years)",
         "why_nri_suitable": "Inflation-hedging diversifier, low correlation to Indian equities.",
         "platform_to_invest": "RBI Retail Direct / NSE-BSE secondary market"},
        {"name": "ICICI Pru Corporate Bond Fund", "isin": "INF109K01VV9-PLACEHOLDER",
         "category": "Debt Mutual Fund", "instrument_type": "debt_mf",
         "suggested_allocation_pct": 15.0, "historical_return_3yr": "7.6%", "historical_return_5yr": "7.9%",
         "risk_level_label": "Low-Moderate", "min_investment_inr": 5000,
         "liquidity": "High (open-ended)",
         "why_nri_suitable": "High-quality AAA corporate exposure adds yield over gilts while staying low-volatility.",
         "platform_to_invest": "ICICI Direct / Kuvera"},
        {"name": "Nippon India ETF Nifty 50", "isin": "INF204KA1S54-PLACEHOLDER",
         "category": "Equity ETF", "instrument_type": "etf",
         "suggested_allocation_pct": 10.0, "historical_return_3yr": "12.8%", "historical_return_5yr": "14.1%",
         "risk_level_label": "Moderate-High", "min_investment_inr": 1000,
         "liquidity": "High (exchange-traded)",
         "why_nri_suitable": "Low-cost, broad-market index exposure via a PIS-enabled demat account.",
         "platform_to_invest": "Any NSE/BSE-enabled NRI demat broker"},
    ],
    "aggressive": [
        {"name": "Mirae Asset Large Cap Fund", "isin": "INF769K01AX1-PLACEHOLDER",
         "category": "Equity Mutual Fund", "instrument_type": "equity_mf",
         "suggested_allocation_pct": 20.0, "historical_return_3yr": "15.2%", "historical_return_5yr": "17.8%",
         "risk_level_label": "Moderate-High", "min_investment_inr": 5000,
         "liquidity": "High (open-ended, T+3 redemption)",
         "why_nri_suitable": "Large-cap tilt lowers volatility versus broader flexi/mid-cap funds while capturing India's growth.",
         "platform_to_invest": "Mirae Asset direct / Kuvera"},
        {"name": "Parag Parikh Flexi Cap Fund", "isin": "INF879O01019",
         "category": "Equity Mutual Fund", "instrument_type": "equity_mf",
         "suggested_allocation_pct": 20.0, "historical_return_3yr": "18.5%", "historical_return_5yr": "22.1%",
         "risk_level_label": "Moderate-High", "min_investment_inr": 1000,
         "liquidity": "High (open-ended, T+3 redemption)",
         "why_nri_suitable": "Accepts NRI investments, no US/Canada restriction; built-in US equity diversification.",
         "platform_to_invest": "MF Central / Parag Parikh AMC website"},
        {"name": "Axis Midcap Fund", "isin": "INF846K01EW2-PLACEHOLDER",
         "category": "Equity Mutual Fund (Mid Cap)", "instrument_type": "equity_mf",
         "suggested_allocation_pct": 15.0, "historical_return_3yr": "20.6%", "historical_return_5yr": "23.4%",
         "risk_level_label": "High", "min_investment_inr": 5000,
         "liquidity": "High (open-ended, T+3 redemption)",
         "why_nri_suitable": "Higher-growth mid-cap exposure for long-horizon, high-risk-tolerance investors.",
         "platform_to_invest": "Axis MF direct / Kuvera"},
        {"name": "HDFC Mid-Cap Opportunities Fund", "isin": "INF179K01Y87-PLACEHOLDER",
         "category": "Equity Mutual Fund (Mid Cap)", "instrument_type": "equity_mf",
         "suggested_allocation_pct": 15.0, "historical_return_3yr": "21.3%", "historical_return_5yr": "24.0%",
         "risk_level_label": "High", "min_investment_inr": 5000,
         "liquidity": "High (open-ended, T+3 redemption)",
         "why_nri_suitable": "One of India's largest mid-cap funds by AUM; broad diversification within the mid-cap segment.",
         "platform_to_invest": "HDFC Securities / Kuvera"},
        {"name": "Nippon India ETF Nifty 50", "isin": "INF204KA1S54-PLACEHOLDER",
         "category": "Equity ETF", "instrument_type": "etf",
         "suggested_allocation_pct": 10.0, "historical_return_3yr": "12.8%", "historical_return_5yr": "14.1%",
         "risk_level_label": "Moderate-High", "min_investment_inr": 1000,
         "liquidity": "High (exchange-traded)",
         "why_nri_suitable": "Low-cost core index holding to anchor an otherwise high-conviction, high-risk book.",
         "platform_to_invest": "Any NSE/BSE-enabled NRI demat broker"},
        {"name": "Sovereign Gold Bond (SGB)", "isin": "IN0020230012-PLACEHOLDER (series-specific)",
         "category": "Gold", "instrument_type": "sgb",
         "suggested_allocation_pct": 10.0, "historical_return_3yr": "9.5%", "historical_return_5yr": "11.2%",
         "risk_level_label": "Low-Moderate", "min_investment_inr": 5000,
         "liquidity": "Low (8-year tenor; tradeable on exchange after 5 years)",
         "why_nri_suitable": "Even aggressive portfolios benefit from a small uncorrelated ballast against equity drawdowns.",
         "platform_to_invest": "RBI Retail Direct / NSE-BSE secondary market"},
        {"name": "ICICI Pru Corporate Bond Fund", "isin": "INF109K01VV9-PLACEHOLDER",
         "category": "Debt Mutual Fund", "instrument_type": "debt_mf",
         "suggested_allocation_pct": 10.0, "historical_return_3yr": "7.6%", "historical_return_5yr": "7.9%",
         "risk_level_label": "Low-Moderate", "min_investment_inr": 5000,
         "liquidity": "High (open-ended)",
         "why_nri_suitable": "A minimal debt sleeve to fund near-term liquidity needs without breaking equity positions in a downturn.",
         "platform_to_invest": "ICICI Direct / Kuvera"},
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
