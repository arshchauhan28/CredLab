"""
Database Connection Test Endpoint.
Verifies PostgreSQL connectivity via SQLAlchemy engine ping.
"""

from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel

from app.core.database import check_database_connection

router = APIRouter()


class DatabaseTestResponse(BaseModel):
    connected: bool
    message: str
    database: Optional[str] = None
    server: Optional[str] = None
    error_type: Optional[str] = None
    details: Optional[str] = None
    timestamp: str


@router.get("/db-test", response_model=DatabaseTestResponse, tags=["Database"])
async def test_db_connection() -> DatabaseTestResponse:
    """
    Tests direct connectivity to the configured PostgreSQL database.
    Returns status and diagnostic details.
    """
    result = check_database_connection()
    return DatabaseTestResponse(
        connected=result.get("connected", False),
        message=result.get("message", ""),
        database=result.get("database"),
        server=result.get("server"),
        error_type=result.get("error_type"),
        details=result.get("details"),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
