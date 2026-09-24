"""R-W0 / W0-1b -- RED tests for the off-loop DNS resolver's 60 s NEGATIVE memo.

Spec: the retroactive adversary report on W0-1/W0-2 (PR #135, merge 67f716f2),
defect 2 ("the 60 s negative memo still blacklists healthy hosts"), under the
orchestrator's binding rulings for W0-1b:

  (1) a ``socket.gaierror`` is memoised ONLY for ``EAI_NONAME`` (and
      ``EAI_NODATA`` where the platform defines it). ``EAI_AGAIN`` and every
      other code fail CLOSED for THIS call only and write nothing;
  (2) ``time.monotonic()`` is recorded INSIDE ``_resolve`` when the job starts,
      and a timeout is memoised only when that resolve genuinely ran for the
      bound -- not when it waited in the pool queue and started just before
      the caller's deadline;
  (3) a slow-but-SUCCESSFUL resolve is never a negative verdict: once the
      zombie resolve returns a public address, no ``False`` may remain in the
      memo for that host.

All three shapes are pinned in BOTH flag states. ``ENABLE_OFFLOOP_DNS_RESOLVE``
stays default OFF, and flag OFF must stay byte-identical to base: a direct
``socket.getaddrinfo`` on the caller's own thread, no pool, no memo read, no
memo write -- including through ``_validate_url_offloop_or_sync``, whose OFF
branch the reviewer found had no dedicated pin.

Out of scope here (not in the W0-1b ruling): W0-1c single-flight (defect 3).

Offline by construction: every resolve is a stub on ``socket.getaddrinfo``; the
autouse ``_zero_network`` fixture blocks any non-loopback ``getaddrinfo`` /
``connect`` and fails the test on any attempt, even one the validator swallows.

gaierror codes are the PLATFORM constants (``socket.EAI_NONAME`` is -2 on
Linux/CI and 11001 on Windows), never a hard-coded ``-2``.
"""
from __future__ import annotations

import asyncio
import ipaddress
import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Dict, List

import pytest

import app.utils.url_validator as uv

FLAG = "ENABLE_OFFLOOP_DNS_RESOLVE"
TIMEOUT_ENV = "DNS_RESOLVE_TIMEOUT_SECONDS"
POOL_ENV = "DNS_RESOLVER_POOL_SIZE"

_PUBLIC = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))]
_PRIVATE = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.7", 0))]

EAI_NONAME = socket.EAI_NONAME
EAI_AGAIN = socket.EAI_AGAIN
EAI_FAIL = socket.EAI_FAIL
_EAI_NODATA = getattr(socket, "EAI_NODATA", None)

# The confirmed-negative codes the ruling keeps memoising (deduplicated: on
# Windows EAI_NODATA == EAI_NONAME == 11001).
_MEMOISED_CODES = sorted({EAI_NONAME} | ({_EAI_NODATA} if _EAI_NODATA is not None else set()))


# ---------------------------------------------------------------------------
# zero-network guard (autouse)
# ---------------------------------------------------------------------------

_REAL_GETADDRINFO = socket.getaddrinfo
_REAL_CONNECT = socket.socket.connect
_REAL_CONNECT_EX = socket.socket.connect_ex


def _is_loopback_host(host) -> bool:
    if host is None:
        return True
    if isinstance(host, bytes):
        host = host.decode("ascii", "replace")
    h = str(host).strip("[]").lower()
    if h == "localhost":
        return True
    try:
        return ipaddress.ip_address(h.split("%", 1)[0]).is_loopback
    except ValueError:
        return False


@pytest.fixture(autouse=True)
def _zero_network(monkeypatch):
    """Block every non-loopback resolve and connect. Attempts are RECORDED and
    the test fails at teardown even if the code under test swallowed the
    error (both validators catch ``Exception`` and return False)."""
    attempts: List[tuple] = []

    def _guarded_getaddrinfo(host, *args, **kwargs):
        if not _is_loopback_host(host):
            attempts.append(("getaddrinfo", host))
            raise OSError(f"zero-network guard: getaddrinfo({host!r}) blocked")
        return _REAL_GETADDRINFO(host, *args, **kwargs)

    def _check(sock, address, op):
        if sock.family in (socket.AF_INET, socket.AF_INET6):
            host = address[0] if isinstance(address, tuple) else address
            if not _is_loopback_host(host):
                attempts.append((op, address))
                raise OSError(f"zero-network guard: {op}({address!r}) blocked")

    def _guarded_connect(self, address):
        _check(self, address, "connect")
        return _REAL_CONNECT(self, address)

    def _guarded_connect_ex(self, address):
        _check(self, address, "connect_ex")
        return _REAL_CONNECT_EX(self, address)

    monkeypatch.setattr(socket, "getaddrinfo", _guarded_getaddrinfo)
    monkeypatch.setattr(socket.socket, "connect", _guarded_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", _guarded_connect_ex)
    yield attempts
    assert attempts == [], f"zero-network guard: network attempted: {attempts!r}"


@pytest.fixture(autouse=True)
def _isolate(monkeypatch):
    monkeypatch.delenv(FLAG, raising=False)
    monkeypatch.delenv(TIMEOUT_ENV, raising=False)
    monkeypatch.delenv(POOL_ENV, raising=False)
    uv._reset_dns_state_for_tests()
    yield
    uv._reset_dns_state_for_tests()


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


class _Resolver:
    """A per-host programmable ``getaddrinfo`` stub that records host, thread
    and start time of every call."""

    def __init__(self) -> None:
        self.behaviour: Dict[str, Callable[[], list]] = {}
        self.calls: List[str] = []
        self.threads: List[str] = []
        self.started_at: Dict[str, float] = {}
        self._lock = threading.Lock()

    def __call__(self, host, port, *args, **kwargs):
        with self._lock:
            self.calls.append(host)
            self.threads.append(threading.current_thread().name)
            self.started_at.setdefault(host, time.monotonic())
        return self.behaviour[host]()

    def count(self, host: str) -> int:
        with self._lock:
            return self.calls.count(host)


def _install(monkeypatch) -> _Resolver:
    stub = _Resolver()
    monkeypatch.setattr(uv.socket, "getaddrinfo", stub)
    return stub


def _gai(code):
    def _raise():
        if code is None:
            raise socket.gaierror("resolver failure with no code")
        raise socket.gaierror(code, "stub resolver failure")

    return _raise


def _public():
    return _PUBLIC


def _private_pool(monkeypatch, workers: int) -> ThreadPoolExecutor:
    """A private resolver pool so zombie threads of one test never occupy the
    module pool of the next. monkeypatch restores ``_DNS_POOL`` afterwards."""
    pool = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="dns-resolve")
    monkeypatch.setattr(uv, "_DNS_POOL", pool)
    return pool


# ===========================================================================
# SHAPE A -- gaierror codes (ruling 1)
# ===========================================================================


def _transient_then_public(code):
    state = {"n": 0}

    def _flaky():
        state["n"] += 1
        if state["n"] == 1:
            _gai(code)()
        return _PUBLIC

    return _flaky


@pytest.mark.parametrize(
    "code",
    [EAI_AGAIN, EAI_FAIL, None],
    ids=["EAI_AGAIN", "EAI_FAIL", "errno-None"],
)
def test_red_transient_gaierror_is_not_memoised_async(monkeypatch, code):
    """RED today: a non-NONAME gaierror (EAI_AGAIN = resolver SERVFAIL, etc.) is
    written to the 60 s memo, so a storefront whose resolver hiccupped ONCE is
    refused for a minute even though the very next resolve would succeed.
    Reviewer measurement: flag ON 1st=False, 2nd=False, 1 resolve; base retries
    and returns True."""
    monkeypatch.setenv(FLAG, "true")
    stub = _install(monkeypatch)
    host = f"transient-{str(code).lower()}-rw01a.example"
    stub.behaviour[host] = _transient_then_public(code)

    first = asyncio.run(uv._validate_url_offloop_or_sync(f"https://{host}/p"))
    memo_after_first = uv._memo_get(host)
    second = asyncio.run(uv._validate_url_offloop_or_sync(f"https://{host}/p"))

    assert first is False, "a gaierror must still fail CLOSED for this call"
    assert memo_after_first is None, (
        f"gaierror errno={code!r} (not EAI_NONAME/EAI_NODATA) was memoised as "
        f"{memo_after_first!r}: a transient resolver failure now blacklists "
        f"{host!r} for 60 s for every user in the process"
    )
    assert second is True and stub.count(host) == 2, (
        "the next validation must re-resolve and succeed, got "
        f"second={second!r} after {stub.count(host)} resolve(s)"
    )


@pytest.mark.parametrize(
    "code",
    [EAI_AGAIN, EAI_FAIL, None],
    ids=["EAI_AGAIN", "EAI_FAIL", "errno-None"],
)
def test_red_transient_gaierror_is_not_memoised_sync_twin(monkeypatch, code):
    """RED today: the SYNC validator reads and writes the same memo under the
    flag, so the ruling covers it too (reviewer's ``sync3rd=False``)."""
    monkeypatch.setenv(FLAG, "true")
    stub = _install(monkeypatch)
    host = f"transient-sync-{str(code).lower()}-rw01a.example"
    stub.behaviour[host] = _transient_then_public(code)

    first = uv.validate_external_url(f"https://{host}/p")
    memo_after_first = uv._memo_get(host)
    second = uv.validate_external_url(f"https://{host}/q")

    assert first is False
    assert memo_after_first is None, (
        f"sync validator memoised gaierror errno={code!r} as {memo_after_first!r}"
    )
    assert second is True and stub.count(host) == 2


@pytest.mark.parametrize("code", _MEMOISED_CODES)
def test_pin_confirmed_negative_gaierror_is_still_memoised(monkeypatch, code):
    """PIN (green today): EAI_NONAME -- and EAI_NODATA where the platform has
    it -- is a CONFIRMED negative and keeps the P0's win: one resolve, then the
    memo serves False to BOTH validators."""
    monkeypatch.setenv(FLAG, "true")
    stub = _install(monkeypatch)
    host = f"nxdomain-{code}-rw01a.example"
    stub.behaviour[host] = _gai(code)

    first = asyncio.run(uv._validate_url_offloop_or_sync(f"https://{host}/a"))
    second = asyncio.run(uv._validate_url_offloop_or_sync(f"https://{host}/b"))
    third = uv.validate_external_url(f"https://{host}/c")

    assert (first, second, third) == (False, False, False)
    assert uv._memo_get(host) is False
    assert stub.count(host) == 1, (
        f"a confirmed NXDOMAIN must be resolved once, got {stub.count(host)}"
    )

    # ...and the sync twin writes it too.
    host2 = f"nxdomain-sync-{code}-rw01a.example"
    stub.behaviour[host2] = _gai(code)
    assert uv.validate_external_url(f"https://{host2}/a") is False
    assert uv._memo_get(host2) is False
    assert uv.validate_external_url(f"https://{host2}/b") is False
    assert stub.count(host2) == 1


def test_pin_private_address_is_still_memoised(monkeypatch):
    """PIN (green today): a private/reserved verdict is a confirmed negative."""
    monkeypatch.setenv(FLAG, "true")
    stub = _install(monkeypatch)
    host = "private-rw01a.example"
    stub.behaviour[host] = lambda: _PRIVATE
    assert asyncio.run(uv._validate_url_offloop_or_sync(f"http://{host}/")) is False
    assert asyncio.run(uv._validate_url_offloop_or_sync(f"http://{host}/")) is False
    assert uv._memo_get(host) is False and stub.count(host) == 1


@pytest.mark.parametrize(
    "code",
    [EAI_AGAIN, EAI_NONAME],
    ids=["EAI_AGAIN", "EAI_NONAME"],
)
def test_pin_flag_off_gaierror_path_is_base(monkeypatch, code):
    """PIN (green today), flag OFF: every call re-resolves on the caller's own
    thread through BOTH entry points, nothing is memoised, and a transient
    failure is followed by a success -- exactly base."""
    stub = _install(monkeypatch)
    host = f"flagoff-gai-{code}-rw01a.example"
    stub.behaviour[host] = _transient_then_public(code)
    caller = threading.current_thread().name

    first = asyncio.run(uv._validate_url_offloop_or_sync(f"https://{host}/p"))
    second = asyncio.run(uv._validate_url_offloop_or_sync(f"https://{host}/p"))
    third = uv.validate_external_url(f"https://{host}/q")

    assert (first, second, third) == (False, True, True)
    assert stub.count(host) == 3
    assert stub.threads == [caller, caller, caller], (
        f"flag OFF must resolve on the caller's thread, got {stub.threads!r}"
    )
    assert uv._DNS_MEMO == {}, f"flag OFF wrote the memo: {uv._DNS_MEMO!r}"


# ===========================================================================
# SHAPE B -- slow but SUCCESSFUL resolve (ruling 3)
# ===========================================================================


def test_red_slow_but_successful_resolve_leaves_no_negative_memo(monkeypatch):
    """RED today: a resolve that outruns the 0.3 s bound but then RETURNS A
    PUBLIC ADDRESS stays blacklisted for 60 s. The reviewer measured a 2.4 s
    resolve on a 2.0 s bound: flag ON 1st=False, 2nd=False with no second
    resolve, while base returned True twice.

    Contract: this call fails CLOSED (the bound is the bound), but once the
    zombie returns a public address no ``False`` remains in the memo and the
    next validation succeeds. The event loop is kept alive while the zombie
    finishes, so a completion callback hooked on either the concurrent or the
    asyncio future gets to run."""
    monkeypatch.setenv(FLAG, "true")
    monkeypatch.setenv(TIMEOUT_ENV, "0.3")
    pool = _private_pool(monkeypatch, 2)
    stub = _install(monkeypatch)
    host = "slow-ok-rw01b.example"
    zombie_done = threading.Event()

    def _slow_public():
        time.sleep(0.7)  # 0.4 s past the bound, then a healthy answer
        zombie_done.set()
        return _PUBLIC

    stub.behaviour[host] = _slow_public

    async def _drive():
        t0 = time.monotonic()
        first = await uv._validate_url_offloop_or_sync(f"https://{host}/p")
        elapsed = time.monotonic() - t0
        deadline = time.monotonic() + 10.0
        while not zombie_done.is_set() and time.monotonic() < deadline:
            await asyncio.sleep(0.02)
        await asyncio.sleep(0.2)  # let any completion callback run on this loop
        memo_after_zombie = uv._memo_get(host)
        stub.behaviour[host] = _public  # the resolver cache is warm now
        second = await uv._validate_url_offloop_or_sync(f"https://{host}/p")
        return first, elapsed, zombie_done.is_set(), memo_after_zombie, second

    try:
        first, elapsed, finished, memo_after_zombie, second = asyncio.run(_drive())
    finally:
        pool.shutdown(wait=False)

    assert first is False and elapsed < 0.3 + 0.5, (
        f"the first call must still be bounded and fail closed, got {first!r} "
        f"after {elapsed:.2f}s"
    )
    assert finished, "precondition: the zombie resolve must have returned"
    assert memo_after_zombie is not False, (
        f"{host!r} RESOLVED to a public address, yet the memo still holds a 60 s "
        "NEGATIVE verdict for it: a slow-but-healthy storefront is off the price "
        "path and the /url/* routes for a minute"
    )
    assert second is True, (
        f"after the zombie proved {host!r} resolves, the next validation must "
        f"succeed, got {second!r}"
    )


def test_pin_full_bound_timeout_is_still_memoised(monkeypatch):
    """PIN (green today): a resolve that starts at once and is still hung when
    the bound expires is the P0's black hole -- memoised, one resolve, and the
    second validation is served from the memo while the zombie is STILL hung
    (it never returned a public address)."""
    monkeypatch.setenv(FLAG, "true")
    monkeypatch.setenv(TIMEOUT_ENV, "0.3")
    pool = _private_pool(monkeypatch, 2)
    stub = _install(monkeypatch)
    host = "blackhole-rw01b.example"
    release = threading.Event()

    def _hang():
        release.wait(20.0)
        _gai(EAI_AGAIN)()  # what glibc reports when the resolver times out

    stub.behaviour[host] = _hang

    async def _drive():
        first = await uv._validate_url_offloop_or_sync(f"https://{host}/x")
        memo = uv._memo_get(host)
        second = await uv._validate_url_offloop_or_sync(f"https://{host}/y")
        return first, memo, second

    try:
        first, memo, second = asyncio.run(_drive())
    finally:
        release.set()
        pool.shutdown(wait=False)

    assert (first, second) == (False, False)
    assert memo is False, "a full-bound started timeout must be memoised"
    assert stub.count(host) == 1, (
        f"the second validation must come from the memo, got {stub.count(host)} "
        "resolves"
    )


def test_pin_flag_off_slow_success_is_base(monkeypatch):
    """PIN (green today), flag OFF: a slow resolve is NOT bounded (base has no
    bound), returns True on the caller's thread, and nothing is memoised."""
    monkeypatch.setenv(TIMEOUT_ENV, "0.1")  # must be ignored with the flag OFF
    stub = _install(monkeypatch)
    host = "flagoff-slow-rw01b.example"

    def _slow_public():
        time.sleep(0.4)
        return _PUBLIC

    stub.behaviour[host] = _slow_public
    caller = threading.current_thread().name

    t0 = time.monotonic()
    first = asyncio.run(uv._validate_url_offloop_or_sync(f"https://{host}/p"))
    elapsed = time.monotonic() - t0
    second = uv.validate_external_url(f"https://{host}/p")

    assert first is True and second is True
    assert elapsed >= 0.35, f"flag OFF must not bound the resolve ({elapsed:.2f}s)"
    assert stub.threads == [caller, caller]
    assert uv._DNS_MEMO == {}


# ===========================================================================
# SHAPE C -- queued, then STARTED just before the caller's deadline (ruling 2)
# ===========================================================================


def _start_near_deadline(monkeypatch, *, late_behaviour):
    """One-worker pool, bound T = 2.0 s. A blocker occupies the worker; a
    second validation (the "late" host) is queued behind it; the blocker is
    released at 0.8 T after the late call began, so the late resolve STARTS at
    ~0.8 T and has run only ~0.2 T (~0.4 s) when the caller's 2.0 s deadline
    fires. Returns the observations taken IMMEDIATELY after the late call
    returned, plus the stub and the release events."""
    T = 2.0
    monkeypatch.setenv(FLAG, "true")
    monkeypatch.setenv(TIMEOUT_ENV, str(T))
    pool = _private_pool(monkeypatch, 1)
    stub = _install(monkeypatch)
    blocker = "blocker-rw01c.example"
    late = "late-start-rw01c.example"
    release_blocker = threading.Event()
    stub.behaviour[blocker] = lambda: (release_blocker.wait(20.0), _gai(EAI_NONAME)())
    stub.behaviour[late] = late_behaviour

    async def _drive():
        parked = asyncio.create_task(
            uv._validate_url_offloop_or_sync(f"https://{blocker}/x")
        )
        await asyncio.sleep(0.1)  # the single worker is now parked on the blocker
        t_late = time.monotonic()
        timer = threading.Timer(0.8 * T, release_blocker.set)
        timer.start()
        verdict = await uv._validate_url_offloop_or_sync(f"https://{late}/p")
        returned_at = time.monotonic()
        memo_now = uv._memo_get(late)
        late_started = stub.started_at.get(late)
        await parked
        return verdict, t_late, returned_at, memo_now, late_started

    return T, pool, stub, late, release_blocker, _drive


def test_red_resolve_started_just_before_deadline_is_not_memoised(monkeypatch):
    """RED today: ``started.is_set()`` is not proof the host is slow. A job that
    waited in the queue and reached a worker just before the caller's deadline
    is memoised for 60 s after resolving for a fraction of the bound. The
    reviewer reproduced this at the DEFAULT pool of 16 (16 black-holed hosts +
    1 healthy store with a 0.35 s cold resolve -> healthy blacklisted).

    Contract (ruling 2): the start time is recorded inside ``_resolve``; a
    timeout is memoised only when the resolve itself ran for the bound. Here it
    ran ~0.4 s of a 2.0 s bound, so nothing may be written -- checked the
    moment the caller returns, while the late resolve is still in flight."""
    release_late = threading.Event()

    def _late_hangs():
        release_late.wait(20.0)
        return _PUBLIC

    T, pool, stub, late, release_blocker, drive = _start_near_deadline(
        monkeypatch, late_behaviour=_late_hangs
    )
    try:
        verdict, t_late, returned_at, memo_now, late_started = asyncio.run(drive())
    finally:
        release_blocker.set()
        release_late.set()
        pool.shutdown(wait=False)

    assert verdict is False, "the late call must still fail CLOSED at its bound"
    assert late_started is not None and late_started < returned_at, (
        "precondition: the late resolve must have STARTED before the caller's "
        "deadline (otherwise this is the queued-never-started case, already "
        "pinned by test_queued_but_never_started_resolve_is_not_memoized)"
    )
    ran_for = returned_at - late_started
    assert ran_for < 0.5 * T, (
        f"precondition: the late resolve must have run only a fraction of the "
        f"{T}s bound, but it ran {ran_for:.2f}s"
    )
    assert memo_now is None, (
        f"{late!r} was memoised as {memo_now!r} after its resolve ran only "
        f"{ran_for:.2f}s of the {T}s bound -- it spent the rest queued behind "
        "another host. That is queue contention, not a slow host, and it "
        "blacklists a healthy storefront for 60 s"
    )


def test_red_late_start_healthy_host_is_not_blacklisted(monkeypatch):
    """RED today -- the reviewer's exact shape (C): the late-started healthy
    resolve finishes 0.2 T after it started, AFTER its caller timed out. With
    the pool idle and the resolver instant, the host must validate True."""
    late_done = threading.Event()

    def _late_healthy():
        time.sleep(0.4)  # 0.2 T of real resolving
        late_done.set()
        return _PUBLIC

    T, pool, stub, late, release_blocker, drive = _start_near_deadline(
        monkeypatch, late_behaviour=_late_healthy
    )

    async def _drive_and_retry():
        verdict, _t_late, _ret, _memo_now, late_started = await drive()
        deadline = time.monotonic() + 10.0
        while not late_done.is_set() and time.monotonic() < deadline:
            await asyncio.sleep(0.02)
        await asyncio.sleep(0.2)
        memo_later = uv._memo_get(late)
        stub.behaviour[late] = _public
        retry = await uv._validate_url_offloop_or_sync(f"https://{late}/other")
        return verdict, late_started, memo_later, retry

    try:
        verdict, late_started, memo_later, retry = asyncio.run(_drive_and_retry())
    finally:
        release_blocker.set()
        pool.shutdown(wait=False)

    assert verdict is False
    assert late_started is not None, "precondition: the late resolve must start"
    assert late_done.is_set(), "precondition: the late resolve must finish"
    assert memo_later is not False, (
        f"healthy {late!r} is still memoised False after resolving to a public "
        "address -- a queue-contention event became a 60 s blacklist"
    )
    assert retry is True, (
        f"with the pool idle and the resolver instant, {late!r} must validate "
        f"True, got {retry!r}"
    )


def test_pin_flag_off_never_touches_pool_or_memo(monkeypatch):
    """PIN (green today), flag OFF, the queue shape: the helper's OFF branch
    runs the sync validator INLINE on the caller's thread. It never submits to
    the resolver pool (a pool that raises on submit is never reached), never
    READS the memo (a pre-seeded False is ignored and a public host validates
    True) and never WRITES it (a private host leaves no entry)."""

    class _ExplodingPool:
        def submit(self, *a, **k):  # pragma: no cover - reaching it is the failure
            raise AssertionError("flag OFF submitted to the DNS resolver pool")

    monkeypatch.setattr(uv, "_DNS_POOL", _ExplodingPool())
    stub = _install(monkeypatch)
    public_host = "flagoff-seeded-rw01c.example"
    private_host = "flagoff-private-rw01c.example"
    stub.behaviour[public_host] = _public
    stub.behaviour[private_host] = lambda: _PRIVATE
    uv._memo_put(public_host, False)  # seeded by an earlier flag-ON window
    caller = threading.current_thread().name

    ok = asyncio.run(uv._validate_url_offloop_or_sync(f"https://{public_host}/p"))
    blocked = asyncio.run(uv._validate_url_offloop_or_sync(f"http://{private_host}/"))

    assert ok is True, (
        "flag OFF read the memo: a seeded False short-circuited a public host"
    )
    assert blocked is False
    assert stub.calls == [public_host, private_host]
    assert stub.threads == [caller, caller], (
        f"flag OFF must resolve inline on the caller's thread, got {stub.threads!r}"
    )
    assert private_host not in uv._DNS_MEMO, "flag OFF wrote the memo"


# ===========================================================================
# GREEN-phase pins: the W0-1b done-callback (ruling 3) -- it DROPS a False
# memo once a zombie resolve returns an allowed address, and it never writes
# True (tests/test_url_validator_offloop.py::test_positive_result_is_not_memoized
# is the DNS-rebinding contract).
# ===========================================================================


def _drive_zombie(host, stub, *, answer, zombie_s, timeout_s, then=None):
    """First call times out on a resolve that STARTED at once (so the 0.75
    rule memoises it); the zombie then returns ``answer``. Returns the first
    verdict, the memo right after it, the memo once the zombie returned (+0.3 s
    for its callback), and the optional follow-up verdict."""
    zombie_done = threading.Event()

    def _zombie():
        time.sleep(zombie_s)
        zombie_done.set()
        return answer

    stub.behaviour[host] = _zombie

    async def _drive():
        first = await uv._validate_url_offloop_or_sync(f"https://{host}/p")
        memo_first = uv._DNS_MEMO.get(host)
        deadline = time.monotonic() + 10.0
        while not zombie_done.is_set() and time.monotonic() < deadline:
            await asyncio.sleep(0.02)
        await asyncio.sleep(0.3)
        memo_after = uv._DNS_MEMO.get(host)
        follow = None
        if then is not None:
            stub.behaviour[host] = then
            follow = await uv._validate_url_offloop_or_sync(f"https://{host}/q")
        return first, memo_first, zombie_done.is_set(), memo_after, follow

    return asyncio.run(_drive())


def test_pin_zombie_success_clears_but_never_writes_a_positive_memo(monkeypatch):
    """PIN: the zombie proves the host resolves publicly, so the False entry is
    REMOVED -- not replaced by True. A host that then rebinds to a private
    address must be re-resolved and blocked, never served a stale True."""
    monkeypatch.setenv(FLAG, "true")
    monkeypatch.setenv(TIMEOUT_ENV, "0.3")
    pool = _private_pool(monkeypatch, 2)
    stub = _install(monkeypatch)
    host = "zombie-clear-rw01g.example"
    try:
        first, memo_first, finished, memo_after, follow = _drive_zombie(
            host, stub, answer=_PUBLIC, zombie_s=1.2, timeout_s=0.3,
            then=lambda: _PRIVATE,
        )
    finally:
        pool.shutdown(wait=False)

    assert first is False
    assert memo_first is not None and memo_first[1] is False, (
        f"precondition: a full-bound timeout must be memoised, got {memo_first!r}"
    )
    assert finished, "precondition: the zombie resolve must have returned"
    assert memo_after is None, (
        f"the zombie's public answer must DROP the entry, not rewrite it; the "
        f"memo holds {memo_after!r} (a True here is a 60 s DNS-rebinding window)"
    )
    assert follow is False, "a rebinding host must be re-resolved and blocked"
    assert stub.count(host) == 2


def test_pin_zombie_private_answer_keeps_the_negative(monkeypatch):
    """PIN: a zombie that returns a PRIVATE address confirms the negative; the
    callback must not drop it, and the next call is served from the memo."""
    monkeypatch.setenv(FLAG, "true")
    monkeypatch.setenv(TIMEOUT_ENV, "0.3")
    pool = _private_pool(monkeypatch, 2)
    stub = _install(monkeypatch)
    host = "zombie-private-rw01g.example"
    try:
        first, memo_first, finished, memo_after, follow = _drive_zombie(
            host, stub, answer=_PRIVATE, zombie_s=1.2, timeout_s=0.3,
            then=_public,
        )
    finally:
        pool.shutdown(wait=False)

    assert first is False and finished
    assert memo_first is not None and memo_first[1] is False
    assert memo_after is not None and memo_after[1] is False, (
        f"a private zombie answer must keep the negative, memo={memo_after!r}"
    )
    assert follow is False and stub.count(host) == 1, (
        "the second call must be served from the memo"
    )


def test_pin_negative_written_after_the_zombie_returned_is_still_dropped(monkeypatch):
    """PIN (the late re-check): the zombie can return between the caller's
    deadline and its memo write. Its callback then finds no entry to drop, so
    the caller must re-check the finished future right after writing. Forced
    deterministically by delaying the memo write until the zombie (and its
    callback) have finished."""
    monkeypatch.setenv(FLAG, "true")
    monkeypatch.setenv(TIMEOUT_ENV, "0.3")
    pool = _private_pool(monkeypatch, 2)
    stub = _install(monkeypatch)
    host = "zombie-race-rw01g.example"
    zombie_done = threading.Event()
    wrote = []

    def _zombie():
        time.sleep(0.5)
        zombie_done.set()
        return _PUBLIC

    stub.behaviour[host] = _zombie
    real_put = uv._memo_put

    def _late_put(h, r):
        zombie_done.wait(10.0)
        time.sleep(0.3)  # the zombie's callback has run and found nothing
        wrote.append((h, r))
        real_put(h, r)

    monkeypatch.setattr(uv, "_memo_put", _late_put)
    try:
        first = asyncio.run(uv._validate_url_offloop_or_sync(f"https://{host}/p"))
    finally:
        pool.shutdown(wait=False)

    assert first is False
    assert wrote == [(host, False)], f"precondition: the timeout was memoised: {wrote!r}"
    assert host not in uv._DNS_MEMO, (
        f"the zombie had already returned a public address, yet {host!r} is "
        f"memoised {uv._DNS_MEMO.get(host)!r}: the late re-check is missing"
    )


def test_pin_flag_off_direct_async_call_never_drops_a_memo_entry(monkeypatch):
    """PIN: with the flag OFF even a DIRECT call of the async validator must not
    touch the memo -- no done-callback is attached, so a zombie's public answer
    leaves a pre-existing entry exactly as it was."""
    monkeypatch.setenv(TIMEOUT_ENV, "0.3")
    pool = _private_pool(monkeypatch, 2)
    stub = _install(monkeypatch)
    host = "flagoff-direct-rw01g.example"
    zombie_done = threading.Event()

    def _zombie():
        time.sleep(0.6)
        zombie_done.set()
        return _PUBLIC

    stub.behaviour[host] = _zombie
    uv._memo_put(host, False)
    seeded = uv._DNS_MEMO[host]

    async def _drive():
        verdict = await uv.validate_external_url_async(f"https://{host}/p")
        deadline = time.monotonic() + 10.0
        while not zombie_done.is_set() and time.monotonic() < deadline:
            await asyncio.sleep(0.02)
        await asyncio.sleep(0.3)
        return verdict

    try:
        verdict = asyncio.run(_drive())
    finally:
        pool.shutdown(wait=False)

    assert verdict is False and zombie_done.is_set()
    assert uv._DNS_MEMO.get(host) == seeded, (
        "flag OFF: the async validator touched the memo through its done-callback"
    )


# ===========================================================================
# FIXER-phase pins (R-W0 retro adversary round 2): the defect it reproduced
# and the surviving mutants N1/N2/N3/N5/N6/N13/N14/N15, each folded into a pin.
# ===========================================================================


def test_pin_zombie_empty_answer_keeps_the_negative(monkeypatch):
    """PIN (adversary defect 1): a zombie resolve that returns an EMPTY
    ``addr_infos`` list proves nothing about the host -- ``_addr_infos_allowed([])``
    is vacuously True (a pre-existing gap in the validators, out of scope), but
    the done-callback must not treat "no addresses" as "resolves publicly" and
    drop a genuine full-bound timeout negative."""
    monkeypatch.setenv(FLAG, "true")
    monkeypatch.setenv(TIMEOUT_ENV, "0.3")
    pool = _private_pool(monkeypatch, 2)
    stub = _install(monkeypatch)
    host = "zombie-empty-rw01h.example"
    try:
        first, memo_first, finished, memo_after, _ = _drive_zombie(
            host, stub, answer=[], zombie_s=0.8, timeout_s=0.3,
        )
    finally:
        pool.shutdown(wait=False)

    assert first is False and finished
    assert memo_first is not None and memo_first[1] is False, (
        f"precondition: a full-bound timeout must be memoised, got {memo_first!r}"
    )
    assert memo_after is not None and memo_after[1] is False, (
        f"an EMPTY zombie answer dropped the timeout negative: memo={memo_after!r}"
    )


class _SplitClock:
    """A deterministic stand-in for ``uv.time`` (only ``monotonic`` is read).

    * A resolver-pool thread (``dns-resolve*``) always reads ``BASE + offset``:
      that is the ``started_at`` stamp ``_resolve`` records.
    * The loop thread reads ``BASE`` until 0.9 T of REAL time has passed, then
      ``BASE + 10 T``. The deadline (taken right after submit, at ~0 real time)
      is therefore exactly ``BASE + T``; anything the except branch reads AFTER
      the real bound fired is 10 T later -- a loop that lagged far past the
      deadline. So ``ran`` measured at the deadline is exactly
      ``T - offset``, while ``ran`` measured at the except branch would be
      ``10 T - offset``.

    Every value is exactly representable in binary (BASE 1000.0, T 1.0,
    offsets in 1/2**20 steps), so ``0.75 * T`` is hit exactly, not
    approximately."""

    BASE = 1000.0

    def __init__(self, timeout: float, worker_offset: float) -> None:
        self._worker = self.BASE + worker_offset
        self._late = self.BASE + 10.0 * timeout
        self._late_after = 0.9 * timeout
        self._real0 = time.monotonic()
        self.worker_reads = 0

    def monotonic(self) -> float:
        if threading.current_thread().name.startswith("dns-resolve"):
            self.worker_reads += 1
            return self._worker
        if time.monotonic() - self._real0 >= self._late_after:
            return self._late
        return self.BASE


@pytest.mark.parametrize(
    "worker_offset, memoised",
    [
        (0.25, True),             # ran exactly 0.75 T by the deadline (>= binds)
        (0.25 + 2 ** -20, False),  # a hair under 0.75 T
        (0.40, False),            # 0.60 T -- would memoise at a 0.5 fraction
        (0.15, True),             # 0.85 T -- would NOT memoise at a 0.95 fraction
    ],
    ids=["exactly-0.75T", "just-under-0.75T", "0.60T", "0.85T"],
)
def test_pin_run_fraction_is_three_quarters_measured_at_the_deadline(
    monkeypatch, worker_offset, memoised
):
    """PIN (surviving mutants N1 0.5, N2 0.95, N15 '>' and N3 'ran measured at
    the except branch'): ruling 2 memoises a started timeout only when the
    resolve had run >= 0.75 x the bound BY THE CALLER'S DEADLINE. The clock is
    split per thread (``_SplitClock``) so the run fraction is exact and the
    except branch runs "10 T late" -- a lagging loop must not inflate how long
    the resolve ran (the conservative choice the green recorded)."""
    T = 1.0
    monkeypatch.setenv(FLAG, "true")
    monkeypatch.setenv(TIMEOUT_ENV, str(T))
    pool = _private_pool(monkeypatch, 2)
    stub = _install(monkeypatch)
    host = f"run-fraction-{worker_offset!r}-rw01i.example".replace("+", "p")
    release = threading.Event()

    def _hang():
        release.wait(20.0)
        _gai(EAI_AGAIN)()  # the zombie FAILS, so its callback drops nothing

    stub.behaviour[host] = _hang
    clock = _SplitClock(T, worker_offset)
    monkeypatch.setattr(uv, "time", clock)
    try:
        verdict = asyncio.run(uv._validate_url_offloop_or_sync(f"https://{host}/p"))
        entry = uv._DNS_MEMO.get(host)
    finally:
        release.set()
        pool.shutdown(wait=False)

    assert verdict is False, "a timed-out resolve must fail CLOSED"
    assert clock.worker_reads == 1, (
        f"precondition: the resolve must have started exactly once "
        f"(worker clock reads: {clock.worker_reads})"
    )
    ran = T - worker_offset
    if memoised:
        assert entry is not None and entry[1] is False, (
            f"the resolve ran {ran!r} s of a {T} s bound (>= 0.75 T) by the "
            f"deadline and must be memoised, got {entry!r}"
        )
    else:
        assert entry is None, (
            f"the resolve ran only {ran!r} s of a {T} s bound (< 0.75 T) by the "
            f"deadline -- measuring at the late except branch, or a fraction "
            f"other than 0.75, memoised it as {entry!r}"
        )


def test_pin_callback_treats_a_cancelled_resolve_as_a_normal_outcome(caplog):
    """PIN (surviving mutant N6, the ``fut.cancelled()`` guard): a queued
    resolve that ``wait_for`` cancelled is a normal outcome, not a callback
    failure. ``concurrent.futures.CancelledError`` is an ``Exception`` on 3.12,
    so without the guard ``fut.exception()`` raises into the callback's
    catch-all and every cancelled queue entry logs "done-callback failed".
    The positive control proves the capture sees that logger at all."""
    import concurrent.futures
    import logging

    host = "cancelled-rw01j.example"
    uv._memo_put(host, False)
    seeded = uv._DNS_MEMO[host]

    broken = concurrent.futures.Future()
    broken.set_result(42)  # not iterable: _addr_infos_allowed raises
    with caplog.at_level(logging.DEBUG, logger=uv.logger.name):
        uv._clear_negative_if_resolved_public(broken, host)
    assert any(
        "done-callback failed" in r.getMessage() for r in caplog.records
    ), "positive control: a genuinely failing callback must be logged"
    assert uv._DNS_MEMO.get(host) == seeded
    caplog.clear()

    cancelled = concurrent.futures.Future()
    assert cancelled.cancel()
    with caplog.at_level(logging.DEBUG, logger=uv.logger.name):
        uv._clear_negative_if_resolved_public(cancelled, host)
    failures = [r.getMessage() for r in caplog.records if "done-callback failed" in r.getMessage()]
    assert failures == [], f"a cancelled resolve was logged as a failure: {failures!r}"
    assert uv._DNS_MEMO.get(host) == seeded, "a cancelled resolve changed the memo"


_DISTINCT_NODATA = 424242  # collides with no EAI_* constant on any platform


@pytest.mark.parametrize("which", ["EAI_NONAME", "EAI_NODATA"])
def test_pin_each_confirmed_code_is_memoised_on_its_own(monkeypatch, which):
    """PIN (surviving mutants N5 / N14): on Windows ``EAI_NODATA == EAI_NONAME
    == 11001``, so dropping either from the confirmed set was invisible there.
    ``EAI_NODATA`` is re-pointed at a distinct value (the helper reads the
    ``socket`` constants at CALL time), so each code must be memoised on its
    own, by both validators, on every platform."""
    monkeypatch.setattr(socket, "EAI_NODATA", _DISTINCT_NODATA, raising=False)
    assert socket.EAI_NONAME != socket.EAI_NODATA
    code = socket.EAI_NONAME if which == "EAI_NONAME" else _DISTINCT_NODATA
    monkeypatch.setenv(FLAG, "true")
    stub = _install(monkeypatch)

    host = f"confirmed-{which.lower()}-rw01k.example"
    stub.behaviour[host] = _gai(code)
    assert asyncio.run(uv._validate_url_offloop_or_sync(f"https://{host}/a")) is False
    assert uv._memo_get(host) is False, f"async: {which} was not memoised"
    assert asyncio.run(uv._validate_url_offloop_or_sync(f"https://{host}/b")) is False
    assert stub.count(host) == 1

    host2 = f"confirmed-sync-{which.lower()}-rw01k.example"
    stub.behaviour[host2] = _gai(code)
    assert uv.validate_external_url(f"https://{host2}/a") is False
    assert uv._memo_get(host2) is False, f"sync: {which} was not memoised"
    assert uv.validate_external_url(f"https://{host2}/b") is False
    assert stub.count(host2) == 1


def test_pin_platform_without_eai_nodata_still_memoises_noname(monkeypatch):
    """PIN: a platform whose ``socket`` has no ``EAI_NODATA`` still memoises
    ``EAI_NONAME`` and still refuses ``EAI_AGAIN`` (the helper must not raise
    on the missing constant -- a raise would be swallowed by the validator as
    a fail-closed call with nothing memoised)."""
    monkeypatch.delattr(socket, "EAI_NODATA", raising=False)
    assert not hasattr(socket, "EAI_NODATA")
    monkeypatch.setenv(FLAG, "true")
    stub = _install(monkeypatch)
    nx = "nodata-absent-nx-rw01k.example"
    again = "nodata-absent-again-rw01k.example"
    stub.behaviour[nx] = _gai(EAI_NONAME)
    stub.behaviour[again] = _gai(EAI_AGAIN)

    assert asyncio.run(uv._validate_url_offloop_or_sync(f"https://{nx}/")) is False
    assert uv.validate_external_url(f"https://{again}/") is False
    assert uv._memo_get(nx) is False
    assert uv._memo_get(again) is None


def test_pin_sync_validator_memoises_a_private_address_under_the_flag(monkeypatch):
    """PIN (surviving mutant N13, pre-existing code): the SYNC validator's own
    private-address memo write (``if memoise and not allowed``) had no pin --
    test_pin_private_address_is_still_memoised drives only the async path."""
    monkeypatch.setenv(FLAG, "true")
    stub = _install(monkeypatch)
    host = "private-sync-rw01l.example"
    stub.behaviour[host] = lambda: _PRIVATE

    assert uv.validate_external_url(f"http://{host}/") is False
    assert uv._memo_get(host) is False, "the sync validator did not memoise a private answer"
    assert uv.validate_external_url(f"http://{host}/x") is False
    assert stub.count(host) == 1
