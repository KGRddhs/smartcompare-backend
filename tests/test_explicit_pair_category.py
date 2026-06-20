"""A3/A4: per-product category WRITE-BACK proof (sync + stream).

THE load-bearing proof for this bundle is the CAPTURE test: patch
_fetch_product_data, drive an explicit fragrance pair through compare_from_text
/ compare_from_text_streaming, and assert the captured product_info["category"]
== "fragrances". Scoring (compute_scores reads products_data[0]["category"]),
spec-schema selection, and category-aware source discovery ALL key off the
per-product `category` field via _fetch_product_data -> result["category"] —
NOT `category_used`. So a green fragrance-dims test alone is only a routing
sanity check; the write-back is what this file pins.
"""
import asyncio
import pytest
from unittest.mock import patch

from app.services.structured_comparison_service import get_comparison_service


# ============================================
# A3: SYNC path write-back (the load-bearing proof)
# ============================================

def test_explicit_pair_selected_category_is_authority_sync():
    svc = get_comparison_service()
    captured = []

    async def fake_fetch(product_info, *a, **k):   # _fetch_product_data(self, product_info, region, ...)
        captured.append(dict(product_info))
        raise RuntimeError("stop after capture")   # capture happens BEFORE the raise

    with patch.object(svc, "_fetch_product_data", side_effect=fake_fetch):
        try:
            asyncio.run(svc.compare_from_text(
                query="Tom Ford Soleil Neige 100ml vs Tom Ford Oud Voyager 100ml",
                explicit_pair=("Tom Ford Soleil Neige 100ml", "Tom Ford Oud Voyager 100ml"),
                selected_category="fragrances",
            ))
        except Exception:
            pass

    assert captured, "_fetch_product_data was never reached"
    assert all(c.get("category") == "fragrances" for c in captured), \
        f"per-product category not written back: {[c.get('category') for c in captured]}"


def test_explicit_pair_detection_wins_over_chip_sync():
    # Names carry fragrance words -> detection overrides a wrong electronics chip.
    svc = get_comparison_service()
    captured = []

    async def fake_fetch(product_info, *a, **k):
        captured.append(dict(product_info))
        raise RuntimeError("stop after capture")

    with patch.object(svc, "_fetch_product_data", side_effect=fake_fetch):
        try:
            asyncio.run(svc.compare_from_text(
                query="Dior Sauvage perfume vs Creed Aventus cologne",
                explicit_pair=("Dior Sauvage perfume", "Creed Aventus cologne"),
                selected_category="electronics",   # wrong chip
            ))
        except Exception:
            pass

    assert captured
    assert all(c.get("category") == "fragrances" for c in captured), \
        f"detection should override chip: {[c.get('category') for c in captured]}"


def test_explicit_pair_supplements_still_classified_sync():
    svc = get_comparison_service()
    captured = []

    async def fake_fetch(product_info, *a, **k):
        captured.append(dict(product_info))
        raise RuntimeError("stop after capture")

    with patch.object(svc, "_fetch_product_data", side_effect=fake_fetch):
        try:
            asyncio.run(svc.compare_from_text(
                query="NOW Foods Vitamin D3 vs Solgar Vitamin D3",
                explicit_pair=("NOW Foods Vitamin D3", "Solgar Vitamin D3"),
                selected_category=None,
            ))
        except Exception:
            pass

    assert captured
    assert all(c.get("category") == "supplements" for c in captured), \
        f"supplements not classified: {[c.get('category') for c in captured]}"


def test_explicit_pair_no_chip_no_detection_escalates_via_llm_sync():
    # Brand-only names + no chip -> resolve_category escalates -> classify_category_llm
    # is consulted. Mock it to return fragrances and assert it lands on the products.
    svc = get_comparison_service()
    captured = []

    async def fake_fetch(product_info, *a, **k):
        captured.append(dict(product_info))
        raise RuntimeError("stop after capture")

    async def fake_llm(_texts):
        return "fragrances"

    with patch.object(svc, "_fetch_product_data", side_effect=fake_fetch), \
         patch("app.services.structured_comparison_service.classify_category_llm",
               side_effect=fake_llm):
        try:
            asyncio.run(svc.compare_from_text(
                query="Soleil Neige vs Oud Voyager",
                explicit_pair=("Soleil Neige", "Oud Voyager"),
                selected_category=None,
            ))
        except Exception:
            pass

    assert captured
    assert all(c.get("category") == "fragrances" for c in captured), \
        f"A2b escalation result not written back: {[c.get('category') for c in captured]}"


# ============================================
# A4: STREAMING path write-back + sync/stream parity
# ============================================

def test_streaming_explicit_pair_selected_category_is_authority():
    svc = get_comparison_service()
    captured = []

    async def fake_fetch(product_info, *a, **k):
        captured.append(dict(product_info))
        raise RuntimeError("stop after capture")

    async def drive():
        agen = svc.compare_from_text_streaming(
            query="Tom Ford Soleil Neige 100ml vs Tom Ford Oud Voyager 100ml",
            explicit_pair=("Tom Ford Soleil Neige 100ml", "Tom Ford Oud Voyager 100ml"),
            selected_category="fragrances",
        )
        try:
            async for _ in agen:
                pass
        except Exception:
            pass

    with patch.object(svc, "_fetch_product_data", side_effect=fake_fetch):
        try:
            asyncio.run(drive())
        except Exception:
            pass

    assert captured, "_fetch_product_data was never reached (stream)"
    assert all(c.get("category") == "fragrances" for c in captured), \
        f"per-product category not written back (stream): {[c.get('category') for c in captured]}"


def test_sync_stream_category_parity():
    """Same explicit pair + chip -> same resolved category on both paths."""
    svc = get_comparison_service()

    def capture_sync():
        cap = []

        async def fake_fetch(product_info, *a, **k):
            cap.append(dict(product_info))
            raise RuntimeError("stop")

        with patch.object(svc, "_fetch_product_data", side_effect=fake_fetch):
            try:
                asyncio.run(svc.compare_from_text(
                    query="Dior Sauvage perfume vs Creed Aventus cologne",
                    explicit_pair=("Dior Sauvage perfume", "Creed Aventus cologne"),
                    selected_category=None,
                ))
            except Exception:
                pass
        return [c.get("category") for c in cap]

    def capture_stream():
        cap = []

        async def fake_fetch(product_info, *a, **k):
            cap.append(dict(product_info))
            raise RuntimeError("stop")

        async def drive():
            agen = svc.compare_from_text_streaming(
                query="Dior Sauvage perfume vs Creed Aventus cologne",
                explicit_pair=("Dior Sauvage perfume", "Creed Aventus cologne"),
                selected_category=None,
            )
            try:
                async for _ in agen:
                    pass
            except Exception:
                pass

        with patch.object(svc, "_fetch_product_data", side_effect=fake_fetch):
            try:
                asyncio.run(drive())
            except Exception:
                pass
        return [c.get("category") for c in cap]

    sync_cats = capture_sync()
    stream_cats = capture_stream()
    assert sync_cats and stream_cats
    assert set(sync_cats) == set(stream_cats) == {"fragrances"}, \
        f"sync/stream parity broken: sync={sync_cats} stream={stream_cats}"


# ============================================
# Routing sanity check (NOT the write-back proof — duplicates
# test_category_keystone_scoring.py): fragrance dicts -> fragrance dims.
# ============================================

def test_fragrance_dicts_score_with_fragrance_dims():
    from app.services.scoring_service import ScoringService, CATEGORY_DIMENSIONS
    products = [
        {"brand": "Tom Ford", "name": "A", "category": "fragrances",
         "specs": {"longevity": "8 hours", "concentration": "edp"},
         "price": {"amount": 80, "currency": "BHD"}},
        {"brand": "Creed", "name": "B", "category": "fragrances",
         "specs": {"longevity": "10 hours", "concentration": "edp"},
         "price": {"amount": 90, "currency": "BHD"}},
    ]
    result = ScoringService().compute_scores(products)
    keys = set()
    for pk in ("product_0", "product_1"):
        keys |= set(result["scores"][pk]["breakdown"].keys())
    # fragrance dims present, electronics/other 'build' dim absent
    assert "longevity_score" in keys, f"no longevity dim: {keys}"
    assert "projection_score" in keys, f"no projection dim: {keys}"
    assert "build_score" not in keys, f"build_score leaked into fragrance dims: {keys}"
    assert keys == set(CATEGORY_DIMENSIONS["fragrances"])
