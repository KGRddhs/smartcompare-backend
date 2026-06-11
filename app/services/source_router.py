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
from typing import List, Tuple
from urllib.parse import urlparse


@dataclass(frozen=True)
class Source:
    domain: str
    tier: str  # "bahrain" | "gcc" | "global"
    categories: Tuple[str, ...]  # empty tuple = all categories
    weight: float


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
    Source("spinneysbahrain.com", "bahrain", ("grocery",), 3.0),
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
        "shopalmoayyed.com", "bahrain", ("electronics",), 3.0
    ),  # Y.K. Almoayyed & Sons (Shopify) — AC/appliances/electronics
    Source(
        "bh.asgharali.com", "bahrain", ("fragrances",), 3.0
    ),  # Asgharali Perfumes BH (Shopify)
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


def get_sources_for_category(category: str) -> List[Source]:
    """Return sources ordered by tier (bahrain -> gcc -> global), filtered by category.

    A source with empty `categories` matches every category. Otherwise the
    category must appear in the tuple.
    """
    result: List[Source] = []
    for tier in _TIER_ORDER:
        for s in SOURCE_REGISTRY:
            if s.tier != tier:
                continue
            if s.categories and category not in s.categories:
                continue
            result.append(s)
    return result


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
    """
    domains = [
        s.domain for s in get_sources_for_category(category) if s.tier == tier
    ][:limit]
    if not domains:
        return ""
    return f"{product_query} " + " OR ".join(f"site:{d}" for d in domains)
