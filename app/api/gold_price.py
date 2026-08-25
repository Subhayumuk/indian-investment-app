"""
Gold Price API Router

Fetches the current INR/gram gold price from goldapi.io, with a hardcoded
fallback so the frontend's gold section always has a usable estimate even
without an API key or when the upstream call fails for any reason.
"""
import logging
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter
from pydantic import BaseModel

from app.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter()

FALLBACK_GOLD_PRICE_INR_PER_GRAM = 7500.0
GOLD_API_URL = "https://www.goldapi.io/api/XAU/INR"
REQUEST_TIMEOUT_SECONDS = 5.0
TROY_OUNCE_IN_GRAMS = 31.1035


class GoldPriceResponse(BaseModel):
    price_per_gram_inr: float
    source: str  # "live" | "fallback"
    timestamp: str


def _fallback() -> GoldPriceResponse:
    return GoldPriceResponse(
        price_per_gram_inr=FALLBACK_GOLD_PRICE_INR_PER_GRAM,
        source="fallback",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/gold-price", response_model=GoldPriceResponse)
async def get_gold_price():
    """Returns the current 24K gold price in INR per gram, falling back to a
    hardcoded rate if no API key is configured or the upstream call fails
    for any reason (timeout, non-200, malformed payload)."""
    settings = get_settings()

    if not settings.GOLD_API_KEY:
        return _fallback()

    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
            response = await client.get(
                GOLD_API_URL,
                headers={"x-access-token": settings.GOLD_API_KEY, "Content-Type": "application/json"},
            )
        if response.status_code != 200:
            raise ValueError(f"goldapi.io returned status {response.status_code}")

        data = response.json()
        price_per_gram = data.get("price_gram_24k")
        if price_per_gram is None:
            price_per_ounce = data.get("price")
            if price_per_ounce is None:
                raise ValueError("Malformed goldapi.io response — no price field found")
            price_per_gram = float(price_per_ounce) / TROY_OUNCE_IN_GRAMS

        return GoldPriceResponse(
            price_per_gram_inr=round(float(price_per_gram), 2),
            source="live",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
    except Exception as e:
        logger.warning(f"Gold price fetch failed, using fallback: {e}")
        return _fallback()
