"""
Application entry point.

Usage:
    python run.py
"""

import sys
import traceback

try:
    import uvicorn
    from backend.config import settings
except ImportError as exc:
    print(f"[ERROR] Missing dependency: {exc}")
    print("Run: pip install -r requirements.txt")
    sys.exit(1)

if __name__ == "__main__":
    try:
        uvicorn.run(
            "backend.main:app",
            host=settings.HOST,
            port=settings.PORT,
            reload=settings.DEBUG,
            log_level="debug" if settings.DEBUG else "info",
        )
    except Exception:
        traceback.print_exc()
        sys.exit(1)
