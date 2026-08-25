from typing import Dict, Any, List
from app.models.user_profile import UserProfile
from app.models.recommendation import RecommendationResponse

class ExplanationBuilder:
    def build_profile_summary(self, profile: UserProfile) -> str:
        parts = []
        if profile.age:
            parts.append(f"{profile.age}-year-old")
        if profile.nri_status:
            parts.append("NRI")
        if profile.tax_residency_country:
            parts.append(f"based in {profile.tax_residency_country}")
        if profile.risk_tolerance:
            parts.append(f"with {profile.risk_tolerance} risk appetite")
        if profile.investment_goal:
            parts.append(f"investing for {profile.investment_goal}")
        if profile.investment_horizon_years:
            parts.append(f"over {profile.investment_horizon_years} years")
        return " ".join(parts) if parts else "NRI investor"

    def build_key_insights(self, profile: UserProfile, allocation: Any, tax_summary: Any) -> List[str]:
        insights = []
        country = profile.tax_residency_country or "your country"
        if profile.risk_tolerance == "aggressive":
            insights.append(f"Your aggressive risk profile supports higher equity allocation — equity markets have historically delivered 12-15% CAGR over 10+ year periods in India.")
        elif profile.risk_tolerance == "conservative":
            insights.append("Your conservative profile prioritizes capital preservation. NRE Fixed Deposits offer tax-free interest in India with full repatriation rights.")
        if tax_summary and tax_summary.dtaa_applicable:
            insights.append(f"India has a DTAA with {country} — you can claim credit for taxes paid in India against your {country} tax liability, avoiding double taxation.")
        if profile.tax_residency_country and profile.tax_residency_country.lower() in ["uae", "singapore"]:
            insights.append(f"{country} has zero capital gains tax — your Indian investment returns face only Indian taxation, making it highly efficient.")
        if profile.investment_horizon_years and profile.investment_horizon_years > 10:
            insights.append("Your long investment horizon (10+ years) is a significant advantage — compounding works best over long periods and equity volatility smooths out.")
        if profile.age and profile.age < 35:
            insights.append("Starting early gives you the most powerful investment advantage: time. Even small SIPs grow substantially over 20-30 years due to compounding.")
        if getattr(profile, "has_nre_account", False):
            insights.append("Your NRE account allows tax-free interest income in India and full repatriation — ideal for parking foreign earnings meant for India investment.")
        return insights[:5]

    def build_action_steps(self, profile: UserProfile, instruments: List[Any]) -> List[str]:
        steps = []
        if not getattr(profile, "has_pan", False):
            steps.append("🔴 Apply for PAN card immediately — mandatory for all Indian investments above ₹50,000")
        if not getattr(profile, "has_nre_account", False) and not getattr(profile, "has_nro_account", False):
            steps.append("🔴 Open NRE/NRO bank account with an Indian bank (SBI, HDFC, ICICI offer NRI services)")
        steps.append("📋 Complete KYC with NRI status at your chosen broker/AMC (HDFC Securities, ICICI Direct, or NRI platforms like SBNRI)")
        steps.append("📑 Obtain a Certificate of Residence from your country's tax authority to claim DTAA benefits")
        if profile.tax_residency_country and profile.tax_residency_country.lower() == "usa":
            steps.append("🇺🇸 File FBAR (FinCEN 114) if your Indian account balances exceed USD 10,000 at any point in the year")
        steps.append("💰 Start with NRE FD or liquid funds while completing investment account setup")
        steps.append("📊 Review and rebalance your portfolio annually or when life circumstances change significantly")
        return steps

    def build_tax_saving_tip(self, profile: UserProfile) -> str:
        country = profile.tax_residency_country.lower() if profile.tax_residency_country else ""
        tips = {
            "denmark": "Hold equity investments for 12+ months to qualify for LTCG at 12.5% in India vs 20% STCG. In Denmark, gains are taxed as capital income — use DTAA credit to offset Danish tax.",
            "usa": "Be aware of PFIC (Passive Foreign Investment Company) rules — Indian MFs may be classified as PFICs, creating complex US tax reporting. Consider direct stocks or ETFs instead.",
            "uk": "Use your CGT annual exempt amount (£3,000 for 2024-25) in the UK. Indian LTCG tax paid can be credited against UK CGT liability under DTAA.",
            "germany": "German Abgeltungsteuer (25% + solidarity surcharge) applies to Indian investment income. Use the €1,000 saver's allowance first. DTAA credit available for Indian taxes paid.",
            "australia": "Hold Indian assets for 12+ months to get 50% CGT discount in Australia. Indian tax paid can be credited against Australian tax under DTAA.",
            "singapore": "Singapore has no capital gains tax — your Indian LTCG at 12.5% is the only tax you pay. Extremely tax-efficient structure for Indian NRI investors.",
            "canada": "Canadian residents pay tax on 50% of capital gains. T1135 filing required for Indian assets > CAD 100,000. Consider RRSP for tax-deferred growth.",
            "uae": "UAE has zero personal income tax — your only tax is Indian TDS/withholding. Use NRE account for tax-free interest. Most tax-efficient NRI jurisdiction for Indian investments.",
        }
        return tips.get(country, "Hold investments for required periods to qualify for long-term capital gains rates. Maintain records of acquisition cost and dates for tax filing in both countries.")
