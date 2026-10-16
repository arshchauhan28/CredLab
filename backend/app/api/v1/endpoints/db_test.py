import logging
import secrets
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import check_database_connection, engine, get_db

logger = logging.getLogger(__name__)
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


@router.get("/db-test/diagnostic", tags=["Database"])
def get_db_diagnostic(
    auth_header: Optional[str] = Header(None, alias="Authorization"),
    x_diagnostic_key: Optional[str] = Header(None, alias="X-Diagnostic-Key"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Secure diagnostic endpoint to inspect active database connection metadata.
    Requires either:
    1. 'X-Diagnostic-Key' header matching server's configured JWT_SECRET_KEY, OR
    2. Bearer token belonging to an active ADMIN user.

    Never exposes DATABASE_URL, username, password, or credentials.
    """
    is_authorized = False

    # Check 1: Diagnostic Key Header
    if x_diagnostic_key and settings.JWT_SECRET_KEY:
        if secrets.compare_digest(x_diagnostic_key.strip(), settings.JWT_SECRET_KEY.strip()):
            is_authorized = True

    # Check 2: Bearer Token for Admin
    if not is_authorized and auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1].strip()
        try:
            from app.core.security import decode_access_token
            from app.models.user import User, UserRole

            payload = decode_access_token(token)
            user_id = int(payload.get("sub", 0))
            user = db.query(User).filter(User.id == user_id, User.is_active.is_(True)).first()
            if user and user.role == UserRole.ADMIN:
                is_authorized = True
        except Exception:
            pass

    if not is_authorized:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Diagnostic authorization required. Provide valid X-Diagnostic-Key or Admin Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        with engine.connect() as conn:
            # Query active database, schema, and PostgreSQL engine version
            meta_row = conn.execute(
                text("SELECT current_database(), current_schema(), version();")
            ).fetchone()
            current_db = meta_row[0] if meta_row else None
            current_schema = meta_row[1] if meta_row else None
            pg_version = meta_row[2] if meta_row else None

            # Query applied alembic migration version
            alembic_version = None
            try:
                alembic_row = conn.execute(
                    text("SELECT version_num FROM alembic_version;")
                ).fetchone()
                if alembic_row:
                    alembic_version = alembic_row[0]
            except Exception:
                alembic_version = "table_not_found"

            # Query row counts of core authentication tables
            user_count = None
            auth_enrollment_count = None
            try:
                user_count = conn.execute(text("SELECT count(*) FROM users;")).scalar()
            except Exception:
                pass
            try:
                auth_enrollment_count = conn.execute(
                    text("SELECT count(*) FROM authorized_enrollments;")
                ).scalar()
            except Exception:
                pass

            return {
                "status": "connected",
                "engine_dialect": engine.dialect.name,
                "engine_host": engine.url.host or "localhost",
                "engine_port": engine.url.port or 5432,
                "current_database": current_db,
                "current_schema": current_schema,
                "server_version": pg_version,
                "alembic_version": alembic_version,
                "table_counts": {
                    "users": user_count,
                    "authorized_enrollments": auth_enrollment_count,
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
    except Exception as exc:
        logger.error(f"Diagnostic query failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Diagnostic query error: {str(exc).splitlines()[0]}",
        )
