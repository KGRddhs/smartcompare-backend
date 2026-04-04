"""Sentry integration -- error monitoring and performance tracing."""
import os
import re
import logging

logger = logging.getLogger(__name__)

# Patterns to scrub from Sentry events
_SENSITIVE_PATTERNS = [
    (re.compile(r'eyJ[A-Za-z0-9_-]{20,}\.eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]+'), '[JWT_REDACTED]'),
    (re.compile(r'sk-proj-[A-Za-z0-9_-]+'), '[OPENAI_KEY_REDACTED]'),
    (re.compile(r'fc-[a-f0-9]{20,}'), '[FIRECRAWL_KEY_REDACTED]'),
    (re.compile(r'[a-f0-9]{40,}'), '[TOKEN_REDACTED]'),  # Generic long hex tokens
    (re.compile(r'Bearer\s+[A-Za-z0-9_.-]+'), 'Bearer [REDACTED]'),
]


def _scrub_string(value: str) -> str:
    """Remove sensitive patterns from a string."""
    for pattern, replacement in _SENSITIVE_PATTERNS:
        value = pattern.sub(replacement, value)
    return value


def _scrub_dict(data: dict) -> dict:
    """Recursively scrub sensitive values from a dict."""
    scrubbed = {}
    for key, value in data.items():
        if isinstance(value, str):
            scrubbed[key] = _scrub_string(value)
        elif isinstance(value, dict):
            scrubbed[key] = _scrub_dict(value)
        elif isinstance(value, list):
            scrubbed[key] = [_scrub_dict(v) if isinstance(v, dict) else (_scrub_string(v) if isinstance(v, str) else v) for v in value]
        else:
            scrubbed[key] = value
    return scrubbed


def _before_send(event, hint):
    """Scrub sensitive data from Sentry events before sending."""
    # Scrub exception values
    if "exception" in event:
        for exc in event["exception"].get("values", []):
            if "value" in exc and isinstance(exc["value"], str):
                exc["value"] = _scrub_string(exc["value"])
    # Scrub breadcrumbs
    if "breadcrumbs" in event:
        for crumb in event["breadcrumbs"].get("values", []):
            if "data" in crumb and isinstance(crumb["data"], dict):
                crumb["data"] = _scrub_dict(crumb["data"])
            if "message" in crumb and isinstance(crumb["message"], str):
                crumb["message"] = _scrub_string(crumb["message"])
    # Scrub request headers
    if "request" in event and "headers" in event["request"]:
        headers = event["request"]["headers"]
        if isinstance(headers, dict):
            for key in list(headers.keys()):
                if key.lower() in ("authorization", "x-admin-key", "cookie"):
                    headers[key] = "[REDACTED]"
    return event


def _strip_tokens_from_breadcrumb(breadcrumb, hint):
    """Redact tokens from Sentry breadcrumb URLs."""
    if breadcrumb.get("data") and isinstance(breadcrumb["data"], dict):
        url = breadcrumb["data"].get("url", "")
        if url:
            breadcrumb["data"]["url"] = _scrub_string(url)
    return breadcrumb


def init_sentry():
    """Initialize Sentry SDK. No-op if SENTRY_DSN not set."""
    dsn = os.getenv("SENTRY_DSN", "")
    if not dsn:
        logger.info("SENTRY_DSN not set -- Sentry disabled")
        return

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration

        sentry_sdk.init(
            dsn=dsn,
            integrations=[
                FastApiIntegration(transaction_style="endpoint"),
                StarletteIntegration(transaction_style="endpoint"),
            ],
            traces_sample_rate=0.1,
            environment=os.getenv("RAILWAY_ENVIRONMENT", "development"),
            release=os.getenv("RAILWAY_GIT_COMMIT_SHA", "unknown"),
            send_default_pii=False,
            before_send=_before_send,
            before_breadcrumb=_strip_tokens_from_breadcrumb,
        )
        logger.info("Sentry initialized successfully")
    except ImportError:
        logger.warning("sentry-sdk not installed -- Sentry disabled")
    except Exception as e:
        logger.warning(f"Sentry init failed: {e}")
