"""noon-BH direct catalog+PDP price adapter (genuine-price KPI Wave C C3).

The vehicle for kpi-frag-002 + kpi-frag-005 and multi-source electronics/
fashion coverage (fix-ladder item 4/6; kpiE2E RS-5 = wire noon as a
first-class adapter instead of relying on organic retrieval). Contract from
the 2026-07-02 live recon (recon_electronics.json ``noon_contract`` +
recon_fragrances.json), which FALSIFIED the round-3/4 "search walled /
SAR-only" claim: the ``x-locale: en-bh`` HEADER (not a cookie, not the path)
flips ``/_svc/catalog/api/v3/search`` to the BHD Bahrain catalog over plain
curl_cffi ``impersonate="chrome"``.

Flow (two steps, both $0 — no Serper, no render credits):
  1. SEARCH ``GET https://www.noon.com/_svc/catalog/api/v3/search?q=&limit=10``
     with the HARD-PINNED ``x-locale: en-bh`` header. FAILURE MODE 1 (silent
     wrong-currency): without the header the response is the KSA/SAR catalog
     with an IDENTICAL shape and NO currency field anywhere in the hit —
     currency is therefore PINNED "BHD" from the header (the
     ALGOLIA_EXPLICIT_STORES pinned-currency pattern) and the header is
     unit-tested onto every request. hits[]: name / brand (NULLABLE — the
     Switch-2 bundle) / sku / url (bare slug) / price / sale_price /
     is_buyable / store_name. Current price = sale_price if not null else
     price (failure mode 6). Retrieval widens via the shared
     ``build_adapter_search_terms`` ladder (full name first; ONLY a zero-row
     response tries the core term; a transport failure STOPS — the F2
     politeness None-sentinel, never a retry against an erroring store).
  2. MATCH the full gate chain per hit — counterfeit / accessory-for-category
     (asymmetric) / numbers_match / strict-or-``selection_primary_admits``
     (the central wrong-brand fence) / variant_mismatch / ``_selection_match``
     — with ``candidate_brand = hits[].brand or ""``. Failure mode 4 (noisy
     relevance: cases/games/other-model rows interleave) is closed by this
     chain; the Mario-Kart-BUNDLE live proof is the token-add rejection pin.
  3. PDP CONFIRM ``GET https://www.noon.com/bahrain-en/{slug}/{sku}/p/`` →
     the Product JSON-LD (priceCurrency "BHD" verified explicitly — never
     assumed). AUTHORITY RULE: ``offers[0]`` IS the buy-box (live-proven:
     offers[0].price 294.23 == the PLP sale_price; offers[1] 266.09 is a
     CHEAPER non-buy-box seller that ``min()`` would mis-select) — the
     selector walks noon's OWN offer order and takes the FIRST offer the
     fail-closed guards admit (BHD ∧ not refurbished/renewed ∧ not explicit
     OOS ∧ above the implausible-low fragrance floor). Advancing past a
     guard-REJECTED offer preserves authority order; it is NEVER
     ``min(offers[].price)``. The identity gates re-run against the PDP's own
     JSON-LD name+brand before any amount is trusted.

source_method: reuses the JSON-LD page-scrape genuine method
``page_scrape_jsonld`` (∈ ``_GENUINE_BH_SOURCE_METHODS`` — 7d genuine TTL,
showable, eval-parity already mirrored; NO new method plumbing). The
marketplace seller (failure mode 5: gray-import Viola-UAE/callmateonline) is
stamped as ``price["seller"]``; noon's registry AUTHORITY stays at the
gcc-tier 1.5 row (sharafdg/extra rank above it — see the source_router row
comment), so a noon marketplace price never outranks the authoritative BH
electronics sources in select_best.

POLITENESS (failure mode 3 — rate-limits on rapid repeats): 0.8–1.2s spacing
between requests within one call, a per-call request cap
(``_MAX_REQUESTS_PER_CALL``), and the shared circuit breaker
(record_failure on 429/5xx/transport; is_circuit_closed fast-fails a
sustained outage).

NEVER raises — best-effort, never critical-path. Gated by ENABLE_PAGE_SCRAPE
+ ``is_price_showable`` + L2 content-safety, mirroring the unbxd/occ/salla
adapter file shape. NO cache writes inside the service (the consume in
structured_comparison_service owns cache/DB policy).
"""
import asyncio
import json
import logging
import random
import re
from html import unescape as html_unescape
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

from app.services.price_service import (
    ENABLE_PAGE_SCRAPE,
    _selection_match,
    build_adapter_search_terms,
    exact_gate_enabled,
    is_accessory_for_category,
    is_available_state,
    is_counterfeit_listing,
    is_implausible_low_fragrance_price,
    is_price_showable,
    normalize_words,
    numbers_match,
    selection_primary_admits,
    strict_title_match,
    variant_mismatch,
)
from app.services.api_budget_service import (
    is_circuit_closed,
    record_failure,
    record_success,
)

logger = logging.getLogger(__name__)

# Circuit-breaker provider label (provider-agnostic — record_failure/
# is_circuit_closed work for any provider string; the unbxd pattern).
_NOON_PROVIDER = "noon"

_HTTP_TIMEOUT = 8.0
_SEARCH_LIMIT = 10
_SEARCH_URL = "https://www.noon.com/_svc/catalog/api/v3/search?q={q}&limit={limit}"
_PDP_URL = "https://www.noon.com/bahrain-en/{slug}/{sku}/p/"

# HARD PIN (failure mode 1) — x-locale: en-bh flips the catalog to Bahrain/BHD
# (live-verified: 294.23 BHD vs 2499 SAR for the SAME sku without it; the
# nloc cookie does NOT work — only the header). Unit-pinned on every request.
_SEARCH_HEADERS: Dict[str, str] = {
    "x-locale": "en-bh",
    "x-platform": "web",
    "x-mp": "noon",
    "accept": "application/json",
}

# POLITENESS (failure mode 3): spacing between consecutive requests within one
# call + a hard per-call request cap (2 ladder searches + up to 2 PDP confirms).
_NOON_SPACING_RANGE = (0.8, 1.2)
_MAX_REQUESTS_PER_CALL = 4
# PDP confirms are bounded separately so a long match list can never spend the
# whole cap on confirms for one product.
_MAX_PDP_CONFIRMS = 2

# Offer rows in these conditions are DIFFERENT sellable units (recon variant &
# condition handling) — never attributed to the new-product query.
_REJECT_CONDITION_TOKENS = ("refurbished", "renewed", "used")

_LDJSON_RE = re.compile(
    r"<script[^>]*type=[\"']application/ld\+json[\"'][^>]*>(.*?)</script>",
    re.S | re.I,
)


# ---------------------------------------------------------------------------
# HTTP plumbing (politeness-spaced, capped, breaker-wired)
# ---------------------------------------------------------------------------

def _http_get(url: str, headers: Optional[Dict[str, str]] = None,
              timeout: float = _HTTP_TIMEOUT):
    """ONE synchronous curl_cffi GET (impersonate=chrome — plain curl is
    Akamai-walled, failure mode 2). Module-level seam so tests mock exactly
    the transport."""
    from curl_cffi import requests as curl_requests

    return curl_requests.get(
        url, headers=headers, impersonate="chrome", timeout=timeout,
        allow_redirects=True,
    )


async def _polite_sleep() -> None:
    """0.8–1.2s politeness gap between consecutive noon requests within one
    call (failure mode 3 — R3 observed rate-limits on rapid repeats)."""
    await asyncio.sleep(random.uniform(*_NOON_SPACING_RANGE))


async def _noon_get(state: Dict[str, int], url: str,
                    headers: Optional[Dict[str, str]] = None):
    """Politeness-spaced, per-call-capped GET. Returns the response object or
    None on cap-exhaustion / transport failure (records a breaker failure on
    transport errors — connection-level, not HTTP-status-level)."""
    if state.get("requests", 0) >= _MAX_REQUESTS_PER_CALL:
        logger.info("[NOON] per-call request cap reached — stopping")
        return None
    if state.get("requests", 0) > 0:
        await _polite_sleep()
    state["requests"] = state.get("requests", 0) + 1
    try:
        return await asyncio.to_thread(
            lambda: _http_get(url, headers=headers, timeout=_HTTP_TIMEOUT)
        )
    except Exception as exc:  # noqa: BLE001 — a fetch error is a miss, never a crash
        logger.info("[NOON] transport error: %s", exc)
        record_failure(_NOON_PROVIDER)
        return None


# ---------------------------------------------------------------------------
# Search-hit parsing + matching
# ---------------------------------------------------------------------------

def _parse_hit_amount(hit: Dict[str, Any]) -> Optional[float]:
    """CURRENT price only — ``sale_price`` if not null else ``price`` (failure
    mode 6; live-verified: iPad-M3 rows carry sale_price=null with
    price=current). Positive only; bool guarded (bool is an int subclass)."""
    for key in ("sale_price", "price"):
        val = hit.get(key)
        if val is None or isinstance(val, bool):
            continue
        try:
            amount = float(val)
        except (TypeError, ValueError):
            continue
        if amount > 0:
            return amount
    return None


def _hit_fields(hit: Dict[str, Any]) -> Dict[str, Any]:
    """Normalized fields from one search hit. ``brand`` CAN BE NULL (the
    Switch-2 bundle live proof) → candidate_brand falls back to "". Titles are
    HTML-entity-decoded (the C2 "&amp;"→"amp" identity-token class)."""
    return {
        "title": html_unescape(str(hit.get("name") or "")).strip(),
        "brand": str(hit.get("brand") or "").strip(),
        "sku": str(hit.get("sku") or "").strip(),
        "slug": str(hit.get("url") or "").strip().strip("/"),
        "amount": _parse_hit_amount(hit),
        "is_buyable": hit.get("is_buyable"),
        "seller": str(hit.get("store_name") or "").strip(),
    }


def _gates_pass(product_name: str, surface: str, cand_brand: str,
                resolved_category: Optional[str]) -> bool:
    """The FULL shared gate chain (the occ/unbxd shape) — run at the search
    match AND re-run against the PDP's own JSON-LD name+brand:
    counterfeit → accessory-for-category (asymmetric — a query that is itself
    an accessory is not blocked by its own class) → numbers_match →
    strict-or-selection-primary (the central ``selection_primary_admits``
    wrong-brand fence) → variant_mismatch → the keystone ``_selection_match``
    (token-add rejection: the Mario-Kart-bundle / Refurbished-prefix skus)."""
    if not surface:
        return False
    if is_counterfeit_listing(surface):
        return False
    if (is_accessory_for_category(surface, resolved_category)
            and not is_accessory_for_category(product_name, resolved_category)):
        return False
    if not numbers_match(product_name, surface):
        return False
    if (not strict_title_match(product_name, surface, candidate_brand=cand_brand)
            and not selection_primary_admits(
                product_name, surface, candidate_brand=cand_brand,
                category=resolved_category)):
        return False
    if variant_mismatch(product_name, surface):
        return False
    if not _selection_match(product_name, surface, resolved_category,
                            candidate_brand=cand_brand):
        return False
    return True


def _match_noon_hits(
    hits: List[Dict[str, Any]], product_name: str,
    resolved_category: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Gate-passing hits RANKED by query-word overlap (desc). Returns the
    ranked field dicts (possibly empty) — the caller PDP-confirms the top
    match(es) in order, so a dead top PDP can fall to the runner-up without a
    new search. A non-buyable hit is skipped (never worth a PDP confirm)."""
    if not hits:
        return []
    p_words = normalize_words(product_name)
    scored: List[tuple] = []
    for idx, hit in enumerate(hits):
        if not isinstance(hit, dict):
            continue
        fields = _hit_fields(hit)
        if not fields["title"] or not fields["sku"] or not fields["slug"]:
            continue
        if fields["is_buyable"] is False:
            continue  # not sellable — a PDP confirm would be wasted
        if fields["amount"] is None:
            continue  # no positive current price on the hit
        # Match surface = brand + name (the algolia _hit_title pattern): the
        # brand disambiguates a brand-omitted name; candidate_brand strips it
        # back out of the identity sets inside the gates.
        surface = f"{fields['brand']} {fields['title']}".strip()
        if not _gates_pass(product_name, surface, fields["brand"],
                           resolved_category):
            continue
        t_words = normalize_words(surface)
        score = (len(p_words & t_words) / len(p_words)) if p_words else 0.0
        if score < 0.4:
            continue
        scored.append((-score, idx, fields))
    scored.sort(key=lambda t: (t[0], t[1]))
    return [fields for _neg, _idx, fields in scored]


# ---------------------------------------------------------------------------
# PDP JSON-LD confirm
# ---------------------------------------------------------------------------

def _extract_product_jsonld(html: str) -> Optional[Dict[str, Any]]:
    """The first @type==Product node among the PDP's ld+json blocks (~7 on a
    live noon PDP). Tolerates lists, @graph wrappers, and garbage blocks."""
    for m in _LDJSON_RE.finditer(html or ""):
        raw = (m.group(1) or "").strip()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except Exception:  # noqa: BLE001 — a garbage block is skipped, never fatal
            continue
        nodes = data if isinstance(data, list) else [data]
        for node in nodes:
            if not isinstance(node, dict):
                continue
            graph = node.get("@graph")
            inner = graph if isinstance(graph, list) else [node]
            for n in inner:
                if (isinstance(n, dict)
                        and str(n.get("@type") or "").strip().lower() == "product"):
                    return n
    return None


def _offers_list(product: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Normalize Product.offers to a list, preserving noon's OWN order (the
    authority order — offers[0] is the buy-box). AggregateOffer unwraps to its
    inner offers when present."""
    offers = product.get("offers")
    if isinstance(offers, dict):
        if (str(offers.get("@type") or "").strip().lower() == "aggregateoffer"
                and isinstance(offers.get("offers"), list)):
            return [o for o in offers["offers"] if isinstance(o, dict)]
        return [offers]
    if isinstance(offers, list):
        return [o for o in offers if isinstance(o, dict)]
    return []


def _jsonld_brand(product: Dict[str, Any]) -> str:
    brand = product.get("brand")
    if isinstance(brand, dict):
        return str(brand.get("name") or "").strip()
    if isinstance(brand, str):
        return brand.strip()
    return ""


def _select_offer(
    offers: List[Dict[str, Any]], product_name: str, pdp_title: str,
) -> Optional[Dict[str, Any]]:
    """AUTHORITY RULE — walk noon's OWN offer order (offers[0] IS the buy-box,
    live-proven == the PLP sale_price) and return the FIRST offer the
    fail-closed guards admit. NEVER ``min(offers[].price)`` (live proof:
    offers[1] 266.09 was a cheaper NON-buy-box seller under the 294.23
    buy-box). Guards per offer row:
      * a positive parseable price,
      * priceCurrency EXPLICITLY "BHD" (the silent-SAR hazard — never assumed),
      * itemCondition not refurbished/renewed/used (different sellable units),
      * availability not explicitly OOS (``is_available_state`` tri-state —
        None/unknown is kept; the display chokepoint arbitrates),
      * the implausible-low fragrance floor (a sub-floor designer offer is a
        sample/decant/wrong-SKU class — recon: AdG 22.86 / Carbon 24.12 fall
        under the 25-BHD/100ml floor while above-floor in-stock offers exist
        on the same PDPs).
    Advancing past a guard-REJECTED offer keeps authority order intact — the
    bounded relaxation is only over offers a guard proves unusable."""
    advanced_past: List[str] = []
    for idx, offer in enumerate(offers):
        raw = offer.get("price")
        try:
            amount = float(str(raw).replace(",", "").strip())
        except (TypeError, ValueError):
            continue
        if amount <= 0:
            continue
        ccy = str(offer.get("priceCurrency") or "").strip().upper()
        if ccy != "BHD":
            advanced_past.append(f"offers[{idx}]:non-BHD({ccy or '?'})")
            continue
        cond = str(offer.get("itemCondition") or "").lower()
        if any(tok in cond for tok in _REJECT_CONDITION_TOKENS):
            advanced_past.append(f"offers[{idx}]:condition")
            continue
        avail = is_available_state(offer.get("availability"))
        if avail is False:
            advanced_past.append(f"offers[{idx}]:oos")
            continue
        if is_implausible_low_fragrance_price(product_name, amount, title=pdp_title):
            advanced_past.append(f"offers[{idx}]:floor({amount})")
            continue
        seller = offer.get("seller")
        seller_name = (
            str(seller.get("name") or "").strip() if isinstance(seller, dict)
            else str(seller or "").strip()
        )
        return {
            "amount": amount,
            "in_stock": avail,  # tri-state: True / None (unknown)
            "seller": seller_name,
            "offer_index": idx,
            "advanced_past": advanced_past,
        }
    if advanced_past:
        logger.info("[NOON] no acceptable offer — guards rejected: %s",
                    "; ".join(advanced_past))
    return None


async def _confirm_pdp(
    state: Dict[str, int], fields: Dict[str, Any], product_name: str,
    resolved_category: Optional[str],
) -> Optional[Dict[str, Any]]:
    """Fetch + confirm ONE matched hit's PDP. Returns the price dict or None.
    The PDP's own JSON-LD name+brand re-runs the full gate chain (fail-closed:
    a search title that matched but a PDP that resolves to a different
    sellable unit — bundle/refurb — is rejected here too)."""
    pdp_url = _PDP_URL.format(slug=fields["slug"], sku=fields["sku"])
    resp = await _noon_get(state, pdp_url)
    if resp is None:
        return None
    status = getattr(resp, "status_code", 0)
    if status != 200:
        if status == 429 or status >= 500:
            record_failure(_NOON_PROVIDER)
        logger.info("[NOON] PDP HTTP %s for %s", status, fields["sku"])
        return None
    record_success(_NOON_PROVIDER)

    product = _extract_product_jsonld(getattr(resp, "text", "") or "")
    if product is None:
        logger.info("[NOON] PDP %s carried no Product JSON-LD", fields["sku"])
        return None

    pdp_name = html_unescape(str(product.get("name") or "")).strip()
    pdp_brand = _jsonld_brand(product)
    surface = f"{pdp_brand} {pdp_name}".strip()
    if not _gates_pass(product_name, surface, pdp_brand, resolved_category):
        logger.info("[NOON] PDP identity re-verify rejected %s (%r)",
                    fields["sku"], pdp_name)
        return None

    sel = _select_offer(_offers_list(product), product_name, pdp_name)
    if sel is None:
        return None
    if sel["offer_index"] == 0:
        logger.info("[NOON] buy-box offers[0] accepted for %s: %.3f BHD (%s)",
                    fields["sku"], sel["amount"], sel["seller"] or "?")
    else:
        logger.info(
            "[NOON] advanced to offers[%d] for %s: %.3f BHD (%s) — past %s",
            sel["offer_index"], fields["sku"], sel["amount"],
            sel["seller"] or "?", "; ".join(sel["advanced_past"]),
        )

    price: Dict[str, Any] = {
        "amount": round(float(sel["amount"]), 3),
        "currency": "BHD",  # explicit per-offer priceCurrency=="BHD" verified
        "retailer": "noon.com",
        "url": pdp_url,
        "estimated": False,
        # Reuse the JSON-LD page-scrape genuine method — already in
        # _GENUINE_BH_SOURCE_METHODS + the eval mirror (no new plumbing).
        "source_method": "page_scrape_jsonld",
        "title": pdp_name or fields["title"],
        "confidence": 0.9,
    }
    if sel["in_stock"] is not None:
        price["in_stock"] = sel["in_stock"]
    if sel["seller"]:
        # failure mode 5 — the (gray-import) marketplace seller is surfaced.
        price["seller"] = sel["seller"]
    # Wave-B identity stamp (the algolia _stamp_matched_identity precedent,
    # exact-gate-scoped): downstream select_best/should_cache_price replay
    # _selection_match with candidate_brand=price["brand"], so the PDP's own
    # brand assertion must ride the dict or the cache-write gate re-rejects
    # the brand-omitting titles the matcher here accepted.
    if pdp_brand and exact_gate_enabled():
        price["brand"] = pdp_brand
    return price


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

async def fetch_noon_price(
    domain: str, product_name: str, currency: str = "BHD",
    resolved_category: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Genuine-BHD price from noon-BH (search door + PDP JSON-LD confirm), or
    None on miss / gate-fail / cap / breaker / error. NEVER raises. NO cache
    writes here — the consume in structured_comparison_service owns caching."""
    if not ENABLE_PAGE_SCRAPE:
        return None
    norm = (domain or "").replace("www.", "").strip().lower()
    if norm != "noon.com":
        return None
    if not is_circuit_closed(_NOON_PROVIDER):
        logger.info("[NOON] circuit open — skipping")
        return None

    state: Dict[str, int] = {"requests": 0}

    hits: List[Dict[str, Any]] = []
    # R1 retrieval-term ladder: full name first; ONLY a zero-row response
    # tries the core term; rows returned — matched or not — never trigger a
    # second request; a transport/HTTP failure STOPS (F2 politeness — no
    # core-term retry against an erroring store).
    for term in build_adapter_search_terms(product_name, resolved_category):
        url = _SEARCH_URL.format(q=quote_plus(term), limit=_SEARCH_LIMIT)
        resp = await _noon_get(state, url, headers=_SEARCH_HEADERS)
        if resp is None:
            return None  # transport failure / cap — stop, never retry
        status = getattr(resp, "status_code", 0)
        if status != 200:
            if status == 429 or status >= 500:
                record_failure(_NOON_PROVIDER)
            logger.info("[NOON] search HTTP %s", status)
            return None
        record_success(_NOON_PROVIDER)
        try:
            data = resp.json()
        except Exception:  # noqa: BLE001 — non-JSON body → miss
            return None
        got = (data or {}).get("hits")
        hits = got if isinstance(got, list) else []
        if hits:
            break
    if not hits:
        return None

    matches = _match_noon_hits(hits, product_name, resolved_category)
    if not matches:
        return None

    for fields in matches[:_MAX_PDP_CONFIRMS]:
        price = await _confirm_pdp(state, fields, product_name, resolved_category)
        if price is None:
            continue
        if not is_price_showable(product_name, price):
            logger.info("[NOON] candidate not showable: %s", price.get("title"))
            continue
        try:
            from app.services.content_safety_service import get_content_safety_service
            svc = get_content_safety_service()
            surface = f"{price.get('title', '')} noon.com {product_name}"
            if svc and not svc.is_text_safe(surface):
                logger.info("[NOON] candidate dropped by content safety")
                continue
        except Exception:  # noqa: BLE001 — safety best-effort
            pass
        return price
    return None
