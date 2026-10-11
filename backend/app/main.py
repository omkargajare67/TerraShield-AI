"""TerraShield AI FastAPI Application Entrypoint."""

from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.geospatial_routes import router as geospatial_router
from backend.app.api.geotechnical_routes import router as geotechnical_router
from backend.app.api.recommendation_routes import router as recommendation_router
from backend.app.api.routes import router as api_router
from backend.app.core.config import settings
from backend.app.schemas.health import HealthResponse

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=(
        "TerraShield AI - AI-Assisted Reforestation Site Planning & "
        "Environmental Risk Analysis (Phase 1 Foundation Prototype)"
    ),
    docs_url="/docs",
    redoc_url="/redoc",
)

# Enable CORS for local development and frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Service Health Check",
    tags=["System"],
)
async def health_check() -> HealthResponse:
    """Return the service health status, application mode, and metadata."""
    return HealthResponse(
        status="healthy",
        app_name=settings.PROJECT_NAME,
        version=settings.VERSION,
        mode=settings.APP_MODE,
        timestamp=datetime.now(timezone.utc),
        message="TerraShield AI Phase 1 API operational.",
    )


# Include API routers
app.include_router(api_router, prefix=settings.API_V1_STR, tags=["Analysis & Parcels"])
app.include_router(geospatial_router, prefix=settings.API_V1_STR, tags=["Geospatial Engine"])
app.include_router(geotechnical_router, prefix=settings.API_V1_STR, tags=["Geotechnical Intelligence"])
app.include_router(recommendation_router, prefix=settings.API_V1_STR, tags=["Spatial Recommendations"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
    )
