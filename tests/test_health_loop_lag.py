"""W1-10 (SESSION 65) RED tests -- ``/health`` reports event-loop lag.

Finding ``LS-FAILURE-MODES-COST-13`` / issue ``#81``. ``GET /health`` returns a
static two-key dict (``app/main.py``: ``{"status": "healthy", "message":
"Qaren API is running"}``). Nothing anywhere reports whether the single uvicorn
worker's loop is actually TURNING. That is the one measurement that
distinguishes "the app is slow" from "the app is wedged", and it is the signal
the activation runbook says to watch through every W5 STEP 0 flag flip.

WHY A HEARTBEAT AND NOT AN INLINE MEASUREMENT
    Measuring inside the handler (``t0 = loop.time(); await asyncio.sleep(0)``)
    only samples the loop at a moment it is demonstrably already running -- it
    cannot observe the interval during which the loop was BLOCKED, which is the
    entire question. A heartbeat due at T that runs at T+11s reports 11,000 ms,
    which is exactly the ``getaddrinfo`` stall W0-1 exists to bound.

-------------------------------------------------------------------------------
CONTRACT PINNED BY THESE TESTS  (``app/main.py`` -- W1-10 is app/main.py only)
-------------------------------------------------------------------------------
The spec names the DESIGN (a startup task looping on ``await
asyncio.sleep(INTERVAL)``, recording ``elapsed - INTERVAL`` in ms, keeping the
LAST value and a rolling MAX, both reported by ``/health``) but does not name
the symbols. These are the names the RED tests pin, so the GREEN implementer
has one unambiguous target:

  ``app.main.LOOP_LAG_INTERVAL_SECONDS`` : float
      The heartbeat interval.

  ``app.main.record_loop_lag_tick(elapsed_seconds: float) -> None``
      Record ONE heartbeat tick. ``lag_ms = max(0.0, (elapsed_seconds -
      LOOP_LAG_INTERVAL_SECONDS) * 1000.0)``. Updates the LAST value and the
      rolling MAX since process start. This is the seam the tests drive
      directly -- feeding the elapsed interval rather than sleeping on a real
      clock, so a 500 ms overshoot is asserted deterministically and NOT via
      wall-clock on a loaded CI box (the spec explicitly forbids the
      ``time.sleep`` + wall-clock form as a flake).

  ``app.main.loop_lag_snapshot() -> dict``
      ``{"loop_lag_ms": <number>, "loop_lag_max_ms": <number>}`` -- exactly the
      two keys ``/health`` merges into its payload. A pure dict read.

  ``app.main._loop_lag_heartbeat()`` : coroutine function
      The task body started on ``startup``. Its ``CancelledError`` must
      PROPAGATE, not be swallowed.

  ``app.main._loop_lag_task``
      The ``asyncio.Task`` handle, so ``shutdown`` can cancel it. ``None``
      before startup.

CONSTRAINTS THE TESTS ALSO PIN
  * The ``/health`` handler stays a DICT READ -- no awaits, no I/O. It is
    Railway's deploy healthcheck with a 30 s timeout and must not become a
    thing that can fail.
  * ``max`` is reported ALONGSIDE ``last``: a probe polling every 30 s samples
    1 second in 30 and would miss almost every stall; the max is what makes a
    low-frequency probe able to see one.
  * ADDITIVE ONLY: ``status`` and ``message`` keep their exact current values,
    because an external uptime check may already be string-matching them.
  * ``CancelledError`` is a ``BaseException``, so a bare ``except Exception``
    will NOT catch it. The spec says verify that rather than assume it --
    ``test_heartbeat_does_not_swallow_cancellation`` does exactly that against
    the real coroutine, so a future ``except BaseException`` / bare ``except:``
    / ``except asyncio.CancelledError: return`` regression is caught.

-------------------------------------------------------------------------------
Expected state at RED
-------------------------------------------------------------------------------
  * ``test_health_reports_loop_lag_keys_as_numbers``        -- RED (keys absent)
  * ``test_recorder_reports_a_500ms_overshoot``             -- RED (no recorder)
  * ``test_max_is_retained_after_a_subsequent_fast_tick``   -- RED (no recorder)
  * ``test_heartbeat_task_is_started_and_cancelled_by_lifespan`` -- RED (no task)
  * ``test_heartbeat_does_not_swallow_cancellation``        -- RED (no coroutine)
  * ``test_health_status_and_message_are_unchanged``  -- GREEN, ADDITIVE PIN
  * ``test_health_handler_is_a_pure_dict_read``       -- GREEN, CONSTRAINT PIN

Every RED node above fails on an ASSERTION about behaviour that is genuinely
absent -- never on a bare ``AttributeError``/``ImportError`` for a symbol that
does not exist yet. ``_require`` turns a missing symbol into an explicit
``pytest.fail`` naming the contract.
"""
import asyncio
import inspect
import numbers

import pytest
from fastapi.testclient import TestClient

from app.main import app
import app.main as app_main

# The current, shipped payload. Additive-only means these survive verbatim.
_CURRENT_STATUS = "healthy"
_CURRENT_MESSAGE = "Qaren API is running"

_CONTRACT = (
    "app/main.py must expose the W1-10 loop-lag recorder: "
    "LOOP_LAG_INTERVAL_SECONDS (float), "
    "record_loop_lag_tick(elapsed_seconds) -> None, "
    "loop_lag_snapshot() -> {'loop_lag_ms': num, 'loop_lag_max_ms': num}, "
    "_loop_lag_heartbeat() (coroutine fn), and _loop_lag_task (the Task handle). "
    "See this module's docstring for the full contract."
)


def _require(name):
    """Fetch a required contract symbol, or fail with WHAT is missing.

    Deliberately not a bare ``getattr``: a RED run must say "the behaviour is
    absent", not raise AttributeError from inside a test body.
    """
    sentinel = object()
    value = getattr(app_main, name, sentinel)
    if value is sentinel:
        pytest.fail(f"app.main has no {name!r} -- behaviour absent.\n{_CONTRACT}")
    return value


def _health_payload() -> dict:
    """GET /health through the real ASGI app."""
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200, (
        f"/health returned {response.status_code}; it is Railway's deploy "
        "healthcheck and must never fail"
    )
    return response.json()


# ---------------------------------------------------------------------------
# 5 -- /health reports both lag numbers  (RED: neither key exists)
# ---------------------------------------------------------------------------


def test_health_reports_loop_lag_keys_as_numbers():
    """RED today: ``/health`` is a static two-key dict with no loop signal.

    Both keys are required. ``loop_lag_ms`` alone is not enough: an external
    probe polling every 30 s samples 1 second in 30 and would miss almost every
    stall, so ``loop_lag_max_ms`` (since process start) is what makes a
    low-frequency probe able to SEE one.

    Booleans are rejected explicitly -- ``bool`` is a subclass of ``int`` in
    Python, and a placeholder ``True`` would otherwise sail through a naive
    numeric check.
    """
    payload = _health_payload()

    for key in ("loop_lag_ms", "loop_lag_max_ms"):
        assert key in payload, (
            f"/health payload has no {key!r}; nothing reports whether the single "
            f"uvicorn worker's loop is turning. got keys={sorted(payload)}"
        )
        value = payload[key]
        assert not isinstance(value, bool), f"/health {key!r} is a bool, not a number"
        assert isinstance(value, numbers.Real), (
            f"/health {key!r} must be a number (milliseconds); got "
            f"{type(value).__name__} {value!r}"
        )
        assert value >= 0, f"/health {key!r} is negative: {value!r}"

    assert payload["loop_lag_max_ms"] >= payload["loop_lag_ms"], (
        "loop_lag_max_ms must be the rolling MAX since process start, so it can "
        "never be below the last sample; got "
        f"max={payload['loop_lag_max_ms']!r} last={payload['loop_lag_ms']!r}"
    )


# ---------------------------------------------------------------------------
# 6 -- additive only  (GREEN today, must stay green)
# ---------------------------------------------------------------------------


def test_health_status_and_message_are_unchanged():
    """ADDITIVE PIN -- GREEN TODAY and must stay green.

    An external uptime check may already be string-matching these exact values,
    so W1-10 may only ADD keys. Do not "tidy" the message.
    """
    payload = _health_payload()
    assert payload.get("status") == _CURRENT_STATUS, (
        f"/health 'status' changed from {_CURRENT_STATUS!r} to "
        f"{payload.get('status')!r}; W1-10 is additive only"
    )
    assert payload.get("message") == _CURRENT_MESSAGE, (
        f"/health 'message' changed from {_CURRENT_MESSAGE!r} to "
        f"{payload.get('message')!r}; W1-10 is additive only"
    )


def test_health_handler_is_a_pure_dict_read():
    """CONSTRAINT PIN -- GREEN TODAY and must stay green.

    ``/health`` is Railway's deploy healthcheck with a 30 s timeout. It must
    not become a thing that can fail or block: no ``await``, no I/O. The lag
    numbers come from module state the heartbeat already wrote.

    Source inspection is the right instrument here -- a behavioural test cannot
    distinguish "read a dict" from "awaited something that happened to be fast".
    """
    handler = app_main.health_check
    source = inspect.getsource(handler)
    body = source.split("\n", 1)[1] if "\n" in source else ""

    assert "await " not in body, (
        "/health handler awaits something. It must stay a pure dict read -- it "
        f"is the deploy healthcheck.\n{source}"
    )
    for forbidden in ("asyncio.sleep", "requests.", "httpx.", "get_cached", "execute("):
        assert forbidden not in body, (
            f"/health handler references {forbidden!r}; the handler must do no "
            f"I/O.\n{source}"
        )


# ---------------------------------------------------------------------------
# 7 -- the recorder observes a real stall  (RED: no recorder exists)
# ---------------------------------------------------------------------------


def test_recorder_reports_a_500ms_overshoot():
    """A heartbeat that overshoots its interval by 500 ms reports ~500 ms.

    Driven directly with an explicit elapsed value rather than a wall-clock
    sleep: the spec forbids a ``time.sleep``-and-assert-on-wall-clock test,
    which is a flake on a loaded CI box.

    RED today: ``app.main`` exposes no recorder at all.
    """
    interval = _require("LOOP_LAG_INTERVAL_SECONDS")
    record = _require("record_loop_lag_tick")
    snapshot = _require("loop_lag_snapshot")

    assert isinstance(interval, numbers.Real) and interval > 0, (
        f"LOOP_LAG_INTERVAL_SECONDS must be a positive number; got {interval!r}"
    )

    record(float(interval) + 0.5)
    last = snapshot()["loop_lag_ms"]

    assert last == pytest.approx(500.0, abs=1.0), (
        "a tick that took INTERVAL + 0.5s must report ~500 ms of lag "
        f"(elapsed - INTERVAL, in ms); got {last!r}"
    )


def test_max_is_retained_after_a_subsequent_fast_tick():
    """The rolling MAX survives a healthy tick; the LAST value drops.

    This is the property that lets a 30 s probe see a stall it never sampled.

    Asserted RELATIVE to a baseline rather than against absolute zero, so the
    test is order-independent: another test in the same process may already
    have pushed the process-wide max up.

    RED today: no recorder exists.
    """
    interval = float(_require("LOOP_LAG_INTERVAL_SECONDS"))
    record = _require("record_loop_lag_tick")
    snapshot = _require("loop_lag_snapshot")

    # A stall, then a healthy tick.
    record(interval + 0.5)
    after_stall = snapshot()
    stall_max = after_stall["loop_lag_max_ms"]

    assert stall_max >= 500.0 - 1.0, (
        f"the 500 ms stall did not reach the rolling max; got {stall_max!r}"
    )

    record(interval)  # dead-on: zero lag
    after_fast = snapshot()

    assert after_fast["loop_lag_ms"] == pytest.approx(0.0, abs=1.0), (
        "a tick that took exactly INTERVAL must report ~0 ms of lag; got "
        f"{after_fast['loop_lag_ms']!r}"
    )
    assert after_fast["loop_lag_max_ms"] == pytest.approx(stall_max, abs=1e-6), (
        "loop_lag_max_ms must be RETAINED across a subsequent fast tick -- it is "
        "the max since process start, not the max of the last sample. got "
        f"{after_fast['loop_lag_max_ms']!r}, expected {stall_max!r}"
    )


def test_recorder_never_reports_negative_lag():
    """An early tick (elapsed < INTERVAL, clock granularity) floors at 0.

    A negative "lag" is meaningless and would corrupt the max comparison.
    RED today: no recorder exists.
    """
    interval = float(_require("LOOP_LAG_INTERVAL_SECONDS"))
    record = _require("record_loop_lag_tick")
    snapshot = _require("loop_lag_snapshot")

    record(max(0.0, interval - 0.01))
    assert snapshot()["loop_lag_ms"] >= 0.0, (
        "lag floored at 0; an elapsed shorter than INTERVAL must not report a "
        f"negative value. got {snapshot()['loop_lag_ms']!r}"
    )


# ---------------------------------------------------------------------------
# 8 -- the task stops on shutdown and does not swallow CancelledError
# ---------------------------------------------------------------------------


def test_heartbeat_task_is_started_and_cancelled_by_lifespan():
    """Startup starts the heartbeat; shutdown stops it.

    Driven through the REAL ASGI lifespan (``with TestClient(app)`` runs the
    app's registered startup handlers on entry and its shutdown handlers on
    exit), so this pins production wiring rather than a hand-rolled imitation.

    Deliberately NOT written against ``app.router.on_startup`` /
    ``.on_shutdown``: this repo runs a different fastapi/starlette locally
    (0.115.0 / 0.38.6) than ``requirements.txt`` pins for CI and Railway
    (0.141.1 / 1.6.0), and framework introspection here must be duck-typed, not
    shape-assuming -- see CLAUDE.md and ``tests/_route_introspection.py``. The
    lifespan protocol is the stable public surface across both.

    The recommended shutdown idiom, which also satisfies
    ``test_heartbeat_does_not_swallow_cancellation``::

        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    (Suppressing at the CANCELLER is fine; the coroutine itself must still let
    CancelledError propagate.)

    RED today: no startup handler creates a lag task, so ``_loop_lag_task``
    never exists.
    """
    _require("_loop_lag_heartbeat")

    with TestClient(app) as client:
        task = getattr(app_main, "_loop_lag_task", None)
        assert task is not None, (
            "after lifespan startup, app.main._loop_lag_task is None -- no "
            f"heartbeat task was created.\n{_CONTRACT}"
        )
        assert isinstance(task, asyncio.Task), (
            f"_loop_lag_task must be an asyncio.Task; got {type(task).__name__}"
        )
        assert not task.done(), (
            "the heartbeat task finished immediately after startup"
        )
        # The heartbeat must not break the healthcheck it feeds.
        assert client.get("/health").status_code == 200
        captured = task

    # The `with` block exit ran the shutdown handlers.
    cancelling = getattr(captured, "cancelling", lambda: 0)()
    assert captured.done() or cancelling > 0, (
        "the heartbeat task was neither stopped nor cancel-requested by "
        "shutdown -- it must be cancelled, not left running"
    )
    if captured.done():
        assert captured.cancelled(), (
            "the heartbeat task finished on shutdown but was NOT cancelled -- "
            "its CancelledError was swallowed instead of propagating"
        )


@pytest.mark.asyncio
async def test_heartbeat_does_not_swallow_cancellation():
    """CancelledError must PROPAGATE out of the heartbeat coroutine.

    ``asyncio.CancelledError`` is a ``BaseException`` in Python 3.8+, so a bare
    ``except Exception`` around the loop body does NOT catch it -- the spec says
    verify that rather than assume it. This test verifies it against the real
    coroutine, and is the regression pin against a future ``except:`` /
    ``except BaseException:`` / ``except asyncio.CancelledError: return``,
    any of which would leave a task that shutdown cannot stop.

    RED today: ``app.main`` has no ``_loop_lag_heartbeat``.
    """
    heartbeat = _require("_loop_lag_heartbeat")
    assert inspect.iscoroutinefunction(heartbeat), (
        f"_loop_lag_heartbeat must be a coroutine function; got {heartbeat!r}"
    )

    task = asyncio.create_task(heartbeat())
    # Let it reach its first await point.
    await asyncio.sleep(0)
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task

    assert task.cancelled(), (
        "the heartbeat task did not end cancelled -- CancelledError was caught "
        "and swallowed instead of propagating"
    )


# ---------------------------------------------------------------------------
# Fable review additions (W1-10) -- two pins that were MISSING.
#
# An adversarial pass showed that two of the tests above named a requirement
# without pinning it, both reproduced by deletion:
#   * deleting the ENTIRE `@app.on_event("shutdown")` handler left the file
#     green -- `captured.done() or cancelling > 0` is satisfied either way;
#   * deleting `record_loop_lag_tick(now - previous)` from the heartbeat left
#     the file green -- the recorder tests drive the recorder DIRECTLY, so
#     nothing connected the loop to it.
# A metric whose wiring is untested is a metric that can silently read 0
# forever, which is worse than no metric: it reads as "the loop is fine".
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_heartbeat_actually_calls_the_recorder():
    """PINS THE WIRING. Fails if `record_loop_lag_tick(...)` is removed from
    `_loop_lag_heartbeat`, which the recorder-only tests cannot see."""
    import asyncio as _asyncio
    import app.main as main

    seen: list[float] = []
    orig_interval = main.LOOP_LAG_INTERVAL_SECONDS
    orig_recorder = main.record_loop_lag_tick
    main.LOOP_LAG_INTERVAL_SECONDS = 0.01
    main.record_loop_lag_tick = lambda elapsed: seen.append(elapsed)
    try:
        task = _asyncio.create_task(main._loop_lag_heartbeat())
        for _ in range(200):
            if seen:
                break
            await _asyncio.sleep(0.005)
        task.cancel()
        try:
            await task
        except _asyncio.CancelledError:
            pass
    finally:
        main.LOOP_LAG_INTERVAL_SECONDS = orig_interval
        main.record_loop_lag_tick = orig_recorder

    assert seen, (
        "the heartbeat never called record_loop_lag_tick -- the loop is not "
        "wired to the recorder, so /health would report 0 lag forever"
    )
    assert seen[0] >= 0.0


@pytest.mark.asyncio
async def test_shutdown_handler_actually_cancels_the_task():
    """PINS THE CANCEL. Fails if the shutdown handler's body is removed.

    Asserts on the OBSERVED terminal state of a real task, not on a predicate
    that a never-started task also satisfies.
    """
    import asyncio as _asyncio
    import app.main as main

    async def _forever() -> None:
        await _asyncio.sleep(3600)

    task = _asyncio.create_task(_forever())
    await _asyncio.sleep(0)  # let it start
    assert not task.done()

    orig = main._loop_lag_task
    main._loop_lag_task = task
    try:
        await main._stop_loop_lag_heartbeat()
    finally:
        if main._loop_lag_task is task:
            main._loop_lag_task = orig

    assert task.cancelled(), (
        "the shutdown handler did not cancel the heartbeat task; it would "
        "survive shutdown and keep the loop alive"
    )
    assert main._loop_lag_task is None, (
        "the shutdown handler must clear the task handle"
    )
