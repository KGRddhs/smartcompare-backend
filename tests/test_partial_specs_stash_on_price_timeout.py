"""Launch degradation fix (2026-07-06) — EARLY identity+specs stash salvage.

The "This one's not loading" dead-end: a compare of two local-brand products
(e.g. "Ajmal Aristocrat vs Rasasi Hawas") whose prices both hang past the
STREAM_HARD_CAP was returning HTTP 503 / STREAM_TIMEOUT with ZERO products —
discarding the specs the LLM had ALREADY produced. The fix stashes each
product's identity+specs into a per-request buffer the instant they land, so the
hard-cap handler assembles a best-available PARTIAL (success:true, specs +
templated verdict) instead of a scary dead-end.

Unlike tests/test_timeout_partial_integration.py (which mocks _fetch_product_data
WHOLESALE and so never exercises the in-method stash), these tests mock only the
INNER phase-1 methods (_get_specs fast, _get_price hangs) so the REAL
_fetch_product_data runs its buffer registration + specs done-callback — the
exact machinery the salvage depends on.

Covers, both directions:
  - specs land + price hangs  -> success:true PARTIAL with specs (sync + stream)
  - specs AND price hang       -> INSUFFICIENT_DATA (sync) / STREAM_TIMEOUT (stream)
                                  (the fix salvages only what LANDED; it is not a
                                  deadline extension)
  - flag OFF (ENABLE_EARLY_SPECS_STASH=false) -> byte-identical pre-fix bodies
  - the _partial_* buffer fallback predicate in isolation
No network: Serper/GPT/Redis/image are all mocked.
"""
import asyncio
import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")
os.environ.setdefault("ADMIN_API_KEY", "test-admin-key")

from contextlib import contextmanager
from unittest.mock import AsyncMock, patch

import pytest

import app.services.structured_comparison_service as scs
from app.services.structured_comparison_service import get_comparison_service


_SPECS = {"concentration": "EDP", "volume_ml": 100, "scent_family": "woody"}


@contextmanager
def _mock_phase1(svc, *, specs_hangs=False, price_hangs=True):
    """Patch ONLY the inner phase-1 machinery so the REAL _fetch_product_data
    runs (and its early-stash buffer + specs done-callback fire). Category
    resolution is stubbed to a fixed fragrances pair; every network touch is
    mocked. `explicit_pair` at the call site skips parse_product_query (no GPT)."""

    async def _specs(*_a, **_k):
        if specs_hangs:
            await asyncio.sleep(40)
        return dict(_SPECS)

    async def _price(*_a, **_k):
        if price_hangs:
            await asyncio.sleep(40)
        return {"amount": 42.0, "currency": "BHD", "source_method": "shopify_json",
                "title": "x", "url": "https://x/p", "retailer": "x", "in_stock": True}

    async def _reviews(*_a, **_k):
        return None

    async def _resolve(*_a, **_k):
        return ("fragrances", False, None)

    with patch.object(svc, "_get_specs", side_effect=_specs), \
            patch.object(svc, "_get_price", side_effect=_price), \
            patch.object(svc, "_get_reviews", side_effect=_reviews), \
            patch.object(svc, "_track_serper_cost", lambda *a, **k: None), \
            patch.object(svc, "_track_gpt_cost", lambda *a, **k: None), \
            patch.object(scs, "_resolve_pair_category", side_effect=_resolve), \
            patch.object(scs, "search_web", AsyncMock(return_value={"organic": [], "shopping": []})), \
            patch.object(scs, "get_cached", lambda *a, **k: None), \
            patch.object(scs, "get_product_image_url", AsyncMock(return_value=None)):
        yield


# ===========================================================================
# Layer A — the buffer-fallback predicate in isolation (no pipeline).
# ===========================================================================
class TestEarlyBufferFallbackPredicate:
    def test_has_usable_falls_back_to_early_buffer(self):
        svc = get_comparison_service()
        svc._partial_product_data = None  # post-gather stash never set (mid-gather cancel)
        svc._early_specs_buffer = [
            {"name": "A", "specs": dict(_SPECS), "price": None},
            {"name": "B", "specs": None, "price": None},
        ]
        assert svc._partial_has_usable_data() is True  # A has specs

    def test_both_empty_early_buffer_is_not_usable(self):
        svc = get_comparison_service()
        svc._partial_product_data = None
        svc._early_specs_buffer = [
            {"name": "A", "specs": None, "price": None},
            {"name": "B", "specs": None, "price": None},
        ]
        assert svc._partial_has_usable_data() is False

    def test_post_gather_stash_takes_precedence(self):
        """When _partial_product_data IS set it wins over the early buffer, so
        the existing sync tests (which seed _partial_product_data directly) are
        unaffected."""
        svc = get_comparison_service()
        svc._partial_product_data = [{"name": "P", "specs": None, "price": {"amount": 5.0}}]
        svc._early_specs_buffer = [{"name": "Q", "specs": None, "price": None}]
        assert svc._partial_has_usable_data() is True  # from _partial_product_data

    def test_empty_slots_compacted(self):
        svc = get_comparison_service()
        svc._early_specs_buffer = [None, {"name": "B", "specs": dict(_SPECS)}]
        got = svc._early_specs_buffer_list()
        assert len(got) == 1 and got[0]["name"] == "B"

    def test_build_partial_response_uses_early_buffer(self):
        svc = get_comparison_service()
        svc._partial_build_ctx = {"query": "A vs B", "region": "bahrain",
                                  "category_used": "fragrances"}
        svc._partial_product_data = None
        svc._partial_scoring_result = None
        svc._partial_comparison = None
        svc._partial_product_names = None
        svc._shopping_items_cache = {}
        svc._early_specs_buffer = [
            {"brand": "Ajmal", "name": "Aristocrat", "full_name": "Ajmal Aristocrat",
             "category": "fragrances", "specs": dict(_SPECS), "price": None},
            {"brand": "Rasasi", "name": "Hawas", "full_name": "Rasasi Hawas",
             "category": "fragrances", "specs": dict(_SPECS), "price": None},
        ]
        resp = svc._build_partial_response(elapsed_seconds=30.0)
        assert resp["success"] is True
        assert resp["metadata"]["partial"] is True
        assert len(resp["overview"]["products"]) == 2


# ===========================================================================
# Layer C — SYNC wrapper hard-cap: the real _fetch_product_data runs, specs
# land, price hangs -> the timeout handler salvages a success:true PARTIAL.
# ===========================================================================
@pytest.mark.asyncio
class TestSyncHardCapSalvagesSpecs:
    async def test_specs_land_price_hangs_returns_partial(self, monkeypatch):
        monkeypatch.setattr(scs, "STREAM_HARD_CAP_SECONDS", 1.0)
        svc = get_comparison_service()
        with _mock_phase1(svc, price_hangs=True):
            result = await svc.compare_from_text(
                "Ajmal Aristocrat vs Rasasi Hawas", region="bahrain",
                explicit_pair=("Ajmal Aristocrat", "Rasasi Hawas"),
            )
        assert result["success"] is True
        assert result["metadata"]["partial"] is True
        assert result.get("code") not in ("TIMEOUT", "STREAM_TIMEOUT", "INSUFFICIENT_DATA")
        assert len(result["overview"]["products"]) == 2
        # The salvage came from the early buffer: both slots carry the landed specs.
        assert svc._early_specs_buffer[0]["specs"] == _SPECS
        assert svc._early_specs_buffer[1]["specs"] == _SPECS
        # Specs surface in the rendered response.
        assert any(p.get("specs") for p in result["specs"]["products"])

    async def test_price_lands_specs_hang_returns_partial(self, monkeypatch):
        """OPPOSITE direction (coverage-review MEDIUM): specs hang but a genuine
        price lands -> the price done-callback stashes it -> success:true PARTIAL
        carrying the price, NOT a dead-end. (BLOCKER 2 makes local-brand prices
        land fast via shopify_gcc while the GPT specs call lags, so this direction
        is real.)"""
        monkeypatch.setattr(scs, "STREAM_HARD_CAP_SECONDS", 1.0)
        svc = get_comparison_service()
        with _mock_phase1(svc, specs_hangs=True, price_hangs=False):
            result = await svc.compare_from_text(
                "Ajmal Aristocrat vs Rasasi Hawas", region="bahrain",
                explicit_pair=("Ajmal Aristocrat", "Rasasi Hawas"),
            )
        assert result["success"] is True
        assert result["metadata"]["partial"] is True
        assert result.get("code") not in ("TIMEOUT", "STREAM_TIMEOUT", "INSUFFICIENT_DATA")
        # The salvage came from the price done-callback: both slots carry the price.
        assert svc._early_specs_buffer[0]["price"]["amount"] == 42.0
        assert svc._early_specs_buffer[1]["price"]["amount"] == 42.0

    async def test_both_hang_falls_through_to_insufficient_data(self, monkeypatch):
        """specs AND price hang -> identity stashed (products resolved) but no
        usable data -> INSUFFICIENT_DATA, NOT a fake partial and NOT a bare TIMEOUT."""
        monkeypatch.setattr(scs, "STREAM_HARD_CAP_SECONDS", 1.0)
        svc = get_comparison_service()
        with _mock_phase1(svc, specs_hangs=True, price_hangs=True):
            result = await svc.compare_from_text(
                "Ajmal Aristocrat vs Rasasi Hawas", region="bahrain",
                explicit_pair=("Ajmal Aristocrat", "Rasasi Hawas"),
            )
        assert result["success"] is False
        assert result["code"] == "INSUFFICIENT_DATA"

    async def test_flag_off_is_byte_identical_timeout(self, monkeypatch):
        """ENABLE_EARLY_SPECS_STASH=false -> buffer never populated -> the pre-fix
        body (graceful TIMEOUT, no salvage) exactly as before the change."""
        monkeypatch.setattr(scs, "STREAM_HARD_CAP_SECONDS", 1.0)
        monkeypatch.setenv("ENABLE_EARLY_SPECS_STASH", "false")
        svc = get_comparison_service()
        with _mock_phase1(svc, price_hangs=True):
            result = await svc.compare_from_text(
                "Ajmal Aristocrat vs Rasasi Hawas", region="bahrain",
                explicit_pair=("Ajmal Aristocrat", "Rasasi Hawas"),
            )
        assert result["success"] is False
        assert result["code"] == "TIMEOUT"
        assert "partial" not in (result.get("metadata") or {})
        # Buffer stayed empty (flag off) — no registration happened.
        assert svc._early_specs_buffer == [None, None]


# ===========================================================================
# Layer D — STREAM hard-cap: the SSE path now yields a success:true PARTIAL
# carrying specs (was: zero-product STREAM_TIMEOUT).
# ===========================================================================
@pytest.mark.asyncio
class TestStreamHardCapSalvagesSpecs:
    async def _drive(self, svc):
        events = []
        async for ev, data in svc.compare_from_text_streaming(
            query="Ajmal Aristocrat vs Rasasi Hawas", region="bahrain",
            explicit_pair=("Ajmal Aristocrat", "Rasasi Hawas"),
        ):
            events.append((ev, data))
            if ev == "complete":
                break
        return events

    async def test_specs_land_price_hangs_yields_partial(self, monkeypatch):
        monkeypatch.setattr(scs, "STREAM_HARD_CAP_SECONDS", 1.0)
        svc = get_comparison_service()
        with _mock_phase1(svc, price_hangs=True):
            events = await self._drive(svc)
        terminal = [d for (t, d) in events if t in ("settle_complete", "complete")]
        assert terminal, f"no terminal event; got {[t for t, _ in events]}"
        body = terminal[-1]
        assert body["success"] is True
        assert body["metadata"]["partial"] is True
        assert len(body["overview"]["products"]) == 2
        assert body.get("code") not in ("TIMEOUT", "STREAM_TIMEOUT", "INSUFFICIENT_DATA")

    async def test_price_lands_specs_hang_yields_partial(self, monkeypatch):
        """Stream OPPOSITE direction: specs hang, price lands -> success:true
        PARTIAL carrying the price (via the price done-callback)."""
        monkeypatch.setattr(scs, "STREAM_HARD_CAP_SECONDS", 1.0)
        svc = get_comparison_service()
        with _mock_phase1(svc, specs_hangs=True, price_hangs=False):
            events = await self._drive(svc)
        body = [d for (t, d) in events if t in ("settle_complete", "complete")][-1]
        assert body["success"] is True
        assert body["metadata"]["partial"] is True
        assert body.get("code") not in ("TIMEOUT", "STREAM_TIMEOUT", "INSUFFICIENT_DATA")
        assert svc._early_specs_buffer[0]["price"]["amount"] == 42.0

    async def test_both_hang_yields_stream_timeout(self, monkeypatch):
        """specs AND price hang on the stream path -> the EXISTING STREAM_TIMEOUT
        body (success:false, partial:true, zero products) is preserved."""
        monkeypatch.setattr(scs, "STREAM_HARD_CAP_SECONDS", 1.0)
        svc = get_comparison_service()
        with _mock_phase1(svc, specs_hangs=True, price_hangs=True):
            events = await self._drive(svc)
        terminal = [d for (t, d) in events if t in ("settle_complete", "complete")]
        assert terminal
        body = terminal[-1]
        assert body["success"] is False
        assert body["code"] == "STREAM_TIMEOUT"

    async def test_flag_off_stream_is_byte_identical(self, monkeypatch):
        monkeypatch.setattr(scs, "STREAM_HARD_CAP_SECONDS", 1.0)
        monkeypatch.setenv("ENABLE_EARLY_SPECS_STASH", "false")
        svc = get_comparison_service()
        with _mock_phase1(svc, price_hangs=True):
            events = await self._drive(svc)
        body = [d for (t, d) in events if t in ("settle_complete", "complete")][-1]
        assert body["success"] is False
        assert body["code"] == "STREAM_TIMEOUT"
        assert svc._early_specs_buffer == [None, None]
