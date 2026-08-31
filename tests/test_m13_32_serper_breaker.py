"""M13-32 pin — a Serper circuit breaker behind ENABLE_SERPER_BREAKER (default OFF).

Failure scenario: Serper (the highest-volume paid provider) had metering but no
breaker — record_failure('serper') / is_circuit_closed('serper') had zero call
sites. On the documented 403 state every compare kept dispatching all six Serper
entry points at full timeout forever. With the breaker ON, three failures open it
and the next dispatch short-circuits. Flag OFF is byte-identical (every call
dispatches, no breaker read, no record).

Zero-network: the api_budget circuit-breaker Redis is dict-stubbed; the httpx
client is a mock.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services import serper_service as ss
from app.services import api_budget_service as abs_mod


class _Resp:
    def __init__(self, status_code):
        self.status_code = status_code
        self.text = ""


def _dict_breaker_redis():
    store = {}
    return (
        store,
        lambda key: store.get(key),
        lambda key, value, ex=None: store.__setitem__(key, value) or True,
    )


@pytest.mark.asyncio
async def test_breaker_opens_after_three_failures_and_short_circuits(monkeypatch):
    monkeypatch.setenv("ENABLE_SERPER_BREAKER", "true")
    monkeypatch.setattr(ss, "_resolve_serper_keys", lambda: ["k1"])  # single-key path
    ss._reset_serper_breaker_cache()

    store, fake_get, fake_set = _dict_breaker_redis()

    client = MagicMock()
    client.post = AsyncMock(return_value=_Resp(500))  # every dispatch is a 5xx failure

    with patch.object(abs_mod, "_redis_get", side_effect=fake_get), \
         patch.object(abs_mod, "_redis_set", side_effect=fake_set):
        # 3 dispatched failures trip the breaker (CB_FAILURE_THRESHOLD == 3).
        for _ in range(abs_mod.CB_FAILURE_THRESHOLD):
            await ss._serper_post(client, "/search", {"q": "x"})
        assert client.post.await_count == abs_mod.CB_FAILURE_THRESHOLD

        # The next call must short-circuit (breaker OPEN) — no dispatch, returns None.
        result = await ss._serper_post(client, "/search", {"q": "x"})
    assert result is None
    assert client.post.await_count == abs_mod.CB_FAILURE_THRESHOLD, (
        "4th call dispatched despite an OPEN breaker"
    )
    ss._reset_serper_breaker_cache()


@pytest.mark.asyncio
async def test_flag_off_never_short_circuits(monkeypatch):
    monkeypatch.delenv("ENABLE_SERPER_BREAKER", raising=False)
    monkeypatch.setattr(ss, "_resolve_serper_keys", lambda: ["k1"])
    ss._reset_serper_breaker_cache()

    store, fake_get, fake_set = _dict_breaker_redis()
    client = MagicMock()
    client.post = AsyncMock(return_value=_Resp(500))

    with patch.object(abs_mod, "_redis_get", side_effect=fake_get), \
         patch.object(abs_mod, "_redis_set", side_effect=fake_set):
        results = [await ss._serper_post(client, "/search", {"q": "x"}) for _ in range(5)]

    # Flag OFF: every call dispatches, none short-circuits, breaker never consulted.
    assert client.post.await_count == 5
    assert all(r is not None for r in results)
    # No circuit state was ever written (record_failure/success were no-ops).
    assert store == {}


@pytest.mark.asyncio
async def test_flag_on_200_records_success(monkeypatch):
    """A 200 keeps the breaker closed; repeated 200s never trip it."""
    monkeypatch.setenv("ENABLE_SERPER_BREAKER", "true")
    monkeypatch.setattr(ss, "_resolve_serper_keys", lambda: ["k1"])
    ss._reset_serper_breaker_cache()

    store, fake_get, fake_set = _dict_breaker_redis()
    client = MagicMock()
    client.post = AsyncMock(return_value=_Resp(200))

    with patch.object(abs_mod, "_redis_get", side_effect=fake_get), \
         patch.object(abs_mod, "_redis_set", side_effect=fake_set):
        for _ in range(6):
            r = await ss._serper_post(client, "/search", {"q": "x"})
            assert r is not None
    assert client.post.await_count == 6
    ss._reset_serper_breaker_cache()
