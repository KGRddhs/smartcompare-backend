"""CLEANUP-2 — URL-compare path category coverage + canonical enum.

url_extraction_service.compare_from_urls bypassed _resolve_pair_category and used
a STALE non-canonical category enum (electronics|grocery|beauty|fashion|home|
sports|automotive|other). 'beauty'/'home'/'sports'/'automotive' all canonicalize
to 'other', so a URL-mode makeup/skincare/fragrance compare silently lost its
real category (wrong dims + no like-for-like fairness). Fix:
  (a) the extraction prompt enumerates the 9 CANONICAL keys;
  (b) extract_from_url canonicalizes the LLM-returned category defensively;
  (c) compare_from_urls resolves the pair category (LLM-judgment = parser-analog),
      writes it back onto products[i]['category'], and passes it to
      generate_comparison(category=...).
"""
import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from app.services import url_extraction_service as ues
from app.services.extraction_service import CATEGORY_SPEC_SCHEMAS


_CANONICAL = set(CATEGORY_SPEC_SCHEMAS.keys())  # the 9 keys, source of truth


# ============================================
# (a) prompt enumerates the 9 canonical keys, not the stale enum
# ============================================

def test_extraction_prompt_uses_canonical_categories():
    # The stale tokens must be gone; the canonical-only ones present.
    blob = ues.URL_EXTRACTION_PROMPT
    for stale in ("beauty", "automotive", "sports", "|home|"):
        assert stale not in blob, f"stale non-canonical category token still present: {stale!r}"
    # canonical fragrance/skincare/makeup keys must be offered to the LLM
    for canon in ("fragrances", "skincare", "makeup", "supplements", "haircare"):
        assert canon in blob, f"canonical category {canon!r} not offered in the prompt"


# ============================================
# (b) normalize_product_data canonicalizes the returned category
# ============================================

def _fake_raw(category):
    return {
        "brand": "Tom Ford", "title": "Tom Ford Oud Wood EDP", "name": "Oud Wood",
        "price": 80.0, "currency": "BHD", "category": category, "variant": "100ml",
        "specs": {"concentration": "EDP"}, "rating": 4.5, "review_count": 100,
        "in_stock": True,
    }


@pytest.mark.parametrize("raw_cat,expected", [
    ("Fragrances", "fragrances"),
    ("beauty", "other"),        # non-canonical -> other (no false mapping)
    ("Skincare", "skincare"),
    ("makeup", "makeup"),
    ("ELECTRONICS", "electronics"),
    (None, "other"),
])
def test_normalize_product_data_canonicalizes_category(raw_cat, expected):
    retailer = {"name": "alhaji", "currency": "BHD", "key": "generic"}
    product = ues.normalize_product_data(
        _fake_raw(raw_cat), retailer, "https://alhaji.example/oud-wood"
    )
    assert product["category"] == expected


# ============================================
# (c) compare_from_urls resolves + writes back + passes category to the verdict
# ============================================

def test_compare_from_urls_writes_back_and_passes_category():
    frag_a = {"success": True, "product": {
        "brand": "Tom Ford", "name": "Oud Wood", "full_name": "Tom Ford Oud Wood",
        "category": "fragrances", "price": {"amount": 80, "currency": "BHD"},
        "specs": {}, "reviews": {}, "variant": "100ml"}}
    frag_b = {"success": True, "product": {
        "brand": "Creed", "name": "Aventus", "full_name": "Creed Aventus",
        "category": "fragrances", "price": {"amount": 120, "currency": "BHD"},
        "specs": {}, "reviews": {}, "variant": "100ml"}}

    captured = {}

    async def fake_generate(p0, p1, region, *a, **k):
        captured["category"] = k.get("category")
        captured["p0_cat"] = p0.get("category")
        captured["p1_cat"] = p1.get("category")
        return {"winner_index": 0, "recommendation": "x", "key_differences": []}

    async def fake_extract(url):
        return frag_a if "oud" in url else frag_b

    with patch.object(ues, "extract_from_url", side_effect=fake_extract), \
         patch("app.services.extraction_service.generate_comparison", side_effect=fake_generate):
        resp = asyncio.run(ues.compare_from_urls(
            "https://x.example/oud-wood", "https://x.example/aventus"
        ))

    assert resp["success"] is True
    # The verdict was told the resolved category (not the 'other' default).
    assert captured.get("category") == "fragrances", (
        f"generate_comparison was not passed the resolved category: {captured.get('category')!r}"
    )
    # Both products carry the resolved category (write-back).
    assert captured.get("p0_cat") == "fragrances"
    assert captured.get("p1_cat") == "fragrances"


def test_compare_from_urls_canonicalizes_legacy_category_before_verdict():
    # Products arrive with a capital-F category (legacy) -> canonicalized before scoring.
    prod_a = {"success": True, "product": {
        "brand": "A", "name": "X", "full_name": "A X", "category": "Fragrances",
        "price": {"amount": 80, "currency": "BHD"}, "specs": {}, "reviews": {}}}
    prod_b = {"success": True, "product": {
        "brand": "B", "name": "Y", "full_name": "B Y", "category": "Fragrances",
        "price": {"amount": 90, "currency": "BHD"}, "specs": {}, "reviews": {}}}

    captured = {}

    async def fake_generate(p0, p1, region, *a, **k):
        captured["category"] = k.get("category")
        return {"winner_index": 0, "recommendation": "", "key_differences": []}

    async def fake_extract(url):
        return prod_a if url.endswith("a") else prod_b

    with patch.object(ues, "extract_from_url", side_effect=fake_extract), \
         patch("app.services.extraction_service.generate_comparison", side_effect=fake_generate):
        resp = asyncio.run(ues.compare_from_urls("https://x/a", "https://x/b"))

    assert resp["success"] is True
    assert captured.get("category") == "fragrances"
