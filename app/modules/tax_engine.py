from typing import Dict, Any, Optional, Tuple

from app.utils.kb_loader import load_india_kb


class TaxEngine:
    def __init__(self):
        kb = load_india_kb("nri_taxation.yaml")
        self._tds = kb["tds_rates"]
        self._capital_gains = kb["capital_gains"]

        # Debt fund, real estate, and gold LTCG treatment are NOT wired to the
        # YAML yet - the 2026-08-27 rate audit flagged these as genuinely
        # unresolved (debt funds have two overlapping rule changes from 2023
        # and 2024; real estate has a property-only grandfather choice whose
        # NRI treatment is disputed across sources). Wiring them here would
        # mean guessing at a legal question this project deliberately leaves
        # to a human - see HOW_IT_WORKS.md §8. Kept hardcoded until verified.
        self.india_tax_rules = {
            "debt_stcg": {"rate": None, "slab": True, "description": "Short-term capital gains on debt taxed at income slab rate"},
            "debt_ltcg": {"rate": 0.125, "holding_months": 24, "description": "Long-term capital gains on debt (held > 24 months) at 12.5%"},
            "rental_income": {"rate": None, "slab": True, "standard_deduction": 0.30, "description": "Rental income taxed at slab, 30% standard deduction"},
            "gold_stcg": {"rate": None, "slab": True, "holding_months": 24, "description": "Short-term gold gains at slab rate"},
            "gold_ltcg": {"rate": 0.125, "holding_months": 24, "description": "Long-term gold gains at 12.5%"},
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

    def _equity_rule(self, section: str, holding_period_months: int) -> Dict[str, Any]:
        cg = self._capital_gains[section]
        threshold = cg["stcg_holding_months"]
        if holding_period_months < threshold:
            return {
                "rate": cg["stcg_rate"] / 100,
                "holding_months": threshold,
                "description": f"Short-term capital gains on equity (held < {threshold} months)",
            }
        return {
            "rate": cg["ltcg_rate"] / 100,
            "holding_months": threshold,
            "exemption_inr": cg["ltcg_exemption_limit_inr"],
            "description": f"Long-term capital gains on equity (held >= {threshold} months), exempt up to ₹{cg['ltcg_exemption_limit_inr']:,}",
        }

    def get_india_tax(self, instrument_type: str, holding_period_months: int = 13) -> Dict[str, Any]:
        if instrument_type == "stocks":
            rule = self._equity_rule("equity_shares", holding_period_months)
        elif instrument_type in ["equity_mf", "etf"]:
            rule = self._equity_rule("equity_mutual_funds", holding_period_months)
        elif instrument_type in ["debt_mf", "bonds", "fd"]:
            if instrument_type == "fd":
                rule = {
                    "rate": None,
                    "slab": True,
                    "tds": self._tds["nri_interest_nro_fd"] / 100,
                    "description": "NRO FD interest taxed at slab rate, TDS under section 195",
                }
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
            rule = {
                "rate": self._capital_gains["sgb"]["redemption_at_maturity_tax"] / 100,
                "description": "Sovereign Gold Bond redemption at maturity - tax exempt",
            }
        elif instrument_type == "nps":
            rule = self.india_tax_rules["nps_withdrawal"]
        elif instrument_type == "ppf":
            rule = self.india_tax_rules["ppf"]
        elif instrument_type == "dividend":
            rule = {
                "rate": None,
                "slab": True,
                "tds": self._tds["nri_dividend"] / 100,
                "description": "Dividend taxed at slab rate for NRI, TDS under section 195",
            }
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
