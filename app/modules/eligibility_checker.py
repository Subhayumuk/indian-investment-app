from typing import Dict, Any, List, Tuple
from app.models.user_profile import UserProfile
from app.utils.kb_loader import load_india_kb, load_country_tax_rules

_SUPPORTED_RESIDENCE_COUNTRIES = [
    "denmark", "usa", "uk", "germany", "australia", "singapore", "canada", "uae",
]

# Maps this module's own instrument keys to app/knowledge_base/india/product_rules.yaml's
# product keys. real_estate and bonds have no entry there and stay hardcoded below.
_PRODUCT_KEY_MAP = {
    "nre_fd": "nre_fixed_deposit",
    "nro_fd": "nro_fixed_deposit",
    "fcnr": "fcnr_deposit",
    "equity_mf": "equity_mutual_funds",
    "debt_mf": "debt_mutual_funds",
    "direct_equity": "direct_equity",
    "ppf": "ppf",
    "nps": "nps",
    "sgb": "sgb",
    "reits": "reits",
    "etf": "etf",
}


def _country_currency(country_lower: str) -> str:
    if country_lower not in _SUPPORTED_RESIDENCE_COUNTRIES:
        return "USD"
    data = load_country_tax_rules(country_lower)
    # Denmark nests this under "overview"; the other 7 countries have it
    # top-level - schema isn't consistent across the knowledge base yet.
    return data.get("currency") or data.get("overview", {}).get("currency", "USD")


class EligibilityChecker:
    def __init__(self):
        products = load_india_kb("product_rules.yaml")["products"]
        fema = load_india_kb("fema_rules.yaml")

        self.nri_eligible_instruments = {
            "real_estate": {"eligible": True, "notes": "NRIs can buy residential/commercial property. Agricultural land restricted"},
            "bonds": {"eligible": True, "account_type": ["NRE", "NRO"], "notes": "Government and corporate bonds available"},
        }
        for key, product_key in _PRODUCT_KEY_MAP.items():
            product = products[product_key]
            self.nri_eligible_instruments[key] = {
                "eligible": product["nri_eligible"],
                "account_type": product.get("account_types_allowed", []),
                "notes": product.get("nri_note") or product.get("us_canada_note") or "",
            }

        # Previously a separate hardcoded list that only named equity_mf and
        # debt_mf - product_rules.yaml already flags "etf" as US/Canada
        # restricted too (us_canada_restriction: true) and that was being
        # missed. Derived from the same source data now, so it can't drift.
        us_canada_restricted = [
            key for key, product_key in _PRODUCT_KEY_MAP.items()
            if products[product_key].get("us_canada_restriction")
        ]
        self.country_restrictions = {
            "usa": us_canada_restricted,
            "canada": us_canada_restricted,
        }

        nre = fema["repatriation_rules"]["nre_account"]
        nro = fema["repatriation_rules"]["nro_account"]
        self.fema_limits = {
            # The $250k/year LRS cap applies to persons resident IN India
            # remitting abroad - it does not govern NRIs at all (their
            # repatriation is the NRO/NRE limits below, which ARE wired to
            # fema_rules.yaml). Flagged during the 2026-08-27 eligibility
            # migration as likely the wrong figure to show an NRI user, but
            # left as-is pending a decision - fema_rules.yaml has no LRS
            # figure to wire this to either way.
            "outward_remittance_usd": 250000,
            "real_estate_purchase": "No limit for residential/commercial",
            "nre_repatriation": "Fully repatriable" if nre["freely_repatriable"] else nre["limit"],
            "nro_repatriation_usd": nro["annual_limit_usd"],
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
        country_lower = country.lower()

        # Exchange rates are live market data, not a legal fact - unlike tax
        # rates, moving these to a YAML file wouldn't fix staleness, since
        # these go stale within days, not years. A real fix needs a live FX
        # call (same pattern as app/api/gold_price.py), not a data file -
        # out of scope for this pass. Left as the same approximate hardcoded
        # rates as before.
        fx_rates = {"denmark": 11.5, "usa": 1.0, "uk": 0.79, "germany": 0.92, "australia": 1.53, "singapore": 1.35, "canada": 1.36, "uae": 3.67}
        rate = fx_rates.get(country_lower, 1.0)
        currency = _country_currency(country_lower)
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
