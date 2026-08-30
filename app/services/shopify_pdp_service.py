"""Shopify per-PDP variant feed — ``GET {pdp_url}.js`` (STEP 5).

WHY
---
Shopify's own structured data on a product page is the least trustworthy price
on the page, measured over the cached fragrance corpus:

* ``numberc.com`` JSON-LD says 12.10 while the live ``.js`` feed says 22.00 —
  the JSON-LD is stale;
* ``watsons.sa`` JSON-LD says 70.0, which is the MAX of a 20.10–70.00 variant
  range, not the shelf price;
* ``alhajisoman.com`` OpenGraph says 3.0 against a real 30.00 — a 10x error.

The ``.js`` endpoint is the platform's own variant feed and answers all three:
it carries every variant with its integer minor-unit price, its
``compare_at_price`` and its per-variant ``available`` flag. Measured live it
returns HTTP 200 in 379–638 ms (worst observed 1234 ms).

THE RULES, ALL MEASURED — do not "improve" them from first principles
--------------------------------------------------------------------
1. ``price = min(v["price"] for v in variants if v["available"]) / 100``.
   The divisor is **ALWAYS 100**, including the 3-decimal Gulf currencies.
   ``bh.taifalemarat`` ships ``6066`` for a 60.66 BHD product and
   ``alhajisoman`` ships ``3000`` for 30.00 OMR. A currency-table divisor
   (BHD/OMR/KWD → 1000) would read those as 6.066 and 3.000 and under-price the
   entire Bahraini catalogue by 10x. There is no currency table here on purpose.
2. When NOTHING is available we still return a price, but we do **not** relax
   rule 1 into "the cheapest variant overall" and hand it back as if it were a
   shelf price. We return the payload's OWN declared product price, flag
   ``in_stock=False`` and label it ``price_basis="product_price_no_stock"`` so
   the caller decides what a sold-out price is worth. On ``watsons.sa`` — five
   variants, 20.10–70.00, not one of them available — the number that comes back
   coincides with the range floor because that is what Shopify itself displays;
   the load-bearing part is that it is never presented as purchasable.
3. Availability is the AND of the top-level ``available`` and the per-variant
   flags. Either one saying "no" means no.
4. ``list_price = compare_at_price / 100`` only when a compare-at exists and
   EXCEEDS the price. Many themes write a literal ``0`` rather than ``null`` for
   "no compare-at" (``bh.mubkhar``, ``bh.azhaperfumes``, ``watsons``), and a
   compare-at equal to the price is not a discount.

SAFETY
------
* **SSRF.** The request goes through the repo's own primitives — the initial URL
  and EVERY redirect hop must pass ``app.utils.url_validator.validate_external_url``
  (blocks non-http(s), unresolvable hosts, private/loopback/link-local/reserved
  IPs) AND ``price_service._host_on_domain`` (pins the chain to the source
  storefront). This mirrors ``curl_fetch_html_same_site`` hop for hop. It is a
  separate loop only because that helper collapses every non-200 to ``None`` and
  this adapter has to see the literal 503 to apply rule 5 — nothing here relaxes
  a check that helper makes.
* **Rate limit.** >= 1s of spacing per domain. A burst gets an identical
  12194-byte HTTP 503. The slot is RESERVED before the request (not merely
  checked), so concurrent callers queue instead of all reading a stale
  "last request" timestamp and firing together.
* **503.** Retry exactly once, then ``None`` so the caller falls through to the
  HTML cascade. No other status is retried.
* The adapter NEVER raises: every network/parse/validation failure is ``None``.

FLAG — ``ENABLE_SHOPIFY_PDP_JSON``, DEFAULT **OFF**
--------------------------------------------------
This is the first thing in the wave that adds a NETWORK CALL, so it ships
dormant per the house rules. The flag gates the FETCH, not the parser: with it
off, ``fetch_shopify_pdp_json`` returns ``None`` before touching DNS, the
spacing table, or a socket. Read per call from ``os.getenv`` (the
``price_service.exact_gate_enabled`` pattern) — never cached at import, and
nothing added to ``app/config.py``.

WIRING — CORRECTED at M10 UNIT A4, 2026-08-31
---------------------------------------------
This docstring used to end "NOT WIRED IN. This module has ZERO call sites",
which was true when the ``.js`` adapter shipped at STEP 5 and is no longer true.
It is corrected rather than deleted, because the claim was load-bearing and a
reader who trusted it would draw a wrong conclusion about the blast radius.

The ``.js`` PRICE adapter (``fetch_shopify_pdp_json``) still has no call site
under ``app/`` — that wiring remains a separate, separately-reviewable change.
What UNIT A4 added is a second adapter in this file, the UCP
``/products/{handle}.json`` channel (see the section at the bottom), and
``price_service._try_ucp_json_price`` calls THAT one from two points in
``fetch_page_price``, behind its own default-OFF ``ENABLE_UCP_JSON_PRICE``.

So: this module is now imported by ``app/services/price_service.py``, and with
both flags off no code path here reaches DNS, the spacing table or a socket. The
guard that keeps that honest is
``tests/test_shopify_pdp_json.py::TestWiringStaysFlagGated``, which replaced the
old zero-call-sites tripwire with the property that tripwire was standing in for.
"""

import asyncio
import json
import logging
import math
import os
import time
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse, urlunparse

logger = logging.getLogger(__name__)

# Per-request curl timeout. Measured .js latency is 379-1234ms; 12s is the same
# generous ceiling salla_service uses for a comparably fast JSON endpoint.
HTTP_TIMEOUT = 12

# Minimum spacing between two requests to the SAME domain. A tighter burst is
# what produced the identical 12194-byte 503s during the live sweep.
MIN_DOMAIN_INTERVAL_S = 1.0

# Redirect budget per attempt — same cap as curl_fetch_html_same_site.
MAX_REDIRECTS = 3

# domain -> monotonic timestamp at which the NEXT request to it may start.
_next_slot_at: Dict[str, float] = {}


# ---------------------------------------------------------------- feature flag


def shopify_pdp_json_enabled() -> bool:
    """True iff the Shopify ``{pdp}.js`` fetch is active (default **OFF**).

    Default OFF because this is the wave's only new NETWORK call: one extra
    round-trip per Shopify PDP, on a rate-limited endpoint that answers a burst
    with 503. It therefore ships dormant and gets turned on deliberately, unlike
    the pure-parse fixes in steps 2-4 which default ON.

    Read PER CALL from ``os.getenv`` so Railway can flip it without a restart —
    never cached at import, and nothing added to ``app/config.py``. Deliberately
    INDEPENDENT of ``exact_gate_enabled``, ``sale_price_first_enabled``,
    ``og_branch_fixes_enabled`` and ``wide_candidate_enabled``: this is a new
    data SOURCE, not a fix to any of those layers, so neither their rollback nor
    their rollout should move it.

    Uses the repo's default-OFF idiom (an explicit truthy allow-list, per
    ``ENABLE_FRAGRANCE_SIZE_RECONCILE_FIX`` at price_service.py:3635) rather than
    the default-ON ``not in (...)`` idiom, so an unset, empty or misspelled value
    leaves the network call OFF."""
    return os.getenv("ENABLE_SHOPIFY_PDP_JSON", "false").strip().lower() in (
        "true", "1", "yes", "on",
    )


# ------------------------------------------------------------------ url shapes


def _normalise_domain(domain: Optional[str]) -> str:
    """Lower-cased, ``www.``-stripped domain key (spacing + same-site pin)."""
    d = (domain or "").strip().lower()
    return d[4:] if d.startswith("www.") else d


def _build_pdp_feed_url(
    pdp_url: Optional[str],
    suffix: str,
    *,
    strip_siblings: Tuple[str, ...] = (),
) -> Optional[str]:
    """``https://host/products/handle`` -> the same path plus ``suffix``.

    Query and fragment are stripped first: a PDP URL that arrives from search or
    a sitemap routinely carries ``?variant=...`` or UTM parameters, and
    ``/products/x?variant=1.js`` is a 404. A trailing slash is dropped so we
    never emit ``/products/x/.js``.

    A path that ALREADY ends in ``suffix`` (any case) is returned as-is rather
    than doubled — some callers hand us the feed URL directly.

    ``strip_siblings`` names the OTHER per-handle feed extensions to remove
    before appending. It exists because the two feeds are SIBLINGS, not layers:
    a caller holding ``/products/x.js`` who asks for the ``.json`` sibling must
    get ``/products/x.json``, never the 404 ``/products/x.js.json``. It defaults
    to empty so ``build_pdp_json_url`` keeps its shipped behaviour exactly —
    UNIT A4 extends this family and is not licensed to move the ``.js`` builder.

    Returns ``None`` for anything unusable (empty, non-string, non-http(s)
    scheme, or no host) so the caller short-circuits before any network work."""
    if not pdp_url or not isinstance(pdp_url, str):
        return None
    try:
        parsed = urlparse(pdp_url.strip())
    except Exception:  # noqa: BLE001 — a malformed URL is a miss, never a crash
        return None
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return None

    path = parsed.path or "/"
    if path.lower().endswith(suffix):
        clean_path = path
    else:
        for other in strip_siblings:
            if path.lower().endswith(other):
                path = path[: -len(other)]
                break
        clean_path = path.rstrip("/") + suffix

    # Drop params/query/fragment — only scheme, netloc and path survive.
    return urlunparse((parsed.scheme, parsed.netloc, clean_path, "", "", ""))


def build_pdp_json_url(pdp_url: Optional[str]) -> Optional[str]:
    """``https://host/products/handle`` -> ``https://host/products/handle.js``.

    The Shopify per-PDP VARIANT feed: integer minor-unit prices and a per-variant
    ``available`` flag, but NO currency (see ``build_pdp_products_json_url`` for
    the complementary feed that carries one)."""
    return _build_pdp_feed_url(pdp_url, ".js")


# ------------------------------------------------------------- domain spacing


def reserve_domain_slot(domain: str, now: Optional[float] = None) -> float:
    """Claim the next request slot for ``domain``; return the seconds to wait.

    RESERVES rather than merely checks: the domain's next-allowed timestamp is
    advanced by ``MIN_DOMAIN_INTERVAL_S`` from the slot just handed out, so N
    concurrent callers on one storefront get 0s, 1s, 2s ... instead of all
    reading the same stale "last request" time and firing at once. That
    stacking behaviour is the whole point — a burst is exactly what returns the
    12194-byte 503.

    Deliberately lock-free: a reservation is a single read-then-write on the
    module dict with no ``await`` in between, so it is atomic under asyncio, and
    it works across the many short-lived event loops a test session creates
    (an ``asyncio.Lock`` built at import binds to the first loop that acquires it
    and then raises on the next one).

    ``now`` is injectable so the arithmetic is testable without sleeping."""
    key = _normalise_domain(domain)
    if not key:
        return 0.0
    current = time.monotonic() if now is None else now
    start_at = max(current, _next_slot_at.get(key, 0.0))
    _next_slot_at[key] = start_at + MIN_DOMAIN_INTERVAL_S
    return max(0.0, start_at - current)


def reset_domain_spacing() -> None:
    """Forget every reservation (tests; a caller never needs this)."""
    _next_slot_at.clear()


async def _await_domain_slot(domain: str) -> None:
    wait = reserve_domain_slot(domain)
    if wait > 0:
        await asyncio.sleep(wait)


# ------------------------------------------------------------------- transport


def _curl_get(url: str, timeout: int):
    """The ONLY place this module touches the network.

    Kept as a one-line module-level seam so the whole SSRF / redirect / retry /
    spacing machinery above it is exercised offline in tests by replacing this
    function — no test ever needs to reach for a real socket, and no code path
    can slip past the validation by calling curl directly.

    ``allow_redirects=False`` is mandatory: the hop loop must inspect and
    validate every ``Location`` itself."""
    from curl_cffi import requests as curl_requests

    return curl_requests.get(
        url, impersonate="chrome", timeout=timeout, allow_redirects=False,
    )


def _hop_is_allowed(url: str, domain: str) -> bool:
    """Both of the repo's own gates, applied to one URL.

    ``validate_external_url`` (app/utils/url_validator.py) blocks non-http(s),
    unresolvable hosts and private/loopback/link-local/reserved IPs;
    ``price_service._host_on_domain`` pins the hop to the source storefront (the
    bare domain or a subdomain of it). Fail-closed — an import or resolution
    problem is a refusal, never a pass."""
    try:
        from app.utils.url_validator import validate_external_url
        from app.services.price_service import _host_on_domain
    except Exception:  # noqa: BLE001 — no validator, no request
        logger.warning("[SHOPIFY_JS] SSRF validators unavailable — refusing fetch")
        return False
    try:
        return bool(validate_external_url(url)) and bool(_host_on_domain(url, domain))
    except Exception:  # noqa: BLE001 — fail closed
        return False


async def _fetch_once(js_url: str, domain: str) -> Tuple[Optional[int], Optional[str]]:
    """One attempt: redirect-validating same-site GET.

    Returns ``(status_code, body_text)``; ``(None, None)`` on a blocked hop, a
    redirect-cap breach or any exception. The status is returned rather than
    swallowed because the 503 retry policy needs to see it — this is the one
    reason we do not just call ``curl_fetch_html_same_site``, which collapses
    every non-200 into ``None``."""
    current = js_url
    for _ in range(MAX_REDIRECTS + 1):
        if not _hop_is_allowed(current, domain):
            logger.info("[SHOPIFY_JS] blocked hop for %s", domain)
            return None, None
        await _await_domain_slot(domain)
        try:
            resp = await asyncio.to_thread(_curl_get, current, HTTP_TIMEOUT)
        except Exception as e:  # noqa: BLE001 — a fetch never raises outward
            logger.info("[SHOPIFY_JS] fetch failed for %s: %s", domain, e)
            return None, None

        status = getattr(resp, "status_code", None)
        if isinstance(status, int) and 300 <= status < 400:
            headers = getattr(resp, "headers", None) or {}
            location = headers.get("Location") or headers.get("location")
            if not location:
                return None, None
            current = urljoin(current, location)
            continue
        return status, (getattr(resp, "text", None) or "")

    logger.info("[SHOPIFY_JS] redirect cap exceeded for %s", domain)
    return None, None


# ---------------------------------------------------------------------- parse


# BLOCKER 3 — the ceiling that makes both helpers below TOTAL.
#
# ``_to_major`` divides by 100.0, and ``int / float`` raises **OverflowError**
# ("int too large to convert to float") for any int past ~1e308 — so an
# unbounded ``_to_minor`` hands ``_to_major`` a live grenade. A cap is also the
# only way to reject a huge-but-finite int, which no isfinite() check can see:
# Python ints are arbitrary precision, so ``{"price": 10**400}`` is a perfectly
# well-formed JSON number.
#
# 10**12 minor units is 10,000,000,000 major units. No storefront on any Shopify
# plan sells anything at ten billion of any currency, so this can only ever
# reject corrupt or hostile data — while sitting ~296 orders of magnitude below
# the float conversion limit.
_MAX_MINOR_UNITS = 10 ** 12


def _to_minor(value: Any) -> Optional[int]:
    """Shopify minor units (integer cents) or ``None``. Never raises.

    Accepts the int the feed actually ships and the numeric string a proxy
    occasionally substitutes; rejects everything else, and rejects negatives
    (a negative price is corrupt data, not a discount).

    BLOCKER 3 — three hostile inputs crashed the previous shape, none of which
    ``except (TypeError, ValueError)`` could see:
      * ``"1e400"`` -> ``float()`` returns ``inf`` WITHOUT raising, then
        ``int(inf)`` raises **OverflowError**;
      * a real ``float('inf')`` — which arrives without ever being a string,
        because Python's json module parses a blob's bare ``Infinity`` token
        into an actual inf — took the float branch, where ``inf >= 0`` is True,
        into the same ``int(inf)`` OverflowError;
      * ``10**400`` as a bare int passed straight through, and detonated one
        call later inside ``_to_major``'s division.
    ``float('nan')`` was the only one that happened to be safe, and only by
    accident: ``nan >= 0`` is False. All four are now rejected on purpose."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        n = value
    elif isinstance(value, float):
        if not math.isfinite(value):
            return None
        n = int(value)
    elif isinstance(value, str):
        text = value.strip()
        # "_" — float("1_000") is 1000.0 because Python allows underscores in
        # numeric LITERALS. No price feed writes them; accepting it would invent
        # a number out of a malformed field.
        if not text or "_" in text:
            return None
        try:
            parsed = float(text)
        except (TypeError, ValueError, OverflowError):
            return None
        if not math.isfinite(parsed):
            return None
        n = int(parsed)
    else:
        return None
    return n if 0 <= n <= _MAX_MINOR_UNITS else None


def _to_major(minor: Optional[int]) -> Optional[float]:
    """Minor units -> major units. ALWAYS /100 (see rule 1 in the module docstring).

    ``round(..., 2)`` only removes binary-float dust: dividing an integer by 100
    can never legitimately produce a third decimal.

    The range re-check is deliberate belt-and-braces, not redundancy: every
    caller today feeds this a ``_to_minor`` result, but ``int / float`` raises
    OverflowError past ~1e308, so a future caller passing a raw feed integer
    would crash here rather than get None (BLOCKER 3)."""
    if minor is None or not isinstance(minor, int) or isinstance(minor, bool):
        return None
    if not 0 <= minor <= _MAX_MINOR_UNITS:
        return None
    return round(minor / 100.0, 2)


def parse_shopify_pdp_json(
    payload: Any,
    *,
    product_url: Optional[str] = None,
    json_url: Optional[str] = None,
    domain: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Normalise a ``{pdp}.js`` body (JSON text or an already-parsed dict).

    Pure and offline — no network, no flag, no clock. Returns ``None`` for
    anything that is not a Shopify product object with at least one usable
    variant price (an HTML 404 page, a ``products.json`` collection, a variant
    list of junk). Never raises."""
    data = payload
    if isinstance(payload, (str, bytes, bytearray)):
        try:
            data = json.loads(payload)
        except Exception:  # noqa: BLE001 — a non-JSON body is an honest miss
            return None
    if not isinstance(data, dict):
        return None

    raw_variants = data.get("variants")
    if not isinstance(raw_variants, list):
        return None
    variants = [v for v in raw_variants if isinstance(v, dict)]
    if not variants:
        return None

    # Rule 3 — availability is the AND of the two signals the feed publishes.
    top_available = bool(data.get("available"))
    priced_available: List[Tuple[int, Dict[str, Any]]] = []
    for v in variants:
        if not v.get("available"):
            continue
        minor = _to_minor(v.get("price"))
        if minor is not None:
            priced_available.append((minor, v))

    if priced_available:
        # Rule 1 — the floor of what a shopper can actually buy today.
        price_minor, chosen = min(priced_available, key=lambda pair: pair[0])
        price_basis = "available_variant_min"
    else:
        # Rule 2 — nothing is buyable. Report the product price the store itself
        # displays and flag it; do NOT widen rule 1 to all variants.
        chosen = variants[0]
        price_minor = _to_minor(data.get("price"))
        if price_minor is None:
            price_minor = _to_minor(chosen.get("price"))
        price_basis = "product_price_no_stock"

    if price_minor is None:
        return None

    # Rule 4 — a compare-at only counts when it is strictly above the price.
    compare_minor = _to_minor(chosen.get("compare_at_price"))
    if compare_minor is None:
        compare_minor = _to_minor(data.get("compare_at_price"))
    list_price = (
        _to_major(compare_minor)
        if compare_minor is not None and compare_minor > price_minor
        else None
    )

    tags = data.get("tags")
    images = data.get("images")
    options = data.get("options")

    return {
        "source": "shopify_pdp_json",
        "product_url": product_url,
        "json_url": json_url,
        "domain": _normalise_domain(domain) or None,
        "product_id": data.get("id"),
        "handle": data.get("handle"),
        "title": data.get("title"),
        # Price block.
        "price": _to_major(price_minor),
        "price_minor": price_minor,
        "list_price": list_price,
        "price_basis": price_basis,
        "in_stock": bool(priced_available) and top_available,
        "product_available_flag": top_available,
        "variant_count": len(variants),
        "available_variant_count": sum(1 for v in variants if v.get("available")),
        "price_min": _to_major(_to_minor(data.get("price_min"))),
        "price_max": _to_major(_to_minor(data.get("price_max"))),
        # Selected variant.
        "variant_id": chosen.get("id"),
        "sku": chosen.get("sku") or None,
        "variant_title": chosen.get("title"),
        # Signal / capture surface — free on a node we already parsed.
        "vendor": data.get("vendor"),
        "product_type": data.get("type") or data.get("product_type"),
        # `{pdp}.js` calls it `description`; `products.json` calls it `body_html`.
        # Normalise to body_html so both feeds look identical to a caller.
        "body_html": data.get("body_html") or data.get("description") or "",
        "tags": list(tags) if isinstance(tags, list) else [],
        "options": list(options) if isinstance(options, list) else [],
        "featured_image": data.get("featured_image"),
        "images": list(images) if isinstance(images, list) else [],
        "variants": variants,
    }


# ---------------------------------------------------------------------- fetch


async def fetch_shopify_pdp_json(pdp_url: str) -> Optional[Dict[str, Any]]:
    """``GET {pdp_url}.js`` and return the normalised dict, or ``None``.

    ``None`` on: the flag being off (no network at all), an unusable URL, a
    blocked SSRF hop, any non-200 after the 503 policy, a non-product body, or
    any exception. The caller is expected to fall through to the HTML cascade on
    ``None`` — this adapter is additive, never authoritative.

    503 is the storefront's burst-throttle answer, so it is retried EXACTLY
    once, and the retry waits out a fresh per-domain slot rather than hammering
    the throttle. Every other status is a single attempt."""
    if not shopify_pdp_json_enabled():
        return None

    js_url = build_pdp_json_url(pdp_url)
    if not js_url:
        return None

    host = urlparse(js_url).hostname or ""
    domain = _normalise_domain(host)
    if not domain:
        return None

    try:
        body = await _fetch_feed_body(js_url, domain, log_tag="SHOPIFY_JS")
        if not body:
            return None

        product_url = _strip_feed_suffix(js_url, ".js")
        return parse_shopify_pdp_json(
            body, product_url=product_url, json_url=js_url, domain=domain,
        )
    except Exception as e:  # noqa: BLE001 — the adapter never raises outward
        logger.warning("[SHOPIFY_JS] unexpected failure for %s: %s", domain, e)
        return None


async def _fetch_feed_body(
    feed_url: str, domain: str, *, log_tag: str = "SHOPIFY_JS",
) -> Optional[str]:
    """One per-handle feed GET with the measured 503 policy. Body text or None.

    503 is the storefront's burst-throttle answer, so it is retried EXACTLY
    once, and the retry waits out a fresh per-domain slot rather than hammering
    the throttle. Every other status is a single attempt.

    Shared by the ``.js`` and ``.json`` feeds on purpose: they are two endpoints
    of ONE storefront, behind one rate limiter and one redirect/SSRF policy, so
    a second copy of this loop would be a second place for those rules to drift."""
    status, body = await _fetch_once(feed_url, domain)
    if status == 503:
        logger.info("[%s] 503 for %s — retrying once", log_tag, domain)
        status, body = await _fetch_once(feed_url, domain)
    if status != 200 or not body:
        if status is not None and status != 200:
            logger.info("[%s] HTTP %s for %s", log_tag, status, domain)
        return None
    return body


def _strip_feed_suffix(feed_url: str, suffix: str) -> str:
    """``https://host/products/x.json`` -> ``https://host/products/x``."""
    parsed = urlparse(feed_url)
    path = parsed.path
    if path.lower().endswith(suffix):
        path = path[: -len(suffix)]
    return urlunparse((parsed.scheme, parsed.netloc, path, "", "", ""))


# ============================================================================
# M10 TRACK A / UNIT A4 — the UCP free-channel price adapter
# ============================================================================
# ``GET /products/{handle}.json`` — the OTHER per-handle Shopify feed, and the
# first channel in this codebase where the CURRENCY IS AN OBSERVED FACT.
#
# MEASURED (M9 `measure-ucp-free`, E4 Probe A, 2026-08-30: 55 live GETs across
# the 6 UCP-advertising hosts, throttle 3.2s, robots fetched and enforced per
# host, no MCP handshake). 34 handles tried, 32 x HTTP 200, and on all 32 the
# variant carries BOTH a major-unit decimal ``price`` and a self-declared
# ``price_currency`` — 32/32 equal to the registry currency. Verbatim:
#
#     "price": "20.000", "price_currency": "BHD",
#     "compare_at_price": "", "compare_at_price_currency": ""
#
# WHY THIS MATTERS MORE THAN ONE MORE ADAPTER. Everywhere else in this service
# the currency is something we ASK for and then hope the page agrees with — the
# failure mode UNIT A1 exists to fix, where a bare-brand query on faces.ae
# shipped 1515 AED labelled BHD, about 9.8x. On this channel nothing is asked:
# the merchant's own endpoint STATES the code next to the number it belongs to.
# So the registry is demoted to a fallback, and the self-declared code wins.
#
# THE FOUR RULES, all measured — do not "improve" them from first principles.
#
# 1. THE PRICE IS ALREADY IN MAJOR UNITS. It is a decimal string scaled to the
#    currency's own ISO 4217 minor-unit exponent (BHD/OMR 3dp, AED/SAR/QAR 2dp),
#    and it goes through ``price_service.parse_money`` — THE canonical parser —
#    with the resolved currency. There is NO division on this channel, and the
#    ``.js`` helpers ``_to_minor``/``_to_major`` must never see these strings.
#    THE PIN: om.swissarabian.com/products/oud-malaki is ``1720`` on ``.js`` and
#    ``"17.200"`` OMR on ``.json``. 1720/100 = 17.20 — NOT /1000, which is why
#    the ``.js`` adapter needs a fixed divisor at all. Feed "17.200" to that
#    divisor chain and you get 0.17: a 100x under-price that wins every
#    cheapest-price comparison downstream. The decimal string removes the
#    divisor question rather than answering it.
# 2. A RESOLVABLE SELF-DECLARED ``price_currency`` BEATS THE REGISTRY ROW; an
#    absent or unresolvable one falls back to the registry; with NEITHER we
#    ABSTAIN. Never fabricate a currency (Decision-F) — an unlabelled amount is
#    a wrong-price stamp waiting for a downstream default.
# 3. ``.json`` CARRIES NO ``available``. ``.js`` carries availability but no
#    currency; the two feeds are COMPLEMENTARY, not layered. So availability is
#    reported as None (unknown) and the ``.js`` companion is fetched ONLY when a
#    caller actually requires in-stock filtering — one extra free GET, bought
#    deliberately, never speculatively.
# 4. ``/collections/all/products.json`` is CURRENCY-BLIND on all 6 hosts and is
#    a discovery channel only. The parser rejects that envelope on purpose so it
#    can never be mistaken for this one.
#
# FLAG — ``ENABLE_UCP_JSON_PRICE``, DEFAULT **OFF**. This adds a network call,
# so it ships dormant. Read per call from ``os.getenv`` (the
# ``price_service.exact_gate_enabled`` idiom) — never cached at import.


def ucp_json_price_enabled() -> bool:
    """True iff the UCP ``/products/{handle}.json`` channel is active (**OFF**).

    Default OFF because it adds a NETWORK call per PDP. Deliberately INDEPENDENT
    of ``ENABLE_SHOPIFY_PDP_JSON``: that flag gates the ``.js`` variant feed,
    this one gates the ``.json`` currency feed, and the two answer different
    questions on different evidence. Rolling one back must not roll back the
    other.

    Uses the repo's default-OFF idiom (an explicit truthy allow-list) so an
    unset, empty or misspelled value leaves the network call OFF."""
    return os.getenv("ENABLE_UCP_JSON_PRICE", "false").strip().lower() in (
        "true", "1", "yes", "on",
    )


def build_pdp_products_json_url(pdp_url: Optional[str]) -> Optional[str]:
    """``https://host/products/handle`` -> ``.../handle.json``.

    ``.js`` is stripped first, because the two per-handle feeds are SIBLINGS:
    a caller holding the variant-feed URL wants the currency feed, not the 404
    that ``/products/x.js.json`` returns."""
    return _build_pdp_feed_url(pdp_url, ".json", strip_siblings=(".js",))


def is_shopify_pdp_path(pdp_url: Optional[str]) -> bool:
    """True iff the URL's PATH has the Shopify per-product shape.

    THE CHEAP HALF OF THE CHANNEL PROBE, and the reason it exists: with the flag
    on, an ungated adapter would issue a ``.json`` GET against every no-price
    page the cascade reaches — most of which are not Shopify at all. That is a
    cost we would be spending on other people's servers to learn something the
    URL already tells us.

    Shopify serves a product at a path whose LAST segment follows a
    ``/products/`` segment. That covers the shapes the measured hosts actually
    use — ``/products/handle``, ``/collections/all/products/handle`` and the
    locale-prefixed ``/en-bh/products/handle`` — while rejecting the collection
    and search paths that would return the currency-blind discovery envelope.

    This is a NECESSARY condition, never a sufficient one: the parser still has
    to see a real product envelope come back (rule 4). A path that looks right
    on a host that is not Shopify simply 404s and the adapter returns None."""
    if not pdp_url or not isinstance(pdp_url, str):
        return False
    try:
        path = urlparse(pdp_url.strip()).path or ""
    except Exception:  # noqa: BLE001 — a malformed URL is not a PDP
        return False
    segments = [seg for seg in path.split("/") if seg]
    if len(segments) < 2:
        return False
    handle = segments[-1]
    for suffix in (".json", ".js"):
        if handle.lower().endswith(suffix):
            handle = handle[: -len(suffix)]
            break
    return bool(handle) and segments[-2].lower() == "products"


def _registry_currency_for_host(host: Optional[str]) -> Optional[str]:
    """The registry row's expected currency for ``host``, or None.

    This is the FALLBACK only — rule 2 above. Lazy-imported (source_router pulls
    in price_service, which imports nothing from here) and fail-soft: no row, no
    registry, or any error means "no fallback", which makes the adapter abstain
    rather than guess."""
    key = _normalise_domain(host)
    if not key:
        return None
    try:
        from app.services.source_router import SOURCE_REGISTRY
    except Exception:  # noqa: BLE001 — no registry, no fallback
        return None
    try:
        for source in SOURCE_REGISTRY:
            domain = _normalise_domain(getattr(source, "domain", ""))
            if not domain:
                continue
            if key == domain or key.endswith("." + domain):
                code = (getattr(source, "currency", "") or "").strip().upper()
                if code:
                    return code
    except Exception:  # noqa: BLE001 — a selector must never break a fetch
        return None
    return None


def parse_ucp_products_json(
    payload: Any,
    *,
    product_url: Optional[str] = None,
    json_url: Optional[str] = None,
    domain: Optional[str] = None,
    registry_currency: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Normalise a ``/products/{handle}.json`` body (JSON text or parsed dict).

    Pure and offline — no network, no flag, no clock. Returns ``None`` for
    anything that is not a single Shopify product with at least one variant
    carrying both a parseable major-unit price AND a resolvable currency. Never
    raises.

    ``priced_variants`` is the load-bearing output: one entry per usable
    variant, each with its own resolved ``currency`` and ``currency_source``,
    because Shopify states the currency PER VARIANT. Variant SELECTION is
    deliberately NOT done here — that is the identity machinery's job, and this
    stays a parser."""
    data = payload
    if isinstance(payload, (str, bytes, bytearray)):
        try:
            data = json.loads(payload)
        except Exception:  # noqa: BLE001 — a non-JSON body is an honest miss
            return None
    if not isinstance(data, dict):
        return None

    # Rule 4 — the single-product envelope only. ``{"products": [...]}`` is the
    # COLLECTION feed, which is currency-blind on all 6 measured hosts; accepting
    # it here would silently re-introduce the registry-guess this unit removes.
    product = data.get("product")
    if not isinstance(product, dict):
        if "products" in data or "variants" not in data:
            return None
        product = data  # a bare product object, unwrapped by a caller

    raw_variants = product.get("variants")
    if not isinstance(raw_variants, list):
        return None
    variants = [v for v in raw_variants if isinstance(v, dict)]
    if not variants:
        return None

    from app.services.price_service import _normalize_currency_code, parse_money

    fallback = _normalize_currency_code(registry_currency)

    priced: List[Dict[str, Any]] = []
    for variant in variants:
        # Rule 2 — the merchant's own statement first, the registry second.
        declared = _normalize_currency_code(variant.get("price_currency"))
        currency = declared or fallback
        if currency is None:
            continue
        # Rule 1 — major units, canonical parser, NO divisor.
        amount = parse_money(variant.get("price"), currency)
        if amount is None or amount <= 0:
            continue
        # A compare-at is a discount only when it is in the SAME currency and
        # strictly above the price. Many themes write "" or 0 for "none", and a
        # compare-at equal to the price is not a discount.
        compare_currency = (
            _normalize_currency_code(variant.get("compare_at_price_currency"))
            or currency
        )
        list_price = None
        if compare_currency == currency:
            compare = parse_money(variant.get("compare_at_price"), currency)
            if compare is not None and compare > amount:
                list_price = compare
        priced.append({
            "variant": variant,
            "amount": amount,
            "currency": currency,
            "currency_source": "self_declared" if declared else "registry",
            "list_price": list_price,
        })

    if not priced:
        return None

    # Feed order, NOT a selection: the first usable variant so the dict answers
    # "what does this feed say" on its own. A caller that must choose between
    # variants uses ``priced_variants`` and the shared discriminator.
    first = priced[0]
    tags = product.get("tags")
    images = product.get("images")
    options = product.get("options")

    return {
        "source": "ucp_products_json",
        "product_url": product_url,
        "json_url": json_url,
        "domain": _normalise_domain(domain) or None,
        "product_id": product.get("id"),
        "handle": product.get("handle"),
        "title": product.get("title"),
        # Price block — major units, currency observed.
        "price": first["amount"],
        "currency": first["currency"],
        "currency_source": first["currency_source"],
        "list_price": first["list_price"],
        "registry_currency": fallback,
        "price_basis": "ucp_json_variant",
        # Rule 3 — this feed publishes no availability. Claiming True would be a
        # fabrication; claiming False would pend a live product.
        "in_stock": None,
        "availability_known": False,
        "variant_count": len(variants),
        "variant_id": first["variant"].get("id"),
        "sku": first["variant"].get("sku") or None,
        "variant_title": first["variant"].get("title"),
        "priced_variants": priced,
        # Signal / capture surface — free on a node we already parsed. body_html
        # ships inside this same envelope, which is where the measured 15-of-32
        # missing variant sizes are recoverable with no extra request.
        "vendor": product.get("vendor"),
        "product_type": product.get("product_type") or product.get("type"),
        "body_html": product.get("body_html") or product.get("description") or "",
        "tags": list(tags) if isinstance(tags, list) else [],
        "options": list(options) if isinstance(options, list) else [],
        "featured_image": product.get("image") or product.get("featured_image"),
        "images": list(images) if isinstance(images, list) else [],
        "variants": variants,
    }


async def fetch_ucp_json_product(
    pdp_url: str, *, registry_currency: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """``GET {pdp}/products/{handle}.json`` -> the normalised dict, or ``None``.

    ``None`` on: the flag being off (no network at all), an unusable URL, a
    blocked SSRF hop, any non-200 after the 503 policy, a non-product body, or
    any exception. ``registry_currency`` defaults to the host's registry row and
    is only ever the FALLBACK (rule 2)."""
    if not ucp_json_price_enabled():
        return None

    # The cheap half of the channel probe — never spend a request to learn
    # something the URL already says.
    if not is_shopify_pdp_path(pdp_url):
        return None

    json_url = build_pdp_products_json_url(pdp_url)
    if not json_url:
        return None

    host = urlparse(json_url).hostname or ""
    domain = _normalise_domain(host)
    if not domain:
        return None

    try:
        body = await _fetch_feed_body(json_url, domain, log_tag="UCP_JSON")
        if not body:
            return None
        fallback = registry_currency
        if fallback is None:
            fallback = _registry_currency_for_host(host)
        return parse_ucp_products_json(
            body,
            product_url=_strip_feed_suffix(json_url, ".json"),
            json_url=json_url,
            domain=domain,
            registry_currency=fallback,
        )
    except Exception as e:  # noqa: BLE001 — the adapter never raises outward
        logger.warning("[UCP_JSON] unexpected failure for %s: %s", domain, e)
        return None


async def fetch_ucp_json_availability(
    pdp_url: str, *, variant_id: Any = None,
) -> Optional[bool]:
    """The ``.js`` companion GET — rule 3. True / False / None (unknown).

    Called ONLY when a caller requires in-stock filtering, because ``.json``
    publishes no availability and this costs a second request. Reuses the
    shipped ``.js`` parser rather than re-reading that feed's minor-unit rules,
    and is gated by THIS unit's flag (the ``.js`` price adapter's own flag gates
    its own price path, which this does not use)."""
    if not ucp_json_price_enabled():
        return None

    js_url = build_pdp_json_url(pdp_url)
    if not js_url:
        return None
    domain = _normalise_domain(urlparse(js_url).hostname or "")
    if not domain:
        return None

    try:
        body = await _fetch_feed_body(js_url, domain, log_tag="UCP_JSON")
        if not body:
            return None
        parsed = parse_shopify_pdp_json(body, json_url=js_url, domain=domain)
        if not parsed:
            return None
        if variant_id is not None:
            for variant in parsed.get("variants") or []:
                if isinstance(variant, dict) and variant.get("id") == variant_id:
                    return bool(variant.get("available")) and bool(
                        parsed.get("product_available_flag")
                    )
        return bool(parsed.get("in_stock"))
    except Exception as e:  # noqa: BLE001 — availability is best-effort
        logger.info("[UCP_JSON] availability probe failed for %s: %s", domain, e)
        return None


async def fetch_ucp_json_price(
    pdp_url: str,
    product_name: str,
    currency: str = "BHD",
    resolved_category: Optional[str] = None,
    *,
    require_in_stock: bool = False,
    registry_currency: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """The cascade-facing entry: a standard price dict for a UCP PDP, or None.

    Threads the SAME identity/size/label machinery every sibling adapter uses —
    a cheap free channel is not a licence to skip the exact-SKU gate, and the
    measured search probe showed size disambiguation stays a MATCHING problem
    even when the fetch is perfect (sa.mubkhar returned ``-15ml``, ``-30-ml``
    and ``-all-over-spray-150ml`` for a 150ml query).

    Labelling follows the sibling ``/products.json`` matcher exactly: a price
    already in the target currency is genuine (``shopify_json``); one we had to
    convert is stamped with the canonical converted sentinel (``converted_usd``)
    so a converted GCC figure can never bank as a genuine BH price."""
    if not ucp_json_price_enabled():
        return None
    try:
        from app.services import price_service as ps

        product = await fetch_ucp_json_product(
            pdp_url, registry_currency=registry_currency,
        )
        if not product:
            return None

        title = product.get("title") or ""
        if not title:
            return None
        if ps.is_counterfeit_listing(title) or ps.is_accessory(title):
            return None

        category = ps._resolve_extractor_category(resolved_category, product_name)
        candidate_brand = ps.normalize_candidate_brand(product.get("vendor"))
        match_score = 0.0
        if product_name:
            if not ps.numbers_match(product_name, title):
                return None
            if not ps.strict_title_match(
                product_name, title, candidate_brand=candidate_brand,
            ):
                return None
            if ps.variant_mismatch(product_name, title):
                return None
            if not ps._selection_match(
                product_name, title, category, candidate_brand=candidate_brand,
            ):
                return None
            p_words = ps.normalize_words(product_name)
            t_words = ps.normalize_words(title)
            match_score = len(p_words & t_words) / len(p_words) if p_words else 0.0
            if p_words and match_score < 0.4:
                return None

        priced = product.get("priced_variants") or []
        if not priced:
            return None

        # Variant binding — the A3 policy, via the SHARED discriminator: the
        # size stated on the query wins, an unbindable spread PENDS, and the
        # smallest is never served as if it were the shelf price.
        if ps.variant_min_guard_enabled():
            chosen = ps._select_shopify_variant(
                [entry["variant"] for entry in priced],
                product_name, title, category, ps.is_luxury_brand(product_name),
            )
            if chosen is None:
                return None
            entry = next((e for e in priced if e["variant"] is chosen), None)
            if entry is None:
                return None
        else:
            entry = priced[0]

        amount = entry["amount"]
        store_currency = entry["currency"]
        target_currency = (currency or "BHD").upper()
        needs_conversion = store_currency != target_currency
        if needs_conversion:
            from app.services.exchange_rate_service import FALLBACK_RATES
            if store_currency not in FALLBACK_RATES or target_currency != "BHD":
                logger.info(
                    "[UCP_JSON] %s: %s not safely convertible to %s — skipping hit",
                    product.get("domain"), store_currency, target_currency,
                )
                return None
            amount = ps._convert_to_bhd(amount, store_currency)
            if amount is None or amount <= 0:
                return None

        # Rule 3 — availability is bought only when it was asked for.
        in_stock: Optional[bool] = None
        if require_in_stock:
            in_stock = await fetch_ucp_json_availability(
                pdp_url, variant_id=entry["variant"].get("id"),
            )
            if in_stock is not True:
                return None

        variant_title = str(entry["variant"].get("title") or "")
        signal_text = f"{title} {variant_title}".strip()
        sizes = ps.extract_sizes_ml(signal_text)
        size = (sorted(sizes)[0] + "ml") if sizes else None
        concentration = ps.extract_concentration(signal_text)
        if ps.wide_signal_text_enabled() and (size is None or concentration is None):
            # NARROW-FIRST, additive only: body_html rides in this same envelope
            # (rule 3's residual-size recovery), but it is marketing copy that
            # names flankers and bundle contents, so a widened value may only
            # FILL a None and a widened size is taken only when the whole widened
            # text agrees on exactly one.
            wide = ps._wide_signal_capture_text(signal_text, product)
            if concentration is None:
                concentration = ps.extract_concentration(wide)
            if size is None:
                wide_sizes = ps.extract_sizes_ml(wide)
                if len(wide_sizes) == 1:
                    size = next(iter(wide_sizes)) + "ml"

        return {
            "amount": round(amount, 2),
            "currency": target_currency,
            "original_currency": store_currency,
            "retailer": product.get("domain") or "",
            "url": product.get("product_url") or pdp_url,
            "in_stock": in_stock,
            "confidence": round(min(0.7 + match_score * 0.3, 1.0), 2),
            "estimated": False,
            "source_method": (
                "converted_usd" if needs_conversion else "shopify_json"
            ),
            # Provenance of the LABEL, not of the number: on the measured corpus
            # registry and merchant agree 32/32, so without this the two are
            # indistinguishable after the fact and a coincidence reads as evidence.
            "price_currency_source": entry["currency_source"],
            "list_price": entry["list_price"],
            "concentration": concentration,
            "size": size,
            "title": title,
            "match_score": round(match_score, 3),
        }
    except Exception as e:  # noqa: BLE001 — the adapter never raises outward
        logger.warning("[UCP_JSON] price failed for %s: %s", pdp_url, e)
        return None
