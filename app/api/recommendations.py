"""
Recommendations API Router
"""
from fastapi import APIRouter, HTTPException
from app.models.user_profile import UserProfile
from app.models.recommendation import RecommendationResponse
from app.modules.recommendation_engine import RecommendationEngine
import logging

logger = logging.getLogger(__name__)
router = APIRouter()
engine = RecommendationEngine()

@router.post("/recommend", response_model=RecommendationResponse)
async def get_recommendations(profile: UserProfile):
    """
    Generate investment recommendations for an NRI based on their profile.
    """
    try:
        result = engine.generate(profile)
        return result
    except Exception as e:
        logger.error(f"Recommendation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/instruments")
async def list_instruments():
    """List all available investment instruments"""
    return {
        "instruments": [
            {"id": "equity_mutual_funds", "name": "Equity Mutual Funds", "category": "Equity"},
            {"id": "nre_fd", "name": "NRE Fixed Deposit", "category": "Debt"},
            {"id": "nro_fd", "name": "NRO Fixed Deposit", "category": "Debt"},
            {"id": "direct_equity", "name": "Direct Equity (PIS)", "category": "Equity"},
            {"id": "reit", "name": "REITs", "category": "Real Estate"},
            {"id": "govt_bonds", "name": "Government Bonds", "category": "Debt"},
            {"id": "elss", "name": "ELSS Tax Saving Funds", "category": "Equity"},
            {"id": "international_funds", "name": "International Funds", "category": "Equity"},
            {"id": "sgb", "name": "Sovereign Gold Bonds", "category": "Gold"},
            {"id": "ppf", "name": "Public Provident Fund", "category": "Debt"}
        ]
    }

@router.get("/health")
async def health_check():
    return {"status": "ok", "service": "recommendations"}
