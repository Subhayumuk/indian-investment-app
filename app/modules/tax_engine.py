from typing import Dict, Any, Optional, Tuple

class TaxEngine:
    def __init__(self):
        self.india_tax_rules = {
            "equity_stcg": {"rate": 0.20, "holding_months": 12, "description": "Short-term capital gains on equity (held < 12 months)"},
            "equity_ltcg": {"rate": 0.125, "holding_months": 12, "exemption_inr": 125000, "description": "Long-term capital gains on equity (held > 12 months), exempt up to ₹1.25L"},
            "debt_stcg": {"rate": None, "slab": True, "description": "Short-term capital gains on debt taxed at income slab rate"},
            "debt_ltcg": {"rate": 0.125, "holding_months": 24, "description": "Long-term capital gains on debt (held > 24 months) at 12.5%"},
            "fd_interest": {"rate": None, "slab": True, "tds": 0.10, "description": "FD interest taxed at slab rate, TDS 10%"},
            "rental_income": {"rate": None, "slab": True, "standard_deduction": 0.30, "description": "Rental income taxed at slab, 30% standard deduction"},
            "dividend": {"rate": None, "slab": True, "tds": 0.20, "description": "Dividend taxed at slab rate for NRI, TDS 20%"},
            "gold_stcg": {"rate": None, "slab": True, "holding_months": 24, "description": "Short-term gold gains at slab rate"},
            "gold_ltcg": {"rate": 0.125, "holding_months": 24, "description": "Long-term gold gains at 12.5%"},
            "sgb_redemption": {"rate": 0.0, "description": "Sovereign Gold Bond redemption at maturity - tax exempt"},
            "nps_withdrawal": {"rate": 0.0, "partial_taxable": 0.40, "description": "NPS: 60% tax-free on maturity, 40% must buy annuity"},
            "ppf": {"rate": 0.0, "description": "PPF interest and maturity fully exempt (NRIs cannot open new, can continue existing)"},
        }
        self.dtaa_countries = {
            "denmark": {"treaty_year": 1989, "dividend_rate": 0.15, "interest_rate": 0.10, "capital_gains": "source_country", "tie_breaker": True},
            "usa": {"treaty_year": 1989, "dividend_rate": 0.15, "interest_rate": 0.15, "capital_gains": "source_country", "tie_breaker": True},
            "uk": {"treaty_year": 1993, "dividend_rate": 0.15, "interest_rate": 0.15, "capital_gains": "source_country", "tie_breaker": True},
            "germany": {"treaty_year": 1995, "dividend_rate": 0.10, "interest_rate": 0.10, "capital_gains": "source_country", "tie_breaker": True},
            "australia": {"treaty_year": 1991, "dividend_rate": 0.15, "interest_rate": 0.15, "capital_gains": "source_country", "tie_breaker": True},
            "singapore": {"treaty_year": 1994, "dividend_rate": 0.15, "interest_rate": 0.15, "capital_gains": "residence_country", "tie_breaker": True},
            "canada": {"treaty_year": 1996, "dividend_rate": 0.15, "interest_rate": 0.15, "capital_gains": "source_country", "tie_breaker": True},
            "uae": {"treaty_year": 1993, "dividend_rate": 0.0, "interest_rate": 0.0, "capital_gains": "residence_country", "tie_breaker": False},
        }

    def get_india_tax(self, instrument_type: str, holding_period_months: int = 13) -> Dict[str, Any]:
        if instrument_type in ["equity_mf", "stocks", "etf"]:
            if holding_period_months < 12:
                rule = self.india_tax_rules["equity_stcg"]
            else:
                rule = self.india_tax_rules["equity_ltcg"]
        elif instrument_type in ["debt_mf", "bonds", "fd"]:
            if instrument_type == "fd":
                rule = self.india_tax_rules["fd_interest"]
            elif holding_period_months < 24:
                rule = self.india_tax_rules["debt_stcg"]
            else:
                rule = self.india_tax_rules["debt_ltcg"]
        elif instrument_type == "real_estate":
            rule = {"rate": 0.125, "holding_months": 24, "description": "LTCG on property at 12.5% without indexation"}
        elif instrument_type in ["gold", "gold_etf"]:
            if holding_period_months < 24:
                rule = self.india_tax_rules["gold_stcg"]
            else:
                rule = self.india_tax_rules["gold_ltcg"]
        elif instrument_type == "sgb":
            rule = self.india_tax_rules["sgb_redemption"]
        elif instrument_type == "nps":
            rule = self.india_tax_rules["nps_withdrawal"]
        elif instrument_type == "ppf":
            rule = self.india_tax_rules["ppf"]
        elif instrument_type == "dividend":
            rule = self.india_tax_rules["dividend"]
        else:
            rule = {"rate": None, "slab": True, "description": "Taxed at applicable slab rate"}
        return rule

    def get_dtaa_benefit(self, country: str, income_type: str) -> Dict[str, Any]:
        country_lower = country.lower()
        if country_lower not in self.dtaa_countries:
            return {"applicable": False, "benefit": "No DTAA with India", "rate": None}
        dtaa = self.dtaa_countries[country_lower]
        if income_type == "dividend":
            return {"applicable": True, "benefit": f"Reduced dividend withholding at {int(dtaa['dividend_rate']*100)}% under DTAA", "rate": dtaa["dividend_rate"]}
        elif income_type == "interest":
            return {"applicable": True, "benefit": f"Reduced interest withholding at {int(dtaa['interest_rate']*100)}% under DTAA", "rate": dtaa["interest_rate"]}
        elif income_type == "capital_gains":
            if dtaa["capital_gains"] == "residence_country":
                return {"applicable": True, "benefit": "Capital gains taxable only in country of residence under DTAA", "rate": 0.0}
            else:
                return {"applicable": True, "benefit": "Capital gains taxable in source country (India) under DTAA", "rate": None}
        return {"applicable": True, "benefit": "DTAA applicable - consult tax advisor for specific treatment", "rate": None}

    def calculate_effective_tax(self, country: str, instrument_type: str, india_tax_rate: float, foreign_tax_rate: float) -> Dict[str, Any]:
        dtaa = self.get_dtaa_benefit(country, "capital_gains")
        if dtaa["applicable"] and dtaa.get("rate") == 0.0:
            effective_rate = foreign_tax_rate
            note = "Taxed only in residence country per DTAA"
        elif india_tax_rate and foreign_tax_rate:
            effective_rate = max(india_tax_rate, foreign_tax_rate)
            note = "Higher of India/foreign tax applies; credit available for tax paid in India"
        else:
            effective_rate = india_tax_rate or foreign_tax_rate or 0
            note = "Single jurisdiction taxation"
        return {"effective_rate": effective_rate, "note": note, "dtaa_used": dtaa["applicable"]}

    def get_foreign_tax_summary(self, country: str) -> Dict[str, Any]:
        summaries = {
            "denmark": {"capital_gains_rate": 0.42, "dividend_rate": 0.27, "interest_rate": 0.37, "currency": "DKK", "notes": "Denmark taxes worldwide income. Foreign investment income taxed as capital income at 27-42%."},
            "usa": {"capital_gains_rate": 0.20, "dividend_rate": 0.20, "interest_rate": 0.37, "currency": "USD", "notes": "LTCG at 0/15/20% based on income. FBAR/FATCA reporting required for foreign accounts."},
            "uk": {"capital_gains_rate": 0.20, "dividend_rate": 0.3375, "interest_rate": 0.45, "currency": "GBP", "notes": "CGT at 20% for higher rate taxpayers. Dividend allowance £500/year."},
            "germany": {"capital_gains_rate": 0.26375, "dividend_rate": 0.26375, "interest_rate": 0.26375, "currency": "EUR", "notes": "Flat Abgeltungsteuer 25% + solidarity surcharge. €1,000 saver's allowance."},
            "australia": {"capital_gains_rate": 0.235, "dividend_rate": 0.30, "interest_rate": 0.30, "currency": "AUD", "notes": "50% CGT discount for assets held >12 months. Marginal rate applies."},
            "singapore": {"capital_gains_rate": 0.0, "dividend_rate": 0.0, "interest_rate": 0.0, "currency": "SGD", "notes": "No capital gains tax. No dividend tax. Very favorable for Indian investments."},
            "canada": {"capital_gains_rate": 0.2665, "dividend_rate": 0.39, "interest_rate": 0.53, "currency": "CAD", "notes": "50% of capital gains included in income. T1135 foreign income verification required."},
            "uae": {"capital_gains_rate": 0.0, "dividend_rate": 0.0, "interest_rate": 0.0, "currency": "AED", "notes": "No personal income tax in UAE. Most favorable jurisdiction for Indian NRI investors."},
        }
        return summaries.get(country.lower(), {"capital_gains_rate": 0.20, "dividend_rate": 0.20, "interest_rate": 0.20, "currency": "USD", "notes": "Standard tax rates apply. Consult local tax advisor."})
