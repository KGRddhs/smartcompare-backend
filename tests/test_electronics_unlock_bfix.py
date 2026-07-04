"""Wave B-FIX BF3 — THE ELECTRONICS UNLOCK (over-rejection sweep OR-1..OR-4,
waveb_overRejection.json 2026-07-02).

Four truth rows (kpi-elec-002/003/004/005) were blocked by matcher
over-rejection despite verified in-stock genuine BHD PDPs — the electronics
lane ceiling was 2/6. Every trigger was token-bisected through the REAL
runtime (sweep_bisect_report) and each fix here is a BOUNDED fold/padding,
pinned in BOTH directions:

  1. SPACED-UNIT FOLD ("256 GB"=="256GB", "11 INCH"=="11-inch", "90 ml"=="90ml")
     at the tokenization layer shared by strict_title_match + normalize_words —
     the same layer as the Wave-A apostrophe fold, but GATED on
     ENABLE_EXACT_PRICE_GATE (the B1 candidate_brand-fold precedent) so the
     rollback surface is untouched. The fold must NOT weaken the numeric axis:
     a folded "512 GB" participates in the storage axis exactly like "512GB".
  2. ONE-SIDED MODEL-YEAR TOLERANCE (electronics+fashion): a TITLE-side bare
     2020-2029 year ("2025", "(2025)", "GEN 2025") is padding IFF the query
     carries NO year token; a query-stated year keeps the full numeric axis.
  3. BOUNDED MARKETING-TOKEN PADDING: electronics "AI" is TITLE-SIDE-ONLY
     padding (the 2025+ Samsung "AI Smartphone" class) — a query-side "AI"
     (a hypothetical product line named AI) stays a required identity token.
  4. INCH-AXIS EQUALITY: a title-side inch-annotation of a bare query digit
     ("13" vs "13-inch"/"13 Inch") is NOT an added axis when the digits are
     EQUAL; a DIFFERENT inch value still contradicts (13 vs 15-inch rejects).
  + core-count spec noise ("10-core CPU / 8-core GPU") off identity, onto a
    both-stated-different _core_count_mismatch axis; "cpu"/"ips" join the
    spec-noun padding ("gpu"/"ram"/"ssd" were already there); the glued Samsung
    colourway "Icyblue" joins the colour-alias set (OR-4's second trigger).

DOCUMENTED RESIDUAL (deliberately NOT fixed): the sharafdg elec-004 title
omits "Apple" while the truth query carries it, so the brandless
_catalog_match_hit strict hard gate still rejects at the ADAPTER level — the
row is unlocked via extra.com (unbxd) + the organic-PDP-harvest path (JSON-LD
stamps brand="Apple"); weakening strict's brand requirement would reopen the
L1/L2 wrong-brand class at every strict-only gate (the PR#13 bolo lesson).

Wave C C2 (re-sweep kpiE2E RS-1 HIGH + RS-4 LOW) — THE ELEC-005 SHARAFDG
UNLOCK on the RAW live title bytes. The BF3 T_SDG_MBA pin encoded a TRUNCATED
plain-hyphen title that does not exist at the retailer (false green); the live
title (probe2_out.json raw bytes, permalink-confirmed) carries a U+2011
non-breaking hyphen in "8‑core", the "&amp;" HTML entity, macOS/keyboard-
layout descriptor segments and the Sky Blue colourway — and was rejected
END-TO-END. Fixes pinned here:
  1. html-unescape at title INGESTION (_catalog_hit_fields / _hit_title /
     unbxd / magento shape nodes / extract_jsonld_price — "&amp;" was
     tokenizing as a false "amp" identity add);
  2. the core-count regexes cover the unicode hyphen family [- ‐ ‑ –];
  3. "keyboard" accessory-keyword exemption when the SAME surface carries a
     laptop-class device noun (is_accessory_for_category — mirrors the BF4
     pharmacy-'skin' scoping; broad is_accessory + the query-side flagship-
     floor exclusion stay unscoped);
  4. macOS-ANCHORED OS-version strip + laptop-scoped keyboard-LAYOUT strip
     ("English & Arabic Keyboard" is a layout attribute, not identity — a
     bare "arabic"/"tahoe" outside its anchor stays a discriminator) + "sky"
     joins the ELECTRONICS-only colour tokens (Apple "Sky Blue"; fashion
     keeps "Sky" distinctive).
"""
import html
import pytest

from app.services.price_service import (
    _core_count_mismatch,
    _selection_match,
    _storage_mismatch,
    extract_jsonld_price,
    is_accessory,
    is_accessory_for_category,
    is_high_value_query,
    should_cache_price,
    strict_title_match,
)
from app.services.algolia_service import (
    ALGOLIA_EXPLICIT_STORES,
    _catalog_hit_fields,
    _catalog_match_hit,
)
from app.services.magento_graphql_service import (
    _shape_a_price_node,
    _shape_b_price_node,
)
from app.services.unbxd_service import _match_unbxd_product
from scripts.eval_runner import (
    load_usable_exact_genuine_truth,
    usable_exact_genuine_for_product,
)


@pytest.fixture(autouse=True)
def _flags(monkeypatch):
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "true")
    monkeypatch.delenv("ENABLE_ADAPTER_SELECTION_PRIMARY", raising=False)
    monkeypatch.delenv("ENABLE_ADAPTER_QUERY_LADDER", raising=False)


def _sel(query, title, brand=""):
    return _selection_match(query, title, "electronics", candidate_brand=brand)


# The LIVE retailer titles (recon 2026-07-02) the sweep bisected — verbatim.
T_SDG_S25 = ("Samsung Galaxy S25 5G 256GB 12GB RAM Icyblue AI Smartphone "
             "Middle East Version")
T_SDG_S25U = ("Samsung Galaxy S25 Ultra 5G 256GB 12GB RAM Titanium Black AI "
              "Smartphone Middle East Version")
T_SDG_IPAD = ("iPad Air 11-inch M3 (2025) Wi-Fi 128GB - Space Grey Middle "
              "East Version with FaceTime")
# C2 (kpiE2E RS-1): the RAW live sharafdg title — VERBATIM bytes incl. the
# U+2011 non-breaking hyphen in "8‑core" and the un-decoded "&amp;" entity
# (WordPress post_title as served by the Algolia index; probe2_out.json).
T_SDG_MBA = ("Apple MacBook Air M5 13-inch (2026) - 10-core CPU / 16GB RAM / "
             "512GB SSD / 8‑core GPU / macOS Tahoe / English &amp; Arabic "
             "Keyboard / Sky Blue / Middle East Version")
# What _catalog_hit_fields emits (ingestion HTML-unescapes) — the bytes every
# downstream gate (selection / cache-write / KPI-usable) actually sees.
T_SDG_MBA_INGESTED = html.unescape(T_SDG_MBA)
T_EXTRA_S25U = "SAMSUNG Galaxy S25 Ultra, 5G, 256 GB, Titanium Black"
T_EXTRA_IPAD = "APPLE IPAD AIR M3 GEN 2025, Wi-Fi, 11 INCH, 128GB, Space Grey"
T_EXTRA_MBA = "APPLE MacBook Air, M5, 16GB, 512GB SSD, 13 Inch IPS, 8 Core GPU, Silver"

Q_S25 = "Samsung Galaxy S25 256GB"
Q_S25U = "Samsung Galaxy S25 Ultra 256GB"
Q_IPAD = "Apple iPad Air 11-inch M3 128GB"
Q_MBA = "MacBook Air 13 M5 512GB"


# ---------------------------------------------------------------------------
# 1. SPACED-UNIT FOLD — strict tokenization layer
# ---------------------------------------------------------------------------

class TestSpacedUnitFold:
    def test_strict_accepts_spaced_storage(self):
        # OR-1: query "256GB" was not a raw substring of the spaced "256 GB".
        assert strict_title_match(Q_S25U, T_EXTRA_S25U) is True

    def test_strict_accepts_spaced_inch(self):
        # OR-3 trigger (a): "11-inch" -> "11inch" vs the spaced "11 INCH".
        assert strict_title_match(Q_IPAD, T_EXTRA_IPAD) is True

    def test_strict_accepts_spaced_ml(self):
        # The perfumesclub live-row class the B4 demotion existed for — now
        # fixed at the tokenization layer itself.
        assert strict_title_match("YSL Black Opium Eau de Parfum 90ml",
                                  "YSL Black Opium (W) EDP 90 ml") is True

    def test_strict_accepts_spaced_watch_mm(self):
        assert strict_title_match("Apple Watch Series 10 45mm",
                                  "Apple Watch Series 10, 45 mm, Jet Black") is True

    def test_fold_vocabulary_is_bounded(self):
        # DELIBERATE exclusions: "w" (the Nike women's suffix "AF1 '07 W"),
        # "g"/"iu" (supplement/grocery units whose axes parse both spellings;
        # the legacy iHerb overlap matcher pins {"1000","iu"} as separate
        # tokens). The spaced forms must stay strict-invisible.
        assert strict_title_match("Kelloggs Corn Flakes 500g",
                                  "Kellogg's Corn Flakes 500 g") is False
        from app.services.price_service import _fold_spaced_units
        assert _fold_spaced_units("Vitamin D-3, 1000 IU") == "Vitamin D-3, 1000 IU"
        assert _fold_spaced_units("Nike Air Force 1 07 W") == "Nike Air Force 1 07 W"

    def test_fold_does_not_weaken_the_storage_axis(self):
        # ADVERSARIAL (both directions): a folded "512 GB" participates in the
        # numeric axes exactly like "512GB" — the wrong storage still rejects
        # at strict AND selection AND the explicit storage axis.
        wrong = "SAMSUNG Galaxy S25 Ultra, 5G, 512 GB, Titanium Black"
        assert strict_title_match(Q_S25U, wrong) is False
        assert _sel(Q_S25U, wrong) is False
        assert _storage_mismatch(Q_S25U, wrong) is True
        # reverse direction: spaced query vs glued wrong-storage title
        assert _sel("Samsung Galaxy S25 Ultra 512 GB",
                    "Samsung Galaxy S25 Ultra 5G 256GB 12GB RAM") is False

    def test_fold_gated_on_exact_price_gate(self, monkeypatch):
        # Rollback surface unchanged: gate OFF -> the raw pre-fold strict
        # tokenization (the spaced form fails again).
        monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "false")
        assert strict_title_match(Q_S25U, T_EXTRA_S25U) is False


# ---------------------------------------------------------------------------
# 2. ONE-SIDED MODEL-YEAR TOLERANCE
# ---------------------------------------------------------------------------

class TestModelYearTolerance:
    def test_sharafdg_ipad_paren_year_tolerated(self):
        # OR-3: "+'GEN' passes, +'2025' FAILS" — the year alone was the trigger.
        assert _sel(Q_IPAD, T_SDG_IPAD, brand="Apple") is True

    def test_extra_ipad_gen_year_tolerated(self):
        assert _sel(Q_IPAD, T_EXTRA_IPAD, brand="Apple") is True

    def test_query_year_keeps_the_numeric_axis(self):
        # BOTH-DIRECTIONS PIN (task-mandated): a query that STATES a year
        # rejects a different-year title...
        assert _sel("Apple iPhone SE 2022 128GB",
                    "Apple iPhone SE (2020) 128GB", brand="Apple") is False
        # ...matches the same-year title...
        assert _sel("Apple iPhone SE 2022 128GB",
                    "Apple iPhone SE (2022) 128GB", brand="Apple") is True
        # ...and stays fail-closed against a year-omitting title.
        assert _sel("Apple iPhone SE 2022 128GB",
                    "Apple iPhone SE 128GB", brand="Apple") is False

    def test_fashion_release_year_tolerated_one_sided_only(self):
        # UPDATED by Wave C (re-sweep RS1 + kpiE2E RS-3): the year tolerance
        # now additionally requires a query-side NON-YEAR generation
        # discriminator (M3/S25-class digit token) that the title matches —
        # for fashion the year IS the season/generation SKU (jersey 2024,
        # Air Max 2021, re-release years), so "Adidas Samba OG" (no
        # discriminator) no longer tolerates the "(2024)" annotation. The
        # REAL footlocker kpi-fash-002 title ("adidas Samba OG - Unisex
        # Shoes", test_footlocker_fashion_wiring) carries NO year — the KPI
        # row is unaffected; this synthetic variant pinned the exact leak
        # class the re-sweep confirmed (fail-closed direction accepted).
        assert _selection_match("Adidas Samba OG",
                                "adidas Samba OG (2024) - Unisex Shoes",
                                "fashion", candidate_brand="adidas") is False
        assert _selection_match("Air Jordan 4 Retro 2020",
                                "Air Jordan 4 Retro (2024)",
                                "fashion", candidate_brand="Nike") is False

    def test_year_range_is_bounded_2020s(self):
        # A 4-digit number OUTSIDE 2020-2029 is NOT year padding — it stays a
        # distinctive identity token (RTX 2080-class numbers must discriminate).
        assert _sel("Sony WH-1000XM5", "Sony WH-1000XM5 (2030)") is False

    def test_year_tolerance_never_bridges_a_chip_axis(self):
        # The M2 predecessor carries (2024): the year is tolerated but the
        # chip axis still rejects — the fold must not widen anything else.
        assert _sel(Q_IPAD,
                    "iPad Air 11-inch M2 (2024) Wi-Fi 128GB - Space Grey",
                    brand="Apple") is False


# ---------------------------------------------------------------------------
# 3. "AI" MARKETING TOKEN — title-side-only padding
# ---------------------------------------------------------------------------

class TestAiMarketingToken:
    def test_s25_ai_smartphone_title_tolerated(self):
        # OR-4 (kpi-elec-002): 'Icyblue' + 'AI' were the two bisected triggers.
        assert _sel(Q_S25, T_SDG_S25) is True

    def test_s25_ultra_ai_smartphone_title_tolerated(self):
        # OR-1 (kpi-elec-003): '+AI' alone flipped the bisect.
        assert _sel(Q_S25U, T_SDG_S25U) is True

    def test_ai_is_title_side_only_never_query_side_dropped(self):
        # ADVERSARIAL PIN (task-mandated): a hypothetical product line named
        # "AI" still requires its own token — the padding tolerates a TITLE
        # add, it never releases a QUERY requirement.
        assert _sel("Nothing AI Phone", "Nothing Phone 3") is False
        assert _sel("Nothing AI Phone", "Nothing AI Phone") is True

    def test_glued_samsung_colourway_icyblue_tolerated(self):
        # 'Icyblue' joins the colour-alias set like phantom/awesome/cosmic —
        # colour is cosmetic for electronics, and it never bridges a real axis:
        assert _sel(Q_S25, "Samsung Galaxy S25 5G 512GB Icyblue AI Smartphone") is False


# ---------------------------------------------------------------------------
# 4. INCH-AXIS — bare query digit vs inch-annotated title
# ---------------------------------------------------------------------------

class TestInchAxis:
    def test_bare_13_query_matches_13_inch_titles(self):
        # OR-2: BOTH wired sources for kpi-elec-005 carried the class.
        # (Matcher-level pins run on the INGESTED bytes — the raw "&amp;" is
        # decoded at _catalog_hit_fields, see TestSharafdgLiveTitleUnlockC2.)
        assert _sel(Q_MBA, T_SDG_MBA_INGESTED, brand="Apple") is True
        assert _sel(Q_MBA, T_EXTRA_MBA, brand="Apple") is True

    def test_bare_13_query_rejects_a_different_inch(self):
        # ADVERSARIAL PIN (task-mandated): 13 vs 15-inch contradicts.
        assert _sel(Q_MBA, "Apple MacBook Air M5 15-inch 512GB SSD",
                    brand="Apple") is False

    def test_inch_query_matches_bare_digit_title(self):
        # Mirror direction: the query annotates, the title is bare — same SKU.
        assert _sel(Q_IPAD, "iPad Air 11 M3 Wi-Fi 128GB Space Grey",
                    brand="Apple") is True

    def test_inch_query_rejects_a_different_bare_digit(self):
        assert _sel(Q_IPAD, "iPad Air 13 M3 Wi-Fi 128GB Space Grey",
                    brand="Apple") is False


# ---------------------------------------------------------------------------
# core-count / spec-noun bounds
# ---------------------------------------------------------------------------

class TestCoreCountSpecNoise:
    def test_one_sided_core_counts_are_spec_noise(self):
        # covered end-to-end by the MBA titles above; pin the helper contract:
        assert _core_count_mismatch("MacBook Air 13 M5 512GB",
                                    "10-core CPU / 8-core GPU") is False

    def test_both_stated_different_core_counts_contradict(self):
        assert _core_count_mismatch("MacBook Pro 14 M4 12-core 1TB",
                                    "MacBook Pro 14-inch M4 10-core CPU 1TB") is True
        assert _sel("MacBook Pro 14 M4 12-core 1TB",
                    "Apple MacBook Pro 14-inch M4 10-core CPU 1TB SSD",
                    brand="Apple") is False

    def test_shared_core_count_is_not_a_contradiction(self):
        assert _core_count_mismatch("MacBook Air M5 10-core",
                                    "10-core CPU / 8-core GPU") is False


# ---------------------------------------------------------------------------
# 5. END-TO-END — adapter accept + cache write + KPI-usable vs the REAL truth
# ---------------------------------------------------------------------------

_TRUTH = {p["id"]: p for p in load_usable_exact_genuine_truth()}
_SDG_STORE = ALGOLIA_EXPLICIT_STORES["bahrain.sharafdg.com"]


def _sdg_hit(title, price, in_stock=1):
    return {"post_title": title, "price": price, "in_stock": in_stock,
            "permalink": "https://bahrain.sharafdg.com/product/x/"}


def _ux(title, price):
    return {"title": title, "sellingPrice": price, "inStockFlag": "true",
            "productUrl": "https://www.extra.com/en-bh/x/p/100"}


def _price(title, amount, url):
    return {"amount": amount, "currency": "BHD", "retailer": "x", "url": url,
            "in_stock": True, "estimated": False, "source_method": "local_bhd",
            "title": title, "confidence": 0.9}


def _usable(query, price, truth_id):
    body = {"overview": {"products": [{"price": price}]}}
    return usable_exact_genuine_for_product(body, 0, _TRUTH[truth_id])


class TestEndToEndUnlock:
    @pytest.mark.parametrize("tid,query,title,amount", [
        ("kpi-elec-002", Q_S25, T_SDG_S25, 359.99),
        ("kpi-elec-003", Q_S25U, T_SDG_S25U, 354.9),
        ("kpi-elec-005", Q_MBA, T_SDG_MBA, 499.899),
    ])
    def test_sharafdg_adapter_accepts(self, tid, query, title, amount):
        hit = _catalog_match_hit([_sdg_hit(title, amount)], query, _SDG_STORE,
                                 resolved_category="electronics")
        assert hit is not None, tid
        assert hit["post_title"] == title

    def test_sharafdg_ipad_adapter_documented_residual(self):
        """The sharafdg elec-004 title omits 'Apple' while the truth query
        carries it — the brandless _catalog_match_hit strict hard gate still
        rejects (NOT the year token any more). Deliberately NOT fixed:
        weakening strict's brand requirement reopens the L1/L2 wrong-brand
        class at every strict-only gate (PR#13 bolo lesson). The row is
        unlocked via extra.com below + the organic-PDP-harvest path (JSON-LD
        stamps brand='Apple', and the brand-aware cache/usable gates PASS —
        see the e2e pins)."""
        hit = _catalog_match_hit([_sdg_hit(T_SDG_IPAD, 240.99)], Q_IPAD,
                                 _SDG_STORE, resolved_category="electronics")
        assert hit is None

    @pytest.mark.parametrize("tid,query,title,amount", [
        ("kpi-elec-003", Q_S25U, T_EXTRA_S25U, 358.0),
        ("kpi-elec-004", Q_IPAD, T_EXTRA_IPAD, 229.99),
        ("kpi-elec-005", Q_MBA, T_EXTRA_MBA, 609.99),
    ])
    def test_unbxd_adapter_accepts(self, tid, query, title, amount):
        got = _match_unbxd_product([_ux(title, amount)], query,
                                   resolved_category="electronics")
        assert got is not None, tid
        assert got["title"] == title

    @pytest.mark.parametrize("title", [
        # variant flanker — the base sibling must not take the Ultra's query
        "SAMSUNG Galaxy S25 Plus, 5G, 256 GB, Navy",
        # wrong storage through the spaced fold
        "SAMSUNG Galaxy S25 Ultra, 5G, 512 GB, Titanium Black",
        # accessory
        "SAMSUNG Galaxy S25 Ultra Clear Case",
    ])
    def test_unbxd_wrong_skus_still_reject(self, title):
        got = _match_unbxd_product([_ux(title, 199.9)], Q_S25U,
                                   resolved_category="electronics")
        assert got is None

    @pytest.mark.parametrize("tid,query,title,url", [
        ("kpi-elec-002", Q_S25, T_SDG_S25,
         "https://bahrain.sharafdg.com/product/samsung-galaxy-s25/"),
        ("kpi-elec-003", Q_S25U, T_SDG_S25U,
         "https://bahrain.sharafdg.com/product/samsung-galaxy-s25-ultra/"),
        ("kpi-elec-004", Q_IPAD, T_SDG_IPAD,
         "https://bahrain.sharafdg.com/product/11-inch-ipad-air-m3-2025/"),
        ("kpi-elec-004", Q_IPAD, T_EXTRA_IPAD,
         "https://www.extra.com/en-bh/x/p/100"),
        ("kpi-elec-005", Q_MBA, T_SDG_MBA_INGESTED,
         "https://bahrain.sharafdg.com/product/apple-macbook-air-m5/"),
        ("kpi-elec-005", Q_MBA, T_EXTRA_MBA,
         "https://www.extra.com/en-bh/x/p/100"),
    ])
    def test_cache_write_and_kpi_usable(self, tid, query, title, url):
        price = _price(title, 100.0, url)
        assert should_cache_price(query, price, "electronics") is True, tid
        assert _usable(query, price, tid) is True, tid

    def test_wrong_sku_never_caches_or_counts(self):
        # the fold battery must not have opened the cache/KPI to a wrong SKU
        price = _price("SAMSUNG Galaxy S25 Ultra, 5G, 512 GB, Titanium Black",
                       100.0, "https://www.extra.com/en-bh/x/p/100")
        assert should_cache_price(Q_S25U, price, "electronics") is False
        assert _usable(Q_S25U, price, "kpi-elec-003") is False


# ---------------------------------------------------------------------------
# 6. Wave C C2 — THE ELEC-005 SHARAFDG UNLOCK on the RAW live title
#    (kpiE2E RS-1 HIGH + RS-4 LOW)
# ---------------------------------------------------------------------------

class TestSharafdgLiveTitleUnlockC2:
    """The RAW live sharafdg MacBook title through the FULL chain: ingestion
    (entity decode) -> accessory gate -> matcher -> adapter -> cache -> KPI."""

    def test_catalog_hit_fields_unescape_the_html_entity(self):
        # RS-1 trigger (ingestion): "&amp;" tokenized as a false "amp"
        # identity add — decode at the hit surface, where the stored title
        # is born.
        fields = _catalog_hit_fields(_sdg_hit(T_SDG_MBA, 499.899), _SDG_STORE)
        assert "&amp;" not in fields["title"]
        assert "English & Arabic Keyboard" in fields["title"]

    def test_laptop_layout_keyboard_is_not_an_accessory(self):
        # RS-4: GCC laptop listings state the keyboard LAYOUT mid-title — a
        # bare "keyboard" hit with a laptop-class device noun on the SAME
        # surface is a layout attribute, not an accessory.
        assert is_accessory_for_category(T_SDG_MBA_INGESTED, "electronics") is False
        assert is_accessory_for_category(
            "Apple MacBook Pro M4 16GB 512GB Arabic Keyboard", "electronics") is False
        assert is_accessory_for_category(
            "Lenovo IdeaPad 5 Laptop English-Arabic Keyboard 512GB",
            "electronics") is False

    def test_real_keyboard_and_keyboard_accessory_still_reject(self):
        # BOTH-DIRECTIONS bound (task-mandated): a real keyboard product
        # (head noun, no device context) still classifies accessory, and any
        # OTHER accessory keyword still flags even in laptop context.
        assert is_accessory_for_category("Logitech MX Keys Keyboard",
                                         "electronics") is True
        assert is_accessory_for_category("Keyboard Case for MacBook Air 13",
                                         "electronics") is True

    def test_broad_is_accessory_and_flagship_floor_unchanged(self):
        # The noisy Serper-shopping/zyte/rating nets keep the UNSCOPED keyword
        # hit, and the QUERY-side flagship-floor exclusion is untouched: a
        # laptop-keyboard accessory QUERY must stay excluded from the floor so
        # its genuine cheap price is never floored away.
        assert is_accessory(T_SDG_MBA_INGESTED) is True
        assert is_high_value_query("Keyboard for MacBook Air") is False

    def test_core_count_strip_covers_the_unicode_hyphen_family(self):
        # RS-1 trigger (identity): U+2011 defeated the ASCII-hyphen-only
        # _CORE_COUNT_RE — "8‑core" survived as a digit-bearing identity add.
        for hyphen in ("-", "‐", "‑", "–"):
            title = ("Apple MacBook Air M5 13-inch (2026) 512GB SSD "
                     f"8{hyphen}core GPU")
            assert _sel(Q_MBA, title, brand="Apple") is True, repr(hyphen)

    def test_labeled_gpu_bin_discriminates_through_the_unicode_hyphen(self):
        # C1's RS4 label-aware core-count axis must parse the U+2011 spelling
        # too — the 8-GPU bin under a 10-GPU query stays a contradiction.
        q10 = "MacBook Air M5 13 10-core CPU 10-core GPU 512GB"
        t8 = ("Apple MacBook Air M5 13-inch 10‑core CPU / "
              "8‑core GPU / 512GB SSD")
        assert _core_count_mismatch(q10, t8) is True
        assert _sel(q10, t8, brand="Apple") is False

    def test_selection_accepts_the_ingested_live_title(self):
        # Brandless FIRST — the live sharafdg hit carries NO brand key, so
        # the adapter threads candidate_brand="" ("Apple" rides padding).
        assert _sel(Q_MBA, T_SDG_MBA_INGESTED) is True
        assert _sel(Q_MBA, T_SDG_MBA_INGESTED, brand="Apple") is True

    def test_selection_accepts_the_single_layout_live_variant(self):
        # The live "English Keyboard" (no Arabic) sibling row — same SKU shape.
        t = ("Apple MacBook Air M5 13-inch (2026) - 10-core CPU / 16GB RAM / "
             "512GB SSD / 8‑core GPU / macOS Tahoe / English Keyboard / "
             "Sky Blue / Middle East Version")
        assert _sel(Q_MBA, t) is True

    def test_macos_version_strip_is_anchored_to_macos(self):
        # "macOS <version>" is the shipping OS, never a SKU discriminator...
        assert _sel(Q_MBA,
                    "Apple MacBook Air M5 13-inch (2026) 512GB SSD macOS Sequoia",
                    brand="Apple") is True
        # ...but a bare version word WITHOUT its "macos" anchor stays a
        # distinctive identity token (bound: never pad a floating word).
        assert _sel(Q_MBA, "Apple MacBook Air M5 13-inch 512GB SSD Tahoe",
                    brand="Apple") is False

    def test_keyboard_layout_strip_is_laptop_scoped(self):
        # A KEYBOARD product's layout still discriminates — no laptop-class
        # noun on the surface, so "Arabic" stays a variant add.
        assert _selection_match("Logitech K120 Keyboard",
                                "Logitech K120 Arabic Keyboard",
                                "electronics", candidate_brand="Logitech") is False

    def test_bare_arabic_outside_the_keyboard_context_stays_identity(self):
        # An Arabic-EDITION product is a DIFFERENT sellable unit — the strip
        # is anchored to the "<layout> keyboard" phrase, never a bare token.
        assert _sel("Amazon Kindle Paperwhite 16GB",
                    "Amazon Kindle Paperwhite 16GB Arabic Edition") is False

    def test_sky_colourway_is_electronics_scoped(self):
        # "sky" joins _ELECTRONICS_ONLY_COLOR_TOKENS (Apple "Sky Blue") — for
        # FASHION a bare "Sky" stays distinctive (Sky Jordan-class lines).
        assert _selection_match("Nike Air Force 1 07",
                                "Nike Air Force 1 07 Sky",
                                "fashion", candidate_brand="Nike") is False

    def test_accessory_exemption_never_admits_a_keyboard_accessory(self):
        # LEAK-direction bound: a laptop-KEYBOARD accessory listing is now
        # EXEMPT at the accessory gate (it carries the laptop noun) — the
        # identity gates must still reject it end-to-end, and the flagship
        # floor pends its accessory price.
        from app.services.price_service import is_price_showable
        acc = "Backlit Replacement Keyboard for MacBook Air 13 M5 512GB Models"
        assert _catalog_match_hit([_sdg_hit(acc, 12.9)], Q_MBA, _SDG_STORE,
                                  resolved_category="electronics") is None
        assert _match_unbxd_product([_ux(acc, 12.9)], Q_MBA,
                                    resolved_category="electronics") is None
        assert _selection_match(Q_MBA, acc, "electronics") is False
        assert is_price_showable(Q_MBA, _price(
            acc, 12.9, "https://bahrain.sharafdg.com/product/kb/")) is False

    def test_layout_stated_laptop_query_trade_documented(self):
        # ACCEPTED TRADE (documented, not a leak class): a laptop query that
        # itself STATES a layout ("... Arabic Keyboard") strips it like the
        # title side, so an other-layout unit of the SAME laptop accepts —
        # GCC layout is a region-standard attribute (the live sharafdg
        # English vs English&Arabic rows price IDENTICALLY at 499.899);
        # keeping layout as an axis would need a new both-stated axis, out of
        # the C2 bound. A future tighten must flip THIS pin consciously.
        t_en = ("Apple MacBook Air M5 13-inch (2026) - 10-core CPU / "
                "16GB RAM / 512GB SSD / 8‑core GPU / macOS Tahoe / "
                "English Keyboard / Sky Blue / Middle East Version")
        assert _sel(Q_MBA + " Arabic Keyboard", t_en) is True

    def test_wrong_skus_still_reject_on_the_live_title_shape(self):
        # Storage flanker through the FULL live shape (fixes must not have
        # widened any numeric axis).
        wrong = T_SDG_MBA.replace("512GB SSD", "256GB SSD")
        assert _catalog_match_hit([_sdg_hit(wrong, 399.9)], Q_MBA, _SDG_STORE,
                                  resolved_category="electronics") is None
        # The REAL 15-inch sibling rows — the bare "13" query contradicts.
        wrong15 = T_SDG_MBA.replace("13-inch", "15-inch")
        assert _catalog_match_hit([_sdg_hit(wrong15, 579.9)], Q_MBA, _SDG_STORE,
                                  resolved_category="electronics") is None


# ---------------------------------------------------------------------------
# 7. Wave C C2 — the "&amp;" ingestion audit at the OTHER hit/title surfaces
#    (unbxd / magento shape nodes / JSON-LD extract; woo already decodes)
# ---------------------------------------------------------------------------

class TestEntityUnescapeIngestionAuditC2:
    def test_unbxd_match_surface_unescapes(self):
        # extra.com lists Arabic-keyboard variants — the raw feed can carry
        # the entity; the match surface must see the decoded "&".
        t = ("APPLE MacBook Air, M5, 16GB, 512GB SSD, 13 Inch IPS, 8 Core GPU, "
             "English &amp; Arabic Keyboard, Silver")
        got = _match_unbxd_product([_ux(t, 609.99)], Q_MBA,
                                   resolved_category="electronics")
        assert got is not None

    def test_magento_shape_nodes_unescape(self):
        a = _shape_a_price_node({
            "__typename": "SimpleProductView",
            "name": "Polo Shirt Black &amp; White",
            "urlKey": "polo",
            "inStock": True,
            "price": {"final": {"amount": {"value": 10.0, "currency": "BHD"}}},
        })
        assert a is not None and a["name"] == "Polo Shirt Black & White"
        b = _shape_b_price_node({
            "name": "Polo Shirt Black &amp; White",
            "url_key": "polo",
            "stock_status": "IN_STOCK",
            "price_range": {"minimum_price": {
                "final_price": {"value": 10.0, "currency": "BHD"}}},
        })
        assert b is not None and b["name"] == "Polo Shirt Black & White"

    def test_jsonld_name_unescapes_and_matches(self):
        # html.parser does NOT entity-decode <script> contents, so a JSON-LD
        # blob's "&amp;" reaches the identity gates verbatim (the same false
        # "amp" add class) — decode at ingestion, gate ON.
        page = (
            '<html><head><script type="application/ld+json">'
            '{"@type": "Product", "name": "Apple MacBook Air M5 13-inch (2026) '
            '512GB SSD 8‑core GPU macOS Tahoe English &amp; Arabic Keyboard", '
            '"brand": "Apple", "offers": {"@type": "Offer", "price": "499.9", '
            '"priceCurrency": "BHD", "availability": "https://schema.org/InStock"}}'
            "</script></head><body></body></html>"
        )
        r = extract_jsonld_price(page, "Apple", "BHD", query_name=Q_MBA,
                                 category="electronics")
        assert r is not None and abs(r["amount"] - 499.9) < 0.01
        assert "&amp;" not in (r.get("name") or "")
