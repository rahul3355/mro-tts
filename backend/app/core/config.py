from typing import Annotated, Any, ClassVar

from pydantic import BeforeValidator, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def parse_cors_origins(v: Any) -> list[str]:
    if isinstance(v, str) and not v.startswith("["):
        return [i.strip() for i in v.split(",")]
    if isinstance(v, (list, str)):
        return v  # type: ignore[return-value]
    raise ValueError(v)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore")

    # API Keys & Endpoints
    OPENROUTER_API_KEY: str = Field(..., description="API Key for OpenRouter service access")
    OPENROUTER_BASE_URL: str = Field(
        "https://openrouter.ai/api/v1",
        description="Base URL endpoint for OpenRouter queries",
    )


    PINECONE_API_KEY: str = Field(..., description="API Key for Pinecone vector engine")
    PINECONE_INDEX_NAME: str = Field("mro-tts-manuals", description="Index name for AMM vectors")
    PINECONE_INDEX_HOST: str = Field(
        "https://mro-tts-o133fy5.svc.aped-4627-b74a.pinecone.io",
        description="API host URL for Pinecone index REST endpoint",
    )
    PINECONE_DIMENSION: ClassVar[int] = 512

    # Database
    DATABASE_URL: str = Field(..., description="Neon PostgreSQL connection URL")
    DB_POOL_SIZE: int = Field(20, description="SQLAlchemy connection pool base size")
    DB_MAX_OVERFLOW: int = Field(10, description="SQLAlchemy connection pool overflow max size")

    # App Config
    ENVIRONMENT: str = Field("development", description="Deployment environment mode")
    CORS_ORIGINS: Annotated[list[str], BeforeValidator(parse_cors_origins)] = Field(
        ["*"],
        description="Comma-separated strings of allowed origins for CORS validation",
    )


settings = Settings()  # type: ignore[call-arg]
