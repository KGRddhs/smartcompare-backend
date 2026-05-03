"""Shared test configuration — loads .env before any test modules import."""
import os

from dotenv import load_dotenv

load_dotenv(override=True)

# Disable slowapi rate limiter for unit tests that call route functions
# directly (with MagicMock requests). Integration tests that need to verify
# rate-limiting behaviour patch `app.middleware.rate_limiter.limiter.enabled`
# back to True or drive routes via TestClient. Set BEFORE any test imports so
# the Limiter constructor sees enabled=False at module-load time.
os.environ.setdefault("RATE_LIMITER_ENABLED", "false")
