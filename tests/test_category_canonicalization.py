"""Tests for canonicalize_category() — the keystone fix.

The product `category` string from the LLM (e.g. "Fragrances", capital F) was
never normalized, but every downstream lookup (CATEGORY_DIMENSIONS,
CATEGORY_SPEC_SCHEMAS, CATEGORY_PRIORITY_ADJUSTMENTS) keys on lowercase canonical
strings. So "Fragrances" failed exact-match and silently fell back to "other",
whose dimensions include build_score -> "Build" dimension on a perfume.

canonicalize_category() normalizes once: case-fold, strip, synonym-map, and
singular/plural tolerance onto the 9 canonical keys, returning "other" for
None / non-str / unknown.
"""
import pytest

from app.services.extraction_service import canonicalize_category


@pytest.mark.parametrize("raw,expected", [
    # The keystone case: capital F fragrance
    ("Fragrances", "fragrances"),
    ("Fragrance", "fragrances"),
    ("perfume", "fragrances"),
    ("Perfume", "fragrances"),
    # Electronics + synonyms
    ("ELECTRONICS", "electronics"),
    ("smartphone", "electronics"),
    # Whitespace + case
    ("  Skincare ", "skincare"),
    # Makeup spacing variants
    ("Make Up", "makeup"),
    # Unknown / empty / None -> other
    ("totally-unknown-thing", "other"),
    ("", "other"),
    (None, "other"),
])
def test_canonicalize_category(raw, expected):
    assert canonicalize_category(raw) == expected


@pytest.mark.parametrize("raw,expected", [
    # All 9 canonical keys must round-trip to themselves (already-correct unchanged)
    ("electronics", "electronics"),
    ("grocery", "grocery"),
    ("supplements", "supplements"),
    ("makeup", "makeup"),
    ("skincare", "skincare"),
    ("haircare", "haircare"),
    ("fragrances", "fragrances"),
    ("fashion", "fashion"),
    ("other", "other"),
])
def test_canonical_keys_roundtrip_unchanged(raw, expected):
    assert canonicalize_category(raw) == expected


@pytest.mark.parametrize("raw,expected", [
    # Fragrance synonyms
    ("cologne", "fragrances"),
    ("edp", "fragrances"),
    ("edt", "fragrances"),
    # Electronics synonyms
    ("phone", "electronics"),
    ("mobile", "electronics"),
    ("laptop", "electronics"),
    ("tablet", "electronics"),
    ("gadget", "electronics"),
    # Makeup synonyms
    ("make-up", "makeup"),
    ("cosmetics", "makeup"),
    # Multi-word -> hyphenless canonical
    ("hair care", "haircare"),
    ("skin care", "skincare"),
    # Singular -> plural canonical
    ("supplement", "supplements"),
    # Plural -> singular canonical
    ("groceries", "grocery"),
])
def test_canonicalize_category_synonyms(raw, expected):
    assert canonicalize_category(raw) == expected


def test_canonicalize_category_non_string_returns_other():
    # Defensive: non-str inputs must not raise
    assert canonicalize_category(123) == "other"
    assert canonicalize_category(["fragrances"]) == "other"
    assert canonicalize_category({"category": "fragrances"}) == "other"
