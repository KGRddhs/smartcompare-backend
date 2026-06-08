"""Lane 1 L1.7+L1.8 — overview.products[i] variant + pros_cons surfaces.

Prod (2026-06-08) emits the overview product blocks with `variant=None`
and a flat `pros` / `cons` list but no `pros_cons` accordion block.
Design Screen 1 needs:
- `variant`: short tag like '128GB · Black' so the FE card renders the
  full product line below the title (capped at 3 segments to fit narrow
  phones).
- `pros_cons`: explicit accordion block with `pros`, `cons`, and an
  `is_winner` flag so the FE can star the winner side.

The underlying data is already extracted upstream; the overview
builder just drops it. L1.7 + L1.8 thread it through.
"""
from __future__ import annotations

import pytest

from app.services.response_builder import build_comparison_response


def _make_products(category: str, with_specs: bool = True):
    p0_specs = (
        {"storage": "128GB", "color": "Black", "ram": "8GB"}
        if with_specs and category == "electronics"
        else (
            {"volume_ml": 50, "concentration": "EDP"}
            if with_specs and category == "fragrances"
            else (
                {"active_ingredient": "Vitamin D3 1000 IU", "form": "softgel"}
                if with_specs and category == "supplements"
                else {}
            )
        )
    )
    p1_specs = (
        {"storage": "256GB", "color": "Silver", "ram": "12GB"}
        if with_specs and category == "electronics"
        else (
            {"volume_ml": 100, "concentration": "Parfum"}
            if with_specs and category == "fragrances"
            else (
                {"active_ingredient": "Vitamin D3 5000 IU", "form": "capsule"}
                if with_specs and category == "supplements"
                else {}
            )
        )
    )
    return [
        {
            "name": "Alpha",
            "brand": "X",
            "category": category,
            "specs": p0_specs,
            "price": {"amount": 100, "currency": "BHD"},
            "rating": 4.5,
            "review_count": 200,
            "pros_cons": {
                "pros": ["Fast", "Reliable", "Great battery"],
                "cons": ["Pricey"],
            },
        },
        {
            "name": "Beta",
            "brand": "Y",
            "category": category,
            "specs": p1_specs,
            "price": {"amount": 90, "currency": "BHD"},
            "rating": 4.4,
            "review_count": 180,
            "pros_cons": {
                "pros": ["Affordable", "Lightweight"],
                "cons": ["Shorter battery", "Plastic build"],
            },
        },
    ]


# ---------------------------------------------------------------------------
# L1.7 — variant string
# ---------------------------------------------------------------------------


def test_overview_product_variant_emitted_for_electronics():
    products = _make_products("electronics")
    resp = build_comparison_response(
        products=products,
        comparison={"winner_index": 0},
        category_used="electronics",
    )
    ov = resp["overview"]["products"]
    assert "variant" in ov[0]
    assert ov[0]["variant"], f"empty variant for electronics: {ov[0]['variant']!r}"
    # Storage + color should be in the variant tag
    assert "128GB" in ov[0]["variant"]


def test_overview_product_variant_emitted_for_fragrances():
    products = _make_products("fragrances")
    resp = build_comparison_response(
        products=products,
        comparison={"winner_index": 1},
        category_used="fragrances",
    )
    ov = resp["overview"]["products"]
    assert "variant" in ov[0]
    # Volume should be in the variant tag (with ml unit)
    assert "ml" in ov[0]["variant"].lower() or "50" in ov[0]["variant"]


def test_overview_product_variant_caps_at_three_segments():
    """Narrow phones — variant must cap at 3 segments to fit the card."""
    products = _make_products("electronics")
    # Add bonus segments that should not push past the cap
    products[0]["specs"]["extra1"] = "EXTRA1"
    products[0]["specs"]["extra2"] = "EXTRA2"
    resp = build_comparison_response(
        products=products,
        comparison={"winner_index": 0},
        category_used="electronics",
    )
    variant = resp["overview"]["products"][0]["variant"]
    # Separator is "·"
    segments = variant.split("·") if variant else []
    assert len(segments) <= 3, f"variant exceeds 3 segments: {variant!r}"


def test_overview_product_variant_empty_string_when_no_specs():
    """When the product has no specs hooks, variant emits an empty
    string (NOT None, NOT a crash)."""
    products = _make_products("electronics", with_specs=False)
    resp = build_comparison_response(
        products=products,
        comparison={"winner_index": 0},
        category_used="electronics",
    )
    variant = resp["overview"]["products"][0]["variant"]
    assert variant == ""


def test_overview_product_variant_safe_on_missing_category():
    """Defensive: unknown / `other` category falls back to a generic
    grab-bag of common spec hooks."""
    products = _make_products("other", with_specs=False)
    resp = build_comparison_response(
        products=products,
        comparison={"winner_index": 0},
        category_used="other",
    )
    variant = resp["overview"]["products"][0]["variant"]
    assert isinstance(variant, str)


# ---------------------------------------------------------------------------
# L1.8 — pros_cons block + is_winner flag
# ---------------------------------------------------------------------------


def test_overview_product_has_pros_cons_block():
    products = _make_products("electronics")
    resp = build_comparison_response(
        products=products,
        comparison={"winner_index": 0},
        category_used="electronics",
    )
    ov = resp["overview"]["products"]
    assert isinstance(ov[0].get("pros_cons"), dict)
    assert isinstance(ov[1].get("pros_cons"), dict)


def test_overview_pros_cons_populated_from_product_data():
    products = _make_products("electronics")
    resp = build_comparison_response(
        products=products,
        comparison={"winner_index": 0},
        category_used="electronics",
    )
    ov = resp["overview"]["products"]
    pc0 = ov[0]["pros_cons"]
    assert len(pc0["pros"]) == 3
    assert len(pc0["cons"]) == 1
    assert "Fast" in pc0["pros"]


def test_overview_pros_cons_caps_pros_at_four():
    """Design § Screen 1 — pros/cons accordion caps at 4 per side to
    keep the card height bounded."""
    products = _make_products("electronics")
    products[0]["pros_cons"]["pros"] = [f"pro_{i}" for i in range(10)]
    products[0]["pros_cons"]["cons"] = [f"con_{i}" for i in range(10)]
    resp = build_comparison_response(
        products=products,
        comparison={"winner_index": 0},
        category_used="electronics",
    )
    pc = resp["overview"]["products"][0]["pros_cons"]
    assert len(pc["pros"]) <= 4
    assert len(pc["cons"]) <= 4


def test_overview_pros_cons_is_winner_flag_marks_winner_only():
    products = _make_products("electronics")
    resp = build_comparison_response(
        products=products,
        comparison={"winner_index": 1},  # winner is Beta
        category_used="electronics",
    )
    ov = resp["overview"]["products"]
    assert ov[1]["pros_cons"]["is_winner"] is True
    assert ov[0]["pros_cons"]["is_winner"] is False


def test_overview_pros_cons_empty_when_product_has_none():
    products = _make_products("electronics")
    products[0]["pros_cons"] = None  # explicit missing
    resp = build_comparison_response(
        products=products,
        comparison={"winner_index": 0},
        category_used="electronics",
    )
    pc = resp["overview"]["products"][0]["pros_cons"]
    assert pc is not None  # block must still emit
    assert pc["pros"] == []
    assert pc["cons"] == []


# ---------------------------------------------------------------------------
# Backward compat — existing flat pros/cons must still emit
# ---------------------------------------------------------------------------


def test_overview_existing_flat_pros_cons_preserved():
    """Bundle C surfaced `pros` / `cons` at the top level of the
    overview product block; the new `pros_cons` accordion is ADDITIVE.
    The old flat keys must still resolve to the same data."""
    products = _make_products("electronics")
    resp = build_comparison_response(
        products=products,
        comparison={"winner_index": 0},
        category_used="electronics",
    )
    ov = resp["overview"]["products"][0]
    assert ov["pros"] == ov["pros_cons"]["pros"]
    assert ov["cons"] == ov["pros_cons"]["cons"]
