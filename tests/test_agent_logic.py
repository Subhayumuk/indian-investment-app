from agent.agent_logic import analyze_tax, build_investment_allocation, calculate_liquid_reserve
from app.services.input_adapter import adapt_planner_inputs


def test_adapt_planner_inputs_maps_frontend_fields():
    api_inputs = {
        "tax_resident_denmark": True,
        "declares_india_income_in_denmark": False,
        "has_nro_account": True,
        "has_nre_account": False,
        "has_fcnr_account": False,
        "india_principal_inr": 1_000_000,
        "india_annual_interest_inr": 50_000,
        "indian_tds_percent": 10,
        "monthly_expenses_dkk": 20_000,
        "inr_to_dkk_rate": 0.08,
        "risk_profile": "moderate",
        "investment_horizon_years": 7,
    }

    adapted = adapt_planner_inputs(api_inputs)

    assert adapted["dk_residency"] == "tax_resident"
    assert adapted["dk_prev_declared"] == "no"
    assert adapted["india_account_type"] == "NRO"
    assert adapted["india_amount_in_inr"] == 1_000_000
    assert adapted["india_interest_in_inr"] == 50_000
    assert adapted["india_withholding_info"] == "10% TDS"
    assert adapted["monthly_expenses_inr"] == 250_000


def test_calculate_liquid_reserve_uses_monthly_expenses():
    inputs = {"monthly_expenses_inr": 50_000, "emergency_months": 6}
    result = calculate_liquid_reserve(inputs, total_india_savings=2_000_000)

    assert result["suggested_liquid_reserve_inr"] == 300_000
    assert result["investable_amount_inr"] == 1_700_000


def test_build_investment_allocation_percentages_sum_to_100():
    allocation = build_investment_allocation(
        investable_amount=500_000,
        risk_profile="moderate",
        investment_horizon_years=7,
    )

    assert allocation
    assert sum(item["percentage"] for item in allocation) == 100
    assert sum(item["amount_inr"] for item in allocation) == 500_000


def test_analyze_tax_returns_structured_result():
    inputs = adapt_planner_inputs(
        {
            "tax_resident_denmark": True,
            "has_nro_account": True,
            "india_principal_inr": 1_000_000,
            "india_annual_interest_inr": 60_000,
            "indian_tds_percent": 10,
            "risk_profile": "moderate",
            "investment_horizon_years": 7,
        }
    )

    result = analyze_tax(inputs)

    assert "liquidity_plan" in result
    assert "investment_recommendation" in result
    assert "denmark_tax_actions" in result
    assert "india_tax_notes" in result
    assert "display_text" in result
    assert result["inputs_interpreted"]["india_principal_inr"] == 1_000_000
