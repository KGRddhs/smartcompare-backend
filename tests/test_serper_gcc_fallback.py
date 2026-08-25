"""Bundle C § 1c A.3.3-fix-2 — GCC → US shopping fallback.

Per diagnostic curls (Session 52): Serper Shopping returns empty
`shopping: []` for `gl=bh|sa|ae|kw|qa|om` system-wide, even on
mainstream queries (iPhone 16, CeraVe, Centrum) — Google Shopping
has no Bahrain merchant feed for these products.

Lever (a) per spec § 1c: when GCC primary call returns empty, retry
once with `gl=us`. Downstream `price_service` converts USD→BHD via
the existing `exchange_rate_service` and tags `source_method:
'converted_usd'`. NOT speculative — qa-bundle-c approved after
diagnostic curl evidence.

Operational stopgap: this fallback is intended to hold UNTIL Google
Shopping's Bahrain merchant feed catches up. The `shopping_region`
field on the response identifies which region the items came from
so admin dashboards can monitor fallback rate.
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from app.services import serper_service


def _mock_response(status_code: int, json_data: dict) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = Exception(f"HTTP {status_code}")
    return resp


def _patch_httpx_sequence(responses):
    """Patch httpx.AsyncClient to return responses[0], [1], ... in order
    across successive .post() calls."""
    call_count = {"n": 0}

    class _AsyncClient:
        def __init__(self, *args, **kwargs):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            return False
        async def post(self, *args, **kwargs):
            r = responses[call_count["n"]]
            call_count["n"] += 1
            return r

    return patch(
        "app.services.serper_service.httpx.AsyncClient",
        _AsyncClient,
    ), call_count


def _patch_httpx_capture(responses):
    """Like _patch_httpx_sequence but also records the `gl` of each POST body so
    a test can assert WHICH shopping leg fired (#60 drops the dead gl=<gcc> leg)."""
    state = {"n": 0, "gl": []}

    class _AsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url=None, headers=None, json=None):
            state["gl"].append((json or {}).get("gl"))
            r = responses[state["n"]]
            state["n"] += 1
            return r

    return patch(
        "app.services.serper_service.httpx.AsyncClient",
        _AsyncClient,
    ), state


# #60 — every test in this module asserts SHOPPING-LEG behaviour, not budget
# behaviour. Stub the Redis counter read so the new serper budget gate is
# deterministically OPEN and no assertion here depends on the live Upstash
# lifetime counter.
@pytest.fixture(autouse=True)
def _budget_gate_open():
    from app.services import api_budget_service

    with patch.object(api_budget_service, "_redis_get", return_value=None):
        yield


# #60 — the always-fired gl=<gcc> primary is dropped by default. The env
# allow-list below is the rollback flip that restores the legacy two-leg
# behaviour (and is what the pre-#60 tests in this module now exercise).
_ALLOWLIST_ENV = "SERPER_SHOPPING_PRIMARY_COUNTRIES"


@pytest.fixture(autouse=True)
def _clean_allowlist(monkeypatch):
    monkeypatch.delenv(_ALLOWLIST_ENV, raising=False)


# ---------------------------------------------------------------------------
# #60 — DEFAULT: the dead gl=<gcc> primary is NOT purchased
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_gcc_default_fires_only_the_us_leg(monkeypatch):
    """Google has NO GCC shopping feed (module docstring: gl=bh|sa|ae|kw|qa|om
    return empty system-wide), so the gl=<gcc> primary was one credit per
    product per compare bought to satisfy a branch the code knows is dead.
    Default is now a SINGLE gl=us call."""
    monkeypatch.setattr(serper_service, "SERPER_API_KEY", "test-key")
    us_full = _mock_response(200, {"shopping": [{"title": "iPhone 16", "price": "$529.00"}]})
    ctx, state = _patch_httpx_capture([us_full])
    with ctx:
        result = await serper_service.search_product_prices("iPhone 16", country="bh")
    assert state["n"] == 1, "the dead gl=bh leg must not be purchased"
    assert state["gl"] == ["us"]
    assert len(result["shopping"]) == 1
    assert result.get("shopping_region") == "us_fallback"


@pytest.mark.asyncio
@pytest.mark.parametrize("gcc_country", ["bh", "sa", "ae", "kw", "qa", "om"])
async def test_gcc_default_single_leg_for_every_gcc_country(gcc_country, monkeypatch):
    """All 6 GCC codes were covered by the same diagnostic (empty system-wide),
    so all 6 drop the primary leg."""
    monkeypatch.setattr(serper_service, "SERPER_API_KEY", "test-key")
    us_full = _mock_response(200, {"shopping": [{"title": "x", "price": "$10"}]})
    ctx, state = _patch_httpx_capture([us_full])
    with ctx:
        result = await serper_service.search_product_prices("test", country=gcc_country)
    assert state["gl"] == ["us"]
    assert result.get("shopping_region") == "us_fallback"


@pytest.mark.asyncio
async def test_gcc_default_records_usage_exactly_once(monkeypatch):
    """One leg = one billable credit (was two).

    TWO responses are queued deliberately: if a second leg still fired it would
    get a real 200 and bump the meter, so this fails loudly rather than passing
    because the stub ran out of responses."""
    monkeypatch.setattr(serper_service, "SERPER_API_KEY", "test-key")
    us_full = _mock_response(200, {"shopping": [{"title": "x", "price": "$5"}]})
    ctx, state = _patch_httpx_capture([us_full, us_full])
    with ctx:
        with patch.object(serper_service, "record_usage") as mock_record:
            await serper_service.search_product_prices("test", country="bh")
    assert state["n"] == 1
    assert mock_record.call_count == 1
    assert mock_record.call_args_list[0].args == ("serper",)


@pytest.mark.asyncio
async def test_gcc_default_empty_us_leg_still_tags_us_fallback(monkeypatch):
    """Empty result keeps the SAME shape/tag the both-empty path returned, so
    downstream selection + admin dashboards are unchanged and the cascade falls
    through to Tier 1.5 / 2 / 3."""
    monkeypatch.setattr(serper_service, "SERPER_API_KEY", "test-key")
    us_empty = _mock_response(200, {"shopping": []})
    ctx, state = _patch_httpx_capture([us_empty, us_empty])
    with ctx:
        result = await serper_service.search_product_prices("Almarai laban", country="bh")
    assert state["n"] == 1
    assert state["gl"] == ["us"]
    assert result["shopping"] == []
    assert result.get("shopping_region") == "us_fallback"


# ---------------------------------------------------------------------------
# #60 — ROLLBACK: the per-country allow-list restores the legacy two-leg run
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_allowlist_restores_the_primary_leg(monkeypatch):
    """If Google ever ships a GCC shopping feed, the operator re-enables the
    primary per country via SERPER_SHOPPING_PRIMARY_COUNTRIES — no redeploy."""
    monkeypatch.setattr(serper_service, "SERPER_API_KEY", "test-key")
    monkeypatch.setenv(_ALLOWLIST_ENV, "bh")
    bh_full = _mock_response(200, {"shopping": [{"title": "BH merchant", "price": "BHD 200"}]})
    us_full = _mock_response(200, {"shopping": [{"title": "US", "price": "$529.00"}]})
    ctx, state = _patch_httpx_capture([bh_full, us_full])
    with ctx:
        result = await serper_service.search_product_prices("iPhone 16", country="bh")
    assert state["n"] == 2
    assert sorted(state["gl"]) == ["bh", "us"]
    assert result["shopping"][0]["title"] == "BH merchant"
    assert result.get("shopping_region") == "bh"


@pytest.mark.asyncio
async def test_allowlist_is_per_country_not_global(monkeypatch):
    """A country NOT on the allow-list keeps the single-leg default even when
    another GCC country is allow-listed."""
    monkeypatch.setattr(serper_service, "SERPER_API_KEY", "test-key")
    monkeypatch.setenv(_ALLOWLIST_ENV, "sa")
    us_full = _mock_response(200, {"shopping": [{"title": "US", "price": "$529.00"}]})
    ctx, state = _patch_httpx_capture([us_full])
    with ctx:
        await serper_service.search_product_prices("iPhone 16", country="bh")
    assert state["gl"] == ["us"]


# ---------------------------------------------------------------------------
# gl=us fallback fires when GCC primary returns empty (legacy two-leg run,
# now reachable only via the #60 allow-list rollback flip)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_gl_bh_empty_triggers_us_fallback(monkeypatch):
    """Primary gl=bh returns shopping=[]; fallback gl=us returns 3 items.
    Result must contain the us-fallback items AND shopping_region='us_fallback'."""
    monkeypatch.setattr(serper_service, "SERPER_API_KEY", "test-key")
    monkeypatch.setenv(_ALLOWLIST_ENV, "bh")  # #60 rollback flip: two-leg run
    bh_empty = _mock_response(200, {"shopping": []})
    us_full = _mock_response(200, {"shopping": [
        {"title": "iPhone 16", "price": "$529.00", "source": "Walmart"},
        {"title": "iPhone 16 Plus", "price": "$829.00", "source": "Apple"},
        {"title": "iPhone 16 Refurb", "price": "$609.97", "source": "Best Buy"},
    ]})
    ctx, calls = _patch_httpx_sequence([bh_empty, us_full])
    with ctx:
        result = await serper_service.search_product_prices("iPhone 16", country="bh")
    assert calls["n"] == 2, "expected primary + fallback calls"
    assert len(result["shopping"]) == 3
    assert result.get("shopping_region") == "us_fallback"


@pytest.mark.asyncio
async def test_gl_bh_with_results_prefers_primary(monkeypatch):
    """Genuine-BH starvation fix (2026-06-27): the gl=bh primary and gl=us
    fallback now fire CONCURRENTLY for GCC countries (reclaiming the ~3s the old
    serial fallback stole from the downstream genuine-BH curl fan_out). SELECTION
    is unchanged — when gl=bh returns items they are PREFERRED (genuine local feed)
    and the shopping_region stays 'bh'; the gl=us result is ignored. In production
    gl=bh effectively never returns items (Google has no Bahrain shopping feed —
    see module docstring), so the concurrent second call is a near-zero net cost.

    #60: that "near-zero net cost" was still one purchased credit per product per
    compare, so the primary leg is now OFF by default — this test pins the
    SELECTION rule under the allow-list rollback flip."""
    monkeypatch.setattr(serper_service, "SERPER_API_KEY", "test-key")
    monkeypatch.setenv(_ALLOWLIST_ENV, "bh")
    bh_full = _mock_response(200, {"shopping": [
        {"title": "iPhone 16 from BH merchant", "price": "BHD 200", "source": "noon.com"},
    ]})
    us_full = _mock_response(200, {"shopping": [
        {"title": "iPhone 16 US", "price": "$529.00", "source": "Walmart"},
    ]})
    ctx, calls = _patch_httpx_sequence([bh_full, us_full])
    with ctx:
        result = await serper_service.search_product_prices("iPhone 16", country="bh")
    # Both calls now fire concurrently (no serial skip), but gl=bh wins selection.
    assert len(result["shopping"]) == 1
    assert result["shopping"][0]["title"] == "iPhone 16 from BH merchant"
    assert result.get("shopping_region") == "bh"


@pytest.mark.asyncio
async def test_non_gcc_country_does_not_fallback(monkeypatch):
    """Non-GCC countries don't trigger the gl=us fallback (they ARE us, or
    have their own coverage — fallback only addresses the GCC gap)."""
    monkeypatch.setattr(serper_service, "SERPER_API_KEY", "test-key")
    us_empty = _mock_response(200, {"shopping": []})
    ctx, calls = _patch_httpx_sequence([us_empty])
    with ctx:
        result = await serper_service.search_product_prices("Obscure Item", country="us")
    assert calls["n"] == 1, "non-GCC country should NOT trigger fallback"
    assert result.get("shopping_region") == "us"


@pytest.mark.asyncio
@pytest.mark.parametrize("gcc_country", ["bh", "sa", "ae", "kw", "qa", "om"])
async def test_all_gcc_countries_trigger_fallback_when_empty(gcc_country, monkeypatch):
    """All 6 GCC country codes get the same fallback treatment when empty
    (legacy two-leg run — #60 allow-list rollback flip)."""
    monkeypatch.setattr(serper_service, "SERPER_API_KEY", "test-key")
    monkeypatch.setenv(_ALLOWLIST_ENV, gcc_country)
    primary_empty = _mock_response(200, {"shopping": []})
    us_full = _mock_response(200, {"shopping": [{"title": "x", "price": "$10"}]})
    ctx, calls = _patch_httpx_sequence([primary_empty, us_full])
    with ctx:
        result = await serper_service.search_product_prices("test", country=gcc_country)
    assert calls["n"] == 2
    assert result.get("shopping_region") == "us_fallback"


@pytest.mark.asyncio
async def test_both_empty_returns_empty_without_crashing(monkeypatch):
    """When BOTH primary AND fallback are empty (Saudi-only items like
    Almarai laban), result is empty + tagged primary region — pipeline
    naturally falls through to Tier 1.5 / Tier 2 / Tier 3 downstream."""
    monkeypatch.setattr(serper_service, "SERPER_API_KEY", "test-key")
    monkeypatch.setenv(_ALLOWLIST_ENV, "bh")
    bh_empty = _mock_response(200, {"shopping": []})
    us_empty = _mock_response(200, {"shopping": []})
    ctx, calls = _patch_httpx_sequence([bh_empty, us_empty])
    with ctx:
        result = await serper_service.search_product_prices("Almarai laban", country="bh")
    assert calls["n"] == 2
    assert result["shopping"] == []
    # When both empty, region tag should mark the primary (callers know we tried)
    assert result.get("shopping_region") in {"bh", "us_fallback"}


@pytest.mark.asyncio
async def test_fallback_records_usage_for_both_calls(monkeypatch):
    """A.3.3-fix-1 meter must bump for BOTH the primary + the fallback
    call (both billable). Confirms record_usage instrumentation survived.
    Two legs only fire under the #60 allow-list rollback flip."""
    monkeypatch.setattr(serper_service, "SERPER_API_KEY", "test-key")
    monkeypatch.setenv(_ALLOWLIST_ENV, "bh")
    bh_empty = _mock_response(200, {"shopping": []})
    us_full = _mock_response(200, {"shopping": [{"title": "x", "price": "$5"}]})
    ctx, _ = _patch_httpx_sequence([bh_empty, us_full])
    with ctx:
        with patch.object(serper_service, "record_usage") as mock_record:
            await serper_service.search_product_prices("test", country="bh")
    # Both primary + fallback HTTP 200 → 2 record_usage calls.
    assert mock_record.call_count == 2
    for call in mock_record.call_args_list:
        assert call.args == ("serper",)
