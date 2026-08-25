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
  (e) `SERPER_LIFETIME_LIMIT` UNSET (the DEFAULT, and the config prod actually
      runs) -> the gate is INERT: calls go through even past 2200. The packaged
      2200 is a FREE-tier number and prod runs a PAID key, so a gate armed at it
      would darken all six entry points on a schedule. See
      `_serper_gate_engaged`.
  (f) the decision is MEMOISED, so the six entry points do not each pay a
      blocking Upstash round trip on the asyncio event loop.

Redis is stubbed at `api_budget_service._redis_get` so no test reads the live
Upstash counter; httpx is stubbed at the serper_service module level exactly as
the sibling serper suites do.
"""
import os

import pytest
from unittest.mock import MagicMock, patch

from app.services import api_budget_service
from app.services import serper_service


def _gate_armed(limit: int = 2200):
    """Arm the #60 spend gate at `limit`.

    The gate is INERT unless an operator DECLARES a ceiling — that is the whole
    point of `_serper_gate_engaged` — so every test that wants to observe gate
    CLOSURE has to declare one. Tests that assert the default/unset behaviour
    deliberately do not use this."""
    return patch.dict(os.environ, {"SERPER_LIFETIME_LIMIT": str(limit)})


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
        "ENABLE_SERPER_FAIL_FAST", "SERPER_GATE_CACHE_TTL",
    ):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr(serper_service, "SERPER_API_KEY", "test-key")
    monkeypatch.setenv("SERPER_API_KEY", "test-key")
    serper_service._serper_exhausted_logged.clear()
    # The gate decision is memoised per process; a stale one would make these
    # assertions depend on collection order. (tests/conftest.py clears it
    # suite-wide too; this keeps the module self-contained.)
    serper_service.reset_serper_budget_cache()
    # The one-shot config INFO line costs an extra get_remaining() read on the
    # first gate call in a process. Latch it as already-logged so the
    # round-trip-COUNTING tests below don't depend on collection order;
    # test_gate_config_is_logged_once unlatches it deliberately.
    monkeypatch.setattr(api_budget_service, "_serper_gate_config_logged", True)


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
    with _gate_armed(2200), _patch_counter(2500):
        assert api_budget_service.has_budget("serper") is False
        assert api_budget_service.serper_gate_allows() is False


# --------------------------------------------------------------------------- #
# DEFAULT (unset) configuration — the gate must be INERT                       #
#                                                                              #
# #60 review, blocking 4. Shipping the gate armed at the packaged 2200 means    #
# that the moment the live lifetime counter crosses it, ALL SIX serper entry    #
# points go dark app-wide — price, specs, reviews, images, the discovery        #
# fan-out — and the price-cache warmer with them, on a FREE-tier number that    #
# has nothing to do with the PAID key production runs. That is the exact        #
# failure mode cron_warm_price_cache.py:118-131 refuses to reproduce and that   #
# #60's own warning block told the implementer to avoid. These tests pin the    #
# DEFAULT config (the one prod actually runs) rather than leaving it implicit.  #
# --------------------------------------------------------------------------- #
def test_gate_is_inert_when_no_ceiling_is_declared():
    assert api_budget_service._serper_gate_engaged() is False
    with _patch_counter(2201):
        assert api_budget_service.has_budget("serper") is False   # accounting
        assert api_budget_service.serper_gate_allows() is True    # but no gate


def test_gate_engages_only_on_a_positive_declared_ceiling(monkeypatch):
    assert api_budget_service._serper_gate_engaged() is False
    monkeypatch.setenv("SERPER_LIFETIME_LIMIT", "250000")
    assert api_budget_service._serper_gate_engaged() is True
    monkeypatch.setenv("SERPER_LIFETIME_LIMIT", "0")
    assert api_budget_service._serper_gate_engaged() is False
    monkeypatch.setenv("SERPER_LIFETIME_LIMIT", "not-a-number")
    assert api_budget_service._serper_gate_engaged() is False


def test_accounting_ceiling_is_unchanged_when_the_gate_is_inert():
    """The packaged 2200 stays a get_remaining()/dashboard number — depletion is
    still VISIBLE (and the 80%-burn alert still fires) before anything blocks."""
    assert api_budget_service._serper_lifetime_limit() == 2200
    with _patch_counter(1000):
        assert api_budget_service.get_remaining("serper") == 1200


@pytest.mark.asyncio
async def test_default_unset_config_still_calls_serper_past_2200():
    """THE regression this whole default-inert design exists for: with the
    DEFAULT (unset) config and the counter over the packaged free-tier ceiling,
    search_web must still dispatch. A gate armed at 2200 would return a benign
    empty here and the product would go dark on a schedule."""
    assert os.environ.get("SERPER_LIFETIME_LIMIT") is None
    resp = _mock_response(200, {"organic": [{"title": "x"}]})
    ctx, calls = _patch_http_counting(resp)
    with _patch_counter(2201), ctx:
        result = await serper_service.search_web("iPhone 16")
    assert calls["n"] == 1, "the DEFAULT config must not darken Serper at 2200"
    assert result["organic"] == [{"title": "x"}]


@pytest.mark.asyncio
async def test_default_unset_config_does_not_darken_the_warmer_path():
    """The warmer drives search_product_prices. Under the default config its
    Serper legs must fire regardless of the free-tier counter — the warmer
    deliberately does not consult has_budget for exactly this reason."""
    ctx, attempts = _patch_no_http()
    with _patch_counter(999999), ctx:
        result = await serper_service.search_product_prices("iPhone 16", country="bh")
    assert attempts["n"] >= 1, "default config must not stop the warmer's spend"
    assert result.get("shopping_region")


def test_gate_config_is_logged_once(monkeypatch, caplog):
    """An operator must be able to SEE whether live spend is gated and at what
    ceiling — otherwise the gate's state is implicit (#60 review, blocking 4:
    'no startup log of the effective ceiling'). One line per process, no spam."""
    monkeypatch.setattr(api_budget_service, "_serper_gate_config_logged", False)
    with caplog.at_level("INFO"), _patch_counter(10):
        api_budget_service.serper_gate_allows()
        api_budget_service.serper_gate_allows()
    assert caplog.text.count("serper spend gate") == 1
    assert "INERT" in caplog.text
    assert "SERPER_LIFETIME_LIMIT" in caplog.text

    caplog.clear()
    monkeypatch.setattr(api_budget_service, "_serper_gate_config_logged", False)
    monkeypatch.setenv("SERPER_LIFETIME_LIMIT", "250000")
    with caplog.at_level("INFO"), _patch_counter(10):
        api_budget_service.serper_gate_allows()
    assert "ENGAGED" in caplog.text
    assert "250000" in caplog.text


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
    """A dead Upstash must never disable Serper (has_budget's own convention).
    Armed, so the fail-open is doing the work rather than the inert default."""
    with _gate_armed(2200), _patch_counter(RuntimeError("upstash down")):
        assert api_budget_service.serper_gate_allows() is True


# --------------------------------------------------------------------------- #
# The warn threshold tracks the EFFECTIVE ceiling (#60 review, blocking 2)     #
# --------------------------------------------------------------------------- #
def test_warn_threshold_is_the_packaged_2000_when_no_ceiling_is_declared():
    """Byte-identical to pre-#60 for the unset env and for every non-serper
    provider."""
    assert api_budget_service._provider_warn_at("serper") == 2000
    assert api_budget_service._provider_warn_at("firecrawl") == 400
    assert api_budget_service._provider_warn_at("scrapedo") == 800
    assert api_budget_service._provider_warn_at("brightdata") == 4000


def test_warn_threshold_scales_with_a_raised_ceiling(monkeypatch):
    monkeypatch.setenv("SERPER_LIFETIME_LIMIT", "250000")
    # same ~91% ratio the packaged 2000/2200 pair encodes
    assert api_budget_service._provider_warn_at("serper") == 2000 * 250000 // 2200


def test_raised_ceiling_does_not_log_a_false_budget_warning(monkeypatch, caplog):
    """The recommended paid-key config logged `[BUDGET] serper budget warning
    (5136/250000)` on EVERY has_budget call — a depletion alarm at 2%
    utilisation, ~10-12 times per compare now that #60 wires the gate into all
    six entry points, on the exact signal an operator uses to spot REAL
    depletion."""
    monkeypatch.setenv("SERPER_LIFETIME_LIMIT", "250000")
    with caplog.at_level("WARNING"), _patch_counter(5136):
        assert api_budget_service.has_budget("serper") is True
    assert "budget warning" not in caplog.text, caplog.text


def test_raised_ceiling_still_warns_near_the_real_ceiling(monkeypatch, caplog):
    """...and the warning is not merely deleted: it still fires at ~91% of the
    DECLARED ceiling, so real depletion of a paid key is still signalled."""
    monkeypatch.setenv("SERPER_LIFETIME_LIMIT", "250000")
    with caplog.at_level("WARNING"), _patch_counter(240000):
        assert api_budget_service.has_budget("serper") is True
    assert "budget warning" in caplog.text


def test_default_ceiling_still_warns_at_the_packaged_2000(caplog):
    with caplog.at_level("WARNING"), _patch_counter(2050):
        assert api_budget_service.has_budget("serper") is True
    assert "budget warning (2050/2200)" in caplog.text


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
    with _gate_armed(2200), _patch_counter(10):
        assert serper_service._serper_budget_ok() is True
    serper_service.reset_serper_budget_cache()
    with _gate_armed(2200), _patch_counter(2500):
        assert serper_service._serper_budget_ok() is False


def test_serper_budget_ok_fails_open_when_the_gate_raises():
    with patch.object(
        serper_service, "serper_gate_allows", side_effect=RuntimeError("boom")
    ):
        assert serper_service._serper_budget_ok() is True


# --------------------------------------------------------------------------- #
# The gate decision is MEMOISED (#60 review, blocking 3)                       #
#                                                                              #
# serper_gate_allows -> has_budget -> cache_service._redis_get is a BLOCKING    #
# Upstash REST round trip (~163ms) on the single asyncio event loop. Six entry  #
# points x ~10-12 calls per compare INSIDE the 15s price race is the exact      #
# stall class structured_comparison_service._cache_get_async /                  #
# ENABLE_ASYNC_REDIS_OFFLOAD exist to remove (#71).                             #
# --------------------------------------------------------------------------- #
def test_gate_decision_is_memoised_so_repeat_calls_do_not_hit_redis():
    with _gate_armed(2200), _patch_counter(10) as redis_get:
        for _ in range(12):
            assert serper_service._serper_budget_ok() is True
    assert redis_get.call_count == 1, (
        "12 entry-point gate checks must cost ONE blocking Upstash round trip, "
        f"not {redis_get.call_count} — that is the #71 event-loop stall class"
    )


@pytest.mark.asyncio
async def test_six_entry_points_share_one_gate_round_trip():
    """End to end: a compare touching every entry point pays for one read."""
    resp = _mock_response(200, {"organic": [], "shopping": [], "videos": [],
                                "images": [], "news": []})
    ctx, _calls = _patch_http_counting(resp)
    with _gate_armed(2200), _patch_counter(10) as redis_get, ctx:
        await serper_service.search_web("q")
        await serper_service.search_product_prices("q", country="bh")
        await serper_service.search_price_organic("q", country="bh")
        await serper_service.search_videos("q")
        await serper_service.search_images("q")
        await serper_service.search_news("q")
    assert redis_get.call_count == 1, (
        f"expected 1 memoised gate read across six entry points, got "
        f"{redis_get.call_count}"
    )


def test_memo_expires_so_a_depleted_key_is_noticed():
    """The memo must be a short TTL, not a permanent latch: an OPEN decision has
    to expire or the gate could never close mid-process."""
    with _gate_armed(2200), _patch_counter(10) as redis_get:
        assert serper_service._serper_budget_ok() is True
        assert redis_get.call_count == 1
        # travel past the TTL
        expires_at, allowed = serper_service._serper_gate_cache
        serper_service._serper_gate_cache = (expires_at - 10_000.0, allowed)
        assert serper_service._serper_budget_ok() is True
        assert redis_get.call_count == 2


def test_memo_can_be_disabled_by_a_zero_ttl(monkeypatch):
    monkeypatch.setenv("SERPER_GATE_CACHE_TTL", "0")
    with _gate_armed(2200), _patch_counter(10) as redis_get:
        for _ in range(3):
            assert serper_service._serper_budget_ok() is True
    assert redis_get.call_count == 3
    assert serper_service._serper_gate_cache is None


def test_inert_gate_never_reads_redis_at_all():
    """Under the DEFAULT config the gate short-circuits before has_budget, so
    the blocking round trip does not happen even once."""
    with _patch_counter(10) as redis_get:
        assert serper_service._serper_budget_ok() is True
    assert redis_get.call_count == 0


# --------------------------------------------------------------------------- #
# Budget-out -> ZERO HTTP, ZERO record_usage, benign empty shape               #
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_search_web_budget_out_makes_zero_http_calls():
    ctx, attempts = _patch_no_http()
    with _gate_armed(2200), _patch_counter(2500), ctx:
        with patch.object(serper_service, "record_usage") as rec:
            result = await serper_service.search_web("iPhone 16")
    assert attempts["n"] == 0, "budget-out must not dispatch a Serper POST"
    assert result["organic"] == []
    assert result.get("error")
    rec.assert_not_called()


@pytest.mark.asyncio
async def test_search_product_prices_budget_out_makes_zero_http_calls():
    ctx, attempts = _patch_no_http()
    with _gate_armed(2200), _patch_counter(2500), ctx:
        with patch.object(serper_service, "record_usage") as rec:
            result = await serper_service.search_product_prices("iPhone 16", country="bh")
    assert attempts["n"] == 0, "budget-out must not dispatch a Serper POST"
    assert result["shopping"] == []
    assert result["organic"] == []
    rec.assert_not_called()


@pytest.mark.asyncio
async def test_search_price_organic_budget_out_makes_zero_http_calls():
    ctx, attempts = _patch_no_http()
    with _gate_armed(2200), _patch_counter(2500), ctx:
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
    with _gate_armed(2200), _patch_counter(2500), ctx:
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
    with _gate_armed(2200), _patch_counter(2500), ctx:
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
    with _gate_armed(2200), _patch_counter(2500), ctx:
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
    with _gate_armed(2200), _patch_counter(10), ctx:
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
    with _gate_armed(2200), _patch_counter(RuntimeError("upstash down")), ctx:
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
