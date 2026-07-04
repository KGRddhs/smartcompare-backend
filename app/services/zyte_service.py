"""Zyte render-tier adapter — genuine BHD prices from Akamai-walled luxury sites.

The luxury Western fragrance/beauty gap (Tom Ford, Dior, YSL …) lives on sites
like sephora.me /bh-en that are Akamai-walled — `curl_cffi` and even a plain
datacenter render get a 403. Zyte API's AI extraction with `geolocation: "BH"`
cracks the wall (residential, Bahrain-geo) and returns a STRUCTURED BHD price.
Feasibility-proven 2026-06-26 (Tom Ford Oud Wood EDP 77.000 BHD via sephora.me).

⚠️ OFF-CLOCK ONLY. A Zyte browser render is SLOW (browserHtml >90s; product
extraction tens of seconds) — far past the 15s live price clock. So this adapter
is GATED by ENABLE_ZYTE_RENDER (fail-CLOSED, default OFF) and is invoked ONLY by
the off-clock seed/warmer (scripts/seed_zyte_luxury.py), never on the request
path. The live cascade serves the genuine BHD price the seed wrote to the cache.

Genuine method ``zyte_render_bhd``. FRAGRANCE/BEAUTY-scoped (the fils-fix assumes
a plausible price < 1000 BHD). Strict-match no-fab via a HARD product-identity
gate (sephora doesn't stock every brand — a "Creed Aventus" search returns makeup,
and a flanker like "Black Opium Over Red" or a near-name like "Ombre Nomade" must
be rejected, not shipped as a wrong price). NOT yet metered in api_budget_service;
instead a terminal billing 4xx (401/402/403) trips a per-run kill-switch so a
suspended/over-limit account is not hammered for the rest of a seed run. NEVER
raises.
"""
from __future__ import annotations

import asyncio
import base64
import logging
import os
import re
import unicodedata
import urllib.parse
from typing import Any, Dict, List, Optional

import httpx

from app.services.price_service import (
    numbers_match,
    variant_mismatch,
    is_counterfeit_listing,
    is_accessory,
    is_price_showable,
    is_available_state,
    normalize_words,
    extract_concentration,
    extract_size_ml_any,
    _CONCENTRATION_PATTERNS,
)

logger = logging.getLogger(__name__)

ZYTE_API_URL = "https://api.zyte.com/v1/extract"
_TIMEOUT = float(os.getenv("ZYTE_TIMEOUT", "100"))
_GENUINE_METHOD = "zyte_render_bhd"

# Concentration-word tokens — excluded from the "extra tokens" penalty so a plain
# "Oud Wood - Eau de Parfum" is NOT scored worse than "Oud Wood Parfum" just for
# carrying the (expected) concentration words. Mirrors extract_concentration's
# vocabulary.
_CONCENTRATION_TOKENS = frozenset({
    "eau", "de", "parfum", "toilette", "cologne", "edp", "edt", "edc",
    "extrait", "intense", "fraiche", "perfume",
})

# Default concentration preference when the QUERY does not state one. EDP and EDT
# are CO-FLAGSHIP (both the everyday wearable a brand+name query means) — the pricier
# niche Parfum/Extrait rank well below. This fixes "Tom Ford Oud Wood" mis-matching
# the Parfum (158) over the EDP (77). EDP and EDT TIE on purpose: between them the
# canonical bottle is brand-specific (Sauvage/Black Opium are EDP-iconic; Acqua di
# Gio/CK One are EDT-iconic), so the tie is broken by sephora's own relevance
# ranking (metadata.probability) rather than a wrong fixed EDP>EDT bias. Higher =
# preferred.
_CONCENTRATION_PREFERENCE = {
    "EDP": 0.30,
    "EDT": 0.30,
    "EDC": 0.20,
    "Eau Fraiche": 0.18,
    "Parfum": 0.10,
    "Parfum Intense": 0.10,
    "Extrait": 0.05,
}

# Non-bottle FORM phrases. sephora's productList for a fragrance search also
# surfaces gift sets, body sprays/mists, deodorants, candles, etc. — a DIFFERENT
# product form whose price must not be attributed to the fragrance bottle (e.g.
# "Oud Wood - All Over Body Spray" 41 BHD, "Oud Wood Eau de Parfum Set" 119 BHD).
# Rejected unless the QUERY itself asks for that form. "spray" alone is NOT here
# (a normal EDP bottle is titled "Eau de Parfum Spray").
_NON_BOTTLE_PHRASES = (
    "body spray", "body mist", "hair mist", "body lotion", "body cream",
    "body oil", "shower gel", "deodorant", "gift set", "discovery set",
    "travel set", "candle", "refill", "miniature", "rollerball",
    "roll-on", "roll on",
)


def _is_wrong_form(query_lc: str, title_lc: str, q_words: set, t_words: set) -> bool:
    """True iff the candidate title is a NON-BOTTLE product form the query did
    not ask for (gift set / body spray / deodorant / candle …)."""
    for phrase in _NON_BOTTLE_PHRASES:
        if phrase in title_lc and phrase not in query_lc:
            return True
    # A trailing/standalone "Set" token = a gift/bundle SKU (e.g. "… Parfum Set").
    if "set" in t_words and "set" not in q_words:
        return True
    return False


# --- product-identity gate + account kill-switch (no-fab hardening 2026-06-26) ---
# A terminal billing 4xx (401/402/403) sets this so the rest of a seed RUN stops
# issuing paid Zyte renders against a suspended / over-limit account (fragile-trial
# protection — the prior account was suspended at its spending limit). Per-process.
_ACCOUNT_DEAD = False


def reset_account_state() -> None:
    """Test/seed hook — clear the per-run account-dead kill-switch."""
    global _ACCOUNT_DEAD
    _ACCOUNT_DEAD = False


# Size tokens ("100ml", "3.4 oz") are NOT product identity — stripped before the
# identity comparison (size fairness is handled downstream).
_SIZE_TOKEN_RE = re.compile(r"\b\d+(?:\.\d+)?\s*(?:ml|fl\s*oz|oz)\b", re.I)

# Form/packaging words that are NOT product identity. The form GATE rejects the
# real non-bottle forms first; these are defense-in-depth so a stray suffix (a lone
# "Spray" on a normal EDP bottle) doesn't break identity equality.
_FORM_TOKENS = frozenset({
    "set", "spray", "mist", "deodorant", "candle", "refill", "miniature",
    "lotion", "cream", "gel", "oil", "balm", "shower", "body", "hair", "travel",
})


def _fold(s: str) -> str:
    """Lowercase + strip diacritics so an accented sephora title matches a
    plain-ASCII query and vice versa: "Acqua di Giò" → "acqua di gio", "Lancôme" →
    "lancome", "Hermès" → "hermes". Without this the identity gate falsely PENDS a
    genuine listing whose only difference is an accent (live-observed: sephora's
    "Acqua di Giò Eau de Toilette" rejected for query "Acqua di Gio")."""
    return "".join(
        c for c in unicodedata.normalize("NFKD", (s or "").lower())
        if not unicodedata.combining(c)
    )


def _brand_token_set(brand: str) -> set:
    """The brand's identity tokens, ALIAS-EXPANDED via the shared
    price_service._BRAND_ALIAS_GROUPS (same intersect-trigger the keystone matcher
    uses), so "YSL" and "Yves Saint Laurent" subtract the same token family from
    both sides — a query built with the abbreviation still matches a title carrying
    the spelled-out house (and vice versa)."""
    toks = normalize_words(_fold(brand))
    if not toks:
        return toks
    try:
        from app.services.price_service import _BRAND_ALIAS_GROUPS
        for _group in _BRAND_ALIAS_GROUPS:
            if toks & _group:
                toks = toks | set(_group)
    except Exception:  # noqa: BLE001 — alias fold is best-effort; literal tokens still apply
        pass
    return toks


def _identity_tokens(text: str, brand: str = "") -> set:
    """PRODUCT-IDENTITY tokens of `text`: its words (DIACRITIC-FOLDED) minus the
    brand, the concentration PHRASE (so "eau de parfum"/"parfum intense" go but a
    standalone product word like the "intense" in "Dior Homme Intense" STAYS), size
    tokens, form words, and sub-3-char noise. Two listings are the SAME product iff
    their identity sets are EQUAL — the no-fab gate that rejects a flanker ("Black
    Opium Over Red" -> {black,opium,over,red}), a near-name ("Ombre Nomade" vs
    "Ombre Leather"), and a base shipped for a flanker query ("Dior Homme" {homme}
    vs "Dior Homme Intense" {homme,intense}). Phrase-based concentration stripping
    (the price_service patterns) keeps "intense" as identity unless it is the
    "parfum intense" concentration."""
    if not text:
        return set()
    stripped = _fold(text)
    for pat, _label in _CONCENTRATION_PATTERNS:
        stripped = pat.sub(" ", stripped)
    stripped = _SIZE_TOKEN_RE.sub(" ", stripped)
    words = normalize_words(stripped)
    brand_words = _brand_token_set(brand)
    return {w for w in (words - brand_words - _FORM_TOKENS) if len(w) > 2}


def _name_is_brand_string(name: str, brand: str) -> bool:
    """True iff a productList tile NAME is just the BRAND string (the recon
    'YVES SAINT LAURENT' wobble: sephora sometimes returns the brand as the tile
    name). Alias-aware (a tile named the spelled-out house matches an abbreviated
    `brand` param). A name carrying ANY non-brand product word is NOT a brand
    string — the fallback below never fires for a real title."""
    if not name or not brand:
        return False
    n_toks = normalize_words(_fold(name))
    if not n_toks:
        return False
    return n_toks <= _brand_token_set(brand)


def _slug_text(url: str) -> str:
    """The product IDENTITY text carried by a PDP URL slug — the LONGEST
    hyphenated path segment, hyphens→spaces ("/bh-en/p/black-opium-eau-de-parfum/
    P1920022" → "black opium eau de parfum"). Empty when the URL has no hyphenated
    segment. Used ONLY as the brand-as-name wobble fallback token source — the
    identity EQUALITY gate is unchanged (a flanker slug still mismatches)."""
    if not url:
        return ""
    try:
        path = urllib.parse.urlsplit(url).path
    except Exception:  # noqa: BLE001 — a garbage URL is just "no slug"
        return ""
    segs = [s for s in path.split("/") if "-" in s]
    if not segs:
        return ""
    return max(segs, key=len).replace("-", " ").strip()


def _concentration_bonus(q_conc: Optional[str], t_conc: Optional[str]) -> float:
    """Scoring bonus for a candidate's concentration.

    - Query states a concentration → the matching candidate gets the bonus, an
      unstated-title candidate gets 0 (kept on benefit-of-doubt, ranked below an
      exact match); a mismatched explicit concentration is rejected upstream.
    - Query unspecified → prefer the flagship wearable concentration (EDP > EDT …)
      so a brand+name query lands on the EDP, not the pricier Parfum/Extrait."""
    if q_conc:
        return 0.30 if t_conc == q_conc else 0.0
    return _CONCENTRATION_PREFERENCE.get(t_conc or "", 0.0)

# Per-store config: apex domain -> {search URL template, currency}. The search
# productList extraction returns matching PDPs + prices in one Zyte call.
ZYTE_STORES: Dict[str, Dict[str, str]] = {
    "sephora.me": {
        "search": "https://www.sephora.me/bh-en/search?q={q}",
        "currency": "BHD",
    },
}


def _enabled() -> bool:
    """Fail-CLOSED gate. Zyte is a PAID, SLOW render — it fires ONLY when the
    off-clock seed explicitly enables it. The live web service leaves this OFF, so
    a Zyte render can never land on the 15s request path."""
    return os.getenv("ENABLE_ZYTE_RENDER", "").strip().lower() in ("true", "1", "yes", "on")


def _auth_header() -> Optional[str]:
    key = os.getenv("ZYTE_API_KEY")
    if not key:
        return None
    return "Basic " + base64.b64encode(f"{key}:".encode()).decode()


def normalize_bhd_amount(raw: Any) -> Optional[float]:
    """The fils-fix. Zyte parses BHD's 3-decimal format INCONSISTENTLY — the same
    "77.000 BHD" comes back as "77000.0" (decimal stripped → fils) or, sometimes,
    "11.0" (kept). For the FRAGRANCE/BEAUTY scope (genuine prices well under 1000
    BHD) a value >= 1000 is therefore the fils form → divide by 1000. A value < 1000
    is already the major unit. Returns None for non-positive/garbage. (NOT safe for
    electronics, where a genuine >1000 BHD price exists — this adapter is
    fragrance/beauty-scoped.)"""
    try:
        amt = float(raw)
    except (TypeError, ValueError):
        return None
    if amt <= 0:
        return None
    if amt >= 1000:
        amt = amt / 1000.0
    return round(amt, 3)


async def _zyte_extract(url: str, body: Dict[str, Any]) -> Optional[dict]:
    """ONE Zyte API extraction with geolocation=BH, with bounded retry on TRANSIENT
    failures (transport error / HTTP 429 / 5xx). A 4xx (auth/billing/not-found) is
    TERMINAL — never retried (a suspended account or bad key would just burn the
    retry budget). Returns the parsed JSON or None. Never raises.

    Retry knobs (env, read fresh): ZYTE_RETRIES (total attempts, default 2),
    ZYTE_RETRY_BACKOFF (seconds between attempts, default 2.0; 0 in tests)."""
    auth = _auth_header()
    if not auth:
        return None
    attempts = max(1, int(os.getenv("ZYTE_RETRIES", "2")))
    backoff = float(os.getenv("ZYTE_RETRY_BACKOFF", "2.0"))
    for attempt in range(1, attempts + 1):
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.post(
                    ZYTE_API_URL,
                    headers={"Authorization": auth},
                    json={"url": url, "geolocation": "BH", **body},
                )
        except Exception as exc:  # noqa: BLE001 — a fetch error is a miss, never a crash
            logger.warning("[ZYTE] transport error for %s (attempt %d/%d): %s",
                           url, attempt, attempts, exc)
            if attempt < attempts and backoff > 0:
                await asyncio.sleep(backoff)
            continue
        if resp.status_code == 200:
            try:
                return resp.json()
            except Exception:  # noqa: BLE001
                return None
        # 429 / 5xx = transient (rate-limit / Zyte hiccup) → retry. Any other 4xx
        # (401 bad key, 402/403 billing/suspended, 404) = terminal → stop now.
        if resp.status_code == 429 or resp.status_code >= 500:
            logger.info("[ZYTE] HTTP %s (transient) for %s (attempt %d/%d)",
                        resp.status_code, url, attempt, attempts)
            if attempt < attempts and backoff > 0:
                await asyncio.sleep(backoff)
            continue
        # An account-level terminal status (401 bad key, 402/403 billing/suspended)
        # means EVERY further render this run will also fail → trip the per-run
        # kill-switch so the seed loop stops hammering a dead/over-limit account
        # (a suspended-account 403 protects the single call; this protects the run).
        if resp.status_code in (401, 402, 403):
            global _ACCOUNT_DEAD
            _ACCOUNT_DEAD = True
            logger.warning("[ZYTE] account-level HTTP %s — disabling Zyte for the rest of this run",
                           resp.status_code)
        logger.info("[ZYTE] HTTP %s (terminal) for %s: %s",
                    resp.status_code, url, resp.text[:160])
        return None
    return None


def _match_product(
    products: List[Dict[str, Any]], product_name: str, brand: str = "",
) -> Optional[Dict[str, Any]]:
    """Best STRICT identity match among Zyte products, or None. No-fab gates so a
    wrong-brand hit (sephora returns makeup for "Creed Aventus"), a flanker, or a
    near-name is REJECTED, never shipped as the query's price.

    Gates (2026-06-26 hardening):
      (1) FORM gate — gift sets / body sprays / deodorants / candles are a different
          product form and are dropped (their price ≠ the bottle's).
      (2) HARD PRODUCT-IDENTITY gate — the candidate's identity tokens
          (_identity_tokens: brand + concentration phrase + size + form stripped)
          must EQUAL the query's. This is BRAND-AWARE (sephora omits the brand from
          titles, so a "Marc Jacobs Daisy" query matches a "Daisy - Eau de Toilette"
          title) yet rejects:
            • a flanker — "Black Opium Over Red" ({black,opium,over,red}) ≠
              "YSL Black Opium" ({black,opium});
            • a near-name — "Ombre Nomade" ≠ "Tom Ford Ombre Leather";
            • a base shipped for a flanker query — "Dior Homme" ({homme}) ≠
              "Dior Homme Intense" ({homme,intense}).
          (Replaces a loose 0.5 distinctive-overlap that admitted all three.)
      (3) CONCENTRATION precision — an explicit query concentration must match
          (mismatch rejected); among identity-equal candidates an unspecified query
          prefers the flagship EDP/EDT over the pricier Parfum/Extrait (Oud Wood →
          77 EDP, not 158 Parfum). Ties broken by Zyte's metadata.probability.
    """
    if not products:
        return None
    q_ident = _identity_tokens(product_name, brand)
    if not q_ident:
        return None
    p_words = normalize_words(product_name)
    query_lc = product_name.lower()
    q_conc = extract_concentration(product_name)
    best: Optional[Dict[str, Any]] = None
    best_score = -1.0
    for product in products:
        if not isinstance(product, dict):
            continue
        name = (product.get("name") or "").strip()
        if not name:
            continue
        if is_counterfeit_listing(name) or is_accessory(name):
            continue
        if not numbers_match(product_name, name):
            continue
        if variant_mismatch(product_name, name):
            continue
        if normalize_bhd_amount(product.get("price")) is None:
            continue
        t_words = normalize_words(name)
        if _is_wrong_form(query_lc, name.lower(), p_words, t_words):
            continue
        # (2) HARD identity equality — same product or pend. No partial-overlap,
        # no extra-token flanker, no missing-token base.
        t_ident = _identity_tokens(name, brand)
        conc_source = name
        if t_ident != q_ident and _name_is_brand_string(name, brand):
            # Brand-as-name wobble (recon 2026-07-02): the tile name is JUST the
            # brand string ("YVES SAINT LAURENT" for the Black Opium tile) — the
            # PDP URL slug carries the real identity. Fall back to slug-derived
            # tokens BEFORE rejecting; the equality gate itself is unchanged (a
            # flanker slug "black-opium-over-red" still mismatches) and the FORM
            # gate re-runs on the slug (a "…-set" slug is a different sellable
            # unit the brand-only tile name could not reveal).
            slug = _slug_text(product.get("url") or "")
            if slug:
                s_words = normalize_words(slug)
                if not _is_wrong_form(query_lc, slug.lower(), p_words, s_words):
                    t_ident = _identity_tokens(slug, brand)
                    conc_source = slug
        if t_ident != q_ident:
            continue
        # (3) concentration: reject an EXPLICIT mismatch; rank by preference.
        # (conc_source is the slug when the wobble fallback fired — the brand-only
        # tile name carries no concentration signal.)
        t_conc = extract_concentration(conc_source)
        if q_conc and t_conc and t_conc != q_conc:
            continue
        prob = 0.0
        meta = product.get("metadata")
        if isinstance(meta, dict):
            try:
                prob = float(meta.get("probability") or 0.0)
            except (TypeError, ValueError):
                prob = 0.0
        # extra non-concentration tokens (≈0 after the identity gate) + concentration
        # preference + Zyte confidence as the final deterministic tiebreak.
        non_conc_extra = len((t_words - p_words) - _CONCENTRATION_TOKENS)
        score = _concentration_bonus(q_conc, t_conc) - 0.1 * non_conc_extra + 0.001 * prob
        if score > best_score:
            best = product
            best_score = score
    return best


async def fetch_zyte_price(
    domain: str, product_name: str, currency: str = "BHD", category: str = "fragrances",
    brand: str = "",
) -> Optional[Dict[str, Any]]:
    """Genuine BHD price for an Akamai-walled luxury store via Zyte render, or None.

    OFF-CLOCK only (gated by ENABLE_ZYTE_RENDER). Searches the store via Zyte
    productList, strict-matches the product (no-fab, brand+concentration-aware),
    fils-normalizes the BHD amount, and returns a ``source_method="zyte_render_bhd"``
    price dict (is_price_showable + content-safety gated) or None on any miss /
    wrong-match / error. ``brand`` (when known) drives the brand-aware overlap so a
    multi-word brand whose name sephora omits from the title still matches. NEVER
    raises."""
    if not _enabled():
        return None
    # Per-run kill-switch: once an account-level terminal status (401/402/403) has
    # been seen this run, every further render would also fail — stop issuing paid
    # Zyte calls (protects a fragile/suspended trial across a 20-product seed loop).
    if _ACCOUNT_DEAD:
        logger.info("[ZYTE] account disabled this run (prior terminal 4xx) — skipping %s", product_name)
        return None
    store = ZYTE_STORES.get((domain or "").replace("www.", "").strip().lower())
    if not store:
        return None

    search_url = store["search"].format(q=urllib.parse.quote(product_name))
    # Retry an EMPTY (200-but-no-products) result — those are transient on sephora
    # (the 2 Mugler/Paco empties in the seed). A None from _zyte_extract is terminal
    # (auth/billing/exhausted transport retries) → stop immediately.
    empty_retries = max(1, int(os.getenv("ZYTE_EMPTY_RETRIES", "2")))
    backoff = float(os.getenv("ZYTE_RETRY_BACKOFF", "2.0"))
    products: List[Dict[str, Any]] = []
    for attempt in range(1, empty_retries + 1):
        data = await _zyte_extract(search_url, {"productList": True})
        if data is None:
            return None
        products = (data.get("productList") or {}).get("products") or []
        if products:
            break
        logger.info("[ZYTE] empty productList for '%s' @ %s (attempt %d/%d)",
                    product_name, domain, attempt, empty_retries)
        if attempt < empty_retries and backoff > 0:
            await asyncio.sleep(backoff)

    hit = _match_product(products, product_name, brand)
    if not hit:
        logger.info("[ZYTE] no strict match for '%s' @ %s (%d candidates)",
                    product_name, domain, len(products))
        return None

    amount = normalize_bhd_amount(hit.get("price"))
    if amount is None:
        return None

    domain = (domain or "").replace("www.", "").strip().lower()
    title = (hit.get("name") or "").strip()
    if _name_is_brand_string(title, brand):
        # Brand-as-name wobble hit (matched via the slug fallback) — a bare brand
        # string is NOT a usable product identity for the downstream write/display
        # gates, so surface the slug's identity as the title instead.
        slug = _slug_text(hit.get("url") or "")
        if slug:
            title = slug.title()
    price = {
        "amount": amount,
        "currency": "BHD",
        "retailer": domain,
        "url": hit.get("url") or f"https://{domain}/",
        "in_stock": True,
        "estimated": False,
        "source_method": _GENUINE_METHOD,
        "title": title,
        "confidence": 0.9,
        "image_url": (hit.get("mainImage") or {}).get("url") if isinstance(hit.get("mainImage"), dict) else None,
    }

    if not is_price_showable(product_name, price):
        return None
    try:
        from app.services.content_safety_service import get_content_safety_service
        svc = get_content_safety_service()
        if svc and not svc.is_text_safe(f"{title} {domain} {product_name}"):
            logger.info("[ZYTE] candidate dropped by content safety: %s", domain)
            return None
    except Exception:  # noqa: BLE001 — safety best-effort; never block a clean price
        pass

    logger.info("[ZYTE] genuine BHD: %.3f for '%s' @ %s", amount, product_name, domain)
    return price


async def fetch_zyte_pdp_price(
    domain: str, pdp_url: str, product_name: str, currency: str = "BHD",
    category: str = "fragrances", brand: str = "",
) -> Optional[Dict[str, Any]]:
    """VARIANT-AWARE genuine BHD price from ONE pinned PDP via Zyte product-DETAIL
    extraction, or None. The truth-critical seed path (Wave C C4).

    Unlike the productList search (`fetch_zyte_price`), the ``product`` extraction
    returns the PDP's SIZE and AVAILABILITY — so the seeded dict pins the EXACT
    variant (`pdp_url` should carry the productVariantId; recon caveat: a
    productList match for Acqua di Gio landed the 50ml DEFAULT variant under a
    100ml query) and a REAL tri-state ``in_stock`` instead of the productList
    path's unconditional True stamp. Fail-closed both ways:
      * query states a size the detail CONTRADICTS -> None (wrong variant);
      * query states a size the detail cannot CONFIRM -> None (unverified variant
        — a truth-critical seed must prove the SKU, never assume it);
      * explicit OutOfStock -> None (pends at the showable gate);
      * unknown availability stays None on the dict (tri-state, never True).
    All the productList no-fab gates (counterfeit / accessory / numbers / variant /
    form / HARD identity equality with the brand-as-name slug fallback /
    concentration) run against the detail too. OFF-CLOCK only (ENABLE_ZYTE_RENDER
    fail-closed + the per-run account kill-switch). HTTP 520 website-bans retry
    once via _zyte_extract's transient handling (recon: they alternate with 200s).
    NEVER raises."""
    if not _enabled():
        return None
    if _ACCOUNT_DEAD:
        logger.info("[ZYTE] account disabled this run (prior terminal 4xx) — skipping %s", product_name)
        return None
    if not pdp_url or not product_name:
        return None
    q_ident = _identity_tokens(product_name, brand)
    if not q_ident:
        return None

    # Retry an EMPTY (200-but-no-product) extraction — transient on sephora, same
    # class as the productList empties. A None from _zyte_extract is terminal.
    empty_retries = max(1, int(os.getenv("ZYTE_EMPTY_RETRIES", "2")))
    backoff = float(os.getenv("ZYTE_RETRY_BACKOFF", "2.0"))
    prod: Dict[str, Any] = {}
    for attempt in range(1, empty_retries + 1):
        data = await _zyte_extract(pdp_url, {"product": True})
        if data is None:
            return None
        prod = data.get("product") or {}
        if isinstance(prod, dict) and prod.get("name"):
            break
        logger.info("[ZYTE] empty product detail for %s (attempt %d/%d)",
                    pdp_url, attempt, empty_retries)
        if attempt < empty_retries and backoff > 0:
            await asyncio.sleep(backoff)
    if not isinstance(prod, dict) or not prod.get("name"):
        return None

    name = (prod.get("name") or "").strip()
    if is_counterfeit_listing(name) or is_accessory(name):
        return None
    if not numbers_match(product_name, name):
        return None
    if variant_mismatch(product_name, name):
        return None
    q_words = normalize_words(product_name)
    query_lc = product_name.lower()
    if _is_wrong_form(query_lc, name.lower(), q_words, normalize_words(name)):
        return None

    # HARD identity equality (same gate as the productList path), with the
    # brand-as-name slug fallback — the pinned PDP's slug carries the identity
    # when the extracted name is just the brand string.
    t_ident = _identity_tokens(name, brand)
    conc_source = name
    if t_ident != q_ident and _name_is_brand_string(name, brand):
        slug = _slug_text(prod.get("url") or pdp_url)
        if slug and not _is_wrong_form(query_lc, slug.lower(), q_words, normalize_words(slug)):
            t_ident = _identity_tokens(slug, brand)
            conc_source = slug
    if t_ident != q_ident:
        logger.info("[ZYTE] detail identity mismatch for '%s' @ %s (name=%r)",
                    product_name, pdp_url, name[:60])
        return None

    # Concentration — reject an EXPLICIT mismatch (the size string often carries
    # the concentration when the name omits it: size='Eau de Toilette 100ml').
    size_str = (prod.get("size") or "").strip()
    q_conc = extract_concentration(product_name)
    t_conc = extract_concentration(f"{conc_source} {size_str}".strip())
    if q_conc and t_conc and t_conc != q_conc:
        logger.info("[ZYTE] detail concentration mismatch for '%s' (%s vs %s)",
                    product_name, q_conc, t_conc)
        return None

    # SIZE / variant-awareness (the C4 core). t_size mines the detail's size field
    # + name; extract_size_ml_any snaps oz forms to standard bottle sizes.
    t_size = extract_size_ml_any(f"{name} {size_str}".strip())
    q_size = extract_size_ml_any(product_name)
    if q_size is not None:
        if t_size is None:
            logger.info("[ZYTE] detail size UNCONFIRMED for '%s' @ %s — fail-closed",
                        product_name, pdp_url)
            return None
        if t_size != q_size:
            logger.info("[ZYTE] detail size mismatch for '%s' (%sml vs %sml) — wrong variant",
                        product_name, q_size, t_size)
            return None

    amount = normalize_bhd_amount(prod.get("price"))
    if amount is None:
        return None

    # Availability — REAL tri-state from the PDP (replaces the productList path's
    # unconditional in_stock=True stamp for truth-critical seeds).
    in_stock = is_available_state(prod.get("availability"))

    # Display title: the detail name, wobble-fallback to the slug, enriched with
    # the CONFIRMED concentration/size so the downstream write/display/KPI gates
    # (which verify axes on the TITLE) see the proven variant.
    title = name
    if _name_is_brand_string(title, brand):
        slug = _slug_text(prod.get("url") or pdp_url)
        if slug:
            title = slug.title()
    if size_str and extract_concentration(size_str) and not extract_concentration(title):
        title = f"{title} {size_str}".strip()
    if t_size is not None and extract_size_ml_any(title) is None:
        title = f"{title} {t_size}ml".strip()

    b = prod.get("brand")
    if isinstance(b, dict):
        b = b.get("name")
    resolved_brand = (str(b).strip() if b else "") or (brand or "").strip()

    domain_norm = (domain or "").replace("www.", "").strip().lower()
    price: Dict[str, Any] = {
        "amount": amount,
        "currency": "BHD",
        "retailer": domain_norm,
        # The citation stays the PINNED variant-exact PDP (it carries the
        # productVariantId the recon confirmed), not Zyte's canonical URL.
        "url": pdp_url,
        "in_stock": in_stock,
        "estimated": False,
        "source_method": _GENUINE_METHOD,
        "title": title,
        "confidence": 0.9,
        "image_url": (prod.get("mainImage") or {}).get("url") if isinstance(prod.get("mainImage"), dict) else None,
    }
    if resolved_brand:
        price["brand"] = resolved_brand
    if t_size is not None:
        price["size"] = f"{t_size}ml"

    # CHOKEPOINT-grade gate (enforce_correctness=True) — a truth-critical seed
    # must clear the SAME fail-closed backstop the live display runs (explicit
    # OOS pends, non-PDP listing URL pends, exact-identity backstop), so a
    # seeded price can never be display-pended later.
    if not is_price_showable(product_name, price, category, enforce_correctness=True):
        return None
    try:
        from app.services.content_safety_service import get_content_safety_service
        svc = get_content_safety_service()
        if svc and not svc.is_text_safe(f"{title} {domain_norm} {product_name}"):
            logger.info("[ZYTE] detail candidate dropped by content safety: %s", domain_norm)
            return None
    except Exception:  # noqa: BLE001 — safety best-effort; never block a clean price
        pass

    logger.info("[ZYTE] genuine BHD (pdp detail): %.3f for '%s' @ %s (size=%s in_stock=%s)",
                amount, product_name, domain_norm, size_str or "?", in_stock)
    return price
