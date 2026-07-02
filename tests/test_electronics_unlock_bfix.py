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
"""
import pytest

from app.services.price_service import (
    _core_count_mismatch,
    _selection_match,
    _storage_mismatch,
    should_cache_price,
    strict_title_match,
)
from app.services.algolia_service import ALGOLIA_EXPLICIT_STORES, _catalog_match_hit
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
T_SDG_MBA = ("Apple MacBook Air M5 13-inch (2026) - 10-core CPU / 16GB RAM / "
             "512GB SSD / 8-core GPU - Midnight")
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
        assert _selection_match("Adidas Samba OG",
                                "adidas Samba OG (2024) - Unisex Shoes",
                                "fashion", candidate_brand="adidas") is True
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
        assert _sel(Q_MBA, T_SDG_MBA, brand="Apple") is True
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
        ("kpi-elec-005", Q_MBA, T_SDG_MBA,
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
