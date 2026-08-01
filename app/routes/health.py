import os

from fastapi import APIRouter

from app.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/api/health")
def health():
    settings = get_settings()
    index_path = os.path.join(settings.STATIC_DIR, "index.html")

    return {
        "status": "ok",
        "version": settings.APP_VERSION,
        "static_index_exists": os.path.exists(index_path),
    }
