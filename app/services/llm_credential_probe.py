"""MON1 LLM-CREDENTIAL-HEALTH: the DARK active credential check (a lifespan task).

ENABLE_LLM_CREDENTIAL_PROBE (default OFF, read per tick with the house idiom as the
FIRST statement of `tick()`): OFF, a tick builds no client and does no I/O. ON, each
tick makes ONE metadata call per in-use provider (models.retrieve: GET
/v1/models/{model}, no tokens) under a hard CALL_TIMEOUT_SECONDS, never retried, off
the request path, and feeds the outcome to the credential-state leaf with source
`probe`. LLM_CREDENTIAL_PROBE_INTERVAL_SECONDS (default 900, floor 300) spaces the
ticks; the first one runs FIRST_DELAY_SECONDS after startup.

A probe outcome is weaker evidence than a dispatch outcome (R-MON1-17 / R-MON1-18):
a probe 401 / 403 rejects only with the structured invalid-credential signal, and a
probe success never clears a quota state or a dispatch-sourced 403; every other
probe failure is inconclusive and changes nothing.

No spend admit, no usage-ledger record, no breaker admission (it is not a
completion). The provider modules are imported inside functions; the clients are
the existing ones (openai_service.get_client, llm_router._client_for), copied with
`with_options`, so no new host, constructor or credential name appears here.
"""

import asyncio
import logging
import math
import os
import time

from app.services import llm_credential_health as _cred_health

logger = logging.getLogger(__name__)

FLAG = "ENABLE_LLM_CREDENTIAL_PROBE"
INTERVAL_ENV = "LLM_CREDENTIAL_PROBE_INTERVAL_SECONDS"
DEFAULT_INTERVAL_SECONDS = 900.0
MIN_INTERVAL_SECONDS = 300.0
FIRST_DELAY_SECONDS = 20.0
CALL_TIMEOUT_SECONDS = 5.0

# R-MON1-18: one INFO line per process per (provider, exception class) of an
# inconclusive probe failure.
_INCONCLUSIVE_LOGGED: set = set()


def probe_enabled() -> bool:
    return os.getenv(FLAG, "false").strip().lower() in ("true", "1", "yes", "on")


def probe_interval() -> float:
    """Unset, unparsable, inf, nan or <= 0 -> the default; below the floor -> the
    floor."""
    raw = os.getenv(INTERVAL_ENV)
    try:
        value = float(raw.strip()) if raw is not None else DEFAULT_INTERVAL_SECONDS
    except (TypeError, ValueError):
        return DEFAULT_INTERVAL_SECONDS
    if not math.isfinite(value) or value <= 0:
        return DEFAULT_INTERVAL_SECONDS
    return max(value, MIN_INTERVAL_SECONDS)


def _metadata_call(provider: str):
    """The awaitable of one metadata call, or None when the provider has no
    credential to probe. Raises when the client cannot be built.

    S81-12d (GATE GC-5, H5): while ENABLE_OPENAI_EGRESS_STOP is ON the openai
    branch raises OpenAIEgressStoppedError before any client is built, so nothing
    reaching this function can call OpenAI (the in-use rule already keeps the
    probe pass away from it). No log line of its own."""
    from app.services import api_budget_service as _abs
    from app.services import model_config

    if provider == "openai":
        if _abs.openai_egress_stop_enabled():
            raise _abs.OpenAIEgressStoppedError(_abs.OPENAI_EGRESS_STOP_MESSAGE)
        from app.services import openai_service

        client = openai_service.get_client().with_options(
            max_retries=0, timeout=CALL_TIMEOUT_SECONDS
        )
        return client.models.retrieve(model_config.standard_model())
    if provider == "anthropic":
        from app.services import llm_router

        material = llm_router._anthropic_api_key()
        if material is None:
            return None
        client = llm_router._client_for(material).with_options(
            max_retries=0, timeout=CALL_TIMEOUT_SECONDS
        )
        return client.models.retrieve(model_config.anthropic_model("text"))
    return None


def _log_inconclusive_once(provider: str, cls_name: str) -> None:
    marker = (provider, cls_name)
    if marker in _INCONCLUSIVE_LOGGED:
        return
    _INCONCLUSIVE_LOGGED.add(marker)
    logger.info(
        "[LLM_PROBE] inconclusive failure provider=%s class=%s (first in this process)",
        provider,
        cls_name,
    )


async def _probe_provider(provider: str) -> str:
    t0 = time.monotonic()
    cls_name = "none"
    outcome = "unavailable"
    call = None
    try:
        call = _metadata_call(provider)
    except Exception as exc:  # noqa: BLE001 -- no client: nothing to probe
        cls_name = type(exc).__name__
    if call is not None:
        try:
            await asyncio.wait_for(call, CALL_TIMEOUT_SECONDS)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 -- classified by class, never message
            cls_name = type(exc).__name__
            verdict = _cred_health.classify(provider, exc, "probe")
            if verdict is None:
                outcome = "inconclusive"
                _log_inconclusive_once(provider, cls_name)
            else:
                outcome = verdict[0]
                _cred_health.note_failure(provider, exc, "probe")
        else:
            outcome = "ok"
            _cred_health.note_success(provider, "probe")
    logger.info(
        "[LLM_PROBE] provider=%s outcome=%s class=%s ms=%d",
        provider,
        outcome,
        cls_name,
        int((time.monotonic() - t0) * 1000),
    )
    return outcome


async def probe_once() -> dict:
    """One metadata call per in-use provider; {provider: outcome}."""
    out = {}
    for provider in _cred_health.providers_in_use():
        out[provider] = await _probe_provider(provider)
    return out


async def tick() -> dict:
    """One probe tick. The flag read is the FIRST statement (R-MON1-19): OFF builds
    no client and awaits nothing."""
    if not probe_enabled():
        return {}
    return await probe_once()


async def run_forever() -> None:
    """The lifespan task (app.main): first tick after FIRST_DELAY_SECONDS, then one
    per probe_interval(). CancelledError always propagates."""
    await asyncio.sleep(FIRST_DELAY_SECONDS)
    while True:
        try:
            await tick()
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 -- the task survives a bad tick
            logger.warning("[LLM_PROBE] tick failed class=%s", type(exc).__name__)
        await asyncio.sleep(probe_interval())
