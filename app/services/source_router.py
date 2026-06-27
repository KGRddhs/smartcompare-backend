"""Bahrain-first source registry + URL scoring.

Lane 2 (Backend Comparison Engine Overhaul). Replaces the per-tier hard-coded
`OFFICIAL_BRAND_DOMAINS` / `AUTHORIZED_LUXURY_RETAILERS` / `GCC_LUXURY_RETAILERS`
sets with a single weighted registry. Bahrain retailers score x3.0, GCC x1.5,
global x1.0 — feeds into Tier 1 source consolidation + the page-scrape
escalation cascade.

Source weighting drives the cross-validation in `confidence_service.py` so
mismatched Tier-1 Bahrain prices outvote a distant amazon.com listing.
"""

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple
from urllib.parse import urlparse


@dataclass(frozen=True)
class Source:
    domain: str
    tier: str  # "bahrain" | "gcc" | "global"
    categories: Tuple[str, ...]  # empty tuple = all categories
    weight: float
    # S2 I2.5 — what this source feeds. "price" (default) = price-discovery
    # only; "review" = review-content only (no prices — kept OUT of the price
    # scrape pool to avoid budget burn); "both" = usable for either. Default
    # "price" on every legacy row → zero behaviour change.
    usage: str = "price"
    # S3 L1.3 — Shopify-platform store. When True, the Tier 1.5 cascade can hit
    # `{domain}/products.json` DIRECTLY (free, static BHD prices, no Serper /
    # render credits) before the Serper site: discovery. Default False → every
    # legacy row unchanged; only verified-Shopify BH stores are tagged.
    is_shopify: bool = False
    # S3-genuine (2026-06-14) — JS-SPA store whose STATIC curl HTML carries no
    # usable price (confirmed by curling the PDP through the extractor). When
    # True, the cascade EXCLUDES it from the free curl-direct harvest (a curl is
    # wasted) and INCLUDES it in the budget-gated Firecrawl/Scrape.do render-tier
    # escalation. The store is real + priced — just render-needed. Default False.
    is_render_only: bool = False
    # S3 #21/#1 (2026-06-14) — storefront backed by a PUBLIC Algolia search index
    # (6thStreet today). When True, the Tier-2 Algolia cascade (between the
    # Shopify /products.json direct-fetch and the Serper site: discovery) queries
    # the index DIRECTLY via algolia_service.fetch_algolia_price (free, $0, no
    # Serper/render, genuine BHD). Default False → every legacy row unchanged.
    is_algolia: bool = False
    # WS-G (fragrance-content-quality P8, 2026-06-22) — CF-walled BH retailer that
    # ONLY cracks with Scrape.do "super" (residential proxy + anti-bot). When True
    # the row is EXCLUDED from all routing/discovery unless SCRAPEDO_SUPER is
    # enabled — so with the flag OFF (the cost-neutral default) the registry is
    # byte-identical to today (the row absent) and we never waste a CF-blocked
    # datacenter render + trip the SHARED scrapedo breaker on a wall only
    # residential proxies can pass. Default False → every legacy row unchanged.
    requires_super: bool = False
    # Source-intelligence — "regional storefront alias" descriptor (2026-06-23).
    # Discovery + classification metadata so the cascade, the warmer, and the
    # provider-test read ONE descriptor instead of scattered flags. ALL fields
    # default empty/() so every existing positional/kwarg row is byte-unchanged.
    # HARD RULE: tuple defaults MUST be bare () (frozen-dataclass-safe immutable),
    # NEVER field(default_factory=list).
    locale_paths: Tuple[str, ...] = ()          # /bh-en, /en-bh, /ar-bh, /bahrain, /bh
    subdomain_patterns: Tuple[str, ...] = ()    # bh., bahrain., en-bh.
    currency: str = ""                          # expected currency, e.g. "BHD"
    discovery_query_templates: Tuple[str, ...] = ()  # site:{domain}{locale} "{product}" BHD
    mechanism: str = ""                         # "" | curl | json_api | sitemap | algolia | shopify | render | provider | woo_store_json | salla_api | occ_rest | magento_graphql | unbxd | rest_json
    pdp_url_pattern: str = ""                   # e.g. /bh-en/p/{slug}/{product_id}
    sample_url: str = ""                        # one live-verified PDP (liveness anchor)
    status: str = ""                            # "" | live | provider-test-candidate | render-only
    # BH/GCC source-build (2026-06-25) — fan-out cap ordering key. Each
    # direct-fetch selector sorts (tier_order, priority_rank, registry_order) then
    # top-K slices so a category with hundreds of catalog rows can't fan out
    # hundreds of concurrent GETs and blow the 15s Phase-1 price cap. LOWER =
    # fetched first. Frozen-default 100 → every existing literal row byte-unchanged
    # (and outranked by a curated low-rank catalog row only when one exists).
    priority_rank: int = 100


_LITERAL_ROWS: List[Source] = [
    # === BAHRAIN PRIMARY (weight 3.0) ===
    # I5.3 (Bundle B S2, 2026-06-11) — dead-domain replacement, Decision F
    # (verify-or-delete, never fabricate). Liveness control-calibrated: the
    # control set (google.com, shopalmoayyed.com) returned HTTP 200 in the SAME
    # env, so a failure here is a real NXDOMAIN, not a sandbox DNS block. The
    # replaced domains were curl exit-6 "Could not resolve host" + Python
    # socket.gethostbyname gaierror; the replacements resolve to a real IP +
    # HTTP 200. Evidence: docs/investigations/2026-06-11-i5.3-registry-liveness.md.
    #   lulu.com.bh (NXDOMAIN)      -> luluhypermarket.com (192.185.171.105, 200;
    #                                  Cloudflare-defended, scrapes via Firecrawl)
    #   sharafdg.com.bh (NXDOMAIN)  -> bahrain.sharafdg.com (104.18.31.100, 200,
    #                                  6 JSON-LD blocks + 258 BHD — rich scrape)
    #   extra.com.bh (NXDOMAIN)     -> extra.com (104.18.14.223, 200, /ar-bh BHD)
    #   carrefourbh.com + geant.com.bh DELETED (both NXDOMAIN; carrefour.com.bh
    #     also NXDOMAIN — no live BH Carrefour/Geant domain exists to replace
    #     with, and a dead site: row starves the limit=4 discovery window).
    # S3-genuine gap-fill (2026-06-14, Decision-F): RETARGET bare
    # luluhypermarket.com -> gcc.luluhypermarket.com. The bare host's catalog is
    # en-ae/AED (WHY lulu yielded nothing); gcc + /en-bh/ serves BHD JSON-LD
    # (priceCurrency lowercase "bhd" — extractor .upper()-normalizes). THE
    # electronics keystone: broad catalog (electronics+grocery+pharmacy+beauty).
    Source("gcc.luluhypermarket.com", "bahrain", (), 3.0),
    Source("bahrain.sharafdg.com", "bahrain", ("electronics",), 3.0),
    Source("extra.com", "bahrain", ("electronics",), 3.0),
    # bahrain.microless.com — PDP curl Decision-F (2026-06-14): MacBook Air M4
    # PDP → 439.062 BHD via JSON-LD (offer price+priceCurrency=BHD, InStock).
    # CURL-scrapeable (the first 403 was a parallel-write race, re-curl = 200).
    # Laptops/computing electronics retailer.
    Source("bahrain.microless.com", "bahrain", ("electronics",), 3.0),
    Source(
        "bn.boots.com",
        "bahrain",
        ("supplements", "skincare", "makeup", "haircare"),
        3.0,
        is_render_only=True,  # JS-SPA: no static curl price → render-tier
    ),
    Source(
        "bolo.bh", "bahrain", ("supplements", "makeup", "skincare"), 3.0,
        # Source-intel recon 2026-06-23: Nuxt SSR — the PDP carries a genuine BHD
        # price in PLAIN-curl static HTML (the old "render-only" flag was STALE).
        # Discovery via its own products-sitemap (16 child) -> off-clock index.
        mechanism="sitemap", currency="BHD", subdomain_patterns=("www.",),
        pdp_url_pattern="/products/{internal_id}-{slug}",
        sample_url="https://www.bolo.bh/products/UO0872Z3OMT-kensington-wireless-presenter-with-red-laser-pointer-k33272ww",
        status="live",
    ),
    # S3-genuine gap-fill (2026-06-14, Decision-F): behbehani.com +
    # jumboelectronics.com DELETED — both are 200-but-NOT-a-store
    # (jumbo = 114-byte parked /lander redirect; behbehani = brochure splash, no
    # shop). I5.3 had kept them on a status-only 200 check; they have zero shop
    # signals and starve the limit=8 BH discovery window (the electronics 0/N).
    Source("talabat.com", "bahrain", ("grocery",), 3.0),
    # spinneysbahrain.com DELETED (I5.11 liveness gate 2026-06-12): NXDOMAIN;
    # spinneys.com live but no Bahrain storefront evidence (Decision F: never
    # fabricate). Re-add when a verified Bahrain-serving domain exists (S3).
    # megamart.bh — PDP curl Decision-F (2026-06-14): Angular SPA shell, the
    # "BD 3.455" price is JS-rendered (ZERO price in static curl HTML) → render-tier.
    Source("megamart.bh", "bahrain", ("grocery",), 3.0, is_render_only=True),
    # F1.5 expansion (verified live 2026-06-10) — Bahrain grocery + pharmacy
    # gaps. RATIFICATION REQUIRED (F1.5 checkpoint) before merge.
    Source(
        "alosraonline.com", "bahrain", ("grocery",), 3.0,
        is_render_only=True,  # Alosra (BMMI) — JS-SPA → render-tier
    ),
    Source(
        "nasserpharmacy.com",
        "bahrain",
        ("supplements", "skincare", "makeup", "haircare", "fragrances"),
        3.0,
        # Source-intel recon 2026-06-23: bare Apache (NO Cloudflare); genuine BHD
        # via its OWN JSON API (newapi.nasserpharmacy.com /v1/filterSearchs returns
        # the price directly). NOT render-only (the old flag was STALE).
        mechanism="json_api", currency="BHD", locale_paths=("/bh-en",),
        pdp_url_pattern="/bh-en/{product_alias}",
        sample_url="https://www.nasserpharmacy.com/bh-en/optifucin-1-5-g-ophthalmic-gel-tube-13589",
        status="live",
    ),  # Nasser Pharmacy — Bahrain's largest chain, 10k+ health/beauty SKUs
    Source(
        "bahrainpharmacy.com",
        "bahrain",
        ("supplements", "skincare", "makeup", "haircare"),
        3.0,
    ),  # Bahrain Pharmacy & General Store
    # WS-G (fragrance-content-quality P8, 2026-06-22) — the two BH retailers that
    # ACTUALLY carry Western-luxury fragrance/beauty but sit behind a Cloudflare
    # interstitial that a plain datacenter render can't pass (render-wall doc:
    # docs/investigations/2026-06-15-render-wall-bh-retailers.md). They are
    # render-only AND requires_super: routed/discovered ONLY when SCRAPEDO_SUPER
    # is enabled (residential proxy + anti-bot). With the flag OFF (the default)
    # these rows are filtered out everywhere, so discovery is byte-identical to
    # today and we never burn a CF-blocked render / trip the shared breaker. The
    # gated A/B measurement (G4) flips SCRAPEDO_SUPER to see if super cracks them.
    Source(
        # Source-intel correction 2026-06-23: the CANONICAL BH Sephora is
        # sephora.me + /bh-en (NOT sephora.bh, which 301s + is unverified). Ahmed's
        # real PDP /bh-en/p/.../713779 returns 403 AkamaiGHost from a non-BH IP.
        "sephora.me", "bahrain", ("makeup", "skincare", "fragrances"), 3.0,
        is_render_only=True, requires_super=True,
        locale_paths=("/bh-en",), currency="BHD", mechanism="provider",
        pdp_url_pattern="/bh-en/p/{slug}/{product_id}",
        discovery_query_templates=('site:sephora.me/bh-en "{product}" BHD',),
        sample_url="https://www.sephora.me/bh-en/p/size-up-immediate-supersized-volume-mascara/713779",
        status="provider-test-candidate",
    ),  # Sephora Bahrain (sephora.me /bh-en) — Akamai-walled, provider-test candidate
    Source(
        "boutiqaat.com", "bahrain",
        ("makeup", "skincare", "haircare", "fragrances"), 3.0,
        # Source-intel RE-VERIFIED LIVE 2026-06-23 (Wave-3c): the pre-re-verify
        # render-only/requires_super stance was CONSERVATIVE — the /en-bh PDP
        # actually serves a GENUINE native-BHD price in PLAIN-curl JSON-LD (a flat
        # @type:Product offer, priceCurrency="BHD"), proven across 4 product types
        # (fragrance 50.430 / lens 10.460 / bundle 43.050 / single 15.930). FLIPPED
        # off render-only/super → mechanism="sitemap" (own 47k-PDP products-sitemap,
        # off-clock indexed; $0 curl adapter fetch_boutiqaat_price — NO Serper, NO
        # render). Per-SKU data gaps (some bdl/sold-out SKUs serve Organization-only
        # JSON-LD) return an honest None (verify-or-omit), never a fabricated price.
        mechanism="sitemap", currency="BHD",
        locale_paths=("/en-bh",), subdomain_patterns=("www.",),
        pdp_url_pattern="/en-bh/{gender}/{slug}/p/",
        sample_url="https://www.boutiqaat.com/en-bh/women/ghuyoum-alqassar-100ml-edp-by-sulaiman-al-qassar-i-00000213650-1/p/",
        status="live",
    ),  # Boutiqaat — GCC beauty/fragrance, genuine BHD via sitemap+curl (Wave-3c)
    # F1.5 addendum (deeper verified-source discovery, live 2026-06-10) —
    # appliance/AC + fragrance + premium-grocery gap-fillers. Each is a real
    # BH e-commerce site with BHD prices + checkout + product pages.
    Source(
        "shopalmoayyed.com", "bahrain", ("electronics",), 3.0, is_shopify=True
    ),  # Y.K. Almoayyed & Sons (Shopify) — AC/appliances/electronics. S3 L1.3:
    #    /products.json verified — 30 products, static BHD JSON-LD (page_scrape).
    Source(
        "sonyworld.bh", "bahrain", ("electronics",), 3.0, is_shopify=True
    ),  # Sony World Bahrain (official Sony, Shopify, base currency BHD). S3.1
    #    follow-on A1: prod fetch_shopify_price → WH-1000XM5 145.0 BHD across 176
    #    products, /products.json (shopify_json) — fills the audio-gadget gap.
    Source(
        "bh.asgharali.com", "bahrain", ("fragrances",), 3.0, is_shopify=True
    ),  # Asgharali Perfumes BH (Shopify). S3 L1.3: /products.json verified —
    #    93 products, static BHD prices.
    # S3-reopen T4 (research brief §1, Decision-F re-verified 2026-06-14):
    # two verified free-endpoint Shopify fragrance stores — cheapest genuine-BHD
    # win ($0, no render). en-bh.ajmal.com /meta.json=BHD ("Oud Nadir 48.000");
    # alhajisbahrain.com /meta.json=BHD ("Meraki Amber 5.000"). (ajmal.com apex
    # is NOT Shopify — the BH store is the en-bh subdomain.)
    Source(
        "en-bh.ajmal.com", "bahrain", ("fragrances",), 3.0, is_shopify=True
    ),  # Ajmal Perfumes BH (Shopify /products.json, BHD)
    Source(
        "alhajisbahrain.com", "bahrain", ("fragrances",), 3.0, is_shopify=True
    ),  # Al Hajis BH (Shopify /products.json, designer fragrances, BHD)
    # S3 #21/#1 — 6thStreet (Apparel Group), Magento+Algolia. The PUBLIC search
    # index exposes genuine BHD via algolia_service.fetch_algolia_price (free,
    # $0, no Serper/render). FASHION/FOOTWEAR ONLY — L2 verify-or-omit
    # (2026-06-14): the harvested index returns NO genuine beauty ("lipstick"→0
    # hits, "Dior Sauvage"→backpacks, "Charlotte Tilbury"→Forever New dresses);
    # the beauty catalog is a SEPARATE Algolia index reachable only via a
    # headless browser (not harvestable, dropped). Positive gate proven:
    # "Nike Air Max SC"→genuine Nike BHD 32.000. Beauty (makeup/skincare/
    # haircare) rides the boutiqaat sitemap+curl adapter (Wave-3c, genuine BHD) +
    # nasser JSON-API + the Shopify fragrance stores (ajmal/alhajis/asgharali) +
    # sephora render-tier. Tier-2 (after Shopify, before curl).
    Source(
        "en-bh.6thstreet.com", "bahrain", ("fashion",), 3.0,
        is_algolia=True,
    ),  # 6thStreet BH (Algolia index, BHD, fashion/footwear only)
    Source(
        "jalilaperfumes.com", "bahrain", ("fragrances",), 3.0
    ),  # Jalila Perfumes BH (custom PHP, product pages + BHD)
    Source(
        "bateel.bh", "bahrain", ("grocery",), 3.0
    ),  # Bateel BH — premium dates / gourmet
    # S3 L1.2 (Ahmed pre-approved, Decision-F control-calibrated 2026-06-13) —
    # ounass.com's Bahrain subdomain. Verified curl-EXTRACTABLE: product pages
    # expose static Product JSON-LD with priceCurrency=BHD (extract_price_from_
    # html pulls 80 BHD from a real fixture once the L1.4 brand-field fix lets
    # the brand match). Real-BHD luxury source — unlike the Landmark fashion
    # SPAs (curl-unscrapeable, deferred to the L1.STRETCH dataset). The GCC
    # ounass.com apex row below is untouched; this BH subdomain scores 3.0.
    Source(
        "bahrain.ounass.com", "bahrain",
        ("fashion", "fragrances", "makeup"), 3.0,
    ),

    # === GCC SECONDARY (weight 1.5) ===
    # S3 coverage #2 — noon.com is Akamai-walled: a plain curl gets a 0-byte
    # body, and its JSON-LD price is a hardcoded-0 placeholder (the real price
    # hydrates in the Next.js RSC stream). Flag is_render_only so the cascade
    # routes it to the render tier instead of wasting a plain curl. noon stays
    # gcc-tier (SECONDARY breadth, gray-import) — never authoritative for Apple/
    # Samsung; sharafdg/microless are the authoritative BH electronics sources.
    Source("noon.com", "gcc", (), 1.5, is_render_only=True),
    Source("amazon.ae", "gcc", (), 1.5),
    Source("sharafdg.com", "gcc", ("electronics",), 1.5),
    Source("ounass.com", "gcc", ("fashion", "fragrances", "makeup"), 1.5),
    Source("bloomingdales.ae", "gcc", ("fashion",), 1.5),
    Source("tryano.com", "gcc", ("fashion", "fragrances"), 1.5),

    # === GLOBAL FALLBACK (weight 1.0) ===
    Source("amazon.com", "global", (), 1.0),
    Source("apple.com", "global", ("electronics",), 1.0),
    Source("samsung.com", "global", ("electronics",), 1.0),
    Source("sony.com", "global", ("electronics",), 1.0),
    Source("lg.com", "global", ("electronics",), 1.0),
    Source("iherb.com", "global", ("supplements",), 1.0),
    Source("sephora.com", "global", ("makeup", "skincare", "fragrances"), 1.0),
    Source("walmart.com", "global", (), 1.0),
    Source("fragrantica.com", "global", ("fragrances",), 1.0),
    Source("incidecoder.com", "global", ("skincare", "makeup", "haircare"), 1.0),
    Source("gsmarena.com", "global", ("electronics",), 1.0),

    # === ARABIC REVIEW-CONTENT SOURCES (S2 I2.5, usage="review") ===
    # Verified-real GCC editorial/review sites with NO product prices — kept
    # OUT of the price scrape pool (usage="review") and consulted only by the
    # review-content path. F1.5 carry-over (prep-notes §1, Ahmed-ratified).
    Source(
        "sayidaty.net", "gcc",
        ("fashion", "makeup", "skincare", "haircare", "fragrances"),
        1.5, usage="review",
    ),
    Source(
        "khaleejtimes.com", "gcc",
        ("fashion", "makeup", "skincare", "haircare", "fragrances"),
        1.5, usage="review",
    ),
    Source(
        "gulfnews.com", "gcc",
        ("fashion", "makeup", "skincare", "haircare", "fragrances"),
        1.5, usage="review",
    ),
]


# ===========================================================================
# BH/GCC catalog-loaded rows (source-build 2026-06-25)
# ===========================================================================
# The 400-source BH/GCC discovery catalog is consolidated + normalized by
# scripts/build_source_registry_data.py into ONE flat data file
# (data/bh_gcc_sources.json), each row carrying the FINAL Source field values
# (tier/weight/categories/mechanism/flags/currency/sample_url/priority_rank/
# status). This loader is deliberately DUMB — it does no mechanism/category
# mapping (the consolidation script owns that); it just constructs Source objects
# for the rows the liveness gate has PROMOTED.
#
# ZERO-REGRESSION BY CONSTRUCTION: a row is admitted ONLY when its status is
# "live" (a real PDP/API price was verified by scripts/verify_bh_gcc_sources.py).
# "render-only" and "provider-test-candidate" rows stay in the data file
# (provenance + a future Firecrawl/Scrape.do render pass) but are NOT admitted
# (see _ADMITTED_STATUSES below). The consolidation writes every row
# "provider-test-candidate" by default,
# so BEFORE the liveness gate runs, this loader admits ZERO catalog rows and
# SOURCE_REGISTRY is byte-identical to _LITERAL_ROWS — the whole change is a
# prod no-op until rows are explicitly promoted. The existing selectors therefore
# need NO status filter; the registry simply never contains an unverified row.
#
# Import-time-pure + fail-OPEN: pure stdlib (json + pathlib), NO network/DB, path
# resolved relative to __file__ (NOT cwd — Windows cwd-persist trap), and ANY
# failure (missing file, parse error, malformed row) returns [] / skips-with-log
# rather than raising — a broken data file must NEVER brick every import of
# source_router / price_service.
import json as _json
import logging as _logging
from pathlib import Path as _Path

_loader_logger = _logging.getLogger(__name__)

_CATALOG_DATA_PATH = (
    _Path(__file__).resolve().parent.parent.parent / "data" / "bh_gcc_sources.json"
)
# Only these statuses enter the registry (verify-or-omit; see module note). ONLY
# "live" — a row promoted by the liveness gate after a real sample_url price
# probe. "render-only"/"provider-test-candidate" rows stay in the data file
# (provenance + a future Firecrawl/Scrape.do render pass) but are NOT admitted, so
# before the gate runs SOURCE_REGISTRY == _LITERAL_ROWS exactly (a prod no-op) and
# nothing enters Serper discovery / scoring until it is explicitly verified live.
_ADMITTED_STATUSES = frozenset({"live"})
# Verification F7 (belt-and-suspenders) — a CATALOG row may only be bahrain/gcc.
# tier="global" is reserved for the hand-curated literals (apple/samsung/amazon)
# and must NEVER come from the catalog: _is_genuine_bh_candidate force-downgrades a
# global-tier domain's genuine scrape to converted, so a global catalog row would
# silently lose its genuine stamp. The consolidation provably never emits global;
# this gate enforces it at load time regardless.
_VALID_TIERS = frozenset({"bahrain", "gcc"})


def _row_to_source(row: dict) -> Optional[Source]:
    """Construct a Source from one consolidated catalog row, or None if the row
    is malformed / not admitted. Never raises."""
    try:
        if not isinstance(row, dict):
            return None
        status = str(row.get("status") or "")
        if status not in _ADMITTED_STATUSES:
            return None
        domain = str(row.get("domain") or "").strip().lower()
        if not domain:
            return None
        tier = str(row.get("tier") or "")
        if tier not in _VALID_TIERS:
            return None
        cats = row.get("categories") or []
        if not isinstance(cats, list):
            return None
        try:
            weight = float(row.get("weight", 1.5))
        except (TypeError, ValueError):
            weight = 1.5
        try:
            prank = int(row.get("priority_rank", 100))
        except (TypeError, ValueError):
            prank = 100
        return Source(
            domain=domain,
            tier=tier,
            categories=tuple(str(c) for c in cats),
            weight=weight,
            is_shopify=bool(row.get("is_shopify", False)),
            is_algolia=bool(row.get("is_algolia", False)),
            is_render_only=bool(row.get("is_render_only", False)),
            currency=str(row.get("currency") or ""),
            mechanism=str(row.get("mechanism") or ""),
            sample_url=str(row.get("sample_url") or ""),
            status=status,
            priority_rank=prank,
        )
    except Exception as exc:  # noqa: BLE001 — one bad row must never brick the load
        _loader_logger.info("[source_router] skipped malformed catalog row: %s", exc)
        return None


def _catalog_sources_enabled() -> bool:
    """The BH/GCC catalog rows load ONLY when ENABLE_BH_GCC_CATALOG_SOURCES is on
    (fail-CLOSED, default OFF — same posture as the price-warmer / sitemap-index
    crons). So the build SHIPS DORMANT: even after the liveness gate promotes rows
    to status="live" in the data file, SOURCE_REGISTRY == _LITERAL_ROWS until the
    flag is flipped on Railway — then the verified genuine BH/GCC sources activate
    (Ahmed's call, like the warmer). One env read, no import-time cost."""
    import os
    return os.getenv("ENABLE_BH_GCC_CATALOG_SOURCES", "").strip().lower() in (
        "true", "1", "yes", "on",
    )


def _load_catalog_rows() -> List[Source]:
    """Load the liveness-promoted BH/GCC catalog rows from data/bh_gcc_sources.json.

    Returns [] when the activation flag is OFF (ships dormant) OR on a
    missing/unreadable/non-list file (fail-open) so the registry degrades to the
    literal rows rather than failing every import. Dedup against the literals is
    done HERE (skip any catalog domain already covered by a literal apex) so an
    edit-in-place literal (sharafdg/extra/bn.boots/noon) always wins over a
    duplicate catalog row."""
    # Flag OFF (the default) → ZERO catalog rows, registry == literals, prod no-op.
    if not _catalog_sources_enabled():
        return []
    try:
        if not _CATALOG_DATA_PATH.exists():
            return []
        raw = _CATALOG_DATA_PATH.read_text(encoding="utf-8")
        data = _json.loads(raw)
    except Exception as exc:  # noqa: BLE001 — fail-open: degrade to literals
        _loader_logger.warning(
            "[source_router] catalog load failed (%s) — registry = literals only", exc
        )
        return []
    if not isinstance(data, list):
        return []
    literal_domains = {s.domain.replace("www.", "").lower() for s in _LITERAL_ROWS}
    out: List[Source] = []
    seen: set = set()
    for row in data:
        src = _row_to_source(row)
        if src is None:
            continue
        d = src.domain.replace("www.", "").lower()
        # Dedup: skip if a literal already covers this apex (or a parent of it),
        # or if an earlier catalog row claimed the same domain.
        if d in seen:
            continue
        if any(d == ld or d.endswith("." + ld) for ld in literal_domains):
            continue
        seen.add(d)
        out.append(src)
    return out


# The runtime registry = the curated literals + the liveness-promoted catalog
# rows. Assembled ONCE at import. (Before the liveness gate promotes any row this
# equals _LITERAL_ROWS exactly — a prod no-op.)
SOURCE_REGISTRY: List[Source] = _LITERAL_ROWS + _load_catalog_rows()


_TIER_ORDER = ("bahrain", "gcc", "global")


def _normalize_domain(host: str) -> str:
    host = host.lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def match_registry_apex(host: str) -> str:
    """Collapse a winning retailer host to its registry apex, if any.

    `uae.sharafdg.com` -> `sharafdg.com`; `www.noon.com` -> `noon.com`;
    `talabat.com` -> `talabat.com`. An off-registry host is returned unchanged
    (lowercased, www-stripped). Suffix-match mirrors `score_source` so a
    regional subdomain of a registry source is counted under the apex — fixes
    the by_source subdomain undercount (G1 finding F2: writer recorded the raw
    subdomain while the reader probed apex keys only).
    """
    if not host:
        return host
    domain = _normalize_domain(str(host))
    for s in SOURCE_REGISTRY:
        registry_domain = s.domain.lower()
        if domain == registry_domain or domain.endswith("." + registry_domain):
            return registry_domain
    return domain


def registry_tier(host_or_url: str) -> Optional[str]:
    """Return the registry tier ("bahrain" | "gcc" | "global") for a host/URL,
    or None when the domain isn't in the registry.

    Suffix-matches like `score_source`/`match_registry_apex` so a regional
    subdomain resolves to its apex tier (`store.apple.com` -> apple.com ->
    "global"; `bahrain.sharafdg.com` -> "bahrain"). Accepts a bare host or a
    full URL.

    S3 coverage #2 (the apple.com-198.9 wrong-scrape) — used by `_curl_scraper`
    to enforce "a GLOBAL-tier domain can never carry a genuine page_scrape*/
    local_bhd label" (no BH Apple Store ⇒ a global scrape is converted_usd at
    best). A non-registry domain (None) is treated as NOT-global by the caller
    (a discovered BH retailer PDP off-registry can still be genuine).
    """
    if not host_or_url:
        return None
    raw = str(host_or_url)
    # Accept a full URL — pull the netloc; else treat as a bare host.
    if "://" in raw or "/" in raw:
        try:
            from urllib.parse import urlparse
            netloc = urlparse(raw if "://" in raw else "//" + raw).netloc
            raw = netloc or raw
        except Exception:  # noqa: BLE001
            pass
    domain = _normalize_domain(raw)
    if not domain:
        return None
    for s in SOURCE_REGISTRY:
        registry_domain = s.domain.lower()
        if domain == registry_domain or domain.endswith("." + registry_domain):
            return s.tier
    return None


def _usage_allows(source_usage_value: str, wanted: str) -> bool:
    """True when a source of `source_usage_value` may serve `wanted`.

    "both" serves either; "price"/"review" serve only their own kind.
    """
    if source_usage_value == "both":
        return True
    return source_usage_value == wanted


def _super_routing_enabled() -> bool:
    """WS-G — whether requires_super registry rows are routable. Reads the SAME
    SCRAPEDO_SUPER flag the Scrape.do request params read, via the single source
    of truth in scrapedo_service (so the gate and the actual super-render request
    can never disagree, and the existing reset_super_flags_cache() test hook
    resets both). Lazy import keeps source_router import-time dependency-free;
    fail-CLOSED (treat as OFF) on any import/read error so a broken flag never
    accidentally routes a credit-spending CF-walled source."""
    try:
        from app.services.scrapedo_service import _super_enabled

        return _super_enabled()
    except Exception:  # noqa: BLE001 — fail-closed: flag OFF on any error
        return False


def get_sources_for_category(
    category: str, usage: Optional[str] = None
) -> List[Source]:
    """Return sources ordered by tier (bahrain -> gcc -> global), filtered by category.

    A source with empty `categories` matches every category. Otherwise the
    category must appear in the tuple.

    S2 I2.5 — when `usage` is given ("price" or "review"), only sources usable
    for that purpose are returned (a "both" source qualifies for either). The
    default `usage=None` preserves the pre-S2 behaviour (all sources for the
    category, regardless of usage).

    WS-G — a `requires_super` source (CF-walled BH retailer that only cracks via
    Scrape.do "super") is EXCLUDED unless SCRAPEDO_SUPER is enabled. With the
    flag OFF (the cost-neutral default) the returned set is byte-identical to
    today — the gated rows absent — so this routing chokepoint (and the
    build_site_discovery_query / Serper discovery it feeds) never surfaces a
    domain we'd waste a CF-blocked datacenter render on.
    """
    super_enabled = _super_routing_enabled()
    result: List[Source] = []
    for tier in _TIER_ORDER:
        for s in SOURCE_REGISTRY:
            if s.tier != tier:
                continue
            if getattr(s, "requires_super", False) and not super_enabled:
                continue
            if s.categories and category not in s.categories:
                continue
            if usage is not None and not _usage_allows(s.usage, usage):
                continue
            result.append(s)
    return result


def get_shopify_sources_for_category(category: str) -> List[Source]:
    """S3 L1.3 — Bahrain-tier Shopify sources for `category`, in registry order.

    The Tier 1.5 cascade iterates these to hit `{domain}/products.json` DIRECTLY
    (free, static BHD, no Serper/render) before the Serper site: discovery. A
    Shopify source with empty `categories` would match every category; today's
    tagged rows are category-scoped (almoayyed=electronics, asgharali=
    fragrances). Returns a (possibly empty) list — never raises.
    """
    return [
        s
        for s in SOURCE_REGISTRY
        if s.is_shopify
        and s.tier == "bahrain"
        and (not s.categories or category in s.categories)
    ]


def get_algolia_sources_for_category(category: str) -> List[Source]:
    """S3 #21/#1 — Bahrain-tier Algolia-backed sources for `category`, in
    registry order.

    The Tier-2 cascade (between the Shopify /products.json direct-fetch and the
    Serper site: discovery) iterates these to query the store's PUBLIC Algolia
    index DIRECTLY via algolia_service.fetch_algolia_price (free, $0, no Serper/
    render, genuine BHD). Returns a (possibly empty) list — never raises.
    """
    return [
        s
        for s in SOURCE_REGISTRY
        if s.is_algolia
        and s.tier == "bahrain"
        and (not s.categories or category in s.categories)
    ]


def get_jsonapi_sources_for_category(category: str) -> List[Source]:
    """Source-intelligence (2026-06-23) — Bahrain-tier JSON-API sources for
    `category`, in registry order. The cascade hits the store's OWN JSON API
    DIRECTLY (free, $0, no Serper/render, genuine BHD) — e.g. nasserpharmacy's
    /v1/filterSearchs. Returns a (possibly empty) list — never raises.
    """
    return [
        s
        for s in SOURCE_REGISTRY
        if s.mechanism == "json_api"
        and s.tier == "bahrain"
        and (not s.categories or category in s.categories)
    ]


def get_curl_pagescrape_sources_for_category(category: str) -> List[Source]:
    """Genuine-BH orphan-row fix (2026-06-27) — Bahrain-tier PLAIN curl /
    JSON-LD sources for `category`, in registry order.

    These are the catalog rows that map to NO direct per-domain adapter
    (mechanism "" or "curl", genuine_method "page_scrape_jsonld" — e.g.
    sporter.com / drnutrition.com / matgarbahrain.com / healbahrain.com).
    The consolidation script (build_source_registry_data._mechanism_and_flags)
    emits ~199 such live rows (47 bahrain-tier), but UNTIL THIS SELECTOR they
    had no consumer except the limit-capped Serper `site:` discovery — the
    supplement branch (which never runs that discovery) reached NONE of them.

    A row qualifies on mechanism ("" or "curl"), bahrain tier, and category —
    the same predicate `_bahrain_discovery_only_sources` uses, minus the
    Shopify/Algolia exclusions (already excluded by the is_shopify/is_algolia
    guards). The caller curls/attributes the source's apex domain. Returns a
    (possibly empty) list — never raises. Bahrain-tier only (every bahrain
    literal + catalog row is BHD, so a hit on these is genuine BHD).
    """
    return [
        s
        for s in SOURCE_REGISTRY
        if (s.mechanism or "") in ("", "curl")
        and s.tier == "bahrain"
        and not s.is_shopify
        and not s.is_algolia
        and (not s.categories or category in s.categories)
    ]


def get_sitemap_sources_for_category(category: str) -> List[Source]:
    """Source-intelligence (2026-06-23) — Bahrain-tier sitemap/curl sources for
    `category`, in registry order. Discovery via the store's OWN sitemap (an
    off-clock index) then a plain curl of the PDP for a genuine BHD price ($0, no
    Serper/render). Returns a (possibly empty) list — never raises.
    """
    return [
        s
        for s in SOURCE_REGISTRY
        if s.mechanism in ("sitemap", "curl")
        and s.tier == "bahrain"
        and (not s.categories or category in s.categories)
    ]


# ===========================================================================
# BH/GCC source-build (2026-06-25) — new direct-fetch mechanism selectors
# ===========================================================================
# The 6 NEW $0 adapters (woocommerce / salla / occ / magento-graphql / unbxd /
# rest-json) get their own per-mechanism selectors. UNLIKE the bahrain-only
# Shopify/Algolia/sitemap/jsonapi selectors (safe — every bahrain literal is
# BHD), these span BOTH bahrain AND gcc tiers because the same adapter serves the
# converted GCC tail too — the ADAPTER stamps genuine (BHD) vs converted_usd by
# the response's ACTUAL currency, so a gcc row never mis-claims a genuine BH
# price. Each selector applies the FAN-OUT CAP so a category with hundreds of
# catalog rows can't fan out hundreds of concurrent GETs (see _fanout_cap).

# Top-K direct-fetch sources per mechanism per category. Env-overridable so an ops
# tune needs no code change. Mirrors the existing `[:limit]` discovery caps.
def _fanout_k() -> int:
    try:
        import os
        return max(1, int(os.getenv("BH_GCC_FANOUT_K", "6")))
    except (TypeError, ValueError):
        return 6


def _direct_fetch_sources(category: str, mechanism: str) -> List[Source]:
    """Bahrain+GCC-tier sources of `mechanism` for `category`, ordered
    (tier: bahrain before gcc, then priority_rank asc, then registry order) and
    TOP-K capped (_fanout_k). Returns [] never raises. The cap bounds the cascade
    fan-out; the adapter still stamps genuine-vs-converted by actual currency."""
    matched = [
        (idx, s)
        for idx, s in enumerate(SOURCE_REGISTRY)
        if s.mechanism == mechanism
        and s.tier in ("bahrain", "gcc")
        and (not s.categories or category in s.categories)
    ]
    # bahrain (tier index 0) before gcc (1); then low priority_rank first; then
    # stable registry order.
    matched.sort(key=lambda t: (_TIER_ORDER.index(t[1].tier), t[1].priority_rank, t[0]))
    return [s for _idx, s in matched[: _fanout_k()]]


def get_woo_sources_for_category(category: str) -> List[Source]:
    """WooCommerce Store API sources (fetch_woocommerce_store_api_price)."""
    return _direct_fetch_sources(category, "woo_store_json")


def get_salla_sources_for_category(category: str) -> List[Source]:
    """Salla storefront API sources (fetch_salla_api_price)."""
    return _direct_fetch_sources(category, "salla_api")


def get_occ_sources_for_category(category: str) -> List[Source]:
    """SAP-Hybris OCC v2 sources (fetch_occ_rest_price)."""
    return _direct_fetch_sources(category, "occ_rest")


def get_magento_gql_sources_for_category(category: str) -> List[Source]:
    """Adobe-Commerce/Magento GraphQL sources (fetch_magento_graphql_price)."""
    return _direct_fetch_sources(category, "magento_graphql")


def get_unbxd_sources_for_category(category: str) -> List[Source]:
    """Unbxd search-API sources (fetch_unbxd_price)."""
    return _direct_fetch_sources(category, "unbxd")


def get_restjson_sources_for_category(category: str) -> List[Source]:
    """Custom REST-JSON sources — panda/ourshopee/beautybooth (fetch_rest_json_price)."""
    return _direct_fetch_sources(category, "rest_json")


def source_usage(url: str, category: str) -> str:
    """Return the registry usage ("price"|"review"|"both") for `url` under
    `category`, or "price" for unknown / mis-categorized domains.

    Mirrors `score_source`'s matching so the price-harvest gate can reject
    review-only domains. Unknown domains default to "price" (conservative:
    they never enter the registry harvest gate anyway since score_source
    returns 0.5 < 1.5 for them).
    """
    try:
        parsed = urlparse(url)
    except (ValueError, TypeError):
        return "price"
    if not parsed.netloc:
        return "price"

    domain = _normalize_domain(parsed.netloc)
    for s in SOURCE_REGISTRY:
        registry_domain = s.domain.lower()
        if domain == registry_domain or domain.endswith("." + registry_domain):
            if not s.categories or category in s.categories:
                return s.usage
    return "price"


def score_source(url: str, category: str) -> float:
    """Return weight 0.5-3.0 for `url` under the given `category`.

    Unknown domains return 0.5. Mis-categorized known domains (e.g., sharafdg
    BH URL under category="supplements") also return 0.5 — the source is
    relevant only inside its declared categories.
    """
    try:
        parsed = urlparse(url)
    except (ValueError, TypeError):
        return 0.5
    if not parsed.netloc:
        return 0.5

    domain = _normalize_domain(parsed.netloc)
    for s in SOURCE_REGISTRY:
        registry_domain = s.domain.lower()
        if domain == registry_domain or domain.endswith("." + registry_domain):
            if not s.categories or category in s.categories:
                return s.weight
    return 0.5


# S3-genuine (team-lead live probe 2026-06-14) — wrong-GCC-locale path segments.
# Serper `site:` discovery returns mixed-locale results for the multi-locale BH
# registry domains; score_source matches by DOMAIN and ignores the locale PATH,
# so a /en-sa/ (SAR) page on bahrain-tier extra.com scores 3.0 and gets scraped
# → a Saudi price. These segments mark a NON-Bahrain GCC locale to DROP. NO
# rewrite (SKU IDs differ per locale → 404); we only filter.
_WRONG_GCC_LOCALE_SEGMENTS = (
    "/en-sa/", "/ar-sa/",   # Saudi (SAR)
    "/en-ae/", "/ar-ae/", "/uae_en/", "/uae_ar/",  # UAE (AED)
    "/en-om/", "/ar-om/",   # Oman (OMR)
    "/en-kw/", "/ar-kw/",   # Kuwait (KWD)
    "/en-qa/", "/ar-qa/",   # Qatar (QAR)
)
# Genuine-BH latency+warmer bundle D8 (2026-06-15) — REGION-in-PATH markers used
# by retailers (esp. noon.com) that name the country as a bare path prefix rather
# than an `xx-yy` locale segment. noon serves `noon.com/egypt-en/...`,
# `noon.com/saudi-en/...`, `noon.com/uae-en/...` — a Bahrain query must drop these
# (foreign currency: EGP/SAR/AED). KEEP `noon.com/bahrain-en/` (added to the BH
# markers below). These complement `_WRONG_GCC_LOCALE_SEGMENTS` (the `xx-yy` form);
# matched as substrings so the leading-slash/hyphen variants all catch.
_WRONG_REGION_PATH_SEGMENTS = (
    "/egypt-", "/egypt/",           # Egypt (EGP)
    "/saudi-", "/saudi/", "/ksa-", "/ksa/",  # Saudi (SAR)
    "/uae-", "/uae/",               # UAE (AED) — bare-region form (not uae_en locale)
    "/oman-", "/oman/",             # Oman (OMR)
    "/kuwait-", "/kuwait/",         # Kuwait (KWD)
    "/qatar-", "/qatar/",           # Qatar (QAR)
    "/cairo/", "/cairo-",           # Egypt city
)
# Bahrain locale markers — if present, the URL is explicitly BH (keep even if a
# wrong-locale string somehow co-occurs, which it shouldn't). `/bahrain-` covers
# noon's bare-region form (`noon.com/bahrain-en/...`).
_BH_LOCALE_MARKERS = (
    "/en-bh/", "/ar-bh/", "/bahrain_en/", "/bahrain_ar/", "-bh/",
    "/bahrain-", "/bahrain/",
)


def is_wrong_locale_url(url: str) -> bool:
    """True iff `url` carries a NON-Bahrain GCC locale path segment (so it would
    yield a foreign-currency price and must be dropped from the BH scrape pool).

    KEEP: explicit BH locale (/en-bh/, /ar-bh/, /bahrain_en/), bahrain.* subdomain,
    and locale-NEUTRAL paths (no recognizable GCC locale segment) — conservative,
    never drop a maybe-BH page. DROP only an explicit wrong-GCC-locale segment.
    """
    if not url:
        return False
    try:
        parsed = urlparse(url)
    except (ValueError, TypeError):
        return False
    host = (parsed.netloc or "").lower()
    path = (parsed.path or "").lower()
    # A bahrain.* subdomain is inherently BH — keep.
    if host.startswith("bahrain.") or host.startswith("www.bahrain."):
        return False
    # An explicit BH locale marker anywhere → keep.
    if any(m in path for m in _BH_LOCALE_MARKERS):
        return False
    # An explicit wrong-GCC-locale segment (xx-yy form) → drop.
    if any(seg in path for seg in _WRONG_GCC_LOCALE_SEGMENTS):
        return True
    # Genuine-BH bundle D8 — a wrong-REGION bare-path segment (noon's
    # `/egypt-en/`, `/saudi-en/`, `/cairo/`, …) → drop.
    return any(seg in path for seg in _WRONG_REGION_PATH_SEGMENTS)


# Genuine-BH bundle D8 (2026-06-15) — PDP signals vs listing/search signals for
# the render-wave candidate filter. A render scrape only pays off on a
# product-detail page (one price). A category/search/listing page (no single
# price) wastes a Firecrawl/Scrape.do credit + can mis-attribute a "from" price.
# `_PDP_PATH_MARKERS` mirrors `_is_pdp_link` in structured_comparison_service +
# adds Shopify (`/products/<handle>`) and a couple of common BH PDP shapes.
_PDP_PATH_MARKERS = ("/product/", "/products/", "/p/", "/item/", "/dp/", "/buy/")
# Explicit listing/search/category markers — present ⇒ NOT a PDP. HIGH-CONFIDENCE
# ONLY: every entry here must be unambiguous so a real PDP is never dropped.
# DELIBERATELY EXCLUDED (false-positive prone on official brand sites — tier15
# regression 2026-06-15): `/shop/` and `/store/` (Apple PDPs live at
# `apple.com/shop/<product>`; Microsoft Store PDPs at `/store/`), `/s/` `/sr`
# (too short, substring-collide), `/sale` `/deals` `/offers` `/all-` `/list`
# `/brand(s)/` (collide inside product slugs like `/wholesale-`, `/stylist-`).
# The remaining set still drops the genuine category/search/collection surfaces.
_LISTING_PATH_MARKERS = (
    "/c/", "/category/", "/categories/", "/cat/",
    "/search",                           # search result pages
    "/collections/", "/collection/",     # Shopify collection (NOT /products/)
)
# Query params that mark a search/listing surface even on a PDP-looking path.
_LISTING_QUERY_MARKERS = ("q=", "search=", "query=", "keyword=", "page=")


def is_non_pdp_listing_url(url: str) -> bool:
    """True iff `url` is a category / search / listing surface rather than a
    product-detail page — so the render wave should DROP it (no single price to
    extract; a render credit would be wasted / a "from N" listing price could
    mis-attribute).

    Conservative: a URL with an explicit PDP marker (`/product/`, `/products/`,
    Shopify `/products/<handle>`, …) is KEPT even if a listing-ish token co-occurs
    (PDP signal wins). A URL with NO PDP marker AND an explicit listing/search
    marker (path or query) → drop. A locale-neutral, marker-free URL (e.g. a bare
    brand homepage or an unknown slug) is KEPT — never drop a maybe-PDP.
    """
    if not url:
        return False
    try:
        parsed = urlparse(url)
    except (ValueError, TypeError):
        return False
    path = (parsed.path or "").lower()
    query = (parsed.query or "").lower()
    # An explicit PDP marker wins — keep.
    if any(m in path for m in _PDP_PATH_MARKERS):
        return False
    # No PDP marker: an explicit listing/search marker (path or query) → drop.
    if any(m in path for m in _LISTING_PATH_MARKERS):
        return True
    if any(m in query for m in _LISTING_QUERY_MARKERS):
        return True
    return False


# S3 Lulu BH-locale (live-verified 2026-06-14) — retailers that use an IDENTICAL
# product slug across GCC locales, so a wrong-locale URL can be REWRITTEN to
# /en-bh/ to hit the genuine BH PDP (instead of being dropped). ALLOW-SET only
# (Decision-F): Lulu confirmed (Nutella 3.34 / Maybelline 7.825 / H&S 1.59 /
# Centrum 12.09 BHD via /en-bh/ rewrite). sharafdg/extra are NOT here — their
# SKU IDs differ per locale, so a rewrite would 404 / mis-attribute.
_BH_LOCALE_REWRITE_DOMAINS = ("luluhypermarket.com",)
# (en|ar)-(wrong GCC) locale segment, captured for substitution.
_LOCALE_SEG_RE = re.compile(r"/(?:en|ar)-(?:sa|ae|om|kw|qa)/", re.IGNORECASE)


def rewrite_to_bh_locale(url: str) -> Optional[str]:
    """For an ALLOW-SET same-slug retailer (Lulu), rewrite a wrong-GCC-locale
    path segment to `/en-bh/` and return the rewritten URL; else return None.

    None when: not an allow-set domain, already /en-bh/, or no locale segment to
    rewrite. The caller adds the rewritten URL to the BH scrape pool — the BH
    store serves the same slug in BHD (page_scrape), unlocking grocery/makeup/
    haircare/supplements from one source.
    """
    if not url:
        return None
    try:
        parsed = urlparse(url)
    except (ValueError, TypeError):
        return None
    host = _normalize_domain(parsed.netloc or "")
    if not host:
        return None
    if not any(host == d or host.endswith("." + d) for d in _BH_LOCALE_REWRITE_DOMAINS):
        return None
    # Already BH → nothing to do.
    if any(m in (parsed.path or "").lower() for m in _BH_LOCALE_MARKERS):
        return None
    rewritten, n = _LOCALE_SEG_RE.subn("/en-bh/", url)
    if n == 0:
        return None
    return rewritten


def is_render_only_domain(domain_or_url: str) -> bool:
    """True iff `domain_or_url` resolves to a registry Source marked
    is_render_only (a JS-SPA whose static curl yields no price). The Approach-A
    curl wave SKIPS these (a curl is wasted) and the render wave INCLUDES them.
    Accepts a bare domain or a full URL."""
    if not domain_or_url:
        return False
    host = domain_or_url
    if "://" in domain_or_url or "/" in domain_or_url:
        try:
            host = urlparse(
                domain_or_url if "://" in domain_or_url else "//" + domain_or_url
            ).netloc or domain_or_url
        except (ValueError, TypeError):
            host = domain_or_url
    host = host.replace("www.", "").lower()
    for s in SOURCE_REGISTRY:
        if not getattr(s, "is_render_only", False):
            continue
        d = s.domain.replace("www.", "").lower()
        if host == d or host.endswith("." + d) or d.endswith("." + host):
            return True
    return False


def build_site_discovery_query(
    product_query: str, category: str, tier: str = "bahrain", limit: int = 4
) -> str:
    """Serper query targeting registry sources of one tier for a category.

    Returns '<query> site:a OR site:b ...' — empty string when the tier has
    no sources for the category (the caller then skips the discovery call).
    Domains preserve registry order (Bahrain-first within the tier).

    S2 I2.5 — only price-usable sources are queried (review-only domains have
    no prices, so including them is pure scrape-budget burn).
    """
    domains = [
        s.domain
        for s in get_sources_for_category(category, usage="price")
        if s.tier == tier
    ][:limit]
    if not domains:
        return ""
    return f"{product_query} " + " OR ".join(f"site:{d}" for d in domains)
