from typing import Dict, Any
from app.models.user_profile import UserProfile

class ConfidenceScorer:
    def __init__(self):
        self.field_weights = {
            "age": 10, "annual_income_inr": 15, "monthly_expenses_inr": 10,
            "existing_investments_inr": 10, "risk_tolerance": 15, "investment_goal": 10,
            "investment_horizon_years": 10, "tax_residency_country": 10, "nri_status": 5,
            "has_nre_account": 5, "has_nro_account": 5, "has_pan": 5,
        }

    def score_profile(self, profile: UserProfile) -> Dict[str, Any]:
        total_weight = sum(self.field_weights.values())
        earned = 0
        missing = []
        for field, weight in self.field_weights.items():
            val = getattr(profile, field, None)
            if val is not None and val != "" and val != 0:
                earned += weight
            else:
                missing.append(field)
        score = round(earned / total_weight, 2)
        if score >= 0.8:
            level = "high"
            message = "Strong profile — recommendations are well-tailored"
        elif score >= 0.5:
            level = "medium"
            message = "Moderate profile — some assumptions made for missing data"
        else:
            level = "low"
            message = "Limited profile — recommendations are generic; provide more details for better accuracy"
        return {"score": score, "level": level, "message": message, "missing_fields": missing, "earned_points": earned, "total_points": total_weight}

    def score_instrument(self, instrument_type: str, profile: UserProfile) -> float:
        base = 0.7
        country = profile.tax_residency_country.lower() if profile.tax_residency_country else ""
        if instrument_type in ["equity_mf", "debt_mf"] and country in ["usa", "canada"]:
            base -= 0.2
        if instrument_type in ["nre_fd", "fcnr"] and getattr(profile, "has_nre_account", False):
            base += 0.1
        if instrument_type == "ppf":
            base = 0.3
        if profile.risk_tolerance:
            risk = profile.risk_tolerance.lower()
            if risk == "conservative" and instrument_type in ["equity_mf", "direct_equity"]:
                base -= 0.15
            elif risk == "aggressive" and instrument_type in ["nre_fd", "nro_fd"]:
                base -= 0.1
        return min(max(round(base, 2), 0.1), 1.0)
