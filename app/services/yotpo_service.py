"""UNIT B6 — Yotpo review + ratings adapter (ENABLE_YOTPO_REVIEWS, default OFF).

MEASURED (research/B6/adapter_yotpo.json): Yotpo's PUBLIC read endpoint

    GET https://api-cdn.yotpo.com/v1/widget/{app_key}/products/{product_id}/reviews.json?per_page=150

returns the full review text + score + title + verified_buyer + PRE-COMPUTED
``sentiment`` + ``language`` in ONE unauthenticated call (no header, no cookie,
no Referer). ``api-cdn.yotpo.com/robots.txt`` (fetched 2026-08-30) is a blanket
``Disallow: /`` with an explicit per-path ``Allow`` list, and the review-read
paths are affirmatively opted in for anonymous crawlers — so this adapter reads
ONLY the merchant's own Yotpo widget data through paths Yotpo itself permits,
never Yotpo's closed authenticated API. The ToS binds a contracting "Client"
(the merchant), not an anonymous reader of the robots-allowed widget endpoint.

The pre-computed ``sentiment`` / ``language`` REPLACE the paid LLM sentiment pass
for Yotpo-sourced reviews (both are otherwise paid work in the Qaren pipeline),
and the aggregate rating (``bottomline``) is the PRIMARY target — review bodies
are secondary (measured: full text recovered for only a couple of Gulf hosts;
ratings recover far more widely).

HARD RULES (from the B6 spec):
  1. ``app_key`` MUST be exactly 40 chars ``[A-Za-z0-9]`` — the 32-hex boilerplate
     key (e51a4e2686c9072bb405bf25837fe8f7) is a decoy that 404s 'Account not
     found'; it is copy-pasted theme boilerplate, not a key.
  2. REJECT the bare substring ``yotpo`` as an install signal (26/34 corpus pages
     that contain 'yotpo' carry only the stock Shopify metafield snippet
     ``var MetafieldYotpoRating = null`` and have NO install). Detection requires
     a valid 40-char key from one of the three strict PDP patterns.
  3. Enforce a hard ALLOWLIST of the robots-allowed Yotpo paths, never a denylist —
     every fetched URL's path is checked against ``_YOTPO_ROBOTS_ALLOW`` BEFORE the
     request is issued.
  4. On ``total_review == 0`` do ONE ``yotpo_site_reviews`` liveness call to
     classify bad-key (dead account) vs empty-product (live account, no reviews).
  5. Log the robots permission relied on for each fetched path.

This is a NEW, opportunistic, DEFAULT-OFF enrichment capability — it does NOT
repair a measured-0%-success production path, so per CLAUDE.md rule 1 it ships
DARK (flag read PER CALL via ``os.getenv``, mirroring
``price_service.exact_gate_enabled``). With the flag OFF every entry point returns
``None`` before doing anything and no network call is issued, so the rollback is
byte-identical.

The adapter NEVER raises: every network / parse error resolves to ``None``
(verify-or-omit). ``$0`` — no Serper, no render, no paid LLM.
"""

import asyncio
import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Yotpo's public read CDN host (identical robots grant on api.yotpo.com).
YOTPO_CDN_HOST = "api-cdn.yotpo.com"
_YOTPO_BASE = f"https://{YOTPO_CDN_HOST}"

# Per-request timeout (SPEC universal recipe; Yotpo's CDN is fast).
_HTTP_TIMEOUT = 12

# per_page — measured max that returned a complete review set in ONE request.
_PER_PAGE_MAX = 150

# ---------------------------------------------------------------------------
# The robots ALLOWLIST (rule 3) — api-cdn.yotpo.com/robots.txt, fetched
# 2026-08-30. Blanket ``Disallow: /`` + these explicit ``Allow`` prefixes. We
# admit a fetch ONLY when its path prefix-matches one of these patterns (robots
# ``*`` == any run of chars). This is an ALLOWLIST: an unlisted path is refused.
# ---------------------------------------------------------------------------
_YOTPO_ROBOTS_ALLOW: Tuple[str, ...] = (
    "/products/*/*/reviews",
    "/products/*/*/bottomline",
    "/products/*/*/questions",
    "/products/*/*/qna_bottomline",
    "/v1/widget/*",
    "/v1/star_distribution/*",
    "/v3/rich_snippets/*",
    "/v3/storefront/store/*",
)


def _allow_pattern_to_regex(pattern: str) -> "re.Pattern[str]":
    """Compile a robots ``Allow`` prefix pattern into an anchored regex. Robots
    patterns are prefix matches with ``*`` == any run of characters (including
    ``/``), so ``/products/*/*/reviews`` matches
    ``/products/<key>/<pid>/reviews.json``."""
    esc = re.escape(pattern).replace(r"\*", ".*")
    return re.compile("^" + esc)


_YOTPO_ALLOW_RE: Tuple["re.Pattern[str]", ...] = tuple(
    _allow_pattern_to_regex(p) for p in _YOTPO_ROBOTS_ALLOW
)


def robots_allows_path(path: str) -> bool:
    """True iff ``path`` is on the Yotpo robots ALLOWLIST (rule 3). ``path`` is a
    URL path (leading ``/``, no host). A path that matches NONE of the explicit
    Allow prefixes is refused — this is an allowlist, never a denylist."""
    if not path or not path.startswith("/"):
        return False
    return any(rx.match(path) for rx in _YOTPO_ALLOW_RE)


def _allowed_rule_for(path: str) -> Optional[str]:
    """The robots Allow pattern a ``path`` relies on (for the rule-5 log), or None."""
    for pattern, rx in zip(_YOTPO_ROBOTS_ALLOW, _YOTPO_ALLOW_RE):
        if rx.match(path):
            return pattern
    return None


# ---------------------------------------------------------------------------
# Flag gate — read PER CALL (never cached at import), default OFF.
# ---------------------------------------------------------------------------

def yotpo_reviews_enabled() -> bool:
    """True iff the Yotpo review/ratings adapter is active (default OFF).

    A NEW opportunistic enrichment capability, not a repair of a
    measured-0%-success path, so it ships DARK and is flipped on Railway during
    canary (contrast ENABLE_FIRECRAWL_RAW_HTML, which repaired a live 0/9 path
    and justified default-ON). Read PER CALL from ``os.getenv`` (copying
    ``price_service.exact_gate_enabled``) so the flag can be flipped without a
    restart. With the flag OFF every entry point returns ``None`` before doing
    anything, so the rollback is byte-identical."""
    return os.getenv("ENABLE_YOTPO_REVIEWS", "").strip().lower() in (
        "true", "1", "yes", "on",
    )


# ---------------------------------------------------------------------------
# app_key + product_id extraction from the PDP HTML the crawler already holds.
# ---------------------------------------------------------------------------

# A valid Yotpo app_key is EXACTLY 40 chars of [A-Za-z0-9] (rule 1). The 32-hex
# decoy and the 22-char strings are all shorter and 404.
_APP_KEY_RE = re.compile(r"^[A-Za-z0-9]{40}$")

# Three PDP extraction patterns, ranked by measured reliability. Each captures a
# CANDIDATE that is then hard-gated by ``_is_valid_app_key`` (exactly 40
# [A-Za-z0-9]) — so a shorter/decoy capture is dropped even if a lenient class
# matched it.
_KEY_PATTERNS: Tuple["re.Pattern[str]", ...] = (
    # cdn-widgetsrepository loader — measured 3/3 valid; the 40 length gate is
    # load-bearing (a lenient class here would over-capture the decoy).
    re.compile(r"cdn-widgetsrepository\.yotpo\.com/v1/loader/([A-Za-z0-9_-]{20,})"),
    # data-appkey attribute (non-Shopify Salesforce/SFCC sites).
    re.compile(r"""data-appkey\s*=\s*["']([A-Za-z0-9]{20,})["']"""),
    # legacy staticw2 widget.js loader.
    re.compile(r"staticw2\.yotpo\.com/([A-Za-z0-9_-]{20,})/widget\.js"),
)

# product_id: a numeric id on a tag that ALSO references yotpo (either attribute
# order), so the bare-'yotpo' theme snippet — which carries no product-id tag —
# can never satisfy this. Covers the Shopify numeric product id and the
# non-Shopify data-product-id on id=yotpo-reviews-top-div.
_PRODUCT_ID_RE = re.compile(
    r"<[^>]*yotpo[^>]*data-product-id\s*=\s*[\"'](\d+)[\"']"
    r"|<[^>]*data-product-id\s*=\s*[\"'](\d+)[\"'][^>]*yotpo",
    re.IGNORECASE,
)


def _is_valid_app_key(key: Optional[str]) -> bool:
    """Rule 1 — True iff ``key`` is EXACTLY 40 chars of [A-Za-z0-9]."""
    return bool(key) and bool(_APP_KEY_RE.match(key))


def extract_yotpo_app_key(html: Optional[str]) -> Optional[str]:
    """The Yotpo app_key from PDP HTML, or None. Tries the three ranked patterns
    in order and returns the FIRST candidate that passes the strict 40-char gate.
    A candidate that is not exactly 40 [A-Za-z0-9] (the 32-hex decoy, the 22-char
    strings) is rejected."""
    if not html or not isinstance(html, str):
        return None
    for rx in _KEY_PATTERNS:
        for m in rx.finditer(html):
            cand = m.group(1)
            if _is_valid_app_key(cand):
                return cand
    return None


def extract_yotpo_product_id(html: Optional[str]) -> Optional[str]:
    """The Yotpo product_id (numeric) from a yotpo-widget tag, or None. Rule 2:
    the id must sit on a tag that references 'yotpo', so the stock metafield
    snippet (no product-id tag) never yields one."""
    if not html or not isinstance(html, str):
        return None
    m = _PRODUCT_ID_RE.search(html)
    if not m:
        return None
    return m.group(1) or m.group(2)


def extract_yotpo_install(html: Optional[str]) -> Optional[Tuple[str, str]]:
    """``(app_key, product_id)`` iff the PDP carries a VALID Yotpo install, else
    None. Rules 1+2: requires BOTH a strict 40-char key AND a widget product-id —
    the bare 'yotpo' substring / stock metafield snippet satisfies neither."""
    app_key = extract_yotpo_app_key(html)
    if not app_key:
        return None
    product_id = extract_yotpo_product_id(html)
    if not product_id:
        return None
    return app_key, product_id


# ---------------------------------------------------------------------------
# URL builders — every path is on the robots ALLOWLIST (rule 3).
# ---------------------------------------------------------------------------

def _reviews_url(app_key: str, product_id: str, per_page: int = _PER_PAGE_MAX) -> str:
    return (
        f"{_YOTPO_BASE}/v1/widget/{app_key}/products/{product_id}"
        f"/reviews.json?per_page={per_page}"
    )


def _site_reviews_url(app_key: str) -> str:
    # The site-wide liveness product id is the literal 'yotpo_site_reviews'.
    return (
        f"{_YOTPO_BASE}/v1/widget/{app_key}/products/yotpo_site_reviews"
        f"/reviews.json?per_page=1"
    )


def _bottomline_url(app_key: str, product_id: str) -> str:
    return f"{_YOTPO_BASE}/products/{app_key}/{product_id}/bottomline"


# ---------------------------------------------------------------------------
# Transport — allowlist-checked GET, never raises.
# ---------------------------------------------------------------------------

def _path_of(url: str) -> str:
    from urllib.parse import urlparse
    return urlparse(url).path or ""


async def _yotpo_get_json(url: str) -> Optional[Dict[str, Any]]:
    """GET a Yotpo read URL and return parsed JSON, or None.

    Rule 3 — the URL's path is checked against the robots ALLOWLIST BEFORE the
    request is issued; a non-allowlisted path is REFUSED (logged + None, no
    network call). Rule 5 — logs the robots Allow rule relied on. A non-200 /
    network error / non-JSON body all resolve to None (verify-or-omit; never
    raises)."""
    path = _path_of(url)
    rule = _allowed_rule_for(path)
    if rule is None:
        logger.warning("[YOTPO] refusing non-allowlisted path (allowlist, not denylist): %s", path)
        return None
    # Rule 5 — record the robots permission this read relies on.
    logger.info("[YOTPO] GET %s (robots Allow: %s on %s/robots.txt)", path, rule, YOTPO_CDN_HOST)
    try:
        from curl_cffi import requests as curl_requests
        resp = await asyncio.to_thread(
            lambda: curl_requests.get(
                url,
                impersonate="chrome",
                timeout=_HTTP_TIMEOUT,
                allow_redirects=True,
            )
        )
    except Exception as exc:  # noqa: BLE001 — a fetch error is a miss, never a crash
        logger.info("[YOTPO] GET failed for %s: %s", path, exc)
        return None
    if getattr(resp, "status_code", 0) != 200:
        logger.info("[YOTPO] HTTP %s for %s", getattr(resp, "status_code", "?"), path)
        return None
    try:
        payload = resp.json()
    except Exception:  # noqa: BLE001 — non-JSON body -> miss
        return None
    return payload if isinstance(payload, dict) else None


# ---------------------------------------------------------------------------
# Parsing.
# ---------------------------------------------------------------------------

def _response(payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """The Yotpo ``response`` envelope (``{bottomline, reviews, pagination, ...}``),
    or ``{}``."""
    if not isinstance(payload, dict):
        return {}
    resp = payload.get("response")
    return resp if isinstance(resp, dict) else {}


def _bottomline_total(payload: Optional[Dict[str, Any]]) -> int:
    """``response.bottomline.total_review`` as an int (0 when absent/malformed)."""
    bl = _response(payload).get("bottomline")
    if not isinstance(bl, dict):
        return 0
    try:
        return int(bl.get("total_review") or 0)
    except (TypeError, ValueError):
        return 0


def _parse_rating(payload: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """The aggregate rating from ``response.bottomline`` (the PRIMARY target), or
    None when no usable bottomline is present."""
    bl = _response(payload).get("bottomline")
    if not isinstance(bl, dict):
        return None
    try:
        total = int(bl.get("total_review") or 0)
    except (TypeError, ValueError):
        total = 0
    avg_raw = bl.get("average_score")
    try:
        average = float(avg_raw) if avg_raw is not None else None
    except (TypeError, ValueError):
        average = None
    return {
        "average_score": average,
        "total_reviews": total,
        "star_distribution": bl.get("star_distribution") or {},
    }


def _map_review(raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """One ``response.reviews[]`` entry -> the normalized review dict, carrying the
    PRE-COMPUTED ``sentiment`` + ``language`` (which replace the paid LLM pass).
    None when the entry is malformed."""
    if not isinstance(raw, dict):
        return None
    content = (raw.get("content") or "").strip()
    title = (raw.get("title") or "").strip()
    # Keep an entry only when it carries SOME textual signal or an explicit
    # rating (a rating-only review still contributes to the aggregate view).
    if not content and not title and raw.get("score") is None:
        return None
    try:
        score = float(raw.get("score")) if raw.get("score") is not None else None
    except (TypeError, ValueError):
        score = None
    sentiment = raw.get("sentiment")
    try:
        sentiment = float(sentiment) if sentiment is not None else None
    except (TypeError, ValueError):
        sentiment = None
    user = raw.get("user")
    display_name = user.get("display_name") if isinstance(user, dict) else None
    return {
        "id": raw.get("id"),
        "title": title,
        "content": content,
        "score": score,
        # PRE-COMPUTED — do NOT re-run the paid LLM sentiment pass on these.
        "sentiment": sentiment,
        "language": raw.get("language"),
        "verified_buyer": bool(raw.get("verified_buyer")),
        "created_at": raw.get("created_at"),
        "votes_up": raw.get("votes_up"),
        "votes_down": raw.get("votes_down"),
        "user": display_name,
    }


def parse_yotpo_reviews(
    payload: Optional[Dict[str, Any]], app_key: str, product_id: str,
    retailer: str = "",
) -> Optional[Dict[str, Any]]:
    """Build the adapter result (rating + mapped reviews) from a reviews.json
    payload, or None when there is no usable rating and no review. The
    pre-computed sentiment/language are carried through and the result flags that
    the LLM sentiment pass is NOT required for these reviews."""
    rating = _parse_rating(payload)
    raw_reviews = _response(payload).get("reviews")
    reviews: List[Dict[str, Any]] = []
    if isinstance(raw_reviews, list):
        for r in raw_reviews:
            mapped = _map_review(r)
            if mapped is not None:
                reviews.append(mapped)
    if not reviews and (rating is None or rating.get("total_reviews", 0) <= 0):
        return None
    return {
        "source": "yotpo",
        "app_key": app_key,
        "product_id": product_id,
        "retailer": retailer,
        "rating": rating,
        "reviews": reviews,
        # The pre-computed sentiment/language REPLACE the paid LLM sentiment pass.
        "sentiment_source": "yotpo_precomputed",
        "llm_sentiment_required": False,
    }


# ---------------------------------------------------------------------------
# Liveness classification (rule 4).
# ---------------------------------------------------------------------------

async def classify_yotpo_key(app_key: str) -> str:
    """ONE ``yotpo_site_reviews`` liveness call -> ``"live"`` or ``"dead"``.

    A live account returns ``bottomline.total_review > 0`` for the site-wide
    product even when a specific product has none — so this distinguishes a genuine
    empty-product from a bad/decoy key (rule 4). Any miss (404 / error / zero
    site total) is classified ``"dead"``."""
    payload = await _yotpo_get_json(_site_reviews_url(app_key))
    return "live" if _bottomline_total(payload) > 0 else "dead"


# ---------------------------------------------------------------------------
# Public entry points.
# ---------------------------------------------------------------------------

async def fetch_yotpo_reviews(
    html: Optional[str], url: str = "", per_page: int = _PER_PAGE_MAX,
) -> Optional[Dict[str, Any]]:
    """Real reviews + aggregate rating for a PDP carrying a valid Yotpo install,
    or None.

    Flow: gate on the flag (default OFF -> None, no fetch); extract the valid
    40-char app_key + product_id from the PDP HTML the crawler already holds (no
    extra request); GET the robots-allowed reviews.json (per_page capped at the
    measured 150). When the product has reviews, return the parsed result with the
    pre-computed sentiment/language carried (replacing the paid LLM pass). When
    ``total_review == 0``, fire ONE ``yotpo_site_reviews`` liveness call to
    classify bad-key vs empty-product (rule 4) and return None either way.

    Returns None on flag-OFF / no install / fetch miss / zero reviews / error.
    NEVER raises. ``$0`` — no Serper, no render, no paid LLM."""
    if not yotpo_reviews_enabled():
        return None
    install = extract_yotpo_install(html)
    if install is None:
        return None
    app_key, product_id = install

    retailer = ""
    if url:
        from urllib.parse import urlparse
        retailer = (urlparse(url).netloc or "").replace("www.", "").strip().lower()

    per_page = min(int(per_page or _PER_PAGE_MAX), _PER_PAGE_MAX)
    payload = await _yotpo_get_json(_reviews_url(app_key, product_id, per_page))
    if payload is None:
        return None

    if _bottomline_total(payload) <= 0:
        # Rule 4 — ONE liveness call classifies bad-key vs empty-product.
        verdict = await classify_yotpo_key(app_key)
        if verdict == "live":
            logger.info(
                "[YOTPO] product %s on live key %s… has no reviews (empty-product, not bad-key)",
                product_id, app_key[:8],
            )
        else:
            logger.info(
                "[YOTPO] key %s… classified DEAD via yotpo_site_reviews liveness (bad-key)",
                app_key[:8],
            )
        return None

    result = parse_yotpo_reviews(payload, app_key, product_id, retailer=retailer)
    if result is not None:
        logger.info(
            "[YOTPO] %d reviews + %s aggregate for product %s @ %s",
            len(result["reviews"]),
            (result.get("rating") or {}).get("average_score"),
            product_id, retailer or "?",
        )
    return result


async def fetch_yotpo_bottomline(
    html: Optional[str], url: str = "",
) -> Optional[Dict[str, Any]]:
    """Ratings-only aggregate for a PDP carrying a valid Yotpo install, or None.

    Uses the cheaper ``/products/{app_key}/{product_id}/bottomline`` endpoint
    (robots-allowed) to fill the ratings gap without pulling review bodies —
    ratings are the primary, more-widely-recoverable target. Flag-OFF -> None,
    no fetch. NEVER raises."""
    if not yotpo_reviews_enabled():
        return None
    install = extract_yotpo_install(html)
    if install is None:
        return None
    app_key, product_id = install
    payload = await _yotpo_get_json(_bottomline_url(app_key, product_id))
    rating = _parse_rating(payload)
    if rating is None or rating.get("total_reviews", 0) <= 0:
        return None
    return rating
