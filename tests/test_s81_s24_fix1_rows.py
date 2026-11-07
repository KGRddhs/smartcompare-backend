"""S81-24 fix round 1 rows (RULINGS_FIX1_S81_24 F1-1, the security MAJOR F1).

The shielded LOGIN_FAIL / LOGIN_CLEAR writes keep their durability, but a
cancel of the outer wait (a wait_for timeout or a task cancel) followed by a
LATER failure of the pool job must never leave the loop's ERROR
'Future exception was never retrieved' (with the exception repr); the inner
future's exception is retrieved by a done-callback and logged as ONE
constants-only WARNING '[AUTH_THROTTLE] record failed endpoint=<name>
type=<Type>'. The gate read stays cancellable and unshielded (R-S24-24).

- F1-R1 (RED at f8f64d9d): a cancelled durable write whose job raises later.
- F1-R2 (PIN): a cancelled gate read raises nothing and logs nothing new.
- F1-R3 (PIN): the durable write still lands after the outer cancel.

Hermetic: no network, no .env, synthetic values built at run time, a small
upstash-shaped fake client; the module's pool is replaced per row.
"""
import asyncio
import concurrent.futures
import gc
import logging
import re
import threading

import pytest

MOD = "app.services.auth_throttle"
FLAG = "ENABLE_AUTH_THROTTLE_V2"
HOP_FLAG = "ENABLE_HOP_PROBE_LOG"
PEPPER_ENV_NAME = "AUTH_THROTTLE_" + "PEPPER"
PEPPER_VALUE = "s24-fix1-" + "q" * 8
TIMEOUT_KNOB = "AUTH_THROTTLE_REDIS_TIMEOUT_SECONDS"
KNOB_VALUES = (
    ("AUTH_THROTTLE_LOGIN_CAP_SECONDS", "30"),
    ("AUTH_THROTTLE_REGISTER_INTERVAL_SECONDS", "20"),
    ("AUTH_THROTTLE_RESET_INTERVAL_SECONDS", "15"),
    ("AUTH_THROTTLE_RESET_PER_DAY", "3"),
    ("AUTH_THROTTLE_ACCOUNT_PER_WINDOW", "2"),
    ("AUTH_THROTTLE_ACCOUNT_WINDOW_SECONDS", "120"),
    ("AUTH_THROTTLE_TTL_SECONDS", "7200"),
    (TIMEOUT_KNOB, "0.05"),
)
E1 = "fix1-a" + "@" + "example.com"
BAD_RESULT = {"success": False, "error": "Invalid email or password"}
LATE_TEXT = "s24 late failure detail"
RECORD_FAILED_RE = re.compile(
    r"\[AUTH_THROTTLE\] record failed endpoint=([a-z_]+) type=([A-Za-z_][A-Za-z0-9_]*)"
)
SKIPPED_RE = re.compile(r"\[AUTH_THROTTLE\] skipped endpoint=([a-z_]+) type=([A-Za-z_][A-Za-z0-9_]*)")
NEVER = "never retrieved"


class LateFake:
    """upstash-redis shaped: eval(script, keys=, args=); the call is recorded
    first, then the job blocks until released, then raises or returns."""

    def __init__(self):
        self.calls = []
        self.release = threading.Event()
        self.finished = threading.Event()
        self.fail_with = None
        self.reply = 1

    def eval(self, script, keys=None, args=None):
        self.calls.append((script, tuple(keys or ()), tuple(str(a) for a in (args or ()))))
        try:
            self.release.wait(5.0)
            if self.fail_with is not None:
                raise self.fail_with(LATE_TEXT)
            return self.reply
        finally:
            self.finished.set()


LateFake.__module__ = "upstash_redis.s24fix1"


class Cap(logging.Handler):
    def __init__(self):
        super().__init__(level=logging.DEBUG)
        self.records = []

    def emit(self, record):
        self.records.append(record)

    def messages(self):
        return [r.getMessage() for r in self.records]


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    import app.main  # noqa: F401  (the DOTENV GUARD rule: import first, then setenv)
    for name in (FLAG, HOP_FLAG, PEPPER_ENV_NAME):
        monkeypatch.delenv(name, raising=False)
    for name, _v in KNOB_VALUES:
        monkeypatch.delenv(name, raising=False)
    import importlib
    m = importlib.import_module(MOD)
    m._reset_pepper_warning()
    m._reset_skip_memo()
    yield
    m._reset_pepper_warning()
    m._reset_skip_memo()


@pytest.fixture
def caps():
    app_lg = logging.getLogger("app")
    aio_lg = logging.getLogger("asyncio")
    app_cap, aio_cap = Cap(), Cap()
    old = (app_lg.level, aio_lg.level)
    app_lg.addHandler(app_cap)
    aio_lg.addHandler(aio_cap)
    app_lg.setLevel(logging.INFO)
    aio_lg.setLevel(logging.DEBUG)
    yield app_cap, aio_cap
    app_lg.removeHandler(app_cap)
    aio_lg.removeHandler(aio_cap)
    app_lg.setLevel(old[0])
    aio_lg.setLevel(old[1])


def _arm(monkeypatch):
    import importlib
    at = importlib.import_module(MOD)
    monkeypatch.setenv(FLAG, "true")
    monkeypatch.setenv(PEPPER_ENV_NAME, PEPPER_VALUE)
    for name, value in KNOB_VALUES:
        monkeypatch.setenv(name, value)
    fake = LateFake()
    from app.services import cache_service
    monkeypatch.setattr(cache_service, "redis_client", fake)
    ex = concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix="s24-fix1")
    monkeypatch.setattr(at, "_pool", lambda: ex)
    return at, fake, ex


async def _settle(fake):
    """Release the parked job, wait for it to finish on its thread, let the
    loop run the chained callbacks, then collect inside the running loop."""
    fake.release.set()
    for _ in range(300):
        if fake.finished.is_set():
            break
        await asyncio.sleep(0.01)
    for _ in range(5):
        await asyncio.sleep(0.02)
    gc.collect()
    await asyncio.sleep(0.02)


def _drive(at, fake, mode, handler_ctx):
    async def main():
        loop = asyncio.get_running_loop()
        loop.set_exception_handler(lambda _l, ctx: handler_ctx.append(dict(ctx)))
        if mode == "fail_timeout":
            await at.record_login_failure(E1, dict(BAD_RESULT))
        elif mode == "clear_cancel":
            task = asyncio.ensure_future(at.record_login_success(E1))
            await asyncio.sleep(0.01)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        elif mode == "gate_timeout":
            assert await at.gate("login", E1) is None
        await _settle(fake)
    asyncio.run(main())
    gc.collect()


def _never_retrieved(handler_ctx, aio_cap):
    hits = [c.get("message", "") for c in handler_ctx if NEVER in str(c.get("message", ""))]
    hits += [m for m in aio_cap.messages() if NEVER in m]
    return hits


@pytest.mark.parametrize("mode,endpoint", [("fail_timeout", "login_fail"), ("clear_cancel", "login_clear")])
def test_f1_r1_cancelled_durable_write_late_raise_is_retrieved(monkeypatch, caps, mode, endpoint):
    app_cap, aio_cap = caps
    at, fake, ex = _arm(monkeypatch)
    fake.fail_with = ConnectionError
    handler_ctx = []
    try:
        _drive(at, fake, mode, handler_ctx)
    finally:
        fake.release.set()
        ex.shutdown(wait=True)
    assert len(fake.calls) == 1
    assert _never_retrieved(handler_ctx, aio_cap) == []
    lines = [r for r in app_cap.records if r.getMessage().startswith("[AUTH_THROTTLE] record failed")]
    assert [r.getMessage() for r in lines] == [
        "[AUTH_THROTTLE] record failed endpoint=%s type=ConnectionError" % endpoint
    ]
    rec = lines[0]
    assert RECORD_FAILED_RE.fullmatch(rec.getMessage())
    assert rec.levelno == logging.WARNING and rec.name == MOD
    assert rec.exc_info is None and not rec.exc_text and rec.stack_info is None
    for r in app_cap.records:
        msg = r.getMessage()
        assert LATE_TEXT not in msg, msg
        assert "auth_throttle:" not in msg and E1 not in msg and PEPPER_VALUE not in msg, msg
        assert not re.search(r"[0-9a-f]{32}", msg), msg
    for c in handler_ctx:
        assert LATE_TEXT not in repr(c)


def test_f1_r2_cancelled_gate_read_raises_nothing_logs_nothing_new(monkeypatch, caps):
    app_cap, aio_cap = caps
    at, fake, ex = _arm(monkeypatch)
    fake.fail_with = ConnectionError
    handler_ctx = []
    try:
        _drive(at, fake, "gate_timeout", handler_ctx)
    finally:
        fake.release.set()
        ex.shutdown(wait=True)
    assert len(fake.calls) == 1
    assert handler_ctx == []
    assert _never_retrieved(handler_ctx, aio_cap) == []
    msgs = [m for m in app_cap.messages() if m.startswith("[AUTH_THROTTLE]")]
    assert msgs == ["[AUTH_THROTTLE] skipped endpoint=login type=TimeoutError"]
    assert all(LATE_TEXT not in m for m in app_cap.messages())


def test_f1_r3_durable_write_lands_after_outer_cancel(monkeypatch, caps):
    app_cap, aio_cap = caps
    at, fake, ex = _arm(monkeypatch)
    handler_ctx = []
    try:
        _drive(at, fake, "fail_timeout", handler_ctx)
        fake2 = LateFake()
        from app.services import cache_service
        monkeypatch.setattr(cache_service, "redis_client", fake2)
        _drive(at, fake2, "clear_cancel", handler_ctx)
    finally:
        fake.release.set()
        ex.shutdown(wait=True)
    assert fake.finished.is_set() and fake2.finished.is_set()
    assert [c[0] for c in fake.calls] == [at.LOGIN_FAIL_SCRIPT]
    assert [c[0] for c in fake2.calls] == [at.LOGIN_CLEAR_SCRIPT]
    key = fake.calls[0][1]
    assert len(key) == 1 and key[0].startswith("auth_throttle:login:backoff:")
    assert fake2.calls[0][1] == key
    assert handler_ctx == []
    assert _never_retrieved(handler_ctx, aio_cap) == []
    assert [m for m in app_cap.messages() if m.startswith("[AUTH_THROTTLE] record failed")] == []
    skipped = [SKIPPED_RE.fullmatch(m).groups() for m in app_cap.messages()
               if m.startswith("[AUTH_THROTTLE] skipped")]
    assert skipped == [("login_fail", "TimeoutError")]
