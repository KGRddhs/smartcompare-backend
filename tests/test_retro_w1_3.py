"""Retro-fix R-BREAKER (W1-3, PR #147) -- RED phase for W1-3a and W1-3b, plus pins.

Spec: the retroactive adversary report for "W1-3 OpenAI preflight breaker
ENABLE_LLM_PREFLIGHT_BREAKER", narrowed by the orchestrator's binding rulings:

  W1-3a (BLOCKING)  A bare ``asyncio.CancelledError`` inside
      ``api_budget_service.guarded_llm_create`` records NO breaker failure. A
      cancel from a sibling's wall, the hard cap, a client disconnect or a
      shutdown says nothing about OpenAI's health. Today every in-flight guarded
      dispatch that ONE outer wall cancels records its own failure, so a single
      compare that cancels three or more concurrent LLM calls trips the global
      breaker (``CB_FAILURE_THRESHOLD`` = 3) and the preflight then refuses
      every compare from every user for ``CB_RECOVERY_TIMEOUT`` (600 s), with
      OpenAI healthy the whole time.

  W1-3b  Every admitted half-open probe records a TOTAL outcome. A 4xx other
      than 429 (context-length / content-policy 400, 401, 403, 404, 409, 422)
      records success-for-health (the server answered) OR explicitly releases
      the probe slot; a non-SDK exception (and, by W1-3a, a cancellation)
      releases the probe slot. Today none of those record anything, the single
      probe INCR is spent, the blob stays ``half_open`` and every later
      dispatch is denied for up to the blob's 3600 s TTL while the read-only
      compare-entry preflight ADMITS every compare, so each one pays the whole
      Serper / Bright Data / Firecrawl fan-out and then fails at the LLM.

  Minor  Pin the flag-OFF compare-entry read (reviewer mutation M10): with the
      flag unset, neither compare entry reads ``circuit:openai``.

Everything stays inside ENABLE_LLM_PREFLIGHT_BREAKER (default OFF); flag OFF is
byte-identical and is pinned here (no Redis op, no record, the exception object
re-raised unchanged).

Which tests are RED today and why (each fails for the defect, not a name):
  * test_one_outer_wall_cancelling_three_guarded_dispatches_leaves_breaker_closed
  * test_external_task_cancel_is_reraised_and_records_nothing
  * test_one_compare_tier2_wall_does_not_open_the_breaker
  * test_cancelled_half_open_probe_releases_the_slot
  * test_failing_half_open_probe_never_wedges_deny_all_while_preflight_admits[*]
Everything else in this file is a PIN that passes today and must keep passing.

Deliberately NOT pinned (outside the rulings): reviewer W1-3c (cross-worker
streak decay) and the optional per-compare contextvar dedupe / stale-probe
window. An implementation may add them; nothing here forbids it.

Zero-network: an autouse guard blocks every non-loopback ``connect`` and
``getaddrinfo`` and fails the test on any attempt; the breaker Redis is a dict
stub and every OpenAI client is a mock.
"""
import asyncio
import socket as _socket_mod
import time

import httpx
import openai as openai_sdk
import pytest
from unittest.mock import MagicMock, patch

from app.services import api_budget_service as abs_mod
from app.services import openai_service as oai
from app.services import serper_service as ss
from app.services import structured_comparison_service as scs
from tests.test_openai_breaker import (
    _FanOutCounters,
    _all,
    _arm_prod_search_config,
    _breaker_blob,
    _dict_breaker_redis,
    _mock_openai_client,
    _open_breaker_seed,
    _patch_breaker_redis,
    _probe_key_for,
    _rate_limit_error,
    _reset_breaker_memo,
    _run_compare,
    _run_stream,
)

FLAG = "ENABLE_LLM_PREFLIGHT_BREAKER"
TTL_ENV = "LLM_BREAKER_CACHE_TTL"
PROVIDER = "openai"
_URL = "https://api.openai.com/v1/chat/completions"


# ---------------------------------------------------------------------------
# Autouse fixtures: zero network + clean breaker state
# ---------------------------------------------------------------------------
_LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost", "0.0.0.0"}


def _is_loopback(host) -> bool:
    if host is None:
        return True
    h = host.decode() if isinstance(host, (bytes, bytearray)) else str(host)
    return h in _LOOPBACK_HOSTS or h.startswith("127.")


@pytest.fixture(autouse=True)
def _zero_network(monkeypatch):
    """Block every non-loopback connect / getaddrinfo and FAIL the test on any
    attempt, even one the code under test swallows (the attempt is recorded
    before the OSError is raised, and asserted empty at teardown)."""
    attempts = []
    real_connect = _socket_mod.socket.connect
    real_connect_ex = _socket_mod.socket.connect_ex
    real_getaddrinfo = _socket_mod.getaddrinfo
    af_unix = getattr(_socket_mod, "AF_UNIX", None)

    def _host_of(address):
        if isinstance(address, tuple) and address:
            return address[0]
        return address

    def _local(sock, address):
        return (af_unix is not None and sock.family == af_unix) or _is_loopback(
            _host_of(address)
        )

    def _connect(self, address):
        if _local(self, address):
            return real_connect(self, address)
        attempts.append(("connect", repr(address)))
        raise OSError(f"zero-network guard: blocked connect to {address!r}")

    def _connect_ex(self, address):
        if _local(self, address):
            return real_connect_ex(self, address)
        attempts.append(("connect_ex", repr(address)))
        raise OSError(f"zero-network guard: blocked connect_ex to {address!r}")

    def _getaddrinfo(host, *args, **kwargs):
        if _is_loopback(host):
            return real_getaddrinfo(host, *args, **kwargs)
        attempts.append(("getaddrinfo", repr(host)))
        raise _socket_mod.gaierror(f"zero-network guard: blocked getaddrinfo({host!r})")

    monkeypatch.setattr(_socket_mod.socket, "connect", _connect)
    monkeypatch.setattr(_socket_mod.socket, "connect_ex", _connect_ex)
    monkeypatch.setattr(_socket_mod, "getaddrinfo", _getaddrinfo)
    yield attempts
    assert not attempts, f"zero-network guard: the test attempted network access: {attempts}"


@pytest.fixture(autouse=True)
def _clean_breaker_state(monkeypatch):
    """Also pins serper_service's module-level SERPER_API_KEY to None (the
    single-key fallback reads the MODULE attr, not the env) and drops its 60 s
    memoised spend-gate decision. In the comm-gate set run an EARLIER test file
    left a key on the module attr, so the compare harness -- whose
    `_arm_prod_search_config` only clears the ENV var -- attempted real Serper
    POSTs (12 blocked getaddrinfo attempts on google.serper.dev in the flag-OFF
    compare-entry pin; the same file passes alone with zero attempts)."""
    monkeypatch.delenv(FLAG, raising=False)
    monkeypatch.delenv(TTL_ENV, raising=False)
    monkeypatch.setattr(ss, "SERPER_API_KEY", None)
    _reset_breaker_memo()
    ss.reset_serper_budget_cache()
    yield
    _reset_breaker_memo()
    ss.reset_serper_budget_cache()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _status_error(cls, status):
    request = httpx.Request("POST", _URL)
    return cls(
        f"synthetic {status}", response=httpx.Response(status, request=request), body=None
    )


def _non_transient_4xx():
    """Every 4xx other than 429 the ruling names (400 covers context-length and
    content-policy rejections, which the SDK raises as BadRequestError)."""
    return [
        ("400-context-length", _status_error(openai_sdk.BadRequestError, 400)),
        ("401-auth", _status_error(openai_sdk.AuthenticationError, 401)),
        ("403-permission", _status_error(openai_sdk.PermissionDeniedError, 403)),
        ("404-model", _status_error(openai_sdk.NotFoundError, 404)),
        ("409-conflict", _status_error(openai_sdk.ConflictError, 409)),
        ("422-unprocessable", _status_error(openai_sdk.UnprocessableEntityError, 422)),
    ]


def _transient_shapes():
    request = httpx.Request("POST", _URL)
    return [
        ("429-rate-limit", _rate_limit_error()),
        ("connection-error", openai_sdk.APIConnectionError(request=request)),
        ("sdk-request-timeout", openai_sdk.APITimeoutError(request=request)),
        ("500-internal", _status_error(openai_sdk.InternalServerError, 500)),
        ("503-status", _status_error(openai_sdk.APIStatusError, 503)),
        # A TimeoutError RAISED from inside the dispatch (the SDK's own
        # deadline, or a future in-guard asyncio.timeout) is a genuine OpenAI
        # stall and keeps recording. Only an outer CANCELLATION stops recording.
        ("in-call-timeout-error", asyncio.TimeoutError("in-call deadline")),
    ]


class _SlowClient:
    """An OpenAI stand-in whose create() never returns inside the test's walls;
    it counts how many dispatches actually started, so a wall-cancel test can
    prove the LLM was really in flight (never vacuous)."""

    def __init__(self, delay=30.0):
        self.delay = delay
        self.started = 0
        self.chat = MagicMock()
        self.chat.completions.create = self._create

    async def _create(self, **kwargs):
        self.started += 1
        await asyncio.sleep(self.delay)
        raise AssertionError("the wall should have cancelled this dispatch")


def _assert_no_failure_recorded(store, context):
    blob = _breaker_blob(store)
    if blob is None:
        return
    assert blob.get("state") == abs_mod.CB_CLOSED and int(blob.get("failure_count") or 0) == 0, (
        f"{context}: the breaker recorded a failure for a cancellation that says "
        f"nothing about OpenAI's health -> blob {blob}"
    )


async def _guarded(client):
    return await abs_mod.guarded_llm_create(client, model="gpt-4o-mini", messages=[])


# ===========================================================================
# W1-3a (BLOCKING) -- a cancellation is not an OpenAI health signal   [RED]
# ===========================================================================
@pytest.mark.asyncio
async def test_one_outer_wall_cancelling_three_guarded_dispatches_leaves_breaker_closed(monkeypatch):
    """THE ruling's pin. Three concurrent guarded dispatches, all in flight on a
    healthy-but-slow OpenAI, are cancelled by ONE outer wall (the Tier-2 4 s
    wall, the 25 s stream hard cap and the per-stage wait_fors all have this
    shape). The breaker must stay CLOSED and the preflight must keep admitting.

    RED today: each cancellation runs openai_record_failure(), so one wall
    event reaches CB_FAILURE_THRESHOLD and opens the global breaker for 600 s.
    """
    monkeypatch.setenv(FLAG, "true")
    store, ops, _get, _set, _incr, _expire = _dict_breaker_redis()
    slow = _SlowClient()

    with _all(*_patch_breaker_redis(_get, _set, _incr, _expire)):
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(
                asyncio.gather(_guarded(slow), _guarded(slow), _guarded(slow)),
                timeout=0.2,
            )
        assert slow.started == 3, f"harness: expected 3 dispatches in flight, saw {slow.started}"

        _assert_no_failure_recorded(store, "one outer wall cancelling 3 guarded dispatches")

        _reset_breaker_memo()
        assert scs._llm_preflight_short_circuits() is False, (
            "one compare's wall event made the preflight refuse EVERY compare "
            f"(blob={_breaker_blob(store)})"
        )
        healthy = _mock_openai_client()
        await _guarded(healthy)
        assert healthy.chat.completions.create.await_count == 1, (
            "a healthy OpenAI call was denied after a wall cancellation"
        )


@pytest.mark.asyncio
async def test_external_task_cancel_is_reraised_and_records_nothing(monkeypatch):
    """A bare task.cancel() (client disconnect / ENABLE_PREVERDICT_DISCONNECT_ABORT
    / shutdown) must propagate the CancelledError untouched AND record nothing.

    RED today on the second half: failure_count 1 is written. (The re-raise half
    passes today and must keep passing -- the guard never swallows a cancel.)"""
    monkeypatch.setenv(FLAG, "true")
    store, ops, _get, _set, _incr, _expire = _dict_breaker_redis()
    slow = _SlowClient()

    with _all(*_patch_breaker_redis(_get, _set, _incr, _expire)):
        task = asyncio.ensure_future(_guarded(slow))
        for _ in range(50):
            if slow.started:
                break
            await asyncio.sleep(0.005)
        assert slow.started == 1, "harness: the dispatch never started"
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    _assert_no_failure_recorded(store, "an external task.cancel()")


@pytest.mark.asyncio
async def test_one_compare_tier2_wall_does_not_open_the_breaker(monkeypatch):
    """The reviewer's P1 through the REAL compare-path caller:
    structured_comparison_service.tier2_fill_non_negotiables fans out one search
    + one guarded extract per missing smartphone non-negotiable (battery,
    processor, ram, rear_camera = 4) and cancels them all at its wall.

    RED today: re-reproduced on the pinned venv -> blob
    {'state': 'open', 'failure_count': 4} after ONE compare, and the preflight
    then short-circuits every compare."""
    monkeypatch.setenv(FLAG, "true")
    monkeypatch.setattr(scs, "_TIER2_WALL_SECONDS", 0.3)
    store, ops, _get, _set, _incr, _expire = _dict_breaker_redis()
    slow = _SlowClient(delay=5.0)

    async def _search(query, num_results=3):
        return {"organic": [{"snippet": f"{query} snippet"}]}

    monkeypatch.setattr(ss, "search_web", _search)
    monkeypatch.setattr(oai, "get_client", lambda: slow)

    with _all(*_patch_breaker_redis(_get, _set, _incr, _expire)):
        out = await scs.tier2_fill_non_negotiables(
            brand="Acme", name="Phone", variant=None, category="smartphone", specs_so_far={}
        )
        assert out == {}
        assert slow.started >= abs_mod.CB_FAILURE_THRESHOLD, (
            f"harness: only {slow.started} guarded dispatches were in flight at the wall"
        )
        _assert_no_failure_recorded(store, "one compare's Tier-2 wall")
        _reset_breaker_memo()
        assert scs._llm_preflight_short_circuits() is False


@pytest.mark.asyncio
async def test_cancelled_half_open_probe_releases_the_slot(monkeypatch):
    """W1-3a x W1-3b interplay: once a cancellation records nothing, a CANCELLED
    half-open probe must still release its slot, or the W1-3a fix would itself
    wedge the breaker (probe INCR spent, nothing recorded). The next healthy
    dispatch must be admitted, reach OpenAI and close the breaker, and the
    preflight must never admit a compare whose dispatch is then denied.

    RED today: the cancelled probe is recorded as a failure, which re-OPENs the
    breaker for a fresh 600 s window -> 0 healthy dispatches reach OpenAI."""
    monkeypatch.setenv(FLAG, "true")
    store, ops, _get, _set, _incr, _expire = _dict_breaker_redis(
        _open_breaker_seed(tripped_ago=abs_mod.CB_RECOVERY_TIMEOUT + 5)
    )
    slow = _SlowClient()
    healthy = _mock_openai_client()

    with _all(*_patch_breaker_redis(_get, _set, _incr, _expire)):
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(_guarded(slow), timeout=0.1)
        assert slow.started == 1, "harness: the half-open probe never dispatched"

        inconsistent = []
        for _ in range(5):
            _reset_breaker_memo()
            preflight_admits = abs_mod.openai_preflight_allows_compare()
            try:
                await _guarded(healthy)
                admitted = True
            except abs_mod.LLMUnavailableError:
                admitted = False
            if preflight_admits and not admitted:
                inconsistent.append("preflight admitted, dispatch denied")

    assert healthy.chat.completions.create.await_count >= 1, (
        "a cancelled half-open probe blocked every later healthy dispatch "
        f"(blob={_breaker_blob(store)})"
    )
    assert not inconsistent, f"deny-all wedge behind an admitting preflight: {inconsistent}"
    assert _breaker_blob(store)["state"] == abs_mod.CB_CLOSED


# ===========================================================================
# W1-3b -- every admitted half-open probe records a total outcome     [RED]
# ===========================================================================
_WEDGE_CASES = _non_transient_4xx() + [
    ("non-sdk-ValueError", ValueError("malformed response payload")),
    ("non-sdk-KeyError", KeyError("choices")),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "exc", [e for _, e in _WEDGE_CASES], ids=[i for i, _ in _WEDGE_CASES]
)
async def test_failing_half_open_probe_never_wedges_deny_all_while_preflight_admits(monkeypatch, exc):
    """Cooldown-expired OPEN breaker; the ONE admitted probe dispatch ends in a
    non-transient 4xx or a non-SDK exception. Per the ruling the probe records a
    total outcome: a 4xx other than 429 records success-for-health or releases
    the slot; a non-SDK exception releases the slot. Either way the exception is
    re-raised unchanged, a later healthy dispatch reaches OpenAI and closes the
    breaker, and there is never an iteration where the preflight admits a
    compare whose dispatch is then denied.

    RED today (re-reproduced for 400): nothing is recorded, the probe INCR is
    spent, the blob stays half_open with half_open_calls 1, and 5/5 healthy
    dispatches raise LLMUnavailableError while the preflight admits 5/5."""
    monkeypatch.setenv(FLAG, "true")
    store, ops, _get, _set, _incr, _expire = _dict_breaker_redis(
        _open_breaker_seed(tripped_ago=abs_mod.CB_RECOVERY_TIMEOUT + 5)
    )
    probe = _mock_openai_client(raises=exc)
    healthy = _mock_openai_client()

    with _all(*_patch_breaker_redis(_get, _set, _incr, _expire)):
        with pytest.raises(type(exc)) as excinfo:
            await _guarded(probe)
        assert excinfo.value is exc, "the probe's exception was not re-raised unchanged"
        assert probe.chat.completions.create.await_count == 1, "harness: probe not dispatched"

        inconsistent = 0
        for _ in range(5):
            _reset_breaker_memo()
            preflight_admits = abs_mod.openai_preflight_allows_compare()
            try:
                await _guarded(healthy)
                admitted = True
            except abs_mod.LLMUnavailableError:
                admitted = False
            if preflight_admits and not admitted:
                inconsistent += 1

    blob = _breaker_blob(store)
    assert healthy.chat.completions.create.await_count >= 1, (
        f"a {type(exc).__name__} half-open probe wedged the breaker in deny-all "
        f"with a healthy OpenAI (blob={blob})"
    )
    assert inconsistent == 0, (
        f"{inconsistent}/5 compares were admitted by the preflight and then denied "
        f"at dispatch -- each pays the full paid fan-out for nothing (blob={blob})"
    )
    assert blob["state"] == abs_mod.CB_CLOSED, f"breaker left {blob['state']!r}: {blob}"
    assert int(blob.get("failure_count") or 0) == 0


# ===========================================================================
# PINS -- behaviour that must NOT change (all pass today)
# ===========================================================================
@pytest.mark.asyncio
async def test_pin_non_transient_4xx_never_trips_the_breaker(monkeypatch):
    """Reviewer M6 pin: a 4xx other than 429 is a REQUEST defect (bad prompt,
    wrong model id, dead key) and must never trip the breaker that gates every
    compare. Three rounds of every shape on a CLOSED breaker record no failure.
    (Measured: RED under M6, `_openai_failure_is_transient` -> always True.)"""
    monkeypatch.setenv(FLAG, "true")
    store, ops, _get, _set, _incr, _expire = _dict_breaker_redis()

    with _all(*_patch_breaker_redis(_get, _set, _incr, _expire)):
        for _ in range(abs_mod.CB_FAILURE_THRESHOLD):
            for _name, exc in _non_transient_4xx():
                client = _mock_openai_client(raises=exc)
                with pytest.raises(type(exc)):
                    await _guarded(client)
                assert client.chat.completions.create.await_count == 1

    blob = _breaker_blob(store)
    assert blob is None or int(blob.get("failure_count") or 0) == 0, (
        f"a non-transient 4xx was recorded as an OpenAI failure: {blob}"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "exc", [e for _, e in _transient_shapes()], ids=[i for i, _ in _transient_shapes()]
)
async def test_pin_transient_shapes_still_record_one_failure(monkeypatch, exc):
    """The genuine OpenAI-health signals keep recording exactly one failure each
    and are re-raised unchanged: 429, connection error, the SDK request timeout
    (APITimeoutError), 500, 503, and a TimeoutError raised from INSIDE the call.
    The W1-3a fix narrows the CancelledError arm only."""
    monkeypatch.setenv(FLAG, "true")
    store, ops, _get, _set, _incr, _expire = _dict_breaker_redis()
    client = _mock_openai_client(raises=exc)

    with _all(*_patch_breaker_redis(_get, _set, _incr, _expire)):
        with pytest.raises(type(exc)) as excinfo:
            await _guarded(client)

    assert excinfo.value is exc
    blob = _breaker_blob(store)
    assert blob is not None and blob["failure_count"] == 1, (
        f"a transient {type(exc).__name__} was not recorded: {blob}"
    )


@pytest.mark.asyncio
async def test_pin_three_sdk_request_timeouts_still_trip(monkeypatch):
    """A genuinely stalled OpenAI (SDK APITimeoutError x3) still trips the
    breaker, and the 4th call is denied without dispatching -- the stall signal
    the MINOR-5 cancellation arm was trying to capture is still captured."""
    monkeypatch.setenv(FLAG, "true")
    store, ops, _get, _set, _incr, _expire = _dict_breaker_redis()
    request = httpx.Request("POST", _URL)
    client = _mock_openai_client(raises=openai_sdk.APITimeoutError(request=request))

    with _all(*_patch_breaker_redis(_get, _set, _incr, _expire)):
        for _ in range(abs_mod.CB_FAILURE_THRESHOLD):
            with pytest.raises(openai_sdk.APITimeoutError):
                await _guarded(client)
        with pytest.raises(abs_mod.LLMUnavailableError):
            await _guarded(client)

    assert client.chat.completions.create.await_count == abs_mod.CB_FAILURE_THRESHOLD
    assert _breaker_blob(store)["state"] == abs_mod.CB_OPEN


@pytest.mark.asyncio
async def test_pin_transient_half_open_probe_failure_reopens_consistently(monkeypatch):
    """A half-open probe that gets a 429 re-OPENs the breaker for a fresh window,
    and the preflight and the dispatch then AGREE (both deny) -- no
    admit-then-deny. W1-3b must not turn a genuine failure into a release."""
    monkeypatch.setenv(FLAG, "true")
    store, ops, _get, _set, _incr, _expire = _dict_breaker_redis(
        _open_breaker_seed(tripped_ago=abs_mod.CB_RECOVERY_TIMEOUT + 5)
    )
    before = time.time()
    probe = _mock_openai_client(raises=_rate_limit_error())
    healthy = _mock_openai_client()

    with _all(*_patch_breaker_redis(_get, _set, _incr, _expire)):
        with pytest.raises(openai_sdk.RateLimitError):
            await _guarded(probe)
        blob = _breaker_blob(store)
        assert blob["state"] == abs_mod.CB_OPEN and blob["tripped_at"] >= before, blob

        _reset_breaker_memo()
        assert abs_mod.openai_preflight_allows_compare() is False
        with pytest.raises(abs_mod.LLMUnavailableError):
            await _guarded(healthy)
    assert healthy.chat.completions.create.await_count == 0


@pytest.mark.asyncio
async def test_pin_in_flight_half_open_probe_still_limits_admission_to_one(monkeypatch):
    """While the single half-open probe is still in flight, a concurrent dispatch
    is denied (CB_HALF_OPEN_MAX_CALLS == 1, the #115 atomic INCR). W1-3b's
    "release the slot" must be a release on the probe's OUTCOME, never an
    always-admit. When the probe then succeeds, the breaker closes."""
    monkeypatch.setenv(FLAG, "true")
    store, ops, _get, _set, _incr, _expire = _dict_breaker_redis(
        _open_breaker_seed(tripped_ago=abs_mod.CB_RECOVERY_TIMEOUT + 5)
    )
    gate = asyncio.Event()
    started = asyncio.Event()
    ok = _mock_openai_client()
    ok_response = ok.chat.completions.create.return_value

    probe_client = MagicMock()

    async def _held_create(**kwargs):
        started.set()
        await gate.wait()
        return ok_response

    probe_client.chat.completions.create = _held_create
    second = _mock_openai_client()

    with _all(*_patch_breaker_redis(_get, _set, _incr, _expire)):
        probe_task = asyncio.ensure_future(_guarded(probe_client))
        await asyncio.wait_for(started.wait(), timeout=5)
        probe_key = _probe_key_for(store)

        _reset_breaker_memo()
        with pytest.raises(abs_mod.LLMUnavailableError):
            await _guarded(second)
        assert second.chat.completions.create.await_count == 0

        gate.set()
        await asyncio.wait_for(probe_task, timeout=5)

    assert store.get(probe_key) is not None
    assert _breaker_blob(store)["state"] == abs_mod.CB_CLOSED


# ---------------------------------------------------------------------------
# Flag-OFF identity pins
# ---------------------------------------------------------------------------
def _breaker_spies():
    seen = {"closed": 0, "fail": 0, "success": 0}

    def _closed(provider):
        seen["closed"] += 1
        return True

    def _fail(provider):
        seen["fail"] += 1

    def _success(provider):
        seen["success"] += 1

    return seen, (
        patch.object(abs_mod, "is_circuit_closed", side_effect=_closed),
        patch.object(abs_mod, "record_failure", side_effect=_fail),
        patch.object(abs_mod, "record_success", side_effect=_success),
    )


@pytest.mark.asyncio
async def test_pin_flag_off_wall_cancelled_dispatches_touch_no_breaker():
    """Flag OFF: the ruling's three-dispatch wall shape makes zero Redis ops and
    no breaker call; the cancellation still propagates as the wall's timeout."""
    store, ops, _get, _set, _incr, _expire = _dict_breaker_redis()
    slow = _SlowClient()
    seen, spies = _breaker_spies()

    with _all(*_patch_breaker_redis(_get, _set, _incr, _expire), *spies):
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(
                asyncio.gather(_guarded(slow), _guarded(slow), _guarded(slow)),
                timeout=0.2,
            )
        task = asyncio.ensure_future(_guarded(slow))
        await asyncio.sleep(0.02)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    assert slow.started == 4
    assert ops == {"get": 0, "set": 0, "incr": 0, "expire": 0}, ops
    assert seen == {"closed": 0, "fail": 0, "success": 0}, seen
    assert store == {}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "exc",
    [e for _, e in _WEDGE_CASES + _transient_shapes()],
    ids=[i for i, _ in _WEDGE_CASES + _transient_shapes()],
)
async def test_pin_flag_off_any_exception_on_a_half_open_blob_touches_nothing(exc):
    """Flag OFF with a poisoned (cooldown-expired OPEN) blob in Redis: every
    exception shape is re-raised as the SAME object, the blob is not read or
    rewritten, and the next call still dispatches."""
    seed = _open_breaker_seed(tripped_ago=abs_mod.CB_RECOVERY_TIMEOUT + 5)
    store, ops, _get, _set, _incr, _expire = _dict_breaker_redis(seed)
    snapshot = dict(store)
    failing = _mock_openai_client(raises=exc)
    healthy = _mock_openai_client()
    seen, spies = _breaker_spies()

    with _all(*_patch_breaker_redis(_get, _set, _incr, _expire), *spies):
        with pytest.raises(type(exc)) as excinfo:
            await _guarded(failing)
        await _guarded(healthy)

    assert excinfo.value is exc
    assert healthy.chat.completions.create.await_count == 1
    assert ops == {"get": 0, "set": 0, "incr": 0, "expire": 0}, ops
    assert seen == {"closed": 0, "fail": 0, "success": 0}, seen
    assert store == snapshot


@pytest.mark.asyncio
async def test_pin_flag_off_tier2_wall_records_nothing(monkeypatch):
    """Reviewer P1b: flag OFF, the same Tier-2 wall shape makes zero breaker
    Redis ops."""
    monkeypatch.setattr(scs, "_TIER2_WALL_SECONDS", 0.3)
    store, ops, _get, _set, _incr, _expire = _dict_breaker_redis()
    slow = _SlowClient(delay=5.0)

    async def _search(query, num_results=3):
        return {"organic": [{"snippet": "x"}]}

    monkeypatch.setattr(ss, "search_web", _search)
    monkeypatch.setattr(oai, "get_client", lambda: slow)

    with _all(*_patch_breaker_redis(_get, _set, _incr, _expire)):
        out = await scs.tier2_fill_non_negotiables(
            brand="Acme", name="Phone", variant=None, category="smartphone", specs_so_far={}
        )

    assert out == {}
    assert slow.started >= 1
    assert store == {} and ops == {"get": 0, "set": 0, "incr": 0, "expire": 0}, ops


def _openai_key_read_counter(get):
    """Wrap the dict stub's GET so ONLY reads of `circuit:openai` are counted --
    the flag-OFF compare path legitimately makes ~12 other breaker GETs (the
    pre-existing firecrawl / scrapedo render gates), which is why the merged
    flag-OFF tests could not assert on `ops` and why M10 survived them."""
    reads = {"openai": 0}
    openai_key = abs_mod._circuit_key(PROVIDER)

    def _counting_get(key):
        if key == openai_key:
            reads["openai"] += 1
        return get(key)

    return reads, _counting_get


def _no_supabase():
    """The compare path's L2 cache (product_data_service) reaches the admin
    Supabase client; conftest points it at `neutralized.supabase.invalid`, which
    still ATTEMPTS a DNS lookup. Make client construction raise instead -- every
    L2 read/save already catches and degrades -- so the zero-network guard sees
    no attempt at all."""
    from app.services import database_service as db_mod
    from app.services import product_data_service as pds_mod

    def _refuse(*args, **kwargs):
        raise RuntimeError("zero-network: supabase stubbed in test_retro_w1_3")

    return (
        patch.object(pds_mod, "get_admin_supabase_client", side_effect=_refuse),
        patch.object(db_mod, "get_admin_supabase_client", side_effect=_refuse),
    )


def test_pin_flag_off_preflight_never_reads_the_openai_breaker():
    """Reviewer M10 pin, fastest form: flag unset + an OPEN blob -> the compare
    entry's preflight returns False (no short-circuit) with ZERO reads of
    `circuit:openai`. (Measured: RED under M10.)"""
    store, ops, _get, _set, _incr, _expire = _dict_breaker_redis(_open_breaker_seed())
    reads, counting_get = _openai_key_read_counter(_get)

    with _all(*_patch_breaker_redis(counting_get, _set, _incr, _expire)):
        assert scs._llm_preflight_short_circuits() is False

    assert reads["openai"] == 0, f"flag OFF read circuit:openai {reads['openai']}x"
    assert ops == {"get": 0, "set": 0, "incr": 0, "expire": 0}, ops


@pytest.mark.asyncio
async def test_pin_flag_off_both_compare_entries_never_read_the_openai_breaker(monkeypatch):
    """Reviewer M10 pin through BOTH real entries (compare_from_text and the
    SSE compare_from_text_streaming): flag unset, OPEN blob seeded, key-filtered
    read counter stays 0 while the fan-out is reached. A flag-ON control run in
    the SAME harness proves the counter can see the read (non-vacuous).
    (Measured: RED under M10.)"""
    _arm_prod_search_config(monkeypatch)

    # Flag OFF: the runs under test.
    store, ops, _get, _set, _incr, _expire = _dict_breaker_redis(_open_breaker_seed())
    reads, counting_get = _openai_key_read_counter(_get)
    fan = _FanOutCounters()
    llm_client = _mock_openai_client()
    with _all(*_patch_breaker_redis(counting_get, _set, _incr, _expire),
              *fan.patches(llm_client), *_no_supabase()):
        result = await _run_compare()
        events = await _run_stream()

    assert result.get("code") != "LLM_UNAVAILABLE"
    assert "LLM_UNAVAILABLE" not in [d.get("code") for e, d in events if e == "error"]
    assert fan.total > 0, "harness: flag OFF never reached the fan-out"
    assert reads["openai"] == 0, (
        f"flag OFF read circuit:openai {reads['openai']}x across the two compare "
        "entries -- a blocking Upstash GET added to every flag-OFF compare"
    )

    # Flag ON control: the identical harness DOES read the key.
    monkeypatch.setenv(FLAG, "true")
    _reset_breaker_memo()
    store2, ops2, _get2, _set2, _incr2, _expire2 = _dict_breaker_redis(_open_breaker_seed())
    reads_on, counting_get_on = _openai_key_read_counter(_get2)
    fan_on = _FanOutCounters()
    with _all(*_patch_breaker_redis(counting_get_on, _set2, _incr2, _expire2),
              *fan_on.patches(_mock_openai_client()), *_no_supabase()):
        on_result = await _run_compare()
    assert on_result.get("code") == "LLM_UNAVAILABLE"
    assert reads_on["openai"] >= 1, "control: the counter never saw a circuit:openai read"


# ===========================================================================
# GREEN-phase pins -- which TOTAL outcome each probe shape records
# ===========================================================================
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "exc",
    [ValueError("malformed response payload"), KeyError("choices")],
    ids=["non-sdk-ValueError", "non-sdk-KeyError"],
)
async def test_green_non_sdk_probe_exception_releases_the_slot_not_success(monkeypatch, exc):
    """Per the ruling a non-SDK exception on a half-open probe RELEASES the slot:
    the blob stays half_open (no verdict recorded) and the per-trip probe
    counter is reset to 0, so the next dispatch takes the probe. It must not be
    recorded as a success (that would close the breaker on no evidence) nor as a
    failure (that would re-open it on no evidence)."""
    monkeypatch.setenv(FLAG, "true")
    store, ops, _get, _set, _incr, _expire = _dict_breaker_redis(
        _open_breaker_seed(tripped_ago=abs_mod.CB_RECOVERY_TIMEOUT + 5)
    )
    probe = _mock_openai_client(raises=exc)

    with _all(*_patch_breaker_redis(_get, _set, _incr, _expire)):
        with pytest.raises(type(exc)):
            await _guarded(probe)

    blob = _breaker_blob(store)
    assert blob["state"] == abs_mod.CB_HALF_OPEN, f"expected a release, not a verdict: {blob}"
    assert int(blob.get("failure_count") or 0) == abs_mod.CB_FAILURE_THRESHOLD, blob
    assert store[_probe_key_for(store)] == "0", "the probe slot was not released"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "exc", [e for _, e in _non_transient_4xx()], ids=[i for i, _ in _non_transient_4xx()]
)
async def test_green_4xx_probe_records_success_for_health(monkeypatch, exc):
    """This implementation's choice among the ruling's two options: a 4xx other
    than 429 on the half-open probe means OpenAI ANSWERED, so it is recorded as
    success-for-health and the breaker closes immediately (failure_count 0)."""
    monkeypatch.setenv(FLAG, "true")
    store, ops, _get, _set, _incr, _expire = _dict_breaker_redis(
        _open_breaker_seed(tripped_ago=abs_mod.CB_RECOVERY_TIMEOUT + 5)
    )
    probe = _mock_openai_client(raises=exc)

    with _all(*_patch_breaker_redis(_get, _set, _incr, _expire)):
        with pytest.raises(type(exc)) as excinfo:
            await _guarded(probe)

    assert excinfo.value is exc
    blob = _breaker_blob(store)
    assert blob["state"] == abs_mod.CB_CLOSED and blob["failure_count"] == 0, blob


@pytest.mark.asyncio
async def test_green_release_discards_denied_checks_counted_while_probe_in_flight(monkeypatch):
    """The release RESETS the probe counter (it is not a DECR): checks that were
    denied while the probe was in flight also INCRed it, so a DECR of the
    probe's own increment would leave the counter >= 1 and re-wedge. Two denied
    dispatches during the probe, then the probe is cancelled: the next healthy
    dispatch must still be admitted and close the breaker."""
    monkeypatch.setenv(FLAG, "true")
    store, ops, _get, _set, _incr, _expire = _dict_breaker_redis(
        _open_breaker_seed(tripped_ago=abs_mod.CB_RECOVERY_TIMEOUT + 5)
    )
    slow = _SlowClient()
    denied = _mock_openai_client()
    healthy = _mock_openai_client()

    with _all(*_patch_breaker_redis(_get, _set, _incr, _expire)):
        task = asyncio.ensure_future(_guarded(slow))
        for _ in range(50):
            if slow.started:
                break
            await asyncio.sleep(0.005)
        assert slow.started == 1, "harness: the probe never dispatched"
        for _ in range(2):
            _reset_breaker_memo()
            with pytest.raises(abs_mod.LLMUnavailableError):
                await _guarded(denied)
        assert int(store[_probe_key_for(store)]) == 3, "harness: denied checks did not INCR"

        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

        _reset_breaker_memo()
        await _guarded(healthy)

    assert denied.chat.completions.create.await_count == 0
    assert healthy.chat.completions.create.await_count == 1
    assert _breaker_blob(store)["state"] == abs_mod.CB_CLOSED


@pytest.mark.asyncio
async def test_green_cancel_on_closed_streak_admission_makes_no_release_call(monkeypatch):
    """A cancel on a CLOSED breaker with a standing failure streak (admitted
    without the probe path) records nothing AND makes no release round trip:
    exactly the one snapshot GET, no SET. The release is for probe admissions
    only."""
    monkeypatch.setenv(FLAG, "true")
    seed = {
        abs_mod._circuit_key(PROVIDER): (
            '{"state": "%s", "failure_count": 1, "last_failure_at": %f}'
            % (abs_mod.CB_CLOSED, time.time())
        )
    }
    store, ops, _get, _set, _incr, _expire = _dict_breaker_redis(seed)
    snapshot = dict(store)
    slow = _SlowClient()

    with _all(*_patch_breaker_redis(_get, _set, _incr, _expire)):
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(_guarded(slow), timeout=0.1)

    assert slow.started == 1
    assert ops == {"get": 1, "set": 0, "incr": 0, "expire": 0}, ops
    assert store == snapshot


@pytest.mark.parametrize("state", ["closed", "open"])
def test_green_release_writes_nothing_unless_the_blob_is_half_open(monkeypatch, state):
    """If another dispatch already recorded the probe's verdict (CLOSED, or a
    re-trip to OPEN) there is no slot to release: one GET, no SET, store
    untouched."""
    monkeypatch.setenv(FLAG, "true")
    seed = {
        abs_mod._circuit_key(PROVIDER): (
            '{"state": "%s", "failure_count": 0, "tripped_at": %f}' % (state, time.time())
        )
    }
    store, ops, _get, _set, _incr, _expire = _dict_breaker_redis(seed)
    snapshot = dict(store)
    with _all(*_patch_breaker_redis(_get, _set, _incr, _expire)):
        abs_mod.openai_release_half_open_probe()
    assert ops == {"get": 1, "set": 0, "incr": 0, "expire": 0}, ops
    assert store == snapshot


def test_green_release_helper_is_a_no_op_with_the_flag_off():
    """The new release helper carries its own flag read: flag OFF it makes zero
    Redis ops even on a half_open blob."""
    seed = {
        abs_mod._circuit_key(PROVIDER): (
            '{"state": "%s", "failure_count": 3, "tripped_at": 1.0, "half_open_calls": 1}'
            % abs_mod.CB_HALF_OPEN
        )
    }
    store, ops, _get, _set, _incr, _expire = _dict_breaker_redis(seed)
    snapshot = dict(store)
    with _all(*_patch_breaker_redis(_get, _set, _incr, _expire)):
        abs_mod.openai_release_half_open_probe()
    assert ops == {"get": 0, "set": 0, "incr": 0, "expire": 0}, ops
    assert store == snapshot



# ===========================================================================
# FIX-phase pins (retro adversary on the green): outcome-level pins for the
# cancel arm (N5/N6), the probe-only Exception arm (N1), and the teardown-class
# BaseException arm that makes "every admitted probe records a total outcome"
# literally total.
# ===========================================================================
class _ProcessTeardown(BaseException):
    """A BaseException that is neither CancelledError nor Exception -- the
    shape KeyboardInterrupt / SystemExit take through the guard. A private
    subclass is used so a failing test can never interrupt the pytest run the
    way a real KeyboardInterrupt would."""


def _closed_streak_seed(failures=2):
    return {
        abs_mod._circuit_key(PROVIDER): (
            '{"state": "%s", "failure_count": %d, "last_failure_at": %f}'
            % (abs_mod.CB_CLOSED, failures, time.time())
        )
    }


def _assert_released_not_decided(store, context):
    blob = _breaker_blob(store)
    assert blob["state"] == abs_mod.CB_HALF_OPEN, (
        f"{context}: expected a slot release (blob still half_open), got a verdict: {blob}"
    )
    assert int(blob.get("failure_count") or 0) == abs_mod.CB_FAILURE_THRESHOLD, (
        f"{context}: the failure streak moved: {blob}"
    )
    assert store[_probe_key_for(store)] == "0", f"{context}: the probe slot was not released"


@pytest.mark.asyncio
@pytest.mark.parametrize("how", ["outer-wall", "task-cancel"])
async def test_fix_cancelled_probe_is_a_release_not_a_verdict(monkeypatch, how):
    """Ruling (1): a bare cancel records NOTHING; a cancelled half-open probe
    only RELEASES its slot. Right after the cancel the blob must still be
    half_open with the failure streak unchanged and the probe counter at '0'.
    The end-state tests above cannot see this: a cancel recorded as SUCCESS
    (mutation N5) also ends CLOSED after a later healthy call -- and would
    close the breaker with no evidence during a real OpenAI outage."""
    monkeypatch.setenv(FLAG, "true")
    store, ops, _get, _set, _incr, _expire = _dict_breaker_redis(
        _open_breaker_seed(tripped_ago=abs_mod.CB_RECOVERY_TIMEOUT + 5)
    )
    slow = _SlowClient()

    with _all(*_patch_breaker_redis(_get, _set, _incr, _expire)):
        if how == "outer-wall":
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(_guarded(slow), timeout=0.1)
        else:
            task = asyncio.ensure_future(_guarded(slow))
            for _ in range(50):
                if slow.started:
                    break
                await asyncio.sleep(0.005)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task

    assert slow.started == 1, "harness: the half-open probe never dispatched"
    _assert_released_not_decided(store, f"cancelled probe ({how})")


_CLOSED_STREAK_NON_TRANSIENT = [
    ("400-context-length", _status_error(openai_sdk.BadRequestError, 400)),
    ("non-sdk-ValueError", ValueError("malformed response payload")),
    ("teardown-BaseException", _ProcessTeardown("process teardown")),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "exc",
    [e for _, e in _CLOSED_STREAK_NON_TRANSIENT],
    ids=[i for i, _ in _CLOSED_STREAK_NON_TRANSIENT],
)
async def test_fix_closed_streak_non_transient_outcome_is_not_recorded(monkeypatch, exc):
    """W1-3b changes ONLY half-open probe outcomes. On a CLOSED breaker with a
    standing failure streak (admitted without the probe path) a 4xx, a non-SDK
    exception or a teardown BaseException records nothing and makes no release
    round trip: exactly the one snapshot GET, no SET, the streak untouched.
    Mutation N1 (`elif probe` -> `elif outcome_matters`) makes the 400 wipe the
    streak with a SET and the ValueError pay a release GET on the hot path."""
    monkeypatch.setenv(FLAG, "true")
    store, ops, _get, _set, _incr, _expire = _dict_breaker_redis(_closed_streak_seed(2))
    snapshot = dict(store)
    client = _mock_openai_client(raises=exc)

    with _all(*_patch_breaker_redis(_get, _set, _incr, _expire)):
        with pytest.raises(type(exc)) as excinfo:
            await _guarded(client)

    assert excinfo.value is exc
    assert client.chat.completions.create.await_count == 1
    assert ops == {"get": 1, "set": 0, "incr": 0, "expire": 0}, ops
    assert store == snapshot
    assert _breaker_blob(store)["failure_count"] == 2


@pytest.mark.asyncio
async def test_fix_teardown_base_exception_on_probe_releases_the_slot(monkeypatch):
    """A half-open probe ending in a BaseException that is neither
    CancelledError nor Exception (KeyboardInterrupt / SystemExit shape) records
    no verdict and releases the slot, and the exception object is re-raised
    unchanged. Before this arm the probe INCR stayed spent (counter 1, blob
    half_open) and every later dispatch was denied while the preflight admitted
    -- the W1-3b wedge until the 3600 s blob TTL."""
    monkeypatch.setenv(FLAG, "true")
    store, ops, _get, _set, _incr, _expire = _dict_breaker_redis(
        _open_breaker_seed(tripped_ago=abs_mod.CB_RECOVERY_TIMEOUT + 5)
    )
    exc = _ProcessTeardown("process teardown")
    probe = _mock_openai_client(raises=exc)
    healthy = _mock_openai_client()

    with _all(*_patch_breaker_redis(_get, _set, _incr, _expire)):
        with pytest.raises(_ProcessTeardown) as excinfo:
            await _guarded(probe)
        assert excinfo.value is exc
        assert probe.chat.completions.create.await_count == 1
        _assert_released_not_decided(store, "teardown probe")

        _reset_breaker_memo()
        assert abs_mod.openai_preflight_allows_compare()
        await _guarded(healthy)

    assert healthy.chat.completions.create.await_count == 1
    assert _breaker_blob(store)["state"] == abs_mod.CB_CLOSED


@pytest.mark.asyncio
async def test_fix_orphaned_probe_coroutine_closed_releases_the_slot(monkeypatch):
    """An orphaned probe coroutine that is CLOSED (coro.close() -> GeneratorExit
    at its await, what garbage collection of a dropped coroutine does) releases
    the slot instead of leaving it spent. SIGKILL / OOM stay out of scope
    (ruling 4) -- no Python code runs there."""
    monkeypatch.setenv(FLAG, "true")
    store, ops, _get, _set, _incr, _expire = _dict_breaker_redis(
        _open_breaker_seed(tripped_ago=abs_mod.CB_RECOVERY_TIMEOUT + 5)
    )
    slow = _SlowClient()

    with _all(*_patch_breaker_redis(_get, _set, _incr, _expire)):
        coro = _guarded(slow)
        coro.send(None)  # runs up to the in-flight OpenAI await, then suspends
        assert slow.started == 1, "harness: the probe never dispatched"
        assert store[_probe_key_for(store)] == "1", "harness: the probe INCR was not spent"
        coro.close()

    _assert_released_not_decided(store, "closed orphan probe")


@pytest.mark.asyncio
async def test_fix_flag_off_teardown_and_close_touch_nothing():
    """Flag OFF: a teardown BaseException is re-raised as the same object and a
    closed in-flight dispatch finishes closing, both with zero Redis ops and no
    breaker call, on a poisoned (cooldown-expired OPEN) blob."""
    seed = _open_breaker_seed(tripped_ago=abs_mod.CB_RECOVERY_TIMEOUT + 5)
    store, ops, _get, _set, _incr, _expire = _dict_breaker_redis(seed)
    snapshot = dict(store)
    exc = _ProcessTeardown("process teardown")
    failing = _mock_openai_client(raises=exc)
    slow = _SlowClient()
    seen, spies = _breaker_spies()

    with _all(*_patch_breaker_redis(_get, _set, _incr, _expire), *spies):
        with pytest.raises(_ProcessTeardown) as excinfo:
            await _guarded(failing)
        coro = _guarded(slow)
        coro.send(None)
        coro.close()

    assert excinfo.value is exc
    assert slow.started == 1
    assert ops == {"get": 0, "set": 0, "incr": 0, "expire": 0}, ops
    assert seen == {"closed": 0, "fail": 0, "success": 0}, seen
    assert store == snapshot
