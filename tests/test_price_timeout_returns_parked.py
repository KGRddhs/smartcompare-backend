"""S3-genuine prod-hardening (team-lead rollback 2026-06-14) — Fix A.

THE PROD REGRESSION (from the prod logs): the Tier-1.5 render wave fired on
gl=us GLOBAL urls (samsung.com/us) → _get_price exceeded the 15s
_PHASE1_TIMEOUTS["price"] cap → the outer wait_for CANCELLED the coroutine → the
Phase-1 handler set result["price"] = None. So prod went from "shows 127.8" to
"shows NO price". The parked converted_fallback was a LOCAL var inside _get_price
— it died with the cancelled stack frame.

THE FIX: _get_price stashes the parked price on a per-request self attribute
(self._parked_price[full_name]) the MOMENT it parks it (early, before the slow
render wave). The Phase-1 timeout/exception handler reads it and returns it
instead of None. The fallback chain NEVER yields None when a parked price exists.

Drives _fetch_product_data with a _get_price that stashes a parked price then
times out (the price race cap is patched tiny so the test is fast).
"""

import asyncio
import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def service(monkeypatch):
    from app.services import structured_comparison_service as scs_mod
    monkeypatch.setattr(scs_mod, "get_cached", lambda *a, **kw: None)
    monkeypatch.setattr(scs_mod, "set_cached", lambda *a, **kw: None)
    monkeypatch.setattr(
        "app.services.product_data_service.get_cached_price",
        AsyncMock(return_value=None),
    )
    svc = scs_mod.get_comparison_service()
    svc._save_price_to_db = MagicMock()
    return svc


@pytest.mark.asyncio
async def test_price_timeout_returns_parked_not_none(monkeypatch, service):
    """When _get_price stashes a parked converted price then TIMES OUT (the outer
    wait_for cancels it), _fetch_product_data must return the PARKED price, not
    None."""
    from app.services import structured_comparison_service as scs_mod

    # Patch the price race cap tiny so the test doesn't wait 15s.
    monkeypatch.setattr(scs_mod, "_PRICE_RACE_TIMEOUT", 0.3, raising=False)

    parked = {"amount": 127.8, "currency": "BHD", "retailer": "Walmart",
              "source_method": "converted_usd", "estimated": False}

    async def _slow_get_price(brand, name, variant, region, search_query, nocache, category):
        # Stash the parked price EARLY (as the real _get_price will), then hang
        # past the price race cap so the outer wait_for cancels this coroutine.
        full_name = f"{brand} {name} {variant or ''}".strip()
        service._parked_price[full_name] = dict(parked)
        await asyncio.sleep(30)

    monkeypatch.setattr(service, "_get_price", _slow_get_price)
    # Stub specs/reviews/image so only the price task is exercised + fast.
    monkeypatch.setattr(service, "_get_specs", AsyncMock(return_value={"specs": {}}))
    monkeypatch.setattr(service, "_get_reviews", AsyncMock(return_value={"reviews": []}))
    monkeypatch.setattr(
        "app.services.structured_comparison_service.get_product_image_url",
        AsyncMock(return_value=None),
    )

    result = await service._fetch_product_data(
        {"brand": "Apple", "name": "iPhone 15", "variant": "128GB",
         "category": "electronics", "search_query": "Apple iPhone 15 128GB"},
        region="bahrain", include_specs=True, include_reviews=True, nocache=True,
    )

    price = result.get("price")
    assert price is not None, "price-task timeout must fall back to the parked price, not None"
    assert price.get("amount") == pytest.approx(127.8)
    assert price.get("source_method") == "converted_usd"


@pytest.mark.asyncio
async def test_no_parked_price_timeout_still_none(monkeypatch, service):
    """Control: when there's NO parked price (nothing found at all), a price
    timeout still yields None (the INSUFFICIENT_DATA path) — the fix only
    surfaces a parked price that EXISTS, it doesn't fabricate one."""
    from app.services import structured_comparison_service as scs_mod
    monkeypatch.setattr(scs_mod, "_PRICE_RACE_TIMEOUT", 0.3, raising=False)

    async def _slow_get_price_no_park(brand, name, variant, region, search_query, nocache, category):
        await asyncio.sleep(30)  # times out, parks nothing

    monkeypatch.setattr(service, "_get_price", _slow_get_price_no_park)
    monkeypatch.setattr(service, "_get_specs", AsyncMock(return_value={"specs": {}}))
    monkeypatch.setattr(service, "_get_reviews", AsyncMock(return_value={"reviews": []}))
    monkeypatch.setattr(
        "app.services.structured_comparison_service.get_product_image_url",
        AsyncMock(return_value=None),
    )

    result = await service._fetch_product_data(
        {"brand": "Apple", "name": "iPhone 15", "variant": "128GB",
         "category": "electronics", "search_query": "Apple iPhone 15 128GB"},
        region="bahrain", include_specs=True, include_reviews=True, nocache=True,
    )
    assert result.get("price") is None  # no parked price to surface
