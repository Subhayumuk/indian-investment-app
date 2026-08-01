# agent/agent_logic.py
from typing import Dict, Any, Optional, Tuple, List


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
) -> List[Dict[str, Any]]:
    """
    Creates Denmark reporting/tax action list.
    This is intentionally cautious and high-level.
    """

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
                "Include Indian income/returns in the Danish tax reporting "
                "process using DKK conversion."
            ),
        })

        actions.append({
            "area": "Foreign bank accounts/assets",
            "declare_in_denmark": True,
            "what_to_declare": (
                "Indian bank accounts, balances and income depending on Danish "
                "reporting requirements."
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
                    "Convert INR interest to DKK using a consistent/relevant "
                    "exchange rate and report under the correct Danish category."
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
                    "Confirm actual annual interest from Indian bank statements "
                    "before filing in Denmark."
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
                    "Keep TDS certificates/Form 16A and ask whether foreign tax "
                    "credit can be claimed in Denmark."
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
                    "Consider contacting SKAT or a Danish tax adviser to assess "
                    "whether past Danish tax filings need correction."
                ),
            })

    else:
        actions.append({
            "area": "Tax residency uncertainty",
            "declare_in_denmark": "Depends",
            "what_to_declare": (
                "Danish declaration obligations depend on whether you are tax "
                "resident or otherwise taxable in Denmark."
            ),
            "action": (
                "Confirm Danish tax residency status before deciding reporting obligations."
            ),
        })

    # Account-specific Denmark notes
    if "nro" in account_type_norm:
        actions.append({
            "area": "NRO account",
            "declare_in_denmark": is_dk_tax_resident,
            "what_to_declare": (
                "NRO interest and income may be taxable in India and reportable "
                "in Denmark if Danish tax resident."
            ),
            "action": "Keep Indian TDS documentation and interest certificates.",
        })

    if "nre" in account_type_norm:
        actions.append({
            "area": "NRE account",
            "declare_in_denmark": is_dk_tax_resident,
            "what_to_declare": (
                "NRE interest may be exempt in India for eligible NRIs, but "
                "Denmark may still tax/report it for Danish tax residents."
            ),
            "action": (
                "Do not assume Indian exemption means Danish exemption. Verify "
                "Danish reporting treatment."
            ),
        })

    if "fcnr" in account_type_norm:
        actions.append({
            "area": "FCNR account",
            "declare_in_denmark": is_dk_tax_resident,
            "what_to_declare": (
                "Foreign currency deposit balance and interest may need Danish reporting."
            ),
            "action": "Track both INR/foreign currency value and DKK conversion.",
        })

    # Investment-specific Denmark notes
    for allocation in investment_allocation:
        inv_type = allocation["investment_type"]

        if "Fixed Deposits" in inv_type or "Short-term FD" in inv_type:
            actions.append({
                "area": "Indian fixed deposits",
                "declare_in_denmark": is_dk_tax_resident,
                "what_to_declare": "FD interest income and deposit balance.",
                "action": (
                    "Track interest accrual/receipt, TDS if any, maturity "
                    "proceeds and DKK conversion."
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
                    "Holdings, dividends/distributions, realized gains/losses "
                    "and potentially annual taxation depending on Danish classification."
                ),
                "action": (
                    "Check Danish tax classification of foreign funds before investing. "
                    "Danish rules for foreign funds can be complex."
                ),
            })

        elif "Debt Mutual Funds" in inv_type:
            actions.append({
                "area": "Indian debt mutual funds",
                "declare_in_denmark": is_dk_tax_resident,
                "what_to_declare": "Holdings, distributions and gains/losses.",
                "action": (
                    "Review Danish taxation carefully; debt/investment fund "
                    "classification may affect timing and category of taxation."
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
                    "Check whether Denmark treats the fund as equity-based, "
                    "bond-based or another category."
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
                    "Maintain trade contract notes, dividend statements, cost "
                    "basis and sale records in DKK terms."
                ),
            })

    return actions


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

    lines = []

    lines.append("## 🇮🇳🇩🇰 NRI India Savings, Investment & Denmark Tax Planning Summary")
    lines.append("")

    lines.append("### 📌 Important disclaimer")
    lines.append("- This is general educational information only.")
    lines.append("- It is not tax, legal or investment advice.")
    lines.append("- Danish taxation of foreign funds, shares and bank income can be complex.")
    lines.append("- Please confirm with a qualified Danish tax adviser and Indian tax adviser before acting.")
    lines.append("")

    lines.append("### 🧾 1) Inputs understood")
    lines.append(f"- Denmark residency status: `{inputs.get('dk_residency')}`")
    lines.append(f"- Previously declared Indian/foreign accounts in Denmark: `{inputs.get('dk_prev_declared_foreign_accounts')}`")
    lines.append(f"- Indian account type: `{inputs.get('india_account_type')}`")
    lines.append(f"- Indian amount reviewed: **{_money_inr(inputs.get('india_principal_inr', 0))}**")
    lines.append(f"- Indian annual interest: `{inputs.get('india_annual_interest_inr')}`")
    lines.append(f"- Indian withholding/TDS info: `{inputs.get('india_withholding_info')}`")
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

    lines.append("### 🇩🇰 4) Denmark tax/reporting implications and actions")
    for action in dk_actions:
        lines.append(f"- **{action['area']}**")
        lines.append(f"  - Declare in Denmark: `{action['declare_in_denmark']}`")
        lines.append(f"  - What to declare/check: {action['what_to_declare']}")
        lines.append(f"  - Action: {action['action']}")
    lines.append("")

    lines.append("### 🇮🇳 5) India tax notes")
    for note in india_notes:
        lines.append(f"- **{note['area']}**")
        lines.append(f"  - India tax treatment: {note['india_tax_treatment']}")
        lines.append(f"  - Action: {note['action']}")
    lines.append("")

    lines.append("### 🛠️ 6) Practical documents to keep")
    lines.append("- Indian bank statements")
    lines.append("- Interest certificates")
    lines.append("- TDS certificates/Form 16A, if applicable")
    lines.append("- Mutual fund statements/CAS")
    lines.append("- Share contract notes")
    lines.append("- Dividend statements")
    lines.append("- Purchase/sale dates and values")
    lines.append("- INR to DKK exchange-rate evidence")
    lines.append("- Prior Danish tax filing records")
    lines.append("")

    lines.append("### 🧠 7) Questions for better accuracy")
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
    # Structured result
    # -----------------------------
    structured_result: Dict[str, Any] = {
        "inputs_interpreted": {
            "dk_residency": dk_residency,
            "dk_capital_income_dkk": dk_capital_income,
            "dk_prev_declared_foreign_accounts": dk_prev_declared,
            "india_account_type": india_account_type,
            "india_principal_inr": india_amount,
            "india_interest_received_selected": bool(india_interest_has),
            "india_annual_interest_inr": india_interest_value,
            "india_withholding_info": india_withholding_info,
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
            "This is a tax-aware NRI investment planning summary for Indian "
            "savings with Denmark reporting considerations."
        ),
        "liquidity_plan": liquidity_plan,
        "investment_recommendation": investment_recommendation,
        "denmark_tax_actions": denmark_tax_actions,
        "india_tax_notes": india_tax_notes,
        "follow_up_questions": build_follow_up_questions(inputs),
        "assumptions_used": [
            "Assumption: the user wants general educational guidance, not regulated financial advice.",
            "Assumption: Denmark tax residency is decisive for worldwide income reporting.",
            "Assumption: Indian tax treatment depends heavily on whether the account is NRE, NRO or FCNR.",
            "Assumption: Danish treatment of Indian mutual funds/shares should be verified before investment.",
        ],
        "warnings": [
            "This is not tax, legal or investment advice.",
            "Tax laws change and depend on personal facts.",
            "Danish taxation of foreign investment funds can be complex.",
            "Check with SKAT/a Danish tax adviser and an Indian tax adviser before acting.",
        ],
        "disclaimer": (
            "This is general educational information only and should not be "
            "treated as personalized tax, legal or investment advice."
        ),
    }

    structured_result["display_text"] = build_display_text(structured_result)

    return structured_result