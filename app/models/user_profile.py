from pydantic import BaseModel, Field, validator
from typing import Optional, List
from enum import Enum


class RiskTolerance(str, Enum):
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"


class InvestmentGoal(str, Enum):
    RETIREMENT = "retirement"
    PROPERTY_PURCHASE = "property_purchase"
    CHILD_EDUCATION = "child_education"
    WEALTH_CREATION = "wealth_creation"
    PASSIVE_INCOME = "passive_income"
    EMERGENCY_FUND = "emergency_fund"
    RETURN_TO_INDIA = "return_to_india"


class EmploymentStatus(str, Enum):
    SALARIED = "salaried"
    SELF_EMPLOYED = "self_employed"
    BUSINESS_OWNER = "business_owner"
    RETIRED = "retired"
    STUDENT = "student"
    UNEMPLOYED = "unemployed"


class MaritalStatus(str, Enum):
    SINGLE = "single"
    MARRIED = "married"
    DIVORCED = "divorced"
    WIDOWED = "widowed"


class IndianResidentialStatus(str, Enum):
    RESIDENT = "resident"
    RNOR = "rnor"
    NON_RESIDENT = "non_resident"
    UNKNOWN = "unknown"


class AccountType(str, Enum):
    NRE = "NRE"
    NRO = "NRO"
    FCNR = "FCNR"
    RESIDENT_SAVINGS = "resident_savings"
    RFC = "RFC"


class LiquidityNeed(str, Enum):
    HIGH = "high"       # May need funds within 1 year
    MEDIUM = "medium"   # May need funds within 1-3 years
    LOW = "low"         # Can lock in for 3+ years


class PersonalProfile(BaseModel):
    age: int = Field(..., ge=18, le=80, description="Age in years")
    marital_status: MaritalStatus
    dependents: int = Field(0, ge=0, le=10, description="Number of financial dependents")
    employment_status: EmploymentStatus
    income_stability: str = Field(..., description="stable / variable / seasonal")
    citizenship: str = Field(..., description="Country of citizenship e.g. India, Denmark")
    oci_pio_status: bool = Field(False, description="Does user hold OCI or PIO card")


class FinancialProfile(BaseModel):
    monthly_income_inr: float = Field(0.0, ge=0, description="Monthly income in INR equivalent")
    monthly_income_foreign: float = Field(0.0, ge=0, description="Monthly income in foreign currency")
    foreign_currency: str = Field("USD", description="Currency of foreign income e.g. DKK, USD, EUR")
    monthly_expenses_inr: float = Field(0.0, ge=0)
    monthly_expenses_foreign: float = Field(0.0, ge=0)
    emergency_fund_months: float = Field(0.0, ge=0, description="Emergency fund in months of expenses")
    existing_debt_inr: float = Field(0.0, ge=0, description="Total outstanding debt in INR")
    monthly_emi_inr: float = Field(0.0, ge=0, description="Monthly EMI obligations in INR")
    insurance_coverage: bool = Field(False, description="Has adequate life and health insurance")
    insurance_sum_assured_inr: float = Field(0.0, ge=0)
    existing_investments_inr: float = Field(0.0, ge=0, description="Current investment portfolio value in INR")
    retirement_savings_inr: float = Field(0.0, ge=0)
    total_assets_inr: float = Field(0.0, ge=0)
    bank_accounts: List[dict] = Field(default_factory=list, description='[{"bank_name","account_type","balance_inr"}]')
    mutual_funds: List[dict] = Field(default_factory=list, description='[{"fund_name","current_value_inr"}]')
    stocks: List[dict] = Field(default_factory=list, description='[{"stock_name","current_value_inr"}]')
    properties: List[dict] = Field(default_factory=list, description='[{"description","value_inr"}]')
    gold_grams: float = Field(0.0, ge=0, description="Physical/digital gold held, in grams")
    gold_value_inr: float = Field(0.0, ge=0, description="Estimated INR value of gold held")
    other_savings: List[dict] = Field(default_factory=list, description='[{"type","value_inr"}] e.g. PPF/NPS/EPF/NSC')


class ResidencyProfile(BaseModel):
    country_of_stay: str = Field(..., description="Country where currently living e.g. Denmark")
    tax_residency_country: str = Field(..., description="Country of tax residence (may differ)")
    days_in_india_current_fy: int = Field(0, ge=0, le=365)
    days_in_india_last_4_fy: int = Field(0, ge=0, le=1460, description="Total days in India in last 4 FYs")
    indian_residential_status: IndianResidentialStatus = Field(
        IndianResidentialStatus.UNKNOWN,
        description="Will be auto-determined if unknown"
    )
    has_indian_bank_accounts: bool = True
    account_types_held: List[AccountType] = Field(default_factory=list)
    repatriation_required: bool = Field(False, description="Will user need to repatriate funds abroad")
    plans_to_return_to_india: bool = Field(False)
    expected_return_year: Optional[int] = Field(None, description="Year planning to return to India")
    has_trc: bool = Field(False, description="Has Tax Residency Certificate from country of residence")
    has_pan: bool = Field(True, description="Has Indian PAN card")
    has_kyc: bool = Field(True, description="KYC completed with Indian banks/AMCs")


class InvestmentProfile(BaseModel):
    risk_tolerance: RiskTolerance
    investment_horizon_years: int = Field(..., ge=1, le=40)
    liquidity_need: LiquidityNeed
    primary_goal: InvestmentGoal
    secondary_goals: List[InvestmentGoal] = Field(default_factory=list)
    monthly_investable_inr: float = Field(0.0, ge=0, description="Amount available for investment per month")
    lump_sum_investable_inr: float = Field(0.0, ge=0, description="One-time lump sum available")
    preferred_currency: str = Field("INR", description="Preferred currency for returns INR/USD/EUR/DKK")
    existing_india_investments: List[str] = Field(
        default_factory=list,
        description="e.g. ['equity_mf', 'nre_fd', 'direct_equity']"
    )
    avoid_instruments: List[str] = Field(
        default_factory=list,
        description="Instruments to avoid e.g. ['real_estate', 'direct_equity']"
    )
    esg_preference: bool = Field(False, description="Prefers ESG/sustainable investments")


class UserProfile(BaseModel):
    session_id: str
    personal: PersonalProfile
    financial: FinancialProfile
    residency: ResidencyProfile
    investment: InvestmentProfile

    class Config:
        use_enum_values = True
