"""
Safety guardrails: rate limiting, input sanitization, and request validation.

These middleware components protect the application from abuse and ensure
that all data flowing through the system is safe to process.
"""

from __future__ import annotations

import html
import re
import time
import logging
from collections import defaultdict
from typing import Callable

from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from backend.config import settings

logger = logging.getLogger("sentinel.guardrails")


# ---------------------------------------------------------------------------
# Rate limiter (in-memory, per-IP, sliding window)
# ---------------------------------------------------------------------------

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding-window rate limiter that tracks requests per client IP."""

    def __init__(self, app, max_requests: int = 30, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window = window_seconds
        self._buckets: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for static assets
        if request.url.path.startswith("/static"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        cutoff = now - self.window

        # Prune expired entries
        bucket = self._buckets[client_ip]
        self._buckets[client_ip] = [ts for ts in bucket if ts > cutoff]

        if len(self._buckets[client_ip]) >= self.max_requests:
            logger.warning("Rate limit exceeded for %s", client_ip)
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "rate_limit_exceeded",
                    "message": "Too many requests. Please wait before retrying.",
                    "retry_after_seconds": self.window,
                },
            )

        self._buckets[client_ip].append(now)
        response = await call_next(request)
        return response


# ---------------------------------------------------------------------------
# Input sanitization utilities
# ---------------------------------------------------------------------------

_DANGEROUS_PATTERNS = re.compile(
    r"(<script|javascript:|on\w+\s*=|eval\(|exec\(|__import__|subprocess)",
    re.IGNORECASE,
)


def sanitize_text(value: str, max_length: int = 4096) -> str:
    """Strip dangerous content from user-provided text."""
    if not value:
        return value

    # Truncate
    cleaned = value[:max_length]

    # HTML-escape to prevent XSS
    cleaned = html.escape(cleaned, quote=True)

    # Remove known dangerous patterns
    cleaned = _DANGEROUS_PATTERNS.sub("[FILTERED]", cleaned)

    return cleaned.strip()


def validate_incident_id(incident_id: str) -> str:
    """Ensure incident IDs conform to expected format."""
    cleaned = incident_id.strip()
    if not re.match(r"^[A-Za-z0-9\-_]{1,64}$", cleaned):
        raise HTTPException(
            status_code=400,
            detail="Invalid incident ID format.",
        )
    return cleaned


# ---------------------------------------------------------------------------
# Security headers middleware
# ---------------------------------------------------------------------------

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Inject standard security headers into every response."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response
