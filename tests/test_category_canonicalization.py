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

from app.services.extraction_service import (
    canonicalize_category,
    classify_category_from_text,
)


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


# ============================================
# A1: classify_category_from_text — deterministic product-type classifier
# ============================================
#
# Cheap $0/no-LLM classifier that recognizes generic category WORDS (perfume,
# cologne, edp, laptop, vitamin, ...) in a free-form product name. A bare
# brand/model with NO category word ("iPhone 15 Pro", "Tom Ford Soleil Neige")
# is EXPECTED to return "other" — the caller resolves it via a user chip or the
# A2b GPT-mini escalation. We do NOT widen the synonym map with brand names.

@pytest.mark.parametrize("text,expected", [
    ("Dior Sauvage perfume", "fragrances"),
    ("Creed Aventus cologne", "fragrances"),
    ("Tom Ford Oud Wood EDP", "fragrances"),        # 'edp' token
    ("NOW Foods Vitamin D3", "supplements"),
    ("gaming laptop", "electronics"),               # 'laptop' token
    ("iPhone 15 Pro", "other"),                     # brand/model only -> other (chip/A2b resolves)
    ("Tom Ford Soleil Neige 100ml", "other"),       # no category word -> other
    ("plain mystery object", "other"),
    ("", "other"),
    (None, "other"),
])
def test_classify_category_from_text(text, expected):
    assert classify_category_from_text(text) == expected


def test_classify_category_from_text_supplement_precedence():
    # is_supplement_query fires before the synonym scan: a multivitamin name with
    # no other category word still classifies as supplements.
    assert classify_category_from_text("Centrum Multivitamin tablets") == "supplements"


def test_classify_category_from_text_non_string_returns_other():
    # Defensive: non-str inputs must not raise.
    assert classify_category_from_text(123) == "other"
    assert classify_category_from_text(["perfume"]) == "other"
