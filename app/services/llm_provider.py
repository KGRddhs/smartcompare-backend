"""OpenAI-compatible provider indirection (2026-08-17).

Every LLM call in this codebase goes through ``openai.AsyncOpenAI``. That SDK
talks to any OpenAI-COMPATIBLE endpoint when given a ``base_url``, so a single
env var is enough to move the whole app off api.openai.com without touching a
call site.

WHY THIS EXISTS: on 2026-08-17 both OpenAI keys returned 429
``credit_balance_exhausted`` and every ``/text/compare`` failed at product
identification. The free-trial grant is a one-time expiring credit, not a daily
allowance, so it does not come back on its own. This module makes the
provider a CONFIG decision instead of a code change.

CONTRACT of ``provider_base_url()`` (read fresh on every call):
  * unset, blank or whitespace-only → the EXPLICIT stock URL
    ``https://api.openai.com/v1``, never ``None`` (see provider_base_url()).
    The client ends up where the SDK default puts it (``client.base_url`` is
    ``https://api.openai.com/v1/`` either way). The only difference in object
    state is the SDK's private ``_base_url_was_default`` flag: False here, True
    for the SDK default. openai 3.3.1 reads that flag only in
    copy()/with_options() when the workload-identity mode changes, and this app
    configures no workload identity, so the difference has no effect here.
  * an http(s) URL with a host (the scheme is matched case-insensitively and
    surrounding whitespace is stripped) → that URL, with the scheme lower-cased.
  * any other non-blank value → FAIL CLOSED. The value is returned unchanged
    (after stripping whitespace), so every client is built against it and every
    request fails at request time with ``openai.APIConnectionError``. One
    ``logger.error`` per call names OPENAI_BASE_URL, with the value redacted to
    its length and first 8 characters. It is NEVER swapped for stock OpenAI: an
    operator who set the variable meant to route AWAY from api.openai.com
    (a gateway, data residency, cost), and a typo must not send that key and the
    users' prompts to OpenAI instead. How the request fails depends on the
    value (measured on openai 3.3.1 / httpx 0.28.1):
      - no http(s) scheme at all (``not-a-url``, ``api.gateway.test/v1``,
        ``//proto``, ``ftp://x``): httpx raises ``UnsupportedProtocol`` before
        any DNS lookup or connect.
      - an http(s) scheme but no host (``https://``, or a scheme typo such as
        ``https:/gw.test/v1`` or ``http:gw.test/v1``): httpx parses an EMPTY
        host, makes one name-resolution attempt on that empty host, and fails
        with ``ConnectError``. Nothing is sent to OpenAI or to the intended
        gateway, but the resolver is still called.
      - an http(s) scheme with an authority ``urlsplit`` cannot parse (an
        unclosed IPv6 bracket, ``https://[gw.test/v1``): httpx percent-encodes
        it and makes one resolution attempt on the mangled name
        (``%5bgw.test``), which fails with ``ConnectError``.

SCOPE — read before relying on it:
  * This covers providers that accept the SAME MODEL NAMES this codebase sends
    (``gpt-4o-mini``, ``gpt-4o``, ``omni-moderation-latest``). That means Azure
    OpenAI, and any gateway that maps model names server-side (LiteLLM proxy,
    Cloudflare AI Gateway, an OpenRouter-style alias layer).
  * A provider with its OWN model names (Groq's ``llama-3.3-70b``, DeepSeek's
    ``deepseek-chat``) ALSO needs model-name mapping — the model strings are
    still hardcoded at ~12 call sites. Point such a provider at a mapping
    gateway, or add model indirection as a follow-up.
  * ``client.moderations.create`` (content_safety L3) is OpenAI-specific. Most
    compatible providers do not implement it. That path already FAILS OPEN on
    exception, so a swap degrades to "no L3 moderation" rather than breaking —
    a real safety reduction to weigh, not a crash.
"""
from __future__ import annotations

import logging
import os
from urllib.parse import urlsplit, urlunsplit

logger = logging.getLogger(__name__)

_ENV = "OPENAI_BASE_URL"

# Stock OpenAI, spelled out. This MUST be returned explicitly rather than None —
# see the note on provider_base_url().
STOCK_OPENAI_BASE_URL = "https://api.openai.com/v1"

_HTTP_PREFIXES = ("http://", "https://")


def _is_http_url(value: str) -> bool:
    """True iff ``value`` is ``http://`` or ``https://`` (scheme matched
    case-insensitively) followed by a non-empty host."""
    if not value.lower().startswith(_HTTP_PREFIXES):
        return False
    try:
        return bool(urlsplit(value).hostname)
    except ValueError:
        return False


def _redacted(value: str) -> str:
    """Length and first 8 characters only. The raw value may carry userinfo."""
    return f"len={len(value)}, starts={value[:8]!r}"


def _is_stock(base: str) -> bool:
    """True iff ``base`` is the stock OpenAI endpoint, however it is spelled
    (scheme/host case, trailing slash)."""
    try:
        parts = urlsplit(base)
    except ValueError:
        return False
    return (
        parts.scheme.lower() == "https"
        and parts.netloc.lower() == "api.openai.com"
        and parts.path.rstrip("/") == "/v1"
        and not parts.query
        and not parts.fragment
    )


def _without_credentials(url: str) -> str:
    """``url`` with userinfo, query string and fragment removed.

    An ``@`` that lands in the path, query or fragment means the userinfo held
    an unencoded ``/``, ``?`` or ``#``, so the parser split the password across
    components. Nothing after the scheme can then be shown safely, and the
    whole location is redacted.
    """
    try:
        parts = urlsplit(url)
    except ValueError:
        return f"{url.split(':', 1)[0].lower()}://<unparseable>"
    if "@" in parts.path or "@" in parts.query or "@" in parts.fragment:
        return f"{parts.scheme}://<redacted>"
    host = parts.netloc.rpartition("@")[2]
    return urlunsplit((parts.scheme, host, parts.path, "", ""))


def provider_base_url() -> str:
    """The OpenAI-compatible base URL to build clients with. NEVER ``None``.

    🔒 WHY NEVER None (regression 2026-08-17): openai-python resolves the value
    ITSELF when handed ``None`` — ``AsyncOpenAI.__init__`` does

        if base_url is None: base_url = os.environ.get("OPENAI_BASE_URL")
        if base_url is None: base_url = "https://api.openai.com/v1"

    so returning ``None`` would let the SDK re-read the variable behind this
    module's back. The unset case therefore returns the stock URL explicitly.

    A MALFORMED value (anything but an http(s) URL with a host) is returned as
    given, and that is deliberate: it FAILS CLOSED. Every request then fails at
    request time, and one ERROR line names the variable. A value with no http(s)
    scheme fails before any DNS lookup or connect; a value with an http(s) scheme
    but no parseable host (``https://``, ``https:/gw.test``,
    ``https://[gw.test``) fails after one resolution attempt on an empty or
    mangled host name. None of them reaches api.openai.com or the intended
    gateway. Substituting stock OpenAI here would fail OPEN: a mistyped gateway
    URL would send the configured key and the users' prompts to api.openai.com.
    See the module docstring for the full contract.

    (The corollary: the SDK already supported ``OPENAI_BASE_URL`` natively. What
    this module adds is validation, a loud error and a diagnostic label, NOT the
    capability.)

    Read FRESH per call (no module cache) so a Railway change applies on the next
    client construction with no redeploy.
    """
    raw = (os.getenv(_ENV) or "").strip()
    if not raw:
        return STOCK_OPENAI_BASE_URL
    if _is_http_url(raw):
        scheme, sep, rest = raw.partition("://")
        return scheme.lower() + sep + rest
    logger.error(
        "[llm_provider] %s is set but is not an http(s) URL with a host (%s). "
        "NOT falling back to stock OpenAI: clients are built against this value "
        "and every LLM request will fail until %s is fixed or unset.",
        _ENV, _redacted(raw), _ENV,
    )
    return raw


def is_custom_provider() -> bool:
    """True iff a VALID (http/https) non-stock endpoint is configured.

    False when unset, for any spelling of the stock URL, and for a malformed
    value (which is not a usable provider; see provider_base_url()).
    """
    base = provider_base_url()
    return _is_http_url(base) and not _is_stock(base)


def describe_provider() -> str:
    """Short human label for logs/diagnostics. Never includes credentials.

    ``openai`` for the stock endpoint, ``openai-compatible@<url>`` for a valid
    custom endpoint (userinfo, query string and fragment stripped; the whole
    location becomes ``<redacted>`` when an unencoded ``/``, ``?`` or ``#`` in
    the password makes the split ambiguous), and
    ``misconfigured:OPENAI_BASE_URL`` for a malformed value, which is never
    echoed.
    """
    base = provider_base_url()  # once: a malformed value logs once per call
    if _is_stock(base):
        return "openai"
    if not _is_http_url(base):
        return f"misconfigured:{_ENV}"
    return f"openai-compatible@{_without_credentials(base)}"
