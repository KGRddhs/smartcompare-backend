"""Bahrain-first source registry + URL scoring.

Lane 2 (Backend Comparison Engine Overhaul). Replaces the per-tier hard-coded
`OFFICIAL_BRAND_DOMAINS` / `AUTHORIZED_LUXURY_RETAILERS` / `GCC_LUXURY_RETAILERS`
sets with a single weighted registry. Bahrain retailers score x3.0, GCC x1.5,
global x1.0 — feeds into Tier 1 source consolidation + the page-scrape
escalation cascade.

Source weighting drives the cross-validation in `confidence_service.py` so
mismatched Tier-1 Bahrain prices outvote a distant amazon.com listing.
"""

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


SOURCE_REGISTRY: List[Source] = [
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
    Source("luluhypermarket.com", "bahrain", (), 3.0),
    Source("bahrain.sharafdg.com", "bahrain", ("electronics",), 3.0),
    Source("extra.com", "bahrain", ("electronics",), 3.0),
    Source(
        "bn.boots.com",
        "bahrain",
        ("supplements", "skincare", "makeup", "haircare"),
        3.0,
    ),
    Source("bolo.bh", "bahrain", ("supplements", "makeup", "skincare"), 3.0),
    Source("behbehani.com", "bahrain", ("electronics", "fashion"), 3.0),
    # I5.3 — eroselectronics.com DELETED (NXDOMAIN 2026-06-11; no live BH
    # replacement). behbehani.com + jumboelectronics.com verified alive (200), kept.
    Source("jumboelectronics.com", "bahrain", ("electronics",), 3.0),
    Source("talabat.com", "bahrain", ("grocery",), 3.0),
    # spinneysbahrain.com DELETED (I5.11 liveness gate 2026-06-12): NXDOMAIN;
    # spinneys.com live but no Bahrain storefront evidence (Decision F: never
    # fabricate). Re-add when a verified Bahrain-serving domain exists (S3).
    Source("megamart.bh", "bahrain", ("grocery",), 3.0),
    # F1.5 expansion (verified live 2026-06-10) — Bahrain grocery + pharmacy
    # gaps. RATIFICATION REQUIRED (F1.5 checkpoint) before merge.
    Source("alosraonline.com", "bahrain", ("grocery",), 3.0),  # Alosra (BMMI)
    Source(
        "nasserpharmacy.com",
        "bahrain",
        ("supplements", "skincare", "makeup", "haircare", "fragrances"),
        3.0,
    ),  # Nasser Pharmacy — Bahrain's largest chain, 10k+ health/beauty SKUs
    Source(
        "bahrainpharmacy.com",
        "bahrain",
        ("supplements", "skincare", "makeup", "haircare"),
        3.0,
    ),  # Bahrain Pharmacy & General Store
    # F1.5 addendum (deeper verified-source discovery, live 2026-06-10) —
    # appliance/AC + fragrance + premium-grocery gap-fillers. Each is a real
    # BH e-commerce site with BHD prices + checkout + product pages.
    Source(
        "shopalmoayyed.com", "bahrain", ("electronics",), 3.0, is_shopify=True
    ),  # Y.K. Almoayyed & Sons (Shopify) — AC/appliances/electronics. S3 L1.3:
    #    /products.json verified — 30 products, static BHD JSON-LD (page_scrape).
    Source(
        "bh.asgharali.com", "bahrain", ("fragrances",), 3.0, is_shopify=True
    ),  # Asgharali Perfumes BH (Shopify). S3 L1.3: /products.json verified —
    #    93 products, static BHD prices.
    Source(
        "jalilaperfumes.com", "bahrain", ("fragrances",), 3.0
    ),  # Jalila Perfumes BH (custom PHP, product pages + BHD)
    Source(
        "bateel.bh", "bahrain", ("grocery",), 3.0
    ),  # Bateel BH — premium dates / gourmet

    # === GCC SECONDARY (weight 1.5) ===
    Source("noon.com", "gcc", (), 1.5),
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


def _usage_allows(source_usage_value: str, wanted: str) -> bool:
    """True when a source of `source_usage_value` may serve `wanted`.

    "both" serves either; "price"/"review" serve only their own kind.
    """
    if source_usage_value == "both":
        return True
    return source_usage_value == wanted


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
    """
    result: List[Source] = []
    for tier in _TIER_ORDER:
        for s in SOURCE_REGISTRY:
            if s.tier != tier:
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
