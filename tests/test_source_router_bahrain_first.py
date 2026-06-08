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
    bh_score = score_source("https://www.lulu.com.bh/product/123", category="electronics")
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
    """sharafdg.com.bh is registered for electronics only.

    Asking for a supplements URL against sharafdg should fall through to the
    unknown-source default 0.5 (not 3.0).
    """
    score_electronics = score_source(
        "https://www.sharafdg.com.bh/product/p1", category="electronics"
    )
    score_supplements = score_source(
        "https://www.sharafdg.com.bh/product/p1", category="supplements"
    )
    assert score_electronics == 3.0
    assert score_supplements == 0.5


def test_score_source_bn_boots_supplements():
    score = score_source(
        "https://bn.boots.com/wellness/vitamin-d-tablets", category="supplements"
    )
    assert score == 3.0


def test_score_source_lulu_works_across_all_categories():
    """Lulu has empty `categories` tuple → matches every category."""
    for cat in ("electronics", "supplements", "grocery", "fashion"):
        assert score_source("https://www.lulu.com.bh/x", category=cat) == 3.0


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
    assert "sharafdg.com.bh" in domains
    assert "extra.com.bh" in domains


def test_get_sources_for_category_grocery_includes_talabat_and_spinneys():
    sources = get_sources_for_category("grocery")
    domains = [s.domain for s in sources]
    assert "talabat.com" in domains
    assert "spinneysbahrain.com" in domains
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
    """www.lulu.com.bh and lulu.com.bh should both score 3.0."""
    with_www = score_source("https://www.lulu.com.bh/x", category="electronics")
    without_www = score_source("https://lulu.com.bh/x", category="electronics")
    assert with_www == 3.0
    assert without_www == 3.0
