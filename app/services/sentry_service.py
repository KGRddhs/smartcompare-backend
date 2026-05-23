"""Sentry integration -- error monitoring and performance tracing."""
import os
import re
import logging

logger = logging.getLogger(__name__)

# Patterns to scrub from Sentry events.
# M4 (audit 2026-05-22): widened the generic hex pattern from {40,} to {32,}
# so 32-char lowercase Serper API keys (e.g., 1d3cf422...) get caught.
# Also added key-name scrubbing below so any value living in a dict key
# matching api_key / token / secret gets redacted regardless of format —
# defense-in-depth against future provider keys (Scrape.do, Upstash REST,
# etc.) that don't match any specific pattern here.
_SENSITIVE_PATTERNS = [
    (re.compile(r'eyJ[A-Za-z0-9_-]{20,}\.eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]+'), '[JWT_REDACTED]'),
    (re.compile(r'sk-proj-[A-Za-z0-9_-]+'), '[OPENAI_KEY_REDACTED]'),
    (re.compile(r'fc-[a-f0-9]{20,}'), '[FIRECRAWL_KEY_REDACTED]'),
    (re.compile(r'[a-f0-9]{32,}'), '[TOKEN_REDACTED]'),  # Generic long hex tokens (Serper 32+, SHA-256 64, etc.)
    (re.compile(r'Bearer\s+[A-Za-z0-9_.-]+'), 'Bearer [REDACTED]'),
]

# Bundle D Task 1.B.6 (R21) — query-string scrubbing for free-text user input.
# Targets the five param names that carry user-typed content in this API:
#   q, query, email, search, text
# Captures everything from `&<name>=` (or `?<name>=`) up to the next `&` or
# end-of-URL, replacing the value with [QUERY_REDACTED]. Preserves bookkeeping
# params (?nocache=, ?limit=, ?offset=, etc.) by NOT matching their names.
# `?token=` is already covered by the `_scrub_dict` key-name denylist below,
# but the wholesale `[a-f0-9]{32,}` token pattern also catches hex tokens that
# leak into URLs.
_QUERY_STRING_PII_PARAMS = ("q", "query", "email", "search", "text")
_QUERY_STRING_SCRUB_PATTERN = re.compile(
    r"(?<=[?&])(" + "|".join(_QUERY_STRING_PII_PARAMS) + r")=[^&#]*",
    re.IGNORECASE,
)


def _scrub_query_string(url: str) -> str:
    """Replace PII-carrying query-string values with [QUERY_REDACTED].

    Bundle D R21: regex is targeted (matches `?q=`, `?query=`, `?email=`,
    `?search=`, `?text=`) so legitimate non-PII params like `?nocache=true`
    or `?limit=20` round-trip untouched. Existing `?token=` handling lives
    in `_scrub_dict` (key-name denylist) and the wholesale hex pattern.
    """
    if not url:
        return url
    if "?" not in url and "=" not in url:
        # Neither a full URL with query string NOR a raw query_string field —
        # nothing to scrub.
        return url
    return _QUERY_STRING_SCRUB_PATTERN.sub(r"\1=[QUERY_REDACTED]", url)


def _scrub_raw_query_string(qs: str) -> str:
    """Scrub a RAW query-string fragment (no leading `?`).

    Bundle D R21 follow-up (Frontend cross-QA `c12a7c6` review): modern
    sentry-python populates `event.request.query_string` separately from
    `event.request.url` — a string like `q=foo&search=bar` with no `?`
    prefix. The lookbehind in `_QUERY_STRING_SCRUB_PATTERN` requires `?`
    or `&` immediately before the param name, so the very first param
    of a raw query_string would slip through `_scrub_query_string`.

    Fix: normalize by prepending `?` before regex application, then
    strip the prepended char back off when returning. Lookbehind now
    matches uniformly across both shapes.
    """
    if not qs:
        return qs
    # Bytes from some sentry-sdk versions — decode defensively.
    if isinstance(qs, (bytes, bytearray)):
        try:
            qs = qs.decode("utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            return qs
    if not isinstance(qs, str):
        return qs
    normalized = "?" + qs
    scrubbed = _QUERY_STRING_SCRUB_PATTERN.sub(r"\1=[QUERY_REDACTED]", normalized)
    # Strip the prepended `?` back off — caller stores raw query_string.
    return scrubbed[1:] if scrubbed.startswith("?") else scrubbed

# Key-name denylist (case-insensitive substring match). When _scrub_dict
# encounters a string value under a key matching one of these, the whole
# value is replaced — regardless of whether the value itself matches a
# pattern above. Catches provider-specific tokens whose shape we don't
# explicitly pattern-match (e.g., Scrape.do, Upstash REST token, future).
_SENSITIVE_KEY_FRAGMENTS = ("api_key", "apikey", "token", "secret", "password")


def _scrub_string(value: str) -> str:
    """Remove sensitive patterns from a string."""
    for pattern, replacement in _SENSITIVE_PATTERNS:
        value = pattern.sub(replacement, value)
    return value


def _key_is_sensitive(key: str) -> bool:
    """True when a dict key name suggests its value is a secret."""
    lowered = key.lower()
    return any(frag in lowered for frag in _SENSITIVE_KEY_FRAGMENTS)


def _scrub_dict(data: dict) -> dict:
    """Recursively scrub sensitive values from a dict.

    M4 fix: if the key name suggests a secret (api_key / token / secret /
    password), redact the value wholesale even when the string content
    doesn't match a specific pattern.
    """
    scrubbed = {}
    for key, value in data.items():
        if isinstance(key, str) and _key_is_sensitive(key) and value is not None:
            scrubbed[key] = "[REDACTED]"
        elif isinstance(value, str):
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
    # Scrub request headers + query-string
    if "request" in event:
        if "headers" in event["request"]:
            headers = event["request"]["headers"]
            if isinstance(headers, dict):
                for key in list(headers.keys()):
                    if key.lower() in ("authorization", "x-admin-key", "cookie"):
                        headers[key] = "[REDACTED]"
        # Bundle D Task 1.B.6 (R21) — scrub PII query-string values from request URL
        if isinstance(event["request"].get("url"), str):
            event["request"]["url"] = _scrub_query_string(event["request"]["url"])
        # Bundle D R21 follow-up (Frontend cross-QA review on c12a7c6):
        # modern sentry-python FastAPI/Starlette integrations populate
        # `request.query_string` separately as raw `key=val&key2=val2`
        # (no leading `?`). The lookbehind in _QUERY_STRING_SCRUB_PATTERN
        # would miss the first param of a raw query_string, so route it
        # through _scrub_raw_query_string which normalizes by prepending
        # `?` before regex application.
        raw_qs = event["request"].get("query_string")
        if raw_qs is not None:
            event["request"]["query_string"] = _scrub_raw_query_string(raw_qs)
    return event


def _strip_tokens_from_breadcrumb(breadcrumb, hint):
    """Redact tokens + PII query strings from Sentry breadcrumb URLs."""
    if breadcrumb.get("data") and isinstance(breadcrumb["data"], dict):
        url = breadcrumb["data"].get("url", "")
        if url:
            # Bundle D R21: scrub PII query-string values BEFORE token-pattern
            # scrub so a URL like `?q=eyJabc...` doesn't get masked by the JWT
            # pattern but then leak the rest of the query value.
            url = _scrub_query_string(url)
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
