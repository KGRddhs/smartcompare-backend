"""WS1 (genuine-bh-latency bundle, D1) — graceful hard-cap behavior tests.

The hard cap on compare_from_text used to return a bare scary
`{success:false, code:"TIMEOUT", error:"We couldn't … Try again."}` for ANY
slow query. D1 changes that:

  - >=1 product has usable data stashed  → best-available PARTIAL
    (success:true, metadata.partial:true), assembled via _build_partial_response.
  - products resolved but neither usable  → INSUFFICIENT_DATA (success:false).
  - nothing usable at all                 → friendly TIMEOUT (success:false,
    code:"TIMEOUT", non-scary copy).

These tests drive the timeout by mocking _compare_from_text_impl to hang AFTER
seeding the partial stash on `self`, so the wrapper's TimeoutError handler runs
against a realistic stash state. No network, no live calls.
"""
import asyncio
import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

import pytest
from unittest.mock import patch

from app.services import structured_comparison_service as scs
from app.services.structured_comparison_service import get_comparison_service


def _fake_product(name: str, *, with_specs=True, with_price=True):
    """Minimal product_data dict matching the shape _fetch_product_data returns
    and build_comparison_response consumes."""
    pd = {
        "brand": "",
        "name": name,
        "full_name": name,
        "category": "fragrances",
    }
    if with_specs:
        pd["specs"] = {"concentration": "EDP", "volume_ml": 100}
    else:
        pd["specs"] = None
    if with_price:
        pd["price"] = {
            "amount": 80.0,
            "currency": "BHD",
            "retailer": "Al Hajis",
            "source_method": "page_scrape_jsonld",
            "url": "https://alhajisbahrain.com/x",
        }
    else:
        pd["price"] = None
    return pd


async def _hang_after(seed_fn):
    """Return an impl stub that seeds the stash via seed_fn(self) then hangs
    past the hard cap so the wrapper's TimeoutError path runs."""
    async def _impl(self, *args, **kwargs):
        seed_fn(self)
        await asyncio.sleep(60)
        return {"success": True}
    return _impl


@pytest.mark.asyncio
async def test_hardcap_returns_partial_when_one_product_has_data(monkeypatch):
    """Both products have specs+price stashed → PARTIAL success:true with
    metadata.partial:true and real prices."""
    monkeypatch.setattr(scs, "STREAM_HARD_CAP_SECONDS", 0.2)
    svc = get_comparison_service()

    def seed(self):
        self._partial_build_ctx = {
            "query": "Tom Ford Ombré Leather vs Tom Ford Tobacco Vanille",
            "region": "bahrain", "from_cache": False, "user_preferences": None,
            "category_used": "fragrances", "category_switched": False,
            "original_category": None,
        }
        self._partial_product_data = [
            _fake_product("Ombré Leather"),
            _fake_product("Tobacco Vanille"),
        ]
        self._partial_scoring_result = None
        self._partial_product_names = None
        self._partial_comparison = None

    async def _impl(self, *a, **k):
        seed(self)
        await asyncio.sleep(60)

    with patch.object(svc, "_compare_from_text_impl", _impl.__get__(svc)):
        result = await svc.compare_from_text("foo vs bar", region="bahrain")

    assert result["success"] is True
    assert result["metadata"]["partial"] is True
    # Both genuine prices survive into the partial.
    prods = result["overview"]["products"]
    assert prods[0]["price"]["amount"] == 80.0
    assert prods[0]["price"]["source_method"] == "page_scrape_jsonld"


@pytest.mark.asyncio
async def test_hardcap_partial_with_scoring_and_verdict(monkeypatch):
    """When scoring + verdict also landed before the cap, the partial carries
    the real winner declaration (not the templated fallback)."""
    monkeypatch.setattr(scs, "STREAM_HARD_CAP_SECONDS", 0.2)
    svc = get_comparison_service()

    def seed(self):
        self._partial_build_ctx = {
            "query": "A vs B", "region": "bahrain", "from_cache": False,
            "user_preferences": None, "category_used": "fragrances",
            "category_switched": False, "original_category": None,
        }
        self._partial_product_data = [_fake_product("A"), _fake_product("B")]
        self._partial_scoring_result = {
            "scores": {"product_0": {"overall": 72}, "product_1": {"overall": 60}},
            "winner_index": 0,
            "dimension_winners": {},
            "price_tiers": {},
        }
        self._partial_product_names = ["A", "B"]
        self._partial_comparison = {
            "winner_declaration": "A",
            "winner_reason": "A leads on scent longevity.",
            "winner_index": 0,
        }

    async def _impl(self, *a, **k):
        seed(self)
        await asyncio.sleep(60)

    with patch.object(svc, "_compare_from_text_impl", _impl.__get__(svc)):
        result = await svc.compare_from_text("A vs B", region="bahrain")

    assert result["success"] is True
    assert result["metadata"]["partial"] is True
    assert result["overview"]["winner"]["reason"] == "A leads on scent longevity."
    # Deterministic winner from the stashed scoring_result.
    assert result["overview"]["winner"]["product_index"] == 0


@pytest.mark.asyncio
async def test_hardcap_insufficient_data_when_products_empty(monkeypatch):
    """Products resolved but NEITHER has specs or price → INSUFFICIENT_DATA,
    not a fake partial."""
    monkeypatch.setattr(scs, "STREAM_HARD_CAP_SECONDS", 0.2)
    svc = get_comparison_service()

    def seed(self):
        self._partial_build_ctx = {"query": "x vs y", "region": "bahrain"}
        self._partial_product_data = [
            _fake_product("x", with_specs=False, with_price=False),
            _fake_product("y", with_specs=False, with_price=False),
        ]

    async def _impl(self, *a, **k):
        seed(self)
        await asyncio.sleep(60)

    with patch.object(svc, "_compare_from_text_impl", _impl.__get__(svc)):
        result = await svc.compare_from_text("x vs y", region="bahrain")

    assert result["success"] is False
    assert result["code"] == "INSUFFICIENT_DATA"


@pytest.mark.asyncio
async def test_hardcap_timeout_when_nothing_stashed(monkeypatch):
    """No product data stashed at all (cap fired during/before Phase 1) →
    friendly TIMEOUT body, non-scary copy."""
    monkeypatch.setattr(scs, "STREAM_HARD_CAP_SECONDS", 0.2)
    svc = get_comparison_service()

    async def _impl(self, *a, **k):
        # Note: does NOT seed any stash (mirrors a cap during Phase 1).
        await asyncio.sleep(60)

    with patch.object(svc, "_compare_from_text_impl", _impl.__get__(svc)):
        result = await svc.compare_from_text("foo vs bar", region="bahrain")

    assert result["success"] is False
    assert result["code"] == "TIMEOUT"


@pytest.mark.asyncio
async def test_hardcap_timeout_copy_has_no_forbidden_vocab(monkeypatch):
    """Every timeout-path body (TIMEOUT + INSUFFICIENT_DATA) must be free of
    scary vocab — no 'couldn't' / 'try again' / 'Failed to'."""
    monkeypatch.setattr(scs, "STREAM_HARD_CAP_SECONDS", 0.2)
    svc = get_comparison_service()

    async def _impl(self, *a, **k):
        await asyncio.sleep(60)

    with patch.object(svc, "_compare_from_text_impl", _impl.__get__(svc)):
        result = await svc.compare_from_text("foo vs bar", region="bahrain")

    msg = (result.get("error") or "").lower()
    assert "couldn't" not in msg
    assert "try again" not in msg
    assert "failed to" not in msg
    # And the module-level constant itself is clean.
    clean = scs.TIMEOUT_FRIENDLY_MESSAGE.lower()
    assert "couldn't" not in clean and "try again" not in clean


@pytest.mark.asyncio
async def test_fast_result_passes_through_unchanged(monkeypatch):
    """A fast successful impl is delegated verbatim — no partial marker."""
    svc = get_comparison_service()

    async def _impl(self, *a, **k):
        return {"success": True, "marker": "fast", "metadata": {}}

    with patch.object(svc, "_compare_from_text_impl", _impl.__get__(svc)):
        result = await svc.compare_from_text("foo vs bar", region="bahrain")

    assert result["marker"] == "fast"
    assert result.get("metadata", {}).get("partial") is not True
