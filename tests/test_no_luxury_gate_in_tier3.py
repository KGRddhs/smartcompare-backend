"""B0-B Item 2 regression — verify `is_luxury_brand()` no longer gates the
Tier-3 sanity-check threshold band at the two old call sites
(`structured_comparison_service.py:2393-2394` + `:2654`).

The replacement is `_sanity_check_thresholds(sources)`, which routes ALL
categories through `compute_price_confidence` and picks the tight band
(1.8 / 0.6) when confidence is low, loose band (2.0 / 0.5) otherwise.

The 3 tests below pin:
  1. Static grep over the relevant range — `is_luxury_brand(full_name)`
     must NOT appear inside `_get_price`'s Tier-1 / Tier-2 sanity-check
     bodies. This catches a future revert.
  2. `_sanity_check_thresholds` is exported from the module + returns the
     tight band for a single-source low-retailer-score candidate (the
     pattern that previously required `is_luxury_brand=True`).
  3. The same helper returns the loose band for a multi-source agreeing
     high-retailer-score input (the pattern that previously implied
     non-luxury default thresholds).
"""
from __future__ import annotations

import re
from pathlib import Path


def _read_get_price_body() -> str:
    """Return the source of `_get_price` so a grep can scan only that body."""
    src_path = Path(__file__).parent.parent / "app" / "services" / "structured_comparison_service.py"
    src = src_path.read_text(encoding="utf-8")
    # _get_price starts at `async def _get_price` and continues until the
    # next sibling `async def`/`def` at the same indent. Grab a chunk that
    # spans both the Tier-1 sanity check (was line 2393-2394) and the
    # Tier-2 sanity check (was line 2654) — both of which used to call
    # `is_luxury_brand(full_name)`.
    match = re.search(
        r"async def _get_price\([^)]*\).*?(?=\n    (?:async )?def )",
        src,
        re.DOTALL,
    )
    assert match, "Could not locate _get_price body in structured_comparison_service.py"
    return match.group(0)


def test_get_price_body_has_no_is_luxury_brand_runtime_call():
    """B0-B Item 2 contract — `_get_price` no longer runtime-gates the
    Tier-3 sanity-check band on `is_luxury_brand(full_name)`. Comments
    that reference the legacy gate by name are fine; the call itself
    (with full_name as arg) is forbidden.
    """
    body = _read_get_price_body()
    # Strip out comment-only lines so the assertion only inspects executable code.
    code_only = "\n".join(
        line for line in body.splitlines()
        if not line.strip().startswith("#")
    )
    assert "is_luxury_brand(full_name)" not in code_only, (
        "is_luxury_brand(full_name) found in _get_price runtime path — "
        "B0-B Item 2 regression. Use _sanity_check_thresholds(sources) "
        "instead of the legacy luxury gate."
    )


def test_sanity_check_thresholds_returns_tight_band_for_low_confidence():
    """A single-source candidate from a low-score retailer is the canonical
    low-confidence pattern (this is what `is_luxury_brand=True` used to
    catch). It must yield the tight luxury-equivalent band 1.8 / 0.6.
    """
    from app.services.structured_comparison_service import _sanity_check_thresholds

    sources = [{
        "src": "serper_shopping",
        "amount": 142.12,
        "retailer_score": 0.4,  # low — typical marketplace seller
    }]
    high, low = _sanity_check_thresholds(sources)
    assert (high, low) == (1.8, 0.6), (
        f"Expected tight luxury-equivalent band (1.8, 0.6) for "
        f"low-confidence single source, got ({high}, {low})"
    )


def test_sanity_check_thresholds_returns_loose_band_for_medium_confidence():
    """Two sources agreeing within 20% with reasonable retailer score is
    medium-or-better confidence. The legacy non-luxury default is the
    loose band 2.0 / 0.5.
    """
    from app.services.structured_comparison_service import _sanity_check_thresholds

    sources = [
        {"src": "serper_shopping", "amount": 142.0, "retailer_score": 0.9},
        {"src": "page_scrape", "amount": 145.0, "retailer_score": 0.9},
    ]
    high, low = _sanity_check_thresholds(sources)
    assert (high, low) == (2.0, 0.5), (
        f"Expected loose default band (2.0, 0.5) for multi-source "
        f"medium-confidence input, got ({high}, {low})"
    )


def test_sanity_check_thresholds_fires_tight_band_for_non_luxury_low_confidence():
    """The B0-B Item 2 behavior change in plain terms: a non-luxury query
    (e.g. an electronics product) that has weak Tier-1 data ALSO now gets
    the tight band — luxury was just a heuristic for low confidence.
    This test is the load-bearing one: it pins that the gate change is
    *category-agnostic*, not just a rename.
    """
    from app.services.structured_comparison_service import _sanity_check_thresholds

    # Single source, low retailer score — would have been is_luxury_brand=False
    # → loose band under the old code. Now the helper picks the tight band.
    sources = [{
        "src": "serper_shopping",
        "amount": 250.0,
        "retailer_score": 0.3,
    }]
    high, low = _sanity_check_thresholds(sources)
    assert (high, low) == (1.8, 0.6), (
        "Non-luxury low-confidence Tier-1 candidate must get the tight "
        "band — this is the whole point of removing the luxury gate. "
        f"Got ({high}, {low})."
    )
