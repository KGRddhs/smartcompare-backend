"""Sitemap DISCOVERY channel — Wave 2 (BH Source-Intelligence, 2026-06-23).

The regional BH storefronts whose discovery mechanism is ``mechanism="sitemap"``
(bolo.bh today; boutiqaat.com conditional) have NO clean public JSON search API
(Finders 2+3 probed: bolo ``/api/v1/*`` → 500, boutiqaat ``searchplus/rest`` →
404). Their OWN products-sitemap IS the name→PDP-URL resolver.

ARCHITECTURE (3 pieces) — a BOUNDED token-bucket INVERTED INDEX (Codex HIGH-2):
  1. ``build_sitemap_index(domain, ...)`` — an OFF-CLOCK builder: fetch the
     source's sitemap-INDEX → its child sitemaps → extract every ``/products/``
     ``<loc>`` PDP URL → build the ``{normalized_slug → pdp_url}`` map → then
     BUCKET it: for every slug token, append ``[slug, url]`` to that token's
     bucket and store each non-empty bucket under
     ``discovery:sitemap:{domain}:t:{token}`` (24h TTL). A small META key
     ``discovery:sitemap:{domain}:meta`` records the build. Each bucket is capped
     at ``_BUCKET_CAP`` entries (a too-common token is a poor lookup key — a rarer
     co-token in any real query covers the match).
  2. ``_match_sitemap_slug(slug_index, query)`` — a PURE per-query matcher
     reusing the price_service title helpers (``normalize_words`` /
     ``numbers_match`` / ``variant_mismatch`` + an ml-size guard): query tokens ⊆
     slug tokens, numbers match, variant/size guard does not fire → best PDP URL.
     It runs over a SMALL candidate dict (one token's bucket, ≤ ``_BUCKET_CAP``),
     NEVER the full catalog.
  3. ``resolve_pdp_via_sitemap(domain, query)`` — the REQUEST-PATH lookup: read
     META → pick up to ``_MAX_BUCKET_PROBES`` distinctive query tokens (longest
     first, rarity proxy) → fetch each token's small bucket → run the matcher on
     it → first non-None match wins. NO live fetch on the clock, NO full-catalog
     read. On a cold/missing index → graceful None (the cascade continues → honest
     pending, NEVER a fabricated price). Do NOT crawl on a miss.

🔒 BOUNDED REQUEST WORK (Codex HIGH-2, 336k-entry benchmark) — the OLD layout
stored the ENTIRE {slug→url} catalog in ONE Redis JSON value and the request path
read + scanned ALL of it per call (336k entries = 45.93 MiB transfer + 2.375s CPU
— it blocked the event loop on the 15s clock). The token-bucket layout bounds
each request to ≤ ``_MAX_BUCKET_PROBES`` small (≤ ``_BUCKET_CAP``-entry) bucket
fetches + matches. That 45MB / 2.4s full-catalog path is GONE.

🚨 OFF-CLOCK ONLY — the builder is the ONLY thing that fetches a sitemap, and it
is called EXCLUSIVELY from ``scripts/cron_index_sitemaps.py`` (the off-clock
index cron), NEVER from the 15s request path. The sitemaps are huge (bolo = 16
children × ~21k = ~336k URLs / ~20MB; boutiqaat = 27MB + 20MB). The request path
only ever calls ``resolve_pdp_via_sitemap`` / ``_match_sitemap_slug``, which read
small pre-built Redis buckets and run a pure matcher — zero network.

NO-FABRICATION: a discovery miss returns None (resolver) or the honest
``sitemap_no_match_price()`` sentinel, which ``price_service.should_negative_cache``
EXEMPTS from the 30d negative cache (exempt-like ``converted_usd`` / SF-1) so a
later index refresh can upgrade the product to a genuine ``page_scrape_jsonld``
price. This module ships NO genuine-set / cascade change — it is discovery-only,
consumed by the Wave-3 adapters.
"""

from __future__ import annotations

import logging
import os
import re
import time
from typing import Awaitable, Callable, Dict, List, Optional, Sequence, Union
from urllib.parse import urlparse
from xml.etree import ElementTree as ET

from app.services.cache_service import get_cached, set_cached
from app.services.price_service import (
    extract_sizes_ml,
    normalize_words,
    numbers_match,
    variant_mismatch,
)

logger = logging.getLogger(__name__)

# Redis key templates for the per-domain token-bucket inverted index.
#   meta    : discovery:sitemap:{domain}:meta   → {built_at, pdp_count, bucket_count}
#   bucket  : discovery:sitemap:{domain}:t:{token} → [[slug, url], ...]  (≤ _BUCKET_CAP)
_META_KEY = "discovery:sitemap:{domain}:meta"
_BUCKET_KEY = "discovery:sitemap:{domain}:t:{token}"
# 24h — the bolo sitemap declares <changefreq>daily</changefreq>; the Shopify
# catalog precedent is 6h, but a product-sitemap turns over far slower than a
# storefront catalog, so a day is safe and keeps the heavy off-clock build rare.
_SITEMAP_INDEX_TTL = 24 * 3600

# Cap per-token bucket size. A token whose bucket would exceed this is a poor
# lookup key (too common — its bucket isn't distinctive), and a rarer co-token in
# any real product query covers the match anyway. Bounds request-path work to
# ≤ _MAX_BUCKET_PROBES × _BUCKET_CAP matcher iterations (vs 336k full-catalog).
_BUCKET_CAP = 4000

# How many distinctive query tokens the request path probes before giving up. The
# matcher requires EVERY query token ⊆ the slug, so a SINGLE token's bucket is
# sufficient to FIND the correct PDP; probing a few distinctive tokens just covers
# the case where the first token's bucket hit the cap (and so dropped the slug).
_MAX_BUCKET_PROBES = 3

# A PDP loc is a /products/{id}-{slug} (bolo) or /.../{slug}-{id}/p/ (boutiqaat)
# URL. Listing / collection / brand / category locs are NOT products and are
# excluded so the index stays a pure name→PDP map.
_PDP_PATH_MARKERS = ("/products/", "/p/")
_NON_PDP_MARKERS = ("/collections/", "/categories/", "/brands/", "/category/")

# --- ENABLE_SITEMAP_PDP_MARKERS_V2 recognizer (M6 C2) ----------------------
# The shipped markers see only Shopify /products/ and the bolo/boutiqaat /p/, so
# WooCommerce /product/ (singular), Magento <slug>.html, and the Salla
# /{slug}/p{id} shape index ZERO real PDPs (M5: 5/12 hosts), while reef's
# /p/{static-page} CONTENT pages get indexed as false PDPs. V2 generalizes
# recognition. Default OFF — it changes what the OFF-CLOCK builder indexes (a new
# capability), and the whole sitemap channel is already gated by
# ENABLE_SITEMAP_INDEX; flag-OFF is byte-identical to the shipped recognition.

# WooCommerce singular product marker. Distinct from the Shopify /products/
# marker: "/products/" contains the substring "/product" but NOT "/product/"
# (the char after "product" is "s", not "/"), so the two never collide.
_WOO_PDP_MARKER = "/product/"

# Salla PDP shape: /{slug}/p{numeric-id} — the FINAL path segment is p<digits>
# (reef: /en/reef-33/p1243364177). The shipped /p/ marker does not match it (no
# slash after the p), and reef's /p/{static} content pages wrongly do.
_SALLA_PDP_RE = re.compile(r"/p\d+/?$")

# Magento PDP heuristic: a .html (or .htm) leaf that is NOT a known non-PDP path
# (klinq: /en/dior-miss-dior-edp.html). Deliberately permissive per M5 — the
# whole channel is gated OFF and a few category .html over-inclusions add only
# bucket noise the matcher never resolves to a real product query.
_HTML_LEAF_RE = re.compile(r"\.html?$")

# Curated content-page stoplist for the /p/{static-page} class. Salla and similar
# platforms serve CMS pages under /p/{about|locations|...}; these match the broad
# /p/ marker but are NOT products. A curated list (NOT a general "/p/ + non-digit"
# rule) so genuine /p/ PDPs (bolo/boutiqaat, where p is the TRAILING segment) are
# never over-excluded.
_P_CONTENT_STOPWORDS = frozenset(
    {
        "about",
        "about-us",
        "aboutus",
        "contact",
        "contact-us",
        "contactus",
        "locations",
        "location",
        "stores",
        "store",
        "branches",
        "terms",
        "terms-and-conditions",
        "terms-conditions",
        "privacy",
        "privacy-policy",
        "policy",
        "policies",
        "faq",
        "faqs",
        "shipping",
        "shipping-policy",
        "returns",
        "return-policy",
        "refund",
        "refund-policy",
        "delivery",
        "blog",
        "news",
        "careers",
        "jobs",
        "sitemap",
        "help",
        "support",
        "wholesale",
        "franchise",
        "sales-wholesale-franchise",
        "warranty",
        "loyalty",
        "rewards",
        "gift-card",
        "gift-cards",
    }
)

# Sitemaps namespace the elements: {http://www.sitemaps.org/schemas/sitemap/0.9}.
# Strip any namespace so the tag-name checks are robust to the xmlns.
_NS_RE = re.compile(r"\{[^}]*\}")

# A token must sanitize to a Redis-key-safe string. Strip anything outside
# [a-z0-9]; a token that is empty / <2 chars / pure-numeric after sanitization is
# NOT used as a bucket KEY (it still lives inside slugs for matching — matching is
# by _match_sitemap_slug on the candidate set, not by the bucket key).
_TOKEN_KEY_RE = re.compile(r"[^a-z0-9]")


def _norm_domain(domain: str) -> str:
    return (domain or "").replace("www.", "").strip().lower()


def _meta_key(domain: str) -> str:
    return _META_KEY.format(domain=_norm_domain(domain))


def _sanitize_token_key(token: str) -> str:
    """Stable Redis-key-safe token. ``""`` when the token is unusable as a bucket
    key (empty / <2 chars / pure-numeric after stripping non-[a-z0-9])."""
    safe = _TOKEN_KEY_RE.sub("", (token or "").lower())
    if len(safe) < 2 or safe.isdigit():
        return ""
    return safe


def _bucket_key(domain: str, sanitized_token: str) -> str:
    return _BUCKET_KEY.format(domain=_norm_domain(domain), token=sanitized_token)


def _local_tag(elem) -> str:
    return _NS_RE.sub("", elem.tag).lower()


def _iter_locs(xml_text: str):
    """Yield every ``<loc>`` text in a sitemap-index or urlset, namespace-robust.

    Tolerant of malformed XML: a parse failure yields nothing (the builder logs
    and moves on — a broken child sitemap must never crash the off-clock run)."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:  # noqa: BLE001 — best-effort off-clock parse
        logger.warning("[sitemap_discovery] XML parse failed: %s", exc)
        return
    for elem in root.iter():
        if _local_tag(elem) == "loc":
            text = (elem.text or "").strip()
            if text:
                yield text


def pdp_markers_v2_enabled() -> bool:
    """True iff the generalized builder PDP-URL recognizer is active (default OFF).

    Read PER CALL from ``os.getenv`` (copying ``price_service.exact_gate_enabled``);
    flag-OFF ``_is_pdp_url`` is byte-identical to the shipped Shopify + ``/p/``
    recognition. Scoped to the OFF-CLOCK builder path — it only changes what
    ``build_sitemap_index`` indexes; the whole sitemap channel is separately gated
    by ``ENABLE_SITEMAP_INDEX``."""
    return os.getenv("ENABLE_SITEMAP_PDP_MARKERS_V2", "").strip().lower() in (
        "true",
        "1",
        "yes",
        "on",
    )


def _is_p_content_page(segments: List[str]) -> bool:
    """True iff a path is a ``/p/{static-page}`` CMS page (a ``p`` segment followed
    by a curated stoplist word — reef ``/en/p/about``). A genuine ``/p/`` PDP keeps
    ``p`` as the TRAILING segment (boutiqaat ``…/{slug}/p/``), so it is never here
    (``p`` is not in ``segments[:-1]``) and is not over-excluded."""
    for i, seg in enumerate(segments[:-1]):
        if seg == "p" and segments[i + 1] in _P_CONTENT_STOPWORDS:
            return True
    return False


def _is_pdp_url_v2(low_url: str) -> bool:
    """Generalized PDP recognition (``ENABLE_SITEMAP_PDP_MARKERS_V2``). ``low_url``
    is already lowercased and already passed the ``_NON_PDP_MARKERS`` exclusion.

    Recognizes Shopify ``/products/`` + boutiqaat trailing ``/p/`` (shipped),
    WooCommerce ``/product/`` (singular), the Salla ``/{slug}/p{id}`` shape, and a
    Magento ``.html`` leaf. EXCLUDES the ``/p/{static-page}`` content class."""
    path = urlparse(low_url).path
    segments = [s for s in path.split("/") if s]
    if not segments:
        return False
    # EXCLUDE the /p/{static-page} content class first — it would otherwise match
    # the broad /p/ marker (the measured reef false-PDP bug).
    if _is_p_content_page(segments):
        return False
    # Shipped markers: Shopify /products/ and boutiqaat trailing /p/.
    if any(m in low_url for m in _PDP_PATH_MARKERS):
        return True
    # WooCommerce singular /product/.
    if _WOO_PDP_MARKER in low_url:
        return True
    # Salla /{slug}/p{numeric-id}.
    if _SALLA_PDP_RE.search(path):
        return True
    # Magento <slug>.html leaf (heuristic — non-PDP paths already excluded above).
    if _HTML_LEAF_RE.search(path):
        return True
    return False


def _is_pdp_url(url: str) -> bool:
    low = url.lower()
    if any(m in low for m in _NON_PDP_MARKERS):
        return False
    if pdp_markers_v2_enabled():
        return _is_pdp_url_v2(low)
    return any(m in low for m in _PDP_PATH_MARKERS)


def _bare_host(host_or_url: str) -> str:
    """The registrable host (leading ``www.`` stripped, lowercased) of a URL or a
    raw host string. ``""`` when unparseable."""
    try:
        netloc = urlparse(host_or_url).netloc or (host_or_url or "")
    except (ValueError, TypeError):
        return ""
    h = netloc.strip().lower()
    return h[4:] if h.startswith("www.") else h


def _same_site(url: str, expected_bare: str) -> bool:
    """True iff ``url``'s host is the expected registrable domain or a subdomain of
    it.

    🔒 SSRF GUARD (source-intel review 2026-06-23) — the ONLY trust boundary on a
    sitemap ``<loc>`` / child-sitemap URL. ``build_sitemap_index`` stores PDP URLs
    that the request path later hands to ``curl_fetch_html`` (which has NO host
    allowlist and follows redirects). Without this bind, a poisoned / MITM'd
    sitemap ``<loc>`` to an arbitrary host (a private IP, ``*.railway.internal``, a
    cloud metadata endpoint) would be indexed in Redis and then fetched on the
    clock. Binding at the WRITE keeps the index a pure same-domain map, so the
    request path can never resolve an off-domain URL. ``notbolo.bh`` /
    ``bolo.bh.evil.com`` correctly do NOT match ``bolo.bh``."""
    if not expected_bare:
        return False
    try:
        host = urlparse(url).netloc.strip().lower()
    except (ValueError, TypeError):
        return False
    if not host:
        return False
    if host.startswith("www."):
        host = host[4:]
    return host == expected_bare or host.endswith("." + expected_bare)


def _slug_from_pdp(url: str) -> str:
    """The human, matchable slug text from a PDP URL.

    bolo: /products/UO07CAPPYQ2-cerave-vitamin-c-serum-...  → the slug after the
    leading id token (a UO-prefixed alnum id). boutiqaat: /.../{slug}-{id}/p/ →
    the path segment before /p/. Hyphens become spaces so the title helpers
    tokenize it. We KEEP the leading id on bolo only as a fallback (the
    normalize_words tokenizer drops the id token's overlap weight naturally — it
    never appears in a product query)."""
    path = urlparse(url).path.strip("/")
    segments = [s for s in path.split("/") if s]
    if not segments:
        return ""
    # boutiqaat ends in /p/ → the slug is the segment before it.
    if segments[-1].lower() == "p" and len(segments) >= 2:
        slug = segments[-2]
    else:
        slug = segments[-1]
    # bolo prefixes a {internal_id}- token; drop a leading alnum id of >=6 chars
    # that carries no English letters-after-digits product signal. Conservative:
    # only strip when the first hyphen group is a UO-style id (all upper alnum,
    # contains a digit). Otherwise keep the whole slug.
    head, _, tail = slug.partition("-")
    if tail and re.fullmatch(r"[A-Z0-9]{6,}", head) and any(c.isdigit() for c in head):
        slug = tail
    return slug.replace("-", " ")


async def _collect_slugs_for_index(
    domain: str,
    index_url: str,
    fetch: Callable[[str], Awaitable[Optional[str]]],
    max_children: int,
) -> Dict[str, str]:
    """Fetch + validate ONE sitemap-index ``index_url`` → its ``{slug → pdp_url}``
    map. Each index derives its OWN ``_expected_site`` and applies the per-index
    SSRF ``_same_site`` guard against THAT host (so a 2-URL build can't smuggle a
    cross-host loc through the other index's expected domain). Graceful-empty on
    any failure (a missing / malformed index or child is skipped). Never raises."""
    index_xml = await fetch(index_url)
    if not index_xml:
        logger.info("[sitemap_discovery] %s: index fetch empty (%s)", domain, index_url)
        return {}

    # 🔒 SSRF guard — only trust <loc>/child URLs on THIS index's OWN registrable
    # domain (derived from index_url). A poisoned/MITM'd sitemap <loc> to an
    # arbitrary host would otherwise be indexed + later curl-fetched on the request
    # path (curl_fetch_html has no host allowlist + follows redirects). Bind at the
    # WRITE so the request path can never resolve an off-domain URL.
    _expected_site = _bare_host(index_url) or _bare_host(domain)
    locs = list(_iter_locs(index_xml))
    # A sitemap-INDEX's <loc>s point to child sitemaps (.xml); a flat urlset's
    # <loc>s are PDP URLs directly. Distinguish by the presence of any PDP loc.
    child_sitemaps = [
        u for u in locs
        if u.lower().endswith(".xml") and _same_site(u, _expected_site)
    ]
    inline_pdps = [
        u for u in locs if _is_pdp_url(u) and _same_site(u, _expected_site)
    ]

    slug_index: Dict[str, str] = {}

    if inline_pdps and not child_sitemaps:
        # index_url was itself a flat product urlset.
        for url in inline_pdps:
            slug = _slug_from_pdp(url)
            if slug:
                slug_index[slug] = url
    else:
        for child_url in child_sitemaps[:max_children]:
            child_xml = await fetch(child_url)
            if not child_xml:
                logger.info("[sitemap_discovery] %s: child empty (%s)", domain, child_url)
                continue
            for url in _iter_locs(child_xml):
                if not _is_pdp_url(url):
                    continue
                if not _same_site(url, _expected_site):
                    continue  # 🔒 SSRF guard — off-domain PDP loc
                slug = _slug_from_pdp(url)
                if slug:
                    slug_index[slug] = url
    return slug_index


async def build_sitemap_index(
    domain: str,
    *,
    index_url: Union[str, Sequence[str]],
    fetch: Optional[Callable[[str], Awaitable[Optional[str]]]] = None,
    max_children: int = 32,
) -> int:
    """OFF-CLOCK ONLY. Build + Redis-cache a BOUNDED token-bucket inverted index of
    the ``{normalized_slug → pdp_url}`` map for ``domain`` from its sitemap-index
    at ``index_url``.

    ``index_url`` may be a single URL (str) OR a sequence of URLs (e.g. a store
    that splits its catalog across several locale/section index files — boutiqaat
    serves women + men under separate ``/en-bh/{section}/sitemap.xml`` files). For
    a sequence, EACH index is fetched + validated independently (its OWN
    ``_expected_site`` + per-index SSRF guard), and their validated ``{slug → url}``
    maps are UNIONed BEFORE bucketing — the catalog is then bucketed + persisted +
    META-written ONCE (a single write, exactly as a str index_url). A str keeps the
    exact current behavior.

    🚨 Called EXCLUSIVELY from ``scripts/cron_index_sitemaps.py`` — NEVER from the
    request path (the sitemaps are 20MB+). ``fetch`` is an injectable async
    HTML/XML fetcher (the cron supplies a curl_cffi fetcher; tests inject a
    recorded-fixture fetcher) so this stays free-tier + offline-testable.

    Layout (Codex HIGH-2): for every (slug, url), for every token in
    ``normalize_words(slug)``, append ``[slug, url]`` to that token's bucket (capped
    at ``_BUCKET_CAP``). Each non-empty bucket → ``discovery:sitemap:{domain}:t:{token}``;
    a META key → ``discovery:sitemap:{domain}:meta``. The request path reads small
    buckets, never the full catalog.

    Returns the number of PDP URLs actually indexed (0 on a totally-failed build OR
    a failed META write — MED-4: no phantom success count). Graceful on every
    failure (a missing / malformed child sitemap is skipped). Never raises.
    """
    fetch = fetch or _default_fetch

    # Normalize to a list of index URLs. A str keeps the exact current behavior;
    # a sequence fetches + validates EACH index independently, then UNIONs the
    # validated {slug → url} maps before the single bucket+persist+meta write.
    index_urls: List[str] = (
        [index_url] if isinstance(index_url, str) else [u for u in index_url if u]
    )

    slug_index: Dict[str, str] = {}
    for one_index_url in index_urls:
        partial = await _collect_slugs_for_index(
            domain, one_index_url, fetch, max_children
        )
        # UNION across indexes (a later index's slug wins on a collision — same
        # last-writer semantics as the within-index dict assignment).
        slug_index.update(partial)

    if not slug_index:
        logger.info("[sitemap_discovery] %s: 0 PDPs indexed — not caching", domain)
        return 0

    # --- Build the token-bucket inverted index over the small slug→url map. ---
    buckets: Dict[str, List[List[str]]] = {}
    for slug, url in slug_index.items():
        for token in normalize_words(slug):
            tkey = _sanitize_token_key(token)
            if not tkey:
                continue  # unusable as a bucket key (empty / <2 chars / numeric)
            bucket = buckets.get(tkey)
            if bucket is None:
                bucket = buckets[tkey] = []
            if len(bucket) >= _BUCKET_CAP:
                continue  # cap a too-common token — a rarer co-token covers it
            bucket.append([slug, url])

    if not buckets:
        logger.info("[sitemap_discovery] %s: 0 usable bucket tokens — not caching", domain)
        return 0

    # Persist each bucket; count only buckets that actually persisted (MED-4).
    persisted = 0
    for tkey, bucket in buckets.items():
        try:
            if set_cached(_bucket_key(domain, tkey), bucket, _SITEMAP_INDEX_TTL):
                persisted += 1
            else:
                logger.warning(
                    "[sitemap_discovery] %s: bucket write returned False (token=%s)",
                    domain, tkey,
                )
        except Exception as exc:  # noqa: BLE001 — one bad write must not abort the build
            logger.warning(
                "[sitemap_discovery] %s: bucket write failed (token=%s): %s",
                domain, tkey, exc,
            )

    if persisted == 0:
        # MED-4 (review NIT): every bucket write failed → the index has NO
        # request-path-readable bucket even if the META write would succeed. Report
        # an HONEST 0 (no phantom success), same posture as a failed META write.
        logger.warning(
            "[sitemap_discovery] %s: 0/%d buckets persisted — reporting 0 (index unusable)",
            domain, len(buckets),
        )
        return 0

    pdp_count = len(slug_index)
    meta = {
        "built_at": int(time.time()),
        "pdp_count": pdp_count,
        "bucket_count": persisted,
    }
    try:
        meta_ok = set_cached(_meta_key(domain), meta, _SITEMAP_INDEX_TTL)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[sitemap_discovery] %s: meta write failed: %s", domain, exc)
        meta_ok = False
    if not meta_ok:
        # MED-4: a failed META write means the index is unreadable on the request
        # path (resolve gates on meta) — report an HONEST 0, not a phantom success.
        logger.warning(
            "[sitemap_discovery] %s: META write failed — reporting 0 (index unusable)",
            domain,
        )
        return 0

    logger.info(
        "[sitemap_discovery] %s: indexed %d PDP slugs across %d token buckets "
        "(24h TTL, off-clock)",
        domain, pdp_count, persisted,
    )
    return pdp_count


async def _default_fetch(url: str) -> Optional[str]:
    """Default off-clock fetcher (curl_cffi, no JS render). ONLY used by the cron;
    tests inject a recorded-fixture fetcher. Graceful-None on any failure.

    🔒 SSRF GUARD (Codex HIGH-5, sitemap-crawl half) — the off-clock builder
    fetches the sitemap-INDEX + its child sitemaps with THIS fetcher. The generic
    ``curl_fetch_html`` follows redirects (``allow_redirects=True``) with NO
    per-hop host validation, so a poisoned / MITM'd sitemap-index that 30x-redirects
    to an arbitrary host / private IP / ``*.railway.internal`` / a cloud-metadata
    endpoint would be crawled by the cron (SSRF). We instead use the redirect-safe
    ``curl_fetch_html_same_site`` bound to the URL's OWN registrable domain
    (``_bare_host`` strips a leading ``www.``): it disables auto-redirect, validates
    the initial URL AND every redirect hop via ``url_validator.validate_external_url``
    (blocks private/loopback/link-local + non-http(s)) AND host-on-domain, and caps
    hops + body. The index_url + child sitemap URLs are all on the source's own
    domain (already ``_same_site``-validated as URLs at the WRITE), so binding each
    fetch to its own host's registrable domain is correct and blocks any off-domain
    / private redirect hop."""
    try:
        from app.services.price_service import curl_fetch_html_same_site
        return await curl_fetch_html_same_site(url, _bare_host(url))
    except Exception as exc:  # noqa: BLE001 — best-effort
        logger.warning("[sitemap_discovery] default fetch failed for %s: %s", url, exc)
        return None


# V2 overlap floor — the fraction of QUERY tokens that must appear in the slug once
# the strict ``issubset`` requirement is dropped. Higher than the shipped 0.5 floor
# so the relaxed matcher stays fail-closed: it tolerates a FEW extra brand/gender/
# size tokens the slug omits (M5: coral "Coral", myperfumes "Men", goldenscent
# "30 ml") but still rejects a genuinely-different product that only shares a generic
# token or two. Measured M5 "extra-token" recoveries sit at ~0.67 (4 of 6 words).
_SITEMAP_V2_MIN_OVERLAP = 0.6


def sitemap_match_v2_enabled() -> bool:
    """True iff the relaxed overlap-ratio SITEMAP matcher is active (default OFF).

    The shipped ``_match_sitemap_slug`` demands strict ``q_words.issubset(s_words)``
    — every query token present in the slug. Real JSON-LD ``Product.name`` values
    carry store/brand/gender/size tokens the URL slug omits, so a name-driven query
    is never a subset and the match is lost (M5: 92% of targets present, 8% matched).
    V2 relaxes the SITEMAP matcher ONLY (never the price identity gate) toward the
    word-overlap ratio it already computes, and drops phantom empty-string tokens
    LOCALLY (so the measured empty-token hits — tuzzut, samawa — recover regardless
    of ``ENABLE_NORMALIZE_WORDS_EMPTY_FIX``). The ``numbers_match`` / ``variant_
    mismatch`` / ml-size guards and the "return None, never a wrong URL" fail-closed
    property are preserved.

    Read PER CALL from ``os.getenv`` (copying ``exact_gate_enabled``); flag-OFF is
    byte-identical to the shipped strict matcher."""
    return os.getenv("ENABLE_SITEMAP_MATCH_V2", "").strip().lower() in (
        "true", "1", "yes", "on",
    )


def _match_sitemap_slug(
    slug_index: Optional[Dict[str, str]],
    query: str,
) -> Optional[str]:
    """PURE matcher: the best PDP URL in ``slug_index`` for ``query``, or None.

    ``slug_index`` is a SMALL candidate ``{slug: url}`` dict (one token's bucket,
    ≤ ``_BUCKET_CAP``) — never the full catalog. Reuses the price_service title
    helpers exactly like the Shopify matcher so it behaves consistently:
      - every significant query NUMBER must appear in the slug (``numbers_match``),
      - the query must NOT be a different model-line variant (``variant_mismatch``),
      - an ml-size in the QUERY must appear in the slug (size guard — the 50ml-vs-
        30ml case ``variant_mismatch`` doesn't cover for skincare/fragrance),
      - SHIPPED (V2 OFF): the query's normalized tokens must be a SUBSET of the slug
        tokens (every query word present), gated by a ≥0.5 word-overlap ratio,
      - RELAXED (``ENABLE_SITEMAP_MATCH_V2``): the strict subset requirement is
        dropped for a ≥``_SITEMAP_V2_MIN_OVERLAP`` word-overlap ratio (phantom empty
        tokens dropped locally), so a name with extra brand/gender/size tokens still
        resolves its own PDP while a genuinely-different product still returns None,
      - ties broken by the highest word-overlap (then shortest slug — the most
        specific exact match).

    Never raises. Empty / None index → None.
    """
    if not isinstance(slug_index, dict) or not slug_index:
        return None
    q = (query or "").strip()
    if not q:
        return None

    q_words = normalize_words(q)
    if not q_words:
        return None
    v2 = sitemap_match_v2_enabled()
    if v2:
        # Drop phantom empty-string tokens LOCALLY (independent of PART A's global
        # flag) so a spaced-hyphen name is not sunk before the overlap is computed.
        q_words = q_words - {""}
        if not q_words:
            return None
    q_sizes = extract_sizes_ml(q)

    best_url: Optional[str] = None
    best_rank = (-1.0, 10 ** 9)  # (overlap_ratio, -slug_len) → max overlap, then shortest

    for slug, url in slug_index.items():
        if not numbers_match(q, slug):
            continue
        if variant_mismatch(q, slug):
            continue
        # ml-size guard: if the query states a size, the slug must carry it.
        if q_sizes:
            slug_sizes = extract_sizes_ml(slug)
            if slug_sizes and not (q_sizes & slug_sizes):
                continue
        s_words = normalize_words(slug)
        if v2:
            # Relaxed: overlap-ratio only (no strict subset). The guards above +
            # this floor keep it fail-closed on a genuinely-different product.
            s_words = s_words - {""}
            overlap = len(q_words & s_words) / len(q_words)
            if overlap < _SITEMAP_V2_MIN_OVERLAP:
                continue
        else:
            # Query tokens must be a subset of the slug tokens (every query word
            # present in the slug) — the discovery match is name-driven.
            if not q_words.issubset(s_words):
                continue
            overlap = len(q_words & s_words) / len(q_words)
            if overlap < 0.5:
                continue
        rank = (overlap, -len(slug))
        if rank > best_rank:
            best_rank = rank
            best_url = url
    return best_url


def _ordered_probe_tokens(query: str) -> List[str]:
    """The order to probe token buckets for ``query``: significant tokens (>=3
    chars, NOT pure-numeric) sorted by LENGTH DESC (a rarity proxy — distinctive
    product words are long), then any remaining tokens. De-duped, sanitize-keyed."""
    words = normalize_words(query or "")
    if not words:
        return []
    significant = sorted(
        (w for w in words if len(w) >= 3 and not w.isdigit()),
        key=lambda w: (-len(w), w),
    )
    remaining = sorted(w for w in words if w not in significant)
    ordered: List[str] = []
    seen: set = set()
    for w in (*significant, *remaining):
        tkey = _sanitize_token_key(w)
        if tkey and tkey not in seen:
            seen.add(tkey)
            ordered.append(tkey)
    return ordered


def resolve_pdp_via_sitemap(domain: str, query: str) -> Optional[str]:
    """REQUEST-PATH lookup: read the pre-built Redis token-bucket index for
    ``domain`` and return the best-matching PDP URL for ``query``, or None.

    🚨 NO live fetch on the clock, NO full-catalog read — this reads the small META
    key + up to ``_MAX_BUCKET_PROBES`` small per-token buckets built off-clock by
    ``build_sitemap_index`` (via the cron). On a cold / missing index (flag OFF,
    first deploy, expired) → graceful None: the cascade continues to an honest
    pending, NEVER a fabricated price, and NO crawl is triggered.

    The matcher requires every query token ⊆ the slug, so a SINGLE token's bucket
    is sufficient to FIND the correct PDP; the first probed bucket that yields a
    non-None match wins.

    Never raises.
    """
    try:
        meta = get_cached(_meta_key(domain))
    except Exception as exc:  # noqa: BLE001 — fail-open like the rest of the cache
        logger.info("[sitemap_discovery] %s: meta read failed (%s)", domain, exc)
        return None
    if not meta:
        return None  # cold/missing index → None, no crawl

    probe_tokens = _ordered_probe_tokens(query)
    if not probe_tokens:
        return None

    for tkey in probe_tokens[:_MAX_BUCKET_PROBES]:
        try:
            bucket = get_cached(_bucket_key(domain, tkey))
        except Exception as exc:  # noqa: BLE001 — fail-open per-bucket
            logger.info("[sitemap_discovery] %s: bucket read failed (%s)", domain, exc)
            continue
        if not bucket:
            continue
        # Reconstruct a small {slug: url} candidate dict from the bucket list.
        candidate: Dict[str, str] = {}
        for entry in bucket:
            try:
                slug, url = entry[0], entry[1]
            except (TypeError, IndexError, ValueError):
                continue
            if slug and url:
                candidate[slug] = url
        match = _match_sitemap_slug(candidate, query)
        if match:
            return match
    return None


def _index_is_built(domain: str) -> bool:
    """Whether ``domain``'s token-bucket index exists (the META key is present). A
    downstream wave's cold-detection consumes this. Never raises."""
    try:
        return bool(get_cached(_meta_key(domain)))
    except Exception:  # noqa: BLE001 — fail-open: treat an unreadable index as cold
        return False


def _sitemap_index_cron_enabled() -> bool:
    """Fail-closed mirror of the cron's ENABLE_SITEMAP_INDEX flag (same truthy set
    as scripts/cron_index_sitemaps.py). When OFF, the off-clock index is never
    built, so a cold index is NOT a transient state."""
    return os.getenv("ENABLE_SITEMAP_INDEX", "").strip().lower() in (
        "true", "1", "yes", "on",
    )


def sitemap_discovery_is_cold(category: str) -> bool:
    """True iff at least one ``mechanism="sitemap"`` source applies to ``category``
    AND that source's index is NOT yet built (cron OFF / cold / TTL-expired).

    Consumed by the price cascade's Tier-3 negative-cache decision (Codex HIGH-3):
    while a category's sitemap index is cold, a Tier-3 GPT estimate is a TRANSIENT
    miss (the cron hasn't warmed the index yet — a later build resolves the PDP to a
    genuine price), so its negative cache TTL is capped to 24h instead of 30d. Once
    every applicable sitemap source's index is built, this returns False and the
    estimate is a structural dead-end (30d-cacheable).

    A FUNCTION-LEVEL import of ``get_sitemap_sources_for_category`` avoids a circular
    import (source_router has no dependency on this module, but the request-path
    caller — structured_comparison_service — imports both, and keeping the import
    lazy keeps this module standalone-importable). Never raises (False on any error
    — fail-toward-the-conservative 30d structural path, matching the prior behaviour
    before this guard existed)."""
    try:
        # Gate-fix (review NIT): the 24h transient cap only makes sense if the cron
        # WILL build the index. With ENABLE_SITEMAP_INDEX OFF (the default / ship
        # state) the index is NEVER built, so a cold-index estimate is a REAL
        # structural dead-end — treating it as transient would re-run the full
        # scrape cascade every 24h (vs 30d) for the entire structural-gap tail,
        # burning the finite Serper/Firecrawl/Scrape.do budget for no benefit (the
        # cron can't warm it). It is only "transiently" cold when the cron is on.
        if not _sitemap_index_cron_enabled():
            return False
        from app.services.source_router import get_sitemap_sources_for_category

        # get_sitemap_sources_for_category returns BOTH "sitemap" and "curl" rows;
        # only the "sitemap" mechanism participates in the off-clock index build, so
        # the cold-detection is scoped to those.
        sitemap_sources = [
            s
            for s in get_sitemap_sources_for_category(category)
            if getattr(s, "mechanism", "") == "sitemap"
        ]
        if not sitemap_sources:
            return False
        # Cold iff ANY applicable sitemap source still lacks a built index — that
        # source could resolve the product to a genuine price once warmed.
        return any(not _index_is_built(s.domain) for s in sitemap_sources)
    except Exception:  # noqa: BLE001 — never raise on the price hot path
        return False


def sitemap_unbuilt_domains(category: str) -> List[str]:
    """The ``mechanism="sitemap"`` source DOMAINS for ``category`` whose off-clock
    index is NOT yet built (cold / TTL-expired).

    RAW — NOT cron-gated (unlike ``sitemap_discovery_is_cold``): this answers the
    bare question "which genuine sitemap sources were unavailable when this price
    was resolved?", independent of whether the cron is currently enabled. It is
    consumed by the negative-cache READ-side invalidation (Codex re-review HIGH-3):
    the WRITE stamps these cold domains onto the cached estimate, and the READ later
    invalidates the sentinel the moment ANY stamped domain's index becomes built —
    even if the cron was OFF (and so ``sitemap_discovery_is_cold`` returned False,
    leaving a 30d TTL) at WRITE time. Without the raw signal, an estimate
    negcached-for-30d while the cron was cold would keep being served for up to 30
    days after the cron warms the index, and the genuine price would never resolve.

    A FUNCTION-LEVEL import of ``get_sitemap_sources_for_category`` avoids a circular
    import (same posture as ``sitemap_discovery_is_cold``). Never raises (returns []
    on any error — fail-toward-no-stamp, i.e. the prior 30d-structural behaviour).
    """
    try:
        from app.services.source_router import get_sitemap_sources_for_category

        # get_sitemap_sources_for_category returns BOTH "sitemap" and "curl" rows;
        # only the "sitemap" mechanism participates in the off-clock index build.
        return [
            s.domain
            for s in get_sitemap_sources_for_category(category)
            if getattr(s, "mechanism", "") == "sitemap"
            and not _index_is_built(s.domain)
        ]
    except Exception:  # noqa: BLE001 — never raise on the price hot path
        return []


def sitemap_domains_now_built(domains: Sequence[str]) -> bool:
    """True iff ANY domain in ``domains`` now has a built (META-present) sitemap
    index.

    The READ-side invalidation predicate (Codex re-review HIGH-3): a negcache
    sentinel stamped with the cold sitemap domains at WRITE time is re-resolved the
    moment one of those domains' indexes becomes available, so the genuine PDP price
    can replace the stale estimate. Never raises (False on any error — fail-toward
    serving the cached value, the conservative no-extra-scrape path)."""
    try:
        return any(_index_is_built(d) for d in (domains or ()))
    except Exception:  # noqa: BLE001 — never raise on the price hot path
        return False


def sitemap_no_match_price() -> Dict[str, object]:
    """The honest price-dict shape a sitemap adapter returns on a discovery MISS
    (no index yet / no PDP found).

    Stamped ``source_method="sitemap_no_match"`` which
    ``price_service.should_negative_cache`` EXEMPTS from the 30d negative cache
    (exempt-like ``converted_usd`` / SF-1): the miss is TRANSIENT — a later index
    refresh can resolve the PDP and upgrade it to a genuine price — so it must NOT
    be cached as a structural dead-end. amount=None → the cascade continues."""
    return {"amount": None, "source_method": "sitemap_no_match"}
