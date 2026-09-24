"""Retro-fix R-MAIN / W1-7b + W1-10b -- RED phase.

Spec: the retroactive adversary report on W1-7 + W1-10 (PR #144,
``--limit-concurrency`` + ``/health`` loop lag), defects 1-3, plus the
orchestrator's binding rulings for this group:

  W1-7b / W1-10b (tests):  the loop-lag pins become NON-VACUOUS --
      * a synthetic tick recorded through ``record_loop_lag_tick`` is read back
        THROUGH ``GET /health`` without the heartbeat running to overwrite it
        (kills mutant A: ``/health`` returning literal 0.0/0.0);
      * the heartbeat records ``now - previous`` -- the MEASURED elapsed time,
        not the interval (kills mutant B: constant ``LOOP_LAG_INTERVAL_SECONDS``)
        and advances ``previous`` every tick (kills mutant C: accumulating
        elapsed);
      * the shutdown handler is REGISTERED, not only callable (kills mutant D:
        ``@app.on_event("shutdown")`` removed -- the portal's teardown cancels
        the task anyway, so the old ``done() or cancelling`` check survived).
      These are PINS: the code on main is correct today, and they pass today.
      Each was mutation-checked against A/B/C/D (see the RED-phase report).

  W1-10b (app/main.py, ADDITIVE KEYS ONLY): ``loop_lag_max_ms`` is a
      high-water mark since process start that never decays -- measured: after
      an 11 s stall, 3,600 healthy ticks and a NEW 4 s stall, ``/health`` reads
      ``{loop_lag_ms: 0.0, loop_lag_max_ms: 11000.0}`` and the new stall is
      invisible. Add ``loop_lag_max_60s_ms``: the max over a 60-slot ring of
      per-tick lag samples, so a new stall after an old high-water mark is
      visible. ``/health`` stays a dict read; ``status``, ``message``,
      ``loop_lag_ms`` and ``loop_lag_max_ms`` keep their exact meaning.

The recorder is process-global state, so an autouse fixture snapshots every
``app.main._loop_lag*`` global (except the task handle) and restores it after
each test -- these tests push the high-water mark to 11 s and must not leak
that into any other file.

Zero network: an autouse guard blocks every non-loopback ``connect`` and
``getaddrinfo`` and fails the test on any attempt.
"""
from __future__ import annotations

import asyncio
import copy
import ipaddress
import numbers
import socket
import types

import pytest
from fastapi.testclient import TestClient

import app.main as app_main
from app.main import app

INTERVAL = float(app_main.LOOP_LAG_INTERVAL_SECONDS)
RING_SLOTS = 60
NEW_KEY = "loop_lag_max_60s_ms"


# ---------------------------------------------------------------------------
# Zero-network guard (autouse)
# ---------------------------------------------------------------------------

_LOOPBACK_NAMES = {"localhost", "testserver", "", None}


def _is_loopback(host) -> bool:
    if isinstance(host, (bytes, bytearray)):
        host = bytes(host).decode("latin-1")
    if host in _LOOPBACK_NAMES:
        return True
    try:
        return ipaddress.ip_address(str(host).split("%", 1)[0]).is_loopback
    except ValueError:
        return False


@pytest.fixture(autouse=True)
def _zero_network(monkeypatch):
    attempts: list = []
    real_connect = socket.socket.connect
    real_connect_ex = socket.socket.connect_ex
    real_gai = socket.getaddrinfo

    def _host(addr):
        return addr[0] if isinstance(addr, tuple) else addr

    def guarded_connect(self, addr):
        if not _is_loopback(_host(addr)):
            attempts.append(("connect", repr(addr)))
            raise OSError(f"zero-network guard: blocked connect to {addr!r}")
        return real_connect(self, addr)

    def guarded_connect_ex(self, addr):
        if not _is_loopback(_host(addr)):
            attempts.append(("connect_ex", repr(addr)))
            raise OSError(f"zero-network guard: blocked connect_ex to {addr!r}")
        return real_connect_ex(self, addr)

    def guarded_gai(host, *args, **kwargs):
        if not _is_loopback(host):
            attempts.append(("getaddrinfo", repr(host)))
            raise OSError(f"zero-network guard: blocked getaddrinfo({host!r})")
        return real_gai(host, *args, **kwargs)

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", guarded_connect_ex)
    monkeypatch.setattr(socket, "getaddrinfo", guarded_gai)
    yield
    assert not attempts, f"test attempted network access: {attempts}"


@pytest.fixture(autouse=True)
def _restore_loop_lag_state():
    """Snapshot and restore every recorder global (not the task handle)."""
    names = [
        n for n in vars(app_main) if n.startswith("_loop_lag") and n != "_loop_lag_task"
    ]
    saved = {}
    for n in names:
        value = getattr(app_main, n)
        if callable(value):
            continue
        saved[n] = copy.deepcopy(value)
    yield
    for n, value in saved.items():
        setattr(app_main, n, value)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _tick(lag_seconds: float) -> None:
    app_main.record_loop_lag_tick(INTERVAL + lag_seconds)


def _healthy(n: int) -> None:
    for _ in range(n):
        app_main.record_loop_lag_tick(INTERVAL)


def _health() -> dict:
    """GET /health WITHOUT entering the lifespan -- no heartbeat is running, so
    nothing can overwrite the synthetic ticks the test recorded."""
    resp = TestClient(app).get("/health")
    assert resp.status_code == 200
    return resp.json()


def _require_new_key(payload: dict) -> float:
    if NEW_KEY not in payload:
        pytest.fail(
            f"{NEW_KEY!r} absent (keys={sorted(payload)}): loop_lag_max_ms is a "
            "high-water mark since process start that never decays, so a NEW "
            "stall after an old one is invisible to both existing numbers "
            "(W1-10b)."
        )
    value = payload[NEW_KEY]
    assert not isinstance(value, bool) and isinstance(value, numbers.Real), value
    return float(value)


# ===========================================================================
# PINS (green today) -- the wiring the old file only claimed to pin
# ===========================================================================


class TestW110bHealthReadsTheRecorder:
    def test_health_reflects_a_recorded_tick(self):
        """Kills mutant A (/health returns literal zeros)."""
        _tick(0.7)
        payload = _health()
        assert payload["loop_lag_ms"] == pytest.approx(700.0, abs=1.0), payload
        assert payload["loop_lag_max_ms"] >= 700.0 - 1.0, payload

    def test_health_last_value_follows_the_latest_tick(self):
        _tick(0.25)
        assert _health()["loop_lag_ms"] == pytest.approx(250.0, abs=1.0)
        _healthy(1)
        assert _health()["loop_lag_ms"] == pytest.approx(0.0, abs=1.0)

    def test_high_water_mark_semantics_are_unchanged(self):
        """PIN for 'existing keys unchanged': loop_lag_max_ms stays the max
        since process start -- it must NOT become windowed. After an 11 s
        stall and 120 healthy ticks it still reads >= 11,000 ms."""
        _tick(11.0)
        _healthy(2 * RING_SLOTS)
        payload = _health()
        assert payload["loop_lag_max_ms"] >= 11000.0 - 1.0, payload
        assert payload["loop_lag_ms"] == pytest.approx(0.0, abs=1.0), payload

    def test_status_and_message_are_unchanged(self):
        payload = _health()
        assert payload["status"] == "healthy"
        assert payload["message"] == "Qaren API is running"


class _Stop(Exception):
    """Raised by the fake sleep to end the heartbeat after N ticks."""


class TestW17bHeartbeatMeasuresElapsed:
    def test_heartbeat_records_now_minus_previous(self, monkeypatch):
        """Kills mutant B (records the interval) and mutant C (never advances
        ``previous``). Driven by a scripted loop clock, so nothing depends on
        the wall clock of a loaded box.

        Clock: 100.0 (start), 101.0, 102.0, 105.5 (a 2.5 s stall), 106.5.
        Correct: [1.0, 1.0, 3.5, 1.0].  Mutant B: [1, 1, 1, 1].
        Mutant C: [1.0, 2.0, 5.5, 6.5].
        """
        clock = iter([100.0, 101.0, 102.0, 105.5, 106.5])
        fake_loop = types.SimpleNamespace(time=lambda: next(clock))
        sleeps: list[float] = []

        async def fake_sleep(seconds):
            if len(sleeps) == 4:
                raise _Stop()
            sleeps.append(seconds)

        fake_asyncio = types.SimpleNamespace(
            get_running_loop=lambda: fake_loop,
            sleep=fake_sleep,
            CancelledError=asyncio.CancelledError,
        )
        seen: list[float] = []
        monkeypatch.setattr(app_main, "asyncio", fake_asyncio)
        monkeypatch.setattr(app_main, "record_loop_lag_tick", seen.append)

        coro = app_main._loop_lag_heartbeat()
        with pytest.raises(_Stop):
            coro.send(None)

        assert seen == pytest.approx([1.0, 1.0, 3.5, 1.0]), (
            f"the heartbeat recorded {seen!r}; it must record the MEASURED "
            "elapsed time between consecutive wake-ups (now - previous)"
        )
        assert sleeps == [app_main.LOOP_LAG_INTERVAL_SECONDS] * 4, sleeps

    def test_heartbeat_feeds_the_real_recorder(self, monkeypatch):
        """End of the chain: the scripted stall reaches /health."""
        clock = iter([200.0, 201.0 + 1.25])
        fake_loop = types.SimpleNamespace(time=lambda: next(clock))
        calls = {"n": 0}

        async def fake_sleep(seconds):
            calls["n"] += 1
            if calls["n"] == 2:
                raise _Stop()

        monkeypatch.setattr(
            app_main,
            "asyncio",
            types.SimpleNamespace(get_running_loop=lambda: fake_loop, sleep=fake_sleep),
        )
        coro = app_main._loop_lag_heartbeat()
        with pytest.raises(_Stop):
            coro.send(None)
        monkeypatch.undo()  # restore the real asyncio before driving the app
        assert _health()["loop_lag_ms"] == pytest.approx(1250.0, abs=1.0)


class TestW17bShutdownIsRegistered:
    def test_lifespan_shutdown_runs_the_app_handler(self):
        """Kills mutant D (shutdown decorator removed). Only the app's own
        handler clears ``_loop_lag_task``; the portal's teardown cancel does
        not."""
        with TestClient(app):
            task = app_main._loop_lag_task
            assert isinstance(task, asyncio.Task)
        assert task.cancelled(), "the heartbeat task was not cancelled on shutdown"
        assert app_main._loop_lag_task is None, (
            "the app's shutdown handler did not run -- _loop_lag_task is still "
            "set after lifespan exit, so the handler is not registered"
        )

    def test_heartbeat_stop_is_registered_before_the_drain(self):
        """The W1-6 drain comment reasons from this order: stop the thing that
        never ends before waiting on the things that do."""
        handlers = list(getattr(app.router, "on_shutdown", []) or [])
        names = [getattr(h, "__name__", repr(h)) for h in handlers]
        assert "_stop_loop_lag_heartbeat" in names, names
        assert "_drain_background_tasks" in names, names
        assert names.index("_stop_loop_lag_heartbeat") < names.index(
            "_drain_background_tasks"
        ), names


# ===========================================================================
# RED -- W1-10b: a windowed max so a NEW stall is visible
# ===========================================================================


class TestW110bWindowedMax:
    def test_health_reports_the_windowed_max(self):
        """RED today: /health has no loop_lag_max_60s_ms."""
        payload = _health()
        value = _require_new_key(payload)
        assert value >= 0.0
        # additive: the existing keys are still there, still numbers
        for key in ("loop_lag_ms", "loop_lag_max_ms"):
            assert isinstance(payload[key], numbers.Real) and not isinstance(payload[key], bool)

    def test_snapshot_carries_the_windowed_max(self):
        """RED today: loop_lag_snapshot() returns two keys only."""
        snap = app_main.loop_lag_snapshot()
        assert {"loop_lag_ms", "loop_lag_max_ms"} <= set(snap)
        _require_new_key(snap)

    def test_new_stall_after_old_high_water_mark_is_visible(self):
        """RED today. The adversary's measured scenario: 11 s stall, a minute
        of healthy ticks, then a NEW 4 s stall and one healthy tick. Today both
        numbers hide the new stall (last = 0, max = 11,000)."""
        _healthy(RING_SLOTS)  # flush whatever earlier tests left in the window
        _tick(11.0)
        _healthy(RING_SLOTS)
        _tick(4.0)
        _healthy(1)
        payload = _health()
        windowed = _require_new_key(payload)
        assert windowed == pytest.approx(4000.0, abs=1.0), payload
        assert payload["loop_lag_max_ms"] >= 11000.0 - 1.0, payload
        assert payload["loop_lag_ms"] == pytest.approx(0.0, abs=1.0), payload

    def test_window_is_exactly_sixty_ticks(self):
        """RED today. A stall is visible for the tick it happened on plus the
        next 59, and gone on the 60th healthy tick after it."""
        _healthy(RING_SLOTS)
        _tick(2.0)
        _healthy(RING_SLOTS - 1)
        assert _require_new_key(app_main.loop_lag_snapshot()) == pytest.approx(2000.0, abs=1.0)
        _healthy(1)
        assert _require_new_key(app_main.loop_lag_snapshot()) == pytest.approx(0.0, abs=1.0)

    def test_windowed_max_is_never_below_last_nor_above_high_water_mark(self):
        """RED today (key absent). Invariant on every tick."""
        _healthy(RING_SLOTS)
        for lag in (0.0, 0.3, 0.05, 1.2, 0.0, 0.0, 0.4):
            _tick(lag)
            snap = app_main.loop_lag_snapshot()
            windowed = _require_new_key(snap)
            assert snap["loop_lag_ms"] <= windowed + 1e-9, snap
            assert windowed <= snap["loop_lag_max_ms"] + 1e-9, snap

    def test_negative_elapsed_still_floors_at_zero_in_the_window(self):
        """RED today (key absent). Clock granularity is not negative lag."""
        _healthy(RING_SLOTS)
        app_main.record_loop_lag_tick(max(0.0, INTERVAL - 0.01))
        assert _require_new_key(app_main.loop_lag_snapshot()) == pytest.approx(0.0, abs=1e-9)

    def test_window_of_only_short_ticks_reads_zero_not_negative(self):
        """GREEN-phase pin (added after mutant W5 -- the ring fed the UNFLOORED
        lag -- survived the test above: one negative sample never wins a max
        over 59 zeros). A full window of short ticks must read 0.0, never a
        negative lag."""
        for _ in range(RING_SLOTS):
            app_main.record_loop_lag_tick(max(0.0, INTERVAL - 0.01))
        assert _require_new_key(app_main.loop_lag_snapshot()) == 0.0

    def test_windowed_max_is_computed_by_the_recorder_not_by_health(self):
        """FIX-ROUND-2 pin (prove-nothing row: a mutant where loop_lag_snapshot
        returned max(_loop_lag_ring, default=0.0) survived every node). The
        design claim is that the RECORDER recomputes the windowed max once per
        tick, so /health and loop_lag_snapshot() stay a pure dict read that
        never walks the ring. After a real stall is recorded, the ring is
        swapped for one that fails the test if anything iterates, measures or
        indexes it; both the snapshot and GET /health must still report the
        recorder's value."""
        _healthy(RING_SLOTS)
        _tick(3.0)
        _healthy(2)
        recorded = _require_new_key(app_main.loop_lag_snapshot())
        assert recorded == pytest.approx(3000.0, abs=1.0)

        class _UntouchableRing:
            def _touched(self, *args, **kwargs):
                raise AssertionError(
                    "the /health read path walked the loop-lag ring; the "
                    "windowed max must be precomputed by the recorder"
                )

            __iter__ = __len__ = __getitem__ = __contains__ = __reversed__ = _touched
            __bool__ = _touched

        # Plain assignment, not monkeypatch: the autouse _restore_loop_lag_state
        # fixture puts every _loop_lag* global (this ring included) back.
        app_main._loop_lag_ring = _UntouchableRing()
        assert _require_new_key(app_main.loop_lag_snapshot()) == recorded
        assert _require_new_key(_health()) == recorded
