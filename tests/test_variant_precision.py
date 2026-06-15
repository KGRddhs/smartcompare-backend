"""WS5 variant/concentration precision (Genuine-BH latency+warmer bundle).

The trace pair mis-compared a 100ml-class Ounass listing vs a 30ml Sephora
listing (a size mismatch, not like-for-like). These tests cover the parse helpers
and the candidate-selection PREFERENCE — pure functions + mocked-list selection,
NO live network / Serper / render.

Invariants:
  - extract_concentration / extract_sizes_ml parse the two fragrance axes.
  - variant_precision_rank rewards a query-stated size/concentration match.
  - extract_price_from_shopping prefers the matching variant BEFORE cheapest
    price, and annotates price.size / price.concentration.
  - non-fragrance (electronics) is completely unaffected (all-zero rank).
  - the shipped accuracy guards are NOT regressed (implausible-floor still fires).
"""

import pytest

from app.services.price_service import (
    extract_concentration,
    extract_sizes_ml,
    variant_precision_rank,
    extract_price_from_shopping,
    is_implausible_high_value_price,
)


# --------------------------------------------------------------------------- #
# parse helpers                                                               #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("text,expected", [
    ("Tom Ford Tobacco Vanille Eau de Parfum 100ml", "EDP"),
    ("Tom Ford Ombre Leather EDP", "EDP"),
    ("Dior Sauvage Eau de Toilette", "EDT"),
    ("Versace Eros EDT 100ml", "EDT"),
    ("Chanel No 5 Eau de Cologne", "EDC"),
    ("Tom Ford Tobacco Vanille Parfum", "Parfum"),
    ("Mugler Alien Parfum Intense 60ml", "Parfum Intense"),
    ("Frederic Malle Portrait of a Lady Extrait", "Extrait"),
    ("iPhone 15 Pro Max 256GB", None),
    ("", None),
])
def test_extract_concentration(text, expected):
    assert extract_concentration(text) == expected


def test_edp_beats_bare_parfum_specificity():
    # "Eau de Parfum" must resolve to EDP, not the generic bare-"Parfum"
    assert extract_concentration("Creed Aventus Eau de Parfum 100ml") == "EDP"


@pytest.mark.parametrize("text,expected", [
    ("Tom Ford 100ml", {"100"}),
    ("Ombre Leather 50 ml EDP", {"50"}),
    ("Sampler 30ml / 50ml / 100ml", {"30", "50", "100"}),
    ("Tom Ford Tobacco Vanille", set()),
    ("MacBook Air 13", set()),     # a bare number is NOT a size (ml required)
    ("", set()),
])
def test_extract_sizes_ml(text, expected):
    assert extract_sizes_ml(text) == expected


# --------------------------------------------------------------------------- #
# variant_precision_rank                                                       #
# --------------------------------------------------------------------------- #
def test_rank_rewards_exact_size_and_concentration():
    q = "Tom Ford Tobacco Vanille EDP 100ml"
    assert variant_precision_rank(q, "Tom Ford Tobacco Vanille Eau de Parfum 100ml") == (1, 1)
    assert variant_precision_rank(q, "Tom Ford Tobacco Vanille EDP 30ml") == (1, -1)
    assert variant_precision_rank(q, "Tom Ford Tobacco Vanille EDT 100ml") == (-1, 1)
    assert variant_precision_rank(q, "Tom Ford Tobacco Vanille") == (0, 0)


def test_rank_neutral_when_query_unspecified():
    # query says nothing about size/concentration -> neither axis is enforced
    q = "Tom Ford Tobacco Vanille"
    assert variant_precision_rank(q, "Tom Ford Tobacco Vanille EDP 100ml") == (0, 0)


def test_rank_non_fragrance_is_neutral():
    assert variant_precision_rank("iPhone 15", "iPhone 15 128GB Blue") == (0, 0)
    assert variant_precision_rank("", "anything") == (0, 0)
    assert variant_precision_rank("q", "") == (0, 0)


# --------------------------------------------------------------------------- #
# extract_price_from_shopping — preference + annotation                        #
# --------------------------------------------------------------------------- #
def _item(title, price, source="Boots Bahrain", link="https://bn.boots.com/p/x"):
    return {"title": title, "price": price, "source": source, "link": link}


def test_shopping_prefers_query_size_over_cheaper_wrong_size():
    """A query for 100ml must NOT grab the cheaper 30ml — variant_rank tie-breaks
    before price."""
    q = "Tom Ford Tobacco Vanille EDP 100ml"
    items = [
        _item("Tom Ford Tobacco Vanille EDP 30ml", "BHD 72.000"),    # cheaper, WRONG size
        _item("Tom Ford Tobacco Vanille EDP 100ml", "BHD 118.000"),  # correct size
    ]
    out = extract_price_from_shopping(q, items, "BHD")
    assert out is not None
    assert out["amount"] == 118.0, "should pick the 100ml match, not the cheaper 30ml"
    assert out["size"] == "100ml"
    assert out["concentration"] == "EDP"


def test_shopping_annotates_size_and_concentration():
    out = extract_price_from_shopping(
        "Dior Sauvage EDT 100ml",
        [_item("Dior Sauvage Eau de Toilette 100ml", "BHD 35.000")],
        "BHD",
    )
    assert out is not None
    assert out["concentration"] == "EDT"
    assert out["size"] == "100ml"
    # internal sort key must NOT leak to the caller
    assert "variant_rank" not in out


def test_shopping_unspecified_query_keeps_cheapest_basis():
    """When the query specifies no size, variant_rank is all-zero so the existing
    cheapest-among-equal-authority ordering is unchanged."""
    q = "Tom Ford Tobacco Vanille"
    items = [
        _item("Tom Ford Tobacco Vanille EDP 100ml", "BHD 118.000"),
        _item("Tom Ford Tobacco Vanille EDP 50ml", "BHD 80.000"),
    ]
    out = extract_price_from_shopping(q, items, "BHD")
    assert out is not None
    # both rank (0,0); luxury sort falls through to cheapest -> 80
    assert out["amount"] == 80.0


# --------------------------------------------------------------------------- #
# accuracy-guard non-regression                                                #
# --------------------------------------------------------------------------- #
def test_implausible_high_value_floor_still_fires():
    """WS5 must not regress the shipped is_implausible_high_value_price guard
    (an 11.9 BHD 'phone' is still rejected as an accessory leak)."""
    assert is_implausible_high_value_price("iPhone 15 Pro Max", 11.9) is True
    assert is_implausible_high_value_price("iPhone 15 Pro Max", 350.0) is False
