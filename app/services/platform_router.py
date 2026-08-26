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
and the first hit wins.

TWO FIELDS, NOT ONE STRING (2026-08-26)
---------------------------------------
The single-string verdict conflated two different questions and was measured
failing at both. Over all 521 cached pages (429 `_proof/global/html/` +
92 `_proof/html/`, one call each, no network):

* it said `unknown` on 230 of 521 (44.1%) - and on 101 of the 247 usable global
  PDPs (40.9%; 106 = 43% before `zid` was admitted, which is the number the
  finding quotes). It was the single most common verdict in the corpus, more
  common than shopify;
* `nextjs` - 53 more pages - is NOT a platform. It fires across five unrelated
  commerce backends, so it can never route an extraction strategy.
  `sephora.com.tr` proves the shape from cached bytes: a Next.js front end over
  Salesforce Commerce (`/dw/image/v2/.../on/demandware.static/`). Counting
  `nextjs` as the non-answer it is, the single string named no extraction
  contract on 283 of 521 pages (54.3%).

So `detect_platform_verdict` returns a `PlatformVerdict` of two INDEPENDENT
fields:

* `commerce_platform` - the EXTRACTION contract. One of `COMMERCE_PLATFORMS`.
* `render_stack`      - the FETCH strategy. One of `RENDER_STACKS`.

Either may be `unknown` on its own, and a framework signal is structurally
incapable of supplying a `commerce_platform`: the two label sets are disjoint
apart from `unknown`, and they are produced by two separate scans.

Signatures added in the same pass, each anchored to cached bytes (hit counts
over the 521 pages): `sap_hybris` 27 - the single biggest recovery, all
previously `unknown` - plus `prestashop` 10, `magento` +9 via Adobe Commerce's
own asset paths, `bigcommerce` 4 (previously `nextjs`), `shopware` 3, and the
explicit `/on/demandware.store/` spelling of `sfcc`. `vtex` is in the table
with ZERO corpus evidence, and that is stated rather than hidden. Result:
pages with a routable extraction contract go 238 -> 291 of 521, i.e. the
no-contract share falls 54.3% -> 44.1%; on the usable-PDP slice the finding
quotes, 43% -> 38.9%.

The residual 230 are not a regex gap. 66 have no corpus row at all, 47 are
non-200 (31 of them WAF/403 bodies under 6KB), and the labelled remainder are
genuinely bespoke or headless (`noon.com`, `boutiqaat.com`,
`luluhypermarket`, `walmart`, `target`) or run a platform outside the enum
(`opencart`, `oxid`, `shift4shop`, `adobe_aem`, `episerver`, `remix`).
Measured separately: removing `MAX_SCAN_CHARS` entirely would recover 8 more
pages at depths up to 3.4MB, which is not a trade worth making.

CONTRACT
--------
Pure, offline, cheap, and dependency-light on purpose:

* no network and no I/O — it only reads the strings it is handed;
* no import of `price_service` (which imports half the service layer and would
  create a cycle the moment the router is called from there);
* TOTAL. `None`, undecoded `bytes`, an int, a list - anything that is not a
  non-empty `str` is NO EVIDENCE, never an exception. A classifier that raised
  on a bad page would take the whole price cascade down with it;
* scanning is capped at `MAX_SCAN_CHARS` (and `MAX_ROBOTS_CHARS` for a robots
  body) so a 2.6MB page (goldenscent.com is 2,575,292 bytes) costs a bounded
  amount of work;
* every field of the return value is always a known label, never `None`.

THE FLAG
--------
`ENABLE_PLATFORM_VERDICT`, default ON, read PER CALL via `os.getenv`, never
cached at import. It gates exactly one thing: whether the back-compat wrapper
`detect_platform` returns the widened `commerce_platform` or its verbatim
legacy body.

It exists because `detect_platform` cannot preserve one of the values it used
to return - `"nextjs"` is not an extraction contract, and removing it from the
answer set IS the finding. Everything else is preserved by CONSTRUCTION rather
than by promise: `_COMMERCE_TIER_A` is a slice of the legacy `_SIGNATURES`
tuple and is consulted over the markup and then the URL before any signature
added in this wave, so a page the legacy classifier placed can never be moved.
Measured over all 521 cached pages: 0 move off a legacy non-`nextjs` label.

`detect_platform_verdict` itself is NOT gated - it is unreachable before this
commit, so there is no legacy behaviour for a rollback to restore.

The one live call site, `price_service._og_sale_price_platform`, asks only
`detect_platform(...) in {"salla", "zid"}` behind `ENABLE_SALE_PRICE_FIRST`.
Both labels are Tier-A labels, so that predicate is provably identical in both
flag states - this change cannot move a price.
"""

from __future__ import annotations

import os
import re
from typing import Final, NamedTuple, Tuple

__all__ = [
    "detect_platform",
    "detect_platform_verdict",
    "platform_verdict_enabled",
    "PlatformVerdict",
    "COMMERCE_PLATFORMS",
    "RENDER_STACKS",
    "PLATFORMS",
    "UNKNOWN",
    "MAX_SCAN_CHARS",
]

UNKNOWN: Final[str] = "unknown"

#: Every value `detect_platform` can return, in EITHER flag state. It is the
#: union of `COMMERCE_PLATFORMS` (what it returns with the flag ON) and the
#: legacy eight (what it returns with the flag OFF) - the only member of the
#: latter that is not also a commerce label is `nextjs`.
PLATFORMS: Final[frozenset] = frozenset(
    {
        "shopify", "salla", "zid", "woocommerce", "magento", "sfcc",
        "bigcommerce", "prestashop", "shopware", "sap_hybris", "vtex",
        "nextjs", UNKNOWN,
    }
)

#: The EXTRACTION contract: which family of markup/API a price extractor should
#: reach for. Never contains a rendering framework.
COMMERCE_PLATFORMS: Final[frozenset] = frozenset(
    {
        "shopify", "salla", "zid", "woocommerce", "magento", "sfcc",
        "bigcommerce", "prestashop", "shopware", "sap_hybris", "vtex", UNKNOWN,
    }
)

#: The FETCH strategy: how the document is assembled in a browser. Never
#: contains a commerce platform.
RENDER_STACKS: Final[frozenset] = frozenset(
    {"nextjs", "nuxt", "react", "vue", "angular", "classic", UNKNOWN}
)


class PlatformVerdict(NamedTuple):
    """Two INDEPENDENT answers about one document.

    `commerce_platform` answers "what does the price live in?"; `render_stack`
    answers "how do I have to fetch it?". Either may be ``"unknown"`` on its
    own, and a `render_stack` signal is never allowed to supply a
    `commerce_platform` - that conflation is the defect this type exists to
    make unrepresentable.
    """

    commerce_platform: str
    render_stack: str


#: Upper bound on how much of the document is scanned, so a 2.6MB page costs a
#: bounded amount of work (goldenscent.com, 2,575,292 bytes: 53ms worst case
#: measured, 9.8ms mean over the corpus).
#:
#: Do NOT shrink this without re-measuring. Signatures are NOT all in the head:
#: the deepest first hit across the 92 cached pages is nazih.ae (magento) at
#: character 135,159, with nazih.qa at 124,760 and alibaksh.com (woocommerce)
#: at 114,894. A 128KB cap would silently reclassify nazih.ae as "unknown".
#: 400KB leaves ~3x headroom over the deepest observed signature.
#:
#: Do NOT GROW it either, and this was measured rather than assumed: removing
#: the cap entirely across all 521 cached pages recovers a label on exactly 8
#: more pages (5 boutiqaat.com, 2 lookfantastic.com, 1 unmapped) at first-hit
#: depths of 555KB to 3.4MB - i.e. paying an unbounded scan on every page to
#: rescue 1.5% of them, several of which are stray mentions rather than
#: storefront assets.
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


#: TIER A - the six commerce entries of `_SIGNATURES`, byte-for-byte the same
#: compiled patterns in the same order, with the `nextjs` entry dropped because
#: a framework is not an extraction contract.
#:
#: Keeping this a SLICE rather than a copy is what makes the back-compat claim
#: provable instead of hopeful: `detect_platform_verdict` consults Tier A over
#: the markup and then over the URL BEFORE it looks at anything added in this
#: wave, so a page the legacy classifier placed can never be moved by a new
#: signature. Measured over all 521 cached pages (429 global + 92 Gulf): 0
#: pages move off a legacy non-`nextjs` label.
_COMMERCE_TIER_A: Final[Tuple[Tuple[str, "re.Pattern[str]"], ...]] = _SIGNATURES[:6]

#: TIER B - the platforms and the widened patterns the 328-page global corpus
#: measured and the six legacy regexes miss. Reached ONLY when every Tier-A
#: pattern has missed both the markup and the URL, i.e. exactly where the
#: legacy verdict was `nextjs` or `unknown`.
#:
#: Each entry records what it is anchored to. Hit counts are over the 521
#: cached pages unless stated.
_COMMERCE_TIER_B: Final[Tuple[Tuple[str, "re.Pattern[str]"], ...]] = (
    # Shopify, in its ROBOTS-shaped spelling. `/.well-known/shopify/monorail`
    # is a line Shopify puts in every storefront's robots.txt; it is what stops
    # hudabeauty.com - whose robots opens "# we use Shopify as our ecommerce
    # platform" and still carries a stale `Disallow: /on/demandware.store/`
    # from the platform it migrated off - being called SFCC. Harmless on
    # markup: it occurs in 118 cached pages and Tier A already calls every one
    # of them shopify, so it can never move a page on its own.
    ("shopify", re.compile(r"\.well-known/shopify/", re.IGNORECASE)),
    # SAP Commerce Cloud (hybris). The biggest single recovery in this wave:
    # 27 pages, previously all `unknown`. `smartedit` is SAP's own CMS
    # authoring runtime (it survives into the storefront as the
    # `.smartEditComponent` CSS class); `cx-page-slot` and `cx-storefront` are
    # the Spartacus Angular storefront's component selectors;
    # `/medias/sys_master/` is the hybris media repository path.
    #
    # This is also where corpus.json's `platform_truth` is WRONG against its
    # own cached bytes, twice: douglas.at / douglas.ch are filed `magento` and
    # carry no Magento token whatsoever, and www.watsons.com.tr is filed
    # `unknown` while shipping the complete Spartacus set.
    (
        "sap_hybris",
        re.compile(
            r"smartedit|cx-page-slot|cx-storefront|/medias/sys_master/"
            r"|/_ui/responsive/|\bhybris\b",
            re.IGNORECASE,
        ),
    ),
    # Salesforce Commerce, spelled out. The bare `demandware` token in Tier A
    # already catches every SFCC page in these corpora, so these alternations
    # add nothing on markup - they exist because they are the spellings that
    # appear in a robots.txt (`Disallow: /on/demandware.store/*` is what
    # sephora.me publishes) and in an image URL on a headless SFCC front end
    # (`/dw/image/v2/...`), which is where the framework was masking the
    # platform.
    (
        "sfcc",
        re.compile(
            r"/on/demandware\.(?:store|static)/|\bdwfrm_|/dw/image/v2/|demandware",
            re.IGNORECASE,
        ),
    ),
    # PrestaShop: 10 pages (eperfumy.pl, parfumdo.com, parfumerie-burdin.com).
    # The bare product name is safe here - it occurs on exactly those 10 and
    # nowhere else in 521 pages.
    ("prestashop", re.compile(r"prestashop", re.IGNORECASE)),
    # Shopware: 3 pages (pieper.de, duftzwilling.de). Same reasoning; note the
    # label is version-free on purpose, `shopware5` and `shopware6` are the
    # same extraction contract for our purposes.
    ("shopware", re.compile(r"shopware", re.IGNORECASE)),
    # BigCommerce: 4 pages (ideabellezza.it), every one of which the legacy
    # classifier called `nextjs`.
    (
        "bigcommerce",
        re.compile(r"cdn11\.bigcommerce\.com|stencil-utils|/stencil/", re.IGNORECASE),
    ),
    # VTEX. ZERO hits across all 521 cached pages - it is in the table because
    # the assignment names it and because these two asset hosts are
    # unambiguous, NOT because the corpus proved it. Deliberately narrow: only
    # the two CDN hostnames, no bare `vtex` word (which collides with ordinary
    # text) and no `__RUNTIME__` (which is not VTEX-exclusive).
    ("vtex", re.compile(r"vtexassets\.com|vteximg\.com\.br", re.IGNORECASE)),
    # Magento, widened: 9 more pages (ounass.ae, druni.es, parfumcenter.nl,
    # jomashop.com). `/media/catalog/product/` and `/static/version<digits>/`
    # are Adobe Commerce's own asset paths and `x-magento-init` its inline
    # bootstrap hook.
    (
        "magento",
        re.compile(
            r"/media/catalog/product/|/static/version\d|x-magento"
            r"|/frontend/Magento/|mageplaza|amasty",
            re.IGNORECASE,
        ),
    ),
    # WooCommerce, widened with the AJAX endpoint and the JS config object a
    # store emits even when the plugin path has been rewritten by a CDN. No
    # page in these corpora needs it; it is here for symmetry with magento.
    (
        "woocommerce",
        re.compile(r"wc-ajax|woocommerce_params|woocommerce-page", re.IGNORECASE),
    ),
)

#: The RENDER stack, scanned independently of everything above. First hit wins.
#:
#: Order is from most specific to least: Next.js IS React and Nuxt IS Vue, so
#: the meta-framework must be tested before the library it is built on or every
#: Next.js page would report `react`. `classic` is last and is a POSITIVE
#: signal - a jQuery/RequireJS-era server-rendered page - not a synonym for
#: "nothing matched"; when nothing matches at all the answer is `unknown`.
#:
#: Census over the 521 cached pages: classic 213, unknown 214, nextjs 56,
#: react 16, angular 16, nuxt 6, vue 0.
_RENDER_SIGNATURES: Final[Tuple[Tuple[str, "re.Pattern[str]"], ...]] = (
    ("nextjs", re.compile(r"__NEXT_DATA__|/_next/static", re.IGNORECASE)),
    ("nuxt", re.compile(r"window\.__NUXT__|/_nuxt/", re.IGNORECASE)),
    # `ng-version=` is emitted by the root component of every Angular 2+ app
    # and is what the SAP Spartacus storefronts carry.
    (
        "angular",
        re.compile(r"ng-version=|/@angular/|angular\.min\.js|\bng-app=", re.IGNORECASE),
    ),
    (
        "react",
        re.compile(
            r"data-reactroot|data-reactid|react-dom|__REACT_DEVTOOLS"
            r"|/react@|react\.production\.min",
            re.IGNORECASE,
        ),
    ),
    # `data-v-<hash>` is Vue's scoped-CSS attribute. Only reachable once nuxt
    # has missed, since a Nuxt page emits it too.
    (
        "vue",
        re.compile(
            r"data-v-[0-9a-f]{6,8}|window\.__VUE__|vue\.runtime|/vue@|vue\.min\.js",
            re.IGNORECASE,
        ),
    ),
    (
        "classic",
        re.compile(r"jquery|requirejs|require\.js|prototype\.js|mootools", re.IGNORECASE),
    ),
)

#: robots.txt gets its OWN table because a robots file has different tells from
#: a PDP: it names paths, not assets. Order matters for one measured reason -
#: see the `shopify` note on Tier B and `com_hudabeauty_com_robots.txt`.
_ROBOTS_SIGNATURES: Final[Tuple[Tuple[str, "re.Pattern[str]"], ...]] = (
    ("shopify", re.compile(r"\.well-known/shopify/|/cdn/shop/", re.IGNORECASE)),
    ("salla", re.compile(r"salla\.sa|cdn\.salla\.network", re.IGNORECASE)),
    ("zid", re.compile(r"\bzid\.store", re.IGNORECASE)),
    ("woocommerce", re.compile(r"/wp-admin/|wp-content/plugins/woocommerce", re.IGNORECASE)),
    ("magento", re.compile(r"catalogsearch/|/checkout/cart/|Magento_", re.IGNORECASE)),
    ("sfcc", re.compile(r"/on/demandware\.(?:store|static)/|demandware", re.IGNORECASE)),
    ("sap_hybris", re.compile(r"/_ui/responsive/|/medias/sys_master/|\bhybris\b", re.IGNORECASE)),
    ("prestashop", re.compile(r"prestashop|/modules/ps_", re.IGNORECASE)),
    ("shopware", re.compile(r"shopware|/widgets/emotion", re.IGNORECASE)),
    ("bigcommerce", re.compile(r"cdn11\.bigcommerce\.com|/stencil/", re.IGNORECASE)),
    ("vtex", re.compile(r"vtexassets\.com|vteximg\.com\.br", re.IGNORECASE)),
)

#: Upper bound on how much of a robots.txt is scanned. The largest of the 18
#: cached robots files is h3jssz.zid.store at 22,664 bytes; 64KB is ~2.8x
#: headroom and keeps a hostile multi-megabyte robots response bounded.
MAX_ROBOTS_CHARS: Final[int] = 64 * 1024


def _first_by_priority(text: str) -> "str | None":
    """Highest-priority platform whose signature appears anywhere in ``text``."""
    for name, pattern in _SIGNATURES:
        if pattern.search(text):
            return name
    return None


def _first_of(
    table: Tuple[Tuple[str, "re.Pattern[str]"], ...], text: str
) -> "str | None":
    """First label in ``table`` whose pattern appears anywhere in ``text``."""
    for name, pattern in table:
        if pattern.search(text):
            return name
    return None


def _scan_text(value: object, cap: int) -> str:
    """A capped, scannable prefix of ``value``, or ``""`` if it is not evidence.

    Callers hand this module whatever the fetch layer returned, which on a
    failed fetch can be ``None``, undecoded ``bytes``, or an error object. All
    of those are NO EVIDENCE, never an exception - a classifier that raises on
    a bad page would take the whole price cascade down with it.
    """
    if isinstance(value, str) and value:
        return value[:cap]
    return ""


def platform_verdict_enabled() -> bool:
    """True iff `detect_platform` returns the widened commerce label (default ON).

    This flag exists because `detect_platform` CANNOT preserve one of the
    values it used to return. `"nextjs"` is not an extraction contract - it
    fires across five unrelated commerce backends - and removing it from the
    answer set is precisely the finding. Everything else is preserved by
    construction (see `_COMMERCE_TIER_A`), so the flag gates exactly one
    behaviour change: a page the legacy classifier called `nextjs` now reports
    the commerce platform underneath it, or `unknown`.

    The one live call site - `price_service._og_sale_price_platform`, which
    asks only ``detect_platform(...) in {"salla", "zid"}`` - is provably
    unaffected in either state, since both labels are Tier-A labels. Read per
    call so Railway can flip it without a restart; never cached at import.
    """
    return os.getenv("ENABLE_PLATFORM_VERDICT", "true").strip().lower() not in (
        "false", "0", "no", "off", "",
    )


def _commerce_platform(html: object, url: object, robots_txt: object) -> str:
    """The EXTRACTION contract alone, in the documented evidence order.

    Split out from `detect_platform_verdict` so the back-compat wrapper - the
    one thing on the live price path - does not pay for a `render_stack` scan
    it immediately throws away.

    Measured over the 521 cached pages, mean / p95 / max per call:

        detect_platform, flag OFF (legacy)      17.2 /  42.4 /  46.5 ms
        detect_platform, flag ON (this fn)      32.2 / 104.5 / 106.7 ms
        detect_platform_verdict (both fields)   63.2 / 164.2 / 172.6 ms

    The extra cost is real and is the price of scanning a 400KB prefix with
    nine more patterns; it is paid ONLY on the pages where every legacy pattern
    missed, which is exactly where the old answer was useless. It is CPU on a
    path that is already waiting on a network fetch, and `_og_sale_price_platform`
    - the only live caller - is reached only when an OG sale tag is present at
    all (21 of 521 cached pages).
    """
    doc = _scan_text(html, MAX_SCAN_CHARS)
    loc = _scan_text(url, 2048)
    rob = _scan_text(robots_txt, MAX_ROBOTS_CHARS)
    return (
        # 1-2: exactly the legacy scan, in the legacy order, over exactly the
        # legacy two channels. Nothing added in this wave can preempt it.
        (_first_of(_COMMERCE_TIER_A, doc) if doc else None)
        or (_first_of(_COMMERCE_TIER_A, loc) if loc else None)
        # 3-4: only reachable where the legacy verdict was `nextjs` or `unknown`.
        or (_first_of(_COMMERCE_TIER_B, doc) if doc else None)
        or (_first_of(_COMMERCE_TIER_B, loc) if loc else None)
        # 5: the weakest channel, and its own table.
        or (_first_of(_ROBOTS_SIGNATURES, rob) if rob else None)
        or UNKNOWN
    )


def detect_platform_verdict(
    html: str, url: str = "", robots_txt: str = ""
) -> PlatformVerdict:
    """Name the EXTRACTION contract and the FETCH strategy, independently.

    Args:
        html: The raw PDP markup. Anything that is not a non-empty ``str`` is
            treated as no evidence rather than raising.
        url: Optional page URL - a second, weaker evidence channel, used only
            where the markup was silent (a `salla.sa` storefront URL still
            identifies the platform when the body came back empty or was a WAF
            block page).
        robots_txt: Optional robots.txt body - the THIRD and weakest channel,
            consulted only where both the markup and the URL were silent, and
            scanned against its own signature table because a robots file names
            paths rather than assets. It exists because it is the only evidence
            some hosts give us: every one of the five cached `sephora.me` PDP
            fetches is a 624-byte Akamai "Access Denied" body with no signal of
            any kind, while its robots.txt publishes
            ``Disallow: /on/demandware.store/*``.

    Returns:
        A `PlatformVerdict`. `commerce_platform` is one of
        `COMMERCE_PLATFORMS`; `render_stack` is one of `RENDER_STACKS`; either
        may independently be ``"unknown"``.

    Evidence order for `commerce_platform` is deliberate and load-bearing:

        1. markup, Tier A   ) exactly the legacy scan, in the legacy order,
        2. URL, Tier A      ) so a legacy verdict can never be displaced
        3. markup, Tier B
        4. URL, Tier B
        5. robots.txt

    `render_stack` is derived from the markup ALONE. A URL cannot tell you how
    a page is assembled, and inventing a framework from a path would be the
    same category error this whole change exists to remove.
    """
    doc = _scan_text(html, MAX_SCAN_CHARS)
    render = (_first_of(_RENDER_SIGNATURES, doc) if doc else None) or UNKNOWN
    return PlatformVerdict(_commerce_platform(html, url, robots_txt), render)


def detect_platform(html: str, url: str = "") -> str:
    """Name the storefront platform that produced ``html``.

    Back-compat wrapper over `detect_platform_verdict`, kept because
    `price_service._og_sale_price_platform` calls it. Signature unchanged.

    Args:
        html: The raw PDP markup. Anything that is not a ``str`` (``None``,
            undecoded ``bytes``) is treated as no evidence rather than raising,
            because callers hand us whatever the fetch layer returned.
        url: Optional page URL, used **only** as a fallback when the markup
            yields nothing - a `salla.sa` storefront URL still identifies the
            platform when the body came back empty or truncated. It can never
            override a decision the markup already made.

    Returns:
        With `ENABLE_PLATFORM_VERDICT` ON (the default) the
        `commerce_platform` field of the verdict, i.e. one of
        `COMMERCE_PLATFORMS`. With it OFF, exactly the legacy value: one of
        ``"shopify"``, ``"salla"``, ``"zid"``, ``"woocommerce"``,
        ``"magento"``, ``"sfcc"``, ``"nextjs"`` or ``"unknown"``.

        The two differ on one thing only: where the legacy verdict was
        ``"nextjs"`` or ``"unknown"``.
    """
    if platform_verdict_enabled():
        # Deliberately NOT `detect_platform_verdict(...).commerce_platform`:
        # the caller discards `render_stack`, and computing it would cost this
        # live call site a second full-prefix scan for nothing.
        return _commerce_platform(html, url, "")

    # --- legacy body, verbatim -------------------------------------------
    if isinstance(html, str) and html:
        found = _first_by_priority(html[:MAX_SCAN_CHARS])
        if found is not None:
            return found

    if isinstance(url, str) and url:
        found = _first_by_priority(url[:2048])
        if found is not None:
            return found

    return UNKNOWN
