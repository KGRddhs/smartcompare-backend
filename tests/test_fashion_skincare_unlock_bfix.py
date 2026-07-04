"""Wave B-FIX BF4 — FASHION + SKINCARE over-rejection unlock (coverage sweep
OR-6/OR-7/OR-9/OR-10, waveb_overRejection.json 2026-07-02).

Every fix is a BOUNDED relaxation, pinned in BOTH directions (the fix's own
over-acceptance is the next blind spot):

  OR-6  FASHION CONSTRUCTION/NECKLINE title-side tolerance — namshi lists the
        kpi-fash-006 exact SKU as "Essential Flag Embroidery Crew Neck
        T-Shirt"; 'Embroidery'/'Crew'/'Neck' each variant-add-rejected it.
        The token set {crew, neck, crewneck, vneck, embroidery, embroidered}
        (+ stitch/stitched ONLY inside a sewing-context bigram, B1.1c) is
        tolerated as a TITLE add for fashion ONLY when
        the query does not carry the token (the _ELECTRONICS_TITLE_SIDE_
        TOLERATED "AI" asymmetry) AND q_core is non-empty (the emptied
        brand/class-query fence is unchanged). NOTE: there is NO dedicated
        both-stated neckline axis — a query-stated neckline keeps its token
        required, so V-Neck-query vs Crew-Neck-title rejects via the LEAK-
        direction subset (pinned below in both directions).
  OR-7  the 'skin' ACCESSORY_KEYWORDS false-positive — phone-decal keyword
        hitting genuine pharmacy titles ("For Normal To Oily SKIN", "All SKIN
        Types") on all six direct store-API chains (occ/woo/salla/algolia x2/
        unbxd). The nasser matcher (price_service ~:7813) already documents +
        exempts this exact false-positive; the chains now scope it via
        is_accessory_for_category: for a PHARMACY-class resolved category
        (skincare/haircare/supplements/makeup) a bare "skin" hit alone is not
        an accessory signal — any OTHER accessory keyword still flags, and
        every non-pharmacy category (incl. None — fail-closed) keeps the full
        broad is_accessory (a real "Skin Decal Wrap" under an electronics
        query still rejects).
  OR-9  the Luxottica 0-prefix fold generalized from (rb|rx) to ANY
        two-letter house code (^0([a-z]{2}\\d{3,})$) — namshi lists ALL
        Luxottica-house brands with the catalog 0-prefix (0Oo9102 Oakley,
        0Po0714 Persol, live-verified 0Rb3025). Full-token, 0 + exactly two
        letters + 3+ digits: a pure-numeric leading-zero token ("0801") is
        NEVER stripped.
  OR-10 "eyeglasses" joins the generic class-noun set beside "sunglasses"/
        "eyewear" (the optical-frame listing noun on namshi/eyewa/optica).
        "optical frame" can NOT be added: the generic sets are single-TOKEN
        sets (normalize_words tokens) — a phrase can never match, and the
        bare tokens "optical"/"frame" are collision-prone cross-category
        (digital photo Frame) so they are deliberately omitted.
"""
import pytest

from app.services.price_service import (
    ACCESSORY_KEYWORDS,
    _identity_tokens_ps,
    _selection_match,
    is_accessory,
    is_accessory_for_category,
    should_cache_price,
    strict_title_match,
)
from app.services.occ_service import _select_product
from app.services.salla_service import _select_candidate
from app.services.woocommerce_service import _match_woo_product
from app.services.unbxd_service import _match_unbxd_product
from app.services.algolia_service import (
    ALGOLIA_EXPLICIT_STORES,
    _catalog_match_hit,
    _match_algolia_hit,
)
from scripts.eval_runner import (
    load_usable_exact_genuine_truth,
    usable_exact_genuine_for_product,
)


@pytest.fixture(autouse=True)
def _flags(monkeypatch):
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "true")
    monkeypatch.delenv("ENABLE_ADAPTER_SELECTION_PRIMARY", raising=False)
    monkeypatch.delenv("ENABLE_ADAPTER_QUERY_LADDER", raising=False)


def _sel(query, title, brand="", cat="fashion"):
    return _selection_match(query, title, cat, candidate_brand=brand)


# The LIVE titles the sweep bisected — verbatim.
Q_TOMMY = "Tommy Hilfiger Essential Flag T-Shirt"
T_NAMSHI_TEE = "Essential Flag Embroidery Crew Neck T-Shirt"
Q_CERAVE = "CeraVe Foaming Cleanser 236ml"
T_BOOTS_CERAVE = "Foaming Cleanser For Normal To Oily Skin 236 ml"
T_BRANDED_CERAVE = "CeraVe Foaming Cleanser For Normal To Oily Skin 236 ml"

_TRUTH = {p["id"]: p for p in load_usable_exact_genuine_truth()}
_NAMSHI_PDP = ("https://www.namshi.com/bahrain-en/buy-tommy-hilfiger-essential-"
               "flag-embroidery-crew-neck-t-shirt/p/912345")


# ---------------------------------------------------------------------------
# OR-6 — fashion construction/neckline title-side tolerance
# ---------------------------------------------------------------------------

class TestFashionConstructionTolerance:
    def test_namshi_crew_tee_matches_tommy_truth_query(self):
        # RED->GREEN: 'Embroidery'/'Crew'/'Neck' each individually rejected
        # the only recon-verified kpi-fash-006 source (namshi 9.22 InStock).
        assert _sel(Q_TOMMY, T_NAMSHI_TEE, brand="Tommy Hilfiger") is True

    @pytest.mark.parametrize("added", ["Embroidery", "Crew Neck", "Crewneck",
                                       "V-Neck"])
    def test_each_construction_add_tolerated_alone(self, added):
        assert _sel(Q_TOMMY, f"Essential Flag {added} T-Shirt",
                    brand="Tommy Hilfiger") is True

    # Wave-2 B1.1c (gate-scoped, un-flagged): a BARE 'stitch'/'stitched' is NO
    # LONGER tolerated alone — a standalone "Stitch" is the Disney character (a
    # distinct graphic-print SKU, census FULL-leak). It tolerates ONLY inside a
    # sewing-context bigram ("stitched logo"/"contrast stitch"/"topstitch").
    @pytest.mark.parametrize("added", ["Stitch", "Stitched"])
    def test_bare_stitch_now_distinctive(self, added):
        assert _sel(Q_TOMMY, f"Essential Flag {added} T-Shirt",
                    brand="Tommy Hilfiger") is False

    @pytest.mark.parametrize("added", ["stitched logo", "contrast stitch",
                                       "stitch detail", "topstitch"])
    def test_stitch_in_sewing_bigram_still_tolerated(self, added):
        assert _sel(Q_TOMMY, f"Essential Flag {added} T-Shirt",
                    brand="Tommy Hilfiger") is True

    # ---- bounds (adversarial, both directions) ----

    def test_polo_query_vs_crew_tee_class_swap_still_rejects(self):
        # CRITICAL bound: the polo/t-shirt CLASS axis is untouched — a polo
        # query never matches a plain crew tee.
        assert _sel("Tommy Hilfiger Essential Flag Polo", T_NAMSHI_TEE,
                    brand="Tommy Hilfiger") is False

    def test_a2_polo_compound_tightening_still_holds(self):
        # "Polo T-Shirt" collapses to class polo: a polo query matches it, a
        # plain t-shirt query class-swap-rejects it (both directions pinned
        # in test_matcher_folds_wave_a; re-pinned here against THIS change).
        assert _sel("Lacoste L1212 Polo", "L1212 Polo T-Shirt - White",
                    brand="Lacoste") is True
        assert _sel(Q_TOMMY, "Essential Flag Polo T-Shirt",
                    brand="Tommy Hilfiger") is False

    def test_both_stated_neckline_contradiction_rejects(self):
        # NO dedicated neckline axis exists — the LEAK-direction subset is the
        # both-stated guard: the query's own neckline token stays required.
        assert _sel("Tommy Hilfiger Essential V-Neck T-Shirt",
                    "Essential Crew Neck T-Shirt",
                    brand="Tommy Hilfiger") is False
        assert _sel("Tommy Hilfiger Essential Crew Neck T-Shirt",
                    "Essential V-Neck T-Shirt",
                    brand="Tommy Hilfiger") is False

    def test_query_stated_construction_still_required(self):
        # The tolerance is title-side ONLY: a query that states the neckline
        # does not match a title omitting it (fail-closed, unchanged).
        assert _sel("Tommy Hilfiger Essential Crew Neck T-Shirt",
                    "Essential Flag T-Shirt", brand="Tommy Hilfiger") is False

    def test_emptied_generic_query_fence_unchanged(self):
        # q_core-non-empty bound: a fashion brand/class query (core emptied to
        # padding) still matches NO specific member — the tolerance must not
        # blank a construction-only distinctive core into an accept.
        assert _sel("Nike T-Shirt", "Nike Stitch T-Shirt") is False

    def test_non_fashion_categories_untouched(self):
        # 'crew'/'neck' stay distinctive tokens outside fashion.
        assert _selection_match("Logitech MX Keys", "Logitech MX Keys Crew",
                                "electronics") is False

    def test_other_variant_adds_still_reject(self):
        # The tolerance releases ONLY the bounded construction set — any other
        # distinctive add is still a different SKU.
        assert _sel(Q_TOMMY, "Essential Flag Monogram T-Shirt",
                    brand="Tommy Hilfiger") is False

    # ---- end-to-end: adapter + cache + eval-usable (kpi-fash-006) ----

    def test_adapter_accepts_namshi_style_row(self):
        # occ-shaped chain (carries the brand field like the namshi feed).
        payload = {"products": [{
            "name": T_NAMSHI_TEE, "manufacturer": "Tommy Hilfiger",
            "price": {"value": 9.22, "currencyIso": "BHD"},
            "url": "/p/912345", "stock": {"stockLevelStatus": "inStock"},
        }]}
        got = _select_product(payload, Q_TOMMY, "fashion")
        assert got is not None and got["name"] == T_NAMSHI_TEE

    def test_cache_write_and_kpi_usable(self):
        price = {"amount": 9.22, "currency": "BHD", "retailer": "namshi",
                 "url": _NAMSHI_PDP, "in_stock": True, "estimated": False,
                 "source_method": "local_bhd", "title": T_NAMSHI_TEE,
                 "brand": "Tommy Hilfiger", "confidence": 0.9}
        assert should_cache_price(Q_TOMMY, price, "fashion") is True
        body = {"overview": {"products": [{"price": price}]}}
        assert usable_exact_genuine_for_product(
            body, 0, _TRUTH["kpi-fash-006"]) is True

    def test_wrong_sku_never_caches(self):
        # the tolerance must not have opened the cache to a non-construction add
        price = {"amount": 9.22, "currency": "BHD", "retailer": "namshi",
                 "url": _NAMSHI_PDP, "in_stock": True, "estimated": False,
                 "source_method": "local_bhd",
                 "title": "Essential Flag Polo T-Shirt",
                 "brand": "Tommy Hilfiger", "confidence": 0.9}
        assert should_cache_price(Q_TOMMY, price, "fashion") is False


# ---------------------------------------------------------------------------
# OR-7 — 'skin' accessory false-positive scoped out of the pharmacy chains
# ---------------------------------------------------------------------------

class TestPharmacySkinAccessoryScoping:
    def test_wrapper_pharmacy_categories_ignore_bare_skin(self):
        for cat in ("skincare", "haircare", "supplements", "makeup"):
            assert is_accessory_for_category(T_BOOTS_CERAVE, cat) is False
            assert is_accessory_for_category(
                "Nivea Soft Moisturising Cream All Skin Types 200ml", cat) is False

    def test_wrapper_non_pharmacy_keeps_broad_filter(self):
        # Electronics (and unresolved None — fail-closed) keep the full set:
        # a REAL phone-skin decal still classifies as an accessory.
        assert is_accessory_for_category("Galaxy S25 Skin Decal Wrap",
                                         "electronics") is True
        assert is_accessory_for_category(T_BOOTS_CERAVE, None) is True
        assert is_accessory_for_category(T_BOOTS_CERAVE, "other") is True

    def test_wrapper_other_accessory_keywords_still_flag_in_pharmacy(self):
        # Only the bare-'skin' hit is exempt — any other keyword still flags.
        assert is_accessory_for_category("CeraVe Cleansing Brush Case",
                                         "skincare") is True
        assert is_accessory_for_category("Vitamin Organizer Pouch",
                                         "supplements") is True

    def test_broad_is_accessory_unchanged(self):
        # The Serper-shopping paths keep the broad filter — 'skin' still in it.
        assert "skin" in ACCESSORY_KEYWORDS
        assert is_accessory(T_BOOTS_CERAVE) is True
        assert is_accessory("Galaxy S25 Skin Decal Wrap") is True

    # ---- the six direct-API chains accept genuine skin-carrying titles ----

    def test_occ_chain_accepts_pharmacy_skin_title(self):
        # The sweep's exact repro: occ chain rejected this even though strict
        # falls through and _selection_match is True.
        payload = {"products": [{
            "name": T_BOOTS_CERAVE, "manufacturer": "CeraVe",
            "price": {"value": 5.2, "currencyIso": "BHD"},
            "url": "/p/123", "stock": {"stockLevelStatus": "inStock"},
        }]}
        got = _select_product(payload, Q_CERAVE, "skincare")
        assert got is not None and got["name"] == T_BOOTS_CERAVE

    def test_woo_chain_accepts_pharmacy_skin_title(self):
        products = [{
            "name": T_BRANDED_CERAVE,
            "prices": {"price": "5200", "currency_code": "BHD",
                       "currency_minor_unit": 3},
            "permalink": "https://bahrainpharmacy.com/product/cerave-foaming-cleanser/",
            "is_in_stock": True,
        }]
        got = _match_woo_product(products, Q_CERAVE, "BHD",
                                 resolved_category="skincare")
        assert got is not None and got["title"] == T_BRANDED_CERAVE

    def test_salla_chain_accepts_pharmacy_skin_title(self):
        got = _select_candidate([{"name": T_BRANDED_CERAVE, "price": 5.2}],
                                Q_CERAVE, "skincare")
        assert got is not None and got["name"] == T_BRANDED_CERAVE

    def test_unbxd_chain_accepts_pharmacy_skin_title(self):
        hit = {"title": T_BRANDED_CERAVE, "sellingPrice": 5.2,
               "inStockFlag": "true",
               "productUrl": "https://www.example.bh/x/p/100"}
        got = _match_unbxd_product([hit], Q_CERAVE, resolved_category="skincare")
        assert got is not None and got["title"] == T_BRANDED_CERAVE

    def test_algolia_hit_chain_accepts_pharmacy_skin_title(self):
        hit = {"name": T_BOOTS_CERAVE, "brand": "CeraVe",
               "price": [{"BHD": {"default": 5.2}}]}
        got = _match_algolia_hit([hit], Q_CERAVE, resolved_category="skincare")
        assert got is not None and got["name"] == T_BOOTS_CERAVE

    def test_algolia_catalog_chain_accepts_pharmacy_skin_title(self):
        store = ALGOLIA_EXPLICIT_STORES["bahrain.sharafdg.com"]
        hit = {"post_title": T_BRANDED_CERAVE, "price": 5.2, "in_stock": 1,
               "permalink": "https://bahrain.sharafdg.com/product/x/"}
        got = _catalog_match_hit([hit], Q_CERAVE, store,
                                 resolved_category="skincare")
        assert got is not None and got["post_title"] == T_BRANDED_CERAVE

    # ---- adversarial: the electronics decal class stays rejected ----

    def test_unbxd_still_rejects_real_skin_accessory_for_electronics(self):
        hit = {"title": "Samsung Galaxy S25 256GB Skin Decal Wrap",
               "sellingPrice": 4.9, "inStockFlag": "true",
               "productUrl": "https://www.extra.com/en-bh/x/p/100"}
        assert _match_unbxd_product([hit], "Samsung Galaxy S25 256GB",
                                    resolved_category="electronics") is None

    def test_occ_still_rejects_real_skin_accessory_for_electronics(self):
        payload = {"products": [{
            "name": "Galaxy S25 Skin Decal Wrap", "manufacturer": "Samsung",
            "price": {"value": 4.9, "currencyIso": "BHD"},
            "url": "/p/9", "stock": {"stockLevelStatus": "inStock"},
        }]}
        assert _select_product(payload, "Samsung Galaxy S25",
                               "electronics") is None


# ---------------------------------------------------------------------------
# OR-9 — Luxottica 0-prefix fold generalized to ^0([a-z]{2}\d{3,})$
# ---------------------------------------------------------------------------

class TestLuxotticaZeroFoldGeneralized:
    def test_oakley_zero_prefixed_code_accepts(self):
        assert _sel("Oakley Holbrook OO9102",
                    "Oakley 0Oo9102 Holbrook Sunglasses", brand="Oakley") is True

    def test_persol_zero_prefixed_code_accepts(self):
        assert _sel("Persol PO0714 Steve McQueen",
                    "Persol 0Po0714 Steve McQueen Sunglasses",
                    brand="Persol") is True

    def test_rayban_regression_still_accepts(self):
        # the original rb/rx forms keep working (kpi-fash-004 class)
        assert _sel("Ray-Ban Aviator RB3025",
                    "Ray-Ban 0Rb3025 Aviator Sunglasses", brand="Ray-Ban") is True

    def test_different_code_still_rejects(self):
        # both directions: the fold is an ALIAS, never a wildcard
        assert _sel("Oakley Holbrook OO9102",
                    "Oakley 0Oo9208 Holbrook Sunglasses", brand="Oakley") is False
        assert _sel("Ray-Ban Aviator RB3025",
                    "Ray-Ban 0Rb3026 Aviator Sunglasses", brand="Ray-Ban") is False

    def test_pure_numeric_leading_zero_never_stripped(self):
        # "0801"-style tokens must stay untouched (the NARROW-by-design pin).
        toks = _identity_tokens_ps("Style 0801 Jacket", "", "fashion")
        assert "0801" in toks
        # and the fold requires >=3 digits: 0ab12 stays identity as-is
        toks2 = _identity_tokens_ps("Model 0ab12", "", "fashion")
        assert "0ab12" in toks2 and "ab12" not in toks2


# ---------------------------------------------------------------------------
# OR-10 — "eyeglasses" joins the generic class-noun set
# ---------------------------------------------------------------------------

class TestEyeglassesGenericNoun:
    def test_rx5154_clubmaster_eyeglasses_accepts(self):
        assert _sel("Ray-Ban RX5154 Clubmaster",
                    "Ray-Ban 0Rx5154 Clubmaster Eyeglasses",
                    brand="Ray-Ban") is True

    def test_sunglasses_control_still_accepts(self):
        assert _sel("Ray-Ban RX5154 Clubmaster",
                    "Ray-Ban 0Rx5154 Clubmaster Sunglasses",
                    brand="Ray-Ban") is True

    def test_class_swap_sunglasses_vs_eyeglasses_rejects(self):
        # A generic-noun pair that DISAGREES is a class swap: the sun and
        # optical Clubmaster are different (differently-priced) products.
        assert _sel("Ray-Ban RX5154 Clubmaster Sunglasses",
                    "Ray-Ban 0Rx5154 Clubmaster Eyeglasses",
                    brand="Ray-Ban") is False
        assert _sel("Ray-Ban RX5154 Clubmaster Eyeglasses",
                    "Ray-Ban 0Rx5154 Clubmaster Sunglasses",
                    brand="Ray-Ban") is False

    def test_query_side_eyeglasses_tolerated_when_title_omits(self):
        # generic nouns are tolerated-when-omitted in either direction
        assert _sel("Ray-Ban RX5154 Clubmaster Eyeglasses",
                    "Ray-Ban 0Rx5154 Clubmaster", brand="Ray-Ban") is True
