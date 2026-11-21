"""INC-T1c REFUSAL-VISIBLE: the users entitlement guard refusal, made visible.

Migration 054 refuses a change to the eleven users entitlement columns that does not
come from the server role, with SQLSTATE 42501 and one fixed message. The server
writes as the service role and should never be refused; when a missed path is, the
except arm of that writer calls ``note_if_guard_refusal(exc, "<site>")``: ONE fixed
ERROR line ``DB_GUARD_REFUSED site=<site>`` (no id, no row data, no exception text;
ERROR lines become Sentry events) and one more on a per-process counter that
``/health`` shows as ``db_guard_refusals``. The arm keeps its own behaviour.

A stdlib leaf: no app import, no third-party import, no I/O. The counter resets on
each deploy; the log line and the Sentry event are the durable record.
"""
from __future__ import annotations

import logging
import re
import threading
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

GUARD_SQLSTATE = "42501"
GUARD_MESSAGE = "users entitlement columns are server-managed (INC-T1b)"
LINE_PREFIX = "DB_GUARD_REFUSED site="

_SITE_RE = re.compile(r"[a-z][a-z0-9_.]{0,63}")
_lock = threading.Lock()
_count = 0
_last_at: Optional[str] = None


def is_guard_refusal(exc) -> bool:
    """True only for an error whose ``code`` is 42501 and whose ``message`` carries the
    054 text (postgrest 2.31 APIError sets both from the PostgREST JSON). Never raises."""
    try:
        code = getattr(exc, "code", None)
        message = getattr(exc, "message", None)
        return str(code) == GUARD_SQLSTATE and isinstance(message, str) and GUARD_MESSAGE in message
    except Exception:  # noqa: BLE001 -- a visibility probe must never break the arm
        return False


def note_refusal(site) -> None:
    """Count one refusal and log the one fixed line. A site that is not a fixed
    lower-case name is logged as ``invalid`` so no value can reach the line."""
    global _count, _last_at
    name = site if isinstance(site, str) and _SITE_RE.fullmatch(site) else "invalid"
    with _lock:
        _count += 1
        _last_at = datetime.now(timezone.utc).isoformat()
    logger.error(LINE_PREFIX + name)


def note_if_guard_refusal(exc, site) -> bool:
    """The except-arm call: note the refusal when ``exc`` is one. Never raises."""
    try:
        if not is_guard_refusal(exc):
            return False
        note_refusal(site)
        return True
    except Exception:  # noqa: BLE001
        return False


def refusal_count() -> int:
    return _count


def guard_snapshot() -> dict:
    """/health's ``db_guard_refusals`` key, the MON1 house shape (GC-1): {} until this
    process recorded a refusal, then {count, last_at}. A dict read under the lock, no I/O."""
    with _lock:
        if not _count:
            return {}
        return {"db_guard_refusals": {"count": _count, "last_at": _last_at}}


def _reset_guard_state() -> None:
    """Test seam (GC-7): count 0 and last_at None, under the lock (the house name
    pattern of llm_credential_health._reset_credential_health_state)."""
    global _count, _last_at
    with _lock:
        _count = 0
        _last_at = None
