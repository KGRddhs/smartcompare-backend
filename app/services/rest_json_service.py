"""Custom JSON-API price adapters (R4 of the BH/GCC source build).

`fetch_rest_json_price(domain, product_name, currency)` dispatches by domain to
one of three small custom-JSON clients, each a public unauthenticated GET:

  - ourshopee (apios.ourshopee.com)  — BHD GENUINE  → source_method="rest_json_bhd"
    (catalog row DEMOTED to status="dead" 2026-07-02 — see _OURSHOPEE_SEARCH_URL)
  - panda     (api.panda.sa)          — SAR          → converted_usd
  - beautyboothqa (admin.beautybooth.qa) — QAR        → converted_usd

(noon is NOT here — it rides the existing fetch_page_price / page_scrape_jsonld.)

HARD RULES (verify-or-omit, no-fab):
  - ENABLE_PAGE_SCRAPE gate first; unknown domain → None.
  - curl_cffi impersonate="chrome", per-request timeout, run off-thread.
  - strict title-match (strict_title_match + numbers_match + variant_mismatch +
    word-overlap) before emitting any price — a wrong-brand/model hit is REJECTED.
  - is_price_showable plausibility gate + L2 content-safety surface gate.
  - GENUINE vs CONVERTED: branch on the response's ACTUAL currency. BHD (or, for
    ourshopee, BHD-by-construction via x-country=6) → the genuine method string;
    any other currency → _convert_to_bhd(...) + the literal "converted_usd" with
    original_currency set. If the rate is unknown / conversion impossible → None.
  - NEVER raises: every network/parse wrapped in try/except → None.

Prices are HUMAN numbers (NOT minor units) — parse as float, no /100 / /1000.
"""
import asyncio
import logging
import re
from typing import Any, Dict, List, Optional

from app.services.price_service import (
    normalize_candidate_brand,
    ENABLE_PAGE_SCRAPE,
    _VARIANT_QUALIFIERS,
    _convert_to_bhd,
    selection_primary_admits,
    is_price_showable,
    normalize_words,
    numbers_match,
    parse_price_string,
    strict_title_match,
    _selection_match,
    variant_mismatch,
)

logger = logging.getLogger(__name__)

# Genuine NATIVE-BHD method string (ourshopee, x-country=6). A converted GCC→BHD
# price always stamps the literal "converted_usd", never this.
_GENUINE_METHOD = "rest_json_bhd"

from app.services.adapter_timeouts import adapter_timeout
_REQUEST_TIMEOUT = adapter_timeout(12)  # per-request curl timeout (s); M13-34 clamp under wrap
_MATCH_MIN_OVERLAP = 0.4  # word-overlap floor (mirrors _match_nasser_product)

# Per-domain pinned config. host = the API host (may differ from the storefront
# domain the registry row carries). The dispatch key is the NORMALIZED apex
# (strip www., lowercase) so a registry domain like "ourshopee.com" /
# "www.panda.sa" routes correctly.
# DEAD ROUTE (probed 2026-07-02): apios has NO search-by-name route — /api/search
# and 5 plausible variants (get_search_products/getSearchProducts/search_product/
# searchProduct/getSearch) all 404 while the API family is alive
# (api/product_detail?sku= and api/getTopSelling → 200, BHD). The round-4 crack
# documented only getTopSelling/getallcategoryItems/product_detail (none
# search-by-name), and the Next.js App Router storefront fetches server-side, so
# no client chunk exposes a search path. Catalog row → status="dead"; the adapter
# stays (panda precedent) for a future re-crack via browser XHR capture. NOTE:
# verify_bh_gcc_sources.py would RE-PROMOTE this row off a storefront-200
# (api-backed rows are reachability-checked only) — do not re-promote without a
# working search route (tests/test_ourshopee_demotion.py is the tripwire).
_OURSHOPEE_SEARCH_URL = "https://apios.ourshopee.com/api/search"
_OURSHOPEE_HEADERS = {
    "x-language": "en",
    "x-country": "6",  # 6 = BHD storefront (RUNTIME-selected; not echoed)
    "Accept": "application/json",
}
_PANDA_SEARCH_URL = "https://api.panda.sa/v3/products"
_PANDA_HEADERS = {
    "X-Panda-Source": "PandaClick",
    "X-PandaClick-Agent": "4",
    "api-version": "2025-10-01",
    "X-Language": "en",
    "Accept": "application/json",
}
_BEAUTYBOOTH_SEARCH_URL = "https://admin.beautybooth.qa/api/v3/products"
_BEAUTYBOOTH_HEADERS = {"Accept": "application/json"}


def _normalize_domain(domain: str) -> str:
    d = (domain or "").strip().lower()
    if d.startswith("http://"):
        d = d[7:]
    if d.startswith("https://"):
        d = d[8:]
    d = d.split("/")[0]
    if d.startswith("www."):
        d = d[4:]
    return d


def _word_overlap(product_name: str, title: str) -> float:
    p_words = normalize_words(product_name)
    if not p_words:
        return 0.0
    t_words = normalize_words(title)
    return len(p_words & t_words) / len(p_words)


def _title_matches(product_name: str, title: str, resolved_category=None,
                   candidate_brand: str = "") -> bool:
    """Strict, no-fab match for a direct-API hit.

    candidate_brand (brand-implied match, 2026-07-07): the candidate's OWN brand
    (per-store field, derived by the caller). An own-brand store OMITS its brand
    from titles; threading candidate_brand into strict_title_match /
    selection_primary_admits / _selection_match lets a brand-omitted title of the
    query's brand pass, while a WRONG-brand hit keeps the query brand required.
    Empty (the default, e.g. the brandless ourshopee search path) → legacy
    behaviour; inert flag-OFF (byte-identical). Mirrors magento/occ.

    Uses numbers_match + strict_title_match + word-overlap (the algolia_service
    precedent for a direct-API adapter). variant_mismatch is applied ONLY when
    the QUERY carries a model-line qualifier (pro/max/plus/ultra/...) — that
    blocks a base-model query from matching a higher variant, while NOT
    false-rejecting a clean query against a long descriptive marketing title
    (e.g. "Windows 11 Pro" / "14-inch" inside an ourshopee laptop title would
    otherwise trip variant_mismatch's qualifier/size heuristics)."""
    if not title:
        return False
    if not numbers_match(product_name, title):
        return False
    # SELECTION-PRIMARY acceptance (recon_cascade R2, Wave B4): a strict FAIL
    # falls through to the conditional-variant / _selection_match / overlap
    # gates below instead of hard-rejecting (strict's RAW tokenization rejects
    # correct rows on spacing/alias variance the keystone collapses) — GATED
    # by selection_primary_admits (Wave B-FIX wrong-brand fence: rest_json
    # rows carry no brand signal, so a FASHION padding-brand query requires
    # its brand token in the title). Flag OFF (or exact gate OFF) restores
    # the exact pre-change hard gate.
    if (not strict_title_match(product_name, title, candidate_brand=candidate_brand)
            and not selection_primary_admits(
                product_name, title, candidate_brand=candidate_brand,
                category=resolved_category)):
        return False
    q_words = set(re.findall(r"[a-z]+", (product_name or "").lower()))
    if (q_words & _VARIANT_QUALIFIERS) and variant_mismatch(product_name, title):
        return False
    # Keystone variant-add guard (coverage/independent review). Flag-safe (True when off).
    if not _selection_match(product_name, title, resolved_category,
                            candidate_brand=candidate_brand):
        return False
    return _word_overlap(product_name, title) >= _MATCH_MIN_OVERLAP


def _stamp_genuine_or_converted(
    amount: float,
    response_currency: str,
    target_currency: str,
) -> Optional[Dict[str, Any]]:
    """Resolve the BHD amount + source_method/original_currency by ACTUAL
    response currency. Returns a partial price dict (amount/currency/
    source_method/[original_currency]) or None if conversion is impossible."""
    rc = (response_currency or "").upper()
    # Review gate-fix (MEDIUM, the #1 KPI-corruption trap): a genuine stamp
    # requires the RESPONSE's actual currency to be BHD — NEVER a match against the
    # caller-supplied `target_currency`. Wave-C wiring passes each Source row's real
    # currency (a panda row is currency="SAR"), so the old
    # `target_currency == rc` clause would have banked a SAR price as genuine BHD
    # (rest_json_bhd: 7d TTL, showable, counted in the genuine-share KPI). The app
    # target is always BHD, so genuine <=> the store natively returns BHD.
    if rc == "BHD":
        # Native BHD — genuine, no conversion.
        return {
            "amount": round(float(amount), 3),
            "currency": "BHD",
            "source_method": _GENUINE_METHOD,
        }
    # A non-BHD GCC price — convert and stamp the LITERAL "converted_usd".
    converted = _convert_to_bhd(float(amount), rc)
    if converted is None:
        return None
    # _convert_to_bhd returns the amount unchanged when the currency is unknown —
    # treat that as unconvertible (do NOT ship a foreign figure mislabelled BHD).
    # Membership via the shared EFFECTIVE-table gate (is_convertible — M21 W4).
    # Behaviour-neutral here: this branch only fires when _convert_to_bhd (which
    # already reads the effective table) could not convert, i.e. the code is
    # outside the effective table, hence outside the base table too — routed
    # through the shared helper so no adapter gate reads the base table.
    if rc and converted == float(amount):
        from app.services.exchange_rate_service import is_convertible
        if not is_convertible(rc):
            return None
    return {
        "amount": round(float(converted), 3),
        "currency": "BHD",
        "original_currency": rc,
        "source_method": "converted_usd",
    }


# ---------------------------------------------------------------------------
# ourshopee — BHD GENUINE
# ---------------------------------------------------------------------------

def _ourshopee_candidates(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Yield normalized {name, price, currency, stock, url, sku} from either the
    search/listing envelope (data[] flat) or the product_detail envelope
    (data.product[])."""
    out: List[Dict[str, Any]] = []
    if not isinstance(payload, dict):
        return out
    data = payload.get("data")
    items: List[Dict[str, Any]] = []
    if isinstance(data, list):
        items = [i for i in data if isinstance(i, dict)]
    elif isinstance(data, dict):
        prod = data.get("product")
        if isinstance(prod, list):
            items = [i for i in prod if isinstance(i, dict)]
    for it in items:
        name = it.get("name") or ""
        if not name:
            continue
        price_val = parse_price_string(str(it.get("display_price") or ""))
        if price_val is None or price_val <= 0:
            continue
        # Review gate-fix (LOW): ourshopee's storefront currency is RUNTIME-selected
        # by the x-country=6 header (BHD) and is BHD-by-construction; the listing's
        # `currency` field can leak a multi-country value. Pin BHD by construction
        # rather than trusting the field (else a leaked 'AED' would wrongly convert
        # a real BHD price). This is the x-country=6 guarantee, not a guess.
        currency = "BHD"
        stock_raw = str(it.get("stock") or "").lower()
        # "In stock" → True; explicit out-of-stock → False; unknown → None.
        in_stock: Optional[bool]
        if "in stock" in stock_raw or stock_raw == "instock":
            in_stock = True
        elif "out" in stock_raw:
            in_stock = False
        else:
            in_stock = None
        sku = it.get("sku") or ""
        url_part = (it.get("url") or "").strip()
        if url_part.startswith("http"):
            url = url_part
        elif url_part:
            url = f"https://ourshopee.com/bahrain/{url_part.strip('/')}/"
        elif sku:
            url = f"https://ourshopee.com/bahrain/{sku}/"
        else:
            url = "https://ourshopee.com/bahrain/"
        out.append({
            "name": name,
            "price": price_val,
            "currency": str(currency).upper(),
            "in_stock": in_stock,
            "url": url,
            "sku": sku,
        })
    return out


async def _fetch_ourshopee(product_name: str, currency: str, resolved_category: Optional[str] = None) -> Optional[Dict[str, Any]]:
    try:
        from curl_cffi import requests as curl_requests
        resp = await asyncio.to_thread(
            lambda: curl_requests.get(
                _OURSHOPEE_SEARCH_URL,
                params={"q": product_name, "search": product_name},
                headers=_OURSHOPEE_HEADERS,
                impersonate="chrome",
                timeout=_REQUEST_TIMEOUT,
                allow_redirects=True,
            )
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("[PRICE] ourshopee fetch failed for %s: %s", product_name, exc)
        return None
    if getattr(resp, "status_code", 0) != 200:
        logger.info("[PRICE] ourshopee HTTP %s for '%s'", getattr(resp, "status_code", "?"), product_name)
        return None
    try:
        payload = resp.json()
    except Exception:  # noqa: BLE001
        return None

    best: Optional[Dict[str, Any]] = None
    best_score = -1.0
    for cand in _ourshopee_candidates(payload):
        if not _title_matches(product_name, cand["name"], resolved_category):
            continue
        score = _word_overlap(product_name, cand["name"])
        if score > best_score:
            best_score = score
            best = cand
    if not best:
        return None

    # ourshopee x-country=6 is BHD by construction — the listing currency
    # confirms it when present.
    partial = _stamp_genuine_or_converted(best["price"], best.get("currency") or "BHD", currency)
    if not partial:
        return None
    price = {
        **partial,
        "retailer": "ourshopee.com",
        "url": best["url"],
        "estimated": False,
        "title": best["name"],
        "confidence": 0.85,
    }
    if best.get("in_stock") is not None:
        price["in_stock"] = best["in_stock"]
    return price


# ---------------------------------------------------------------------------
# panda — SAR → converted
# ---------------------------------------------------------------------------

async def _fetch_panda(product_name: str, currency: str, resolved_category: Optional[str] = None) -> Optional[Dict[str, Any]]:
    try:
        from curl_cffi import requests as curl_requests
        resp = await asyncio.to_thread(
            lambda: curl_requests.get(
                _PANDA_SEARCH_URL,
                params={"q": product_name},
                headers=_PANDA_HEADERS,
                impersonate="chrome",
                timeout=_REQUEST_TIMEOUT,
                allow_redirects=True,
            )
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("[PRICE] panda fetch failed for %s: %s", product_name, exc)
        return None
    if getattr(resp, "status_code", 0) != 200:
        logger.info("[PRICE] panda HTTP %s for '%s'", getattr(resp, "status_code", "?"), product_name)
        return None
    try:
        payload = resp.json()
    except Exception:  # noqa: BLE001
        return None
    if not isinstance(payload, dict):
        return None
    products = (payload.get("data") or {}).get("products") if isinstance(payload.get("data"), dict) else None
    if not isinstance(products, list) or not products:
        return None

    best: Optional[Dict[str, Any]] = None
    best_score = -1.0
    for prod in products:
        if not isinstance(prod, dict):
            continue
        name = prod.get("name") or ""
        # Brand-implied match (2026-07-07) — panda carries brand as a NESTED
        # object prod["brand"]["name"]; normalize_candidate_brand handles the
        # dict / null / string shapes safely.
        _cand_brand = normalize_candidate_brand(prod.get("brand"))
        if not _title_matches(product_name, name, resolved_category, candidate_brand=_cand_brand):
            continue
        varieties = prod.get("varieties")
        if not isinstance(varieties, list) or not varieties:
            continue
        var = varieties[0]
        if not isinstance(var, dict):
            continue
        price_val = parse_price_string(str(var.get("price") or ""))
        if price_val is None or price_val <= 0:
            continue
        avail = var.get("availability")
        in_stock = bool(avail == 1) if avail is not None else None
        score = _word_overlap(product_name, name)
        if score > best_score:
            best_score = score
            best = {
                "name": name,
                "price": price_val,
                "in_stock": in_stock,
                "sku": var.get("sku") or prod.get("id") or "",
            }
    if not best:
        return None

    partial = _stamp_genuine_or_converted(best["price"], "SAR", currency)
    if not partial:
        return None
    sku = best.get("sku") or ""
    price = {
        **partial,
        "retailer": "panda.sa",
        "url": f"https://www.panda.sa/product/{sku}" if sku else "https://www.panda.sa/",
        "estimated": False,
        "title": best["name"],
        "confidence": 0.8,
    }
    if best.get("in_stock") is not None:
        price["in_stock"] = best["in_stock"]
    return price


# ---------------------------------------------------------------------------
# beautyboothqa — QAR → converted
# ---------------------------------------------------------------------------

async def _fetch_beautybooth(product_name: str, currency: str, resolved_category: Optional[str] = None) -> Optional[Dict[str, Any]]:
    try:
        from curl_cffi import requests as curl_requests
        resp = await asyncio.to_thread(
            lambda: curl_requests.get(
                _BEAUTYBOOTH_SEARCH_URL,
                params={"q": product_name, "search": product_name},
                headers=_BEAUTYBOOTH_HEADERS,
                impersonate="chrome",
                timeout=_REQUEST_TIMEOUT,
                allow_redirects=True,
            )
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("[PRICE] beautybooth fetch failed for %s: %s", product_name, exc)
        return None
    if getattr(resp, "status_code", 0) != 200:
        logger.info("[PRICE] beautybooth HTTP %s for '%s'", getattr(resp, "status_code", "?"), product_name)
        return None
    try:
        payload = resp.json()
    except Exception:  # noqa: BLE001
        return None
    if not isinstance(payload, dict):
        return None

    # Items live under data[] (a real product search) OR best_sell.data[] (the
    # endpoint also returns a best-seller list). Scan whichever is present.
    items: List[Dict[str, Any]] = []
    data = payload.get("data")
    if isinstance(data, list) and data:
        items.extend(i for i in data if isinstance(i, dict))
    best_sell = payload.get("best_sell")
    if isinstance(best_sell, dict):
        bs_data = best_sell.get("data")
        if isinstance(bs_data, list):
            items.extend(i for i in bs_data if isinstance(i, dict))
    if not items:
        return None

    best: Optional[Dict[str, Any]] = None
    best_score = -1.0
    for it in items:
        name = it.get("name") or ""
        # Brand-implied match (2026-07-07) — beautybooth carries brand as a FLAT
        # top-level string it["brand"] ("The Ordinary").
        _cand_brand = normalize_candidate_brand(it.get("brand"))
        if not _title_matches(product_name, name, resolved_category, candidate_brand=_cand_brand):
            continue
        price_val = parse_price_string(str(it.get("net_price") or it.get("main_price") or ""))
        if price_val is None or price_val <= 0:
            continue
        in_stock_raw = it.get("in_stock")
        in_stock = bool(in_stock_raw) if in_stock_raw is not None else None
        slug = it.get("slug") or ""
        score = _word_overlap(product_name, name)
        if score > best_score:
            best_score = score
            best = {"name": name, "price": price_val, "in_stock": in_stock, "slug": slug}
    if not best:
        return None

    partial = _stamp_genuine_or_converted(best["price"], "QAR", currency)
    if not partial:
        return None
    slug = best.get("slug") or ""
    price = {
        **partial,
        "retailer": "beautybooth.qa",
        "url": f"https://beautybooth.qa/product/{slug}" if slug else "https://beautybooth.qa/",
        "estimated": False,
        "title": best["name"],
        "confidence": 0.8,
    }
    if best.get("in_stock") is not None:
        price["in_stock"] = best["in_stock"]
    return price


# ---------------------------------------------------------------------------
# dispatch
# ---------------------------------------------------------------------------

# Normalized-apex → per-domain fetcher.
_DISPATCH = {
    "ourshopee.com": _fetch_ourshopee,
    "apios.ourshopee.com": _fetch_ourshopee,
    "panda.sa": _fetch_panda,
    "api.panda.sa": _fetch_panda,
    "beautybooth.qa": _fetch_beautybooth,
    "admin.beautybooth.qa": _fetch_beautybooth,
}


async def fetch_rest_json_price(
    domain: str, product_name: str, currency: str = "BHD",
    resolved_category: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Genuine/converted BH/GCC price from a custom-JSON storefront API.

    Dispatches by `domain` (ourshopee/panda/beautybooth). Returns a price dict
    (genuine `rest_json_bhd` for native BHD, `converted_usd` for a converted GCC
    price) or None on any gate/miss/error. NEVER raises."""
    if not ENABLE_PAGE_SCRAPE:
        return None
    fetcher = _DISPATCH.get(_normalize_domain(domain))
    if fetcher is None:
        return None

    try:
        price = await fetcher(product_name, currency, resolved_category)
    except Exception as exc:  # noqa: BLE001 — defense in depth; a fetcher bug is a miss
        logger.warning("[PRICE] rest_json fetch crashed for %s/%s: %s", domain, product_name, exc)
        return None
    if not price:
        return None

    # Plausibility gate (accuracy guards) then L2 content-safety surface gate.
    if not is_price_showable(product_name, price):
        return None
    try:
        from app.services.content_safety_service import get_content_safety_service
        surface = f"{price.get('title', '')} {_normalize_domain(domain)} {product_name}"
        if not get_content_safety_service().is_text_safe(surface):
            logger.info("[content_safety] L2 dropped rest_json candidate for %s", product_name)
            return None
    except Exception:  # noqa: BLE001 — safety service failure must not crash the adapter
        pass

    logger.info(
        "[PRICE] rest_json %s: %s %s for '%s'",
        price.get("source_method"), price.get("currency"), price.get("amount"), product_name,
    )
    return price
