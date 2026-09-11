"""W1-6 (SESSION 65) RED tests -- a shutdown that DRAINS, so an offloaded
refund is not lost.

Finding ``LS-FAILURE-MODES-COST-05``. No feature flag: this is ops behaviour,
and it only ever waits LONGER, never shorter.

-------------------------------------------------------------------------------
THE MECHANISM, RE-CONFIRMED IN CODE AT THIS HEAD
-------------------------------------------------------------------------------
``app/utils/async_utils.py::fire_and_forget`` does ``asyncio.create_task(coro)``,
attaches an exception-logging done-callback, and returns the task to a caller
that ignores it. There is **no task set, no drain, and no shutdown handler that
awaits them**: the only ``@app.on_event("shutdown")`` in ``app/main.py`` is
W1-10's ``_stop_loop_lag_heartbeat``, and the only ``asyncio.wait(`` in the tree
is the price fan-out's, not a shutdown drain.

``usage_service.refund_comparison_credit`` is reached through ``fire_and_forget``
from the compare routes when a comparison fails *after* the gate already debited
a credit. RE-COUNTED AT THIS HEAD, and it is **seven** sites, not the spec's six:
``text_routes.py`` :296 :449 :722 :736, ``image_routes.py`` :166, and
``url_routes.py`` :102 :112 -- the last two are NOT named in the spec and are
recent (W2-1 put ``/url/compare`` behind the metering gate, so those refunds are
newly real). Its body::

    if _redis_offload_enabled():
        await asyncio.to_thread(_refund_credit_sync, ...)   # YIELDS
    else:
        _refund_credit_sync(...)                            # runs inline

With ``ENABLE_ASYNC_REDIS_OFFLOAD`` OFF the refund body runs to completion with
no suspension point, so it survives today by accident. Flip the flag and the
task is mid-``await`` at shutdown, untracked, and simply dropped -- the user paid
a credit for a compare that failed and the refund evaporated on whichever deploy
happened to be in flight. That is why this unit is a HARD PRECONDITION for the
``ENABLE_ASYNC_REDIS_OFFLOAD`` canary. ``test_refund_survives_a_shutdown_that_
races_the_offloaded_refund`` below is that finding, executed.

-------------------------------------------------------------------------------
CONTRACT PINNED BY THESE TESTS
-------------------------------------------------------------------------------
The spec names the DESIGN but not the symbols. These are the names the RED tests
pin, so the GREEN implementer has one unambiguous target:

  ``app.utils.async_utils._BACKGROUND_TASKS`` : a set-like container
      Every task ``fire_and_forget`` creates is added to it, and the existing
      done-callback discards it again. Bounded by construction: a task leaves
      the set when it finishes. ``len()`` and iteration must work.

  ``app.main.DRAIN_TIMEOUT`` : float | int, seconds
      The bound on the drain. Read at CALL time (a module-global lookup inside
      the handler), so the tests can shorten it without a 8 s wall-clock wait.

  ``app.main._drain_background_tasks()`` : async, registered with
  ``@app.on_event("shutdown")`` AFTER ``_stop_loop_lag_heartbeat``
      Awaits ``asyncio.wait(pending, timeout=DRAIN_TIMEOUT)``. **Never
      ``gather``** -- one raising task must not stop the others from draining
      (``test_one_raising_task_does_not_prevent_the_others_from_draining``
      reproduces exactly that). A task that does not finish inside the bound is
      logged at WARNING **naming its label** and abandoned; the handler returns
      and the process still exits.

  ``railway.json`` / ``Procfile``
      Both start commands gain ``exec`` and ``--timeout-graceful-shutdown 20``,
      and stay byte-identical (W1-7's pin).
      ``railway.json`` gains ``deploy.drainingSeconds: 30``.

-------------------------------------------------------------------------------
THE THREE NUMBERS, AND WHY THEY ARE WHAT THEY ARE
-------------------------------------------------------------------------------
  30 s  ``railway.json`` ``deploy.drainingSeconds``  -- Railway's SIGTERM->SIGKILL
        window. Today the key is ABSENT on this service and
        ``RAILWAY_DEPLOYMENT_DRAINING_SECONDS`` is unset on both ``web`` and
        ``price-warmer``, so we run at an undocumented platform default. Setting
        it makes the window DETERMINISTIC instead of something a bounded drain
        has to fit under blind.
  20 s  ``--timeout-graceful-shutdown``  -- a cap on uvicorn's own REQUEST-drain
        phase, NOT on our handler (see the correction block below).
   8 s  ``app.main.DRAIN_TIMEOUT``  -- the bound on our lifespan drain.

Arithmetic, and it is load-bearing: **30 > 20 + 8**, with 2 s of margin. If the
request cap plus our drain ever exceeded the Railway window the container would
die mid-drain and we would be back to losing work, now with a false sense of
safety. ``test_the_shutdown_window_arithmetic_holds`` pins that inequality.

-------------------------------------------------------------------------------
WHAT ``--timeout-graceful-shutdown`` ACTUALLY BOUNDS -- MEASURED, and it is NOT
what the spec body first claimed
-------------------------------------------------------------------------------
Measured on the INSTALLED ``uvicorn 0.30.0`` (``uvicorn/server.py``)::

    await asyncio.wait_for(self._wait_tasks_to_complete(),
                           timeout=self.config.timeout_graceful_shutdown)

That bounds ``_wait_tasks_to_complete()`` -- uvicorn's OWN ``server_state.tasks``,
i.e. in-flight REQUEST handlers -- and the installed default is ``None`` =
UNBOUNDED. It never touches app-created background tasks, and lifespan shutdown
(where ``@app.on_event("shutdown")`` handlers run) happens AFTER that wait and is
not under this timeout at all.

So the flag is NOT what gives our drain a window: our handler already gets to run
under today's defaults and is bounded only by ``DRAIN_TIMEOUT``. The flag is worth
adding for a different reason -- with ``None``, ONE hung request handler blocks
shutdown forever, Railway eventually SIGKILLs, and then everything including our
drain is lost. A 20 s cap converts "hangs until killed" into "20 s, then proceed
to lifespan shutdown and our drain".

PINNED-VERSION GAP, same class as W1-7's: that default was read off the INSTALLED
``uvicorn 0.30.0`` while ``requirements.txt`` pins ``uvicorn==0.52.4``, and
installing is not permitted in this worktree. ``test_timeout_graceful_shutdown_
is_a_real_uvicorn_option_on_this_build`` therefore asserts the OPTION EXISTS on
whatever uvicorn is present, so CI settles it on the pinned build. A renamed
option in a boot-critical start command is a crash loop, not a lost feature.

-------------------------------------------------------------------------------
RAILWAY TEARDOWN -- MEASURED FROM REMOVED-DEPLOYMENT LOGS, NOT FROM THE DOCS
-------------------------------------------------------------------------------
The tail of two REMOVED deployments shows, in full::

    INFO:     Shutting down
    INFO:     Waiting for application shutdown.
    INFO:     Application shutdown complete.
    INFO:     Finished server process [1]
    Stopping Container

So graceful shutdown DOES run in production on every deploy (the earlier
"zero window / SIGKILL in the same instant" reading of the docs was withdrawn),
and **uvicorn IS PID 1** (``Finished server process [1]``). ``exec`` is therefore
NOT load-bearing -- it is kept because it is free, it is the form Railway's own
start-command doc uses (``/bin/sh -c "exec python main.py --port $PORT"``), and
it removes a dependency on shell behaviour that cannot be observed from this box.
The PR must not claim ``exec`` fixes anything.

What those logs do NOT prove: an IDLE shutdown is sub-second, so they show the
window is > 0 and say nothing about whether an 8 s drain survives it. That is
precisely why ``drainingSeconds`` is being set explicitly.

-------------------------------------------------------------------------------
SHELL EXPANSION OF THE NEW START COMMAND -- MEASURED THIS SESSION
-------------------------------------------------------------------------------
The proposed string was run through ``sh -c`` against an argv-printing stub on
PATH (GNU bash 5.2.37 msys), exactly as W1-7 proved its own form::

    CMD='exec uvicorn app.main:app --host 0.0.0.0 --port $PORT \
         --timeout-graceful-shutdown 20 \
         --limit-concurrency "${UVICORN_LIMIT_CONCURRENCY:-512}"'

    # UVICORN_LIMIT_CONCURRENCY unset, PORT=8080
    ARGV: [app.main:app] [--host] [0.0.0.0] [--port] [8080]
          [--timeout-graceful-shutdown] [20] [--limit-concurrency] [512]
    # UVICORN_LIMIT_CONCURRENCY=250   -> ... [--limit-concurrency] [250]
    # UVICORN_LIMIT_CONCURRENCY=      -> ... [--limit-concurrency] [512]
    # UVICORN_LIMIT_CONCURRENCY='1 --workers 4'
    #                                 -> ... [--limit-concurrency] [1 --workers 4]

``20`` arrives as its own argument and the W1-7 quoting still word-split-proofs
the concurrency value. The argv is byte-identical with and without the ``exec``
prefix, so ``exec`` costs nothing at the argument level. **Not measured, and not
claimed:** whether ``exec`` changes which process is PID 1 -- MSYS translates PIDs
through an intermediate, so the PID readings from this box are meaningless and
are deliberately not reported as evidence. The Railway log above already settles
it: uvicorn is PID 1 today.

-------------------------------------------------------------------------------
HONEST LIMIT (carry into the PR)
-------------------------------------------------------------------------------
This drains on a GRACEFUL shutdown (SIGTERM). A SIGKILL or an OOM kill drains
nothing, and ``restartPolicyType: ON_FAILURE`` implies those happen. The refund is
best-effort by design; this unit makes it survive the common case (a deploy), not
every case. The on-deploy verification is our drain's own log lines appearing
BETWEEN ``Waiting for application shutdown.`` and ``Application shutdown
complete.`` -- uvicorn's own lines already appear, so their presence proves
nothing new.

-------------------------------------------------------------------------------
Expected state at RED
-------------------------------------------------------------------------------
  * test_a_yielding_task_completes_during_the_drain            -- RED (no handler)
  * test_a_task_that_never_finishes_is_abandoned_and_logged    -- RED (no handler)
  * test_one_raising_task_does_not_prevent_the_others_from_draining -- RED
  * test_the_task_registry_does_not_grow                       -- RED (no registry)
  * test_refund_survives_a_shutdown_that_races_the_offloaded_refund -- RED  <-- THE FINDING
  * test_drain_handler_is_registered_after_the_heartbeat_cancel -- RED
  * test_railway_start_command_declares_timeout_graceful_shutdown  -- RED
  * test_procfile_start_command_declares_timeout_graceful_shutdown -- RED
  * test_graceful_shutdown_value_is_the_pinned_number           -- RED
  * test_both_start_commands_begin_with_exec                    -- RED
  * test_railway_json_declares_a_positive_draining_seconds       -- RED
  * test_the_shutdown_window_arithmetic_holds                    -- RED
  * test_start_commands_are_byte_identical              -- GREEN, REGRESSION PIN
  * test_timeout_graceful_shutdown_is_a_real_uvicorn_option_on_this_build
                                                        -- GREEN, BOOT PIN
  * test_fire_and_forget_still_returns_the_task_and_logs_failures
                                                        -- GREEN, PRESERVATION PIN

Every RED node fails on an ASSERTION about behaviour that is genuinely absent, or
on an explicit ``pytest.fail`` from ``_require`` naming the missing contract --
never on a bare ``AttributeError``/``ImportError``.

-------------------------------------------------------------------------------
MUTATION MATRIX -- MEASURED IN THE RED PHASE, NOT PREDICTED
-------------------------------------------------------------------------------
A previous version of this unit shipped a suite that stayed GREEN with the drain
handler deleted, so the mutations were RUN here rather than reasoned about. Each
was executed by injecting a prototype implementation into the already-imported
modules from a throwaway pytest plugin (no repo file was modified), then running
this file. Results, code-side nodes only (the 8 config-file nodes stay RED in
every row because a plugin cannot edit ``railway.json``/``Procfile``):

  correct implementation ....... all 9 code-side nodes GREEN
  handler body replaced by
  ``pass`` (the "green with the
  handler deleted" failure mode)  RED: _a_yielding_task_completes,
                                       _abandoned_and_logged,
                                       _does_not_prevent_the_others,
                                       _refund_survives_a_shutdown  <-- THE FINDING
  ``gather(*pending)`` .......... RED: _does_not_prevent_the_others (the task's
                                  RuntimeError escapes the shutdown handler),
                                  _abandoned_and_logged (gather is unbounded)
  ``gather(..., return_exceptions
  =True)`` ...................... RED: _abandoned_and_logged (still unbounded)
  ``asyncio.wait`` with the
  timeout dropped ............... RED: _abandoned_and_logged -- and it FAILS in
                                  6 s rather than hanging the suite, because the
                                  test wraps the handler in its own ``wait_for``
  registry ``add`` removed from
  ``fire_and_forget`` ........... RED: all four drain nodes + _registry_does_not_grow
"""
import asyncio
import inspect
import json
import logging
import time
from pathlib import Path

import pytest

import app.main as app_main
from app.utils import async_utils

# ---------------------------------------------------------------------------
# Contract helpers
# ---------------------------------------------------------------------------

_CONTRACT = (
    "W1-6 contract:\n"
    "  app.utils.async_utils._BACKGROUND_TASKS  -- set of in-flight tasks;\n"
    "      fire_and_forget adds, the done-callback discards.\n"
    "  app.main.DRAIN_TIMEOUT                   -- seconds, read at call time.\n"
    "  app.main._drain_background_tasks()       -- async @app.on_event('shutdown'),\n"
    "      registered AFTER _stop_loop_lag_heartbeat, awaits\n"
    "      asyncio.wait(pending, timeout=DRAIN_TIMEOUT) (never gather), logs a\n"
    "      WARNING naming the label of anything it abandons, and returns."
)

_GRACEFUL_SHUTDOWN_SECONDS = 20
_DRAINING_SECONDS = 30

_REPO_ROOT = Path(__file__).resolve().parents[1]
_RAILWAY_JSON = _REPO_ROOT / "railway.json"
_PROCFILE = _REPO_ROOT / "Procfile"


def _require_main(name: str):
    """Fetch ``app.main.<name>`` or fail with the contract, never AttributeError."""
    value = getattr(app_main, name, None)
    if value is None:
        pytest.fail(
            f"app.main has no {name!r} -- the shutdown drain is not implemented.\n"
            f"{_CONTRACT}"
        )
    return value


def _require_registry():
    """Fetch the fire-and-forget task registry or fail with the contract."""
    registry = getattr(async_utils, "_BACKGROUND_TASKS", None)
    if registry is None:
        pytest.fail(
            "app.utils.async_utils has no _BACKGROUND_TASKS -- fire_and_forget "
            "tracks nothing, so a shutdown drain has nothing to drain.\n"
            f"{_CONTRACT}"
        )
    return registry


def _drain_handler():
    handler = _require_main("_drain_background_tasks")
    if not inspect.iscoroutinefunction(handler):
        pytest.fail(
            "app.main._drain_background_tasks must be a coroutine function "
            f"(an async shutdown handler); got {handler!r}"
        )
    return handler


async def _run_drain(bound: float):
    """Run the drain handler under an OUTER bound.

    The outer ``wait_for`` is deliberate: if the implementation drops
    ``timeout=DRAIN_TIMEOUT`` the drain becomes unbounded, and a test that simply
    awaited it would HANG the suite instead of reddening. This converts that
    mutation into a clean, named failure.
    """
    handler = _drain_handler()
    try:
        await asyncio.wait_for(handler(), timeout=bound)
    except asyncio.TimeoutError:
        pytest.fail(
            f"_drain_background_tasks did not return within {bound}s. The drain "
            "must be BOUNDED by DRAIN_TIMEOUT -- a task that will not finish is "
            "logged by label and ABANDONED, and the process still exits."
        )


@pytest.fixture(autouse=True)
def _isolate_task_registry():
    """Keep each test's tasks out of every other test's drain.

    The registry is module-level shared state. Snapshot it, hand each test an
    empty one, then cancel whatever the test left behind and restore. Without
    this, one test's hung task would be drained (and time out) inside another's.
    """
    registry = getattr(async_utils, "_BACKGROUND_TASKS", None)
    if registry is None:
        yield
        return
    saved = set(registry)
    registry.clear()
    try:
        yield
    finally:
        leftovers = set(registry)
        registry.clear()
        for task in leftovers:
            if not task.done():
                task.cancel()
        registry.update(saved)


# ---------------------------------------------------------------------------
# 1 -- a yielding fire-and-forget task completes during the drain
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_a_yielding_task_completes_during_the_drain():
    """The core promise: a task that is mid-``await`` at shutdown still finishes.

    RED today: nothing tracks the task and no handler awaits it, so shutdown
    drops it mid-flight and the side effect is never observed.
    """
    _require_registry()
    observed = []

    async def _slow_side_effect() -> None:
        await asyncio.sleep(0.1)
        observed.append("done")

    async_utils.fire_and_forget(_slow_side_effect(), label="w16.slow")

    # Let the task actually START and reach its await point, so the drain is
    # racing a genuinely in-flight task rather than one that never began.
    await asyncio.sleep(0)
    assert not observed, "precondition: the side effect must not have run yet"

    await _run_drain(bound=5.0)

    assert observed == ["done"], (
        "a fire-and-forget task that was mid-await at shutdown did NOT complete "
        "during the drain -- its side effect was lost. This is exactly how an "
        "offloaded refund evaporates on a deploy."
    )


# ---------------------------------------------------------------------------
# 2 -- a task that never finishes is abandoned, by label, inside the bound
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_a_task_that_never_finishes_is_abandoned_and_logged(monkeypatch, caplog):
    """Bounded, not best-effort-forever. The process MUST still exit.

    Pins three things at once: the handler returns inside ``DRAIN_TIMEOUT``, the
    abandoned task is named by its LABEL in a WARNING (a nameless "1 task did not
    finish" line is not actionable at 3am), and the task is left pending rather
    than awaited to completion.

    ``DRAIN_TIMEOUT`` is shortened via monkeypatch, which requires the handler to
    read it as a module global at CALL time -- part of the pinned contract.

    RED today: no handler at all.
    """
    _require_registry()
    _require_main("DRAIN_TIMEOUT")
    monkeypatch.setattr(app_main, "DRAIN_TIMEOUT", 0.2, raising=False)

    async def _never_finishes() -> None:
        await asyncio.sleep(3600)

    task = async_utils.fire_and_forget(_never_finishes(), label="w16.hung_label")
    await asyncio.sleep(0)

    try:
        with caplog.at_level(logging.WARNING):
            started = time.monotonic()
            await _run_drain(bound=5.0)
            elapsed = time.monotonic() - started

        assert elapsed < 2.0, (
            f"the drain took {elapsed:.2f}s with DRAIN_TIMEOUT=0.2 -- it is not "
            "bounded by DRAIN_TIMEOUT. An unbounded drain turns a deploy into a "
            "hang that Railway ends with SIGKILL, losing everything."
        )
        assert not task.done(), (
            "the hung task finished during the drain, so this test proved "
            "nothing about abandonment"
        )
        assert "w16.hung_label" in caplog.text, (
            "the drain abandoned a task without naming its LABEL at WARNING. "
            "Abandonment must be attributable to a call site.\n"
            f"captured log:\n{caplog.text}"
        )
    finally:
        task.cancel()


# ---------------------------------------------------------------------------
# 2b -- the drain ABANDONS a hung task; it never cancels it
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_the_drain_abandons_a_hung_task_without_cancelling_it(monkeypatch):
    """Abandon, not cancel. Adversary (2026-09-11): the sibling test asserts
    ``not task.done()`` SYNCHRONOUSLY, before a cancellation would be processed,
    so a drain that called ``task.cancel()`` on the stragglers stayed green.

    Cancelling would turn a slow refund that WOULD have landed (uvicorn's own
    request-task wait has already passed, and the loop keeps running until the
    process exits) into a guaranteed loss. This yields to the loop twice after
    the drain returns and then checks that no cancellation was requested.

    MUTATION: ``task.cancel()`` on each abandoned task -> red."""
    _require_registry()
    _require_main("DRAIN_TIMEOUT")
    monkeypatch.setattr(app_main, "DRAIN_TIMEOUT", 0.2, raising=False)

    async def _never_finishes() -> None:
        await asyncio.sleep(3600)

    task = async_utils.fire_and_forget(_never_finishes(), label="w16.hung_not_cancelled")
    await asyncio.sleep(0)

    try:
        await _run_drain(bound=5.0)
        # Let any cancel() the drain might have requested be delivered.
        await asyncio.sleep(0)
        await asyncio.sleep(0)

        assert not task.cancelling(), (
            "the drain requested cancellation of an abandoned task; the contract "
            "is ABANDON (log by label, leave it pending), never cancel"
        )
        assert not task.cancelled() and not task.done(), (
            "the abandoned task was cancelled/finished by the drain; it must be "
            "left pending so a slow refund can still land before the process exits"
        )
    finally:
        task.cancel()


# ---------------------------------------------------------------------------
# 2c -- a CANCELLED task still leaves the registry (discard FIRST)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_a_cancelled_task_is_still_discarded_from_the_registry():
    """The done-callback discards BEFORE its ``if t.cancelled(): return``.

    Adversary (2026-09-11): the ordering claim in ``async_utils`` was unpinned --
    moving the discard below the early return left every test green. A task
    cancelled at shutdown (or by a future caller) would then stay in the set
    forever and be re-offered to every later drain as a phantom.

    MUTATION: move ``_BACKGROUND_TASKS.discard(t)`` after the cancelled early
    return -> red."""
    _require_registry()
    registry = async_utils._BACKGROUND_TASKS

    async def _never_finishes() -> None:
        await asyncio.sleep(3600)

    task = async_utils.fire_and_forget(_never_finishes(), label="w16.cancelled")
    await asyncio.sleep(0)
    assert task in registry, "precondition: an in-flight task is registered"

    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    # Done-callbacks run via call_soon; give the loop one tick to deliver it.
    await asyncio.sleep(0)

    assert task.cancelled(), "precondition: the task was cancelled"
    assert task not in registry, (
        "a cancelled task stayed in _BACKGROUND_TASKS -- the discard must run "
        "BEFORE the cancelled early-return in the done-callback"
    )


# ---------------------------------------------------------------------------
# 3 -- one raising task must not stop the others (wait, never gather)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_one_raising_task_does_not_prevent_the_others_from_draining():
    """``asyncio.wait``, never ``gather``.

    ``gather`` (without ``return_exceptions=True``) propagates the FIRST
    exception immediately, so the handler returns while its slower siblings are
    still mid-await -- and at shutdown that means they are dropped. This test
    reproduces exactly that: the raiser fails fast, the two slow tasks need
    100 ms, and both of their side effects must still be observed.

    It also pins that the handler itself does NOT raise: an exception escaping a
    lifespan shutdown handler is a failed shutdown.

    RED today: no handler.
    """
    _require_registry()
    observed = []

    async def _raiser() -> None:
        await asyncio.sleep(0)
        raise RuntimeError("w16 deliberate failure inside a drained task")

    async def _slow(tag: str) -> None:
        await asyncio.sleep(0.1)
        observed.append(tag)

    async_utils.fire_and_forget(_raiser(), label="w16.raiser")
    async_utils.fire_and_forget(_slow("a"), label="w16.slow_a")
    async_utils.fire_and_forget(_slow("b"), label="w16.slow_b")
    await asyncio.sleep(0)

    await _run_drain(bound=5.0)

    assert sorted(observed) == ["a", "b"], (
        "one raising background task prevented the others from being drained -- "
        "the drain must use asyncio.wait (which never propagates a task's "
        "exception) and never gather. observed="
        f"{observed!r}"
    )


# ---------------------------------------------------------------------------
# 4 -- the registry is bounded by construction
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_the_task_registry_does_not_grow():
    """A task leaves the set when it finishes -- so the set cannot leak.

    Tracking tasks to drain them is only safe if the tracking is self-cleaning:
    a set that only ever grows is a memory leak on a long-lived worker that fires
    one of these per compare.

    RED today: there is no registry at all.
    """
    registry = _require_registry()
    assert len(registry) == 0, "fixture precondition: the registry starts empty"

    async def _quick(n: int) -> None:
        await asyncio.sleep(0)

    tasks = [async_utils.fire_and_forget(_quick(i), label=f"w16.quick.{i}") for i in range(25)]
    assert len(registry) == 25, (
        "fire_and_forget did not add every task to _BACKGROUND_TASKS; a task it "
        f"does not track cannot be drained. len={len(registry)!r}"
    )

    await asyncio.gather(*tasks)
    # done-callbacks are scheduled with call_soon; give the loop a few turns.
    for _ in range(10):
        if not registry:
            break
        await asyncio.sleep(0)

    assert len(registry) == 0, (
        "the task registry did not shrink back to empty after every task "
        "completed -- the done-callback must discard the task, or this set is an "
        f"unbounded leak. leftover={registry!r}"
    )


# ---------------------------------------------------------------------------
# 4b -- the COMMON shutdown: nothing in flight (added in the GREEN phase)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_the_drain_is_a_no_op_when_nothing_is_in_flight():
    """An idle worker draining an EMPTY registry must return quietly.

    Added during the GREEN phase because the implementation's empty-set guard
    was a real fix that no node pinned. MEASURED on python 3.12.9:
    ``asyncio.wait(set())`` raises ``ValueError: Set of Tasks/Futures is
    empty.`` -- so a drain that skipped the guard would raise out of the
    lifespan handler on EVERY ordinary shutdown ("Application shutdown failed"
    on every deploy), in exchange for a unit whose whole promise is that it only
    ever waits LONGER, never breaks anything. The overwhelmingly common shutdown
    has nothing in flight, so this is the path that runs almost every time.
    """
    registry = _require_registry()
    assert len(registry) == 0, "fixture precondition: the registry starts empty"

    await _run_drain(bound=5.0)


# ---------------------------------------------------------------------------
# 5 -- THE FINDING: the offloaded refund survives a shutdown
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_refund_survives_a_shutdown_that_races_the_offloaded_refund(monkeypatch):
    """THE finding, executed end to end through the production symbols.

    ``ENABLE_ASYNC_REDIS_OFFLOAD`` ON (patched at the symbol ``usage_service``
    actually calls) makes ``refund_comparison_credit`` await
    ``asyncio.to_thread(_refund_credit_sync, ...)`` -- a real suspension point.
    The refund is dispatched through the same ``fire_and_forget`` the compare
    routes use, and then a shutdown happens immediately. Without a drain the task
    is dropped mid-``to_thread`` and the credit the user paid for a failed
    comparison is never returned.

    The blocking body sleeps 150 ms deliberately: it must NOT be able to finish
    inside the handful of event-loop turns a no-op handler would cost, so
    deleting the drain handler -- or replacing its body with ``pass`` -- turns
    this test RED rather than leaving it accidentally green.

    RED today: no drain handler exists.
    """
    from app.services import usage_service

    _require_registry()
    recorded = []

    def _slow_refund_sync(counter_id, consumed_keys=None):
        # Blocking on purpose: this is what runs inside asyncio.to_thread.
        time.sleep(0.15)
        recorded.append(counter_id)

    monkeypatch.setattr(usage_service, "_redis_offload_enabled", lambda: True)
    monkeypatch.setattr(usage_service, "_refund_credit_sync", _slow_refund_sync)

    async_utils.fire_and_forget(
        usage_service.refund_comparison_credit("user-w16"),
        label="usage_refund.text.post",
    )
    # Let the task start and hand its blocking body to the thread pool.
    await asyncio.sleep(0)
    await asyncio.sleep(0)
    assert not recorded, (
        "precondition: the offloaded refund must still be in flight when the "
        "shutdown starts -- otherwise this test proves nothing"
    )

    await _run_drain(bound=5.0)

    assert recorded == ["user-w16"], (
        "the offloaded refund was LOST at shutdown. With "
        "ENABLE_ASYNC_REDIS_OFFLOAD ON, refund_comparison_credit yields at "
        "asyncio.to_thread; an untracked task mid-await is dropped when the loop "
        "stops, so the user is charged a credit for a comparison that failed. "
        "This is LS-FAILURE-MODES-COST-05 and the reason the offload flag must "
        f"not be canaried before this unit ships. recorded={recorded!r}"
    )


# ---------------------------------------------------------------------------
# 6 -- ordering: the drain runs AFTER the heartbeat cancel
# ---------------------------------------------------------------------------


def _registered_shutdown_handler_names():
    """Names of the app's shutdown handlers, in registration order.

    Duck-typed on purpose. This repo runs a different fastapi/starlette locally
    (0.115.0 / 0.38.6) than ``requirements.txt`` pins for CI and Railway
    (0.141.1 / 1.6.0), so framework introspection must not assume a shape --
    see CLAUDE.md and ``tests/_route_introspection.py``. When ``on_shutdown`` is
    not exposed we fall back to the definition order of the
    ``@app.on_event("shutdown")``-decorated functions in ``app/main.py``, which
    is what registration order follows.
    """
    handlers = getattr(app_main.app.router, "on_shutdown", None)
    if handlers:
        return [getattr(f, "__name__", repr(f)) for f in handlers]

    source = (_REPO_ROOT / "app" / "main.py").read_text(encoding="utf-8")
    names = []
    lines = source.splitlines()
    for index, line in enumerate(lines):
        if 'on_event("shutdown")' not in line and "on_event('shutdown')" not in line:
            continue
        for following in lines[index + 1 : index + 5]:
            stripped = following.strip()
            if stripped.startswith("async def ") or stripped.startswith("def "):
                names.append(stripped.split("def ", 1)[1].split("(", 1)[0].strip())
                break
    return names


def test_drain_handler_is_registered_after_the_heartbeat_cancel():
    """Order matters: cancel the heartbeat FIRST, then drain.

    W1-10's heartbeat is an infinite ``while True: await asyncio.sleep(1)`` loop.
    It is not a ``fire_and_forget`` task so it is not in the registry, but the
    ordering is still the honest one: shutdown stops the things that never end
    before it waits on the things that do. Draining first would, at best, waste
    the window; at worst a future registry-tracked periodic task would consume
    the whole of ``DRAIN_TIMEOUT`` and starve the refund this unit exists for.

    RED today: ``_drain_background_tasks`` is not registered at all.
    """
    names = _registered_shutdown_handler_names()
    assert names, "could not determine the app's shutdown handlers"
    assert "_stop_loop_lag_heartbeat" in names, (
        "W1-10's heartbeat-cancel shutdown handler is missing from "
        f"app/main.py; got {names!r}"
    )
    assert "_drain_background_tasks" in names, (
        "no _drain_background_tasks shutdown handler is registered, so nothing "
        f"drains the fire-and-forget tasks. registered={names!r}\n{_CONTRACT}"
    )
    assert names.index("_drain_background_tasks") > names.index("_stop_loop_lag_heartbeat"), (
        "the drain handler must run AFTER the W1-10 heartbeat cancel, so the "
        f"drain does not wait on a task that never ends. registered={names!r}"
    )


# ---------------------------------------------------------------------------
# 7 -- the two start commands
# ---------------------------------------------------------------------------


def _railway_deploy() -> dict:
    assert _RAILWAY_JSON.is_file(), f"missing {_RAILWAY_JSON}"
    config = json.loads(_RAILWAY_JSON.read_text(encoding="utf-8"))
    deploy = config.get("deploy")
    assert isinstance(deploy, dict), "railway.json has no 'deploy' object"
    return deploy


def _railway_start_command() -> str:
    command = _railway_deploy().get("startCommand")
    assert isinstance(command, str) and command.strip(), (
        "railway.json deploy.startCommand is missing or not a string -- Railway "
        "boots from this string"
    )
    return command.strip()


def _procfile_web_command() -> str:
    assert _PROCFILE.is_file(), f"missing {_PROCFILE}"
    for raw_line in _PROCFILE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line.startswith("web:"):
            return line.split(":", 1)[1].strip()
    pytest.fail("Procfile declares no 'web:' process type")


def _flag_value(command: str, flag: str):
    tokens = command.split()
    for index, token in enumerate(tokens):
        if token == flag:
            if index + 1 >= len(tokens):
                pytest.fail(f"{flag} present in {command!r} with no value after it")
            return tokens[index + 1]
        if token.startswith(f"{flag}="):
            return token.split("=", 1)[1]
    return None


_START_COMMAND_SOURCES = [
    ("railway.json", _railway_start_command),
    ("Procfile", _procfile_web_command),
]


def test_railway_start_command_declares_timeout_graceful_shutdown():
    """RED today: the shipped startCommand carries no graceful-shutdown cap, so
    uvicorn's request-drain phase is UNBOUNDED (installed default ``None``) and
    one hung request handler blocks shutdown until Railway SIGKILLs -- taking our
    drain with it."""
    command = _railway_start_command()
    assert "--timeout-graceful-shutdown" in command, (
        "railway.json deploy.startCommand declares no --timeout-graceful-shutdown; "
        f"got {command!r}"
    )


def test_procfile_start_command_declares_timeout_graceful_shutdown():
    """RED today: same unbounded string as railway.json."""
    command = _procfile_web_command()
    assert "--timeout-graceful-shutdown" in command, (
        f"Procfile web: command declares no --timeout-graceful-shutdown; got {command!r}"
    )


@pytest.mark.parametrize("source, reader", _START_COMMAND_SOURCES)
def test_graceful_shutdown_value_is_the_pinned_number(source, reader):
    """20 s, and the number is pinned because the window arithmetic depends on it.

    It bounds uvicorn's REQUEST drain, not our handler (see the module docstring):
    it converts "hangs until killed" into "20 s, then lifespan shutdown runs".
    """
    value = _flag_value(reader(), "--timeout-graceful-shutdown")
    assert value is not None, (
        f"{source} start command carries no --timeout-graceful-shutdown value"
    )
    assert value == str(_GRACEFUL_SHUTDOWN_SECONDS), (
        f"{source} --timeout-graceful-shutdown is {value!r}, expected "
        f"{str(_GRACEFUL_SHUTDOWN_SECONDS)!r}: the 30 > 20 + 8 window arithmetic "
        "is pinned by test_the_shutdown_window_arithmetic_holds"
    )


@pytest.mark.parametrize("source, reader", _START_COMMAND_SOURCES)
def test_both_start_commands_begin_with_exec(source, reader):
    """``exec`` -- free, documented by Railway, and NOT load-bearing.

    Railway's start-command doc gives the shell-wrapped form as
    ``/bin/sh -c "exec python main.py --port $PORT"``, and its Node
    troubleshooting page explains why: a wrapper left as the main process can
    swallow the signal, and "the service will eventually be force quit".

    Our command runs through a shell because of W1-7's ``"${UVICORN_LIMIT_
    CONCURRENCY:-512}"`` expansion. MEASURED from a removed deployment's log,
    uvicorn is ALREADY PID 1 (``Finished server process [1]``), so this does not
    fix a live defect and the PR must not claim it does. It is adopted because it
    costs nothing (argv is byte-identical with and without it, measured through
    ``sh -c``) and removes a dependency on Nix-image shell behaviour that cannot
    be observed from here. This test exists so nobody drops it while tidying.
    """
    command = reader()
    assert command.startswith("exec "), (
        f"{source} start command does not begin with 'exec '; got {command!r}"
    )
    assert command.split()[1] == "uvicorn", (
        f"{source} start command must be 'exec uvicorn ...'; got {command!r}"
    )


def test_start_commands_are_byte_identical():
    """REGRESSION PIN -- GREEN TODAY and must stay green (W1-7's durable half).

    Railway boots from ``railway.json``'s ``startCommand``, so a Procfile-only
    edit looks applied and does nothing. This unit edits both files, which is
    exactly the window in which they drift.
    """
    railway = _railway_start_command()
    procfile = _procfile_web_command()
    assert railway == procfile, (
        "railway.json deploy.startCommand and the Procfile web: command have "
        "DRIFTED. Railway boots from railway.json, so a Procfile-only edit is a "
        f"silent no-op.\n  railway.json: {railway!r}\n  Procfile:     {procfile!r}"
    )


def test_timeout_graceful_shutdown_is_a_real_uvicorn_option_on_this_build():
    """BOOT PIN -- the start command is boot-critical.

    ``requirements.txt`` pins ``uvicorn==0.52.4``, which is what CI and Railway
    install; only ``0.30.0`` is installed in this worktree and installing is not
    permitted here, so the default-value measurement in the module docstring was
    taken on a build that is NOT the deployed one. If the option were renamed on
    the pinned build, uvicorn would exit on an unrecognised argument and the
    container would CRASH-LOOP -- strictly worse than the unbounded request drain
    this flag exists to cap. Asserting against whatever uvicorn is present lets
    CI settle it on the pinned build instead of Railway discovering it at boot.
    """
    import uvicorn
    import uvicorn.config

    params = inspect.signature(uvicorn.config.Config.__init__).parameters
    assert "timeout_graceful_shutdown" in params, (
        f"uvicorn {getattr(uvicorn, '__version__', '?')} has no "
        "timeout_graceful_shutdown option, but both start commands pass "
        "--timeout-graceful-shutdown. The container would fail to boot."
    )


# ---------------------------------------------------------------------------
# 8 -- the Railway teardown window, and the arithmetic over all three numbers
# ---------------------------------------------------------------------------


def test_railway_json_declares_a_positive_draining_seconds():
    """RED today: ``deploy.drainingSeconds`` is absent.

    Railway sends SIGTERM, allows a draining window, then SIGKILLs. The window is
    ``RAILWAY_DEPLOYMENT_DRAINING_SECONDS`` or ``deploy.drainingSeconds`` --
    neither is set on this service, so we run at an undocumented platform default.
    Removed-deployment logs prove that default is > 0 (a full graceful shutdown
    completes), but an IDLE shutdown is sub-second and proves nothing about
    whether an 8 s drain fits. Setting it makes the window DETERMINISTIC.

    This is also the pin that stops someone tidying the window away and silently
    re-losing every deploy's in-flight work.

    NOTE for the PR: config-as-code is deprecated by Railway but honoured until
    2026-12-01; the migration to Infrastructure-as-Code must carry this key.
    """
    deploy = _railway_deploy()
    assert "drainingSeconds" in deploy, (
        "railway.json deploy has no 'drainingSeconds'. Without it the "
        "SIGTERM->SIGKILL window is an undocumented platform default that a "
        f"bounded drain has to fit under blind. keys={sorted(deploy)!r}"
    )
    value = deploy["drainingSeconds"]
    assert isinstance(value, int) and not isinstance(value, bool), (
        f"deploy.drainingSeconds must be an integer number of seconds; got {value!r}"
    )
    assert value > 0, f"deploy.drainingSeconds must be positive; got {value!r}"
    assert value == _DRAINING_SECONDS, (
        f"deploy.drainingSeconds is {value!r}, expected {_DRAINING_SECONDS} -- "
        "the pinned window the 30 > 20 + 8 arithmetic is built on"
    )


def test_the_shutdown_window_arithmetic_holds():
    """**30 s (Railway) > 20 s (uvicorn request cap) + 8 s (our drain).**

    This is the whole point of shipping the three changes together. If the
    request cap plus our drain ever exceeded the Railway window the container
    would be SIGKILLed mid-drain and we would be losing work again -- now behind
    a false sense of safety.

    The second assertion (``DRAIN_TIMEOUT < --timeout-graceful-shutdown``) is
    recorded honestly as NOT NECESSARY: measured on the installed uvicorn, the
    two bound DIFFERENT phases that run sequentially (uvicorn's request drain,
    then lifespan shutdown), so the spec's own correction retracted the
    "DRAIN_TIMEOUT must be less, with margin" constraint. It is asserted anyway
    because the adopted numbers satisfy it comfortably (8 < 20) and it is a cheap
    guard against a future DRAIN_TIMEOUT being raised past the point where the
    total no longer fits the Railway window.

    RED today: neither DRAIN_TIMEOUT nor drainingSeconds nor the flag exists.
    """
    drain_timeout = _require_main("DRAIN_TIMEOUT")
    assert isinstance(drain_timeout, (int, float)) and not isinstance(drain_timeout, bool), (
        f"app.main.DRAIN_TIMEOUT must be a number of seconds; got {drain_timeout!r}"
    )
    assert drain_timeout > 0, f"DRAIN_TIMEOUT must be positive; got {drain_timeout!r}"

    deploy = _railway_deploy()
    draining = deploy.get("drainingSeconds")
    assert isinstance(draining, int) and not isinstance(draining, bool), (
        "railway.json deploy.drainingSeconds is missing or not an integer, so "
        f"the shutdown window arithmetic cannot be checked. got {draining!r}"
    )

    graceful_raw = _flag_value(_railway_start_command(), "--timeout-graceful-shutdown")
    assert graceful_raw is not None, (
        "railway.json start command carries no --timeout-graceful-shutdown value"
    )
    graceful = int(graceful_raw)

    assert draining > graceful + drain_timeout, (
        f"the shutdown window does not fit: Railway drainingSeconds={draining} is "
        f"NOT greater than uvicorn --timeout-graceful-shutdown={graceful} plus "
        f"DRAIN_TIMEOUT={drain_timeout}. The container would be SIGKILLed "
        "mid-drain and in-flight refunds would be lost anyway."
    )
    assert drain_timeout < graceful, (
        f"DRAIN_TIMEOUT={drain_timeout} is not comfortably under the uvicorn "
        f"request cap {graceful}. (Not strictly required -- the two bound "
        "different, sequential phases -- but a DRAIN_TIMEOUT that large is a "
        "sign the total no longer fits the Railway window.)"
    )


# ---------------------------------------------------------------------------
# 9 -- preservation pin: fire_and_forget keeps its existing contract
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fire_and_forget_still_returns_the_task_and_logs_failures(caplog):
    """PRESERVATION PIN -- GREEN TODAY and must stay green.

    W1-6 adds tracking to ``fire_and_forget``; it must not change what the helper
    already guarantees. The audit-2026-05-22 reason the helper exists at all is
    the done-callback that surfaces a background exception as a WARNING naming
    the label -- registry bookkeeping must not swallow it, and the task must
    still be returned to the caller.
    """
    async def _boom() -> None:
        raise ValueError("w16 preservation probe")

    with caplog.at_level(logging.WARNING):
        task = async_utils.fire_and_forget(_boom(), label="w16.preservation")
        assert isinstance(task, asyncio.Task), (
            f"fire_and_forget must return the asyncio.Task; got {task!r}"
        )
        with pytest.raises(ValueError):
            await task
        for _ in range(10):
            if "w16.preservation" in caplog.text:
                break
            await asyncio.sleep(0)

    assert "w16.preservation" in caplog.text, (
        "fire_and_forget stopped logging a background task's exception with its "
        f"label. captured log:\n{caplog.text}"
    )
