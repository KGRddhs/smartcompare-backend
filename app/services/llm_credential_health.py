"""MON1 LLM-CREDENTIAL-HEALTH: the per-process credential state of the LLM providers.

The operator signal for root cause 2 of the 2026-11-11 incident ("no alarm"): the
OpenAI credential was rejected for days and nothing told anyone. This leaf records,
per provider (openai, anthropic), the credential state ok / rejected / quota from the
outcomes the dispatch chokepoints already see, and turns each state CHANGE into one
alert-grade Sentry event (sentry_service.capture_credential_alert), subject to a
cool-down per (provider, state).

Unflagged by ruling R-MON1-1 (a production bug fix whose OFF path is the defect). It
changes no gating and no response: the hooks call note_failure / note_success, which
never raise, never await and do no I/O beyond the alert send on a state change.

Rules (spec .qa-s80/MON1_UNIT_SPEC.md 2.2, amended by R-MON1-16..22):
- classification by exception CLASS, status_code and the SDK's structured `code` /
  `type` attributes, read through getattr, never from message text;
- a probe-sourced rejection needs the structured invalid-credential signal
  (R-MON1-18); a probe success never clears a quota state or a dispatch-sourced 403
  (R-MON1-17);
- a moderation success proves authentication only, like a probe success (fix
  round 1, F1-3): it never clears a quota state or a dispatch-sourced 403;
- every transition INTO rejected / quota and every recovery to ok emits one event,
  at most one per (kind, provider, state) per ALERT_COOLDOWN_SECONDS (R-MON1-21), a
  FIXED window from the last event emitted (F1-2);
- a transition whose event the cool-down suppressed is never lost (F1-1): it is
  marked pending, and the first outcome that confirms the held state after the
  cool-down emits it once; a transition out of that state clears the mark.

Stdlib only at module top (no `app.` import): the SDKs are reached through
importlib at call time, and the sender through sys.modules. Log lines carry
constants, closed-set names and ints only; never a credential, a header, a URL or
an exception text.
"""

import importlib
import logging
import os
import sys
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

PROVIDERS = ("openai", "anthropic")
STATES = ("ok", "rejected", "quota")
SOURCES = ("dispatch", "probe", "moderation")
ALERT_LLM = "llm_credential"
ALERT_SERPER = "serper_keys"

# R-MON1-21: the minimum interval between two alert events of one
# (kind, provider, state), on the monotonic clock `_monotonic`.
ALERT_COOLDOWN_SECONDS = 900.0
# R-MON1-22: with the probe ON, an in-use provider with no outcome after this many
# seconds of process uptime makes the monitor path answer LLM_CREDENTIAL_UNKNOWN.
UNKNOWN_GRACE_SECONDS = 120.0

_PROBE_FLAG = "ENABLE_LLM_CREDENTIAL_PROBE"

# R-MON1-16: the structured OpenAI out-of-credit / spend-limit codes of a 429.
_OPENAI_QUOTA_CODES = frozenset(
    {
        "credit_balance_exhausted",
        "insufficient_quota",
        "organization_spend_limit_exceeded",
        "project_spend_limit_exceeded",
        "organization_usage_limit_exceeded",
    }
)
_OPENAI_QUOTA_TYPE = "insufficient_quota"
_ANTHROPIC_QUOTA_TYPE = "billing_error"
# R-MON1-18: the structured invalid-credential signal a probe rejection needs.
_OPENAI_PROBE_REJECT_CODE = "invalid_api_key"
_ANTHROPIC_PROBE_REJECT_TYPE = "authentication_error"

_LOCK = threading.Lock()
_STATE: Dict[str, Dict[str, Any]] = {}
_LAST_ALERT: Dict[Tuple[str, str, str], float] = {}
# F1-1: (provider, state) -> the status of a transition whose event was suppressed.
_PENDING: Dict[Tuple[str, str], Optional[int]] = {}


def _monotonic() -> float:
    """The one clock of the cool-down and of the uptime mark (a test seam)."""
    return time.monotonic()


_STARTED_AT = _monotonic()


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sdk(provider: str) -> Any:
    try:
        return importlib.import_module(provider)
    except Exception:  # noqa: BLE001 -- a missing SDK classifies nothing
        return None


def _int_status(exc: BaseException) -> Optional[int]:
    status = getattr(exc, "status_code", None)
    if isinstance(status, int) and not isinstance(status, bool):
        return status
    return None


def classify(
    provider: str, exc: BaseException, source: str = "dispatch"
) -> Optional[Tuple[str, Optional[int]]]:
    """(state, status) for a credential answer, or None when the exception says
    nothing about the credential (a timeout, a connection error, a 5xx, a plain
    rate limit, a 400 / 404 / 409 / 422, a non-SDK exception). Never raises."""
    try:
        if provider not in PROVIDERS:
            return None
        sdk = _sdk(provider)
        status_error = getattr(sdk, "APIStatusError", None) if sdk else None
        if not (isinstance(status_error, type) and isinstance(exc, status_error)):
            return None
        status = _int_status(exc)
        if status is None:
            return None
        if provider == "openai":
            code = getattr(exc, "code", None)
            if status == 429:
                err_type = getattr(exc, "type", None)
                if (isinstance(code, str) and code in _OPENAI_QUOTA_CODES) or (
                    err_type == _OPENAI_QUOTA_TYPE
                ):
                    return ("quota", 429)
                return None
            if status in (401, 403):
                if source == "probe" and not (
                    status == 401 and code == _OPENAI_PROBE_REJECT_CODE
                ):
                    return None
                return ("rejected", status)
            return None
        err_type = getattr(exc, "type", None)
        if err_type == _ANTHROPIC_QUOTA_TYPE:
            return ("quota", status)
        if status in (401, 403):
            if source == "probe" and not (
                status == 401 and err_type == _ANTHROPIC_PROBE_REJECT_TYPE
            ):
                return None
            return ("rejected", status)
        return None
    except Exception:  # noqa: BLE001 -- an odd exception object is no verdict
        return None


def note_failure(provider: str, exc: BaseException, source: str) -> None:
    """Record a failed provider call. A no-op unless the exception is a credential
    answer (classify); never raises; the caller's exception is untouched."""
    try:
        if provider not in PROVIDERS or source not in SOURCES:
            return None
        verdict = classify(provider, exc, source)
        if verdict is None:
            return None
        state, status = verdict
        _transition(provider, state, status, source)
    except Exception:  # noqa: BLE001 -- an observer never breaks a dispatch
        pass
    return None


def note_success(provider: str, source: str) -> None:
    """Record a served provider call (the credential authenticated). Never raises."""
    try:
        if provider not in PROVIDERS or source not in SOURCES:
            return None
        _transition(provider, "ok", None, source)
    except Exception:  # noqa: BLE001 -- an observer never breaks a dispatch
        pass
    return None


def _probe_may_clear(prev: Dict[str, Any]) -> bool:
    """R-MON1-17: a probe success proves authentication only. It clears a
    `rejected` state that the probe itself raised or that carried a 401; never a
    quota state, never a dispatch / moderation 403."""
    if prev.get("state") == "quota":
        return False
    if prev.get("state") == "rejected":
        return prev.get("source") == "probe" or prev.get("last_status") == 401
    return True


def _moderation_may_clear(prev: Dict[str, Any]) -> bool:
    """F1-3: a moderation success proves authentication only. It clears a
    `rejected` state that carried a 401 or that moderation itself raised; never a
    quota state, never a dispatch / probe 403."""
    if prev.get("state") == "quota":
        return False
    if prev.get("state") == "rejected":
        return prev.get("source") == "moderation" or prev.get("last_status") == 401
    return True


def _cooled(key: Tuple[str, str, str], now: float) -> bool:
    """True when no event of `key` was emitted inside the cool-down (the caller
    holds _LOCK). The window is FIXED: only an emitted event stamps it (F1-2)."""
    last = _LAST_ALERT.get(key)
    return last is None or now - last >= ALERT_COOLDOWN_SECONDS


def _transition(provider: str, state: str, status: Optional[int], source: str) -> None:
    at = _utc_now()
    now = _monotonic()
    late = False
    with _LOCK:
        prev = _STATE.get(provider)
        if state == "ok" and prev is not None:
            if source == "probe" and not _probe_may_clear(prev):
                return
            if source == "moderation" and not _moderation_may_clear(prev):
                return
        prev_state = prev.get("state") if prev else None
        count = int(prev.get("count", 0)) + 1 if prev_state == state else 1
        _STATE[provider] = {
            "state": state,
            "last_status": status,
            "at": at,
            "source": source,
            "count": count,
        }
        if prev_state == state:
            key = (ALERT_LLM, provider, state)
            if (provider, state) in _PENDING and _cooled(key, now):
                # F1-1: a confirming outcome after the cool-down emits the held event.
                del _PENDING[(provider, state)]
                _LAST_ALERT[key] = now
                late = True
        else:
            # F1-1: a transition out of a state clears that state's pending mark.
            for held in STATES:
                _PENDING.pop((provider, held), None)
    if prev_state == state:
        if late:
            _send(ALERT_LLM, provider, state, status)
        return
    logger.warning(
        "[LLM_CREDENTIAL] provider=%s state=%s status=%s source=%s",
        provider,
        state,
        status if status is not None else "none",
        source,
    )
    if state in ("rejected", "quota") or prev_state in ("rejected", "quota"):
        if not emit_alert(ALERT_LLM, provider, state, status):
            with _LOCK:
                # F1-1: mark the suppressed transition pending while it is still held.
                held = _STATE.get(provider)
                if held is not None and held.get("state") == state:
                    _PENDING[(provider, state)] = status


def _send(kind: str, provider: str, state: str, status: Optional[int]) -> None:
    """Hand one event to sentry_service.capture_credential_alert, looked up through
    sys.modules at call time (no import); every exception is swallowed."""
    try:
        sender = getattr(
            sys.modules.get("app.services.sentry_service"),
            "capture_credential_alert",
            None,
        )
        if sender is not None:
            sender(kind, provider, state, status)
    except Exception:  # noqa: BLE001 -- an alert never breaks the caller
        pass


def emit_alert(kind: str, provider: str, state: str, status: Optional[int]) -> bool:
    """Send one alert event through sentry_service.capture_credential_alert, at most
    once per (kind, provider, state) per ALERT_COOLDOWN_SECONDS (a fixed window from
    the last event emitted). A suppressed send logs one WARNING and returns False;
    otherwise True. Every exception is swallowed."""
    try:
        key = (kind, provider, state)
        now = _monotonic()
        with _LOCK:
            last = _LAST_ALERT.get(key)
            if not _cooled(key, now):
                remaining = int(ALERT_COOLDOWN_SECONDS - (now - last))
                admitted = False
            else:
                _LAST_ALERT[key] = now
                admitted = True
        if not admitted:
            logger.warning(
                "[LLM_CREDENTIAL] alert suppressed provider=%s state=%s cooldown_s=%d",
                provider,
                state,
                remaining,
            )
            return False
        _send(kind, provider, state, status)
        return True
    except Exception:  # noqa: BLE001 -- an alert never breaks the caller
        return True


def health_snapshot() -> Dict[str, Any]:
    """The /health `llm_credential` entry: {} until this process recorded an
    outcome. A pure read (copies)."""
    with _LOCK:
        if not _STATE:
            return {}
        return {
            "llm_credential": {p: dict(_STATE[p]) for p in PROVIDERS if p in _STATE}
        }


def _present(raw: Optional[str]) -> bool:
    return raw is not None and bool(raw.strip())


def _anthropic_roles_on() -> bool:
    fn = getattr(sys.modules.get("app.services.llm_router"), "any_role_enabled", None)
    if fn is None:
        return False
    try:
        return bool(fn())
    except Exception:  # noqa: BLE001
        return False


def providers_in_use() -> Tuple[str, ...]:
    """openai when OPENAI_API_KEY is set (presence only: the value is never stored,
    compared or logged); anthropic when ANTHROPIC_API_KEY is set AND an
    ENABLE_ANTHROPIC_* role flag is ON (llm_router.any_role_enabled)."""
    out = []
    if _present(os.getenv("OPENAI_API_KEY")):
        out.append("openai")
    if _present(os.getenv("ANTHROPIC_API_KEY")) and _anthropic_roles_on():
        out.append("anthropic")
    return tuple(out)


def _probe_enabled() -> bool:
    return os.getenv(_PROBE_FLAG, "false").strip().lower() in (
        "true",
        "1",
        "yes",
        "on",
    )


def monitor_view() -> Tuple[int, Dict[str, Any]]:
    """GET /health/llm (R-MON1-8 / R-MON1-22): 503 LLM_CREDENTIAL_UNUSABLE while an
    in-use provider is rejected or quota; with the probe ON, 503
    LLM_CREDENTIAL_UNKNOWN while an in-use provider has no outcome after
    UNKNOWN_GRACE_SECONDS of uptime; else 200. Env reads and a dict read only."""
    in_use = providers_in_use()
    with _LOCK:
        states = {p: (_STATE[p]["state"] if p in _STATE else "unknown") for p in in_use}
    if any(s in ("rejected", "quota") for s in states.values()):
        return 503, {
            "status": "degraded",
            "code": "LLM_CREDENTIAL_UNUSABLE",
            "providers": states,
        }
    if (
        _probe_enabled()
        and any(s == "unknown" for s in states.values())
        and _monotonic() - _STARTED_AT > UNKNOWN_GRACE_SECONDS
    ):
        return 503, {
            "status": "degraded",
            "code": "LLM_CREDENTIAL_UNKNOWN",
            "providers": states,
        }
    return 200, {"status": "ok", "providers": states}


def _reset_credential_health_state() -> None:
    """Test seam (conftest calls it before every test)."""
    with _LOCK:
        _STATE.clear()
        _LAST_ALERT.clear()
        _PENDING.clear()
