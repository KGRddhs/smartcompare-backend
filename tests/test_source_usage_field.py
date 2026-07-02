"""S2 I2.5 — Source.usage field + Arabic review-source registration.

Invariants:
  - Every existing registry row defaults to usage="price" → zero behaviour
    change in price discovery / harvest.
  - The 3 new Arabic sources (sayidaty.net, khaleejtimes.com, gulfnews.com)
    are usage="review", gcc tier/weight, review categories.
  - get_sources_for_category(usage=...) and build_site_discovery_query filter
    review-only sources OUT of price discovery.
  - score_source is unchanged (still weight-by-domain — usage is orthogonal).
"""

from app.services import source_router as sr
from app.services.source_router import (
    SOURCE_REGISTRY,
    Source,
    build_site_discovery_query,
    get_sources_for_category,
    score_source,
    source_usage,
)

ARABIC_REVIEW_DOMAINS = {"sayidaty.net", "khaleejtimes.com", "gulfnews.com"}
REVIEW_CATEGORIES = {"fashion", "makeup", "skincare", "haircare", "fragrances"}


# ---------------------------------------------------------------------------
# Dataclass + registry defaults
# ---------------------------------------------------------------------------

def test_source_has_usage_field_default_price():
    s = Source("example.com", "gcc", (), 1.5)
    assert s.usage == "price"


def test_all_legacy_rows_are_price_usage():
    """Every row EXCEPT the 3 new Arabic review sources must be usage='price'
    (zero behaviour change pin)."""
    for s in SOURCE_REGISTRY:
        if s.domain in ARABIC_REVIEW_DOMAINS:
            continue
        assert s.usage == "price", f"{s.domain} should default to price usage"


def test_registry_price_source_count():
    """Price-usable rows are intact; Arabic review sources are additive.

    Count is 35: I5.3/I5.11 purges took 37→33; S3 L1.2 added bahrain.ounass.com
    (33→34); S3-reopen T4 added 2 verified BH Shopify fragrance stores
    en-bh.ajmal.com + alhajisbahrain.com (34→36); S3-reopen gap-fill (Decision-F)
    DELETED 2 dead electronics rows behbehani.com + jumboelectronics.com
    (200-but-not-a-store — starving the limit=8 discovery) and RETARGETED the
    bare luluhypermarket.com → gcc.luluhypermarket.com (net-zero), 36→34;
    S3-reopen PDP-curl Decision-F ADDED bahrain.microless.com (curl-scrapeable
    MacBook PDP → 439.062 BHD JSON-LD), 34→35. S3-coverage #1 ADDED
    en-bh.6thstreet.com (Algolia-backed BH storefront, is_algolia, genuine BHD),
    35→36. S3.1 (56dbca3) ADDED sonyworld.bh (official Sony Shopify, genuine BHD)
    — the 36 pin was never bumped for it, so the true pre-WS-G baseline is 37.
    WS-G (fragrance-content-quality P8, 2026-06-22) ADDED 2 CF-walled BH
    beauty/fragrance render sources sephora.bh + boutiqaat.com (is_render_only +
    requires_super — present in the registry list but routed/discovered ONLY when
    SCRAPEDO_SUPER is on; default usage='price'), 37→39. Wave-3c (2026-06-23)
    PROMOTED boutiqaat.com off render-only/super to mechanism="sitemap" (live
    re-verify cracked it to a $0 curl JSON-LD adapter) — it STAYS a price row
    (usage='price'), so the count is unchanged at 39. A5 (genuine-price KPI,
    2026-07-02) ADDED footlocker.com.bh (APEX, deliberately NOT "www." — see
    the source_router A5 note: _normalize_domain www-strips hosts, so a "www."
    row can never score/tier; the magento adapter re-canonicalizes to its
    pinned www host) (Alshaya Shape-A magento_graphql, genuine BHD,
    fashion/other — the built-but-dead recovery), 39→40. Guard the
    floor so a future accidental mass-deletion of price rows is caught.
    """
    price_rows = [s for s in SOURCE_REGISTRY if s.usage in ("price", "both")]
    assert len(price_rows) == 40


# ---------------------------------------------------------------------------
# Arabic review sources
# ---------------------------------------------------------------------------

def test_arabic_review_sources_registered():
    by_domain = {s.domain: s for s in SOURCE_REGISTRY}
    for dom in ARABIC_REVIEW_DOMAINS:
        assert dom in by_domain, f"{dom} not registered"
        s = by_domain[dom]
        assert s.usage == "review"
        assert s.tier == "gcc"
        assert s.weight == 1.5
        # review categories
        assert set(s.categories) == REVIEW_CATEGORIES


# ---------------------------------------------------------------------------
# source_usage helper
# ---------------------------------------------------------------------------

def test_source_usage_review_for_arabic():
    assert source_usage("https://www.sayidaty.net/some-article", "makeup") == "review"


def test_source_usage_price_for_retailer():
    assert source_usage("https://noon.com/product", "electronics") == "price"


def test_source_usage_unknown_domain_defaults_price():
    # Unknown domains never enter the registry harvest gate anyway; default
    # 'price' keeps the harvest filter conservative.
    assert source_usage("https://random-unknown-xyz.com", "makeup") == "price"


# ---------------------------------------------------------------------------
# Price-discovery filtering — review sources must NOT pollute price harvest
# ---------------------------------------------------------------------------

def test_get_sources_price_excludes_review_only():
    """With usage='price' filter, the Arabic review sources drop out."""
    price_sources = get_sources_for_category("makeup", usage="price")
    domains = {s.domain for s in price_sources}
    assert ARABIC_REVIEW_DOMAINS.isdisjoint(domains)


def test_get_sources_default_unchanged():
    """No usage arg → original behaviour (all sources for the category,
    including the new review ones if category matches)."""
    all_makeup = get_sources_for_category("makeup")
    domains = {s.domain for s in all_makeup}
    # Arabic review sources ARE in makeup's category set, so present here.
    assert "sayidaty.net" in domains


def test_site_discovery_query_excludes_review_sources():
    """The price `site:` discovery query must never target a review-only
    domain (it has no prices — pure scrape-budget burn)."""
    q = build_site_discovery_query("Maybelline Fit Me", "makeup", tier="gcc")
    for dom in ARABIC_REVIEW_DOMAINS:
        assert dom not in q


def test_score_source_unchanged_for_review_domain():
    """score_source is orthogonal to usage — a registered gcc review domain
    still scores its weight (1.5). The harvest-level usage filter, not the
    score, keeps it out of the price pool."""
    assert score_source("https://gulfnews.com/x", "fashion") == 1.5


# ---------------------------------------------------------------------------
# Review-source discovery (the NEW consumption path)
# ---------------------------------------------------------------------------

def test_get_review_sources_for_category():
    review_sources = get_sources_for_category("fashion", usage="review")
    domains = {s.domain for s in review_sources}
    assert ARABIC_REVIEW_DOMAINS.issubset(domains)


def test_review_sources_empty_for_non_review_category():
    """electronics is not a review category for the Arabic sources → none."""
    review_sources = get_sources_for_category("electronics", usage="review")
    domains = {s.domain for s in review_sources}
    assert ARABIC_REVIEW_DOMAINS.isdisjoint(domains)
