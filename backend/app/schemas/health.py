"""Health check schema."""

from datetime import datetime
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(..., description="Service health status, e.g. healthy")
    app_name: str = Field(..., description="Application name")
    version: str = Field(..., description="Application version")
    mode: str = Field(..., description="Current running mode, e.g. demo")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="UTC timestamp of the health check")
    message: str = Field(..., description="Status message")
