"""Lane 1 L1.9 — per-spec-row winner flag for design Screen 4.

Prod (2026-06-08) emits `specs.specs_comparison` as a dict of
`{product_0_advantages, product_1_advantages, similar}` — useful for
the verdict prose, but NOT a per-row table the FE can render with
emerald winner highlighting.

L1.9 augments the structure with a new `rows` list:
    rows: [
        {"field": "battery", "p0_value": "3349 mAh", "p1_value": "4000 mAh", "winner": 1},
        {"field": "ram",     "p0_value": "6 GB",     "p1_value": "8 GB",    "winner": 1},
        {"field": "display", "p0_value": "6.1 in",   "p1_value": "6.1 in",  "winner": "tie"},
        ...
    ]

Winner detection:
- Numeric specs (battery mAh, RAM GB, storage GB, screen size in,
  warranty years): LARGER wins.
- Weight: SMALLER wins (lighter is better).
- String specs: 'tie' when equal, None otherwise.
- 'N/A' / null on one side → the populated side wins.
"""
from __future__ import annotations

import pytest

from app.services.response_builder import build_comparison_response


def _phone(name, specs):
    return {
        "name": name,
        "brand": "X",
        "category": "electronics",
        "specs": specs,
        "price": {"amount": 100, "currency": "BHD"},
        "rating": 4.5,
        "review_count": 200,
        "pros_cons": {"pros": [], "cons": []},
    }


# ---------------------------------------------------------------------------
# rows list always emits
# ---------------------------------------------------------------------------


def test_specs_comparison_emits_rows_list():
    products = [
        _phone("Alpha", {"battery": "3000 mAh", "ram": "6 GB"}),
        _phone("Beta", {"battery": "4500 mAh", "ram": "8 GB"}),
    ]
    resp = build_comparison_response(
        products=products,
        comparison={"winner_index": 1},
        category_used="electronics",
    )
    sc = resp["specs"]["specs_comparison"]
    assert isinstance(sc, dict)
    assert "rows" in sc
    assert isinstance(sc["rows"], list)


def test_specs_row_shape_field_values_winner():
    products = [
        _phone("Alpha", {"battery": "3000 mAh", "ram": "6 GB"}),
        _phone("Beta", {"battery": "4500 mAh", "ram": "8 GB"}),
    ]
    resp = build_comparison_response(
        products=products,
        comparison={"winner_index": 1},
        category_used="electronics",
    )
    rows = resp["specs"]["specs_comparison"]["rows"]
    assert rows, "rows list empty"
    for row in rows:
        assert "field" in row
        assert "p0_value" in row
        assert "p1_value" in row
        assert "winner" in row
        assert row["winner"] in (0, 1, "tie", None)


# ---------------------------------------------------------------------------
# Numeric winner detection
# ---------------------------------------------------------------------------


def test_specs_row_battery_larger_wins():
    products = [
        _phone("Alpha", {"battery": "3000 mAh"}),
        _phone("Beta", {"battery": "4500 mAh"}),
    ]
    resp = build_comparison_response(
        products=products,
        comparison={"winner_index": 1},
        category_used="electronics",
    )
    rows = resp["specs"]["specs_comparison"]["rows"]
    battery_row = next((r for r in rows if r["field"] == "battery"), None)
    assert battery_row is not None
    assert battery_row["winner"] == 1


def test_specs_row_ram_larger_wins():
    products = [
        _phone("Alpha", {"ram": "8 GB"}),
        _phone("Beta", {"ram": "6 GB"}),
    ]
    resp = build_comparison_response(
        products=products,
        comparison={"winner_index": 0},
        category_used="electronics",
    )
    rows = resp["specs"]["specs_comparison"]["rows"]
    ram_row = next((r for r in rows if r["field"] == "ram"), None)
    assert ram_row is not None
    assert ram_row["winner"] == 0


def test_specs_row_weight_smaller_wins():
    """Weight is the inverted-larger-wins case: lighter phone wins."""
    products = [
        _phone("Alpha", {"weight": "171 g"}),
        _phone("Beta", {"weight": "210 g"}),
    ]
    resp = build_comparison_response(
        products=products,
        comparison={"winner_index": 0},
        category_used="electronics",
    )
    rows = resp["specs"]["specs_comparison"]["rows"]
    weight_row = next((r for r in rows if r["field"] == "weight"), None)
    assert weight_row is not None
    assert weight_row["winner"] == 0


def test_specs_row_storage_larger_wins():
    products = [
        _phone("Alpha", {"storage": "128 GB"}),
        _phone("Beta", {"storage": "256 GB"}),
    ]
    resp = build_comparison_response(
        products=products,
        comparison={"winner_index": 1},
        category_used="electronics",
    )
    rows = resp["specs"]["specs_comparison"]["rows"]
    storage_row = next((r for r in rows if r["field"] == "storage"), None)
    assert storage_row is not None
    assert storage_row["winner"] == 1


# ---------------------------------------------------------------------------
# String + tie + N/A handling
# ---------------------------------------------------------------------------


def test_specs_row_equal_strings_tie():
    products = [
        _phone("Alpha", {"os": "iOS 17"}),
        _phone("Beta", {"os": "iOS 17"}),
    ]
    resp = build_comparison_response(
        products=products,
        comparison={"winner_index": 0},
        category_used="electronics",
    )
    rows = resp["specs"]["specs_comparison"]["rows"]
    os_row = next((r for r in rows if r["field"] == "os"), None)
    assert os_row is not None
    assert os_row["winner"] == "tie"


def test_specs_row_one_side_na_other_side_wins():
    products = [
        _phone("Alpha", {"connectivity": "USB-C, NFC, Bluetooth 5.3"}),
        _phone("Beta", {"connectivity": "N/A"}),
    ]
    resp = build_comparison_response(
        products=products,
        comparison={"winner_index": 0},
        category_used="electronics",
    )
    rows = resp["specs"]["specs_comparison"]["rows"]
    conn_row = next((r for r in rows if r["field"] == "connectivity"), None)
    assert conn_row is not None
    assert conn_row["winner"] == 0


def test_specs_row_field_only_on_one_side_omitted():
    """If only one product has a spec field, the row is not emitted —
    no half-empty rows on Screen 4."""
    products = [
        _phone("Alpha", {"display": "6.1 in", "battery": "3000 mAh"}),
        _phone("Beta", {"battery": "4000 mAh"}),  # no display
    ]
    resp = build_comparison_response(
        products=products,
        comparison={"winner_index": 1},
        category_used="electronics",
    )
    rows = resp["specs"]["specs_comparison"]["rows"]
    fields = [r["field"] for r in rows]
    assert "display" not in fields
    assert "battery" in fields  # both sides have it


# ---------------------------------------------------------------------------
# Internal _field_confidence is NOT a comparable spec
# ---------------------------------------------------------------------------


def test_specs_row_skips_internal_fields():
    """`_field_confidence` is metadata, not a comparable spec."""
    products = [
        _phone(
            "Alpha",
            {
                "ram": "6 GB",
                "_field_confidence": {"ram": "snippet"},
            },
        ),
        _phone(
            "Beta",
            {
                "ram": "8 GB",
                "_field_confidence": {"ram": "snippet"},
            },
        ),
    ]
    resp = build_comparison_response(
        products=products,
        comparison={"winner_index": 1},
        category_used="electronics",
    )
    rows = resp["specs"]["specs_comparison"]["rows"]
    fields = [r["field"] for r in rows]
    assert "_field_confidence" not in fields


# ---------------------------------------------------------------------------
# Backward compat — existing keys still emit
# ---------------------------------------------------------------------------


def test_specs_comparison_preserves_existing_keys():
    """The new `rows` list is ADDITIVE — existing `product_0_advantages`,
    `product_1_advantages`, `similar` keys must still emit."""
    products = [
        _phone("Alpha", {"ram": "6 GB"}),
        _phone("Beta", {"ram": "8 GB"}),
    ]
    resp = build_comparison_response(
        products=products,
        comparison={
            "winner_index": 1,
            "specs_comparison": {
                "product_0_advantages": ["Cheaper"],
                "product_1_advantages": ["More RAM"],
                "similar": ["Same OS"],
            },
        },
        category_used="electronics",
    )
    sc = resp["specs"]["specs_comparison"]
    assert sc.get("product_0_advantages") == ["Cheaper"]
    assert sc.get("product_1_advantages") == ["More RAM"]
    assert sc.get("similar") == ["Same OS"]
    assert "rows" in sc  # additive
