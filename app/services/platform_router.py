"""Storefront platform detection for product-detail-page HTML.

WHY
---
Every capture defect we measured is platform-shaped, not site-shaped: Shopify
needs the `{pdp}.js` variant feed, WooCommerce needs the per-response
`prices.currency_minor_unit` divisor, Salla and Zid are the only two families
that publish `product:sale_price:amount`. Deciding *which* of those recovery paths to
run first requires knowing the platform, and the source registry cannot answer
it — `_proof/targets.json` records a mechanism for only 29 of 92 targets. So we
detect from the markup we already fetched instead of looking it up.

HOW
---
A prefix of the document is scanned for signatures that were verified
unambiguous across the 92-page cached fragrance corpus (`_proof/html/`): over
those pages every single one matched exactly one platform family, and the four
custom storefronts matched none. Census of the 86 pages that map to a target
row: shopify 44, salla 14, magento 9, woocommerce 9, custom 4, nextjs 3,
sfcc 3.

`zid` was added 2026-08-26 from the 328-page GLOBAL corpus
(`_proof/global/corpus.json`), which the Gulf-92 sweep does not cover. Zid is a
Saudi storefront platform and was invisible to the original six signatures: all
8 cached Zid rows returned `unknown`, and NO other signature matched them
either, so admitting it cannot reclassify anything that was already placed
(verified: 0 hits for the Zid pattern across the 314 non-Zid cached pages). It
earns a place because it is the OTHER platform that publishes
`product:sale_price:amount` - 5 of the 7 occurrences in the global corpus are
Zid, and `price_service`'s sale-price-first rule is scoped to
`{salla, zid}`.

Order is load-bearing. A Shopify or Salla storefront may *also* ship a Next.js
bundle, so the e-commerce platforms are tested before the generic frameworks
and the first hit wins. `nextjs` is therefore a statement about the rendering
stack of a site we could not place on a known commerce platform, and never
overrides one.

CONTRACT
--------
Pure, offline, cheap, and dependency-light on purpose:

* no network and no I/O — it only reads the string it is handed;
* no import of `price_service` (which imports half the service layer and would
  create a cycle the moment the router is called from there);
* scanning is capped at `MAX_SCAN_CHARS` so a 2.6MB page (goldenscent.com is
  2,575,292 bytes) costs a bounded amount of work. Platform signatures live in
  the head and the first theme/asset references, far inside the cap;
* the return value is always one of `PLATFORMS`, never `None`.

This module carries no feature flag of its own: it decides nothing, it only
names things. Its first call site is `price_service._extract_og_price`, which
uses it to scope the OpenGraph sale-price rule to `{salla, zid}` behind
`ENABLE_SALE_PRICE_FIRST` - that flag is what gates the behaviour, and with it
off this module is never even called.
"""

from __future__ import annotations

import re
from typing import Final, Tuple

__all__ = ["detect_platform", "PLATFORMS", "UNKNOWN", "MAX_SCAN_CHARS"]

UNKNOWN: Final[str] = "unknown"

PLATFORMS: Final[frozenset] = frozenset(
    {"shopify", "salla", "zid", "woocommerce", "magento", "sfcc", "nextjs", UNKNOWN}
)

#: Upper bound on how much of the document is scanned, so a 2.6MB page costs a
#: bounded amount of work (goldenscent.com, 2,575,292 bytes: 53ms worst case
#: measured, 9.8ms mean over the corpus).
#:
#: Do NOT shrink this without re-measuring. Signatures are NOT all in the head:
#: the deepest first hit across the 92 cached pages is nazih.ae (magento) at
#: character 135,159, with nazih.qa at 124,760 and alibaksh.com (woocommerce)
#: at 114,894. A 128KB cap would silently reclassify nazih.ae as "unknown".
#: 400KB leaves ~3x headroom over the deepest observed signature.
MAX_SCAN_CHARS: Final[int] = 400 * 1024

# Signatures verified unambiguous over the cached corpus. Dots are escaped:
# `salla.sa` as a raw pattern would also match `sallaxsa`.
#
# Tuple order IS the priority order, highest first. Each pattern is scanned
# separately and the first hit wins.
#
# MEASURED, do not "optimize" this back: collapsing the six patterns into one
# alternation of named groups scanned with `finditer` (so the prefix is walked
# once) is SLOWER, not faster - mean 20.1ms vs 9.1ms per page and worst case
# 76ms vs 46ms over the 92-page corpus. `re.search` bails at the first hit at C
# speed, whereas a 14-branch alternation costs more per character and
# `finditer` materialises a match object for every one of the thousands of
# `/pub/static/` occurrences on a Magento page.
_SIGNATURES: Final[Tuple[Tuple[str, "re.Pattern[str]"], ...]] = (
    # --- e-commerce platforms: these win ---
    (
        "shopify",
        re.compile(
            r"cdn\.shopify\.com|/cdn/shop/|Shopify\.theme|shopify-section",
            re.IGNORECASE,
        ),
    ),
    ("salla", re.compile(r"salla\.sa|cdn\.salla\.network", re.IGNORECASE)),
    # Zid. Every real signal is a HOST label - the storefront's own
    # `<shop>.zid.store` domain, or the `assets.zid.store` / `media.zid.store`
    # asset CDNs a custom-domain store still preconnects to (that preconnect is
    # the ONLY platform signal mazeed.sa emits: it runs Zid behind a Nuxt front
    # end). One pattern covers all three, since `zid` there is always preceded
    # by a dot or a delimiter.
    #
    # The LEADING \b is what keeps this off an unrelated domain that merely
    # ends in the same letters (`rapidzid.store`); it is the same discipline
    # the escaped dot gives `salla.sa`. There is deliberately no TRAILING
    # boundary - none of the other six signatures has one, and adding one would
    # make the verdict depend on whatever byte happens to follow the match.
    #
    # Placed with the e-commerce platforms, i.e. ABOVE `nextjs`: a framework is
    # never a platform, and mazeed.sa ships a framework bundle. Its position
    # relative to the other five is not load-bearing - across the 8 cached Zid
    # rows no other signature matched at all.
    ("zid", re.compile(r"\bzid\.store", re.IGNORECASE)),
    (
        "woocommerce",
        re.compile(
            r"woocommerce-Price-amount|wp-content/plugins/woocommerce",
            re.IGNORECASE,
        ),
    ),
    (
        "magento",
        re.compile(r"Magento_|/pub/static/|data-mage-init", re.IGNORECASE),
    ),
    ("sfcc", re.compile(r"demandware", re.IGNORECASE)),
    # --- generic frameworks: only reached when nothing above matched ---
    ("nextjs", re.compile(r"__NEXT_DATA__|/_next/static", re.IGNORECASE)),
)


def _first_by_priority(text: str) -> "str | None":
    """Highest-priority platform whose signature appears anywhere in ``text``."""
    for name, pattern in _SIGNATURES:
        if pattern.search(text):
            return name
    return None


def detect_platform(html: str, url: str = "") -> str:
    """Name the storefront platform that produced ``html``.

    Args:
        html: The raw PDP markup. Anything that is not a ``str`` (``None``,
            undecoded ``bytes``) is treated as no evidence rather than raising,
            because callers hand us whatever the fetch layer returned.
        url: Optional page URL, used **only** as a fallback when the markup
            yields nothing - a `salla.sa` storefront URL still identifies the
            platform when the body came back empty or truncated. It can never
            override a decision the markup already made.

    Returns:
        One of ``PLATFORMS``: ``"shopify"``, ``"salla"``, ``"zid"``,
        ``"woocommerce"``, ``"magento"``, ``"sfcc"``, ``"nextjs"`` or
        ``"unknown"``.
    """
    if isinstance(html, str) and html:
        found = _first_by_priority(html[:MAX_SCAN_CHARS])
        if found is not None:
            return found

    if isinstance(url, str) and url:
        found = _first_by_priority(url[:2048])
        if found is not None:
            return found

    return UNKNOWN
