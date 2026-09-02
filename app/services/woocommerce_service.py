"""WooCommerce Store API price adapter — R1 (genuine BH/GCC pricing).

A generic $0 adapter for the long tail of WooCommerce storefronts that expose
the PUBLIC, unauthenticated Store API:

    GET https://<domain>/wp-json/wc/store/products?search=<term>&per_page=20

(alias `.../wc/store/v1/products` — identical; we fall back to it on a 404).
No auth / cookie / nonce. Prices come back in MINOR units with a per-response
`currency_minor_unit`, so the divisor MUST be read from the response — a
hardcoded /100 or /1000 silently 10x/100x-errors real stores (BHD is seen as
both 3 and 2 decimals; OMR as 1/2/3; AED/QAR as 0).

Flow:
  1. ENABLE_PAGE_SCRAPE gate → None if off.
  2. One curl_cffi (impersonate=chrome) GET with WAF-friendly default headers
     (Referer + Sec-Fetch-* — they cost nothing and unlock stores that 403
     without them).
  3. STRICT title match (reuses price_service.strict_title_match / numbers_match
     / variant_mismatch / is_counterfeit_listing / is_accessory) so a fuzzy hit
     is REJECTED, never shipped as a wrong-brand price.
  4. Genuine-vs-converted by the response's ACTUAL `currency_code`: native BHD →
     `source_method="woo_store_api"` (genuine, 7d cache, counts in the KPI); any
     other GCC currency → convert via price_service._convert_to_bhd and stamp the
     LITERAL `"converted_usd"` (NEVER a per-platform *_converted string).
  5. is_price_showable plausibility guard + L2 content-safety before returning.

Returns a price dict (see the module docstring of the SPEC §2.1) or None on
miss / error. NEVER raises — best-effort, never critical-path.
"""
import asyncio
import html
import logging
from typing import Any, Dict, List, Optional

from curl_cffi import requests as curl_requests

from app.services.price_service import (
    normalize_candidate_brand,
    ENABLE_PAGE_SCRAPE,
    _convert_to_bhd,
    _infer_category_from_query,
    _selection_match,
    build_adapter_search_terms,
    is_accessory_for_category,
    is_counterfeit_listing,
    is_price_showable,
    numbers_match,
    select_best,
    selection_primary_admits,
    strict_title_match,
    variant_min_guard_enabled,
    variant_mismatch,
)

logger = logging.getLogger(__name__)

# Genuine method string for native-BHD WooCommerce stores (pinned in BOTH
# _GENUINE_BH_SOURCE_METHODS and the eval mirror — grants the 7d TTL + KPI count).
_WOO_GENUINE_METHOD = "woo_store_api"

# Per-request timeout (s). The cascade also wraps the coro in a 10s
# _ADAPTER_TIMEOUT, so keep the inner curl timeout below that.
from app.services.adapter_timeouts import adapter_timeout
_WOO_TIMEOUT = adapter_timeout(10)  # M13-34: clamp under the per-source _timeout_none wrap

# Default headers. WAF stores (ownperfumes/purpleorchidbh/fragrancebh) 403 the
# JSON endpoint without the Sec-Fetch-* + Referer set, so make them DEFAULT —
# they cost nothing for non-WAF stores. (Referer is filled per-domain at call.)
_BASE_HEADERS = {
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Dest": "empty",
}


def _store_api_url(domain: str, term: str, versioned: bool = False) -> str:
    base = domain.rstrip("/")
    if not base.startswith("http"):
        base = f"https://{base}"
    seg = "wc/store/v1/products" if versioned else "wc/store/products"
    # curl_cffi handles param encoding via `params=`, but we build the path here.
    return f"{base}/wp-json/{seg}"


def _amount_from_prices(prices: Dict[str, Any]) -> Optional[float]:
    """Resolve a major-unit amount honoring the PER-RESPONSE minor unit.

    `prices.price` (string, minor units) preferred; a variable product may have
    `price` null with `price_range.min_amount` set instead. Both null → None.
    NEVER infers the divisor from the currency — reads currency_minor_unit.
    """
    if not isinstance(prices, dict):
        return None
    raw = prices.get("price")
    if raw in (None, "", "null"):
        price_range = prices.get("price_range")
        if isinstance(price_range, dict):
            raw = price_range.get("min_amount")
    if raw in (None, "", "null"):
        return None
    try:
        minor_raw = prices.get("currency_minor_unit")
        # Read per-response (the Store API always emits it). A present 0 MUST be
        # honored (AED/QAR no-division). Review gate-fix (LOW): if it is ever
        # utterly absent, default by the response's currency_code — a 3-decimal
        # currency (BHD/KWD/OMR) defaulting to 2 would 10x-error the price — rather
        # than a blanket 2.
        if minor_raw is not None:
            minor = int(minor_raw)
        else:
            _cc = str(prices.get("currency_code") or "").upper()
            minor = 3 if _cc in ("BHD", "KWD", "OMR") else 2
        if minor < 0:
            return None
        return int(str(raw)) / (10 ** minor)
    except (TypeError, ValueError):
        return None


def _woo_variable_spread(prices: Dict[str, Any]) -> bool:
    """True iff this is a VARIABLE product priced from a price_range with a real
    min != max spread (prices.price is null). Audit 2026-07-08: the Store API list
    response carries NO per-variation sizes, so _amount_from_prices returns the
    price_range MIN — a decant/cheapest variation that cannot be bound to the queried
    size. Serving it leaks a decant as the full bottle. A min == max range (apparel
    S/M/L all one price) or a simple product (single price) is NOT a spread."""
    if not isinstance(prices, dict):
        return False
    if prices.get("price") not in (None, "", "null"):
        return False  # simple product (single price) → never a spread
    pr = prices.get("price_range")
    if not isinstance(pr, dict):
        return False
    lo, hi = pr.get("min_amount"), pr.get("max_amount")
    if lo in (None, "", "null") or hi in (None, "", "null"):
        return False
    try:
        return int(str(lo)) != int(str(hi))
    except (TypeError, ValueError):
        return False


def _match_woo_product(
    products: List[Dict[str, Any]], product_name: str, currency: str,
    resolved_category: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Pick the best strict-matching hit and build the price dict, or None.

    Genuine-vs-converted is branched on the hit's ACTUAL currency_code.
    """
    if not isinstance(products, list):
        return None

    _category = (resolved_category or "").lower() or None if resolved_category else _infer_category_from_query(product_name)
    candidates: list = []

    for prod in products:
        if not isinstance(prod, dict):
            continue
        raw_name = prod.get("name") or ""
        title = html.unescape(raw_name).strip()
        if not title:
            continue

        # Strict no-fab gates — a fuzzy / wrong-brand / wrong-variant / accessory
        # / counterfeit hit is rejected, never shipped as a price.
        if is_counterfeit_listing(title):
            continue
        # SELECTION-PRIMARY acceptance (recon_cascade R2, Wave B4 — flag
        # ENABLE_ADAPTER_SELECTION_PRIMARY): strict tokenizes RAW, so a CORRECT
        # row is rejected on pure spacing/alias variance ("90ml" vs the live
        # perfumesclub "90 ml") that _selection_match below already collapses.
        # A strict PASS keeps the pre-change fast path; a strict FAIL now falls
        # through to the remaining chain (numbers / variant / accessory /
        # _selection_match) instead of hard-rejecting — GATED by
        # selection_primary_admits (Wave B-FIX): flag + the wrong-brand fence
        # (a padding-brand query needs brand evidence; Woo rows carry no brand
        # field, so a FASHION query's brand must appear in the title). Flag
        # OFF — or the exact gate OFF, which makes _selection_match a no-op
        # True — restores the exact pre-change hard gate.
        # Brand-implied match (2026-07-07) — the WooCommerce Store API carries the
        # product's OWN brand in the top-level `brands` array (brands[0].name) or,
        # when that taxonomy is unused, in the `pa_brand` product attribute
        # (terms[0].name). An own-brand store OMITS its brand from titles, so
        # requiring the query brand word rejected the exact SKU; this lets the
        # brand-omitted title pass while a WRONG-brand row keeps the query brand
        # required (candidate_brand drops only the candidate's own tokens;
        # _selection_match vets the SKU). Mirrors magento/occ; inert flag-OFF.
        _cand_brand = ""
        _brands = prod.get("brands")
        if isinstance(_brands, list) and _brands:
            _cand_brand = normalize_candidate_brand(_brands[0])
        if not _cand_brand:
            for _attr in (prod.get("attributes") or []):
                if not isinstance(_attr, dict):
                    continue
                if (str(_attr.get("taxonomy") or "").strip().lower() == "pa_brand"
                        or str(_attr.get("name") or "").strip().lower() == "brand"):
                    _terms = _attr.get("terms")
                    if isinstance(_terms, list) and _terms:
                        _cand_brand = normalize_candidate_brand(_terms[0])
                    break
        if (not strict_title_match(product_name, title, candidate_brand=_cand_brand)
                and not selection_primary_admits(
                    product_name, title, candidate_brand=_cand_brand,
                    category=_category)):
            continue
        if not numbers_match(product_name, title):
            continue
        if variant_mismatch(product_name, title):
            continue
        # Category-scoped (BF4, sweep OR-7): the bare 'skin' accessory keyword
        # must not reject genuine pharmacy titles ("...For Dry Skin", "All
        # Skin Types") when the resolved category is a pharmacy class; any
        # other accessory keyword still flags, non-pharmacy keeps the broad set.
        if (is_accessory_for_category(title, _category)
                and not is_accessory_for_category(product_name, _category)):
            continue
        # CORRECTNESS — identity + axis gate (S24->FE / EDP->EDT / 256->128 /
        # related-product leaks). No-op when the rollback flag is OFF.
        if not _selection_match(product_name, title, _category,
                                candidate_brand=_cand_brand):
            continue

        prices = prod.get("prices") or {}
        amount = _amount_from_prices(prices)
        if amount is None or amount <= 0:
            continue
        # Variant-min decant guard (audit 2026-07-08): a variable product whose price came
        # from a price_range with min != max — the min is the cheapest variation (a decant),
        # and the list response has no per-variation sizes to bind the queried size. PEND
        # (skip) rather than leak the decant as the bottle. Flag OFF → served as today.
        if variant_min_guard_enabled() and _woo_variable_spread(prices):
            continue

        currency_code = (prices.get("currency_code") or "").upper()

        if currency_code == "BHD":
            bhd_amount = round(amount, 3)
            source_method = _WOO_GENUINE_METHOD
            original_currency = None
        else:
            if not currency_code:
                # No currency on the hit → cannot safely stamp → skip.
                continue
            converted = _convert_to_bhd(amount, currency_code)
            # _convert_to_bhd returns the amount UNCHANGED (logs a warning) when
            # the currency is not in the rate table — that would mislabel a raw
            # foreign amount as BHD. Guard explicitly: unconvertible → skip.
            # EFFECTIVE-table membership (is_convertible — M21 W4: honours
            # ENABLE_EXTENDED_FALLBACK_RATES, the same table _convert_to_bhd
            # converts from; flag OFF it is exactly the old FALLBACK_RATES check).
            from app.services.exchange_rate_service import is_convertible
            if not is_convertible(currency_code):
                continue
            if converted is None:
                continue
            bhd_amount = round(converted, 3)
            source_method = "converted_usd"
            original_currency = currency_code

        permalink = prod.get("permalink") or ""
        in_stock = prod.get("is_in_stock")

        candidate: Dict[str, Any] = {
            "amount": bhd_amount,
            "currency": "BHD",
            "retailer": "",  # filled by caller
            "url": permalink,
            "estimated": False,
            "source_method": source_method,
            "title": title,
            "confidence": 0.9 if source_method == _WOO_GENUINE_METHOD else 0.85,
        }
        if isinstance(in_stock, bool):
            candidate["in_stock"] = in_stock
        if original_currency:
            candidate["original_currency"] = original_currency

        candidates.append(candidate)

    # CORRECTNESS — pick by retailer authority / variant precision, never cheapest;
    # in-stock ranked first, an only-OOS match still RETURNED flagged (the response
    # chokepoint pends it) so the adapter's "report OOS" contract is preserved.
    return select_best(candidates, product_name, _category, drop_out_of_stock=False)


def _do_get(url: str, params: Dict[str, Any], headers: Dict[str, str]):
    return curl_requests.get(
        url,
        params=params,
        headers=headers,
        impersonate="chrome",
        timeout=_WOO_TIMEOUT,
        allow_redirects=True,
    )


async def fetch_woocommerce_store_api_price(
    domain: str, product_name: str, currency: str = "BHD",
    resolved_category: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Genuine BH (or converted GCC) price from a WooCommerce Store API store.

    One GET to /wp-json/wc/store/products (search-filtered) → strict-match the
    query → a `woo_store_api` (BHD-native) or `converted_usd` (other GCC) price
    dict, or None.

    Missing-gate / non-200 / non-JSON / no-match / unsafe → None (verify-or-omit).
    NEVER raises. $0 — no Serper, no render.
    """
    if not ENABLE_PAGE_SCRAPE:
        return None
    if not domain or not product_name:
        return None

    headers = dict(_BASE_HEADERS)
    apex = domain.rstrip("/")
    if not apex.startswith("http"):
        headers["Referer"] = f"https://{apex}/"
    else:
        headers["Referer"] = apex.rstrip("/") + "/"

    payload = None
    # R1 retrieval-term ladder (build_adapter_search_terms): the full name
    # first; ONLY a ZERO-ROW 200 retries ONCE with the model-core term (the
    # store search is AND-restrictive — the canonical "Yves Saint Laurent
    # Black Opium Eau de Parfum 90ml" returns 0 rows where "Black Opium"
    # returns the exact SKU). A response WITH rows — matched or not — never
    # triggers a second search (latency pin); non-200/exception keeps the
    # legacy immediate-None (no retry against an erroring/WAF store).
    # Matching below runs against the ORIGINAL product_name, so wider
    # retrieval cannot widen acceptance.
    for term in build_adapter_search_terms(product_name, resolved_category):
        params = {"search": term, "per_page": 20}
        try:
            resp = await asyncio.to_thread(
                _do_get, _store_api_url(domain, term, versioned=False),
                params, headers,
            )
            if getattr(resp, "status_code", None) == 404:
                # Unversioned path missing → retry the /v1/ alias.
                resp = await asyncio.to_thread(
                    _do_get, _store_api_url(domain, term, versioned=True),
                    params, headers,
                )
            if getattr(resp, "status_code", None) != 200:
                logger.info(
                    "[PRICE] woo HTTP %s for '%s' (%s)",
                    getattr(resp, "status_code", "?"), product_name, domain,
                )
                return None
            payload = resp.json()
        except Exception as exc:  # noqa: BLE001 — a fetch/parse error is a miss, not a crash
            logger.warning("[PRICE] woo fetch failed for %s (%s): %s", product_name, domain, exc)
            return None
        if not (isinstance(payload, list) and not payload):
            break  # rows returned (even unmatched) — never a second search

    price = _match_woo_product(payload, product_name, currency, resolved_category=resolved_category)
    if not price:
        return None

    price["retailer"] = apex.replace("https://", "").replace("http://", "").rstrip("/")

    if not is_price_showable(product_name, price):
        return None

    try:
        from app.services.content_safety_service import get_content_safety_service
        _surface = f"{price.get('title', '')} {price['retailer']} {product_name}"
        if not get_content_safety_service().is_text_safe(_surface):
            logger.info("[content_safety] L2 dropped woo candidate for %s", product_name)
            return None
    except Exception:  # noqa: BLE001 — safety-service failure must not crash the adapter
        return None

    logger.info(
        "[PRICE] woo %s: %s %s for '%s' (%s)",
        price["source_method"], price["currency"], price["amount"],
        product_name, price["retailer"],
    )
    return price
