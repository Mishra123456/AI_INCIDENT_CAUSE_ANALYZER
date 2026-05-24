"""
Application configuration management.

Loads settings from environment variables with sensible defaults
for local development. All secrets are read from .env files — never
hardcoded.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Locate the .env file relative to the project root (one level up from
# the backend/ package).
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_ENV_PATH = _PROJECT_ROOT / ".env"

if _ENV_PATH.exists():
    load_dotenv(_ENV_PATH, override=True)


class Settings:
    """Immutable application settings sourced from environment variables."""

    # Google Gemini
    GEMINI_API_KEY: str = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

    # Server
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # Rate limiting (per-IP)
    RATE_LIMIT_REQUESTS: int = int(os.getenv("RATE_LIMIT_REQUESTS", "300"))
    RATE_LIMIT_WINDOW_SECONDS: int = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))

    # Static / template paths
    FRONTEND_DIR: Path = _PROJECT_ROOT / "frontend"

    @classmethod
    def validate(cls) -> list[str]:
        """Return a list of configuration warnings (empty = all good)."""
        warnings: list[str] = []
        if not cls.GEMINI_API_KEY:
            warnings.append(
                "GEMINI_API_KEY is not set — AI analysis will be unavailable."
            )
        return warnings


settings = Settings()
