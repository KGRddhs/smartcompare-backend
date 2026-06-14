"""L2.2 — Tests for `source_router.py` (Bahrain-first hierarchy).

Source weight tiers (per design):
- bahrain x3.0: Lulu BH, Carrefour BH, Sharaf DG BH, eXtra BH, Geant BH,
  bn.boots.com, bolo.bh, Behbehani, Eros, Jumbo, Talabat, Spinneys, Megamart
- gcc x1.5: noon.com, amazon.ae, Ounass, Bloomingdales ME, Tryano
- global x1.0: brand-officials + last-resort marketplaces
"""

import pytest

from app.services.source_router import Source, get_sources_for_category, score_source


# ---------- score_source tier hierarchy ----------

def test_bahrain_sources_score_higher_than_gcc_and_global():
    bh_score = score_source("https://gcc.luluhypermarket.com/en-bh/product/123", category="electronics")
    gcc_score = score_source("https://www.noon.com/uae-en/product/456", category="electronics")
    global_score = score_source("https://www.amazon.com/dp/B0XXX", category="electronics")
    assert bh_score > gcc_score > global_score
    assert bh_score >= 3.0
    assert gcc_score >= 1.5
    assert global_score >= 1.0


def test_score_source_unknown_domain_returns_low_default():
    score = score_source("https://random-blog.example/product/x", category="electronics")
    assert score == 0.5


def test_score_source_handles_subdomain():
    """nutrition.iherb.com → still iherb.com → matches."""
    score = score_source("https://nutrition.iherb.com/pr/abc", category="supplements")
    # iherb.com is global category=supplements → weight 1.0
    assert score == 1.0


def test_score_source_category_filtering():
    """bahrain.sharafdg.com is registered for electronics only.

    Asking for a supplements URL against sharafdg should fall through to the
    unknown-source default 0.5 (not 3.0).
    """
    score_electronics = score_source(
        "https://www.bahrain.sharafdg.com/product/p1", category="electronics"
    )
    score_supplements = score_source(
        "https://www.bahrain.sharafdg.com/product/p1", category="supplements"
    )
    assert score_electronics == 3.0
    assert score_supplements == 0.5


def test_score_source_bn_boots_supplements():
    score = score_source(
        "https://bn.boots.com/wellness/vitamin-d-tablets", category="supplements"
    )
    assert score == 3.0


def test_score_source_lulu_works_across_all_categories():
    """Lulu has empty `categories` tuple → matches every category.

    Retargeted to gcc.luluhypermarket.com (the BHD/en-bh storefront) — the bare
    host (en-ae/AED) was retired by the S3-genuine keystone fix.
    """
    for cat in ("electronics", "supplements", "grocery", "fashion"):
        assert score_source("https://gcc.luluhypermarket.com/en-bh/x", category=cat) == 3.0


# ---------- get_sources_for_category ----------

def test_get_sources_for_category_supplements_includes_iherb_and_boots_bh():
    sources = get_sources_for_category("supplements")
    domains = [s.domain for s in sources]
    assert "iherb.com" in domains
    assert "bn.boots.com" in domains
    # Bahrain-tier appears before global tier
    bh_indices = [i for i, s in enumerate(sources) if s.tier == "bahrain"]
    global_indices = [i for i, s in enumerate(sources) if s.tier == "global"]
    assert len(bh_indices) >= 1
    assert len(global_indices) >= 1
    assert max(bh_indices) < min(global_indices)


def test_get_sources_for_category_electronics_orders_bahrain_first():
    sources = get_sources_for_category("electronics")
    tiers = [s.tier for s in sources]
    # First entry must be bahrain
    assert tiers[0] == "bahrain"
    # No bahrain after a gcc entry has started
    first_gcc = tiers.index("gcc") if "gcc" in tiers else len(tiers)
    assert all(t == "bahrain" for t in tiers[:first_gcc])


def test_get_sources_for_category_electronics_includes_sharaf_dg_bh_and_extra_bh():
    sources = get_sources_for_category("electronics")
    domains = [s.domain for s in sources]
    assert "bahrain.sharafdg.com" in domains
    assert "extra.com" in domains


def test_get_sources_for_category_grocery_includes_talabat():
    sources = get_sources_for_category("grocery")
    domains = [s.domain for s in sources]
    assert "talabat.com" in domains
    # spinneysbahrain.com deleted by I5.11 liveness gate (NXDOMAIN, Decision F)
    assert "spinneysbahrain.com" not in domains
    assert "megamart.bh" in domains


def test_get_sources_for_category_filters_out_irrelevant():
    """Apple/Samsung are electronics-only globals → excluded for grocery."""
    sources = get_sources_for_category("grocery")
    domains = [s.domain for s in sources]
    assert "apple.com" not in domains
    assert "samsung.com" not in domains


def test_get_sources_for_category_returns_only_source_dataclass():
    sources = get_sources_for_category("electronics")
    assert len(sources) > 0
    for s in sources:
        assert isinstance(s, Source)
        assert s.tier in ("bahrain", "gcc", "global")
        assert s.weight in (1.0, 1.5, 3.0)


def test_score_source_handles_www_prefix():
    """A www-prefixed and bare host of a registered bahrain domain both score
    3.0 (www-stripping invariant). Uses gcc.luluhypermarket.com — the bare
    luluhypermarket.com was retired by the S3-genuine keystone retarget."""
    with_www = score_source("https://www.gcc.luluhypermarket.com/en-bh/x", category="electronics")
    without_www = score_source("https://gcc.luluhypermarket.com/en-bh/x", category="electronics")
    assert with_www == 3.0
    assert without_www == 3.0


# ---------- F1.5 — registry expansion (Bahrain retailer gaps) ----------
# Domains verified live 2026-06-10 (real Bahrain e-commerce sites):
#   alosraonline.com  — Alosra supermarket (BMMI), grocery e-commerce
#   nasserpharmacy.com — Nasser Pharmacy, Bahrain's largest pharmacy chain
#                        (10k+ products: supplements/skincare/makeup/haircare/fragrances)
#   bahrainpharmacy.com — Bahrain Pharmacy & General Store
# RATIFICATION REQUIRED before merge (F1.5 checkpoint).

def test_alosra_grocery_bahrain_tier():
    """alosraonline.com is a Bahrain grocery retailer (weight 3.0)."""
    assert score_source("https://www.alosraonline.com/milk", category="grocery") == 3.0


def test_alosra_excluded_from_electronics():
    """Grocery-only Bahrain retailer must not score for electronics."""
    assert score_source("https://www.alosraonline.com/x", category="electronics") == 0.5


def test_nasser_pharmacy_supplements_and_beauty():
    """nasserpharmacy.com covers supplements + skincare/makeup/haircare/fragrances."""
    for cat in ("supplements", "skincare", "makeup", "haircare", "fragrances"):
        assert score_source(
            "https://www.nasserpharmacy.com/p/vitamin-d", category=cat
        ) == 3.0


def test_bahrain_pharmacy_supplements():
    assert score_source(
        "https://bahrainpharmacy.com/wellness/omega-3", category="supplements"
    ) == 3.0


def test_grocery_sources_now_include_alosra():
    sources = get_sources_for_category("grocery")
    domains = [s.domain for s in sources]
    assert "alosraonline.com" in domains
    # Pre-existing grocery sources still present (no regression).
    assert "talabat.com" in domains
    # spinneysbahrain.com deleted by I5.11 liveness gate (NXDOMAIN, Decision F)
    assert "spinneysbahrain.com" not in domains


def test_supplements_sources_now_include_pharmacies():
    sources = get_sources_for_category("supplements")
    domains = [s.domain for s in sources]
    assert "nasserpharmacy.com" in domains
    assert "bahrainpharmacy.com" in domains
    # Pre-existing supplements sources still present.
    assert "bn.boots.com" in domains
    assert "iherb.com" in domains


def test_new_bahrain_retailers_ordered_first():
    """New Bahrain retailers must keep the bahrain-first tier invariant."""
    sources = get_sources_for_category("supplements")
    tiers = [s.tier for s in sources]
    first_gcc = tiers.index("gcc") if "gcc" in tiers else len(tiers)
    first_global = tiers.index("global") if "global" in tiers else len(tiers)
    first_non_bahrain = min(first_gcc, first_global)
    # nasserpharmacy / bahrainpharmacy are bahrain-tier → before any gcc/global.
    for d in ("nasserpharmacy.com", "bahrainpharmacy.com"):
        idx = next(i for i, s in enumerate(sources) if s.domain == d)
        assert idx < first_non_bahrain


# ---------- F1.5 addendum — deeper verified Bahrain source discovery ----------
# All verified LIVE 2026-06-10 (real BH e-commerce, BHD prices, cart/checkout,
# product pages spot-checked). Ahmed pre-authorized verified additions.
#   shopalmoayyed.com — Y.K. Almoayyed & Sons (Shopify), electronics/appliances/AC
#                       (fills the 0%-hit AC/appliance class)
#   bh.asgharali.com  — Asgharali Perfumes BH (Shopify), fragrances
#   jalilaperfumes.com — Jalila Perfumes BH (custom PHP, product pages + BHD), fragrances
#   bateel.bh         — Bateel BH, premium dates (grocery)
# REJECTED: goldenbahrain.com — price-listing PORTAL not e-commerce, disclaims
#           price accuracy (would feed unreliable data into the scrape pool).

def test_shopalmoayyed_electronics_bahrain():
    assert score_source(
        "https://www.shopalmoayyed.com/products/admiral-refrigerator-450l",
        category="electronics",
    ) == 3.0


def test_shopalmoayyed_excluded_from_fragrances():
    assert score_source(
        "https://www.shopalmoayyed.com/products/x", category="fragrances"
    ) == 0.5


def test_asgharali_fragrances_bahrain_subdomain():
    """bh.asgharali.com is registered as the BH subdomain (the brand's global
    asgharali.com is a different surface)."""
    assert score_source(
        "https://bh.asgharali.com/products/bakhoor-estabraq", category="fragrances"
    ) == 3.0


def test_jalila_perfumes_fragrances_bahrain():
    assert score_source(
        "https://www.jalilaperfumes.com/product-details.php?id=2234",
        category="fragrances",
    ) == 3.0


def test_bateel_grocery_bahrain():
    assert score_source(
        "https://bateel.bh/products/sokari-dates-450g", category="grocery"
    ) == 3.0


def test_fragrances_now_have_bahrain_tier_sources():
    """Fragrance tier was thin (no bahrain-tier source). Addendum adds two."""
    sources = get_sources_for_category("fragrances")
    domains = [s.domain for s in sources]
    bh_frag = [s for s in sources if s.tier == "bahrain"]
    assert len(bh_frag) >= 2
    assert "bh.asgharali.com" in domains
    assert "jalilaperfumes.com" in domains


def test_goldenbahrain_not_added():
    """REJECTED candidate — must NOT be in the registry (price portal, not a
    checkout retailer; disclaims price accuracy)."""
    assert score_source("https://www.goldenbahrain.com/price-lists/x", category="electronics") == 0.5


def test_addendum_retailers_keep_tier_first_ordering():
    for cat, domain in (
        ("electronics", "shopalmoayyed.com"),
        ("fragrances", "bh.asgharali.com"),
        ("grocery", "bateel.bh"),
    ):
        sources = get_sources_for_category(cat)
        tiers = [s.tier for s in sources]
        first_gcc = tiers.index("gcc") if "gcc" in tiers else len(tiers)
        first_global = tiers.index("global") if "global" in tiers else len(tiers)
        first_non_bahrain = min(first_gcc, first_global)
        idx = next(i for i, s in enumerate(sources) if s.domain == domain)
        assert idx < first_non_bahrain
