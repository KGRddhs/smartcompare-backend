"""SAP-Hybris OCC v2 REST price adapter (BH/GCC source-build R3a, 2026-06-25).

A single $0 GET to a SAP-Commerce (Hybris) Occ v2 storefront API resolves a
product name → its genuine native price (no Serper, no render). Covers
virginmegastore.bh (GENUINE BHD), its QAR/OMR siblings, and al-dawaa.com (SAR),
all on the same OCC shape.

Flow:
  1. Look up the per-store config (occ_host, baseSite, storefront_origin) for the
     requested domain. Unknown domain → None.
  2. GET ``{occ_host}/occ/v2/{baseSite}/products/search?query={q}&fields=FULL&
     pageSize={n}`` with the MANDATORY ``Accept: application/json`` header (omit →
     the server returns ``application/xml`` with identical data → breaks json).
     Search hits carry the SAME ``price``/``stock``/``url`` shape as a product
     detail, so one call resolves the name AND the price.
  3. STRICT title-match (price_service.strict_title_match / numbers_match /
     variant_mismatch) so a fuzzy hit (AirPods → a wrong brand) is REJECTED — no
     wrong-brand price ever ships.
  4. Filter ``stock.stockLevelStatus == "outOfStock"`` (never sell an OOS price).
     Search hits may OMIT ``stock`` → treat absent as available.
  5. GENUINE vs CONVERTED by the response's ACTUAL ``price.currencyIso``:
     ``"BHD"`` → genuine ``source_method="occ_rest_bhd"``; any other GCC currency
     → ``_convert_to_bhd`` → the LITERAL ``"converted_usd"`` + ``original_currency``.

Returns a price dict or ``None`` on miss / non-200 / garbage / OOS / no-match.
NEVER raises — best-effort, never critical-path. Gated by ENABLE_PAGE_SCRAPE +
``is_price_showable`` + L2 content-safety.
"""
import asyncio
import logging
from typing import Any, Dict, Optional, Tuple

from curl_cffi import requests as _curl

from app.services.price_service import (
    ENABLE_PAGE_SCRAPE,
    _convert_to_bhd,
    selection_primary_admits,
    is_accessory_for_category,
    is_counterfeit_listing,
    is_price_showable,
    normalize_words,
    numbers_match,
    strict_title_match,
    _selection_match,
    variant_mismatch,
)
from app.services.exchange_rate_service import FALLBACK_RATES

logger = logging.getLogger(__name__)

# Per-store OCC config: domain → (occ_host, baseSite, storefront_origin).
# The occ_host serves the API; the storefront_origin is what RELATIVE product
# urls must be prepended with (NEVER the occ_host). al-dawaa MUST use the stg
# host — www.al-dawaa.com/occ/... returns the SPA HTML shell.
# OMIT virginAe / virginSa / virginKw (HTTP 400 — not exposed).
_OCC_STORES: Dict[str, Tuple[str, str, str]] = {
    "virginmegastore.bh": (
        "https://occ.virginmegastore.com", "virginBh",
        "https://www.virginmegastore.bh",
    ),
    "virginmegastore.qa": (
        "https://occ.virginmegastore.com", "virginQa",
        "https://virginmegastore.qa",
    ),
    "virginmegastore.om": (
        "https://occ.virginmegastore.com", "virginOm",
        "https://virginmegastore.om",
    ),
    "al-dawaa.com": (
        "https://stgprevapi.al-dawaa.com", "aldawaa",
        "https://www.al-dawaa.com",
    ),
}

_TIMEOUT = 12
_PAGE_SIZE = 5
# MANDATORY — omit Accept and the OCC server returns XML, breaking json.loads.
_HEADERS = {
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
}


def _normalize_domain(domain: str) -> str:
    d = (domain or "").strip().lower()
    if d.startswith("http://"):
        d = d[len("http://"):]
    elif d.startswith("https://"):
        d = d[len("https://"):]
    d = d.split("/", 1)[0]
    if d.startswith("www."):
        d = d[len("www."):]
    return d


def _stock_ok(prod: Dict[str, Any]) -> Optional[bool]:
    """Return False when the OCC stock signal is outOfStock, True when inStock,
    None when no stock node (search hits often omit it) — caller treats None as
    available (do NOT drop a hit that simply lacks the field)."""
    stock = prod.get("stock")
    if not isinstance(stock, dict):
        return None
    status = str(stock.get("stockLevelStatus") or "").strip().lower()
    if not status:
        return None
    if status == "outofstock":
        return False
    if status == "instock":
        return True
    return None


def _select_product(
    payload: Dict[str, Any], product_name: str, resolved_category: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Best query-matching in-stock product node, or None. PURE."""
    products = payload.get("products")
    if not isinstance(products, list) or not products:
        return None

    p_words = normalize_words(product_name)
    best: Optional[Dict[str, Any]] = None
    best_score = -1.0
    for prod in products:
        if not isinstance(prod, dict):
            continue
        name = prod.get("name") or ""
        if not name:
            continue
        # KEYSTONE candidate_brand (fix-ladder #1/2) — SAP-Commerce OCC search under
        # fields=FULL exposes a top-level `manufacturer` string. Thread it into BOTH
        # gates so a genuine BH retailer PDP that lists a device by its MODEL LINE
        # ("iPad Air M2 128GB", no "Apple") is not rejected on the missing brand word,
        # while a WRONG-brand candidate keeps the query brand required (candidate_brand
        # only drops the candidate's OWN brand tokens, and _selection_match runs
        # alongside to vet the full SKU). Missing manufacturer → "" → legacy behaviour.
        _cand_brand = str(prod.get("manufacturer") or "").strip()
        # Review gate-fix (MEDIUM, NO-FAB): drop counterfeit + (asymmetric)
        # accessory hits so a same-brand same-model ACCESSORY (case/band/strap)
        # never ships as the product's price for a non-high-value category (the
        # is_price_showable ceiling only catches phone/laptop/console leaks).
        if is_counterfeit_listing(name):
            continue
        # Category-scoped (BF4, sweep OR-7): occ's BH stores are pharmacies —
        # the bare 'skin' accessory keyword false-positives on genuine
        # "...For Normal To Oily Skin" titles; the scoped wrapper exempts it
        # for pharmacy-class resolved categories only (any other accessory
        # keyword still flags; electronics keeps the full broad filter).
        if (is_accessory_for_category(name, resolved_category)
                and not is_accessory_for_category(product_name, resolved_category)):
            continue
        if not numbers_match(product_name, name):
            continue
        # SELECTION-PRIMARY acceptance (recon_cascade R2, Wave B4): a strict
        # FAIL no longer hard-rejects — a brand-omitting OCC node under a
        # spelled `manufacturer` fails strict on the raw brand-alias/spacing
        # tokens ("YSL" query vs released "Yves Saint Laurent", "90ml" vs
        # "90 ml") while _selection_match(candidate_brand=) below vets the
        # full SKU via the alias-folding identity sets. The variant /
        # selection / stock / word-overlap gates still run — the fallthrough
        # GATED by selection_primary_admits (Wave B-FIX wrong-brand fence: a
        # node whose manufacturer contradicts a padding-brand query
        # hard-rejects). Flag OFF (or exact gate OFF) restores the exact
        # pre-change hard gate.
        if (not strict_title_match(product_name, name, candidate_brand=_cand_brand)
                and not selection_primary_admits(
                    product_name, name, candidate_brand=_cand_brand,
                    category=resolved_category)):
            continue
        if variant_mismatch(product_name, name):
            continue
        # Keystone variant-add guard (coverage/independent review) — category-aware
        # superset/axes beyond variant_mismatch's pro/max set. Flag-safe (True when off).
        if not _selection_match(product_name, name, resolved_category,
                                candidate_brand=_cand_brand):
            continue
        price = prod.get("price")
        if not isinstance(price, dict):
            continue
        value = price.get("value")
        if not isinstance(value, (int, float)) or value <= 0:
            continue
        # Drop an explicitly out-of-stock hit (None = unknown → keep).
        if _stock_ok(prod) is False:
            continue
        t_words = normalize_words(name)
        score = len(p_words & t_words) / len(p_words) if p_words else 0.0
        if score < 0.4:
            continue
        if score > best_score:
            best_score = score
            best = prod
    return best


def _build_price(
    prod: Dict[str, Any], domain: str, storefront_origin: str, product_name: str
) -> Optional[Dict[str, Any]]:
    """Build the contract price dict from a matched OCC product node, branching
    genuine (BHD) vs converted (other GCC currency). PURE."""
    price = prod.get("price") or {}
    raw_amount = price.get("value")
    if not isinstance(raw_amount, (int, float)) or raw_amount <= 0:
        return None
    src_ccy = str(price.get("currencyIso") or "").upper()
    if not src_ccy:
        return None

    name = prod.get("name") or ""
    rel_url = str(prod.get("url") or "")
    url = ""
    if rel_url:
        if rel_url.startswith("http://") or rel_url.startswith("https://"):
            url = rel_url
        else:
            url = storefront_origin.rstrip("/") + "/" + rel_url.lstrip("/")

    score_words = normalize_words(product_name)
    t_words = normalize_words(name)
    score = len(score_words & t_words) / len(score_words) if score_words else 0.0
    confidence = round(min(0.7 + score * 0.25, 0.95), 2)

    in_stock = _stock_ok(prod)

    out: Dict[str, Any] = {
        "currency": "BHD",
        "retailer": domain,
        "url": url,
        "estimated": False,
        "title": name,
        "confidence": confidence,
    }
    if in_stock is not None:
        out["in_stock"] = in_stock

    if src_ccy == "BHD":
        out["amount"] = round(float(raw_amount), 3)
        out["source_method"] = "occ_rest_bhd"
    else:
        # Converted GCC price. Refuse to mis-stamp an unconvertible currency as a
        # genuine BHD number — only convert known FX rates.
        if src_ccy not in FALLBACK_RATES:
            return None
        bhd = _convert_to_bhd(float(raw_amount), src_ccy)
        if bhd is None or bhd <= 0:
            return None
        out["amount"] = round(float(bhd), 3)
        out["original_currency"] = src_ccy
        out["source_method"] = "converted_usd"
    return out


async def fetch_occ_rest_price(
    domain: str, product_name: str, currency: str = "BHD",
    resolved_category: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Genuine/converted price for a SAP-Hybris OCC v2 storefront, or None.

    ``domain`` keys ``_OCC_STORES`` (virginmegastore.bh/.qa/.om, al-dawaa.com).
    One ``/products/search`` GET resolves the name AND the price. Native BHD →
    ``occ_rest_bhd`` (genuine); any other GCC currency → ``converted_usd``.
    Verify-or-omit: token-less / non-200 / garbage / no-match / OOS → None. NEVER
    raises. Gated by ENABLE_PAGE_SCRAPE + is_price_showable + L2 content-safety.
    """
    if not ENABLE_PAGE_SCRAPE:
        return None

    norm = _normalize_domain(domain)
    cfg = _OCC_STORES.get(norm)
    if cfg is None:
        return None
    occ_host, base_site, storefront_origin = cfg

    search_url = f"{occ_host}/occ/v2/{base_site}/products/search"
    params = {
        "query": product_name,
        "fields": "FULL",
        "pageSize": _PAGE_SIZE,
    }
    try:
        resp = await asyncio.to_thread(
            lambda: _curl.get(
                search_url,
                params=params,
                headers=_HEADERS,
                impersonate="chrome",
                timeout=_TIMEOUT,
                allow_redirects=True,
            )
        )
    except Exception as exc:  # noqa: BLE001 — a fetch error is a miss, never a crash
        logger.warning("[PRICE] occ fetch failed for %s @ %s: %s", product_name, norm, exc)
        return None

    if getattr(resp, "status_code", None) != 200:
        logger.info("[PRICE] occ HTTP %s for '%s' @ %s",
                    getattr(resp, "status_code", "?"), product_name, norm)
        return None

    try:
        payload = resp.json()
    except Exception:  # noqa: BLE001 — non-JSON body (XML / garbage) → miss
        return None
    if not isinstance(payload, dict):
        return None

    prod = _select_product(payload, product_name, resolved_category=resolved_category)
    if prod is None:
        return None

    price = _build_price(prod, norm, storefront_origin, product_name)
    if price is None:
        return None
    if not is_price_showable(product_name, price):
        return None

    try:
        from app.services.content_safety_service import get_content_safety_service
        _surface = f"{price.get('title', '')} {norm} {product_name}"
        if not get_content_safety_service().is_text_safe(_surface):
            logger.info("[content_safety] L2 dropped occ candidate for %s", product_name)
            return None
    except Exception:  # noqa: BLE001 — safety service hiccup → fail-open is acceptable here
        pass

    logger.info(
        "[PRICE] occ %s: %s %s for '%s' @ %s",
        price["source_method"], price["currency"], price["amount"],
        product_name, norm,
    )
    return price
