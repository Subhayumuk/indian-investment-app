from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum

class RiskLevel(str, Enum):
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"

class AssetClass(str, Enum):
    EQUITY = "equity"
    DEBT = "debt"
    REAL_ESTATE = "real_estate"
    GOLD = "gold"
    CASH = "cash"
    HYBRID = "hybrid"

class InvestmentInstrument(BaseModel):
    name: str
    asset_class: AssetClass
    instrument_type: str
    expected_return_min: float
    expected_return_max: float
    risk_level: RiskLevel
    liquidity: str
    min_investment_inr: float
    tax_treatment_india: str
    tax_treatment_foreign: str
    nri_eligible: bool
    recommended_allocation_pct: float
    rationale: str
    confidence_score: float
    warnings: List[str] = []
    isin: str = ""
    category: str = ""
    suggested_allocation_pct: float = 0.0
    suggested_amount_inr: float = 0.0
    why_nri_suitable: str = ""
    historical_return_3yr: str = ""
    historical_return_5yr: str = ""
    platform_to_invest: str = ""
    residence_tax_note: str = ""
    risk_level_label: str = ""

class TaxSummary(BaseModel):
    india_tax_rate: float
    india_tax_type: str
    foreign_country: str
    foreign_tax_rate: float
    dtaa_applicable: bool
    dtaa_benefit: str
    effective_tax_rate: float
    tax_saving_tip: str

class AllocationBreakdown(BaseModel):
    equity_pct: float
    debt_pct: float
    real_estate_pct: float
    gold_pct: float
    cash_pct: float
    hybrid_pct: float

class ScenarioProjection(BaseModel):
    scenario_name: str
    years: int
    initial_investment: float
    monthly_sip: float
    projected_value_conservative: float
    projected_value_moderate: float
    projected_value_optimistic: float
    assumed_return_rate: float

class ComplianceCheck(BaseModel):
    fema_compliant: bool
    rbi_approval_needed: bool
    fatca_applicable: bool
    form_required: List[str]
    annual_limit_inr: Optional[float]
    notes: str

class AssetBreakdown(BaseModel):
    bank_cash_pct: float = 0.0
    mutual_funds_pct: float = 0.0
    stocks_pct: float = 0.0
    property_pct: float = 0.0
    gold_pct: float = 0.0
    other_pct: float = 0.0


class RecommendedAllocation(BaseModel):
    bank_cash_pct: float = 0.0
    mutual_funds_pct: float = 0.0
    stocks_pct: float = 0.0
    property_pct: float = 0.0
    gold_pct: float = 0.0


class PortfolioHealth(BaseModel):
    overall_score: int
    score_label: str  # Poor/Fair/Good/Excellent
    total_corpus_inr: float
    asset_breakdown: AssetBreakdown
    health_flags: List[str] = []
    recommended_allocation: RecommendedAllocation


class RecommendationResponse(BaseModel):
    user_id: Optional[str] = None
    profile_summary: str
    risk_profile: RiskLevel
    investable_amount_inr: float
    investable_amount_foreign: float
    foreign_currency: str
    allocation: AllocationBreakdown
    portfolio_health: PortfolioHealth
    instruments: List[InvestmentInstrument]
    tax_summary: TaxSummary
    compliance: ComplianceCheck
    projections: List[ScenarioProjection]
    key_insights: List[str]
    action_steps: List[str]
    disclaimers: List[str]
    confidence_overall: float
    generated_at: str
