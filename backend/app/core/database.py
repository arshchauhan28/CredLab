"""
Database Setup and Connection Management.
Initializes SQLAlchemy engine, session maker, declarative base, and connection test utilities.
"""

import logging
from typing import Generator, Dict, Any
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings

logger = logging.getLogger(__name__)

# SQLAlchemy Engine
_connect_args = {}
if "sqlite" in settings.sqlalchemy_database_uri:
    _connect_args["check_same_thread"] = False
else:
    _connect_args["connect_timeout"] = 3

engine = create_engine(
    settings.sqlalchemy_database_uri,
    pool_pre_ping=True,
    echo=settings.DEBUG,
    # Sensible defaults for connection pooling
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    connect_args=_connect_args,
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Declarative Base for future ORM models
Base = declarative_base()


def get_db() -> Generator:
    """
    FastAPI dependency that provides a SQLAlchemy database session.
    Automatically closes the session when the request finishes.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_database_connection() -> Dict[str, Any]:
    """
    Executes a test query ('SELECT 1') against the database to verify connectivity.
    Returns a dictionary with status, message, and error details if any.
    """
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            row = result.fetchone()
            if row and row[0] == 1:
                return {
                    "connected": True,
                    "message": "Database connection established successfully.",
                    "database": settings.POSTGRES_DB,
                    "server": f"{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}",
                }
            return {
                "connected": False,
                "message": "Unexpected response from database query.",
                "database": settings.POSTGRES_DB,
            }
    except SQLAlchemyError as err:
        logger.error(f"Database connection error: {err}")
        return {
            "connected": False,
            "message": "Failed to connect to the PostgreSQL database.",
            "error_type": type(err).__name__,
            "details": str(err).splitlines()[0] if str(err) else "Unknown database error",
            "database": settings.POSTGRES_DB,
            "server": f"{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}",
        }
    except Exception as exc:
        logger.error(f"Unexpected error while testing database connection: {exc}")
        return {
            "connected": False,
            "message": "An unexpected error occurred while connecting to database.",
            "error_type": type(exc).__name__,
            "details": str(exc).splitlines()[0] if str(exc) else "Unknown error",
            "database": settings.POSTGRES_DB,
            "server": f"{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}",
        }
