from typing import Dict, Any, List, Tuple
from app.models.user_profile import UserProfile

class EligibilityChecker:
    def __init__(self):
        self.nri_eligible_instruments = {
            "nre_fd": {"eligible": True, "account_type": ["NRE"], "notes": "Tax-free interest in India, repatriable"},
            "nro_fd": {"eligible": True, "account_type": ["NRO"], "notes": "Interest taxable in India at 30% TDS"},
            "fcnr": {"eligible": True, "account_type": ["FCNR"], "notes": "Foreign currency deposit, fully repatriable"},
            "equity_mf": {"eligible": True, "account_type": ["NRE", "NRO"], "notes": "Most equity MFs open to NRIs; USA/Canada NRIs face restrictions"},
            "debt_mf": {"eligible": True, "account_type": ["NRE", "NRO"], "notes": "Debt MFs allowed; check fund-specific NRI policy"},
            "direct_equity": {"eligible": True, "account_type": ["NRE", "NRO"], "notes": "Via PIS (Portfolio Investment Scheme) through NRE/NRO demat"},
            "ppf": {"eligible": False, "notes": "NRIs cannot open new PPF. Existing accounts can continue till maturity"},
            "nps": {"eligible": True, "account_type": ["NRE", "NRO"], "notes": "NRIs can invest in NPS Tier 1. Must close on change to resident"},
            "sgb": {"eligible": True, "account_type": ["NRE", "NRO"], "notes": "Sovereign Gold Bonds available to NRIs"},
            "real_estate": {"eligible": True, "notes": "NRIs can buy residential/commercial property. Agricultural land restricted"},
            "reits": {"eligible": True, "account_type": ["NRE", "NRO"], "notes": "REITs listed on Indian exchanges available to NRIs"},
            "etf": {"eligible": True, "account_type": ["NRE", "NRO"], "notes": "ETFs via PIS account"},
            "bonds": {"eligible": True, "account_type": ["NRE", "NRO"], "notes": "Government and corporate bonds available"},
        }
        self.country_restrictions = {
            "usa": ["equity_mf", "debt_mf"],
            "canada": ["equity_mf", "debt_mf"],
        }
        self.fema_limits = {
            "outward_remittance_usd": 250000,
            "real_estate_purchase": "No limit for residential/commercial",
            "nre_repatriation": "Fully repatriable",
            "nro_repatriation_usd": 1000000,
        }

    def check_instrument_eligibility(self, instrument: str, profile: UserProfile) -> Dict[str, Any]:
        base = self.nri_eligible_instruments.get(instrument, {"eligible": True, "notes": "Check with broker"})
        country = profile.tax_residency_country.lower() if profile.tax_residency_country else ""
        restricted = self.country_restrictions.get(country, [])
        warnings = []
        if instrument in restricted:
            warnings.append(f"Many Indian MF houses do not accept investments from {profile.tax_residency_country} residents due to FATCA/FBAR compliance. Use NRI-friendly platforms like SBNRI or Vested.")
        if instrument == "ppf" and not base["eligible"]:
            return {"eligible": False, "warnings": ["NRIs cannot open new PPF accounts"], "notes": base["notes"]}
        return {"eligible": base["eligible"], "warnings": warnings, "notes": base.get("notes", ""), "account_type": base.get("account_type", [])}

    def check_all_eligibility(self, profile: UserProfile) -> Dict[str, Dict]:
        results = {}
        for instrument in self.nri_eligible_instruments:
            results[instrument] = self.check_instrument_eligibility(instrument, profile)
        return results

    def get_compliance_requirements(self, profile: UserProfile) -> Dict[str, Any]:
        country = profile.tax_residency_country.lower() if profile.tax_residency_country else ""
        requirements = {
            "pan_card": {"required": True, "notes": "PAN mandatory for all investments above ₹50,000"},
            "kyc": {"required": True, "notes": "KYC with NRI status mandatory"},
            "nre_nro_account": {"required": True, "notes": "NRE or NRO bank account required for investments"},
            "fema_declaration": {"required": True, "notes": "FEMA compliance declaration required"},
        }
        if country == "usa":
            requirements["fatca"] = {"required": True, "notes": "FATCA reporting required. Form W-8BEN for US persons"}
            requirements["fbar"] = {"required": True, "notes": "FBAR (FinCEN 114) if Indian accounts exceed USD 10,000"}
        if country == "canada":
            requirements["t1135"] = {"required": True, "notes": "T1135 Foreign Income Verification if foreign assets > CAD 100,000"}
        if country in ["uk", "germany", "denmark", "australia"]:
            requirements["foreign_income_reporting"] = {"required": True, "notes": f"Must report Indian income in {country.title()} tax return"}
        return requirements

    def get_fema_summary(self, profile: UserProfile) -> Dict[str, Any]:
        country = profile.tax_residency_country or "Unknown"
        fx_rates = {"denmark": 11.5, "usa": 1.0, "uk": 0.79, "germany": 0.92, "australia": 1.53, "singapore": 1.35, "canada": 1.36, "uae": 3.67}
        rate = fx_rates.get(country.lower(), 1.0)
        currency_symbols = {"denmark": "DKK", "usa": "USD", "uk": "GBP", "germany": "EUR", "australia": "AUD", "singapore": "SGD", "canada": "CAD", "uae": "AED"}
        currency = currency_symbols.get(country.lower(), "USD")
        limit_usd = self.fema_limits["outward_remittance_usd"]
        limit_local = round(limit_usd * rate)
        return {
            "annual_outward_remittance_limit": f"USD {limit_usd:,} (approx. {currency} {limit_local:,}) per financial year under LRS",
            "nro_repatriation_limit": f"USD {self.fema_limits['nro_repatriation_usd']:,} per financial year from NRO account",
            "nre_repatriation": self.fema_limits["nre_repatriation"],
            "real_estate": self.fema_limits["real_estate_purchase"],
            "currency": currency,
            "country": country,
        }
