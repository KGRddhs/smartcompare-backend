"""Wave-1 (source-intelligence, 2026-06-23) — the regional-storefront-alias
descriptor fields on Source + the json_api/sitemap selectors, and the registry
flag corrections (bolo/nasser flip OFF the STALE render-only flag — the recon
proved them directly readable; sephora.bh -> sephora.me canonical).
"""
from app.services.source_router import (
    Source,
    SOURCE_REGISTRY,
    get_jsonapi_sources_for_category,
    get_sitemap_sources_for_category,
)

_VALID_MECHANISMS = {
    "", "curl", "json_api", "sitemap", "algolia", "shopify", "render", "provider",
    # BH/GCC source-build (2026-06-25) — the 6 new $0 direct-fetch mechanisms.
    "woo_store_json", "salla_api", "occ_rest", "magento_graphql", "unbxd", "rest_json",
}
_DIRECT_MECHANISMS = {
    "curl", "json_api", "sitemap", "algolia", "shopify",
    "woo_store_json", "salla_api", "occ_rest", "magento_graphql", "unbxd", "rest_json",
}
_PROVIDER_MECHANISMS = {"render", "provider"}


def _by_domain():
    return {s.domain: s for s in SOURCE_REGISTRY}


def test_descriptor_fields_default_empty_on_a_bare_source():
    s = Source("x.example", "bahrain", (), 3.0)
    assert s.locale_paths == () and isinstance(s.locale_paths, tuple)
    assert s.subdomain_patterns == () and isinstance(s.subdomain_patterns, tuple)
    assert s.discovery_query_templates == () and isinstance(s.discovery_query_templates, tuple)
    assert s.currency == ""
    assert s.mechanism == ""
    assert s.pdp_url_pattern == ""
    assert s.sample_url == ""
    assert s.status == ""


def test_every_mechanism_is_in_the_enum():
    for s in SOURCE_REGISTRY:
        assert s.mechanism in _VALID_MECHANISMS, (s.domain, s.mechanism)


def test_direct_mechanism_rows_are_not_render_only_or_super():
    """A genuine-readable mechanism (curl/json_api/sitemap/shopify/algolia) must
    NOT carry render-only / requires_super — those flags would exclude it from the
    free curl/API harvest."""
    for s in SOURCE_REGISTRY:
        if s.mechanism in _DIRECT_MECHANISMS:
            assert not s.is_render_only, f"{s.domain} mechanism={s.mechanism} but is_render_only"
            assert not s.requires_super, f"{s.domain} mechanism={s.mechanism} but requires_super"


def test_provider_mechanism_rows_are_gated():
    for s in SOURCE_REGISTRY:
        if s.mechanism in _PROVIDER_MECHANISMS:
            assert s.is_render_only or s.requires_super, f"{s.domain} mechanism={s.mechanism} not gated"


def test_bolo_and_nasser_flipped_off_render_only():
    by = _by_domain()
    bolo = by["bolo.bh"]
    assert bolo.mechanism == "sitemap" and not bolo.is_render_only and bolo.currency == "BHD"
    nasser = by["nasserpharmacy.com"]
    assert nasser.mechanism == "json_api" and not nasser.is_render_only and nasser.currency == "BHD"


def test_sephora_me_is_canonical_provider_candidate():
    domains = {s.domain for s in SOURCE_REGISTRY}
    assert "sephora.me" in domains
    assert "sephora.bh" not in domains  # the unverified domain is replaced
    s = next(s for s in SOURCE_REGISTRY if s.domain == "sephora.me")
    assert s.requires_super and s.mechanism == "provider"
    assert s.status == "provider-test-candidate"
    assert s.sample_url.startswith("https://www.sephora.me/bh-en/")


def test_boutiqaat_flipped_to_live_sitemap_after_reverify():
    """Wave-3c RE-VERIFIED LIVE (2026-06-23): boutiqaat /en-bh PDPs serve a
    GENUINE native-BHD price in PLAIN-curl JSON-LD (flat @type:Product offer,
    priceCurrency=BHD) across 4 product types → promoted off render-only/super to
    mechanism="sitemap" (its own products-sitemap, $0 curl adapter), status live."""
    s = next(s for s in SOURCE_REGISTRY if s.domain == "boutiqaat.com")
    assert s.mechanism == "sitemap"
    assert not s.is_render_only and not s.requires_super
    assert s.currency == "BHD"
    assert s.status == "live"


def test_jsonapi_selector():
    nasser_cats = ("supplements", "skincare", "makeup", "haircare", "fragrances")
    for cat in nasser_cats:
        assert "nasserpharmacy.com" in [s.domain for s in get_jsonapi_sources_for_category(cat)]
    assert get_jsonapi_sources_for_category("__nope__") == []


def test_sitemap_selector():
    for cat in ("supplements", "makeup", "skincare"):
        assert "bolo.bh" in [s.domain for s in get_sitemap_sources_for_category(cat)]
    # Wave-3c — boutiqaat joined the sitemap channel for makeup/skincare/haircare/
    # fragrances (NOT supplements — it carries no supplement category).
    for cat in ("makeup", "skincare", "haircare", "fragrances"):
        assert "boutiqaat.com" in [s.domain for s in get_sitemap_sources_for_category(cat)]
    assert "boutiqaat.com" not in [s.domain for s in get_sitemap_sources_for_category("supplements")]
    assert get_sitemap_sources_for_category("__nope__") == []
