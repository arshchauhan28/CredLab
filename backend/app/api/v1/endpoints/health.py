"""
Health Check Endpoint.
Provides basic service availability status.
"""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class HealthResponse(BaseModel):
    status: str


@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def get_health() -> HealthResponse:
    """
    Standard health check endpoint.
    Returns:
        {"status": "ok"}
    """
    return HealthResponse(status="ok")
