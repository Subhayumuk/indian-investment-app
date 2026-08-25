from typing import List
from app.models.user_profile import UserProfile

class DisclaimerGenerator:
    def get_disclaimers(self, profile: UserProfile) -> List[str]:
        base = [
            "This tool provides general educational information only and does not constitute financial, legal, or tax advice.",
            "Investment recommendations are based on the information provided and general rules-based logic — not personalized professional advice.",
            "Tax laws in India and your country of residence change frequently. Always verify current rates with a qualified tax professional.",
            "Past performance of investment instruments does not guarantee future returns.",
            "Currency exchange rates fluctuate and can significantly impact returns when converting back to your home currency.",
            "FEMA, RBI, and SEBI regulations for NRI investments are subject to change. Verify current rules before investing.",
        ]
        country = profile.tax_residency_country.lower() if profile.tax_residency_country else ""
        if country == "usa":
            base.append("US residents: Indian mutual funds may be classified as PFICs under US tax law. Consult a US tax advisor with international expertise before investing.")
            base.append("FBAR and FATCA reporting obligations apply to US persons with foreign financial accounts. Non-compliance carries significant penalties.")
        if country == "canada":
            base.append("Canadian residents must file T1135 for foreign assets exceeding CAD 100,000. Consult a Canadian tax advisor.")
        base.append("This application does not store your personal financial data. All calculations are performed in-session only.")
        base.append("Consult a SEBI-registered investment advisor and a qualified international tax consultant before making investment decisions.")
        return base
