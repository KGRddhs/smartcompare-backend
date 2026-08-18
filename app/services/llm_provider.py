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

DEFAULT IS A NO-OP: ``OPENAI_BASE_URL`` unset → ``None`` → the SDK uses its own
default (https://api.openai.com/v1) and behaviour is byte-identical to before
this module existed.

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
from typing import Optional

logger = logging.getLogger(__name__)

_ENV = "OPENAI_BASE_URL"

# Stock OpenAI, spelled out. This MUST be returned explicitly rather than None —
# see the note on provider_base_url().
STOCK_OPENAI_BASE_URL = "https://api.openai.com/v1"


def provider_base_url() -> str:
    """The OpenAI-compatible base URL to build clients with. NEVER ``None``.

    🔒 WHY NEVER None (regression 2026-08-17): openai-python resolves the value
    ITSELF when handed ``None`` — ``AsyncOpenAI.__init__`` does

        if base_url is None: base_url = os.environ.get("OPENAI_BASE_URL")
        if base_url is None: base_url = "https://api.openai.com/v1"

    so returning ``None`` for a MALFORMED setting handed the SDK the very value
    the guard had just rejected, and the client was built against it. Returning
    an EXPLICIT url is what makes the validation real.

    (The corollary: the SDK already supported ``OPENAI_BASE_URL`` natively. What
    this module adds is validation + a diagnostic label, NOT the capability.)

    Read FRESH per call (no module cache) so a Railway change applies on the next
    client construction with no redeploy.
    """
    raw = (os.getenv(_ENV) or "").strip()
    if not raw:
        return STOCK_OPENAI_BASE_URL
    if not raw.startswith(("http://", "https://")):
        # Fail SAFE: a typo must not point the app at a bogus host.
        logger.warning(
            "[llm_provider] %s=%r is not an http(s) URL — ignoring, using stock OpenAI",
            _ENV, raw,
        )
        return STOCK_OPENAI_BASE_URL
    return raw


def is_custom_provider() -> bool:
    """True iff a VALID non-stock endpoint is configured."""
    return provider_base_url() != STOCK_OPENAI_BASE_URL


def describe_provider() -> str:
    """Short human label for logs/diagnostics. Never includes credentials."""
    base = provider_base_url()
    return f"openai-compatible@{base}" if is_custom_provider() else "openai"
