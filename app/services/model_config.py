"""Single source of truth for the OpenAI model ids the request path uses.

Before this module the ids were bare literals spread across 7 service files, so
changing a model meant editing every one of them and redeploying, and a running
deployment could not report which model it was actually using.

Every id is env-overridable (``OPENAI_MODEL_<ROLE>``) and the defaults are the
exact ids that were hardcoded previously, so with no env set behavior is
unchanged. Selecting a different model is then a Railway env change with an
instant rollback — no code edit, no deploy.

Resolution is per call, not at import, matching the repo's existing flag helpers
(``exact_gate_enabled``, ``_brightdata_enabled``): a Railway variable change
takes effect on the next request rather than the next restart.

NOTE: this module deliberately does NOT live in ``app/config.py``. That module
declares seven required pydantic fields and instantiates ``Settings()`` at import,
so importing it raises ``ValidationError`` wherever those env vars are absent
(CI, local tooling) — which is why nothing imports it today. Model ids must be
resolvable with zero credentials present.

BEFORE SELECTING A GPT-5 ID (researched against developers.openai.com, 2026-08-24
— read this first, the ids are env-selectable and these are hard 400s):

* ``temperature`` — GPT-5 models are reasoning models and accept only the default
  (1). ``temperature=0`` is rejected. ``sampling_kwargs()`` drops it for those ids,
  but the verdict call's determinism guarantee goes with it.
* ``max_tokens`` — rejected; ``max_completion_tokens`` is required.
  ``token_limit_kwargs()`` handles this.
* ``max_completion_tokens`` counts INVISIBLE REASONING TOKENS against the same
  budget. A straight ``max_tokens=1000`` → ``max_completion_tokens=1000`` carry-over
  can return empty content with ``finish_reason="length"`` because reasoning
  consumed the cap. Raise the caps and/or pass ``reasoning_effort="minimal"``.
* ``gpt-5-pro`` is Responses-API only and will fail on chat completions.

So flipping a model here is a one-line env change, but it is NOT a free one:
smoke-test the target id on a real key before trusting it in production.
"""
import os
import re
from typing import Any, Dict, Optional

# The ids these roles resolved to before #58 made them configurable.
_ROLE_DEFAULTS: Dict[str, str] = {
    # Verdict prose — the only routinely-gpt-4o call, and the most expensive
    # single call in a comparison.
    "verdict": "gpt-4o",
    # Specs / prices / reviews / parsing — the high-volume extraction workhorse.
    "standard": "gpt-4o-mini",
    # Camera product identification (image input).
    "vision": "gpt-4o-mini",
    # Verdict self-critique pass (flag-gated, ENABLE_SELF_CRITIQUE).
    "critic": "gpt-4o-mini",
    # Content moderation — a separate endpoint, priced free.
    "moderation": "omni-moderation-latest",
}

# GPT-5-family ids take `max_completion_tokens`; the GPT-4o/4.1 families take
# `max_tokens`. Sending the wrong one is a 400, so the choice is made from the
# model id in one place instead of at each call site.
_GPT5_FAMILY = re.compile(r"^gpt-5(\b|[.\-])", re.IGNORECASE)


def _resolve(role: str) -> str:
    """Return the configured id for ``role``, falling back to its default.

    A set-but-blank env var (a common Railway slip) resolves to the default
    rather than to the empty string, which would otherwise 400 at the API.
    """
    default = _ROLE_DEFAULTS[role]
    raw = os.getenv(f"OPENAI_MODEL_{role.upper()}")
    if raw is None:
        return default
    return raw.strip() or default


def verdict_model() -> str:
    """Model for verdict prose (``priority="high"`` in the router)."""
    return _resolve("verdict")


def standard_model() -> str:
    """Model for specs, prices, reviews, parsing and targeted fills."""
    return _resolve("standard")


def vision_model() -> str:
    """Model for camera product identification."""
    return _resolve("vision")


def critic_model() -> str:
    """Model for the verdict self-critique pass."""
    return _resolve("critic")


def moderation_model() -> str:
    """Model for the moderation endpoint."""
    return _resolve("moderation")


def uses_completion_token_param(model: str) -> bool:
    """True when ``model`` expects ``max_completion_tokens`` over ``max_tokens``."""
    return bool(_GPT5_FAMILY.match((model or "").strip()))


def sampling_kwargs(model: str, temperature: Optional[float]) -> Dict[str, Any]:
    """Return the sampling kwarg appropriate to ``model``.

    GPT-5-family models are reasoning models and reject any non-default
    ``temperature`` with a 400 ("Only the default (1) value is supported").
    Sending ``temperature=0`` to one is a hard failure, so it is omitted for
    those ids and passed through unchanged for everything else.

    CAVEAT for whoever flips the verdict model: the verdict call relies on
    ``temperature=0`` for determinism (an A/B recorded in
    docs/plans/2026-06-12-s2-shadow-results.md attributes the entire
    winner-variance bucket to it). Dropping it on a GPT-5 id is NOT free —
    re-run that A/B before trusting the output.
    """
    if temperature is None or uses_completion_token_param(model):
        return {}
    return {"temperature": temperature}


def token_limit_kwargs(model: str, limit: Optional[int]) -> Dict[str, Any]:
    """Return the token-cap kwarg appropriate to ``model``.

    Spread into the ``chat.completions.create`` call so a model flipped by env
    keeps its caller's cap instead of silently losing it:

        **token_limit_kwargs(model, 1000)

    Unknown ids keep the legacy ``max_tokens`` form rather than guessing.
    """
    if limit is None:
        return {}
    if uses_completion_token_param(model):
        return {"max_completion_tokens": limit}
    return {"max_tokens": limit}


def resolved_models() -> Dict[str, str]:
    """All roles resolved — for the one-line startup log."""
    return {role: _resolve(role) for role in _ROLE_DEFAULTS}
