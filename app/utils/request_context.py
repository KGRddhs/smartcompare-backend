"""S81-05 REQUEST-CONTEXT: three request headers into ContextVars (stdlib leaf).

Stdlib only, no app imports: this is a LEAF, imported by the pure-ASGI
middleware ``app/middleware/request_context.py`` (which binds the values once
per HTTP request) and by ``app/api/auth_routes.py`` (which re-imports the one
compiled fingerprint pattern). Nothing else reads these accessors yet: the
consumers (S81-06 consent routing, S81-09 device quota, S81-22 compare runs)
come in later units.

Flag: ``ENABLE_REQUEST_CONTEXT_HEADERS`` (default OFF), read per call by
``request_context_headers_enabled`` with the house idiom. With the flag OFF the
middleware binds nothing and every accessor reads ``None`` (every state
"absent").

The three headers (lower-case ASGI names, the FIRST occurrence decides, later
duplicates are ignored, values decoded latin-1):

* ``x-ai-consent-version`` -> ``consent_version()``: a decimal int 0..999 written
  with 1-3 ASCII digits (no sign, no space; leading zeros allowed).
* ``x-device-fingerprint`` -> ``device_fingerprint()``: the existing
  ``^[a-f0-9]{64}$`` shape, matched in full (``DEVICE_FINGERPRINT_RE`` is the
  one compiled object; ``auth_routes`` re-imports it under its old name).
* ``x-compare-request-id`` -> ``compare_request_id()``: a canonical uuid4
  (RFC variant); upper or mixed case is accepted and normalised to the
  canonical lower-case form.

The None rule: a missing, empty, malformed or non-ASCII first occurrence reads
``None``. It is never a 400, never logged, never a changed response byte.
``header_state(name)`` reports the constant ``"absent"`` (not sent), the
constant ``"malformed"`` (sent, but empty or invalid) or the constant ``"ok"``
per header, never a value; it accepts the bytes constants below or the header
name as a str, case-insensitively. The values and the states are bound in ONE
atomic step: every header is parsed into locals first and the ContextVars are
set only after every parse finished; if anything raises, every value is None and
every state "malformed".

Device key: ``device_key(fp)`` = HMAC-SHA256(``DEVICE_KEY_PEPPER``, fp) as 64
lower-case hex, the pepper read per call (stripped). Fail closed: an invalid
fingerprint returns None without reading the pepper; an unset or blank pepper
returns None and logs ONE constant WARNING per process. Never a fallback key,
never the fingerprint itself. The server stores the client's fingerprint value
verbatim today (``auth_routes`` register / social sign-in); this unit changes
no stored value.

ContextVar rule for consumers: read the accessors on the request path BEFORE any
offload. ``asyncio.to_thread``, Starlette's threadpool and a task created
inside the request see the values (a task keeps the snapshot taken at its
creation); ``loop.run_in_executor`` with the installed default executor does
NOT copy the context and reads None.

Never logged anywhere: a header value, the pepper (set or not), a device key, a
parse failure reason, the request id.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import re
import threading
import uuid
from contextvars import ContextVar
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

FLAG_ENV = "ENABLE_REQUEST_CONTEXT_HEADERS"
PEPPER_ENV = "DEVICE_KEY_PEPPER"

HEADER_CONSENT_VERSION = b"x-ai-consent-version"
HEADER_DEVICE_FINGERPRINT = b"x-device-fingerprint"
HEADER_COMPARE_REQUEST_ID = b"x-compare-request-id"
_HEADERS = (
    HEADER_CONSENT_VERSION,
    HEADER_DEVICE_FINGERPRINT,
    HEADER_COMPARE_REQUEST_ID,
)

STATE_ABSENT = "absent"
STATE_MALFORMED = "malformed"
STATE_OK = "ok"
_ABSENT_STATES = (STATE_ABSENT, STATE_ABSENT, STATE_ABSENT)
_MALFORMED_STATES = (STATE_MALFORMED, STATE_MALFORMED, STATE_MALFORMED)

# The canonical compiled fingerprint pattern (migration 021 shape); the
# register / social sign-in reader in auth_routes re-imports this object.
DEVICE_FINGERPRINT_RE = re.compile(r"^[a-f0-9]{64}$")
# ASCII digits only: str.isdigit() and int() accept Arabic-Indic and fullwidth
# digits, which must read None.
_CONSENT_RE = re.compile(r"[0-9]{1,3}")

_CONSENT_VERSION: ContextVar[Optional[int]] = ContextVar(
    "s81_consent_version", default=None
)
_DEVICE_FINGERPRINT: ContextVar[Optional[str]] = ContextVar(
    "s81_device_fingerprint", default=None
)
_COMPARE_REQUEST_ID: ContextVar[Optional[str]] = ContextVar(
    "s81_compare_request_id", default=None
)
_HEADER_STATES: ContextVar[Optional[Tuple[str, str, str]]] = ContextVar(
    "s81_header_states", default=None
)

_PEPPER_WARNED = False
_PEPPER_LOCK = threading.Lock()


def request_context_headers_enabled() -> bool:
    """The flag, read per call (the house idiom; default OFF)."""
    return os.getenv(FLAG_ENV, "false").strip().lower() in (
        "true",
        "1",
        "yes",
        "on",
    )


def parse_consent_version(raw: object) -> Optional[int]:
    """1-3 ASCII digits -> int 0..999; anything else -> None. Never raises."""
    if not isinstance(raw, str) or _CONSENT_RE.fullmatch(raw) is None:
        return None
    return int(raw)


def parse_device_fingerprint(raw: object) -> Optional[str]:
    """Exactly 64 lower-case hex characters -> the value; else None."""
    if not isinstance(raw, str) or DEVICE_FINGERPRINT_RE.fullmatch(raw) is None:
        return None
    return raw


def parse_compare_request_id(raw: object) -> Optional[str]:
    """A canonical uuid4 in any letter case -> its lower-case form; else None.

    ``uuid.UUID(s, version=4)`` forces the version and variant bits, so the
    round trip equals the input only for a canonical hyphenated v4 string with
    the RFC variant (no braces, no ``urn:uuid:``, no 32-hex form, no padding).
    The length check is a work bound before the parse of a long header.
    """
    if not isinstance(raw, str) or len(raw) != 36:
        return None
    low = raw.lower()
    try:
        canonical = str(uuid.UUID(low, version=4))
    except (ValueError, TypeError, AttributeError):
        return None
    if canonical != low:
        return None
    return canonical


def consent_version() -> Optional[int]:
    """The bound consent version of this request, or None."""
    return _CONSENT_VERSION.get()


def device_fingerprint() -> Optional[str]:
    """The bound device fingerprint of this request, or None."""
    return _DEVICE_FINGERPRINT.get()


def compare_request_id() -> Optional[str]:
    """The bound compare request id of this request, or None."""
    return _COMPARE_REQUEST_ID.get()


def _header_index(name: object) -> Optional[int]:
    if isinstance(name, str):
        try:
            key = name.lower().encode("latin-1")
        except UnicodeEncodeError:
            return None
    elif isinstance(name, (bytes, bytearray)):
        key = bytes(name).lower()
    else:
        return None
    try:
        return _HEADERS.index(key)
    except ValueError:
        return None


def header_state(name: object) -> str:
    """Return "absent" | "malformed" | "ok" for one header (never a value).

    ``name`` is one of the HEADER_* bytes constants or the header name as a
    str, case-insensitively; an unknown name, and every name outside a bound
    request, reads "absent". Never raises.
    """
    try:
        states = _HEADER_STATES.get()
        if states is None:
            return STATE_ABSENT
        idx = _header_index(name)
        if idx is None:
            return STATE_ABSENT
        state = states[idx]
    except Exception:  # noqa: BLE001 - a state read is total
        return STATE_ABSENT
    if state in (STATE_ABSENT, STATE_MALFORMED, STATE_OK):
        return state
    return STATE_ABSENT


def _parse_one(raw_values: dict, name: bytes, parser) -> Tuple[object, str]:
    if name not in raw_values:
        return None, STATE_ABSENT
    value = parser(raw_values[name].decode("latin-1"))
    return value, (STATE_MALFORMED if value is None else STATE_OK)


def bind_from_headers(headers: object) -> tuple:
    """Bind the three values and states for one request; return the tokens.

    TOTAL and ATOMIC: ``headers`` (the ASGI ``scope["headers"]`` list of
    ``(bytes, bytes)`` pairs) is read once, the first occurrence of each name
    is kept, every header is parsed into locals, and the ContextVars are set
    only after every parse finished. Any exception while reading or parsing
    binds every value to None and every state to "malformed". Never raises,
    never logs. Pass the returned tokens to ``reset_request_context``.
    """
    try:
        raw_values = {}
        for item in headers:
            name, value = item
            if name in _HEADERS and name not in raw_values:
                raw_values[name] = value
        consent, consent_state = _parse_one(
            raw_values, HEADER_CONSENT_VERSION, parse_consent_version
        )
        fingerprint, fingerprint_state = _parse_one(
            raw_values, HEADER_DEVICE_FINGERPRINT, parse_device_fingerprint
        )
        request_id, request_id_state = _parse_one(
            raw_values, HEADER_COMPARE_REQUEST_ID, parse_compare_request_id
        )
        states = (consent_state, fingerprint_state, request_id_state)
    except Exception:  # noqa: BLE001 - the bind is total
        consent = fingerprint = request_id = None
        states = _MALFORMED_STATES
    return (
        _CONSENT_VERSION.set(consent),
        _DEVICE_FINGERPRINT.set(fingerprint),
        _COMPARE_REQUEST_ID.set(request_id),
        _HEADER_STATES.set(states),
    )


def reset_request_context(tokens: tuple) -> None:
    """Reset the tokens of ``bind_from_headers`` in reverse order. Total: a
    failing reset never replaces the exception of the request it ends."""
    try:
        pairs = list(
            zip(
                (
                    _CONSENT_VERSION,
                    _DEVICE_FINGERPRINT,
                    _COMPARE_REQUEST_ID,
                    _HEADER_STATES,
                ),
                tokens,
            )
        )
    except Exception:  # noqa: BLE001 - the reset is total
        return
    for var, token in reversed(pairs):
        try:
            var.reset(token)
        except Exception:  # noqa: BLE001 - the reset is total
            pass


def _warn_pepper_once() -> None:
    global _PEPPER_WARNED
    with _PEPPER_LOCK:
        if _PEPPER_WARNED:
            return
        _PEPPER_WARNED = True
    logger.warning(
        "[REQUEST-CONTEXT] DEVICE_KEY_PEPPER unset or blank; "
        "device keys disabled (fail closed)"
    )


def _reset_pepper_warning() -> None:
    """Test seam: clear the once-per-process WARNING latch."""
    global _PEPPER_WARNED
    with _PEPPER_LOCK:
        _PEPPER_WARNED = False


def device_key(fp: object) -> Optional[str]:
    """HMAC-SHA256(pepper, fp) as 64 lower-case hex, or None (fail closed)."""
    parsed = parse_device_fingerprint(fp)
    if parsed is None:
        return None
    pepper = os.getenv(PEPPER_ENV)
    if pepper is None or not pepper.strip():
        _warn_pepper_once()
        return None
    return hmac.new(
        pepper.strip().encode("utf-8"), parsed.encode("ascii"), hashlib.sha256
    ).hexdigest()
