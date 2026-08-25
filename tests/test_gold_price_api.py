from fastapi.testclient import TestClient

from app.main import create_app
from app.config import get_settings


def test_gold_price_falls_back_when_no_api_key_configured():
    # get_settings() is process-wide lru_cached, so this only reflects reality
    # when GOLD_API_KEY isn't set in the test environment — assert the
    # precondition rather than silently testing the wrong path.
    assert get_settings().GOLD_API_KEY == ""

    client = TestClient(create_app())
    response = client.get("/api/gold-price")

    assert response.status_code == 200
    data = response.json()
    assert data["source"] == "fallback"
    assert data["price_per_gram_inr"] == 7500.0
