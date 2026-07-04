"""genuine-price serper-multikey — multi-key Serper credit-exhaustion failover.

A single free Serper key holds a finite lifetime credit pool; when it depletes
mid-run the warmer cron (and live compares) silently degrade to `estimated`.
This suite pins the failover layer added to `serper_service`:

  (a) single SERPER_API_KEY, healthy   -> used, byte-identical, no rotation
  (b) SERPER_API_KEYS="k1,k2,k3", k1 depleted -> k1 marked exhausted, k2 used,
      call succeeds
  (c) all keys exhausted -> graceful degradation (same as legacy depleted path)
  (d) exhaustion flag persists (2nd call skips the exhausted key, no re-hit)
  (e) the active key drives api_budget_service._serper_key_prefix()
  (f) a transient 500 (not a credit error) does NOT mark the key exhausted

Redis / cache_service is mocked with an in-memory dict so the exhaustion flag
is observable without a live Redis. httpx is mocked at the module level exactly
as the existing serper tests do (`app.services.serper_service.httpx.AsyncClient`).
"""
import pytest
from unittest.mock import patch, MagicMock

from app.services import serper_service
from app.services import api_budget_service


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_response(status_code: int = 200, json_data: dict | None = None,
                   text: str = "") -> MagicMock:
    """A response whose .text is a real str (so the exhaustion predicate can
    read the credit-depletion message the way a real httpx.Response exposes it)."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data if json_data is not None else {"organic": []}
    resp.text = text
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = Exception(f"HTTP {status_code}")
    return resp


def _patch_httpx_capture(responses):
    """Patch httpx.AsyncClient. `.post(url, headers=..., json=...)` returns
    responses[i] in order and records the X-API-KEY header of each call so
    tests can assert WHICH key was used per attempt."""
    state = {"n": 0, "keys": []}

    class _AsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, *args, **kwargs):
            headers = kwargs.get("headers", {})
            state["keys"].append(headers.get("X-API-KEY"))
            r = responses[state["n"]]
            state["n"] += 1
            return r

    return patch("app.services.serper_service.httpx.AsyncClient", _AsyncClient), state


class _FakeRedis:
    """Minimal in-memory Redis replacement exercised via the cache_service
    helpers serper_service imports (_redis_get / _redis_set)."""

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
    """Route serper_service's lazy cache_service._redis_get/_set imports at an
    in-memory dict so exhaustion flags are observable + persistent within a test."""
    import app.services.cache_service as cache_service
    r = _FakeRedis()
    monkeypatch.setattr(cache_service, "redis_client", r)
    # Reset the per-process WARNING de-dupe set between tests.
    serper_service._serper_exhausted_logged.clear()
    return r


@pytest.fixture(autouse=True)
def _clear_multikey_env(monkeypatch):
    """Ensure SERPER_API_KEYS is unset unless a test sets it (isolation)."""
    monkeypatch.delenv("SERPER_API_KEYS", raising=False)
    serper_service._serper_exhausted_logged.clear()


_NOT_ENOUGH_CREDITS = '{"message":"Not enough credits"}'


# ---------------------------------------------------------------------------
# (a) single key, healthy -> byte-identical, no rotation, one POST
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_single_key_healthy_no_rotation(monkeypatch, fake_redis):
    monkeypatch.setattr(serper_service, "SERPER_API_KEY", "solo-key")
    resp = _mock_response(200, {"organic": [{"title": "x"}]})
    ctx, state = _patch_httpx_capture([resp])
    with ctx:
        with patch.object(serper_service, "record_usage") as mock_record:
            result = await serper_service.search_web("test query")
    assert state["n"] == 1, "healthy single key must fire exactly ONE POST"
    assert state["keys"] == ["solo-key"]
    assert result == {"organic": [{"title": "x"}]}
    mock_record.assert_called_with("serper")
    # No exhaustion flag set for a healthy key.
    assert not serper_service._is_serper_key_exhausted("solo-key")


# ---------------------------------------------------------------------------
# (b) k1 depleted -> k1 marked exhausted, k2 used, call succeeds
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_k1_depleted_rotates_to_k2(monkeypatch, fake_redis):
    monkeypatch.setenv("SERPER_API_KEYS", "k1,k2,k3")
    # k1 returns a 402/credit body; k2 returns a healthy 200.
    depleted = _mock_response(402, {}, text=_NOT_ENOUGH_CREDITS)
    healthy = _mock_response(200, {"organic": [{"title": "ok"}]})
    ctx, state = _patch_httpx_capture([depleted, healthy])
    with ctx:
        with patch.object(serper_service, "record_usage") as mock_record:
            result = await serper_service.search_web("q")
    assert state["keys"] == ["k1", "k2"], "k1 tried, then rotated to k2"
    assert result == {"organic": [{"title": "ok"}]}
    mock_record.assert_called_with("serper")
    assert serper_service._is_serper_key_exhausted("k1"), "k1 must be flagged"
    assert not serper_service._is_serper_key_exhausted("k2")


@pytest.mark.asyncio
async def test_credit_body_on_400_also_rotates(monkeypatch, fake_redis):
    """A depleted free key today returns HTTP 400 + 'Not enough credits' body;
    the substring signal (not just status 402/403) must catch it."""
    monkeypatch.setenv("SERPER_API_KEYS", "kA,kB")
    depleted = _mock_response(400, {}, text=_NOT_ENOUGH_CREDITS)
    healthy = _mock_response(200, {"organic": []})
    ctx, state = _patch_httpx_capture([depleted, healthy])
    with ctx:
        await serper_service.search_web("q")
    assert state["keys"] == ["kA", "kB"]
    assert serper_service._is_serper_key_exhausted("kA")


# ---------------------------------------------------------------------------
# (c) all keys exhausted -> graceful degradation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_all_keys_exhausted_degrades_gracefully(monkeypatch, fake_redis):
    monkeypatch.setenv("SERPER_API_KEYS", "x1,x2")
    # Pre-mark both keys exhausted.
    serper_service._mark_serper_key_exhausted("x1")
    serper_service._mark_serper_key_exhausted("x2")
    # No httpx call should occur — the guard short-circuits.
    ctx, state = _patch_httpx_capture([])
    with ctx:
        with patch.object(serper_service, "record_usage") as mock_record:
            result = await serper_service.search_web("q")
    assert state["n"] == 0, "all-exhausted must NOT hit the network"
    assert result == {"organic": [], "error": "Search not configured"}
    mock_record.assert_not_called()


@pytest.mark.asyncio
async def test_no_keys_configured_degrades_like_legacy(monkeypatch, fake_redis):
    """SERPER_API_KEY=None and no SERPER_API_KEYS -> legacy 'not configured'."""
    monkeypatch.setattr(serper_service, "SERPER_API_KEY", None)
    ctx, state = _patch_httpx_capture([])
    with ctx:
        with patch.object(serper_service, "record_usage") as mock_record:
            result = await serper_service.search_web("q")
    assert state["n"] == 0
    assert result == {"organic": [], "error": "Search not configured"}
    mock_record.assert_not_called()


# ---------------------------------------------------------------------------
# (d) exhaustion flag persists — a second call skips the exhausted key
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_exhaustion_persists_second_call_skips_key(monkeypatch, fake_redis):
    monkeypatch.setenv("SERPER_API_KEYS", "p1,p2")
    # Call 1: p1 depleted -> rotate to p2 (healthy).
    depleted = _mock_response(403, {}, text="forbidden: not enough credit")
    healthy1 = _mock_response(200, {"organic": [{"n": 1}]})
    ctx1, state1 = _patch_httpx_capture([depleted, healthy1])
    with ctx1:
        await serper_service.search_web("q1")
    assert state1["keys"] == ["p1", "p2"]
    assert serper_service._is_serper_key_exhausted("p1")

    # Call 2: p1 is already flagged in Redis -> active key is p2 from the start,
    # so the FIRST (and only) POST uses p2, no re-hit of p1.
    healthy2 = _mock_response(200, {"organic": [{"n": 2}]})
    ctx2, state2 = _patch_httpx_capture([healthy2])
    with ctx2:
        result = await serper_service.search_web("q2")
    assert state2["keys"] == ["p2"], "2nd call must skip the exhausted p1 entirely"
    assert state2["n"] == 1
    assert result == {"organic": [{"n": 2}]}


# ---------------------------------------------------------------------------
# (e) the active key drives api_budget_service._serper_key_prefix()
# ---------------------------------------------------------------------------


def test_active_key_drives_budget_prefix(monkeypatch, fake_redis):
    monkeypatch.setenv("SERPER_API_KEYS", "aaaaaaaa11,bbbbbbbb22,cccccccc33")
    # No exhaustion -> first key active -> prefix = first 8 of aaaaaaaa11.
    assert api_budget_service._serper_key_prefix() == "aaaaaaaa"
    # Exhaust the first key -> prefix tracks the next active key.
    serper_service._mark_serper_key_exhausted("aaaaaaaa11")
    assert api_budget_service._serper_key_prefix() == "bbbbbbbb"
    # Exhaust the second -> tracks the third.
    serper_service._mark_serper_key_exhausted("bbbbbbbb22")
    assert api_budget_service._serper_key_prefix() == "cccccccc"


def test_budget_prefix_single_key_backward_compatible(monkeypatch, fake_redis):
    """With only SERPER_API_KEY set (no SERPER_API_KEYS), the counter prefix is
    the single key's 8-char prefix — byte-identical to the pre-multikey scoping."""
    monkeypatch.delenv("SERPER_API_KEYS", raising=False)
    monkeypatch.setenv("SERPER_API_KEY", "singlekey1234")
    # api_budget_service reads via serper_service._resolve_serper_keys which
    # falls back to the SERPER_API_KEY module attr; align both.
    monkeypatch.setattr(serper_service, "SERPER_API_KEY", "singlekey1234")
    assert api_budget_service._serper_key_prefix() == "singleke"


def test_budget_prefix_nokey_sentinel(monkeypatch, fake_redis):
    monkeypatch.delenv("SERPER_API_KEYS", raising=False)
    monkeypatch.delenv("SERPER_API_KEY", raising=False)
    monkeypatch.setattr(serper_service, "SERPER_API_KEY", None)
    assert api_budget_service._serper_key_prefix() == "nokey"


# ---------------------------------------------------------------------------
# (f) a transient 500 (not a credit error) does NOT mark the key exhausted
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_transient_500_does_not_mark_exhausted(monkeypatch, fake_redis):
    monkeypatch.setenv("SERPER_API_KEYS", "t1,t2")
    # A 500 with a non-credit body: _serper_post returns it as-is (no rotation),
    # and search_web's raise_for_status() turns it into the {error} degrade.
    transient = _mock_response(500, {}, text="Internal Server Error")
    ctx, state = _patch_httpx_capture([transient])
    with ctx:
        result = await serper_service.search_web("q")
    assert state["keys"] == ["t1"], "a 500 must NOT rotate keys"
    assert state["n"] == 1, "no failover POST for a transient error"
    assert not serper_service._is_serper_key_exhausted("t1"), \
        "a transient 500 must NOT mark the key exhausted"
    assert result.get("error"), "raise_for_status still degrades to an error dict"


def test_response_signals_exhaustion_predicate():
    """Unit-pin the detection predicate itself."""
    f = serper_service._response_signals_exhaustion
    assert f(402, "") is True
    assert f(403, "") is True
    assert f(400, '{"message":"Not enough credits"}') is True
    # STATUS-GATED: a legit HTTP 200 body containing 'credit'/'accredited'/
    # 'credited' (e.g. a product named "credit card") must NOT false-positive.
    assert f(200, "plenty of CREDIT left") is False
    assert f(200, "the best credit card in Bahrain") is False
    # A real depletion is a >=400 error whose body carries the credit message.
    assert f(400, "Not enough credits") is True
    assert f(500, "Internal Server Error") is False
    assert f(429, "rate limited") is False
    assert f(200, "") is False
    # A non-str body (e.g. a MagicMock's auto .text) must not blow up / match.
    assert f(200, MagicMock()) is False


def test_resolve_keys_multikey_trims_and_dedupes(monkeypatch):
    monkeypatch.setenv("SERPER_API_KEYS", " k1 , , k2 ,k1, k3 ")
    assert serper_service._resolve_serper_keys() == ["k1", "k2", "k3"]


def test_resolve_keys_falls_back_to_single(monkeypatch):
    monkeypatch.delenv("SERPER_API_KEYS", raising=False)
    monkeypatch.setattr(serper_service, "SERPER_API_KEY", "onlyone")
    assert serper_service._resolve_serper_keys() == ["onlyone"]
