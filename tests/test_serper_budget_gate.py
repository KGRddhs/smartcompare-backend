"""Serper budget gate (#60) — stop live Serper spend before it is billed.

`serper_service` imported `record_usage` but never `has_budget`, so every live
entry point (`search_web`, `search_product_prices`, `search_price_organic`,
`search_videos`, `search_images`, `search_news`) recorded credits AFTER a 200
and nothing ever checked headroom first. The Serper key is a 2,500-credit
ONE-TIME free pool and a cold 2-product compare burns ~10-30 of them, which is
why the key has depleted repeatedly.

This suite pins the gate:

  (a) counter over the ceiling -> ZERO HTTP calls, ZERO record_usage, and the
      SAME benign empty shape the existing missing-key branches return, so the
      price cascade falls through to the next tier instead of erroring.
  (b) `SERPER_LIFETIME_LIMIT` raised (the PAID-key case) -> the gate admits
      calls even when the counter is far past the packaged free-tier 2200.
      This is the failure mode `scripts/cron_warm_price_cache.py:118-131`
      warns about; the warmer must NOT be darkened by this gate.
  (c) `SERPER_LIFETIME_LIMIT=0` -> gate fully disabled (the rollback env flip).
  (d) Redis outage -> FAIL OPEN (a dead Upstash must never disable Serper),
      matching `api_budget_service.has_budget`'s existing convention.

Redis is stubbed at `api_budget_service._redis_get` so no test reads the live
Upstash counter; httpx is stubbed at the serper_service module level exactly as
the sibling serper suites do.
"""
import pytest
from unittest.mock import MagicMock, patch

from app.services import api_budget_service
from app.services import serper_service


# --------------------------------------------------------------------------- #
# Helpers                                                                      #
# --------------------------------------------------------------------------- #
def _patch_no_http():
    """httpx stub that RECORDS every POST attempt instead of raising.

    Raising here would be swallowed by each entry point's broad `except
    Exception` and the benign-empty assertions would pass for the WRONG reason,
    so the attempt count is carried out-of-band and asserted by the caller."""
    attempts = {"n": 0}

    class _AsyncClient:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, *a, **k):
            attempts["n"] += 1
            return _mock_response(200, {"organic": [{"title": "LEAKED"}],
                                        "shopping": [{"title": "LEAKED"}],
                                        "videos": [{"title": "LEAKED"}],
                                        "images": [{"title": "LEAKED"}],
                                        "news": [{"title": "LEAKED"}]})

    return patch("app.services.serper_service.httpx.AsyncClient", _AsyncClient), attempts


def _mock_response(status_code: int = 200, json_data: dict | None = None) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data if json_data is not None else {"organic": []}
    resp.text = ""
    resp.raise_for_status = MagicMock()
    return resp


def _patch_http_counting(response: MagicMock):
    """httpx stub that returns `response` and counts POSTs."""
    calls = {"n": 0}

    class _AsyncClient:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, *a, **k):
            calls["n"] += 1
            return response

    return patch("app.services.serper_service.httpx.AsyncClient", _AsyncClient), calls


def _patch_counter(used):
    """Stub api_budget_service._redis_get so the serper lifetime counter reads
    `used`. `used=Exception` makes every read raise (the Redis-outage case)."""

    def _fake_get(key):
        if isinstance(used, Exception):
            raise used
        if key.endswith(":lifetime"):
            return str(used)
        return None

    return patch.object(api_budget_service, "_redis_get", side_effect=_fake_get)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for var in (
        "SERPER_API_KEYS", "SERPER_LIFETIME_LIMIT", "ENABLE_BRIGHTDATA_FALLBACK",
        "ENABLE_SERPER_FAIL_FAST",
    ):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr(serper_service, "SERPER_API_KEY", "test-key")
    monkeypatch.setenv("SERPER_API_KEY", "test-key")
    serper_service._serper_exhausted_logged.clear()


# --------------------------------------------------------------------------- #
# api_budget_service — env-tunable ceiling + serper_gate_allows()              #
# --------------------------------------------------------------------------- #
def test_default_serper_limit_is_the_packaged_2200():
    """Unset env must be byte-identical to the hardcoded PROVIDER_CONFIGS value
    (tests/test_price_pipeline_diagnostic.py pins get_remaining == 2200)."""
    assert api_budget_service._serper_lifetime_limit() == 2200
    assert api_budget_service.PROVIDER_CONFIGS["serper"]["monthly_limit"] == 2200


def test_serper_limit_is_env_tunable(monkeypatch):
    monkeypatch.setenv("SERPER_LIFETIME_LIMIT", "250000")
    assert api_budget_service._serper_lifetime_limit() == 250000


def test_serper_limit_ignores_garbage_env(monkeypatch):
    monkeypatch.setenv("SERPER_LIFETIME_LIMIT", "not-a-number")
    assert api_budget_service._serper_lifetime_limit() == 2200


def test_gate_closes_when_counter_is_over_the_ceiling():
    with _patch_counter(2500):
        assert api_budget_service.has_budget("serper") is False
        assert api_budget_service.serper_gate_allows() is False


def test_gate_opens_when_lifetime_limit_is_raised(monkeypatch):
    """The PAID-key case. Counter past the free-tier 2200 must NOT darken a key
    whose real ceiling is higher — the cron_warm_price_cache.py:118-131 hazard."""
    monkeypatch.setenv("SERPER_LIFETIME_LIMIT", "250000")
    with _patch_counter(5136):
        assert api_budget_service.get_remaining("serper") == 250000 - 5136
        assert api_budget_service.serper_gate_allows() is True


def test_gate_disabled_entirely_by_zero_limit(monkeypatch):
    """SERPER_LIFETIME_LIMIT=0 is the rollback env flip: gate always allows."""
    monkeypatch.setenv("SERPER_LIFETIME_LIMIT", "0")
    with _patch_counter(999999):
        assert api_budget_service.serper_gate_allows() is True


def test_gate_fails_open_on_redis_error():
    """A dead Upstash must never disable Serper (has_budget's own convention)."""
    with _patch_counter(RuntimeError("upstash down")):
        assert api_budget_service.serper_gate_allows() is True


def test_warmer_is_not_disabled_by_the_gate(monkeypatch):
    """`scripts/cron_warm_price_cache.py` deliberately does NOT consult
    has_budget because the packaged 2200 is a FREE-tier ceiling. With the paid
    ceiling declared (or the gate disabled), the new gate must stay open so the
    warmer still runs to its own WARMER_MAX_SERPER_CREDITS_PER_RUN cap."""
    from scripts import cron_warm_price_cache as warmer

    monkeypatch.setenv("SERPER_LIFETIME_LIMIT", "250000")
    with _patch_counter(50000):
        assert serper_service._serper_budget_ok() is True
    # the warmer's own per-run cap is untouched by this issue
    assert warmer._serper_max_credits_per_run() == 900


# --------------------------------------------------------------------------- #
# serper_service._serper_budget_ok()                                           #
# --------------------------------------------------------------------------- #
def test_serper_budget_ok_mirrors_the_gate():
    with _patch_counter(10):
        assert serper_service._serper_budget_ok() is True
    with _patch_counter(2500):
        assert serper_service._serper_budget_ok() is False


def test_serper_budget_ok_fails_open_when_the_gate_raises():
    with patch.object(
        serper_service, "serper_gate_allows", side_effect=RuntimeError("boom")
    ):
        assert serper_service._serper_budget_ok() is True


# --------------------------------------------------------------------------- #
# Budget-out -> ZERO HTTP, ZERO record_usage, benign empty shape               #
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_search_web_budget_out_makes_zero_http_calls():
    ctx, attempts = _patch_no_http()
    with _patch_counter(2500), ctx:
        with patch.object(serper_service, "record_usage") as rec:
            result = await serper_service.search_web("iPhone 16")
    assert attempts["n"] == 0, "budget-out must not dispatch a Serper POST"
    assert result["organic"] == []
    assert result.get("error")
    rec.assert_not_called()


@pytest.mark.asyncio
async def test_search_product_prices_budget_out_makes_zero_http_calls():
    ctx, attempts = _patch_no_http()
    with _patch_counter(2500), ctx:
        with patch.object(serper_service, "record_usage") as rec:
            result = await serper_service.search_product_prices("iPhone 16", country="bh")
    assert attempts["n"] == 0, "budget-out must not dispatch a Serper POST"
    assert result["shopping"] == []
    assert result["organic"] == []
    rec.assert_not_called()


@pytest.mark.asyncio
async def test_search_price_organic_budget_out_makes_zero_http_calls():
    ctx, attempts = _patch_no_http()
    with _patch_counter(2500), ctx:
        with patch.object(serper_service, "record_usage") as rec:
            result = await serper_service.search_price_organic("iPhone 16", country="bh")
    assert attempts["n"] == 0, "budget-out must not dispatch a Serper POST"
    assert result["organic"] == []
    assert result.get("error")
    rec.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "fn_name,empty_key",
    [("search_videos", "videos"), ("search_images", "images"), ("search_news", "news")],
)
async def test_secondary_searches_budget_out_make_zero_http_calls(fn_name, empty_key):
    fn = getattr(serper_service, fn_name)
    ctx, attempts = _patch_no_http()
    with _patch_counter(2500), ctx:
        with patch.object(serper_service, "record_usage") as rec:
            result = await fn("iPhone 16")
    assert attempts["n"] == 0, "budget-out must not dispatch a Serper POST"
    assert result[empty_key] == []
    assert result.get("error")
    rec.assert_not_called()


@pytest.mark.asyncio
async def test_budget_out_degrades_to_next_tier_not_an_error():
    """A budget-out must produce the SAME fall-through shape the cascade already
    handles when both shopping legs come back empty (structured_comparison_
    service reads `shopping` / `organic` / `shopping_region` and drops to
    Tier 1.5 / 2 / 3). It must NEVER raise — a raise would abort the compare."""
    ctx, attempts = _patch_no_http()
    with _patch_counter(2500), ctx:
        result = await serper_service.search_product_prices("iPhone 16", country="bh")
    assert attempts["n"] == 0
    # exactly the keys the cascade reads, all benign — no Tier-1 price, no raise
    assert result.get("shopping") == []
    assert result.get("organic") == []


@pytest.mark.asyncio
async def test_budget_out_prefers_bright_data_when_that_fallback_is_on(monkeypatch):
    """The budget-out must reuse the EXISTING Bright Data degrade path (#61 owns
    that wiring) rather than dead-ending, when the fallback is enabled."""
    monkeypatch.setenv("ENABLE_BRIGHTDATA_FALLBACK", "true")

    async def _fake_bd(query, num_results=10, country="bh"):
        return {"organic": [{"title": "from-brightdata"}]}

    ctx, attempts = _patch_no_http()
    with _patch_counter(2500), ctx:
        with patch("app.services.brightdata_service._brightdata_enabled", return_value=True):
            with patch("app.services.brightdata_service.bd_search_web", side_effect=_fake_bd):
                result = await serper_service.search_web("iPhone 16")
    assert attempts["n"] == 0
    assert result["organic"] == [{"title": "from-brightdata"}]


# --------------------------------------------------------------------------- #
# Gate OPEN -> the call proceeds exactly as before                             #
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_search_web_proceeds_when_budget_remains():
    resp = _mock_response(200, {"organic": [{"title": "x"}]})
    ctx, calls = _patch_http_counting(resp)
    with _patch_counter(10), ctx:
        with patch.object(serper_service, "record_usage") as rec:
            result = await serper_service.search_web("iPhone 16")
    assert calls["n"] == 1
    assert result["organic"] == [{"title": "x"}]
    rec.assert_called_with("serper")


@pytest.mark.asyncio
async def test_search_web_proceeds_on_redis_outage():
    """Fail-open end-to-end: Upstash down must NOT disable Serper."""
    resp = _mock_response(200, {"organic": [{"title": "x"}]})
    ctx, calls = _patch_http_counting(resp)
    with _patch_counter(RuntimeError("upstash down")), ctx:
        result = await serper_service.search_web("iPhone 16")
    assert calls["n"] == 1
    assert result["organic"] == [{"title": "x"}]


@pytest.mark.asyncio
async def test_search_web_proceeds_past_2200_when_limit_is_raised(monkeypatch):
    monkeypatch.setenv("SERPER_LIFETIME_LIMIT", "250000")
    resp = _mock_response(200, {"organic": [{"title": "x"}]})
    ctx, calls = _patch_http_counting(resp)
    with _patch_counter(9000), ctx:
        result = await serper_service.search_web("iPhone 16")
    assert calls["n"] == 1
    assert result["organic"] == [{"title": "x"}]
