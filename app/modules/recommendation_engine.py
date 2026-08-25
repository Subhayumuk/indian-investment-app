"""
Core Recommendation Engine
Orchestrates tax_engine, eligibility_checker, allocation_engine, confidence_scorer,
explanation_builder, disclaimer_generator and currency_converter to produce a
RecommendationResponse for a (nested) UserProfile.
"""
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any, Dict, List
import logging

from app.models.user_profile import UserProfile
from app.models.recommendation import (
    AllocationBreakdown,
    AssetBreakdown,
    AssetClass,
    ComplianceCheck,
    InvestmentInstrument,
    PortfolioHealth,
    RecommendationResponse,
    RecommendedAllocation,
    RiskLevel,
    ScenarioProjection,
    TaxSummary,
)
from app.modules import instrument_catalog
from app.modules.allocation_engine import AllocationEngine
from app.modules.confidence_scorer import ConfidenceScorer
from app.modules.eligibility_checker import EligibilityChecker
from app.modules.explanation_builder import ExplanationBuilder
from app.modules.tax_engine import TaxEngine
from app.utils.currency_converter import CurrencyConverter
from app.utils.disclaimer_generator import DisclaimerGenerator

logger = logging.getLogger(__name__)

ASSET_CLASS_RETURN = {
    "equity": 0.12,
    "debt": 0.07,
    "real_estate": 0.09,
    "gold": 0.09,
    "cash": 0.04,
    "hybrid": 0.08,
}


class RecommendationEngine:
    def __init__(self):
        self.tax_engine = TaxEngine()
        self.eligibility_checker = EligibilityChecker()
        self.allocation_engine = AllocationEngine()
        self.confidence_scorer = ConfidenceScorer()
        self.explanation_builder = ExplanationBuilder()
        self.disclaimer_generator = DisclaimerGenerator()
        self.currency_converter = CurrencyConverter()

    def generate(self, profile: UserProfile) -> RecommendationResponse:
        try:
            flat = self._flatten_profile(profile)

            allocation = self.allocation_engine.get_allocation(flat)
            eligibility = self.eligibility_checker.check_all_eligibility(flat)
            compliance_reqs = self.eligibility_checker.get_compliance_requirements(flat)
            fema_summary = self.eligibility_checker.get_fema_summary(flat)

            instruments = self._build_named_instruments(flat)
            portfolio_health = self._build_portfolio_health(flat)
            tax_summary = self._build_tax_summary(flat)
            compliance = self._build_compliance(compliance_reqs, fema_summary, flat)
            projections = self._build_projections(allocation, flat)

            profile_confidence = self.confidence_scorer.score_profile(flat)
            key_insights = self.explanation_builder.build_key_insights(flat, allocation, tax_summary)
            action_steps = self.explanation_builder.build_action_steps(flat, instruments)
            disclaimers = self.disclaimer_generator.get_disclaimers(flat)
            disclaimers.append(instrument_catalog.PLACEHOLDER_DISCLAIMER)

            investable_amount_inr = flat.total_corpus_inr
            investable_amount_foreign = 0.0
            currency = ""

            try:
                risk_profile = RiskLevel(flat.risk_tolerance)
            except ValueError:
                risk_profile = RiskLevel.MODERATE

            return RecommendationResponse(
                user_id=profile.session_id,
                profile_summary=self.explanation_builder.build_profile_summary(flat),
                risk_profile=risk_profile,
                investable_amount_inr=investable_amount_inr,
                investable_amount_foreign=investable_amount_foreign,
                foreign_currency=currency,
                allocation=allocation,
                portfolio_health=portfolio_health,
                instruments=instruments,
                tax_summary=tax_summary,
                compliance=compliance,
                projections=projections,
                key_insights=key_insights,
                action_steps=action_steps,
                disclaimers=disclaimers,
                confidence_overall=profile_confidence["score"],
                generated_at=datetime.now(timezone.utc).isoformat(),
            )
        except Exception as e:
            logger.error(f"Recommendation engine error: {e}")
            raise

    def _flatten_profile(self, profile: UserProfile) -> SimpleNamespace:
        """Adapts the nested UserProfile (personal/financial/residency/investment)
        into the flat attribute shape the allocation/eligibility/confidence/
        explanation modules expect."""
        indian_status = profile.residency.indian_residential_status
        account_types = [a.value for a in profile.residency.account_types_held]

        bank_total = sum(float(a.get("balance_inr", 0) or 0) for a in profile.financial.bank_accounts)
        mf_total = sum(float(m.get("current_value_inr", 0) or 0) for m in profile.financial.mutual_funds)
        stocks_total = sum(float(s.get("current_value_inr", 0) or 0) for s in profile.financial.stocks)
        property_total = sum(float(p.get("value_inr", 0) or 0) for p in profile.financial.properties)
        other_total = sum(float(o.get("value_inr", 0) or 0) for o in profile.financial.other_savings)
        gold_value = profile.financial.gold_value_inr or 0.0
        total_corpus_inr = bank_total + mf_total + stocks_total + property_total + gold_value + other_total

        return SimpleNamespace(
            age=profile.personal.age,
            risk_tolerance=profile.investment.risk_tolerance.value,
            investment_goal=str(profile.investment.primary_goal),
            investment_horizon_years=profile.investment.investment_horizon_years,
            tax_residency_country=profile.residency.tax_residency_country,
            nri_status=indian_status.value in ("non_resident", "rnor"),
            has_nre_account="NRE" in account_types,
            has_nro_account="NRO" in account_types,
            has_pan=profile.residency.has_pan,
            annual_income_inr=profile.financial.monthly_income_inr * 12,
            monthly_expenses_inr=profile.financial.monthly_expenses_inr,
            existing_investments_inr=profile.financial.existing_investments_inr,
            lump_sum_investable_inr=profile.investment.lump_sum_investable_inr,
            monthly_investable_inr=profile.investment.monthly_investable_inr,
            bank_accounts=profile.financial.bank_accounts,
            mutual_funds=profile.financial.mutual_funds,
            stocks=profile.financial.stocks,
            properties=profile.financial.properties,
            other_savings=profile.financial.other_savings,
            gold_grams=profile.financial.gold_grams,
            gold_value_inr=gold_value,
            bank_total_inr=bank_total,
            mf_total_inr=mf_total,
            stocks_total_inr=stocks_total,
            property_total_inr=property_total,
            other_total_inr=other_total,
            total_corpus_inr=total_corpus_inr,
        )

    @staticmethod
    def _asset_class_for_category(category: str) -> AssetClass:
        c = category.lower()
        if "equity" in c:
            return AssetClass.EQUITY
        if "gold" in c:
            return AssetClass.GOLD
        if "real estate" in c or "reit" in c:
            return AssetClass.REAL_ESTATE
        if "hybrid" in c:
            return AssetClass.HYBRID
        if "fixed deposit" in c:
            return AssetClass.CASH
        return AssetClass.DEBT

    @staticmethod
    def _parse_pct(value: str) -> float:
        try:
            return float(value.replace("%", "").strip())
        except (ValueError, AttributeError):
            return 0.0

    def _build_named_instruments(self, flat: SimpleNamespace) -> List[InvestmentInstrument]:
        foreign_summary = self.tax_engine.get_foreign_tax_summary(flat.tax_residency_country or "")
        catalog_entries = instrument_catalog.get_named_instruments(flat.risk_tolerance, flat.total_corpus_inr)
        instruments: List[InvestmentInstrument] = []

        for entry in catalog_entries:
            asset_class = self._asset_class_for_category(entry["category"])
            try:
                risk_level = RiskLevel(flat.risk_tolerance)
            except ValueError:
                risk_level = RiskLevel.MODERATE
            return_min = self._parse_pct(entry["historical_return_3yr"])
            return_max = self._parse_pct(entry["historical_return_5yr"])

            instruments.append(InvestmentInstrument(
                name=entry["name"],
                asset_class=asset_class,
                instrument_type=entry["instrument_type"],
                expected_return_min=min(return_min, return_max),
                expected_return_max=max(return_min, return_max),
                risk_level=risk_level,
                liquidity=entry["liquidity"],
                min_investment_inr=entry["min_investment_inr"],
                tax_treatment_india=entry["why_nri_suitable"],
                tax_treatment_foreign=foreign_summary.get("notes", ""),
                nri_eligible=True,
                recommended_allocation_pct=entry["suggested_allocation_pct"],
                rationale=entry["why_nri_suitable"],
                confidence_score=self.confidence_scorer.score_instrument(entry["instrument_type"], flat),
                warnings=[instrument_catalog.PLACEHOLDER_DISCLAIMER] if "PLACEHOLDER" in entry["isin"] else [],
                isin=entry["isin"],
                category=entry["category"],
                suggested_allocation_pct=entry["suggested_allocation_pct"],
                suggested_amount_inr=entry["suggested_amount_inr"],
                why_nri_suitable=entry["why_nri_suitable"],
                historical_return_3yr=entry["historical_return_3yr"],
                historical_return_5yr=entry["historical_return_5yr"],
                platform_to_invest=entry["platform_to_invest"],
                danish_tax_note=entry["danish_tax_note"],
                risk_level_label=entry["risk_level_label"],
            ))
        return instruments

    def _build_portfolio_health(self, flat: SimpleNamespace) -> PortfolioHealth:
        total = flat.total_corpus_inr or 0.0
        if total <= 0:
            return PortfolioHealth(
                overall_score=0, score_label="Poor", total_corpus_inr=0.0,
                asset_breakdown=AssetBreakdown(),
                health_flags=["No assets recorded yet — add your holdings to get a portfolio health score."],
                recommended_allocation=RecommendedAllocation(),
            )

        def pct(x: float) -> float:
            return round(x / total * 100, 1)

        cash_pct = pct(flat.bank_total_inr)
        mf_pct = pct(flat.mf_total_inr)
        stocks_pct = pct(flat.stocks_total_inr)
        property_pct = pct(flat.property_total_inr)
        gold_pct = pct(flat.gold_value_inr)
        other_pct = pct(flat.other_total_inr)

        score = 50
        flags: List[str] = []

        if cash_pct > 40:
            score -= 15
            flags.append(f"{cash_pct}% of your corpus sits in low-growth bank/cash accounts — consider moving a portion into mutual funds or bonds.")
        if property_pct > 50:
            score -= 15
            flags.append(f"{property_pct}% of your net worth is in property — this concentrates risk and is illiquid; consider diversifying into financial assets.")
        if mf_pct + stocks_pct > 20:
            score += 15
        if mf_pct + stocks_pct > 40:
            score += 10
        if 5 < gold_pct <= 20:
            score += 5
        elif gold_pct > 20:
            score -= 5
            flags.append(f"{gold_pct}% in gold is on the higher side — gold typically works best as a 5-15% diversifier, not a core holding.")
        if not flat.bank_accounts:
            flags.append("No Indian bank account details recorded — this limits FEMA-compliant repatriation options.")
        if 0 < cash_pct <= 15:
            score += 5  # healthy liquidity buffer without being excessive

        overall_score = max(0, min(100, score))
        if overall_score <= 40:
            label = "Poor"
        elif overall_score <= 65:
            label = "Fair"
        elif overall_score <= 85:
            label = "Good"
        else:
            label = "Excellent"

        recommended = self.allocation_engine.get_allocation(flat)
        return PortfolioHealth(
            overall_score=overall_score,
            score_label=label,
            total_corpus_inr=round(total, 2),
            asset_breakdown=AssetBreakdown(
                bank_cash_pct=cash_pct, mutual_funds_pct=mf_pct, stocks_pct=stocks_pct,
                property_pct=property_pct, gold_pct=gold_pct, other_pct=other_pct,
            ),
            health_flags=flags or ["Your portfolio looks reasonably balanced — keep reviewing it periodically."],
            recommended_allocation=RecommendedAllocation(
                bank_cash_pct=recommended.cash_pct,
                mutual_funds_pct=recommended.equity_pct + recommended.debt_pct,
                stocks_pct=0.0,
                property_pct=recommended.real_estate_pct,
                gold_pct=recommended.gold_pct,
            ),
        )

    def _build_tax_summary(self, flat: SimpleNamespace) -> TaxSummary:
        country = flat.tax_residency_country or ""
        equity_ltcg = self.tax_engine.get_india_tax("equity_mf", holding_period_months=13)
        dtaa = self.tax_engine.get_dtaa_benefit(country, "capital_gains")
        foreign_summary = self.tax_engine.get_foreign_tax_summary(country)
        effective = self.tax_engine.calculate_effective_tax(
            country, "equity_mf", equity_ltcg.get("rate") or 0.0, foreign_summary.get("capital_gains_rate") or 0.0
        )

        return TaxSummary(
            india_tax_rate=equity_ltcg.get("rate") or 0.0,
            india_tax_type="Long-term capital gains on equity (representative rate; varies by instrument)",
            foreign_country=country,
            foreign_tax_rate=foreign_summary.get("capital_gains_rate") or 0.0,
            dtaa_applicable=dtaa.get("applicable", False),
            dtaa_benefit=dtaa.get("benefit", "No DTAA with India"),
            effective_tax_rate=effective["effective_rate"],
            tax_saving_tip=self.explanation_builder.build_tax_saving_tip(flat),
        )

    def _build_compliance(self, compliance_reqs: Dict[str, Dict], fema_summary: Dict[str, Any], flat: SimpleNamespace) -> ComplianceCheck:
        annual_limit_inr = self.currency_converter.to_inr(self.eligibility_checker.fema_limits["outward_remittance_usd"], "USD")
        notes = f"{fema_summary.get('annual_outward_remittance_limit', '')} {fema_summary.get('nro_repatriation_limit', '')}".strip()

        return ComplianceCheck(
            fema_compliant=bool(flat.has_pan) and (flat.has_nre_account or flat.has_nro_account),
            rbi_approval_needed=False,
            fatca_applicable=(flat.tax_residency_country or "").lower() == "usa",
            form_required=[key for key, req in compliance_reqs.items() if req.get("required")],
            annual_limit_inr=annual_limit_inr,
            notes=notes,
        )

    def _project(self, initial: float, monthly: float, years: int, annual_rate: float) -> float:
        annual_rate = max(annual_rate, 0.0)
        n_months = max(years, 0) * 12
        r_month = annual_rate / 12
        fv_lump = initial * ((1 + annual_rate) ** years)
        if r_month > 0 and n_months > 0:
            fv_sip = monthly * (((1 + r_month) ** n_months - 1) / r_month) * (1 + r_month)
        else:
            fv_sip = monthly * n_months
        return round(fv_lump + fv_sip, 2)

    def _build_projections(self, allocation: AllocationBreakdown, flat: SimpleNamespace) -> List[ScenarioProjection]:
        blended_rate = (
            allocation.equity_pct / 100 * ASSET_CLASS_RETURN["equity"]
            + allocation.debt_pct / 100 * ASSET_CLASS_RETURN["debt"]
            + allocation.real_estate_pct / 100 * ASSET_CLASS_RETURN["real_estate"]
            + allocation.gold_pct / 100 * ASSET_CLASS_RETURN["gold"]
            + allocation.cash_pct / 100 * ASSET_CLASS_RETURN["cash"]
            + allocation.hybrid_pct / 100 * ASSET_CLASS_RETURN["hybrid"]
        )
        years = flat.investment_horizon_years or 10
        initial = flat.total_corpus_inr
        monthly = flat.monthly_investable_inr

        return [ScenarioProjection(
            scenario_name="Base case - current allocation",
            years=years,
            initial_investment=initial,
            monthly_sip=monthly,
            projected_value_conservative=self._project(initial, monthly, years, max(blended_rate - 0.03, 0.02)),
            projected_value_moderate=self._project(initial, monthly, years, blended_rate),
            projected_value_optimistic=self._project(initial, monthly, years, blended_rate + 0.03),
            assumed_return_rate=round(blended_rate * 100, 2),
        )]
