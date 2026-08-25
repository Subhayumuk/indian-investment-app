from typing import Any


def _to_float(value: Any, default: float = 0.0) -> float:
    if value in (None, ""):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def adapt_planner_inputs(inputs: dict[str, Any]) -> dict[str, Any]:
    """
    Map API/frontend field names to the keys expected by agent_logic.analyze_tax.

    Preserves original keys so downstream formatting still works.
    """
    adapted = dict(inputs)

    if "tax_resident_denmark" in inputs and "dk_residency" not in inputs:
        adapted["dk_residency"] = (
            "tax_resident" if inputs.get("tax_resident_denmark") else "non_resident"
        )

    if "declares_india_income_in_denmark" in inputs and "dk_prev_declared" not in inputs:
        declared = inputs.get("declares_india_income_in_denmark")
        adapted["dk_prev_declared"] = "yes" if declared else "no"

    if "india_account_type" not in inputs:
        account_labels = []
        if inputs.get("has_nre_account"):
            account_labels.append("NRE")
        if inputs.get("has_nro_account"):
            account_labels.append("NRO")
        if inputs.get("has_fcnr_account"):
            account_labels.append("FCNR")
        adapted["india_account_type"] = (
            " / ".join(account_labels) if account_labels else "Unknown"
        )

    if "india_principal_inr" in inputs and "india_amount_in_inr" not in inputs:
        adapted["india_amount_in_inr"] = inputs.get("india_principal_inr")

    if "india_annual_interest_inr" in inputs and "india_interest_in_inr" not in inputs:
        adapted["india_interest_in_inr"] = inputs.get("india_annual_interest_inr")

    if "indian_tds_percent" in inputs and "india_withholding_info" not in inputs:
        tds = inputs.get("indian_tds_percent")
        if tds is not None:
            adapted["india_withholding_info"] = f"{tds}% TDS"

    if "monthly_expenses_dkk" in inputs and "monthly_expenses_inr" not in inputs:
        rate = _to_float(inputs.get("inr_to_dkk_rate"), 0.083)
        expenses_dkk = _to_float(inputs.get("monthly_expenses_dkk"), 0.0)
        if expenses_dkk > 0 and rate > 0:
            adapted["monthly_expenses_inr"] = expenses_dkk / rate

    if "dk_capital_income_dkk" in inputs and "dk_capital_income" not in inputs:
        adapted["dk_capital_income"] = inputs.get("dk_capital_income_dkk")

    # Multi-country investment holdings: map to the "india_*_value_inr"
    # naming convention agent_logic already uses for India-side amounts.
    if "mutual_fund_value_inr" in inputs and "india_mutual_fund_value_inr" not in inputs:
        adapted["india_mutual_fund_value_inr"] = inputs.get("mutual_fund_value_inr")

    if "stocks_value_inr" in inputs and "india_stocks_value_inr" not in inputs:
        adapted["india_stocks_value_inr"] = inputs.get("stocks_value_inr")

    if "property_value_inr" in inputs and "india_property_value_inr" not in inputs:
        adapted["india_property_value_inr"] = inputs.get("property_value_inr")

    # tax_residency_country, tax_residency_currency, exchange_rate_to_inr,
    # has_mutual_funds/has_stocks/has_property and wants_repatriation/
    # repatriation_amount_inr already use the exact names agent_logic
    # expects, so they pass through unchanged via the dict(inputs) copy above.

    return adapted
