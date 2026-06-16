"""Keystone scoring tests — a capital-F "Fragrances" category must route to the
fragrance scent dimensions, NOT fall back to "other" (which has build_score ->
the nonsensical "Build" dimension on a perfume).

Also covers Task 1.3: fragrance priority -> scent-dim personalization produces
applied weight shifts on scent dims and scoring_method == "personalized".
"""
import pytest

from app.services.scoring_service import ScoringService, CATEGORY_DIMENSIONS


FRAGRANCE_DIMS = set(CATEGORY_DIMENSIONS["fragrances"])
OTHER_DIMS = set(CATEGORY_DIMENSIONS["other"])


def _fragrance_products(category="Fragrances"):
    """Two minimal fragrance product dicts. compute_scores reads specs/price/
    reviews opportunistically; missing signals fall to MISSING_SCORE, which is
    fine — we only assert which DIMENSION KEYS appear, which is purely a function
    of the (canonicalized) category."""
    return [
        {
            "brand": "Tom Ford",
            "name": "Ombre Leather",
            "category": category,
            "specs": {
                "scent_family": "leather",
                "longevity": "8 hours",
                "sillage": "strong",
                "concentration": "eau de parfum",
                "volume": "100ml",
            },
            "price": {"amount": 85.0, "currency": "BHD", "source_method": "page_scrape"},
            "rating": 4.5,
            "review_count": 1200,
        },
        {
            "brand": "Creed",
            "name": "Aventus",
            "category": category,
            "specs": {
                "scent_family": "fruity",
                "longevity": "10 hours",
                "sillage": "strong",
                "concentration": "eau de parfum",
                "volume": "100ml",
            },
            "price": {"amount": 120.0, "currency": "BHD", "source_method": "page_scrape"},
            "rating": 4.7,
            "review_count": 3400,
        },
    ]


def _product_dim_keys(result):
    """Collect every dimension key present across both products' breakdowns."""
    keys = set()
    for pk in ("product_0", "product_1"):
        keys |= set(result["scores"][pk]["breakdown"].keys())
    return keys


def test_capital_f_fragrance_uses_scent_dims_not_build():
    svc = ScoringService()
    result = svc.compute_scores(_fragrance_products(category="Fragrances"))
    keys = _product_dim_keys(result)
    # Scent dims present
    assert "longevity_score" in keys
    assert "projection_score" in keys
    assert "character_score" in keys
    # The "other"-only build dim must NOT be present
    assert "build_score" not in keys
    # The full set must be exactly the fragrance dims
    assert keys == FRAGRANCE_DIMS


def test_lowercase_fragrances_unchanged():
    """Already-correct lowercase category still routes to scent dims."""
    svc = ScoringService()
    result = svc.compute_scores(_fragrance_products(category="fragrances"))
    keys = _product_dim_keys(result)
    assert keys == FRAGRANCE_DIMS
    assert "build_score" not in keys


def test_capital_electronics_unchanged():
    """Already-correct path: ELECTRONICS canonicalizes to electronics dims."""
    svc = ScoringService()
    products = [
        {"brand": "Apple", "name": "iPhone 15", "category": "ELECTRONICS",
         "specs": {"processor": "A16", "ram": "6GB"}, "price": {"amount": 400.0, "currency": "BHD"}},
        {"brand": "Samsung", "name": "Galaxy S24", "category": "ELECTRONICS",
         "specs": {"processor": "Snapdragon", "ram": "8GB"}, "price": {"amount": 350.0, "currency": "BHD"}},
    ]
    result = svc.compute_scores(products)
    keys = _product_dim_keys(result)
    assert keys == set(CATEGORY_DIMENSIONS["electronics"])
    assert "build_score" not in keys


def test_fragrance_priority_personalization_shifts_scent_dims():
    """Task 1.3 — a fragrance comparison with priorities=['quality'] must produce
    non-empty applied weight shifts on scent dims and scoring_method=personalized.
    quality maps to character_score +0.10 / longevity_score +0.10 / wear_value_score -0.10.
    """
    svc = ScoringService()
    products = _fragrance_products(category="Fragrances")

    base = svc.compute_scores(products)
    personalized = svc.compute_scores(products, preferences={"priorities": ["quality"]})

    assert personalized["scoring_method"] == "personalized"

    # weights_used must differ from the category-weighted baseline on scent dims
    base_w = base["scores"]["product_0"]["weights_used"]
    pers_w = personalized["scores"]["product_0"]["weights_used"]
    assert pers_w != base_w, "personalization produced no weight shift"

    # The shifted dims must be scent dims (not 'other' dims).
    shifted = {k for k in pers_w if pers_w.get(k) != base_w.get(k)}
    assert shifted, "no dimension weight changed"
    assert shifted <= FRAGRANCE_DIMS, f"shifted non-fragrance dims: {shifted - FRAGRANCE_DIMS}"
    # quality should lift longevity/character
    assert pers_w["longevity_score"] > base_w["longevity_score"]
    assert pers_w["character_score"] > base_w["character_score"]
