"""
Sentinel AI — FastAPI Application Factory

Sets up the ASGI application with middleware, routes, static file
serving, and startup diagnostics.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.config import settings
from backend.api.routes import router as api_router
from backend.utils.guardrails import RateLimitMiddleware, SecurityHeadersMiddleware

# ---------------------------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("sentinel")


# ---------------------------------------------------------------------------
# Application lifecycle
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run startup and shutdown tasks."""
    logger.info("=" * 60)
    logger.info("  Sentinel AI — Incident Root Cause Analyzer")
    logger.info("=" * 60)

    warnings = settings.validate()
    for w in warnings:
        logger.warning("CONFIG: %s", w)

    # Pre-generate incident data so the first request is fast
    from backend.services.mock_data import generate_incidents
    generate_incidents()
    logger.info("Mock incident data pre-generated")
    logger.info("Server ready at http://%s:%s", settings.HOST, settings.PORT)

    yield

    logger.info("Sentinel AI shutting down")


# ---------------------------------------------------------------------------
# Create the FastAPI instance
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Sentinel AI",
    description="AI-Powered Incident Root Cause Analyzer for SRE Teams",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url=None,
)

# Middleware (order matters — outermost first)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    RateLimitMiddleware,
    max_requests=settings.RATE_LIMIT_REQUESTS,
    window_seconds=settings.RATE_LIMIT_WINDOW_SECONDS,
)

# API routes
app.include_router(api_router)

# Static files (CSS, JS, images)
app.mount("/static", StaticFiles(directory=str(settings.FRONTEND_DIR / "static")), name="static")


# Serve the SPA for all non-API routes
@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    """Serve the single-page application."""
    return FileResponse(str(settings.FRONTEND_DIR / "index.html"))
