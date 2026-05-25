import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.database import verify_db_connection
from app.routers.records import router as records_router

# Configure logging structure
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("mro-tts-app")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Startup Initialization
    logger.info("Initializing application startup sequence")

    # Establish Client
    app.state.http_client = httpx.AsyncClient(
        base_url=settings.OPENROUTER_BASE_URL,
        timeout=httpx.Timeout(30.0, read=60.0),
        headers={
            "HTTP-Referer": "https://mro-tts.vercel.app",
            "X-Title": "mro-tts-copilot",
            "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        },
    )
    logger.info("OpenRouter HTTP client pool established")

    # Verify Neon Database Connection
    db_verified = await verify_db_connection()
    if not db_verified:
        logger.error("Startup database validation check failed")
    else:
        logger.info("Startup database validation check passed")

    yield

    # Shutdown Cleanup
    logger.info("Initializing application shutdown sequence")
    if hasattr(app.state, "http_client") and app.state.http_client:
        await app.state.http_client.aclose()
        logger.info("OpenRouter HTTP client pool closed")


app = FastAPI(
    title="mro-tts Backend API",
    description="Realtime Aviation Maintenance QA & Validation Intelligence System",
    version="0.1.0",
    lifespan=lifespan,
)

from app.core.observability import init_observability
init_observability(app)

# CORS configurations
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register static files mapping
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Register routers
app.include_router(records_router, prefix="/api/v1/records", tags=["records"])


@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> dict[str, str]:
    """Basic service health liveness status verification probe."""
    db_ok = await verify_db_connection()
    return {
        "status": "healthy" if db_ok else "unhealthy",
        "service": "mro-tts-backend",
        "database": "connected" if db_ok else "disconnected",
    }
