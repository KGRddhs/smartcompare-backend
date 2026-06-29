"""Local code-review (PR #9) follow-up.

FIXED here (each reproduces through the SAME runtime selector the orchestrator runs,
each fix paired with a GUARD that it opens no new leak):
  #2 OVER-REJECT  — an oz-labelled NON-fragrance (CeraVe 8 oz == 236 ml) was
                    snapped to a luxury fragrance bottle size (250) and falsely
                    mismatched its ml-labelled listing of the SAME product.
  #4 OVER-REJECT  — makeup kept pure connective stopwords ("in"/"to"/...) as
                    identity, over-rejecting the common "<product> in <shade>" title.

INVESTIGATED, INTENTIONALLY NOT CHANGED:
  #1 (fragrance gender) — a base/men's query CAN still match a women's flanker
                    ("Versace Eros" -> "Eros Pour Femme"). A symmetric gender rule
                    fixes that narrow leak but mass-over-rejects every WOMEN's-BASE
                    fragrance ("Black Opium" -> "Black Opium For Women" is the SAME
                    product) — gender tokens cannot tell a flanker from a women's-base
                    descriptor. The asymmetry is the correct trade; the tests below
                    PIN the accepted behaviour so it is a conscious decision, not drift.
"""
import os
import pytest

from app.services.price_service import (
    _selection_match,
    _size_ml_mismatch,
    _weight_or_volume_mismatch,
    should_cache_price,
    extract_jsonld_price,
    is_price_showable,
)


def _price(title, amount=40.0, **extra):
    p = {
        "amount": amount, "currency": "BHD", "source_method": "local_bhd",
        "in_stock": True, "url": "https://www.example-bh.com/p/item", "title": title,
    }
    p.update(extra)
    return p


@pytest.fixture(autouse=True)
def _gate_on(monkeypatch):
    """The correctness gate is ON by default in prod; pin it for these tests so a
    local `.env` / OS env that disabled it cannot silently no-op the assertions."""
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "true")


# ---------------------------------------------------------------------------
# #1 — fragrance gender (INVESTIGATED; asymmetry intentionally kept). These tests
# PIN the accepted trade so the behaviour can only change by a conscious edit.
# ---------------------------------------------------------------------------
class TestFragranceGenderAsymmetryAccepted:
    def test_womens_base_descriptor_must_match(self):
        # WHY #1 is not symmetrized: Black Opium IS a women's fragrance, so a genuine
        # candidate that adds the "For Women" descriptor is the SAME product and MUST
        # match. A symmetric "reject when one side states women's" rule would pend this
        # (and every women's-base fragrance) — a far larger over-rejection than the leak.
        assert _selection_match(
            "YSL Black Opium EDP 90ml",
            "YSL Black Opium Eau de Parfum For Women 90ml",
            "fragrances", candidate_brand="YSL",
        ) is True

    def test_known_accepted_men_base_to_femme_flanker_leak(self):
        # DOCUMENTED ACCEPTED LEAK: a men's/base query still matches its women's
        # flanker because gender tokens cannot distinguish it from the women's-base
        # case above. If this ever flips to False, the symmetric rule was (re)introduced
        # and the women's-base test above will be failing too — revisit together.
        assert _selection_match(
            "Versace Eros", "Versace Eros Pour Femme", "fragrances",
            candidate_brand="Versace",
        ) is True

    # --- GUARDS: behaviours that DO hold -----------------------------------
    def test_guard_pour_homme_bestseller_still_matches_base(self):
        # The dominant genuine case: a men's "Pour Homme" query matching a genuine
        # gender-OMITTING base PDP must STILL match (men's/base tolerance preserved).
        assert _selection_match(
            "Bleu de Chanel Pour Homme", "Bleu de Chanel", "fragrances",
            candidate_brand="Chanel",
        ) is True

    def test_guard_femme_query_still_requires_femme_candidate(self):
        # Original _feminine_query_unconfirmed behaviour preserved: a femme query
        # matching a gender-omitting base candidate stays rejected.
        assert _selection_match(
            "Versace Eros Pour Femme", "Versace Eros", "fragrances",
            candidate_brand="Versace",
        ) is False

    def test_guard_same_product_no_gender_matches(self):
        assert _selection_match(
            "Versace Eros", "Versace Eros Eau de Toilette", "fragrances",
            candidate_brand="Versace",
        ) is True

    def test_guard_two_femme_match(self):
        assert _selection_match(
            "Versace Eros Pour Femme", "Versace Eros Pour Femme EDP", "fragrances",
            candidate_brand="Versace",
        ) is True


# ---------------------------------------------------------------------------
# #2 — oz→fragrance-bottle snap applied cross-category (over-rejection)
# ---------------------------------------------------------------------------
class TestOzMlCrossCategorySnap:
    def test_skincare_oz_matches_equivalent_ml(self):
        # 8 fl oz == 236.6 ml; a genuine "236 ml" listing of the SAME product must
        # match (the snap pushed 8oz -> 250 and falsely mismatched).
        assert _selection_match(
            "CeraVe Moisturizing Lotion 8 oz",
            "CeraVe Moisturizing Lotion 236 ml",
            "skincare", candidate_brand="CeraVe",
        ) is True

    def test_size_axis_oz_ml_equivalent_non_fragrance(self):
        # direct axis: 8oz vs 236ml is the SAME size for a non-fragrance.
        assert _size_ml_mismatch(
            "CeraVe Lotion 8 oz", "CeraVe Lotion 236 ml", "skincare",
        ) is False

    # --- GUARDS -------------------------------------------------------------
    def test_guard_real_size_difference_still_rejects(self):
        assert _selection_match(
            "CeraVe Moisturizing Lotion 88 ml",
            "CeraVe Moisturizing Lotion 236 ml",
            "skincare", candidate_brand="CeraVe",
        ) is False
        assert _size_ml_mismatch(
            "CeraVe Lotion 88 ml", "CeraVe Lotion 236 ml", "skincare",
        ) is True

    def test_guard_fragrance_snap_unchanged(self):
        # Fragrance path is unchanged: 3.4 oz snaps to 100 ml (match), 100 vs 50 rejects.
        assert _size_ml_mismatch("Sauvage 3.4 oz", "Sauvage 100 ml", "fragrances") is False
        assert _size_ml_mismatch("Sauvage 100 ml", "Sauvage 50 ml", "fragrances") is True


# ---------------------------------------------------------------------------
# #4 — makeup kept pure connective stopwords as identity (over-rejection)
# ---------------------------------------------------------------------------
class TestMakeupStopwordOverRejection:
    def test_makeup_in_shade_title_matches(self):
        # "<Brand> <Product> in <Shade>" is the canonical makeup title; the query
        # omits the connective "in". Must match the SAME shade.
        assert _selection_match(
            "NARS Lipstick Dolce Vita",
            "NARS Lipstick in Dolce Vita",
            "makeup", candidate_brand="NARS",
        ) is True

    # --- GUARD: a genuinely different shade must still reject ---------------
    def test_guard_different_shade_still_rejects(self):
        assert _selection_match(
            "NARS Lipstick Dolce Vita",
            "NARS Lipstick in Orgasm",
            "makeup", candidate_brand="NARS",
        ) is False


# ---------------------------------------------------------------------------
# #2b — lb->g conversion rounding over-rejection (weight axis; surfaced by the
# adversarial workflow as a preexisting bug in the same family as #2).
# ---------------------------------------------------------------------------
class TestLbToGramConversionRounding:
    def test_protein_lb_matches_equivalent_grams(self):
        # 5 lb == 2267.96 g; the genuine "2270 g" label of the SAME tub must match
        # (the exact-equality weight axis over-rejected it).
        assert _selection_match(
            "Optimum Nutrition Gold Standard Whey 5lb",
            "Optimum Nutrition Gold Standard Whey 2270g",
            "supplements", candidate_brand="Optimum Nutrition",
        ) is True

    def test_weight_axis_lb_grams_equivalent(self):
        assert _weight_or_volume_mismatch("Whey 5lb", "Whey 2270g") is False
        assert _weight_or_volume_mismatch("Whey 5lb", "Whey 2.27kg") is False

    # --- GUARDS -------------------------------------------------------------
    def test_guard_different_lb_sizes_still_reject(self):
        assert _selection_match(
            "Optimum Nutrition Gold Standard Whey 2lb",
            "Optimum Nutrition Gold Standard Whey 5lb",
            "supplements", candidate_brand="Optimum Nutrition",
        ) is False
        assert _weight_or_volume_mismatch("Whey 5lb", "Whey 2kg") is True

    def test_guard_native_grams_stay_exact(self):
        # No lb token anywhere → grams compared EXACTLY (no spurious 1% merge).
        assert _weight_or_volume_mismatch("Cream 500g", "Cream 505g") is True
        assert _weight_or_volume_mismatch("Cream 500g", "Cream 500g") is False


# ---------------------------------------------------------------------------
# #5 — converted-price cache PROVENANCE (external review P2). A URL-less /
# search-url converted price must NOT enter the VERIFIED positive-price cache; a
# converted price WITH a real cited PDP url + matching identity still caches.
# ---------------------------------------------------------------------------
class TestConvertedCacheProvenance:
    def test_converted_with_real_pdp_url_is_cacheable(self):
        price = {
            "amount": 42.5, "currency": "BHD", "source_method": "converted_usd",
            "title": "Sony WH-1000XM5 Wireless Headphones", "brand": "Sony",
            "url": "https://www.noon.com/uae-en/sony-wh-1000xm5/p123",
        }
        assert should_cache_price("Sony WH-1000XM5", price, "electronics") is True

    def test_converted_with_search_url_not_in_verified_cache(self):
        # Provenance: a converted price whose only url is a synthesized search link has no
        # cited PDP and must NOT share the verified positive cache (review P2).
        price = {
            "amount": 42.5, "currency": "BHD", "source_method": "converted_usd",
            "title": "Sony WH-1000XM5 Wireless Headphones", "brand": "Sony",
            "url": "https://www.noon.com/search?q=sony+wh-1000xm5",
        }
        assert should_cache_price("Sony WH-1000XM5", price, "electronics") is False

    def test_genuine_with_search_url_not_cacheable(self):
        price = {
            "amount": 42.5, "currency": "BHD", "source_method": "page_scrape_jsonld",
            "title": "Sony WH-1000XM5 Wireless Headphones", "brand": "Sony",
            "url": "https://www.noon.com/search?q=sony+wh-1000xm5",
        }
        assert should_cache_price("Sony WH-1000XM5", price, "electronics") is False

    def test_converted_wrong_identity_not_cacheable(self):
        price = {
            "amount": 42.5, "currency": "BHD", "source_method": "converted_usd",
            "title": "Samsung Galaxy S24 FE 256GB", "brand": "Samsung",
            "url": "https://www.noon.com/p/galaxy-s24-fe",
        }
        assert should_cache_price("Samsung Galaxy S24 256GB", price, "electronics") is False


# ---------------------------------------------------------------------------
# #3 — a SECONDARY measurement (serving/nutrition weight) must NOT mask a
# different net/package size (external review P1).
# ---------------------------------------------------------------------------
class TestServingWeightDoesNotMaskPackage:
    def test_shared_serving_weight_does_not_match_different_package(self):
        # ISO100 5lb vs 2lb, both "25g protein per serving" — different package sizes that
        # must REJECT even though the 25g serving overlaps.
        assert _weight_or_volume_mismatch(
            "Dymatize ISO100 5lb 25g Protein", "Dymatize ISO100 2lb 25g Protein",
        ) is True
        assert _selection_match(
            "Dymatize ISO100 5lb", "Dymatize ISO100 2lb 25g Protein Per Serving",
            "supplements", candidate_brand="Dymatize",
        ) is False

    def test_guard_serving_figure_does_not_split_same_package(self):
        # Same headline 908g; a one-sided "30g per serving" must NOT manufacture a mismatch.
        assert _weight_or_volume_mismatch("Whey 908g", "Whey 908g 30g Per Serving") is False


# ---------------------------------------------------------------------------
# #2 — the usable_exact_genuine KPI must FAIL-CLOSED on a truth-pinned axis the
# resolved title omits (external review P1).
# ---------------------------------------------------------------------------
def _genuine_body(title):
    return {"products": [{"price": {
        "amount": 99.0, "currency": "BHD", "source_method": "local_bhd",
        "in_stock": True, "url": "https://www.example-bh.com/p/item", "title": title,
    }}]}


class TestKpiAxisFailClosed:
    def test_missing_storage_axis_not_usable(self):
        from scripts.eval_runner import usable_exact_genuine_for_product
        truth = {"query": "iPhone 15 256GB", "category": "electronics",
                 "expected": {"brand": "Apple", "model": "iPhone 15", "storage_gb": 256}}
        # title omits the 256GB the truth pins -> UNVERIFIED -> not usable.
        assert usable_exact_genuine_for_product(
            _genuine_body("Apple iPhone 15"), 0, truth) is False
        # title states the exact 256GB -> usable.
        assert usable_exact_genuine_for_product(
            _genuine_body("Apple iPhone 15 256GB"), 0, truth) is True

    def test_missing_concentration_and_size_not_usable(self):
        from scripts.eval_runner import usable_exact_genuine_for_product
        truth = {"query": "YSL Black Opium Eau de Parfum 90ml", "category": "fragrances",
                 "expected": {"brand": "Yves Saint Laurent", "model": "Black Opium",
                              "concentration": "EDP", "size_ml": 90}}
        assert usable_exact_genuine_for_product(
            _genuine_body("YSL Black Opium"), 0, truth) is False
        assert usable_exact_genuine_for_product(
            _genuine_body("YSL Black Opium Eau de Parfum 90ml"), 0, truth) is True


# ---------------------------------------------------------------------------
# #4 — fail-close the fixable wrong-SKU tradeoffs (gender stays product-approved).
# ---------------------------------------------------------------------------
class TestFailClosedCrossUnitSize:
    def test_g_vs_ml_different_base_rejects(self):
        # Both state a size in DIFFERENT bases (g vs ml) -> unverifiable equivalence -> pend.
        assert _weight_or_volume_mismatch(
            "CeraVe Moisturizing Cream 340g", "CeraVe Moisturizing Cream 177ml") is True
        assert _selection_match(
            "CeraVe Moisturizing Cream 340g", "CeraVe Moisturizing Cream 177ml",
            "skincare", candidate_brand="CeraVe") is False

    def test_guard_same_base_and_one_sided_unaffected(self):
        # Same base same value still matches; a candidate stating BOTH still matches on g.
        assert _weight_or_volume_mismatch("Cream 340g", "Cream 340g 177ml") is False
        # One-sided (candidate omits size) is still tolerated by this axis.
        assert _weight_or_volume_mismatch("Cream 340g", "Cream") is False


class TestSpfAddTolerated:
    # External review #4 — an SPF-add fail-close was implemented and REVERTED (the
    # sunscreen carve-out cannot cover the unbounded set of sunscreen names; the leak it
    # prevents is low-harm). A one-sided SPF is TOLERATED; only a both-stated DIFFERENT SPF
    # rejects (handled by _spf_mismatch elsewhere).
    def test_one_sided_spf_add_tolerated(self):
        assert _selection_match(
            "Kiehl's Ultra Facial Cream", "Kiehl's Ultra Facial Cream SPF 30",
            "skincare", candidate_brand="Kiehl's") is True


class TestFailClosedBackstopFlanker:
    def test_flagship_flanker_pended_at_display_backstop(self):
        # A FLAGSHIP-concentration flanker (Sauvage -> Sauvage Parfum) that reached the
        # display chokepoint must PEND (the bounded _category_type_added backstop check).
        assert is_price_showable(
            "Dior Sauvage", _price("Dior Sauvage Parfum", 40.0), "fragrances",
            enforce_correctness=True) is False

    def test_guard_exact_genuine_still_shows(self):
        assert is_price_showable(
            "Dior Sauvage", _price("Dior Sauvage Eau de Toilette 100ml", 40.0),
            "fragrances", enforce_correctness=True) is True

    def test_guard_descriptive_genuine_not_over_rejected(self):
        # The softened backstop must NOT pend a CORRECT product whose genuine descriptive
        # PDP title adds marketing tokens (the superset-at-backstop over-rejection the
        # adversarial sweep found). These reach display via converted/page-scrape paths.
        assert is_price_showable(
            "The Ordinary Niacinamide 10%",
            _price("The Ordinary Niacinamide 10% + Zinc 1% 30ml", 6.0,
                   source_method="converted_usd", brand="The Ordinary"),
            "skincare", enforce_correctness=True) is True
        assert is_price_showable(
            "Now Foods Omega-3",
            _price("NOW Foods, Omega-3, Molecularly Distilled, 200 Softgels", 12.0,
                   source_method="page_scrape", brand="NOW Foods"),
            "supplements", enforce_correctness=True) is True


# ---------------------------------------------------------------------------
# #6 — a low==high AggregateOffer is the exact SKU price (re-coverage), while a
# low<high range stays skipped (correctness preserved).
# ---------------------------------------------------------------------------
def _jsonld_html(low, high):
    return (
        '<html><head><script type="application/ld+json">'
        '{"@context":"https://schema.org","@type":"Product",'
        '"name":"Sony WH-1000XM5 Wireless Headphones","brand":"Sony",'
        '"offers":{"@type":"AggregateOffer","priceCurrency":"BHD",'
        f'"lowPrice":"{low}","highPrice":"{high}",'
        '"availability":"https://schema.org/InStock"}}'
        '</script></head><body>Sony WH-1000XM5</body></html>'
    )


class TestAggregateOfferLowEqHigh:
    def test_low_eq_high_aggregate_is_used(self):
        price = extract_jsonld_price(
            _jsonld_html("129.000", "129.000"), "Sony", "BHD",
            query_name="Sony WH-1000XM5", category="electronics",
        )
        assert price is not None
        assert abs(price["amount"] - 129.0) < 0.01

    def test_low_lt_high_range_still_skipped(self):
        price = extract_jsonld_price(
            _jsonld_html("129.000", "159.000"), "Sony", "BHD",
            query_name="Sony WH-1000XM5", category="electronics",
        )
        assert price is None
