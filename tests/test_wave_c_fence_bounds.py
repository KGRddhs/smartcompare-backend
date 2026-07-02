"""Wave C (genuine-price KPI) — C1: close the B-FIX re-sweep leak ring.

Eight bounded fixes, each pinned BOTH directions against the coverage-driven
re-sweep evidence (bfix_leakResweep.json RS1-RS8 + bfix_kpiE2E.json RS-2/RS-3,
2026-07-02, every repro reproduced through the REAL runtime functions):

RS2  (HIGH) selection_primary_admits compared the candidate brand against ALL
     query tokens — a compound brand field ("Vans Suede") or a generic house
     label ("Classic") passed via a NON-brand query word. The fence now
     intersects with the QUERY's padding-BRAND token(s) only (alias-expanded
     both sides).
RS7+RS-2 (MED) the BF1 fence was CHAIN-LOCAL (6 adapter fallthroughs): the
     shared consumers — extract_price_from_shopping, select_best,
     should_cache_price — accepted the wrong-brand / brandless same-model-word
     fashion class end-to-end (the organic-harvest route reaches these with no
     adapter fence). The SAME centralized fence (_brand_evidence_ok) now runs
     at all three; both sanctioned unlocks re-pinned.
RS1+RS-3 (HIGH+MED) the BF3 one-sided year tolerance stripped GENERATION /
     SEASON / MODEL discriminators (jersey seasons, Watch SE / iPhone SE gens,
     Air Max 2021 model names). Re-bound: the title year must be an ANNOTATION
     form ("(2025)" / "GEN 2025" — never a bare mid-title year) AND the query
     must carry a NON-YEAR generation discriminator (M3/M5/S25-class token,
     never a measure like 128GB/44mm) that the title also carries.
RS4  (MED) _core_count_mismatch set-INTERSECTION masked a differing GPU bin
     under a shared CPU count (M4 Air 10c/8g vs 10c/10g). Label-aware now:
     cpu-vs-cpu and gpu-vs-gpu compare per-label; unlabelled counts keep set
     semantics against the other side's full value set; both-fully-unlabelled
     compares set EQUALITY. One-sided stays tolerated.
RS5  (MED) bare "crew" in the construction tolerance made "J Crew"
     brand-invisible. 'crew'/'neck' are now tolerated ONLY when the RAW title
     carries a garment neckline BIGRAM ("crew neck" / "v neck" / "round neck";
     the glued "crewneck"/"vneck" single tokens stay). NOTE: 'stitch'/
     'stitched' stay tolerated per the BF4 pin battery — the Disney-Stitch
     residual is documented in the re-sweep, deliberately out of C1 scope.
RS3  (MED) _STRUCTURED_OVERRIDE_BLOCK_TOKENS missed the sibling kid-segment /
     bundle wordings: boys/girls/junior/youth/toddler/bundle/combo now block
     the structured-code override (asymmetric — a query stating the marker is
     unaffected; the L1212 base unlock re-pinned).
RS6  (MED) BH-locale PATH evidence granted harvest eligibility to ANY
     off-registry https .com with a /bahrain-en/ path. The path rung now also
     requires a REGISTRY-KNOWN retail domain (catalog row of ANY status incl.
     dead — namshi qualifies; an SEO fake does not).
RS8  (LOW) the spaced-unit fold widened strict_title_match's per-word
     SUBSTRING acceptance ("5ml" in the folded "75ml", "8gb" in "128gb").
     Digit-bearing unit-shaped tokens now require token-BOUNDARY equality; the
     downstream size axis both-stated pin is kept.

Run: python -m pytest tests/test_wave_c_fence_bounds.py -q
"""
import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

import pytest

import app.services.magento_graphql_service as mg
from app.services.price_service import (
    _core_count_mismatch,
    _selection_match,
    _structured_override_variant_blocked,
    extract_price_from_shopping,
    select_best,
    selection_primary_admits,
    should_cache_price,
    strict_title_match,
)
from app.services.structured_comparison_service import (
    _harvest_organic_pdp_candidates,
    _organic_host_bh_gcc_retail,
)


# ---------------------------------------------------------------------------
# shared fixtures / helpers
# ---------------------------------------------------------------------------

_PDP = "https://www.namshi.com/bahrain-en/buy-adidas-superstar/Z1AB2C3Z/p/"


def _shop_item(title, price="BHD 30.000", link=_PDP, source="Namshi"):
    return {"title": title, "price": price, "link": link, "source": source}


def _cand(title, brand=None, amount=145.0, url=_PDP):
    d = {"title": title, "amount": amount, "currency": "BHD",
         "in_stock": True, "url": url}
    if brand is not None:
        d["brand"] = brand
    return d


def _pdp_price(title, brand=None, **over):
    base = {
        "amount": 45.0, "currency": "BHD", "retailer": "store-example-bh.com",
        "url": "https://store-example-bh.com/product/item-slug/",
        "in_stock": True, "estimated": False, "source_method": "local_bhd",
        "confidence": 0.9, "title": title,
    }
    if brand is not None:
        base["brand"] = brand
    base.update(over)
    return base


def _org(link, title="", snippet="", currency=None, price=None):
    return {"link": link, "title": title, "snippet": snippet,
            "currency": currency, "price": price, "position": 1}


def _harvest_custom(items, query_name, category="fashion"):
    return _harvest_organic_pdp_candidates(
        {"bahrain": {"organic": items}}, category,
        existing_urls=set(), query_name=query_name,
    )


def _sel_e(query, title, brand=""):
    return _selection_match(query, title, "electronics", candidate_brand=brand)


def _sel_f(query, title, brand=""):
    return _selection_match(query, title, "fashion", candidate_brand=brand)


# ===========================================================================
# RS2 — selection_primary_admits: brand evidence vs the QUERY BRAND tokens
# ===========================================================================

class TestRS2AdmitsBrandVsQueryBrandOnly:
    def test_compound_brand_field_no_longer_admits(self):
        # the re-sweep repro: cand {vans,suede} intersected q_toks on 'suede',
        # a NON-brand query word — the fence must compare against {puma} only.
        assert selection_primary_admits(
            "Puma Suede Classic", "Vans Suede Classic Sneakers",
            candidate_brand="Vans Suede", category="fashion") is False

    def test_generic_house_label_no_longer_admits(self):
        assert selection_primary_admits(
            "Puma Suede Classic", "Vans Suede Classic Sneakers",
            candidate_brand="Classic", category="fashion") is False

    def test_magento_end_to_end_compound_brand_rejects(self):
        # the exact chain the re-sweep re-opened (magento _best_match ACCEPTED)
        node = {"name": "Vans Suede Classic Sneakers", "value": 45.0,
                "currency": "BHD", "url_key": "x", "brand": "Vans Suede"}
        assert mg._best_match([node], "Puma Suede Classic", "fashion") is None

    def test_correct_brand_still_admits(self):
        assert selection_primary_admits(
            "Puma Suede Classic", "Suede Classic XXI Sneakers",
            candidate_brand="Puma", category="fashion") is True

    def test_brand_line_compound_containing_query_brand_admits(self):
        # "Adidas Originals" carries the query brand token — brand evidence OK.
        assert selection_primary_admits(
            "Adidas Superstar White", "Superstar White Sneakers",
            candidate_brand="Adidas Originals", category="fashion") is True

    def test_plain_wrong_brand_still_rejects(self):
        assert selection_primary_admits(
            "Adidas Superstar White", "Golden Goose Superstar White Sneakers",
            candidate_brand="Golden Goose", category="fashion") is False

    def test_electronics_contradicting_stamp_still_rejects(self):
        # re-pin of the BF1 electronics fence edge under the tightened rule
        assert selection_primary_admits(
            "Apple Watch Ultra 2", "Galaxy Watch Ultra LTE",
            candidate_brand="Samsung", category="electronics") is False

    def test_non_padding_brand_query_untouched(self):
        # fragrance brands are not padding — the fence stays inert
        assert selection_primary_admits(
            "YSL Black Opium Eau de Parfum 90ml", "Black Opium EDP 90 ml",
            candidate_brand="Yves Saint Laurent", category="fragrances") is True


# ===========================================================================
# RS7 + kpiE2E RS-2 — the SAME fence at the shared consumers
# ===========================================================================

class TestRS7SharedConsumerFence:
    # --- extract_price_from_shopping -------------------------------------
    def test_shopping_brandless_same_model_word_row_rejected(self):
        # RS7 repro: ounass-style brandless title served+cached as local_bhd
        got = extract_price_from_shopping(
            "Adidas Superstar White",
            [_shop_item("Superstar White Sneakers")],
            "BHD", shopping_region="bh", category="fashion")
        assert got is None

    def test_shopping_brand_in_title_row_still_accepted(self):
        got = extract_price_from_shopping(
            "Adidas Superstar White",
            [_shop_item("adidas Superstar White Sneakers")],
            "BHD", shopping_region="bh", category="fashion")
        assert got is not None
        assert got["amount"] == 30.0

    def test_shopping_non_padding_brand_query_unaffected(self):
        # the fence is bounded to padding-brand queries — Lacoste is not one
        got = extract_price_from_shopping(
            "Lacoste Ultra Dry Polo",
            [_shop_item("Lacoste Ultra Dry Polo - Green")],
            "BHD", shopping_region="bh", category="fashion")
        assert got is not None

    # --- select_best ------------------------------------------------------
    def test_select_best_wrong_brand_stamp_rejected(self):
        # kpiE2E RS-2 repro (verbatim): picked + showable + cacheable before
        assert select_best(
            [_cand("Golden Goose Superstar White Sneakers", brand="Golden Goose")],
            "Adidas Superstar White", "fashion") is None

    def test_select_best_brandless_same_model_word_rejected(self):
        assert select_best(
            [_cand("Superstar White Sneakers")],
            "Adidas Superstar White", "fashion") is None

    def test_select_best_correct_brand_stamp_brand_omitted_title_accepted(self):
        # sanctioned unlock (a): the klinq-class stamp, fashion edition
        best = select_best(
            [_cand("Superstar White Sneakers", brand="Adidas")],
            "Adidas Superstar White", "fashion")
        assert best is not None

    def test_select_best_brand_in_title_row_accepted(self):
        # sanctioned unlock (b): brandless row whose TITLE carries the brand
        best = select_best(
            [_cand("adidas Superstar Cloud White Sneakers")],
            "Adidas Superstar White", "fashion")
        assert best is not None

    # --- should_cache_price -------------------------------------------------
    def test_cache_gate_wrong_brand_stamp_refused(self):
        assert should_cache_price(
            "Adidas Superstar White",
            _pdp_price("Golden Goose Superstar White Sneakers",
                       brand="Golden Goose"),
            "fashion") is False

    def test_cache_gate_brandless_same_model_word_refused(self):
        assert should_cache_price(
            "Adidas Superstar White",
            _pdp_price("Superstar White Sneakers"),
            "fashion") is False

    def test_cache_gate_correct_brand_rows_still_cache(self):
        assert should_cache_price(
            "Adidas Superstar White",
            _pdp_price("adidas Superstar Cloud White Sneakers"),
            "fashion") is True
        assert should_cache_price(
            "Adidas Superstar White",
            _pdp_price("Superstar White Sneakers", brand="Adidas"),
            "fashion") is True

    def test_cache_gate_klinq_class_unaffected(self):
        # fragrance brands are not padding-strippable — fence inert
        assert should_cache_price(
            "YSL Black Opium Eau de Parfum 90ml",
            _pdp_price("Black Opium EDP 90 ml", brand="Yves Saint Laurent"),
            "fragrances") is True

    def test_cache_gate_electronics_brand_omitted_unaffected(self):
        # (b) applies to FASHION only — the B4 electronics brand-omitted
        # unlock is untouched at the shared consumers too
        assert should_cache_price(
            "Apple iPad Air 11-inch M3 128GB",
            _pdp_price("iPad Air 11-inch M3 Wi-Fi 128GB Space Grey"),
            "electronics") is True


# ===========================================================================
# RS1 + kpiE2E RS-3 — the year tolerance re-bound
# ===========================================================================

class TestRS1YearToleranceRebound:
    # --- the BF3 unlocks MUST still hold (annotation + matched discriminator)
    def test_sharafdg_ipad_paren_year_still_tolerated(self):
        assert _sel_e(
            "Apple iPad Air 11-inch M3 128GB",
            "iPad Air 11-inch M3 (2025) Wi-Fi 128GB - Space Grey Middle East "
            "Version with FaceTime", brand="Apple") is True

    def test_extra_ipad_gen_year_still_tolerated(self):
        assert _sel_e(
            "Apple iPad Air 11-inch M3 128GB",
            "APPLE IPAD AIR M3 GEN 2025, Wi-Fi, 11 INCH, 128GB, Space Grey",
            brand="Apple") is True

    def test_sharafdg_mba_paren_year_still_tolerated(self):
        assert _sel_e(
            "MacBook Air 13 M5 512GB",
            "Apple MacBook Air M5 13-inch (2026) - 10-core CPU / 16GB RAM / "
            "512GB SSD / 8-core GPU - Midnight", brand="Apple") is True

    # --- the re-sweep leaks MUST now reject
    def test_iphone_se_generation_leak_rejects(self):
        # annotation form BUT no non-year generation discriminator in the
        # query (128GB is a measure, never a discriminator)
        assert _sel_e("iPhone SE 128GB", "Apple iPhone SE (2020) 128GB",
                      brand="Apple") is False
        assert _sel_e("iPhone SE 128GB", "Apple iPhone SE (2022) 128GB",
                      brand="Apple") is False

    def test_watch_se_generation_leak_rejects(self):
        # 44mm is measure-shaped — not a generation discriminator
        assert _sel_e("Apple Watch SE 44mm GPS",
                      "Apple Watch SE (2020) 44mm GPS", brand="Apple") is False

    def test_jersey_season_year_leak_rejects(self):
        # bare mid-title year = the SEASON SKU, never annotation
        assert _sel_f("Real Madrid Home Jersey",
                      "Real Madrid Home Jersey 2024 White") is False

    def test_air_max_model_year_leak_rejects(self):
        # bare year IS the model name (Air Max 2021)
        assert _sel_f("Nike Air Max", "Nike Air Max 2021 Shoes White") is False

    def test_dunk_low_annotation_year_leak_rejects(self):
        # kpiE2E RS-3: annotation form, but a fashion query with no
        # digit-bearing generation discriminator keeps the year required
        assert _sel_f("Nike Dunk Low", "Nike Dunk Low (2021) Retro",
                      brand="Nike") is False

    # --- bounds / non-regression
    def test_bare_year_with_discriminator_still_rejects(self):
        # condition (a) alone: a NON-annotation bare year stays identity even
        # when the query carries a matched discriminator
        assert _sel_e("Samsung Galaxy S25 256GB",
                      "Samsung Galaxy S25 2025 256GB") is False

    def test_model_token_discriminator_unlocks_annotation_year(self):
        # a matched model-line token (WH-1000XM5) is a generation discriminator
        assert _sel_e("Sony WH-1000XM5", "Sony WH-1000XM5 (2022)") is True

    def test_query_stated_year_keeps_the_full_axis(self):
        # unchanged: a query-stated year never tolerates a different one
        assert _sel_e("Apple iPhone SE 2022 128GB",
                      "Apple iPhone SE (2020) 128GB", brand="Apple") is False
        assert _sel_e("Apple iPhone SE 2022 128GB",
                      "Apple iPhone SE (2022) 128GB", brand="Apple") is True

    def test_chip_axis_never_bridged(self):
        # M2 predecessor title: annotation year + a query discriminator the
        # title does NOT carry — no tolerance, and the chip axis rejects
        assert _sel_e(
            "Apple iPad Air 11-inch M3 128GB",
            "iPad Air 11-inch M2 (2024) Wi-Fi 128GB - Space Grey",
            brand="Apple") is False

    def test_end_to_end_jersey_never_serves_or_caches(self):
        # RS1's tier claim: the shopping extractor + write gate both reject
        assert extract_price_from_shopping(
            "Real Madrid Home Jersey",
            [_shop_item("Real Madrid Home Jersey 2024 White")],
            "BHD", shopping_region="bh", category="fashion") is None
        assert should_cache_price(
            "Real Madrid Home Jersey",
            _pdp_price("Real Madrid Home Jersey 2024 White"),
            "fashion") is False


# ===========================================================================
# RS4 — label-aware core-count axis
# ===========================================================================

class TestRS4LabelAwareCoreCounts:
    Q_10_10 = "Apple MacBook Air M4 13 10-Core CPU 10-Core GPU 512GB"
    T_10_8 = "Apple MacBook Air M4 13-inch 10-Core CPU 8-Core GPU 512GB"
    T_10_10 = "Apple MacBook Air M4 13-inch 10-Core CPU 10-Core GPU 512GB SSD"

    def test_shared_cpu_no_longer_masks_gpu_bin(self):
        # the re-sweep repro: {10} & {10,8} non-empty accepted the 8-GPU bin
        assert _core_count_mismatch(self.Q_10_10, self.T_10_8) is True

    def test_end_to_end_wrong_gpu_bin_rejects(self):
        assert _sel_e(self.Q_10_10, self.T_10_8, brand="Apple") is False
        assert should_cache_price(
            self.Q_10_10, _pdp_price(self.T_10_8, brand="Apple"),
            "electronics") is False

    def test_matching_bins_still_accept(self):
        assert _core_count_mismatch(self.Q_10_10, self.T_10_10) is False
        assert _sel_e(self.Q_10_10, self.T_10_10, brand="Apple") is True

    def test_one_sided_counts_stay_tolerated(self):
        # query states no counts — spec noise, unchanged
        assert _core_count_mismatch("MacBook Air 13 M5 512GB",
                                    "10-core CPU / 8-core GPU") is False

    def test_unlabelled_query_vs_labelled_title_keeps_set_semantics(self):
        # existing pins: the unlabelled value compares against the FULL set
        assert _core_count_mismatch("MacBook Pro 14 M4 12-core 1TB",
                                    "MacBook Pro 14-inch M4 10-core CPU 1TB") is True
        assert _core_count_mismatch("MacBook Air M5 10-core",
                                    "10-core CPU / 8-core GPU") is False

    def test_both_fully_unlabelled_compare_set_equality(self):
        assert _core_count_mismatch("MacBook Pro 12-core",
                                    "MacBook Pro 12-core") is False
        assert _core_count_mismatch("MacBook Pro 12-core",
                                    "MacBook Pro 10-core") is True

    def test_labelled_one_axis_only_title_tolerated(self):
        # title states only the CPU count — the GPU axis is one-sided
        assert _core_count_mismatch(self.Q_10_10,
                                    "MacBook Air M4 10-Core CPU 512GB") is False


# ===========================================================================
# RS5 — construction tolerance re-bound to garment bigrams
# ===========================================================================

class TestRS5ConstructionBigramBound:
    Q_TOMMY = "Tommy Hilfiger Essential Flag T-Shirt"

    def test_j_crew_no_longer_brand_invisible(self):
        # the re-sweep repro: 'j' len-dropped + 'crew' tolerance-dropped made
        # the J Crew product serve as the Adidas query's price
        assert _sel_f("Adidas Essentials Hoodie", "J Crew Essentials Hoodie") is False

    def test_j_crew_never_serves_or_caches(self):
        assert extract_price_from_shopping(
            "Adidas Essentials Hoodie",
            [_shop_item("J Crew Essentials Hoodie")],
            "BHD", shopping_region="bh", category="fashion") is None
        assert should_cache_price(
            "Adidas Essentials Hoodie",
            _pdp_price("J Crew Essentials Hoodie"),
            "fashion") is False

    def test_namshi_crew_neck_bigram_still_unlocks(self):
        # the kpi-fash-006 exact SKU title (BF4's sanctioned unlock)
        assert _sel_f(self.Q_TOMMY,
                      "Essential Flag Embroidery Crew Neck T-Shirt",
                      brand="Tommy Hilfiger") is True

    @pytest.mark.parametrize("added", ["Crew Neck", "Crew-Neck", "V Neck",
                                       "Round Neck", "Crewneck", "V-Neck"])
    def test_neckline_bigram_forms_tolerated(self, added):
        assert _sel_f(self.Q_TOMMY, f"Essential Flag {added} T-Shirt",
                      brand="Tommy Hilfiger") is True

    def test_bare_crew_token_no_longer_tolerated(self):
        # tightened direction: no bigram in the title -> 'crew' stays a
        # distinctive add (fail-closed; "Crew Tee" shorthand is the accepted
        # over-rejection tradeoff of closing the J-Crew brand-invisibility)
        assert _sel_f(self.Q_TOMMY, "Essential Flag Crew T-Shirt",
                      brand="Tommy Hilfiger") is False

    def test_bare_neck_token_no_longer_tolerated(self):
        assert _sel_f(self.Q_TOMMY, "Essential Flag Neck Detail T-Shirt",
                      brand="Tommy Hilfiger") is False

    def test_both_stated_different_neckline_still_rejects(self):
        # the query-side token stays required — unchanged both-stated guard
        assert _sel_f("Tommy Hilfiger Essential V-Neck T-Shirt",
                      "Essential Crew Neck T-Shirt",
                      brand="Tommy Hilfiger") is False
        assert _sel_f("Tommy Hilfiger Essential Crew Neck T-Shirt",
                      "Essential V-Neck T-Shirt",
                      brand="Tommy Hilfiger") is False

    def test_query_stated_crew_neck_matches_crew_neck_title(self):
        assert _sel_f("Tommy Hilfiger Essential Flag Crew Neck T-Shirt",
                      "Essential Flag Crew Neck T-Shirt",
                      brand="Tommy Hilfiger") is True


# ===========================================================================
# RS3 — sibling kid-segment / bundle wordings block the code override
# ===========================================================================

class TestRS3StructuredOverrideSiblingMarkers:
    @pytest.mark.parametrize("marker", ["Boys", "Girls", "Junior", "Youth",
                                        "Toddler", "Bundle", "Combo"])
    def test_sibling_marker_add_blocks_override(self, marker):
        assert _structured_override_variant_blocked(
            "Lacoste L1212 Polo",
            f"Logo Detail Polo Shirt {marker} - White L1212") is True

    @pytest.mark.parametrize("marker", ["Boys", "Bundle"])
    def test_sibling_marker_never_caches_end_to_end(self, marker):
        p = _pdp_price(f"Logo Detail Polo Shirt {marker} - White",
                       brand="Lacoste", structured_code="L1212")
        assert should_cache_price("Lacoste L1212 Polo", p, "fashion") is False

    def test_query_stating_the_marker_is_unaffected(self):
        # asymmetry pin: the suppression fires only on tokens the title ADDS
        assert _structured_override_variant_blocked(
            "Lacoste L1212 Polo Boys",
            "Logo Detail Polo Shirt Boys L1212") is False

    def test_l1212_base_unlock_still_passes(self):
        p = _pdp_price("Logo Detail Short Sleeves Polo T-Shirt",
                       brand="Lacoste", structured_code="L1212")
        assert should_cache_price("Lacoste L1212 Polo", p, "fashion") is True


# ===========================================================================
# RS6 — BH-locale path evidence requires a registry-KNOWN retail domain
# ===========================================================================

class TestRS6LocalePathRequiresKnownRetailDomain:
    def test_off_registry_fake_with_bh_path_refused(self):
        # the re-sweep repro: a crafted SEO domain with a /bahrain-en/ path
        assert _organic_host_bh_gcc_retail(
            "best-bahrain-prices.com",
            path="/bahrain-en/apple-iphone-15-pro-256gb-deal") == (False, False)

    def test_off_registry_fake_never_harvests_end_to_end(self):
        rows = _harvest_custom(
            [_org("https://best-bahrain-prices.com/bahrain-en/"
                  "apple-iphone-15-pro-256gb-deal",
                  "Apple iPhone 15 Pro 256GB Best Bahrain Price", "BHD 300")],
            "Apple iPhone 15 Pro 256GB", category="electronics")
        assert rows == []

    def test_namshi_dead_catalog_row_still_qualifies(self):
        # namshi.com is a CATALOG row (status="dead") — registry-KNOWN even
        # though registry_tier() is None; the BF5 unlock must survive
        assert _organic_host_bh_gcc_retail(
            "namshi.com", path="/bahrain-en/buy-x/Z1ABC2Z/p/") == (True, False)

    def test_namshi_pdp_still_harvests_end_to_end(self):
        link = ("https://www.namshi.com/bahrain-en/buy-ray-ban-0rb3025-"
                "aviator-sunglasses/ZED28E4F81949E4666601Z/p/")
        rows = _harvest_custom(
            [_org(link, "Ray-Ban 0Rb3025 Aviator Sunglasses", "82.52 BHD")],
            "Ray-Ban Aviator RB3025")
        assert [r[0] for r in rows] == [link]

    def test_en_sa_ounass_stays_gcc_registry_only(self):
        assert _organic_host_bh_gcc_retail("en-sa.ounass.com") == (True, True)
        assert _organic_host_bh_gcc_retail(
            "en-sa.ounass.com", path="/saudi-en/x") == (True, True)

    def test_bh_tld_and_bahrain_prefix_rungs_unchanged(self):
        # the other rungs are untouched: registry tier (alhajis = bahrain),
        # .bh TLD and bahrain.-prefix need no path/catalog evidence
        assert _organic_host_bh_gcc_retail("alhajisbahrain.com") == (True, True)
        assert _organic_host_bh_gcc_retail("boutique.com.bh") == (True, False)
        assert _organic_host_bh_gcc_retail("bahrain.example.com") == (True, False)


# ===========================================================================
# RS8 — strict_title_match token-boundary equality for unit tokens
# ===========================================================================

class TestRS8StrictUnitTokenBoundary:
    def test_folded_substring_size_no_longer_accepts(self):
        # '5ml' substring-matched the folded '75 ml' -> '75ml'
        assert strict_title_match("Chanel No 5 EDP 5ml",
                                  "Chanel No 5 EDP 75 ml") is False

    def test_folded_substring_storage_no_longer_accepts(self):
        # '8gb' substring-matched the folded '128 GB' -> '128gb'
        assert strict_title_match("Xiaomi Redmi Note 13 8GB",
                                  "Xiaomi Redmi Note 13 128 GB") is False

    def test_exact_unit_tokens_still_match_spaced_titles(self):
        # the BF3 unlocks keep passing (boundary equality, not substring)
        assert strict_title_match("Samsung Galaxy S25 Ultra 256GB",
                                  "SAMSUNG Galaxy S25 Ultra, 5G, 256 GB, "
                                  "Titanium Black") is True
        assert strict_title_match("YSL Black Opium Eau de Parfum 90ml",
                                  "YSL Black Opium (W) EDP 90 ml") is True
        assert strict_title_match("Apple Watch Series 10 45mm",
                                  "Apple Watch Series 10, 45 mm, Jet Black") is True

    def test_decimal_prefix_is_a_boundary_violation(self):
        # '5ml' must not match inside '13.5ml' (a decimal fraction)
        assert strict_title_match("Chanel No 5 EDP 5ml",
                                  "Chanel No 5 EDP 13.5 ml") is False

    def test_downstream_size_axis_still_rejects_both_stated(self):
        # keep the RS8-noted pin: the axis gate catches the class downstream
        assert _selection_match("Chanel No 5 EDP 5ml",
                                "Chanel No 5 EDP 75 ml", "fragrances") is False

    def test_gate_off_keeps_legacy_tokenization(self, monkeypatch):
        # rollback surface: no fold, no boundary rule (byte-identical legacy)
        monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "false")
        assert strict_title_match("Chanel No 5 EDP 5ml",
                                  "Chanel No 5 EDP 75ml") is True
