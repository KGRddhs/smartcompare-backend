"""Lane 1 fixture helpers.

Reconstruct the (product_data, scoring_result) inputs that flow into
`_build_scoring_v2` / `build_dimensions_v2` from a captured prod response.
The captured responses live next to this file as `*_response.json`.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Tuple

_FIXTURE_DIR = os.path.dirname(__file__)


def _load_response(filename: str) -> Dict[str, Any]:
    path = os.path.join(_FIXTURE_DIR, filename)
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def build_inputs(filename: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any], str, int]:
    """Return (product_data, scoring_result, category, winner_index) inputs
    to `_build_scoring_v2` reconstructed from a captured prod response.

    Captured responses contain enough information to drive every Lane 1 unit
    function — overview.products + specs.products + scoring + winner_index.
    """
    resp = _load_response(filename)
    category = resp.get("category") or resp.get("category_used") or "other"
    winner_index = resp.get("winner_index") or resp.get("overview", {}).get(
        "winner", {}
    ).get("product_index") or 0

    ov_products = resp.get("overview", {}).get("products", []) or []
    spec_products = resp.get("specs", {}).get("products", []) or []
    scoring_result = resp.get("scoring", {}) or {}

    product_data: List[Dict[str, Any]] = []
    for i, op in enumerate(ov_products):
        specs_block = (
            spec_products[i].get("specs") if i < len(spec_products) else {}
        ) or {}
        product_data.append(
            {
                "brand": op.get("brand"),
                "name": op.get("name"),
                "price": op.get("price"),
                "rating": op.get("rating"),
                "review_count": op.get("review_count"),
                "specs": specs_block,
                "pros": op.get("pros", []) or [],
                "cons": op.get("cons", []) or [],
                "pros_cons": {
                    "pros": op.get("pros", []) or [],
                    "cons": op.get("cons", []) or [],
                },
                "image_url": op.get("image_url"),
                "category": category,
                # surface a few raw keys hand-coded dim builders look for
                "warranty_years": specs_block.get("warranty_years"),
            }
        )

    return product_data, scoring_result, category, winner_index
