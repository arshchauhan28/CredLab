"""
FastAPI Application Entry Point.
Configures FastAPI instance, CORS middleware, API routing, and lifecycle events.
LabOS Sentinel Platform 2026.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import check_database_connection
from app.api.v1.router import api_router

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("secure_coding_platform")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager for startup and shutdown procedures.
    """
    logger.info("Initializing Secure Coding Assessment Platform Backend...")
    logger.info(f"Environment: {settings.ENVIRONMENT} | Debug: {settings.DEBUG}")
    logger.info(f"CORS Allowed Origins: {settings.BACKEND_CORS_ORIGINS}")
    
    # Check database connection on startup (non-blocking notification)
    db_status = check_database_connection()
    if db_status["connected"]:
        logger.info(f"✓ Database connected successfully to {db_status.get('server')}/{db_status.get('database')}")
    else:
        logger.warning(f"⚠ Database not yet reachable: {db_status.get('message')}")
        logger.warning("Ensure PostgreSQL is running and credentials in backend/.env are correct.")

    yield

    logger.info("Shutting down Secure Coding Assessment Platform Backend...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API for the Secure Coding Assessment Platform. Foundation chunk.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Configure CORS Middleware
# Allows frontend development server to make cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.method} {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred. Please try again later.",
            "path": str(request.url.path),
        },
    )


# Include API v1 routes mounted at /api
app.include_router(api_router, prefix=settings.API_V1_STR)
if settings.API_V1_STR != "/api/v1":
    app.include_router(api_router, prefix="/api/v1")



@app.get("/", tags=["Root"])
async def root():
    """
    Root landing endpoint providing system information and documentation links.
    """
    return {
        "name": settings.PROJECT_NAME,
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "docs": "/docs",
        "health": f"{settings.API_V1_STR}/health",
    }
