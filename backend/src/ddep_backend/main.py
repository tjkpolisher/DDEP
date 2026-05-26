from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ddep_backend import __version__
from ddep_backend.core.config import get_settings
from ddep_backend.domains import DIAGNOSIS_DOMAINS
from ddep_backend.result_report.api import ResultReportPreviewRequest, preview_result_report
from ddep_backend.result_report.models import ResultReport
from ddep_backend.schemas.health import HealthResponse
from ddep_backend.search_agent.api import preview_recommendations
from ddep_backend.search_agent.models import RecommendationRequest, RecommendationRun
from ddep_backend.service_mvp.api import router as service_mvp_router


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
    app.include_router(service_mvp_router)

    @app.get("/health")
    async def health() -> HealthResponse:
        return HealthResponse(
            status="ok",
            service=settings.app_name,
            environment=settings.environment,
            domains=DIAGNOSIS_DOMAINS,
        )

    @app.post("/result-report/preview")
    async def result_report_preview(request: ResultReportPreviewRequest) -> ResultReport:
        return preview_result_report(request)

    @app.post("/recommendations/preview")
    async def recommendations_preview(request: RecommendationRequest) -> RecommendationRun:
        return preview_recommendations(request)

    return app


app = create_app()
