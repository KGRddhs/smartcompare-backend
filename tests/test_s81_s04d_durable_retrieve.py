"""S81-G10 / S81-04d SPEND-DURABLE-RETRIEVE -- RED and PIN rows.

Spec .qa-s80/S81-G10_UNIT_SPEC.md section 04d.5 as amended by RULINGS_S81_G10 (R-G10-9: the
local twin `_retrieve_quietly` in llm_spend_breaker.py, pinned EQUAL to the house body of
app/utils/redis_offloop.py by the ast.dump of the two function bodies (the docstring set
aside), attached only when `durable`, before the shield; R-G10-10: D-M5 is behaviourally
EQUIVALENT, the `if durable` form is pinned structurally). Base 90d4ed74.

The defect: llm_spend_breaker._run_bounded_async(durable=True) awaits
wait_for(shield(wrap_future(pool_job)), bound). When the bound expires (or the awaiting task
is cancelled) the shield's outer future is cancelled first and CPython 3.12's shield then
REMOVES its inner done-callback, so a record EVAL that fails later leaves the inner future's
exception never retrieved: the loop reports 'Future exception was never retrieved' (an ERROR
with the exception repr on the Sentry channel). The fix retrieves it quietly; the late failure
is still counted ONCE as a fail-open by _record_finished -> _record_failed (no new line).

Every RED row fails at base on an AssertionError only (a missing `_retrieve_quietly` is read
with getattr and asserted). The seams: the real _run_bounded_async / record_soon, a fake
upstash-shaped Redis client (eval sleeps, then raises or lands), LLM_SPEND_REDIS_TIMEOUT_SECONDS
small, a loop exception-handler recorder, caplog, gc.collect() inside the loop, and a spy on
the module's asyncio for the wrapped future's callbacks. Hermetic: no network, no .env, no
credential. Pure ASCII, LF.
"""
from __future__ import annotations

import ast
import asyncio
import concurrent.futures
import gc
import logging
import threading
import time
from pathlib import Path

import pytest

import app.main  # noqa: F401  FIRST: the dotenv guard (load_dotenv at import)
from app.services import cache_service
from app.services import llm_spend_breaker as br

ROOT = Path(__file__).resolve().parents[1]
LEAF_PATH = ROOT / "app" / "services" / "llm_spend_breaker.py"
HOUSE_PATH = ROOT / "app" / "utils" / "redis_offloop.py"
FLAG = "ENABLE_LLM_SPEND_BREAKER"
TIMEOUT_ENV = "LLM_SPEND_REDIS_TIMEOUT_SECONDS"
CLEAR = (FLAG, TIMEOUT_ENV, "ENABLE_LLM_PREFLIGHT_BREAKER", "LLM_BREAKER_CACHE_TTL", "LLM_SPEND_MEMO_SECONDS",
         "LLM_SPEND_ENTRY_RESERVE_USD", "LLM_SPEND_CHOKEPOINT_LANE", "LLM_SPEND_CAP_LIVE_USD",
         "LLM_SPEND_CAP_ESCALATION_USD", "LLM_SPEND_CAP_SEARCH_USD", "LLM_SPEND_CAP_OFFCLOCK_USD")
NEVER = "Future exception was never retrieved"
BOUND = "0.05"
LATE = 0.3
FAILOPEN_LINE = "[SPEND] breaker fail-open (ConnectionError) -- admitting and not recording"
LATE_LINE = "[SPEND] late record landed -- recorded after its bound expired"
# R01 of tests/test_s81_s04_spend_breaker.py: the leaf's top-level app imports (base 90d4ed74).
APP_TOP_IMPORTS = {("app.services", "cache_service"), ("app.services", "llm_pricing"),
                   ("app.services", "openai_pricing"), ("app.utils", "async_utils")}


class _LateUpstash:
    """upstash-redis 1.7.0 call shape: eval(script, keys=, args=); every EVAL waits `delay`
    seconds on its pool thread, then raises (`fail`) or lands (the new total)."""

    def __init__(self, *, delay=LATE, fail=True):
        self.delay = delay
        self.fail = fail
        self.store = {}
        self.evals = []
        self.done = threading.Event()

    def get(self, key):
        return self.store.get(key)

    def eval(self, script, keys=None, args=None):
        key = (list(keys or []) or [""])[0]
        self.evals.append(key)
        try:
            time.sleep(self.delay)
            if self.fail:
                raise ConnectionError("s04d synthetic redis failure")
            self.store[key] = args[0] if args else "0"
            return self.store[key]
        finally:
            self.done.set()


_LateUpstash.__module__ = "upstash_redis.client"


class _AsyncioSpy:
    """The module's asyncio, with the wrapped future recorded and its done-callbacks
    snapshotted when wait_for is entered (every other attribute delegates)."""

    def __init__(self, real):
        self._real = real
        self.wrapped = []
        self.snapshots = []

    def __getattr__(self, name):
        return getattr(self._real, name)

    def wrap_future(self, fut, *a, **k):
        out = self._real.wrap_future(fut, *a, **k)
        self.wrapped.append(out)
        return out

    def wait_for(self, aw, timeout):
        cbs = getattr(self.wrapped[-1], "_callbacks", None) or []
        self.snapshots.append([getattr(c[0], "__name__", repr(c[0])) for c in cbs])
        return self._real.wait_for(aw, timeout)


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    for name in CLEAR:
        monkeypatch.delenv(name, raising=False)
    br._reset_spend_breaker_state()
    yield
    br._reset_spend_breaker_state()


def _full(monkeypatch, fake=None):
    monkeypatch.setenv(FLAG, "true")
    monkeypatch.setenv(TIMEOUT_ENV, BOUND)
    if fake is not None:
        monkeypatch.setattr(cache_service, "redis_client", fake)


def _late_job(outcome, delay=LATE):
    ev = threading.Event()

    def job():
        try:
            time.sleep(delay)
            if outcome == "raise":
                raise RuntimeError("s04d synthetic late failure")
            return "landed"
        finally:
            ev.set()
    return job, ev


async def _settle(event, extra=0.2):
    deadline = time.monotonic() + 5.0
    while not event.is_set() and time.monotonic() < deadline:
        await asyncio.sleep(0.02)
    await asyncio.sleep(extra)
    gc.collect()
    await asyncio.sleep(0.05)
    gc.collect()


def _drive(body):
    """Run `body(handled)` in a fresh loop whose exception handler records every context
    message (the 'never retrieved' report and any 'Exception in callback')."""
    handled = []

    async def main():
        loop = asyncio.get_running_loop()
        loop.set_exception_handler(lambda _lp, ctx: handled.append(str(ctx.get("message"))))
        return await body(handled)

    result = asyncio.run(main())
    gc.collect()
    return result, handled


def _never(handled):
    return [m for m in handled if NEVER in m]


# =============================================================== RED rows (R1-R4)

def test_r1_late_failure_after_the_bound_is_retrieved(monkeypatch):
    """R1: a durable job that raises AFTER the awaiter's bound: the awaiter gets TimeoutError;
    once the job ended (gc.collect inside the loop) the loop reports NO 'never retrieved'."""
    _full(monkeypatch)
    job, ev = _late_job("raise")

    async def body(_handled):
        try:
            await br._run_bounded_async(job, durable=True)
            got = "returned"
        except TimeoutError:
            got = "TimeoutError"
        await _settle(ev)
        return got

    got, handled = _drive(body)
    assert got == "TimeoutError" and ev.is_set()
    assert _never(handled) == [], handled


def test_r2_awaiter_cancelled_then_late_failure_is_retrieved(monkeypatch):
    """R2: the awaiting task is cancelled, then the durable job raises: no 'never retrieved'."""
    _full(monkeypatch)
    monkeypatch.setenv(TIMEOUT_ENV, "5.0")
    job, ev = _late_job("raise")

    async def body(_handled):
        task = asyncio.ensure_future(br._run_bounded_async(job, durable=True))
        await asyncio.sleep(0.02)
        task.cancel()
        try:
            await task
            got = "returned"
        except asyncio.CancelledError:
            got = "CancelledError"
        await _settle(ev)
        return got

    got, handled = _drive(body)
    assert got == "CancelledError" and ev.is_set()
    assert _never(handled) == [], handled


def test_r3_record_soon_late_eval_failure(monkeypatch, caplog):
    """R3: record_soon('live', 0.2) whose EVAL raises after the bound: no 'never retrieved'
    report; llm_spend_fail_open +1 exactly once; the breaker logger's lines are exactly the
    base set (the one fail-open WARNING); the EVAL ran once."""
    fake = _LateUpstash(fail=True)
    _full(monkeypatch, fake)
    caplog.set_level(logging.DEBUG, logger=br.logger.name)

    async def body(_handled):
        task = br.record_soon("live", 0.2)
        assert task is not None
        await task
        await _settle(fake.done)
        deadline = time.monotonic() + 3.0
        while br.spend_snapshot().get("llm_spend_fail_open", 0) < 1 and time.monotonic() < deadline:
            await asyncio.sleep(0.02)
        return br.spend_snapshot()

    snap, handled = _drive(body)
    assert _never(handled) == [], handled
    assert handled == [], handled
    assert snap.get("llm_spend_fail_open") == 1 and snap.get("llm_spend_late_records") == 0, snap
    assert len(fake.evals) == 1
    lines = [(r.levelname, r.getMessage()) for r in caplog.records if r.name == br.logger.name]
    assert lines == [("WARNING", FAILOPEN_LINE)], lines


def _body_dump(fn_node):
    body = list(fn_node.body)
    if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant) \
            and isinstance(body[0].value.value, str):
        body = body[1:]
    return [ast.dump(stmt) for stmt in body]


def _module_fn(path, name):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    return None


def test_r4_the_twin_and_its_attach_point():
    """R4: llm_spend_breaker._retrieve_quietly exists and its body (docstring set aside)
    equals the house body of app/utils/redis_offloop.py by ast.dump; _run_bounded_async
    attaches it with add_done_callback inside `if durable:` and BEFORE the asyncio.shield call."""
    assert callable(getattr(br, "_retrieve_quietly", None)), "llm_spend_breaker._retrieve_quietly is missing"
    twin = _module_fn(LEAF_PATH, "_retrieve_quietly")
    house = _module_fn(HOUSE_PATH, "_retrieve_quietly")
    assert twin is not None and house is not None
    assert [a.arg for a in twin.args.args] == [a.arg for a in house.args.args], (
        [a.arg for a in twin.args.args], [a.arg for a in house.args.args])
    assert _body_dump(twin) == _body_dump(house), (_body_dump(twin), _body_dump(house))
    run = _module_fn(LEAF_PATH, "_run_bounded_async")
    assert run is not None
    attach_lines, inside_durable = [], []
    for node in ast.walk(run):
        if isinstance(node, ast.If) and isinstance(node.test, ast.Name) and node.test.id == "durable":
            for sub in ast.walk(node):
                if (isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute)
                        and sub.func.attr == "add_done_callback" and len(sub.args) == 1
                        and isinstance(sub.args[0], ast.Name) and sub.args[0].id == "_retrieve_quietly"):
                    inside_durable.append(sub.lineno)
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "add_done_callback"):
            attach_lines.append(node.lineno)
    shield_lines = [n.lineno for n in ast.walk(run) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                    and n.func.attr == "shield"]
    assert len(inside_durable) == 1 and attach_lines == inside_durable, (inside_durable, attach_lines)
    assert len(shield_lines) == 1 and inside_durable[0] < shield_lines[0], (inside_durable, shield_lines)


# =============================================================== PIN rows (P1-P5)

def test_p1_late_success_lands_once(monkeypatch, caplog):
    """P1 (PIN): a record EVAL that lands after the bound: the store holds the value, ONE
    late-record INFO line, llm_spend_late_records +1, no fail-open, no loop report."""
    fake = _LateUpstash(fail=False)
    _full(monkeypatch, fake)
    caplog.set_level(logging.DEBUG, logger=br.logger.name)

    async def body(_handled):
        task = br.record_soon("live", 0.2)
        assert task is not None
        await task
        await _settle(fake.done)
        deadline = time.monotonic() + 3.0
        while br.spend_snapshot().get("llm_spend_late_records", 0) < 1 and time.monotonic() < deadline:
            await asyncio.sleep(0.02)
        return br.spend_snapshot()

    snap, handled = _drive(body)
    assert handled == [], handled
    assert snap.get("llm_spend_late_records") == 1 and snap.get("llm_spend_fail_open") == 0, snap
    assert len(fake.evals) == 1 and fake.store.get(fake.evals[0]) not in (None, ""), fake.store
    lines = [(r.levelname, r.getMessage()) for r in caplog.records if r.name == br.logger.name]
    assert lines == [("INFO", LATE_LINE)], lines


class _ControlledPool:
    def __init__(self):
        self.futures = []

    def submit(self, fn, *args):
        fut = concurrent.futures.Future()
        self.futures.append(fut)
        return fut


def test_p2_cancelled_inner_future_is_left_alone(monkeypatch):
    """P2 (PIN): the pool job never runs and its future is cancelled after the awaiter's
    bound: no loop report (no 'never retrieved', no 'Exception in callback'): the quiet
    retrieval never calls .exception() on a cancelled future."""
    _full(monkeypatch)
    pool = _ControlledPool()
    monkeypatch.setattr(br, "_get_llm_spend_pool", lambda: pool)

    async def body(_handled):
        try:
            await br._run_bounded_async(lambda: None, durable=True)
            got = "returned"
        except TimeoutError:
            got = "TimeoutError"
        assert len(pool.futures) == 1
        assert pool.futures[0].cancel() is True
        ev = threading.Event()
        ev.set()
        await _settle(ev, extra=0.1)
        return got

    got, handled = _drive(body)
    assert got == "TimeoutError"
    assert handled == [], handled


@pytest.mark.parametrize("durable", [True, False], ids=["durable", "plain"])
def test_p3_in_bound_failure_propagates(monkeypatch, durable):
    """P3 (PIN): a job that fails inside the bound propagates its own exception type to the
    caller, both paths; no loop report."""
    _full(monkeypatch)
    monkeypatch.setenv(TIMEOUT_ENV, "5.0")
    job, ev = _late_job("raise", delay=0.0)

    async def body(_handled):
        try:
            await br._run_bounded_async(job, durable=durable)
            got = "returned"
        except RuntimeError as exc:
            got = type(exc).__name__
        await _settle(ev, extra=0.05)
        return got

    got, handled = _drive(body)
    assert got == "RuntimeError"
    assert handled == [], handled


def test_p4_plain_path_unchanged(monkeypatch):
    """P4 (PIN): durable=False: the wrapped future carries only the chain's own callback when
    it is awaited (nothing attached), the bound still raises TimeoutError and a late failure
    is never reported."""
    _full(monkeypatch)
    spy = _AsyncioSpy(asyncio)
    monkeypatch.setattr(br, "asyncio", spy)
    job, ev = _late_job("raise")

    async def body(_handled):
        try:
            await br._run_bounded_async(job, durable=False)
            got = "returned"
        except TimeoutError:
            got = "TimeoutError"
        await _settle(ev)
        return got

    got, handled = _drive(body)
    assert got == "TimeoutError"
    assert spy.snapshots == [["_call_check_cancel"]], spy.snapshots
    assert handled == [], handled


def test_p5_leaf_import_rule():
    """P5 (PIN): the S81-04 R01 rule holds: the top-level app imports are exactly the base
    four, and nothing imports redis_offloop (top level, lazy or by an importlib string)."""
    tree = ast.parse(LEAF_PATH.read_text(encoding="utf-8"))
    top = set()
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("app."):
            top |= {(node.module, a.name) for a in node.names}
        elif isinstance(node, ast.Import):
            assert not any(a.name.startswith("app.") for a in node.names), ast.dump(node)
    assert top == APP_TOP_IMPORTS, top
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            assert "redis_offloop" not in (node.module or "") and all(
                a.name != "redis_offloop" for a in node.names), ast.dump(node)
        elif isinstance(node, ast.Import):
            assert all("redis_offloop" not in a.name for a in node.names), ast.dump(node)
        elif isinstance(node, ast.Call):
            name = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", "")
            if name in ("import_module", "__import__"):
                args = [a.value for a in node.args if isinstance(a, ast.Constant) and isinstance(a.value, str)]
                assert not any("redis_offloop" in a for a in args), ast.dump(node)
