"""
Application Configuration Module.
Loads settings from environment variables and .env file using pydantic-settings.
"""

from typing import List, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Base Application Settings
    PROJECT_NAME: str = "Secure Coding Assessment Platform"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # CORS Settings
    BACKEND_CORS_ORIGINS: Union[str, List[str]] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            # Support comma-separated origins or JSON array format
            if v.startswith("[") and v.endswith("]"):
                import json
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return ["http://localhost:5173", "http://127.0.0.1:5173"]

    @field_validator("CERTIFICATE_TRUSTED_PUBLIC_KEYS", mode="before")
    @classmethod
    def assemble_trusted_public_keys(cls, v: Union[dict, str, None]) -> dict:
        if isinstance(v, str):
            import json
            try:
                return json.loads(v)
            except Exception:
                return {}
        elif isinstance(v, dict):
            return v
        return {}

    # PostgreSQL Database Connection Parameters
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "your_secure_postgres_password"
    POSTGRES_DB: str = "secure_coding_db"

    # Direct database URL override (optional)
    DATABASE_URL: Union[str, None] = None

    # JWT Authentication Settings
    JWT_SECRET_KEY: str = "change-this-in-development-super-secret-key-32chars"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Judge0 Code Execution Configuration (Chunk 5)
    JUDGE0_API_URL: str = "https://ce.judge0.com"
    JUDGE0_API_KEY: Union[str, None] = None
    JUDGE0_TIMEOUT_SECONDS: float = 15.0
    JUDGE0_CPU_TIME_LIMIT: float = 2.0  # 2.0 seconds default CPU limit
    JUDGE0_MEMORY_LIMIT_KB: int = 128000  # 128 MB default memory limit in KB
    EXECUTION_MOCK_MODE: bool = False  # Set to True for offline/local deterministic mock execution

    # Optional OpenAI-compatible AI provider for test generation and feedback
    AI_API_KEY: Union[str, None] = None
    AI_BASE_URL: str = "https://api.openai.com/v1"
    AI_MODEL: str = "gpt-4o-mini"

    # Cryptographic Completion Certificates (Chunk 10)
    CERTIFICATE_ISSUER_NAME: str = "LabOS Sentinel"
    CERTIFICATE_SCHEMA_VERSION: str = "1.0"
    CERTIFICATE_KEY_ID: str = "labos-sentinel-dev-2026"
    CERTIFICATE_PRIVATE_KEY_HEX: Union[str, None] = None
    CERTIFICATE_PRIVATE_KEY_PATH: Union[str, None] = None
    CERTIFICATE_DEV_KEY_AUTOGEN: bool = False
    CERTIFICATE_TRUSTED_PUBLIC_KEYS: Union[dict, str] = {}

    @property
    def sqlalchemy_database_uri(self) -> str:
        """
        Returns the SQLAlchemy database URI using the psycopg (v3) driver.
        Ensures the URI uses the postgresql+psycopg:// dialect.
        """
        if self.DATABASE_URL:
            url = self.DATABASE_URL.strip()
            # If the user supplied standard postgresql:// or postgres://,
            # adapt it to postgresql+psycopg:// for SQLAlchemy 2.x
            if url.startswith("postgresql://"):
                url = url.replace("postgresql://", "postgresql+psycopg://", 1)
            elif url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql+psycopg://", 1)
            return url

        # Construct connection URI from components
        return (
            f"postgresql+psycopg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


# Global settings singleton
settings = Settings()
