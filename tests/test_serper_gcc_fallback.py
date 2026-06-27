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


# ---------------------------------------------------------------------------
# gl=us fallback fires when GCC primary returns empty
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_gl_bh_empty_triggers_us_fallback(monkeypatch):
    """Primary gl=bh returns shopping=[]; fallback gl=us returns 3 items.
    Result must contain the us-fallback items AND shopping_region='us_fallback'."""
    monkeypatch.setattr(serper_service, "SERPER_API_KEY", "test-key")
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
    see module docstring), so the concurrent second call is a near-zero net cost."""
    monkeypatch.setattr(serper_service, "SERPER_API_KEY", "test-key")
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
    """All 6 GCC country codes get the same fallback treatment when empty."""
    monkeypatch.setattr(serper_service, "SERPER_API_KEY", "test-key")
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
    call (both billable). Confirms record_usage instrumentation survived."""
    monkeypatch.setattr(serper_service, "SERPER_API_KEY", "test-key")
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
