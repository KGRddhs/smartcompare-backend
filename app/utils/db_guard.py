"""INC-T1c REFUSAL-VISIBLE + INC-T1d GUARD-055-VISIBLE: the users guard refusals, made visible.

Migration 054 refuses a change to the eleven users entitlement columns, and migration
055 (INC-SEC-1) a change to the six users profile columns, that does not come from the
server role: both with SQLSTATE 42501, each with its own fixed message. The server
writes as the service role and should never be refused; when a missed path is, the
except arm of that writer calls ``note_if_guard_refusal(exc, "<site>")``: ONE fixed
ERROR line (no id, no row data, no exception text; ERROR lines become Sentry events),
``DB_GUARD_REFUSED site=<site>`` for a 054 refusal and
``DB_GUARD_REFUSED site=<site> guard=055`` for a 055 refusal, and one more on a
per-process counter that ``/health`` shows as ``db_guard_refusals`` (``count`` is the
total; ``count_055`` appears once a 055 refusal was recorded). Any other 42501 text
is not counted. The arm keeps its own behaviour.

A stdlib leaf: no app import, no third-party import, no I/O. The counters reset on
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
GUARD_MESSAGE_055 = "users profile columns are server-managed (INC-SEC-1)"
GUARD_MESSAGES = (GUARD_MESSAGE, GUARD_MESSAGE_055)
GUARD_055_TAIL = " guard=055"
LINE_PREFIX = "DB_GUARD_REFUSED site="

_SITE_RE = re.compile(r"[a-z][a-z0-9_.]{0,63}")
_lock = threading.Lock()
_count = 0
_count_055 = 0
_last_at: Optional[str] = None


def _guard_of(exc) -> Optional[str]:
    """"054" or "055" for an error whose ``code`` is 42501 and whose ``message`` carries
    that guard's fixed text (postgrest 2.31 APIError sets both from the PostgREST JSON),
    else None. Reads ``code`` and ``message`` only. Never raises."""
    try:
        code = getattr(exc, "code", None)
        message = getattr(exc, "message", None)
        if str(code) != GUARD_SQLSTATE or not isinstance(message, str):
            return None
        if GUARD_MESSAGE in message:
            return "054"
        if GUARD_MESSAGE_055 in message:
            return "055"
        return None
    except Exception:  # noqa: BLE001 -- a visibility probe must never break the arm
        return None


def is_guard_refusal(exc) -> bool:
    """True only for a 42501 whose ``message`` carries one of the two fixed texts
    (GUARD_MESSAGES). Never raises."""
    return _guard_of(exc) is not None


def note_refusal(site, guard="054") -> None:
    """Count one refusal and log the one fixed line. A site that is not a fixed
    lower-case name is logged as ``invalid`` so no value can reach the line; only
    ``guard == "055"`` adds the constant tail and counts a 055 refusal."""
    global _count, _count_055, _last_at
    name = site if isinstance(site, str) and _SITE_RE.fullmatch(site) else "invalid"
    with _lock:
        _count += 1
        if guard == "055":
            name += GUARD_055_TAIL
            _count_055 += 1
        _last_at = datetime.now(timezone.utc).isoformat()
    logger.error(LINE_PREFIX + name)


def note_if_guard_refusal(exc, site) -> bool:
    """The except-arm call: note the refusal when ``exc`` is one (054 or 055). Never raises."""
    try:
        guard = _guard_of(exc)
        if guard is None:
            return False
        note_refusal(site, guard)
        return True
    except Exception:  # noqa: BLE001
        return False


def refusal_count() -> int:
    return _count


def guard_snapshot() -> dict:
    """/health's ``db_guard_refusals`` key, the MON1 house shape (GC-1): {} until this
    process recorded a refusal, then {count, last_at}; count_055 joins only once a 055
    refusal was recorded (TD-2). A dict read under the lock, no I/O."""
    with _lock:
        if not _count:
            return {}
        inner = {"count": _count, "last_at": _last_at}
        if _count_055:
            inner["count_055"] = _count_055
        return {"db_guard_refusals": inner}


def _reset_guard_state() -> None:
    """Test seam (GC-7): count 0, count_055 0 and last_at None, under the lock (the
    house name pattern of llm_credential_health._reset_credential_health_state)."""
    global _count, _count_055, _last_at
    with _lock:
        _count = 0
        _count_055 = 0
        _last_at = None
