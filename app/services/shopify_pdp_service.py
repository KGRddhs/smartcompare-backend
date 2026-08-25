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

NOT WIRED IN. This module has ZERO call sites: nothing under ``app/`` imports
it, so no code path reaches it and the runtime is byte-identical to 8adaefb with
the flag in either position. Wiring it into the price cascade is a separate,
separately-reviewable change with its own flag decision.
"""

import asyncio
import json
import logging
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


def build_pdp_json_url(pdp_url: Optional[str]) -> Optional[str]:
    """``https://host/products/handle`` -> ``https://host/products/handle.js``.

    Query and fragment are stripped first: a PDP URL that arrives from search or
    a sitemap routinely carries ``?variant=...`` or UTM parameters, and
    ``/products/x?variant=1.js`` is a 404. A trailing slash is dropped so we
    never emit ``/products/x/.js``.

    A path that ALREADY ends in ``.js`` (any case) is returned as-is rather than
    doubled into ``.js.js`` — some callers hand us the feed URL directly.

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
    if path.lower().endswith(".js"):
        clean_path = path
    else:
        clean_path = path.rstrip("/") + ".js"

    # Drop params/query/fragment — only scheme, netloc and path survive.
    return urlunparse((parsed.scheme, parsed.netloc, clean_path, "", "", ""))


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


def _to_minor(value: Any) -> Optional[int]:
    """Shopify minor units (integer cents) or ``None``.

    Accepts the int the feed actually ships and the numeric string a proxy
    occasionally substitutes; rejects everything else, and rejects negatives
    (a negative price is corrupt data, not a discount)."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value if value >= 0 else None
    if isinstance(value, float):
        return int(value) if value >= 0 else None
    if isinstance(value, str):
        try:
            n = int(float(value.strip()))
        except (TypeError, ValueError):
            return None
        return n if n >= 0 else None
    return None


def _to_major(minor: Optional[int]) -> Optional[float]:
    """Minor units -> major units. ALWAYS /100 (see rule 1 in the module docstring).

    ``round(..., 2)`` only removes binary-float dust: dividing an integer by 100
    can never legitimately produce a third decimal."""
    if minor is None:
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
        status, body = await _fetch_once(js_url, domain)
        if status == 503:
            logger.info("[SHOPIFY_JS] 503 for %s — retrying once", domain)
            status, body = await _fetch_once(js_url, domain)
        if status != 200 or not body:
            if status is not None and status != 200:
                logger.info("[SHOPIFY_JS] HTTP %s for %s", status, domain)
            return None

        product_url = urlunparse(
            (
                urlparse(js_url).scheme,
                urlparse(js_url).netloc,
                urlparse(js_url).path[:-3],  # drop the ".js" we appended
                "", "", "",
            )
        )
        return parse_shopify_pdp_json(
            body, product_url=product_url, json_url=js_url, domain=domain,
        )
    except Exception as e:  # noqa: BLE001 — the adapter never raises outward
        logger.warning("[SHOPIFY_JS] unexpected failure for %s: %s", domain, e)
        return None
