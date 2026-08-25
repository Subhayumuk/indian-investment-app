# agent/agent_logic.py
from typing import Dict, Any, Optional, Tuple, List


# -----------------------------
# Multi-country reference data
# -----------------------------

# Whether India has a Double Taxation Avoidance Agreement in force with each
# supported country of tax residency. Extend this as more countries are added.
DTAA_COUNTRIES: Dict[str, bool] = {
    "Denmark": True,
    "USA": True,
    "UK": True,
    "UAE": False,
    "Singapore": True,
    "Canada": True,
    "Australia": True,
    "Germany": True,
    "Netherlands": True,
    "Sweden": True,
    "Norway": True,
    "New Zealand": True,
    "Switzerland": True,
    "France": True,
    "Japan": True,
}

# LRS = Liberalised Remittance Scheme, an RBI scheme for resident Indians
# remitting funds abroad. Not directly applicable to NRIs repatriating their
# own NRO/NRE/FCNR funds, but relevant context for family remittances.
LRS_LIMIT_USD = 250_000

# Per financial year, current income plus balances, per RBI rules.
NRO_REPATRIATION_LIMIT_USD = 1_000_000


# -----------------------------
# Utility helpers
# -----------------------------

def _to_float(value: Any, default: float = 0.0) -> float:
    """
    Safely convert form/string input to float.
    """
    if value in [None, ""]:
        return default

    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_int(value: Any, default: int = 0) -> int:
    """
    Safely convert form/string input to int.
    """
    if value in [None, ""]:
        return default

    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def _truthy_interest(val: Any) -> Tuple[bool, Optional[float]]:
    """
    Returns (has_interest, annual_interest_value_or_none).

    Treats:
    - None / "" as unknown
    - "0" as no interest
    - positive/negative numeric values as provided interest
    """
    if val is None or val == "":
        return False, None

    try:
        num = float(val)
    except (TypeError, ValueError):
        return False, None

    if num == 0:
        return False, 0.0

    return True, num


def _money_inr(amount: Any) -> str:
    value = _to_float(amount, 0)
    return f"INR {value:,.0f}"


def _money_local(amount: Any, currency: str) -> str:
    value = _to_float(amount, 0)
    return f"{currency or 'local currency'} {value:,.2f}"


def _optional_float(value: Any) -> Optional[float]:
    """Like _to_float, but returns None instead of 0.0 when unset, so a
    genuine value of 0 is not silently discarded."""
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


# -----------------------------
# Liquidity planning
# -----------------------------

def calculate_liquid_reserve(
    inputs: Dict[str, Any],
    total_india_savings: float
) -> Dict[str, Any]:
    """
    Calculates suggested liquid reserve.

    Preferred method:
    - Use monthly expenses and emergency months if provided.

    Fallback method:
    - Use simple percentage-based rules.
    """

    monthly_expenses_inr = _to_float(inputs.get("monthly_expenses_inr"), 0)
    emergency_months = _to_int(inputs.get("emergency_months"), 6)
    planned_short_term_expenses_inr = _to_float(
        inputs.get("planned_short_term_expenses_inr"),
        0,
    )

    if emergency_months <= 0:
        emergency_months = 6

    if monthly_expenses_inr > 0:
        emergency_reserve = monthly_expenses_inr * emergency_months
        suggested_liquid = emergency_reserve + planned_short_term_expenses_inr

        method = (
            f"Based on {emergency_months} months of expenses "
            f"plus planned short-term expenses."
        )

    else:
        # Fallback rule when monthly expenses are unknown.
        if total_india_savings <= 300000:
            suggested_liquid = total_india_savings
            method = (
                "Fallback rule: keep all funds liquid because total Indian "
                "savings are relatively small."
            )

        elif total_india_savings <= 1000000:
            suggested_liquid = total_india_savings * 0.35
            method = "Fallback rule: keep around 35% liquid."

        else:
            suggested_liquid = min(total_india_savings * 0.25, 1000000)
            method = "Fallback rule: keep around 25% liquid, capped at INR 10,00,000."

    suggested_liquid = min(suggested_liquid, total_india_savings)
    investable_amount = max(total_india_savings - suggested_liquid, 0)

    return {
        "suggested_liquid_reserve_inr": round(suggested_liquid, 2),
        "investable_amount_inr": round(investable_amount, 2),
        "method": method,
        "monthly_expenses_inr_used": monthly_expenses_inr,
        "emergency_months_used": emergency_months,
        "planned_short_term_expenses_inr": planned_short_term_expenses_inr,
    }


# -----------------------------
# Investment allocation
# -----------------------------

def build_investment_allocation(
    investable_amount: float,
    risk_profile: str,
    investment_horizon_years: int,
) -> List[Dict[str, Any]]:
    """
    Creates simple model allocation based on:
    - risk profile
    - investment horizon

    This is educational and not personalized financial advice.
    """

    risk_profile = _normalize_text(risk_profile) or "moderate"

    if investable_amount <= 0:
        return []

    short_horizon = investment_horizon_years > 0 and investment_horizon_years < 3

    if short_horizon:
        allocation = [
            {
                "investment_type": "Savings / Liquid Fund / Short-term FD",
                "percentage": 55,
                "reason": "Short investment horizon; capital stability is more important.",
            },
            {
                "investment_type": "Fixed Deposits",
                "percentage": 30,
                "reason": "Predictable return and lower volatility.",
            },
            {
                "investment_type": "Conservative Hybrid Mutual Funds",
                "percentage": 15,
                "reason": "Limited growth exposure with lower volatility than pure equity.",
            },
        ]

    elif risk_profile == "conservative":
        allocation = [
            {
                "investment_type": "Fixed Deposits",
                "percentage": 40,
                "reason": "Capital preservation and predictable income.",
            },
            {
                "investment_type": "Debt Mutual Funds",
                "percentage": 30,
                "reason": "Debt exposure with potential tax/reporting complexity in Denmark.",
            },
            {
                "investment_type": "Conservative Hybrid Mutual Funds",
                "percentage": 20,
                "reason": "Small equity exposure with reduced volatility.",
            },
            {
                "investment_type": "Large-cap Equity Mutual Funds",
                "percentage": 10,
                "reason": "Long-term growth allocation at limited exposure.",
            },
        ]

    elif risk_profile == "aggressive":
        allocation = [
            {
                "investment_type": "Equity Mutual Funds",
                "percentage": 55,
                "reason": "Long-term growth; suitable only if volatility is acceptable.",
            },
            {
                "investment_type": "Index Funds / ETFs",
                "percentage": 20,
                "reason": "Diversified market exposure, usually at lower cost.",
            },
            {
                "investment_type": "Direct Indian Shares",
                "percentage": 10,
                "reason": "Higher-risk satellite allocation only if you understand equity risk.",
            },
            {
                "investment_type": "Hybrid Mutual Funds",
                "percentage": 10,
                "reason": "Diversification between equity and debt.",
            },
            {
                "investment_type": "Fixed Deposits",
                "percentage": 5,
                "reason": "Stability buffer.",
            },
        ]

    else:
        # Moderate default
        allocation = [
            {
                "investment_type": "Equity Mutual Funds",
                "percentage": 35,
                "reason": "Long-term growth through diversified equity exposure.",
            },
            {
                "investment_type": "Index Funds / ETFs",
                "percentage": 20,
                "reason": "Broad market exposure and diversification.",
            },
            {
                "investment_type": "Fixed Deposits",
                "percentage": 20,
                "reason": "Predictable return and lower volatility.",
            },
            {
                "investment_type": "Hybrid Mutual Funds",
                "percentage": 15,
                "reason": "Balanced exposure to equity and debt.",
            },
            {
                "investment_type": "Debt Mutual Funds",
                "percentage": 10,
                "reason": "Lower volatility than equity, but tax treatment must be checked.",
            },
        ]

    for item in allocation:
        item["amount_inr"] = round(
            investable_amount * item["percentage"] / 100,
            2,
        )

    return allocation


# -----------------------------
# Denmark tax/reporting logic
# -----------------------------

def build_denmark_tax_actions(
    dk_residency: str,
    dk_prev_declared: str,
    india_account_type: str,
    investment_allocation: List[Dict[str, Any]],
    india_interest_has: bool,
    india_interest_value: Optional[float],
    india_withholding_info: Any,
    country: str = "Denmark",
    currency: str = "DKK",
) -> List[Dict[str, Any]]:
    """
    Creates residency-country reporting/tax action list.
    This is intentionally cautious and high-level.

    Historically Denmark-specific (hence the function/field names), now
    generalized to any country of tax residency via the `country`/`currency`
    parameters.
    """

    country = country or "Denmark"
    currency = currency or "DKK"

    dk_residency_norm = _normalize_text(dk_residency)
    prev_declared_norm = _normalize_text(dk_prev_declared)
    account_type_norm = _normalize_text(india_account_type)

    is_dk_tax_resident = dk_residency_norm in [
        "tax_resident",
        "tax resident",
        "yes",
        "resident",
        "denmark tax resident",
        "dk tax resident",
    ]

    actions = []

    if is_dk_tax_resident:
        actions.append({
            "area": "Worldwide income",
            "declare_in_denmark": True,
            "what_to_declare": (
                "Relevant worldwide income, including Indian interest, "
                "dividends and capital gains where applicable."
            ),
            "action": (
                f"Include Indian income/returns in your {country} tax reporting "
                f"process using {currency} conversion."
            ),
        })

        actions.append({
            "area": "Foreign bank accounts/assets",
            "declare_in_denmark": True,
            "what_to_declare": (
                f"Indian bank accounts, balances and income depending on "
                f"{country} reporting requirements."
            ),
            "action": (
                "Keep bank statements, year-end balances, interest certificates "
                "and ownership details."
            ),
        })

        if india_interest_has:
            actions.append({
                "area": "Interest income",
                "declare_in_denmark": True,
                "what_to_declare": (
                    f"Indian interest income of approximately "
                    f"INR {india_interest_value:,.0f}."
                ),
                "action": (
                    f"Convert INR interest to {currency} using a consistent/relevant "
                    f"exchange rate and report under the correct {country} category."
                ),
            })
        else:
            actions.append({
                "area": "Interest income",
                "declare_in_denmark": "Check",
                "what_to_declare": (
                    "Interest amount was not provided or was indicated as zero."
                ),
                "action": (
                    f"Confirm actual annual interest from Indian bank statements "
                    f"before filing in {country}."
                ),
            })

        if india_withholding_info not in [None, "", "Unknown", "unknown"]:
            actions.append({
                "area": "Foreign tax credit / double taxation",
                "declare_in_denmark": "Possibly",
                "what_to_declare": (
                    "Indian withholding tax/TDS may be relevant for double-taxation relief."
                ),
                "action": (
                    f"Keep TDS certificates/Form 16A and ask whether foreign tax "
                    f"credit can be claimed in {country}."
                ),
            })

        if prev_declared_norm in ["no", "not declared", "false"]:
            actions.append({
                "area": "Prior-year correction",
                "declare_in_denmark": "Review needed",
                "what_to_declare": (
                    "Previously undeclared Indian accounts/assets/income may "
                    "require correction."
                ),
                "action": (
                    f"Consider contacting your local tax authority or a qualified "
                    f"tax adviser in {country} to assess whether past filings "
                    f"need correction."
                ),
            })

    else:
        actions.append({
            "area": "Tax residency uncertainty",
            "declare_in_denmark": "Depends",
            "what_to_declare": (
                f"{country} declaration obligations depend on whether you are "
                f"tax resident or otherwise taxable in {country}."
            ),
            "action": (
                f"Confirm your {country} tax residency status before deciding "
                f"reporting obligations."
            ),
        })

    # Account-specific residency-country notes
    if "nro" in account_type_norm:
        actions.append({
            "area": "NRO account",
            "declare_in_denmark": is_dk_tax_resident,
            "what_to_declare": (
                f"NRO interest and income may be taxable in India and "
                f"reportable in {country} if you are tax resident there."
            ),
            "action": "Keep Indian TDS documentation and interest certificates.",
        })

    if "nre" in account_type_norm:
        actions.append({
            "area": "NRE account",
            "declare_in_denmark": is_dk_tax_resident,
            "what_to_declare": (
                f"NRE interest may be exempt in India for eligible NRIs, but "
                f"{country} may still tax/report it for its tax residents."
            ),
            "action": (
                f"Do not assume Indian exemption means {country} exemption. "
                f"Verify {country} reporting treatment."
            ),
        })

    if "fcnr" in account_type_norm:
        actions.append({
            "area": "FCNR account",
            "declare_in_denmark": is_dk_tax_resident,
            "what_to_declare": (
                f"Foreign currency deposit balance and interest may need "
                f"{country} reporting."
            ),
            "action": f"Track both INR/foreign currency value and {currency} conversion.",
        })

    # Investment-specific residency-country notes
    for allocation in investment_allocation:
        inv_type = allocation["investment_type"]

        if "Fixed Deposits" in inv_type or "Short-term FD" in inv_type:
            actions.append({
                "area": "Indian fixed deposits",
                "declare_in_denmark": is_dk_tax_resident,
                "what_to_declare": "FD interest income and deposit balance.",
                "action": (
                    f"Track interest accrual/receipt, TDS if any, maturity "
                    f"proceeds and {currency} conversion."
                ),
            })

        elif (
            "Equity Mutual Funds" in inv_type
            or "Index Funds" in inv_type
            or "ETFs" in inv_type
        ):
            actions.append({
                "area": "Indian equity mutual funds / ETFs",
                "declare_in_denmark": is_dk_tax_resident,
                "what_to_declare": (
                    f"Holdings, dividends/distributions, realized gains/losses "
                    f"and potentially annual taxation depending on {country} classification."
                ),
                "action": (
                    f"Check {country} tax classification of foreign funds before "
                    f"investing. {country} rules for foreign funds can be complex."
                ),
            })

        elif "Debt Mutual Funds" in inv_type:
            actions.append({
                "area": "Indian debt mutual funds",
                "declare_in_denmark": is_dk_tax_resident,
                "what_to_declare": "Holdings, distributions and gains/losses.",
                "action": (
                    f"Review {country} taxation carefully; debt/investment fund "
                    f"classification may affect timing and category of taxation."
                ),
            })

        elif "Hybrid Mutual Funds" in inv_type:
            actions.append({
                "area": "Indian hybrid mutual funds",
                "declare_in_denmark": is_dk_tax_resident,
                "what_to_declare": (
                    "Holdings, dividends/distributions, gains/losses and fund classification."
                ),
                "action": (
                    f"Check whether {country} treats the fund as equity-based, "
                    f"bond-based or another category."
                ),
            })

        elif "Direct Indian Shares" in inv_type:
            actions.append({
                "area": "Direct Indian shares",
                "declare_in_denmark": is_dk_tax_resident,
                "what_to_declare": (
                    "Share holdings, dividends and realized capital gains/losses."
                ),
                "action": (
                    f"Maintain trade contract notes, dividend statements, cost "
                    f"basis and sale records in {currency} terms."
                ),
            })

    return actions


# -----------------------------
# FEMA compliance
# -----------------------------

def build_fema_compliance(
    india_account_type: str,
    wants_repatriation: bool,
    repatriation_amount_inr: Optional[float],
) -> List[str]:
    """
    High-level FEMA (Foreign Exchange Management Act) compliance notes
    covering repatriation rules for NRE/NRO/FCNR accounts.
    """

    account_type_norm = _normalize_text(india_account_type)

    notes = [
        (
            f"LRS (Liberalised Remittance Scheme) limit is USD {LRS_LIMIT_USD:,} "
            "per financial year. This governs resident Indians remitting funds "
            "abroad and is generally not a cap on an NRI repatriating their own "
            "NRE/NRO/FCNR funds, but is relevant if family in India is remitting "
            "funds to you."
        ),
        "NRE account balances (principal and interest) are freely and fully repatriable outside India, with no RBI limit.",
        (
            f"NRO account repatriation is capped at USD {NRO_REPATRIATION_LIMIT_USD:,} "
            "per financial year (current income plus balances), subject to "
            "submission of Form 15CA/15CB and payment of applicable Indian taxes."
        ),
        "FCNR (Foreign Currency Non-Resident) deposits are freely repatriable in the deposit currency, both principal and interest.",
    ]

    if wants_repatriation:
        if repatriation_amount_inr:
            notes.append(
                f"You indicated a desired repatriation of approximately "
                f"{_money_inr(repatriation_amount_inr)}. Confirm the source "
                f"account type (NRE/NRO/FCNR), since repatriation limits and "
                f"documentation requirements differ by account."
            )
        else:
            notes.append(
                "You indicated you want to repatriate funds but did not specify "
                "an amount. Provide an estimated amount so limits (e.g. the "
                "NRO account's USD 1,000,000/year cap) can be checked."
            )

        if "nro" in account_type_norm:
            notes.append(
                "Since you hold an NRO account, repatriation requires a "
                "Chartered Accountant certificate (Form 15CB) and remitter "
                "declaration (Form 15CA) before the bank processes the transfer."
            )

    return notes


# -----------------------------
# DTAA benefits
# -----------------------------

def build_dtaa_benefits(tax_residency_country: str) -> List[str]:
    """
    Notes on Double Taxation Avoidance Agreement status/benefits between
    India and the user's country of tax residency.
    """

    country = (tax_residency_country or "Denmark").strip()
    has_dtaa = DTAA_COUNTRIES.get(country)

    if has_dtaa is None:
        return [
            f"DTAA status between India and {country} is not in our reference "
            f"list; verify directly whether a Double Taxation Avoidance "
            f"Agreement exists.",
            "If a DTAA exists, you may be able to claim a foreign tax credit "
            "or a reduced withholding rate on Indian-sourced income; confirm "
            "with a local tax adviser.",
        ]

    if has_dtaa:
        return [
            f"India and {country} have a Double Taxation Avoidance Agreement (DTAA) in force.",
            (
                f"You may be able to claim a foreign tax credit in {country} "
                "for Indian TDS paid on NRO interest, mutual fund gains or "
                "dividends, avoiding double taxation on the same income."
            ),
            (
                "The DTAA may also provide reduced withholding tax rates versus "
                "the domestic Indian rate; check the relevant treaty article and "
                "submit Form 10F plus a Tax Residency Certificate (TRC) to the "
                "Indian payer to claim the treaty rate at source."
            ),
            f"Keep TDS certificates (Form 16A) as evidence when claiming foreign tax credit in {country}.",
        ]

    return [
        f"India and {country} do not currently have a Double Taxation Avoidance Agreement (DTAA) in force.",
        (
            "Indian-sourced income will generally be taxed in India at "
            f"domestic rates without treaty relief; check whether {country} "
            "provides unilateral foreign tax credit instead."
        ),
        f"Confirm with a tax adviser in {country} how Indian TDS is treated for local tax purposes without a DTAA.",
    ]


# -----------------------------
# TDS summary
# -----------------------------

def build_tds_summary(
    india_account_type: str,
    has_mutual_funds: bool,
    mutual_fund_value_inr: Optional[float],
    has_stocks: bool,
    stocks_value_inr: Optional[float],
) -> List[str]:
    """
    Reference TDS (Tax Deducted at Source) rates applicable in India for the
    account types and asset classes the user reported.
    """

    account_type_norm = _normalize_text(india_account_type)
    summary = []

    if "nre" in account_type_norm:
        summary.append("NRE account interest: 0% tax in India (exempt for qualifying NRIs).")

    if "fcnr" in account_type_norm:
        summary.append("FCNR deposit interest: exempt from Indian tax for qualifying NRIs, similar to NRE treatment.")

    if "nro" in account_type_norm or not account_type_norm or account_type_norm == "unknown":
        summary.append("NRO account interest: 30% TDS deducted at source in India (plus applicable surcharge/cess).")

    if has_mutual_funds:
        value_text = (
            f" on your holding of approximately {_money_inr(mutual_fund_value_inr)}"
            if mutual_fund_value_inr else ""
        )
        summary.append(
            f"Mutual fund gains{value_text}: long-term capital gains taxed at "
            "20%, short-term capital gains taxed at 30% (verify current-year "
            "rates and indexation rules before filing)."
        )

    if has_stocks:
        value_text = (
            f" on your holding of approximately {_money_inr(stocks_value_inr)}"
            if stocks_value_inr else ""
        )
        summary.append(
            f"Direct equity/stock gains{value_text}: long-term capital gains "
            "(holding period over 1 year) taxed at 10% above an INR 1,00,000 "
            "exemption per year; short-term capital gains taxed at 15%."
        )

    if not summary:
        summary.append(
            "No specific TDS category identified from the provided accounts/"
            "holdings; provide account type (NRE/NRO/FCNR) and asset holdings "
            "for a precise TDS summary."
        )

    return summary


# -----------------------------
# Investment recommendations (narrative)
# -----------------------------

def build_investment_recommendations(
    investment_allocation: List[Dict[str, Any]],
    has_mutual_funds: bool,
    mutual_fund_value_inr: Optional[float],
    has_stocks: bool,
    stocks_value_inr: Optional[float],
    has_property: bool,
    property_value_inr: Optional[float],
    tax_residency_country: str,
) -> List[str]:
    """
    Narrative (sentence-form) version of the investment allocation table,
    plus notes on any existing mutual fund/stock/property holdings.
    """

    country = tax_residency_country or "Denmark"
    recommendations = []

    for item in investment_allocation:
        recommendations.append(
            f"Allocate {item['percentage']}% (~{_money_inr(item['amount_inr'])}) "
            f"to {item['investment_type']}: {item['reason']}"
        )

    if has_mutual_funds and mutual_fund_value_inr:
        recommendations.append(
            f"You already hold approximately {_money_inr(mutual_fund_value_inr)} "
            f"in Indian mutual funds; review the fund category (equity/debt/"
            f"hybrid) and confirm how {country} taxes foreign mutual fund "
            f"holdings before adding further investment."
        )

    if has_stocks and stocks_value_inr:
        recommendations.append(
            f"You already hold approximately {_money_inr(stocks_value_inr)} in "
            "direct Indian shares; track cost basis and holding period in INR "
            "for LTCG/STCG classification."
        )

    if has_property and property_value_inr:
        recommendations.append(
            f"You hold Indian property valued at approximately "
            f"{_money_inr(property_value_inr)}; rental income and eventual "
            "capital gains on sale are taxable in India regardless of NRI "
            "status, and TDS under Section 195 applies to the buyer when an "
            "NRI sells property."
        )

    if not recommendations:
        recommendations.append(
            "No investable surplus or existing holdings identified for recommendations."
        )

    return recommendations


# -----------------------------
# India tax notes
# -----------------------------

def build_india_tax_notes(
    india_account_type: str,
    india_withholding_info: Any,
    investment_allocation: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Creates Indian tax notes.
    """

    account_type_norm = _normalize_text(india_account_type)

    notes = []

    if "nre" in account_type_norm:
        notes.append({
            "area": "NRE savings / NRE FD",
            "india_tax_treatment": (
                "Often exempt from Indian tax for qualifying NRIs."
            ),
            "action": "Verify NRI eligibility and account status. Keep interest certificates.",
        })

    elif "nro" in account_type_norm:
        notes.append({
            "area": "NRO savings / NRO FD",
            "india_tax_treatment": (
                "Interest is generally taxable in India and may be subject to TDS."
            ),
            "action": (
                "Keep TDS certificates/Form 16A and include income in Indian "
                "tax filing if required."
            ),
        })

    elif "fcnr" in account_type_norm:
        notes.append({
            "area": "FCNR deposits",
            "india_tax_treatment": (
                "Can have favourable Indian tax treatment for eligible NRIs."
            ),
            "action": "Verify eligibility and maintain deposit/interest documents.",
        })

    else:
        notes.append({
            "area": "Indian bank account",
            "india_tax_treatment": (
                "Tax treatment depends on whether the account is NRE, NRO, "
                "FCNR or resident account."
            ),
            "action": "Confirm correct NRI account classification.",
        })

    if india_withholding_info not in [None, "", "Unknown", "unknown"]:
        notes.append({
            "area": "Indian withholding/TDS",
            "india_tax_treatment": (
                f"User provided withholding/TDS info: {india_withholding_info}"
            ),
            "action": (
                "Keep proof of tax deducted, because it may be relevant in both "
                "India and Denmark."
            ),
        })

    investment_types = [
        item["investment_type"] for item in investment_allocation
    ]

    if any("Fixed Deposits" in x or "Short-term FD" in x for x in investment_types):
        notes.append({
            "area": "Indian fixed deposits",
            "india_tax_treatment": (
                "NRO FD interest is generally taxable/TDS applicable; NRE FD "
                "interest may be exempt for eligible NRIs."
            ),
            "action": (
                "Choose FD type carefully: NRE vs NRO has different Indian tax "
                "and repatriation implications."
            ),
        })

    if any(
        "Equity Mutual Funds" in x or "Index Funds" in x or "ETFs" in x
        for x in investment_types
    ):
        notes.append({
            "area": "Indian equity mutual funds",
            "india_tax_treatment": (
                "Indian taxation may involve capital gains rules and possible "
                "tax on dividends/distributions."
            ),
            "action": (
                "Check latest Indian rules for equity fund taxation before investing."
            ),
        })

    if any("Debt Mutual Funds" in x for x in investment_types):
        notes.append({
            "area": "Indian debt mutual funds",
            "india_tax_treatment": (
                "Indian tax treatment of debt funds can differ from equity funds "
                "and has changed over time."
            ),
            "action": "Verify latest Indian tax rules before investment.",
        })

    if any("Direct Indian Shares" in x for x in investment_types):
        notes.append({
            "area": "Direct Indian shares",
            "india_tax_treatment": (
                "Dividends and capital gains may be taxable in India depending "
                "on rules and treaty positions."
            ),
            "action": (
                "Maintain purchase/sale records, dividend statements and tax "
                "deduction documents."
            ),
        })

    return notes


# -----------------------------
# Follow-up questions
# -----------------------------

def build_follow_up_questions(inputs: Dict[str, Any]) -> List[str]:
    questions = []

    if not inputs.get("monthly_expenses_inr"):
        questions.append(
            "What are your average monthly expenses or emergency cash requirement in INR/DKK?"
        )

    if not inputs.get("investment_horizon_years"):
        questions.append(
            "What is your investment horizon: less than 3 years, 3–7 years, or more than 7 years?"
        )

    if not inputs.get("risk_profile"):
        questions.append(
            "What is your risk profile: conservative, moderate or aggressive?"
        )

    if not inputs.get("india_interest_in_inr"):
        questions.append(
            "What was the exact annual interest earned in India for the relevant tax year?"
        )

    questions.extend([
        "Are the Indian accounts NRE, NRO, FCNR or resident accounts?",
        "Are the accounts solely owned or jointly owned?",
        "Which Danish tax year does this apply to?",
        "Do you have TDS certificates/Form 16A from India?",
        "Do you already file Indian income tax returns as an NRI?",
        "Do you want the portfolio optimized for safety, income, tax simplicity or long-term growth?",
    ])

    return questions


# -----------------------------
# Display text builder
# -----------------------------

def build_display_text(result: Dict[str, Any]) -> str:
    inputs = result["inputs_interpreted"]
    liquidity = result["liquidity_plan"]
    allocation = result["investment_recommendation"]
    dk_actions = result["denmark_tax_actions"]
    india_notes = result["india_tax_notes"]
    fema_compliance = result["fema_compliance"]
    dtaa_benefits = result["dtaa_benefits"]
    tds_summary = result["tds_summary"]
    investment_recommendations = result["investment_recommendations"]

    country = inputs.get("tax_residency_country") or "Denmark"
    currency = inputs.get("tax_residency_currency") or "DKK"

    lines = []

    lines.append(f"## 🇮🇳 NRI India Savings, Investment & {country} Tax Planning Summary")
    lines.append("")

    lines.append("### 📌 Important disclaimer")
    lines.append("- This is general educational information only.")
    lines.append("- It is not tax, legal or investment advice.")
    lines.append(f"- {country} taxation of foreign funds, shares and bank income can be complex.")
    lines.append(f"- Please confirm with a qualified tax adviser in {country} and an Indian tax adviser before acting.")
    lines.append("")

    lines.append("### 🧾 1) Inputs understood")
    lines.append(f"- Tax residency country: `{country}` (`{currency}`)")
    lines.append(f"- {country} residency status: `{inputs.get('dk_residency')}`")
    lines.append(f"- Previously declared Indian/foreign accounts in {country}: `{inputs.get('dk_prev_declared_foreign_accounts')}`")
    lines.append(f"- Indian account type: `{inputs.get('india_account_type')}`")
    lines.append(f"- Indian principal amount reviewed: **{_money_inr(inputs.get('india_principal_inr', 0))}**")
    lines.append(f"- Indian annual interest: `{inputs.get('india_annual_interest_inr')}`")
    lines.append(f"- Indian withholding/TDS info: `{inputs.get('india_withholding_info')}`")
    lines.append(f"- Mutual funds: `{inputs.get('has_mutual_funds')}` ({_money_inr(inputs.get('mutual_fund_value_inr', 0))})")
    lines.append(f"- Stocks: `{inputs.get('has_stocks')}` ({_money_inr(inputs.get('stocks_value_inr', 0))})")
    lines.append(f"- Property: `{inputs.get('has_property')}` ({_money_inr(inputs.get('property_value_inr', 0))})")
    lines.append(f"- Total India assets reviewed: **{_money_inr(inputs.get('total_india_assets_inr', 0))}** (~{_money_local(inputs.get('total_india_assets_local'), currency)})")
    lines.append(f"- Risk profile: `{inputs.get('risk_profile')}`")
    lines.append(f"- Investment horizon: `{inputs.get('investment_horizon_years')} years`")
    lines.append("")

    lines.append("### 💰 2) Liquidity recommendation")
    lines.append(f"- Suggested liquid reserve: **{_money_inr(liquidity['suggested_liquid_reserve_inr'])}**")
    lines.append(f"- Potential investable amount: **{_money_inr(liquidity['investable_amount_inr'])}**")
    lines.append(f"- Method used: {liquidity['method']}")
    lines.append("")

    lines.append("### 📊 3) Suggested India investment allocation")
    if allocation:
        for item in allocation:
            lines.append(
                f"- **{item['investment_type']}**: "
                f"{item['percentage']}% ≈ **{_money_inr(item['amount_inr'])}**"
            )
            lines.append(f"  - Reason: {item['reason']}")
    else:
        lines.append("- No investable surplus identified after keeping liquid reserve.")
    lines.append("")

    lines.append("### 💡 4) Investment recommendations")
    for line in investment_recommendations:
        lines.append(f"- {line}")
    lines.append("")

    lines.append("### 🌍 5) FEMA compliance & repatriation")
    for line in fema_compliance:
        lines.append(f"- {line}")
    lines.append("")

    lines.append(f"### 🤝 6) DTAA benefits (India ↔ {country})")
    for line in dtaa_benefits:
        lines.append(f"- {line}")
    lines.append("")

    lines.append("### 🧮 7) TDS summary")
    for line in tds_summary:
        lines.append(f"- {line}")
    lines.append("")

    lines.append(f"### 🌐 8) {country} tax/reporting implications and actions")
    for action in dk_actions:
        lines.append(f"- **{action['area']}**")
        lines.append(f"  - Declare in {country}: `{action['declare_in_denmark']}`")
        lines.append(f"  - What to declare/check: {action['what_to_declare']}")
        lines.append(f"  - Action: {action['action']}")
    lines.append("")

    lines.append("### 🇮🇳 9) India tax notes")
    for note in india_notes:
        lines.append(f"- **{note['area']}**")
        lines.append(f"  - India tax treatment: {note['india_tax_treatment']}")
        lines.append(f"  - Action: {note['action']}")
    lines.append("")

    lines.append("### 🛠️ 10) Practical documents to keep")
    lines.append("- Indian bank statements")
    lines.append("- Interest certificates")
    lines.append("- TDS certificates/Form 16A, if applicable")
    lines.append("- Mutual fund statements/CAS")
    lines.append("- Share contract notes")
    lines.append("- Dividend statements")
    lines.append("- Purchase/sale dates and values")
    lines.append(f"- INR to {currency} exchange-rate evidence")
    lines.append(f"- Prior {country} tax filing records")
    lines.append("")

    lines.append("### 🧠 11) Questions for better accuracy")
    for question in result["follow_up_questions"]:
        lines.append(f"- {question}")

    return "\n".join(lines)


# -----------------------------
# Main function called by FastAPI
# -----------------------------

def analyze_tax(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main function called by main.py.

    Returns:
    - display_text
    - structured result
    - liquidity recommendation
    - investment allocation
    - Denmark reporting actions
    - India tax notes
    """

    # -----------------------------
    # Extract inputs
    # -----------------------------
    dk_residency = inputs.get("dk_residency")
    dk_capital_income = inputs.get("dk_capital_income")
    dk_prev_declared = inputs.get("dk_prev_declared")

    india_account_type = inputs.get("india_account_type")
    india_amount = _to_float(inputs.get("india_amount_in_inr"), 0)

    india_interest_raw = inputs.get("india_interest_in_inr")
    india_withholding_info = inputs.get("india_withholding_info")

    risk_profile = inputs.get("risk_profile", "moderate")
    investment_horizon_years = _to_int(
        inputs.get("investment_horizon_years"),
        5,
    )

    india_interest_has, india_interest_value = _truthy_interest(india_interest_raw)

    # -----------------------------
    # Multi-country tax residency inputs
    # -----------------------------
    tax_residency_country = inputs.get("tax_residency_country") or "Denmark"
    tax_residency_currency = inputs.get("tax_residency_currency") or "DKK"
    exchange_rate_to_inr = _to_float(inputs.get("exchange_rate_to_inr"), 0.0)

    has_mutual_funds = bool(inputs.get("has_mutual_funds"))
    mutual_fund_value_inr = _optional_float(
        inputs.get("india_mutual_fund_value_inr", inputs.get("mutual_fund_value_inr"))
    )

    has_stocks = bool(inputs.get("has_stocks"))
    stocks_value_inr = _optional_float(
        inputs.get("india_stocks_value_inr", inputs.get("stocks_value_inr"))
    )

    has_property = bool(inputs.get("has_property"))
    property_value_inr = _optional_float(
        inputs.get("india_property_value_inr", inputs.get("property_value_inr"))
    )

    wants_repatriation = bool(inputs.get("wants_repatriation"))
    repatriation_amount_inr = _optional_float(inputs.get("repatriation_amount_inr"))

    total_india_assets_inr = (
        india_amount
        + (mutual_fund_value_inr or 0)
        + (stocks_value_inr or 0)
        + (property_value_inr or 0)
    )
    total_india_assets_local = (
        total_india_assets_inr / exchange_rate_to_inr if exchange_rate_to_inr > 0 else 0
    )

    # -----------------------------
    # Confidence / unknown handling
    # -----------------------------
    withholding_known = india_withholding_info not in [
        None,
        "",
        "Unknown",
        "unknown",
    ]

    withholding_confidence = "high" if withholding_known else "low"

    interest_confidence = "high" if india_interest_has else (
        "low" if india_interest_raw in [None, ""] else "medium"
    )

    if india_interest_value == 0:
        interest_confidence = "medium"

    # -----------------------------
    # Liquidity plan
    # -----------------------------
    liquidity_plan = calculate_liquid_reserve(
        inputs=inputs,
        total_india_savings=india_amount,
    )

    investable_amount = liquidity_plan["investable_amount_inr"]

    # -----------------------------
    # Investment recommendation
    # -----------------------------
    investment_recommendation = build_investment_allocation(
        investable_amount=investable_amount,
        risk_profile=risk_profile,
        investment_horizon_years=investment_horizon_years,
    )

    # -----------------------------
    # Denmark tax/reporting actions
    # -----------------------------
    denmark_tax_actions = build_denmark_tax_actions(
        dk_residency=dk_residency,
        dk_prev_declared=dk_prev_declared,
        india_account_type=india_account_type,
        investment_allocation=investment_recommendation,
        india_interest_has=india_interest_has,
        india_interest_value=india_interest_value,
        india_withholding_info=india_withholding_info,
        country=tax_residency_country,
        currency=tax_residency_currency,
    )

    # -----------------------------
    # India tax notes
    # -----------------------------
    india_tax_notes = build_india_tax_notes(
        india_account_type=india_account_type,
        india_withholding_info=india_withholding_info,
        investment_allocation=investment_recommendation,
    )

    # -----------------------------
    # FEMA compliance, DTAA benefits, TDS summary, investment recommendations
    # -----------------------------
    fema_compliance = build_fema_compliance(
        india_account_type=india_account_type,
        wants_repatriation=wants_repatriation,
        repatriation_amount_inr=repatriation_amount_inr,
    )

    dtaa_benefits = build_dtaa_benefits(tax_residency_country)

    tds_summary = build_tds_summary(
        india_account_type=india_account_type,
        has_mutual_funds=has_mutual_funds,
        mutual_fund_value_inr=mutual_fund_value_inr,
        has_stocks=has_stocks,
        stocks_value_inr=stocks_value_inr,
    )

    investment_recommendations = build_investment_recommendations(
        investment_allocation=investment_recommendation,
        has_mutual_funds=has_mutual_funds,
        mutual_fund_value_inr=mutual_fund_value_inr,
        has_stocks=has_stocks,
        stocks_value_inr=stocks_value_inr,
        has_property=has_property,
        property_value_inr=property_value_inr,
        tax_residency_country=tax_residency_country,
    )

    # -----------------------------
    # Structured result
    # -----------------------------
    structured_result: Dict[str, Any] = {
        "inputs_interpreted": {
            "dk_residency": dk_residency,
            "dk_capital_income_dkk": dk_capital_income,
            "dk_prev_declared_foreign_accounts": dk_prev_declared,
            "tax_residency_country": tax_residency_country,
            "tax_residency_currency": tax_residency_currency,
            "exchange_rate_to_inr": exchange_rate_to_inr,
            "india_account_type": india_account_type,
            "india_principal_inr": india_amount,
            "india_interest_received_selected": bool(india_interest_has),
            "india_annual_interest_inr": india_interest_value,
            "india_withholding_info": india_withholding_info,
            "has_mutual_funds": has_mutual_funds,
            "mutual_fund_value_inr": mutual_fund_value_inr,
            "has_stocks": has_stocks,
            "stocks_value_inr": stocks_value_inr,
            "has_property": has_property,
            "property_value_inr": property_value_inr,
            "total_india_assets_inr": total_india_assets_inr,
            "total_india_assets_local": total_india_assets_local,
            "wants_repatriation": wants_repatriation,
            "repatriation_amount_inr": repatriation_amount_inr,
            "risk_profile": risk_profile,
            "investment_horizon_years": investment_horizon_years,
            "monthly_expenses_inr": _to_float(inputs.get("monthly_expenses_inr"), 0),
            "emergency_months": _to_int(inputs.get("emergency_months"), 6),
            "planned_short_term_expenses_inr": _to_float(
                inputs.get("planned_short_term_expenses_inr"),
                0,
            ),
        },
        "confidence": {
            "interest": interest_confidence,
            "withholding": withholding_confidence,
        },
        "summary": (
            f"This is a tax-aware NRI investment planning summary for Indian "
            f"savings with {tax_residency_country} reporting considerations."
        ),
        "liquidity_plan": liquidity_plan,
        "investment_recommendation": investment_recommendation,
        "allocation": investment_recommendation,
        "denmark_tax_actions": denmark_tax_actions,
        "india_tax_notes": india_tax_notes,
        "fema_compliance": fema_compliance,
        "dtaa_benefits": dtaa_benefits,
        "tds_summary": tds_summary,
        "investment_recommendations": investment_recommendations,
        "follow_up_questions": build_follow_up_questions(inputs),
        "assumptions_used": [
            "Assumption: the user wants general educational guidance, not regulated financial advice.",
            f"Assumption: {tax_residency_country} tax residency is decisive for worldwide income reporting.",
            "Assumption: Indian tax treatment depends heavily on whether the account is NRE, NRO or FCNR.",
            f"Assumption: {tax_residency_country} treatment of Indian mutual funds/shares should be verified before investment.",
        ],
        "warnings": [
            "This is not tax, legal or investment advice.",
            "Tax laws change and depend on personal facts.",
            f"{tax_residency_country} taxation of foreign investment funds can be complex.",
            f"Check with a qualified tax adviser in {tax_residency_country} and an Indian tax adviser before acting.",
        ],
        "disclaimer": (
            "This is general educational information only and should not be "
            "treated as personalized tax, legal or investment advice."
        ),
    }

    structured_result["display_text"] = build_display_text(structured_result)

    return structured_result