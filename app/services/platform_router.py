"""Storefront platform detection for product-detail-page HTML.

WHY
---
Every capture defect we measured is platform-shaped, not site-shaped: Shopify
needs the `{pdp}.js` variant feed, WooCommerce needs the per-response
`prices.currency_minor_unit` divisor, Salla is the only family that publishes
`og:product:sale_price:amount`. Deciding *which* of those recovery paths to
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

This module has no call sites yet and changes no behaviour on its own, so it
carries no feature flag; the caller that wires it in is what needs gating.
"""

from __future__ import annotations

import re
from typing import Final, Tuple

__all__ = ["detect_platform", "PLATFORMS", "UNKNOWN", "MAX_SCAN_CHARS"]

UNKNOWN: Final[str] = "unknown"

PLATFORMS: Final[frozenset] = frozenset(
    {"shopify", "salla", "woocommerce", "magento", "sfcc", "nextjs", UNKNOWN}
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
        One of ``PLATFORMS``: ``"shopify"``, ``"salla"``, ``"woocommerce"``,
        ``"magento"``, ``"sfcc"``, ``"nextjs"`` or ``"unknown"``.
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
