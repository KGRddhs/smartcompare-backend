"""Serper fail-fast timeout/rotation (ENABLE_SERPER_FAIL_FAST).

The multi-key rotation loop in `_serper_post` rotates ONLY on a credit-depletion
signal; a SLOW (throttled) free key burns the full per-call timeout each attempt,
so 3 keys can stack to 3x the per-call timeout (~45s) and STARVE the Serper-free
genuine-BH adapter fan-out. This suite pins the opt-in fail-fast layer:

  - _serper_timeout(): flag OFF -> 15.0 (byte-identical); flag ON -> split
    connect/read budget (defaults 3s/8s, env-tunable).
  - _serper_post(): flag OFF -> a timeout PROPAGATES exactly as before (no catch,
    no rotation, no clock read = byte-identical). Flag ON -> a per-call timeout
    ROTATES to the next key (NOT marked exhausted — a timeout is not depletion),
    an overall wall-clock deadline stops the loop stacking, and an all-timeout run
    RE-RAISES the last timeout so the caller's except-path (Bright Data / degrade)
    fires exactly as before.

httpx + Redis mocked at the module level exactly as test_serper_multikey_failover.
"""
import httpx
import pytest
from unittest.mock import MagicMock, patch

from app.services import serper_service


# --------------------------------------------------------------------------- #
# Helpers                                                                      #
# --------------------------------------------------------------------------- #
def _mock_response(status_code: int = 200, json_data: dict | None = None,
                   text: str = "") -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data if json_data is not None else {"organic": []}
    resp.text = text
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = Exception(f"HTTP {status_code}")
    return resp


class _FakeClient:
    """A stand-in httpx client whose .post returns / raises `items` in order,
    recording the X-API-KEY of each attempt."""

    def __init__(self, items):
        self.items = items
        self.n = 0
        self.keys = []

    async def post(self, url, headers=None, json=None):
        self.keys.append((headers or {}).get("X-API-KEY"))
        item = self.items[self.n]
        self.n += 1
        if isinstance(item, Exception):
            raise item
        return item


def _patch_httpx_seq(items):
    """Patch httpx.AsyncClient so `async with ... as client` yields a _FakeClient
    over `items` (responses or exceptions-to-raise). Returns (ctx, holder) where
    holder['client'] is the live fake for key/attempt assertions."""
    holder = {}

    class _AsyncClient:
        def __init__(self, *a, **k):
            self._c = _FakeClient(items)
            holder["client"] = self._c

        async def __aenter__(self):
            return self._c

        async def __aexit__(self, *a):
            return False

    return patch("app.services.serper_service.httpx.AsyncClient", _AsyncClient), holder


class _FakeRedis:
    def __init__(self):
        self.store = {}

    def get(self, key):
        return self.store.get(key)

    def setex(self, key, ttl, value):
        self.store[key] = value

    def set(self, key, value):
        self.store[key] = value


@pytest.fixture
def fake_redis(monkeypatch):
    import app.services.cache_service as cache_service
    r = _FakeRedis()
    monkeypatch.setattr(cache_service, "redis_client", r)
    serper_service._serper_exhausted_logged.clear()
    return r


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for var in (
        "SERPER_API_KEYS", "ENABLE_SERPER_FAIL_FAST", "ENABLE_BRIGHTDATA_FALLBACK",
        "SERPER_READ_TIMEOUT", "SERPER_CONNECT_TIMEOUT", "SERPER_ROTATION_DEADLINE",
    ):
        monkeypatch.delenv(var, raising=False)
    serper_service._serper_exhausted_logged.clear()


_NOT_ENOUGH = '{"message":"Not enough credits"}'


# --------------------------------------------------------------------------- #
# _serper_timeout()                                                            #
# --------------------------------------------------------------------------- #
def test_serper_timeout_flag_off_is_15():
    assert serper_service._serper_timeout() == 15.0


def test_serper_timeout_flag_on_split(monkeypatch):
    monkeypatch.setenv("ENABLE_SERPER_FAIL_FAST", "true")
    t = serper_service._serper_timeout()
    assert isinstance(t, httpx.Timeout)
    assert t.read == 10.0
    assert t.connect == 3.0


def test_serper_timeout_flag_on_env_override(monkeypatch):
    monkeypatch.setenv("ENABLE_SERPER_FAIL_FAST", "1")
    monkeypatch.setenv("SERPER_READ_TIMEOUT", "5")
    monkeypatch.setenv("SERPER_CONNECT_TIMEOUT", "2")
    t = serper_service._serper_timeout()
    assert t.read == 5.0
    assert t.connect == 2.0


# --------------------------------------------------------------------------- #
# _serper_post — flag OFF is byte-identical (timeout propagates, no clock)     #
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_post_flag_off_timeout_propagates(monkeypatch, fake_redis):
    monkeypatch.setenv("SERPER_API_KEYS", "k1,k2")
    client = _FakeClient([httpx.ReadTimeout("slow")])
    with pytest.raises(httpx.ReadTimeout):
        await serper_service._serper_post(client, "/search", {"q": "x"})
    # exactly ONE attempt, no rotation on a timeout when the flag is off
    assert client.keys == ["k1"]
    assert not serper_service._is_serper_key_exhausted("k1")


@pytest.mark.asyncio
async def test_post_flag_off_happy_path_still_one_attempt(monkeypatch, fake_redis):
    """Flag OFF multi-key happy path is unchanged by the #60 unconditional
    deadline: one POST, the response returned, no rotation."""
    monkeypatch.setenv("SERPER_API_KEYS", "k1,k2")
    client = _FakeClient([_mock_response(200, {"organic": [{"ok": 1}]})])
    resp = await serper_service._serper_post(client, "/search", {"q": "x"})
    assert resp.status_code == 200
    assert client.keys == ["k1"]


# --------------------------------------------------------------------------- #
# #60 — the rotation deadline is UNCONDITIONAL (was gated behind the flag)     #
# --------------------------------------------------------------------------- #
def test_rotation_deadline_default_is_under_the_price_race_budget():
    """3 throttled keys x the 15s flag-OFF per-call timeout could consume ~45s
    inside structured_comparison_service's 15s _PRICE_RACE_TIMEOUT. The default
    rotation deadline must be strictly under that race budget."""
    from app.services.structured_comparison_service import _PRICE_RACE_TIMEOUT

    assert serper_service._serper_rotation_deadline() < _PRICE_RACE_TIMEOUT


@pytest.mark.asyncio
async def test_post_flag_off_deadline_stops_rotation(monkeypatch, fake_redis):
    """THE #60 BUG: with ENABLE_SERPER_FAIL_FAST unset, 3 keys answering slowly
    with depletion-400s each burned a full per-call budget and STACKED. The
    wall-clock deadline must now stop the loop even with the flag off."""
    monkeypatch.setenv("SERPER_API_KEYS", "k1,k2,k3")
    # start=0, iter1-top=0 (proceed), iter2-top=999 (deadline spent -> break)
    clock = iter([0.0, 0.0, 999.0])
    monkeypatch.setattr(serper_service, "_serper_now", lambda: next(clock))
    depleted = _mock_response(402, {}, text=_NOT_ENOUGH)
    healthy = _mock_response(200, {"organic": [{"ok": 1}]})
    client = _FakeClient([depleted, healthy, healthy])
    resp = await serper_service._serper_post(client, "/search", {"q": "x"})
    assert client.keys == ["k1"], "flag-OFF deadline must stop the loop after k1"
    assert resp is depleted  # last_response returned after the deadline break
    assert serper_service._is_serper_key_exhausted("k1")


@pytest.mark.asyncio
async def test_single_key_post_never_reads_the_clock(monkeypatch, fake_redis):
    """SINGLE-KEY INERT stays byte-identical: the short-circuit returns before
    the rotation loop, so no clock read and no Redis exhaustion read."""
    monkeypatch.delenv("SERPER_API_KEYS", raising=False)
    monkeypatch.setattr(serper_service, "SERPER_API_KEY", "only-key")
    now = MagicMock(side_effect=AssertionError("single-key path must not read the clock"))
    monkeypatch.setattr(serper_service, "_serper_now", now)
    client = _FakeClient([_mock_response(200, {"organic": [{"ok": 1}]})])
    resp = await serper_service._serper_post(client, "/search", {"q": "x"})
    assert resp.status_code == 200
    assert client.keys == ["only-key"]
    now.assert_not_called()


# --------------------------------------------------------------------------- #
# _serper_post — flag ON rotate-on-timeout / reraise / deadline                #
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_post_flag_on_rotates_on_timeout(monkeypatch, fake_redis):
    monkeypatch.setenv("ENABLE_SERPER_FAIL_FAST", "true")
    monkeypatch.setenv("SERPER_API_KEYS", "k1,k2")
    healthy = _mock_response(200, {"organic": [{"ok": 1}]})
    client = _FakeClient([httpx.ReadTimeout("slow"), healthy])
    resp = await serper_service._serper_post(client, "/search", {"q": "x"})
    assert resp is healthy
    assert client.keys == ["k1", "k2"], "a timeout on k1 must rotate to k2"
    # a timeout is NOT a depletion signal — k1 must NOT be flagged exhausted
    assert not serper_service._is_serper_key_exhausted("k1")


@pytest.mark.asyncio
async def test_post_flag_on_all_timeout_reraises(monkeypatch, fake_redis):
    monkeypatch.setenv("ENABLE_SERPER_FAIL_FAST", "true")
    monkeypatch.setenv("SERPER_API_KEYS", "k1,k2")
    client = _FakeClient([httpx.ReadTimeout("slow"), httpx.ConnectTimeout("slow")])
    with pytest.raises(httpx.TimeoutException):
        await serper_service._serper_post(client, "/search", {"q": "x"})
    assert client.keys == ["k1", "k2"], "both keys attempted before giving up"
    assert not serper_service._is_serper_key_exhausted("k1")
    assert not serper_service._is_serper_key_exhausted("k2")


@pytest.mark.asyncio
async def test_post_flag_on_deadline_stops_rotation(monkeypatch, fake_redis):
    """Once the overall wall-clock deadline is hit, the loop STOPS rotating even
    though healthy keys remain — so N slow keys can't stack to N x per-call."""
    monkeypatch.setenv("ENABLE_SERPER_FAIL_FAST", "true")
    monkeypatch.setenv("SERPER_API_KEYS", "k1,k2,k3")
    # clock: start=0, iter1-top=0 (<deadline -> proceed), iter2-top=999 (>=deadline -> break)
    clock = iter([0.0, 0.0, 999.0])
    monkeypatch.setattr(serper_service, "_serper_now", lambda: next(clock))
    depleted = _mock_response(402, {}, text=_NOT_ENOUGH)  # k1 -> exhausted -> continue
    healthy = _mock_response(200, {"organic": [{"ok": 1}]})  # would be k2 but for the deadline
    client = _FakeClient([depleted, healthy])
    resp = await serper_service._serper_post(client, "/search", {"q": "x"})
    assert client.keys == ["k1"], "deadline must stop the loop before trying k2"
    assert resp is depleted  # last_response returned after the deadline break
    assert serper_service._is_serper_key_exhausted("k1")


@pytest.mark.asyncio
async def test_post_flag_on_timeout_then_depletion_returns_depletion(monkeypatch, fake_redis):
    """A timeout on k1 then a real depletion-402 on k2 must RETURN the 402
    (last_response), NOT reraise the earlier timeout — a real response beats the
    timeout-degrade, and the reraise-guard must not shadow it."""
    monkeypatch.setenv("ENABLE_SERPER_FAIL_FAST", "true")
    monkeypatch.setenv("SERPER_API_KEYS", "k1,k2")
    depleted = _mock_response(402, {}, text=_NOT_ENOUGH)
    client = _FakeClient([httpx.ReadTimeout("slow"), depleted])
    resp = await serper_service._serper_post(client, "/search", {"q": "x"})
    assert resp is depleted, "a real depletion response beats the timeout reraise"
    assert client.keys == ["k1", "k2"]
    assert not serper_service._is_serper_key_exhausted("k1")  # timeout != depletion
    assert serper_service._is_serper_key_exhausted("k2")      # 402 = depletion


# --------------------------------------------------------------------------- #
# SERPER_ROTATION_DEADLINE <= 0 means "NO DEADLINE", never "no calls"          #
#                                                                              #
# #60 review, blocking 1. Making the deadline check unconditional turned        #
# SERPER_ROTATION_DEADLINE=0 into a silent TOTAL Serper blackout for any        #
# multi-key config: 0.0 makes the very first loop-top comparison true, the loop #
# breaks before any POST, _serper_post returns None, and the caller's           #
# `response.raise_for_status()` on None raises AttributeError straight into the #
# broad `except` — a benign empty result and ZERO calls, forever. That inverts  #
# this repo's own `<=0 disables the check` convention                           #
# (cron_warm_price_cache._serper_per_query_estimate /                           #
# _serper_max_credits_per_run) on a value that was completely INERT before #60, #
# and it sits on the obvious rollback flip for part 3 of this very commit.      #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("deadline", ["0", "0.0", "-1"])
@pytest.mark.asyncio
async def test_deadline_zero_disables_the_deadline_flag_off(
    monkeypatch, fake_redis, deadline
):
    """Flag OFF (the default). A non-positive deadline must mean the FULL
    rotation still happens — every key is tried — not that Serper goes dark."""
    monkeypatch.setenv("SERPER_ROTATION_DEADLINE", deadline)
    monkeypatch.setenv("SERPER_API_KEYS", "k1,k2")
    depleted = _mock_response(402, {}, text=_NOT_ENOUGH)
    healthy = _mock_response(200, {"organic": [{"ok": 1}]})
    client = _FakeClient([depleted, healthy])
    resp = await serper_service._serper_post(client, "/search", {"q": "x"})
    assert client.keys == ["k1", "k2"], (
        "a non-positive deadline must DISABLE the deadline, not the rotation"
    )
    assert resp is healthy


@pytest.mark.asyncio
async def test_deadline_zero_disables_the_deadline_flag_on(monkeypatch, fake_redis):
    """Same with ENABLE_SERPER_FAIL_FAST on — the flag changes the per-call
    timeout and rotate-on-timeout, never whether calls happen at all."""
    monkeypatch.setenv("ENABLE_SERPER_FAIL_FAST", "true")
    monkeypatch.setenv("SERPER_ROTATION_DEADLINE", "0")
    monkeypatch.setenv("SERPER_API_KEYS", "k1,k2")
    depleted = _mock_response(402, {}, text=_NOT_ENOUGH)
    healthy = _mock_response(200, {"organic": [{"ok": 1}]})
    client = _FakeClient([depleted, healthy])
    resp = await serper_service._serper_post(client, "/search", {"q": "x"})
    assert client.keys == ["k1", "k2"]
    assert resp is healthy


@pytest.mark.asyncio
async def test_search_web_still_calls_serper_with_a_zero_deadline(
    monkeypatch, fake_redis
):
    """End to end, the shape the outage actually took: with the deadline flipped
    to 0 on a multi-key config, search_web returned a benign empty result having
    fired ZERO POSTs — indistinguishable from depletion, app-wide."""
    monkeypatch.setenv("SERPER_ROTATION_DEADLINE", "0")
    monkeypatch.setenv("SERPER_API_KEYS", "k1,k2")
    ctx, holder = _patch_httpx_seq([_mock_response(200, {"organic": [{"ok": 1}]})])
    with ctx:
        result = await serper_service.search_web("q")
    assert holder["client"].keys == ["k1"], "a zero deadline must not silence Serper"
    assert result.get("organic") == [{"ok": 1}]
    assert not result.get("error")


# --------------------------------------------------------------------------- #
# end-to-end: search_web degrades gracefully on an all-timeout fail-fast run   #
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_search_web_flag_on_all_timeout_degrades(monkeypatch, fake_redis):
    monkeypatch.setenv("ENABLE_SERPER_FAIL_FAST", "true")
    monkeypatch.setenv("SERPER_API_KEYS", "k1,k2")
    ctx, holder = _patch_httpx_seq([httpx.ReadTimeout("s"), httpx.ReadTimeout("s")])
    with ctx:
        result = await serper_service.search_web("q")
    # the reraised timeout reaches search_web's except -> graceful degrade
    assert result.get("error")
    assert result.get("organic") == []
    assert holder["client"].keys == ["k1", "k2"]
