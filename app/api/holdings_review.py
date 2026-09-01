"""
Holdings Review API Router

Reuses the same UserProfile request model as /api/recommend - no new
request schema, so there's no way for this endpoint's input shape to
drift from the main recommendation flow's.
"""
import logging

from fastapi import APIRouter, HTTPException

from app.models.holdings_review import HoldingsReviewResponse
from app.models.user_profile import UserProfile
from app.modules.holdings_review_engine import HoldingsReviewEngine

logger = logging.getLogger(__name__)
router = APIRouter()
engine = HoldingsReviewEngine()


@router.post("/holdings-review", response_model=HoldingsReviewResponse)
async def get_holdings_review(profile: UserProfile):
    """
    Compares a user's actual mutual fund holdings against real AMFI/mfapi.in
    market data and a computed peer benchmark. Verdicts are entirely
    rule-based - there is no AI narration yet (that's Phase C; llm_available
    will always be False until then).
    """
    try:
        return await engine.review(profile)
    except Exception as e:
        logger.error(f"Holdings review error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
