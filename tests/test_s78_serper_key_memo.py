"""S78-SM: in-process memo of the Serper exhausted-key flag.

Unit S78-SM (rulings SM1-SM6 + SM-ADV-1..9). The memo lives in
``serper_service._is_serper_key_exhausted`` behind ENABLE_SERPER_KEY_STATE_MEMO
(default OFF, read per call) with the TTL knob SERPER_KEY_STATE_MEMO_TTL
(default 60.0 s; unset / unparsable / non-finite / <= 0 -> 60.0).

Row ids follow the spec's section 4 table:
  r*  RED rows: fail at base (no memo) on an AssertionError, pass after GREEN.
  p*  PIN rows: pass at base and after GREEN (identity / mutation-kill pins).

Credential-free: fake key literals only (no real key, no sk- shape), a
recording fake Redis installed as cache_service.redis_client, httpx faked, no
network. The flag-OFF golden ``fixtures/s78_sm_flag_off_redis_sequence.json``
was recorded at base e0f3e475 and is never regenerated at HEAD.
"""
import json
import os
import threading

import pytest
from unittest.mock import MagicMock, patch

from app.services import serper_service
import app.services.cache_service as cache_service

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "s78_sm_flag_off_redis_sequence.json")
FLAG = "ENABLE_SERPER_KEY_STATE_MEMO"
KNOB = "SERPER_KEY_STATE_MEMO_TTL"
K1, K2, K3 = "aaaaaaaa1", "bbbbbbbb2", "cccccccc3"
SOLO = "solokey99"
F1, F2 = "serper:exhausted:aaaaaaaa", "serper:exhausted:bbbbbbbb"
CREDITS = '{"message":"Not enough credits"}'

# Env that changes the Serper call graph or the record_usage scoping (SM-ADV-6).
_HYGIENE_ENV = (
    FLAG, KNOB, "SERPER_API_KEYS", "SERPER_API_KEY", "ENABLE_ASYNC_REDIS_OFFLOAD",
    "ENABLE_SERPER_BREAKER", "ENABLE_SERPER_FAIL_FAST", "SERPER_SHOPPING_PRIMARY_COUNTRIES",
    "SERPER_ROTATION_DEADLINE", "ENABLE_BRIGHTDATA_FALLBACK", "SERPER_LIFETIME_LIMIT",
)


def _need(name):
    """The new symbol, or an AssertionError naming it (the base state)."""
    assert hasattr(serper_service, name), (
        "S78-SM: serper_service.%s is missing (memo not implemented)" % name)
    return getattr(serper_service, name)


class RecRedis:
    """Recording fake of the sync Upstash client (only the verbs the path uses)."""

    def __init__(self):
        self.store = {}
        self.calls = []
        self.on_get = None
        self.on_setex = None
        self.get_raises = False
        self.setex_raises = False

    def get(self, key):
        self.calls.append(("get", key))
        value = self.store.get(key)  # the server answered before any concurrent SET
        if self.on_get:
            self.on_get(key)
        if self.get_raises:
            raise RuntimeError("redis down")
        return value

    def setex(self, key, ttl, value):
        self.calls.append(("setex", key, ttl, value))
        if self.on_setex:
            self.on_setex(key)
        if self.setex_raises:
            raise RuntimeError("redis down")
        self.store[key] = value

    def set(self, key, value):
        self.calls.append(("set", key, value))
        self.store[key] = value

    def incrby(self, key, n):
        self.calls.append(("incrby", key, n))
        self.store[key] = int(self.store.get(key) or 0) + n
        return self.store[key]

    def incr(self, key):
        return self.incrby(key, 1)

    def expire(self, key, s):
        self.calls.append(("expire", key, s))

    def gets(self, key=None):
        return [c for c in self.calls if c[0] == "get" and (key is None or c[1] == key)]


class Clock:
    def __init__(self):
        self.t = 1000.0

    def monotonic(self):
        return self.t


def _reset():
    serper_service._serper_exhausted_logged.clear()
    serper_service.reset_serper_budget_cache()
    r = getattr(serper_service, "_reset_serper_key_state_memo", None)
    if r:
        r()


@pytest.fixture
def clean(monkeypatch):
    for n in _HYGIENE_ENV:
        monkeypatch.delenv(n, raising=False)
    monkeypatch.setattr(serper_service, "SERPER_API_KEY", SOLO)
    _reset()
    yield
    _reset()


@pytest.fixture
def rec(clean, monkeypatch):
    r = RecRedis()
    monkeypatch.setattr(cache_service, "redis_client", r)
    return r


@pytest.fixture
def clock(monkeypatch):
    c = Clock()
    monkeypatch.setattr(serper_service, "_time", c)
    return c


def _resp(status=200, text=""):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = {"organic": [], "shopping": [{"title": "x"}]}
    r.text = text
    r.raise_for_status = MagicMock()
    r.headers = {}
    return r


def _client(statuses):
    st = {"n": 0, "keys": []}

    class _C:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, *a, **k):
            st["keys"].append(k["headers"]["X-API-KEY"])
            s = statuses[min(st["n"], len(statuses) - 1)]
            st["n"] += 1
            return _resp(s, CREDITS if s == 400 else "")

    return patch("app.services.serper_service.httpx.AsyncClient", _C), st


# ---------------------------------------------------------------- SM1 flag reader
@pytest.mark.parametrize("raw,want", [
    (None, False), ("", False), ("true", True), ("TRUE", True), (" true ", True),
    ("1", True), ("yes", True), ("on", True), ("ON", True), (" On\t", True),
    ("false", False), ("0", False), ("off", False), ("no", False), ("enabled", False),
])
def test_r1_flag_reader_table(monkeypatch, raw, want):
    fn = _need("_serper_key_state_memo_enabled")
    if raw is None:
        monkeypatch.delenv(FLAG, raising=False)
    else:
        monkeypatch.setenv(FLAG, raw)
    assert fn() is want


# ---------------------------------------------------------------- SM2 TTL knob
@pytest.mark.parametrize("raw,want", [
    (None, 60.0), ("", 60.0), ("30", 30.0), (" 5 ", 5.0), ("0.5", 0.5), ("120", 120.0),
    ("0", 60.0), ("0.0", 60.0), ("-1", 60.0), ("-0.5", 60.0), ("inf", 60.0),
    ("-inf", 60.0), ("nan", 60.0), ("1e400", 60.0), ("garbage", 60.0), ("60s", 60.0),
])
def test_r2_ttl_knob_table(monkeypatch, raw, want):
    fn = _need("_serper_key_state_memo_ttl")
    if raw is None:
        monkeypatch.delenv(KNOB, raising=False)
    else:
        monkeypatch.setenv(KNOB, raw)
    got = fn()
    assert isinstance(got, float) and got == want


# ---------------------------------------------------------------- SM4 flag-OFF identity
SCEN = {
    "single": (None, [], [200]),
    "multi2_none": (f"{K1},{K2}", [], [200]),
    "multi2_k1flagged": (f"{K1},{K2}", [F1], [200]),
    "multi3_k1flagged": (f"{K1},{K2},{K3}", [F1], [200]),
    "multi2_k1depletes": (f"{K1},{K2}", [], [400, 200]),
}
ENTRIES = ("search_web", "search_product_prices", "search_images", "search_videos",
           "search_news", "search_price_organic")


async def _run_matrix(rec, monkeypatch):
    """5 key modes x 6 entry points x 3 consecutive calls: the full ordered Redis
    call list (with arguments and TTLs) and the X-API-KEY of every POST."""
    out = {}
    for scen, (keys, flagged, statuses) in SCEN.items():
        for entry in ENTRIES:
            rec.store.clear()
            rec.calls.clear()
            _reset()
            if keys:
                monkeypatch.setenv("SERPER_API_KEYS", keys)
            else:
                monkeypatch.delenv("SERPER_API_KEYS", raising=False)
            for f in flagged:
                rec.store[f] = "1"
            posted = []
            for i in range(3):
                ctx, st = _client(statuses if i == 0 else [200])
                with ctx:
                    fn = getattr(serper_service, entry)
                    if entry in ("search_product_prices", "search_price_organic"):
                        await fn("Thing", "bh")
                    else:
                        await fn("Thing")
                posted.append(st["keys"])
            out[f"{scen}|{entry}"] = {"redis": [list(c) for c in rec.calls], "posts": posted}
    return out


def _golden():
    with open(FIXTURE, encoding="utf-8") as fh:
        return json.load(fh)


@pytest.mark.asyncio
async def test_p3_flag_off_redis_sequence_identity(rec, monkeypatch):
    want = _golden()
    assert len(want) == 30
    assert await _run_matrix(rec, monkeypatch) == want


@pytest.mark.asyncio
async def test_p3b_flag_off_explicit_false_values_identical(rec, monkeypatch):
    want = _golden()
    for v in ("false", "0", "off", ""):
        monkeypatch.setenv(FLAG, v)
        assert await _run_matrix(rec, monkeypatch) == want, v


def test_r3c_flag_off_never_writes_the_memo(rec, monkeypatch):
    memo = _need("_serper_key_state_memo")
    monkeypatch.setenv("SERPER_API_KEYS", f"{K1},{K2}")
    for _ in range(3):
        serper_service._is_serper_key_exhausted(K1)
        serper_service._active_serper_key()
    assert memo == {}
    assert len(rec.gets(F1)) == 3 + 3


def test_r3d_flag_off_ignores_a_seeded_memo(rec, monkeypatch):
    memo = _need("_serper_key_state_memo")
    monkeypatch.setitem(memo, F1, (float("inf"), True))
    assert serper_service._is_serper_key_exhausted(K1) is False
    assert len(rec.gets(F1)) == 1


# ---------------------------------------------------------------- SM3 ON: one GET per key per window
def test_r4_on_one_get_per_key_per_window(rec, monkeypatch, clock):
    monkeypatch.setenv(FLAG, "true")
    for dt in (0.0, 1.0, 30.0, 59.9):
        clock.t = 1000.0 + dt
        assert serper_service._is_serper_key_exhausted(K1) is False
    assert len(rec.gets(F1)) == 1


def test_r4b_on_memo_caches_true_too(rec, monkeypatch, clock):
    monkeypatch.setenv(FLAG, "true")
    rec.store[F1] = "1"
    for _ in range(4):
        assert serper_service._is_serper_key_exhausted(K1) is True
    assert len(rec.gets(F1)) == 1


def test_r4c_on_keyed_by_the_8_char_prefix(rec, monkeypatch, clock):
    monkeypatch.setenv(FLAG, "true")
    serper_service._is_serper_key_exhausted("aaaaaaaaX")
    serper_service._is_serper_key_exhausted("aaaaaaaaY")
    serper_service._is_serper_key_exhausted(K2)
    assert len(rec.gets(F1)) == 1 and len(rec.gets(F2)) == 1


@pytest.mark.asyncio
async def test_r4d_on_search_web_steady_state(rec, monkeypatch, clock):
    monkeypatch.setenv(FLAG, "true")
    monkeypatch.setenv("SERPER_API_KEYS", f"{K1},{K2}")
    rec.store[F1] = "1"
    for i in range(3):
        if i == 2:
            rec.calls.clear()
        ctx, st = _client([200])
        with ctx:
            await serper_service.search_web("q")
        assert st["keys"] == [K2]
    # call 3: serper_service reads nothing; the two residual GETs are
    # api_budget_service._serper_key_prefix() inside record_usage (L1, out of scope).
    assert [c[1] for c in rec.gets()] == [F1, F2]


def test_r4e_single_key_mode_still_reads_nothing(rec, monkeypatch, clock):
    monkeypatch.setenv(FLAG, "true")
    assert serper_service._active_serper_key() == SOLO
    assert rec.gets() == []


# ---------------------------------------------------------------- SM3 ON: a mark inside the window
def test_p5_on_mark_inside_window_honoured(rec, monkeypatch, clock):
    monkeypatch.setenv(FLAG, "true")
    assert serper_service._is_serper_key_exhausted(K1) is False
    serper_service._mark_serper_key_exhausted(K1)
    clock.t += 1.0
    assert serper_service._is_serper_key_exhausted(K1) is True
    assert len(rec.gets(F1)) == 2


@pytest.mark.asyncio
async def test_p5b_on_rotation_after_depletion(rec, monkeypatch, clock):
    monkeypatch.setenv(FLAG, "true")
    monkeypatch.setenv("SERPER_API_KEYS", f"{K1},{K2}")
    ctx, st = _client([400, 200])
    with ctx:
        await serper_service.search_web("q")
    assert st["keys"] == [K1, K2]
    ctx, st = _client([200])
    with ctx:
        await serper_service.search_web("q")
    assert st["keys"] == [K2]


def test_p5c_on_mark_with_redis_set_failing_is_fail_open(rec, monkeypatch, clock):
    monkeypatch.setenv(FLAG, "true")
    assert serper_service._is_serper_key_exhausted(K1) is False
    rec.setex_raises = True
    serper_service._mark_serper_key_exhausted(K1)
    assert serper_service._is_serper_key_exhausted(K1) is False
    assert len(rec.gets(F1)) == 2


def test_p5d_mark_invalidates_even_with_flag_off(rec, monkeypatch, clock):
    monkeypatch.setenv(FLAG, "true")
    assert serper_service._is_serper_key_exhausted(K1) is False
    monkeypatch.setenv(FLAG, "false")
    serper_service._mark_serper_key_exhausted(K1)
    monkeypatch.setenv(FLAG, "true")
    assert serper_service._is_serper_key_exhausted(K1) is True


def test_p5e_invalidate_after_the_set(rec, monkeypatch, clock):
    """A reader landing while the SET is in flight must not leave a stale False."""
    monkeypatch.setenv(FLAG, "true")
    assert serper_service._is_serper_key_exhausted(K1) is False
    rec.on_setex = lambda key: serper_service._is_serper_key_exhausted(K1)
    serper_service._mark_serper_key_exhausted(K1)
    rec.on_setex = None
    assert serper_service._is_serper_key_exhausted(K1) is True


def test_p5f_mark_during_the_read_is_not_overwritten(rec, monkeypatch, clock):
    """Generation guard: a mark that lands between the GET and the store. The
    mark runs in a helper thread joined with a timeout, so a lock wrongly held
    across the GET (mutant M13) costs seconds, never a deadlock."""
    monkeypatch.setenv(FLAG, "true")
    threads = []

    def mark_once(key):
        rec.on_get = None
        t = threading.Thread(target=serper_service._mark_serper_key_exhausted, args=(K1,))
        threads.append(t)
        t.start()
        t.join(timeout=5)

    rec.on_get = mark_once
    serper_service._is_serper_key_exhausted(K1)
    for t in threads:
        t.join(timeout=5)
    assert threads and not any(t.is_alive() for t in threads)
    assert serper_service._is_serper_key_exhausted(K1) is True


# ---------------------------------------------------------------- SM3 ON: expiry
def test_r6_on_expired_window_rereads(rec, monkeypatch, clock):
    monkeypatch.setenv(FLAG, "true")
    serper_service._is_serper_key_exhausted(K1)
    clock.t = 1059.9
    serper_service._is_serper_key_exhausted(K1)
    assert len(rec.gets(F1)) == 1
    rec.store[F1] = "1"
    clock.t = 1060.0
    assert serper_service._is_serper_key_exhausted(K1) is True
    assert len(rec.gets(F1)) == 2
    clock.t = 1060.1
    assert serper_service._is_serper_key_exhausted(K1) is True
    assert len(rec.gets(F1)) == 2


def test_r6b_on_knob_read_per_call(rec, monkeypatch, clock):
    monkeypatch.setenv(FLAG, "true")
    monkeypatch.setenv(KNOB, "5")
    serper_service._is_serper_key_exhausted(K1)
    clock.t = 1005.0
    serper_service._is_serper_key_exhausted(K1)
    assert len(rec.gets(F1)) == 2
    monkeypatch.setenv(KNOB, "100")
    clock.t = 1010.0
    serper_service._is_serper_key_exhausted(K1)
    assert len(rec.gets(F1)) == 3
    clock.t = 1109.9
    serper_service._is_serper_key_exhausted(K1)
    assert len(rec.gets(F1)) == 3


@pytest.mark.parametrize("bad", ["0", "-1", "nan", "inf", "junk"])
def test_r6c_on_invalid_knob_means_60(rec, monkeypatch, clock, bad):
    monkeypatch.setenv(FLAG, "true")
    monkeypatch.setenv(KNOB, bad)
    serper_service._is_serper_key_exhausted(K1)
    clock.t = 1059.0
    serper_service._is_serper_key_exhausted(K1)
    clock.t = 1060.0
    serper_service._is_serper_key_exhausted(K1)
    assert len(rec.gets(F1)) == 2


def test_r6d_on_window_starts_at_the_clock_read_before_the_get(rec, monkeypatch, clock):
    """SM-ADV-5: the clock is read BEFORE the GET, so a slow GET (30 s here) does
    not extend the window: expiry = t_before_get + 60."""
    monkeypatch.setenv(FLAG, "true")

    def slow(key):
        clock.t += 30.0

    rec.on_get = slow
    serper_service._is_serper_key_exhausted(K1)  # GET starts at 1000.0, returns at 1030.0
    rec.on_get = None
    clock.t = 1059.9
    serper_service._is_serper_key_exhausted(K1)
    assert len(rec.gets(F1)) == 1
    clock.t = 1060.0
    serper_service._is_serper_key_exhausted(K1)
    assert len(rec.gets(F1)) == 2


# ---------------------------------------------------------------- SM5 Redis down / error
@pytest.mark.parametrize("flag", ["false", "true"])
def test_p7_redis_client_none_fail_open(clean, monkeypatch, flag):
    monkeypatch.setattr(cache_service, "redis_client", None)
    monkeypatch.setenv(FLAG, flag)
    monkeypatch.setenv("SERPER_API_KEYS", f"{K1},{K2}")
    assert serper_service._is_serper_key_exhausted(K1) is False
    assert serper_service._active_serper_key() == K1


@pytest.mark.parametrize("flag", ["false", "true"])
def test_p7b_redis_get_error_fail_open(rec, monkeypatch, flag):
    monkeypatch.setenv(FLAG, flag)
    monkeypatch.setenv("SERPER_API_KEYS", f"{K1},{K2}")
    rec.get_raises = True
    assert serper_service._is_serper_key_exhausted(K1) is False
    assert serper_service._active_serper_key() == K1


@pytest.mark.parametrize("flag", ["false", "true"])
def test_p7c_helper_raising_is_fail_open_and_not_memoised(rec, monkeypatch, flag, clock):
    monkeypatch.setenv(FLAG, flag)
    n = {"c": 0}

    def boom(key):
        n["c"] += 1
        raise RuntimeError("x")

    monkeypatch.setattr(cache_service, "_redis_get", boom)
    assert serper_service._is_serper_key_exhausted(K1) is False
    assert serper_service._is_serper_key_exhausted(K1) is False
    assert n["c"] == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("flag", ["false", "true"])
async def test_p7d_search_web_with_redis_down_posts_first_key(rec, monkeypatch, flag):
    monkeypatch.setenv(FLAG, flag)
    monkeypatch.setenv("SERPER_API_KEYS", f"{K1},{K2}")
    rec.get_raises = True
    ctx, st = _client([200])
    with ctx:
        out = await serper_service.search_web("q")
    assert st["keys"] == [K1] and out == {"organic": [], "shopping": [{"title": "x"}]}


@pytest.mark.parametrize("bad_key", [123, b"aaaaaaaa1"], ids=["int", "bytes"])
@pytest.mark.parametrize("flag", ["false", "true"])
def test_p7e_non_str_key_fails_open_without_a_memo_entry(rec, monkeypatch, clock, flag, bad_key):
    """SM-ADV-4: base builds the flag key inside its try, so a non-str key is
    False; ON must do the same and store nothing."""
    monkeypatch.setenv(FLAG, flag)
    assert serper_service._is_serper_key_exhausted(bad_key) is False
    assert serper_service._is_serper_key_exhausted(bad_key) is False
    assert getattr(serper_service, "_serper_key_state_memo", {}) == {}
    assert rec.gets() == []


# ---------------------------------------------------------------- SM3 threads
def test_p8_lock_not_held_across_the_redis_get(rec, monkeypatch, clock):
    lock = _need("_serper_key_state_lock")
    monkeypatch.setenv(FLAG, "true")
    held = []
    rec.on_get = lambda key: held.append(lock.locked())
    serper_service._is_serper_key_exhausted(K1)
    assert held == [False]


def test_p8b_threads_hammer(rec, monkeypatch):
    """16 threads x 200 x (k1 flagged, k2 not). At base this fails on the GET
    count (3200 GETs per key, no memo)."""
    monkeypatch.setenv(FLAG, "true")
    rec.store[F1] = "1"
    errs, outs = [], []
    barrier = threading.Barrier(16)

    def run():
        try:
            barrier.wait(timeout=30)
            for _ in range(200):
                outs.append(serper_service._is_serper_key_exhausted(K1))
                outs.append(serper_service._is_serper_key_exhausted(K2))
        except Exception as e:  # noqa: BLE001
            errs.append(e)

    ts = [threading.Thread(target=run) for _ in range(16)]
    for t in ts:
        t.start()
    for t in ts:
        t.join(timeout=60)
    assert not any(t.is_alive() for t in ts)
    assert errs == []
    assert outs.count(True) == 3200 and outs.count(False) == 3200
    assert len(rec.gets(F1)) <= 16 and len(rec.gets(F2)) <= 16


def test_p8c_mark_from_another_thread_during_the_store_check(rec, monkeypatch, clock):
    """SM-ADV-1: a mark from ANOTHER thread lands while the reader is in its
    store-phase generation check. With the lock the mark waits until the store
    is done and then invalidates it; with a no-op lock the mark lands first and
    a stale False is stored. At base (no memo) the mark simply runs after the
    read and the next read sees the Redis flag."""
    monkeypatch.setenv(FLAG, "true")
    threads = []

    def start_mark(join_timeout):
        t = threading.Thread(target=serper_service._mark_serper_key_exhausted, args=(K1,))
        threads.append(t)
        t.start()
        t.join(timeout=join_timeout)

    class Gen(dict):
        n = 0

        def get(self, k, d=None):
            Gen.n += 1
            v = dict.get(self, k, d)
            if Gen.n == 2:
                start_mark(0.5)
            return v

    monkeypatch.setattr(serper_service, "_serper_key_state_gen", Gen(), raising=False)
    assert serper_service._is_serper_key_exhausted(K1) is False
    if not threads:
        start_mark(5)
    for t in threads:
        t.join(timeout=5)
    assert len(threads) == 1 and not threads[0].is_alive()
    assert serper_service._is_serper_key_exhausted(K1) is True


# ---------------------------------------------------------------- isolation + logs
def test_p9_conftest_resets_the_memo():
    src = open(os.path.join(os.path.dirname(__file__), "conftest.py"), encoding="utf-8").read()
    assert "_reset_serper_key_state_memo()" in src


def test_p9b_reset_clears(rec, monkeypatch, clock):
    reset = _need("_reset_serper_key_state_memo")
    memo = _need("_serper_key_state_memo")
    monkeypatch.setenv(FLAG, "true")
    serper_service._is_serper_key_exhausted(K1)
    assert memo
    reset()
    assert memo == {}


def test_p9c_on_adds_no_log_records(rec, monkeypatch, clock, caplog):
    monkeypatch.setenv(FLAG, "true")
    caplog.set_level("DEBUG", logger="app.services.serper_service")
    for _ in range(3):
        serper_service._is_serper_key_exhausted(K1)
    assert caplog.records == []
