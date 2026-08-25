from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class PlannerInput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    # Residency / identity
    residency_country: Optional[str] = "Denmark"
    tax_resident_denmark: Optional[bool] = True
    indian_residential_status: Optional[str] = "NRI"

    # Multi-country tax residency
    tax_residency_country: Optional[str] = "Denmark"
    tax_residency_currency: Optional[str] = "DKK"
    exchange_rate_to_inr: Optional[float] = 11.5

    # Indian compliance
    has_pan: Optional[bool] = True
    has_aadhaar: Optional[bool] = None
    files_india_itr: Optional[bool] = False

    # Denmark compliance
    declares_india_income_in_denmark: Optional[bool] = False

    # Exchange rate
    inr_to_dkk_rate: Optional[float] = 0.083

    # Indian savings/investments
    india_principal_inr: Optional[float] = None
    india_annual_interest_inr: Optional[float] = None
    india_interest_rate_percent: Optional[float] = None
    indian_tds_percent: Optional[float] = 10.0

    # Other Indian investments
    has_mutual_funds: Optional[bool] = False
    mutual_fund_value_inr: Optional[float] = None
    has_stocks: Optional[bool] = False
    stocks_value_inr: Optional[float] = None
    has_property: Optional[bool] = False
    property_value_inr: Optional[float] = None

    # Repatriation
    wants_repatriation: Optional[bool] = False
    repatriation_amount_inr: Optional[float] = None

    # Danish income / capital income
    dk_salary_income_dkk: Optional[float] = None
    dk_capital_income_dkk: Optional[float] = None
    dk_bank_interest_dkk: Optional[float] = None

    # Planning preferences
    risk_profile: Optional[str] = "moderate"
    investment_horizon_years: Optional[int] = 7
    monthly_expenses_dkk: Optional[float] = None
    emergency_months: Optional[int] = 6
    needs_liquidity: Optional[bool] = True
    wants_india_exposure: Optional[bool] = True
    wants_denmark_investments: Optional[bool] = True

    # Indian bank accounts
    has_nro_account: Optional[bool] = True
    has_nre_account: Optional[bool] = False
    has_fcnr_account: Optional[bool] = False

    # Free text
    notes: Optional[str] = None


DISPLAY_ORDER = [
    "residency_country",
    "tax_resident_denmark",
    "indian_residential_status",
    "tax_residency_country",
    "tax_residency_currency",
    "exchange_rate_to_inr",
    "has_pan",
    "has_aadhaar",
    "inr_to_dkk_rate",
    "india_principal_inr",
    "india_annual_interest_inr",
    "india_interest_rate_percent",
    "indian_tds_percent",
    "has_mutual_funds",
    "mutual_fund_value_inr",
    "has_stocks",
    "stocks_value_inr",
    "has_property",
    "property_value_inr",
    "wants_repatriation",
    "repatriation_amount_inr",
    "dk_salary_income_dkk",
    "dk_capital_income_dkk",
    "dk_bank_interest_dkk",
    "risk_profile",
    "investment_horizon_years",
    "monthly_expenses_dkk",
    "emergency_months",
    "needs_liquidity",
    "wants_india_exposure",
    "wants_denmark_investments",
    "has_nro_account",
    "has_nre_account",
    "has_fcnr_account",
    "files_india_itr",
    "declares_india_income_in_denmark",
    "notes",
]


def model_to_actual_dict(payload: PlannerInput) -> dict[str, Any]:
    """Return only fields sent by the client (exclude unset defaults)."""
    return payload.model_dump(exclude_unset=True)


def model_to_normalized_dict(payload: PlannerInput) -> dict[str, Any]:
    """Return full payload with defaults for internal calculations."""
    return payload.model_dump()
