"""S77 POSTHOG part B -- server-side product analytics (PostHog EU Cloud).

Two choke points send events, both already off the response path inside
`fire_and_forget`:

- `feedback_service.track_after_persist` -> `server_compare_completed` (a
  delivered comparison, saved or not, `success is True` only, ruling PR3);
- `database_service.log_search` failure rows -> `server_compare_failed`
  (`success=False` with a user id; success rows send nothing).

Flags, every one read PER CALL (the `search_log_truth_enabled` idiom):

- `ENABLE_POSTHOG_SERVER_CAPTURE` (default OFF) AND a non-blank
  `POSTHOG_PROJECT_API_KEY`. OFF: no import of `posthog`, no client, no
  `users` read, no new call at either choke point.
- `ENABLE_POSTHOG_PERSON_DELETE` (default OFF) AND non-blank
  `POSTHOG_PERSONAL_API_KEY` + `POSTHOG_PROJECT_ID` (B2): the account-deletion
  route marks the user deleted in this process BEFORE the erase, then asks
  PostHog to delete the person and their events (ruling PR2).

The client is built lazily, once, inside `asyncio.to_thread` (the first
`import posthog` included, ruling PR13), with GeoIP off, exception
autocapture off, `sync_mode=False` (consumer threads send; the queue put
never blocks) and a `before_send` that drops `$ip` (ruling PH8). The capture
call itself also runs in `asyncio.to_thread` (spec 4.3 fallback, measured on
7.60.1: `capture()` builds `posthog.utils.system_context()` on the caller's
thread every time -- a WMI query of about 30 ms per call on Windows, and on
Linux a `distro` read whose first call may start a subprocess). The
construction knobs (`POSTHOG_PROJECT_API_KEY`, `POSTHOG_HOST`) apply at the
first construction: a key change needs a restart (ruling PR19).

Privacy (PH8-PH10): `distinct_id` is the user id string; no email, name,
display name, token, verdict prose, pros/cons, preferences or demographics is
ever a property; the query is cut to 200 characters and every link in it is
reduced to scheme + host + path; product and winner names are cut to 120
characters; anonymous callers send nothing; a user whose analytics preference
(`users.preferences.analytics_enabled`) is False sends nothing, and a failed
or missing preference read sends nothing either (ruling PG4). The failure
event carries a coarse `error_class`, never the message.

Every failure is swallowed and logged at WARNING with the exception TYPE only.
"""
import asyncio
import logging
import os
import threading
import time
from collections import OrderedDict
from typing import Any, Dict, Optional

import httpx

from app.services.log_scrub import _SAFE_EXC_URL_RE, _safe_exc_url

logger = logging.getLogger(__name__)

_TRUTHY = ("true", "1", "yes", "on")

# PH1: EU Cloud. Ingestion host for capture; private API host for B2.
DEFAULT_POSTHOG_HOST = "https://eu.i.posthog.com"
DEFAULT_POSTHOG_API_HOST = "https://eu.posthog.com"

# Spec 2.6 / PR5: the per-process analytics-preference cache. Module globals
# read at CALL time, so ops (and tests) can change them without a re-import.
ANALYTICS_PREF_CACHE_TTL_SECONDS = 300
ANALYTICS_PREF_CACHE_MAX_ENTRIES = 2048

# PR2: B2 drains this process's queue before asking PostHog to delete.
PERSON_DELETE_FLUSH_TIMEOUT_SECONDS = 2
PERSON_DELETE_HTTP_TIMEOUT_SECONDS = 5.0

_QUERY_MAX_CHARS = 200   # PH9
_NAME_MAX_CHARS = 120    # PH9

COMPLETED_EVENT = "server_compare_completed"
FAILED_EVENT = "server_compare_failed"

_client = None
_client_lock = threading.Lock()
# user id -> (monotonic time of the read, analytics allowed). Touched only on
# the event-loop thread; the read itself runs in asyncio.to_thread.
_pref_cache: "OrderedDict[str, tuple]" = OrderedDict()
# PR2: user ids whose account deletion was requested in this process.
_deleted_users: set = set()


def _truthy(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in _TRUTHY


def _present(name: str) -> bool:
    return bool(os.getenv(name, "").strip())


def posthog_server_capture_enabled() -> bool:
    """`ENABLE_POSTHOG_SERVER_CAPTURE` truthy AND `POSTHOG_PROJECT_API_KEY`
    non-blank, read per call."""
    return _truthy("ENABLE_POSTHOG_SERVER_CAPTURE") and _present("POSTHOG_PROJECT_API_KEY")


def posthog_person_delete_enabled() -> bool:
    """B2: `ENABLE_POSTHOG_PERSON_DELETE` truthy AND both
    `POSTHOG_PERSONAL_API_KEY` and `POSTHOG_PROJECT_ID` non-blank, read per call."""
    return (
        _truthy("ENABLE_POSTHOG_PERSON_DELETE")
        and _present("POSTHOG_PERSONAL_API_KEY")
        and _present("POSTHOG_PROJECT_ID")
    )


def _reset_state_for_tests() -> None:
    """Drop the client singleton, the preference cache and the deleted-user
    set. Test-only hook (precedent: database_service._reset_client_cache_for_tests);
    the dropped client is not shut down."""
    global _client
    with _client_lock:
        _client = None
    _pref_cache.clear()
    _deleted_users.clear()


def get_existing_client():
    """The client if one was built in this process, else None. Never builds one."""
    return _client


def mark_user_deleted(user_id) -> None:
    """PR2: no capture for this user id in this process from now on."""
    if user_id:
        _deleted_users.add(str(user_id))


def invalidate_analytics_preference(user_id) -> None:
    """PG6: drop this user's cached analytics preference (the toggles route)."""
    if user_id:
        _pref_cache.pop(str(user_id), None)


# ---------------------------------------------------------------------------
# The client
# ---------------------------------------------------------------------------


def _on_error(exc, batch=None) -> None:
    """PR14: the consumer's upload failure, by TYPE only (never the batch)."""
    logger.warning("[POSTHOG] send failed: %s", type(exc).__name__)


def _before_send(event):
    """PH8: drop any `$ip` property; never drop or raise."""
    try:
        properties = event.get("properties") if isinstance(event, dict) else None
        if isinstance(properties, dict):
            properties.pop("$ip", None)
    except Exception:  # noqa: BLE001 -- a filter must never lose the event
        pass
    return event


def _build_client():
    """Build the singleton once (double-checked under a threading lock). Runs
    in asyncio.to_thread: the first `import posthog` and the consumer-thread
    start stay off the event loop."""
    global _client
    with _client_lock:
        if _client is None:
            key = os.getenv("POSTHOG_PROJECT_API_KEY", "").strip()
            if not key:
                return None
            import posthog

            client = posthog.Posthog(
                key,
                host=os.getenv("POSTHOG_HOST", "").strip() or DEFAULT_POSTHOG_HOST,
                sync_mode=False,
                disable_geoip=True,
                enable_exception_autocapture=False,
                on_error=_on_error,
                before_send=_before_send,
                max_queue_size=1000,
                flush_at=50,
                flush_interval=5.0,
                timeout=5,
                max_retries=2,
            )
            # PR14, AFTER construction: measured on 7.60.1, the constructor sets
            # the "posthog" logger to WARNING itself, and the U8d logging
            # integration would turn the library's ERROR lines into Sentry events.
            logging.getLogger("posthog").setLevel(logging.CRITICAL)
            _client = client
        return _client


async def _get_client():
    client = _client
    if client is not None:
        return client
    return await asyncio.to_thread(_build_client)


# ---------------------------------------------------------------------------
# The analytics preference (spec 2.6 server half, PR5)
# ---------------------------------------------------------------------------


def _allowed_by(preferences) -> bool:
    """PH2: default ON; only an explicit False turns analytics off."""
    return not (isinstance(preferences, dict) and preferences.get("analytics_enabled") is False)


def _read_analytics_allowed(user_id: str) -> bool:
    """Blocking `users.preferences` read (runs in asyncio.to_thread, never
    run_db: run_db is inline while ENABLE_SYNC_DB_OFFLOAD is OFF). A missing
    row means analytics off."""
    from app.services import database_service

    client = database_service.get_admin_supabase_client()
    resp = client.table("users").select("preferences").eq("id", user_id).limit(1).execute()
    rows = resp.data or []
    if not rows or not isinstance(rows[0], dict):
        return False
    return _allowed_by(rows[0].get("preferences"))


async def _analytics_allowed(user_id: str, preferences) -> bool:
    if isinstance(preferences, dict):
        return _allowed_by(preferences)
    now = time.monotonic()
    cached = _pref_cache.get(user_id)
    if cached is not None and now - cached[0] < ANALYTICS_PREF_CACHE_TTL_SECONDS:
        _pref_cache.move_to_end(user_id)
        return cached[1]
    try:
        allowed = await asyncio.to_thread(_read_analytics_allowed, user_id)
    except Exception as exc:  # noqa: BLE001 -- PG4: a failed read fails closed
        logger.warning("[POSTHOG] analytics preference read failed: %s", type(exc).__name__)
        return False
    _pref_cache[user_id] = (time.monotonic(), allowed)
    _pref_cache.move_to_end(user_id)
    while len(_pref_cache) > ANALYTICS_PREF_CACHE_MAX_ENTRIES:
        _pref_cache.popitem(last=False)
    return allowed


# ---------------------------------------------------------------------------
# Properties (spec 4.3, PH9)
# ---------------------------------------------------------------------------


def _reduce_query(value) -> Optional[str]:
    """Every link reduced to scheme + host + path (the log_scrub URL scrub:
    userinfo, query and fragment dropped), then cut to 200 characters."""
    if not isinstance(value, str):
        return None
    return _SAFE_EXC_URL_RE.sub(_safe_exc_url, value)[:_QUERY_MAX_CHARS]


def _text(value, cap: Optional[int] = None) -> Optional[str]:
    if not isinstance(value, str):
        return None
    return value[:cap] if cap is not None else value


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value


def _product_name(product: Dict) -> Optional[str]:
    parts = [p.strip() for p in (product.get("brand"), product.get("name")) if isinstance(p, str) and p.strip()]
    return " ".join(parts)[:_NAME_MAX_CHARS] if parts else None


def _completed_properties(comparison_id, full_response: Dict, input_type) -> Dict[str, Any]:
    metadata = full_response.get("metadata")
    metadata = metadata if isinstance(metadata, dict) else {}
    overview = full_response.get("overview")
    overview = overview if isinstance(overview, dict) else {}
    winner = overview.get("winner")
    winner = winner if isinstance(winner, dict) else {}
    products = overview.get("products")
    products = products if isinstance(products, list) else []
    winner_index = winner.get("product_index")
    query = full_response.get("query")
    props: Dict[str, Any] = {
        "comparison_id": comparison_id or None,
        "saved": bool(comparison_id),
        "input_type": input_type or "text",
        "category": _text(full_response.get("category")),
        "winner_name": _text(winner.get("name"), _NAME_MAX_CHARS),
        "winner_index": winner_index if isinstance(winner_index, int) and not isinstance(winner_index, bool) else None,
        "partial": metadata.get("partial") is True,
        "partial_stage": _text(metadata.get("partial_stage")),
        "latency_ms": _number(metadata.get("elapsed_ms")),
        "cost_usd": _number(metadata.get("total_cost")),
        "cached": metadata.get("cached") if isinstance(metadata.get("cached"), bool) else None,
        "comparison_quality": _text(metadata.get("comparison_quality")),
        "cache_hit": metadata.get("cache_hit") if isinstance(metadata.get("cache_hit"), bool) else None,
        "query": _reduce_query(query if isinstance(query, str) else metadata.get("query")),
    }
    for index, suffix in ((0, "a"), (1, "b")):
        product = products[index] if len(products) > index and isinstance(products[index], dict) else {}
        price = product.get("price")
        price = price if isinstance(price, dict) else {}
        amount = _number(price.get("amount"))
        props["product_" + suffix] = _product_name(product)
        props["price_" + suffix] = amount
        props["currency_" + suffix] = _text(price.get("currency"))
        props["price_found_" + suffix] = amount is not None and price.get("unavailable") is not True
        source_method = price.get("source_method")
        if isinstance(source_method, str) and source_method:
            props["source_method_" + suffix] = source_method
    if metadata.get("model_downgraded") is True:
        props["model_downgraded"] = True
    return props


# PG10: keyed on the sentences and codes log_search actually receives
# (text_routes._failure_log_message passes the human sentence; image_routes and
# the stream fallbacks pass codes). Total: anything else is "other".
_ERROR_CLASSES = (
    ("timeout", ("still gathering prices", "timeout", "timed out")),
    ("content_unavailable", ("content_unavailable", "we don't compare")),
    ("insufficient_data", ("insufficient_data", "data was incomplete")),
)


def _error_class(message) -> str:
    if not isinstance(message, str):
        return "other"
    text = message.lower()
    for error_class, needles in _ERROR_CLASSES:
        if any(needle in text for needle in needles):
            return error_class
    return "other"


# ---------------------------------------------------------------------------
# Capture
# ---------------------------------------------------------------------------


async def _send(event: str, user_id, properties: Dict[str, Any]) -> None:
    client = await _get_client()
    if client is not None:
        # Off the loop (PG11 measurement, see the module docstring).
        await asyncio.to_thread(client.capture, event, distinct_id=str(user_id), properties=properties)


async def capture_compare_completed(
    *,
    user_id,
    comparison_id,
    full_response: Dict,
    input_type: Optional[str] = None,
    preferences: Optional[Dict] = None,
) -> None:
    """`server_compare_completed` for a delivered comparison (`success is
    True`, partials included). `preferences`, when given, is the raw
    `users.preferences` object; None means read it (cached). Never raises."""
    try:
        if not posthog_server_capture_enabled() or not user_id:
            return
        if not isinstance(full_response, dict) or full_response.get("success") is not True:
            return
        uid = str(user_id)
        if uid in _deleted_users or not await _analytics_allowed(uid, preferences):
            return
        await _send(COMPLETED_EVENT, uid, _completed_properties(comparison_id, full_response, input_type))
    except Exception as exc:  # noqa: BLE001 -- analytics never breaks a caller
        logger.warning("[POSTHOG] capture skipped: %s", type(exc).__name__)


async def capture_compare_failed(
    *,
    user_id,
    input_type,
    query,
    error_message,
    duration_ms,
    cost,
) -> None:
    """`server_compare_failed` for a log_search failure row. The message only
    picks the coarse `error_class`; it is never a property. Never raises."""
    try:
        if not posthog_server_capture_enabled() or not user_id:
            return
        uid = str(user_id)
        if uid in _deleted_users or not await _analytics_allowed(uid, None):
            return
        properties = {
            "input_type": _text(input_type),
            "latency_ms": _number(duration_ms),
            "cost_usd": _number(cost),
            "query": _reduce_query(query),
            "error_class": _error_class(error_message),
        }
        await _send(FAILED_EVENT, uid, properties)
    except Exception as exc:  # noqa: BLE001 -- analytics never breaks a caller
        logger.warning("[POSTHOG] capture skipped: %s", type(exc).__name__)


# ---------------------------------------------------------------------------
# B2: person deletion (PH4, PR2, spec 4.5)
# ---------------------------------------------------------------------------


async def request_person_deletion(user_id) -> None:
    """Fire-and-forget body of the account-deletion route (after the erase):
    flush this process's queue (an EXISTING client only, off the loop), then
    POST the documented bulk-delete endpoint
    (POST /api/projects/:project_id/persons/bulk_delete, posthog.com
    docs/privacy/data-storage) with the user id and delete_events. Failures are
    logged by type or status, the response by counts only. Never raises."""
    client = _client
    if client is not None:
        try:
            await asyncio.to_thread(client.flush, timeout_seconds=PERSON_DELETE_FLUSH_TIMEOUT_SECONDS)
        except Exception as exc:  # noqa: BLE001 -- the deletion request still goes out
            logger.warning("[POSTHOG] pre-delete flush failed: %s", type(exc).__name__)
    try:
        key = os.getenv("POSTHOG_PERSONAL_API_KEY", "").strip()
        project_id = os.getenv("POSTHOG_PROJECT_ID", "").strip()
        if not key or not project_id:
            return
        api_host = (os.getenv("POSTHOG_API_HOST", "").strip() or DEFAULT_POSTHOG_API_HOST).rstrip("/")
        async with httpx.AsyncClient(timeout=PERSON_DELETE_HTTP_TIMEOUT_SECONDS) as http:
            resp = await http.post(
                f"{api_host}/api/projects/{project_id}/persons/bulk_delete",
                json={"distinct_ids": [str(user_id)], "delete_events": True},
                headers={"Authorization": "Bearer " + key},
            )
        if resp.status_code >= 400:
            logger.warning("[POSTHOG] person delete failed: HTTP %s", resp.status_code)
            return
        body = resp.json() if resp.content else {}
        body = body if isinstance(body, dict) else {}
        queued = body.get("events_queued_for_deletion")
        errors = body.get("deletion_errors")
        logger.info(
            "[POSTHOG] person delete requested: HTTP %s events_queued_for_deletion=%s deletion_errors=%d",
            resp.status_code,
            queued if isinstance(queued, (bool, int)) else None,
            len(errors) if isinstance(errors, list) else 0,
        )
    except Exception as exc:  # noqa: BLE001 -- never fails the (finished) deletion
        logger.warning("[POSTHOG] person delete failed: %s", type(exc).__name__)
