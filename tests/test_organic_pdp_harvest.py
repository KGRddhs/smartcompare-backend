"""B5 (genuine-price KPI Wave B) — ORGANIC PDP HARVEST.

The curl fan_out candidate_urls came EXCLUSIVELY from Serper `site:` discovery
on registry rows. But the ORGANIC results already fetched during the price
search carry PDP-shaped URLs on BH/GCC retail domains that the tier windows
drop: the captured fixture (a REAL Serper response, q="Tom Ford Oud Wood",
gl=bh) has bahrain.ounass.com organic with structured
{"currency": "BHD", "price": 119.75} and alhajisbahrain.com with BHD in the
snippet — while shopping gl=bh returns 0 items.

`_harvest_organic_pdp_candidates` mines those organic results (bounded,
deduped, fail-closed) and `_merge_organic_pdp_harvest` appends them to
candidate_urls so the existing JSON-LD + exact-identity + availability gates
verify them on the real PDP. Zero extra Serper calls — the harvest only READS
`results_by_tier`.

Fixture: tests/fixtures/serper_oudwood_organic.json. The noise mix (reddit /
fragrantica / youtube / sephora.com / tomfordbeauty.com / niceonesa.com /
thesmellofman.com) is genuine — all must be excluded (registry tier None or
"global"; only bahrain/gcc registry tiers, .bh TLDs, and bahrain.-prefixed
hosts are BH/GCC retail-eligible).

Flag: ENABLE_ORGANIC_PDP_HARVEST (default ON). Flag-OFF -> no harvest,
candidate_urls byte-identical to the pre-B5 pool.
"""

import json
from pathlib import Path

import pytest

from app.services.structured_comparison_service import (
    _ORGANIC_PDP_HARVEST_CAP,
    _harvest_organic_pdp_candidates,
    _merge_organic_pdp_harvest,
    _organic_host_bh_gcc_retail,
)

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "serper_oudwood_organic.json"

OUNASS_PDP = (
    "https://bahrain.ounass.com/shop-tom-ford-beauty-oud-wood-eau-de-parfum-"
    "50ml-for-unisex-207578119_242.html"
)
ALHAJIS_PDP = (
    "https://alhajisbahrain.com/products/tom-ford-oud-wood-edp-100ml"
    "?srsltid=AfmBOor6_qXJi4kGqXDOcta06kbXZEsuUXO3VlwTQEx5jsyMrADXY4vO"
)
QUERY = "Tom Ford Oud Wood"
CATEGORY = "fragrances"

# Every noise domain present in the real captured response — none may harvest.
FIXTURE_NOISE_HOSTS = (
    "reddit.com",
    "tomfordbeauty.com",
    "fragrantica.com",
    "niceonesa.com",
    "sephora.com",
    "youtube.com",
    "thesmellofman.com",
)


@pytest.fixture()
def serper_fixture():
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _harvest(serper_response, existing=(), query_name=QUERY, category=CATEGORY):
    return _harvest_organic_pdp_candidates(
        {"bahrain": serper_response},
        category,
        existing_urls=set(existing),
        query_name=query_name,
    )


def _links(harvested):
    return [h[0] for h in harvested]


def _hosts(harvested):
    return {h[1] for h in harvested}


# ---------------------------------------------------------------------------
# Harvest — inclusion + priority
# ---------------------------------------------------------------------------

class TestHarvestInclusion:
    def test_ounass_structured_bhd_harvested_first(self, serper_fixture):
        """The organic item carrying structured {"currency":"BHD","price":...}
        extras claims the FIRST harvest slot (priority bucket 0)."""
        harvested = _harvest(serper_fixture)
        assert harvested, "harvest returned nothing from the real fixture"
        assert harvested[0][0] == OUNASS_PDP

    def test_alhajis_bhd_snippet_harvested(self, serper_fixture):
        """alhajisbahrain.com (BHD in the snippet, no structured extras) is
        harvested — after the structured-extras ounass item."""
        harvested = _harvest(serper_fixture)
        links = _links(harvested)
        assert ALHAJIS_PDP in links
        assert links.index(ALHAJIS_PDP) > links.index(OUNASS_PDP)

    def test_harvested_tuple_shape_and_route(self, serper_fixture):
        """Harvest rows carry the `(link, domain_label, route, weight)` shape
        `_finalize_fan_winner` route-stamps from `harvested`."""
        harvested = _harvest(serper_fixture)
        for link, label, route, weight in harvested:
            assert link.startswith("https://")
            assert route == "organic_harvest"
            assert isinstance(weight, float)
        labels = _hosts(harvested)
        assert "bahrain.ounass.com" in labels
        assert "alhajisbahrain.com" in labels


class TestHarvestExclusions:
    def test_fixture_noise_domains_all_excluded(self, serper_fixture):
        """tomfordbeauty.com / reddit / fragrantica / sephora.com / youtube /
        niceonesa / thesmellofman: none may enter the candidate pool (registry
        tier None or global — NOT BH/GCC retail)."""
        harvested = _harvest(serper_fixture)
        hosts = _hosts(harvested)
        for noise in FIXTURE_NOISE_HOSTS:
            assert not any(
                h == noise or h.endswith("." + noise) for h in hosts
            ), f"noise domain {noise} leaked into the organic harvest"
        # The real fixture yields EXACTLY the two BH retail PDPs.
        assert hosts == {"bahrain.ounass.com", "alhajisbahrain.com"}

    def test_amazon_marketplace_excluded_even_with_bhd_extras(self, serper_fixture):
        """A general .com marketplace (global registry tier) NEVER harvests,
        even when Serper stamps BHD structured extras on it."""
        serper_fixture["organic"].append({
            "title": "Tom Ford Oud Wood Eau de Parfum 100ml",
            "link": "https://www.amazon.com/dp/B00PJGVKPO",
            "snippet": "Tom Ford Oud Wood 100ml. 119.000 BHD.",
            "currency": "BHD",
            "price": 119.0,
            "position": 11,
        })
        harvested = _harvest(serper_fixture)
        assert not any("amazon.com" in link for link in _links(harvested))

    def test_listing_urls_excluded_on_eligible_domains(self, serper_fixture):
        """A search/listing URL on an otherwise-eligible BH domain is dropped
        (is_non_pdp_listing_url / _is_listing_url gates) — no single PDP price
        to verify."""
        serper_fixture["organic"].extend([
            {
                "title": "Search: tom ford — Al Hajis",
                # WP/Woo search family: exact query-key `s=` marks a listing.
                "link": "https://alhajisbahrain.com/?s=tom+ford+oud+wood",
                "snippet": "Results for tom ford. From 125.000 BHD.",
                "position": 12,
            },
            {
                "title": "Tom Ford | Al Hajis",
                "link": "https://alhajisbahrain.com/collections/tom-ford",
                "snippet": "Shop Tom Ford. Prices in BHD.",
                "position": 13,
            },
        ])
        harvested = _harvest(serper_fixture)
        links = _links(harvested)
        assert not any("?s=" in link for link in links)
        assert not any("/collections/" in link for link in links)


class TestHarvestBounds:
    def test_cap_honored(self, serper_fixture):
        """More eligible PDPs than the cap -> exactly _ORGANIC_PDP_HARVEST_CAP
        rows harvested (bounded BEFORE merging into candidate_urls)."""
        for i in range(6):
            serper_fixture["organic"].append({
                "title": f"Tom Ford Oud Wood EDP {i}",
                # .bh TLD => BH retail-eligible even off-registry.
                "link": f"https://shop{i}.example.bh/products/oud-wood-{i}",
                "snippet": "Tom Ford Oud Wood. 120.000 BHD.",
                "position": 20 + i,
            })
        harvested = _harvest(serper_fixture)
        assert len(harvested) == _ORGANIC_PDP_HARVEST_CAP

    def test_dedupe_vs_site_discovery_urls(self, serper_fixture):
        """A PDP already in the site:-discovery candidate_urls is NOT
        re-harvested (dedupe against existing_urls)."""
        harvested = _harvest(serper_fixture, existing={OUNASS_PDP})
        links = _links(harvested)
        assert OUNASS_PDP not in links
        assert ALHAJIS_PDP in links  # the rest of the harvest survives

    def test_within_harvest_dedupe_sitelink_fragment(self, serper_fixture):
        """The alhajis PDP appears BOTH as a top-level organic item and as a
        reddit `#:~:text=` sitelink in the real fixture — harvested ONCE
        (fragment-stripped dedupe)."""
        harvested = _harvest(serper_fixture)
        alhajis_rows = [
            link for link in _links(harvested) if "alhajisbahrain.com" in link
        ]
        assert len(alhajis_rows) == 1


class TestHarvestFlag:
    def test_flag_off_no_harvest(self, serper_fixture, monkeypatch):
        monkeypatch.setenv("ENABLE_ORGANIC_PDP_HARVEST", "false")
        assert _harvest(serper_fixture) == []

    def test_flag_default_on(self, serper_fixture, monkeypatch):
        monkeypatch.delenv("ENABLE_ORGANIC_PDP_HARVEST", raising=False)
        assert _harvest(serper_fixture)


# ---------------------------------------------------------------------------
# BF5 (sweep OR-8) — BH-locale PATH evidence for off-registry hosts
# ---------------------------------------------------------------------------

def _org(link, title="", snippet="", currency=None, price=None):
    return {"link": link, "title": title, "snippet": snippet,
            "currency": currency, "price": price, "position": 1}


def _harvest_custom(items, query_name, category="fashion"):
    return _harvest_organic_pdp_candidates(
        {"bahrain": {"organic": items}}, category,
        existing_urls=set(), query_name=query_name,
    )


NAMSHI_RB3025_PDP = (
    "https://www.namshi.com/bahrain-en/buy-ray-ban-0rb3025-aviator-sunglasses/"
    "ZED28E4F81949E4666601Z/p/"
)


class TestBhLocalePathEvidence:
    """Wave B-FIX BF5 (sweep OR-8): the harvest registry gate dropped
    namshi.com/bahrain-en PDPs — registry tier None (catalog row dead), host
    neither .bh nor bahrain.-prefixed, and the /bahrain-en locale PATH marker
    was never consulted. A path starting with /bahrain-en, /bahrain-ar,
    /bh-en, /bh-ar on an https host is now BH-retail evidence at the SAME
    trust level as the bahrain. host prefix (off-registry rung — below the
    registry tiers and the global-tier fail-closed check)."""

    def test_namshi_bahrain_en_pdp_harvests(self):
        """The real recon-verified RB3025 PDP (the only genuine-BHD source
        for kpi-fash-004) now enters the fan_out pool."""
        rows = _harvest_custom(
            [_org(NAMSHI_RB3025_PDP,
                  "Ray-Ban 0Rb3025 Aviator Sunglasses", "82.52 BHD")],
            "Ray-Ban Aviator RB3025")
        assert [r[0] for r in rows] == [NAMSHI_RB3025_PDP]
        assert rows[0][1] == "namshi.com"
        assert rows[0][2] == "organic_harvest"

    def test_bh_locale_path_variants_harvest(self):
        """All four locale-path spellings count (namshi serves /bahrain-ar
        too; boutiqaat-style hosts use /bh-en, /bh-ar)."""
        for prefix in ("/bahrain-en", "/bahrain-ar", "/bh-en", "/bh-ar"):
            link = (f"https://www.namshi.com{prefix}/buy-tommy-hilfiger-"
                    "essential-flag-tee/Z405D183BA1857F58C53FZ/p/")
            rows = _harvest_custom(
                [_org(link, "Tommy Hilfiger Essential Flag T-Shirt",
                      "9.22 BHD")],
                "Tommy Hilfiger Essential Flag T-Shirt")
            assert [r[0] for r in rows] == [link], prefix

    def test_saudi_locale_path_gains_no_bh_status(self):
        """/saudi-en/ (or any non-BH locale path) must NOT gain BH status —
        the helper refuses the path evidence AND the wrong-locale gate
        independently drops the URL."""
        assert _organic_host_bh_gcc_retail(
            "namshi.com", path="/saudi-en/buy-x/Z1/p/") == (False, False)
        rows = _harvest_custom(
            [_org("https://www.namshi.com/saudi-en/buy-tommy-hilfiger-"
                  "essential-flag-tee/Z405D183BA1857F58C53FZ/p/",
                  "Tommy Hilfiger Essential Flag T-Shirt", "SAR 99")],
            "Tommy Hilfiger Essential Flag T-Shirt")
        assert rows == []

    def test_en_sa_ounass_keeps_gcc_tier_eligibility(self):
        """PIN THE DISTINCTION (task ruling): the Saudi-locale SUBDOMAIN
        en-sa.ounass.com keeps its registry gcc-tier eligibility exactly as
        today (converted-by-design; registry_known=True) — it is admitted by
        the gcc REGISTRY rung, never by the BH-locale path evidence."""
        assert _organic_host_bh_gcc_retail("en-sa.ounass.com") == (True, True)
        # A Saudi path on the same host changes nothing — still the gcc rung.
        assert _organic_host_bh_gcc_retail(
            "en-sa.ounass.com", path="/saudi-en/x") == (True, True)

    def test_http_scheme_path_evidence_refused(self):
        """BH-locale PATH evidence requires an https host — an http:// URL
        gains no BH status from its path (off-registry host stays excluded)."""
        rows = _harvest_custom(
            [_org("http://www.namshi.com/bahrain-en/buy-ray-ban-0rb3025-"
                  "aviator-sunglasses/ZED28E4F81949E4666601Z/p/",
                  "Ray-Ban 0Rb3025 Aviator Sunglasses", "82.52 BHD")],
            "Ray-Ban Aviator RB3025")
        assert rows == []

    def test_global_tier_never_gains_bh_path_status(self):
        """A registry-'global' host (amazon.com) stays fail-closed even with
        a /bahrain-en path — the path evidence sits BELOW the global-tier
        rejection, exactly like the bahrain. host prefix."""
        assert _organic_host_bh_gcc_retail(
            "amazon.com", path="/bahrain-en/dp/B0CHX2ZLPX") == (False, False)
        rows = _harvest_custom(
            [_org("https://www.amazon.com/bahrain-en/dp/B0CHX2ZLPX",
                  "Ray-Ban RB3025 Aviator", "BHD 30")],
            "Ray-Ban Aviator RB3025")
        assert rows == []


# ---------------------------------------------------------------------------
# BF5 (sweep OR-8 side-note) — HARVEST-side PDP-shape check
# ---------------------------------------------------------------------------

OUNASS_BROWSE = "https://bahrain.ounass.com/women/beauty/fragrance/"


class TestHarvestPdpShape:
    """Wave B-FIX BF5: the ounass category-browse URL (trailing-slash section
    page, no product slug) passes BOTH listing classifiers and wasted a cap
    slot. The HARVEST-side check now requires a product-y last path segment —
    a digit, or >=3 hyphens, or a /p/ marker (derived from the real PDP shapes
    below). The GLOBAL is_non_pdp_listing_url used by the fan_out/display
    gates is deliberately UNTOUCHED."""

    def test_ounass_category_browse_not_harvested(self, serper_fixture):
        serper_fixture["organic"].append(_org(
            OUNASS_BROWSE, "Fragrance | Ounass Bahrain",
            "Shop luxury fragrance online. Prices in BHD."))
        harvested = _harvest(serper_fixture)
        links = _links(harvested)
        assert OUNASS_BROWSE not in links
        # The real shop-* PDP on the SAME host still harvests (first slot).
        assert links[0] == OUNASS_PDP

    def test_global_listing_classifier_untouched(self):
        """HARVEST-side tightening only: the browse page still clears the
        global classifiers other gates consume (pin the scope of the fix)."""
        from app.services.source_router import is_non_pdp_listing_url
        from app.services.price_service import _is_listing_url
        assert is_non_pdp_listing_url(OUNASS_BROWSE) is False
        assert _is_listing_url(OUNASS_BROWSE) is False

    @pytest.mark.parametrize("link,query,category", [
        # digit-bearing slug, trailing slash (sharafdg WP PDP)
        ("https://bahrain.sharafdg.com/product/apple-iphone-15-256gb-pink-"
         "with-facetime-middle-east-version/",
         "Apple iPhone 15 256GB", "electronics"),
        # /p/<digits> tail (extra.com PDP)
        ("https://www.extra.com/en-bh/mobiles-tablets/mobiles/smartphone/"
         "apple-iphone-15-5g-256gb-6-1-inch-pink/p/100350333",
         "Apple iPhone 15 256GB", "electronics"),
        # trailing /p/ marker (noon PDP)
        ("https://www.noon.com/bahrain-en/acqua-di-gio-edt-100ml/"
         "N70115213V/p/",
         "Acqua di Gio Eau de Toilette 100ml", "fragrances"),
        # digit-less slug with >=3 hyphens (footlocker .bh PDP)
        ("https://www.footlocker.com.bh/en/buy-adidas-samba-og-mens-shoes-"
         "white", "Adidas Samba OG", "fashion"),
    ])
    def test_real_pdp_shapes_still_harvest(self, link, query, category):
        rows = _harvest_custom(
            [_org(link, query, "Genuine product. 99.000 BHD.")],
            query, category=category)
        assert [r[0] for r in rows] == [link]

    def test_amazon_ae_gcc_pdp_keeps_harvesting(self):
        """amazon.ae is registry gcc-tier and keeps harvesting AS TODAY —
        CONVERTED-BY-DESIGN (task ruling): the gcc tier feeds AED pages whose
        prices the fan_out gates stamp `converted_usd` honestly; the PDP-shape
        check (/dp/<asin> carries digits) must not disturb it."""
        link = "https://www.amazon.ae/Tom-Ford-Oud-Wood-Parfum/dp/B00PJGVKPO"
        rows = _harvest_custom(
            [_org(link, "Tom Ford Oud Wood Eau de Parfum 100ml", "AED 560")],
            "Tom Ford Oud Wood", category="fragrances")
        assert [r[0] for r in rows] == [link]


# ---------------------------------------------------------------------------
# scs-level merge — candidate_urls composition
# ---------------------------------------------------------------------------

SITE_DISCOVERY_URLS = [
    ("https://www.sharafdg.com/product/tom-ford-oud-wood/", "sharafdg.com"),
    ("https://www.faces.com/bh/en/p/tom-ford-oud-wood", "faces.com"),
    ("https://bahrain.ounass.com/other-tf-pdp-123.html", "bahrain.ounass.com"),
]
SITE_DISCOVERY_HARVESTED = [
    (link, label, "registry", 3.0) for link, label in SITE_DISCOVERY_URLS
]


class TestMergeAtScsLevel:
    def test_merge_appends_bounded_harvest_after_site_discovery(
        self, serper_fixture
    ):
        """Discovery yields N site: URLs; the organic harvest is APPENDED
        (deduped, cap-bounded) — the existing pool order and rows unchanged."""
        merged_urls, merged_harvested = _merge_organic_pdp_harvest(
            list(SITE_DISCOVERY_URLS),
            list(SITE_DISCOVERY_HARVESTED),
            {"bahrain": serper_fixture},
            CATEGORY,
            QUERY,
        )
        # Existing site:-discovery rows lead, order preserved.
        assert merged_urls[: len(SITE_DISCOVERY_URLS)] == SITE_DISCOVERY_URLS
        appended = merged_urls[len(SITE_DISCOVERY_URLS):]
        assert 0 < len(appended) <= _ORGANIC_PDP_HARVEST_CAP
        assert appended[0] == (OUNASS_PDP, "bahrain.ounass.com")
        # `harvested` grows in lockstep (route-stamp observability).
        assert merged_harvested[: len(SITE_DISCOVERY_HARVESTED)] == (
            SITE_DISCOVERY_HARVESTED
        )
        assert all(h[2] == "organic_harvest" for h in
                   merged_harvested[len(SITE_DISCOVERY_HARVESTED):])

    def test_merge_dedupes_vs_discovery(self, serper_fixture):
        """A discovery pool already containing the ounass PDP -> the harvest
        must not duplicate it."""
        pool = list(SITE_DISCOVERY_URLS) + [(OUNASS_PDP, "bahrain.ounass.com")]
        merged_urls, _ = _merge_organic_pdp_harvest(
            pool,
            SITE_DISCOVERY_HARVESTED
            + [(OUNASS_PDP, "bahrain.ounass.com", "registry", 3.0)],
            {"bahrain": serper_fixture},
            CATEGORY,
            QUERY,
        )
        assert [u for u, _l in merged_urls].count(OUNASS_PDP) == 1

    def test_merge_flag_off_byte_identical(self, serper_fixture, monkeypatch):
        """Flag OFF -> the merge returns the EXACT input objects (no harvest,
        candidate_urls exactly as before)."""
        monkeypatch.setenv("ENABLE_ORGANIC_PDP_HARVEST", "false")
        urls_in = list(SITE_DISCOVERY_URLS)
        harvested_in = list(SITE_DISCOVERY_HARVESTED)
        merged_urls, merged_harvested = _merge_organic_pdp_harvest(
            urls_in, harvested_in, {"bahrain": serper_fixture}, CATEGORY, QUERY
        )
        assert merged_urls is urls_in
        assert merged_harvested is harvested_in

    def test_merge_empty_discovery_still_harvests(self, serper_fixture):
        """Zero site: discovery URLs (the fan_out would previously not fire) —
        the organic harvest alone populates the pool."""
        merged_urls, merged_harvested = _merge_organic_pdp_harvest(
            [], [], {"bahrain": serper_fixture}, CATEGORY, QUERY
        )
        assert merged_urls
        assert merged_urls[0] == (OUNASS_PDP, "bahrain.ounass.com")
        assert len(merged_urls) <= _ORGANIC_PDP_HARVEST_CAP

    def test_merge_no_organic_results_noop(self):
        """Discovery ran but produced no organic rows -> inputs returned
        unchanged (no phantom candidates)."""
        urls_in = list(SITE_DISCOVERY_URLS)
        harvested_in = list(SITE_DISCOVERY_HARVESTED)
        merged_urls, merged_harvested = _merge_organic_pdp_harvest(
            urls_in, harvested_in,
            {"bahrain": {"organic": []}, "gcc": {"error": "boom"}},
            CATEGORY, QUERY,
        )
        assert merged_urls == urls_in
        assert merged_harvested == harvested_in
