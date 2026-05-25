from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ddep_backend import __version__
from ddep_backend.core.config import get_settings
from ddep_backend.domains import DIAGNOSIS_DOMAINS
from ddep_backend.schemas.health import HealthResponse


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version=__version__)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin).rstrip("/") for origin in settings.cors_origins],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health() -> HealthResponse:
        return HealthResponse(
            status="ok",
            service=settings.app_name,
            environment=settings.environment,
            domains=DIAGNOSIS_DOMAINS,
        )

    return app


app = create_app()
