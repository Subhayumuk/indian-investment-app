import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.cas_parser import router as cas_router
from app.api.gold_price import router as gold_router
from app.api.recommendations import router as recommendations_router
from app.config import get_settings
from app.routes.health import router as health_router

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    settings = get_settings()

    logging.basicConfig(
        level=logging.DEBUG if settings.DEBUG else logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )

    application = FastAPI(
        title=settings.APP_TITLE,
        description=settings.APP_DESCRIPTION,
        version=settings.APP_VERSION,
    )

    if settings.CORS_ORIGINS == ["*"]:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    else:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=settings.CORS_ORIGINS,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    application.include_router(health_router)
    application.include_router(recommendations_router, prefix="/api")
    application.include_router(cas_router, prefix="/api")
    application.include_router(gold_router, prefix="/api")

    # Serve the built React app (frontend/, `npm run build`) as the site root.
    # Registered last so the API routers above always match first — Starlette
    # tries routes in registration order, and this StaticFiles mount is the
    # catch-all fallback for everything else.
    static_dir = settings.STATIC_DIR
    if os.path.isfile(os.path.join(static_dir, "index.html")):
        application.mount("/", StaticFiles(directory=static_dir, html=True), name="frontend")
    else:
        @application.get("/")
        def frontend_not_built():
            return JSONResponse(
                content={
                    "message": (
                        "Frontend build not found. Run `npm run build` in frontend/ "
                        "to serve it from here, or `npm run dev` there for local "
                        "development (served separately on its own port)."
                    ),
                    "expected_file": f"{static_dir}/index.html",
                }
            )

    return application


app = create_app()
