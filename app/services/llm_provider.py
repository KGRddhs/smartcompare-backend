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


def provider_base_url() -> Optional[str]:
    """The configured OpenAI-compatible base URL, or ``None`` for stock OpenAI.

    Read FRESH per call (no module-level cache) so a Railway change takes effect
    on the next client construction without a code deploy. Whitespace-only or
    unset → ``None``, which the SDK treats exactly as "no base_url given".
    """
    raw = (os.getenv(_ENV) or "").strip()
    if not raw:
        return None
    if not raw.startswith(("http://", "https://")):
        # Fail SAFE: a malformed value must not silently point the app at a
        # bogus host — fall back to stock OpenAI and say so loudly.
        logger.warning(
            "[llm_provider] %s=%r is not an http(s) URL — ignoring, using stock OpenAI",
            _ENV, raw,
        )
        return None
    return raw


def describe_provider() -> str:
    """Short human label for logs/diagnostics. Never includes credentials."""
    base = provider_base_url()
    return f"openai-compatible@{base}" if base else "openai"
