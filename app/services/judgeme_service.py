"""UNIT C5 — judge.me server-HTML opportunistic enrichment
(ENABLE_JUDGEME_HTML_REVIEWS, default OFF).

MEASURED (M5 measure-judgeme/VERDICT.md — zero-network scan over the 92 cached Gulf
PDPs in ``_proof/html``, index ``_proof/sweep2_curl_cffi.jsonl``): judge.me's API is
contractually closed (B6), but the MERCHANT's OWN PDP HTML — which the crawler
already holds and is permitted to read under the merchant's robots — exposes, for a
MINORITY of Gulf judge.me hosts, useful review signal:

  * AGGREGATE RATING for 9/24 hosts, via either the preview badge
    (``.jdgm-prev-badge[data-average-rating][data-number-of-reviews]`` / the review
    widget root ``.jdgm-rev-widg``) or a JSON-LD ``AggregateRating``;
  * some REVIEW TEXT for 6/24 hosts, one substantially (``myperfumes.ae`` — 28 review
    bodies both as ``.jdgm-rev__body`` DOM nodes AND as JSON-LD ``Review[]``);
  * 18/24 are pure shells (star/CSS template only, bodies fetched client-side).

So this is a SMALL, OPPORTUNISTIC enrichment, NOT a reviews spine: the aggregate
RATING is the PRIMARY target (wider recovery), review bodies are SECONDARY. It
piggybacks on HTML already in hand, so the marginal cost is ~zero — no Serper, no
render, no paid LLM, and NO network call at all (the input HTML is parsed in place).

HARD RULES (from the M5 verdict's guardrails):
  1. STRICT multi-marker install detector — a host "runs judge.me" only when a real
     loader/config/widget marker is present: ``cdn.judge.me`` loader OR a ``jdgm.*=``
     config assignment OR a ``jdgm-`` node class OR ``id="judgeme_product_reviews"``.
     NEVER the bare substring ``judge`` — M5 proved that is 6/6 false here (a Shopify
     web-pixel ``webPixelName:"Judge.me"``, an empty integration settings object, a
     failed app-block render, a minified ``c.includes("judge")``, a leftover
     ``judgeme-reviews.css`` theme asset).
  2. Read ONLY the merchant's own PDP HTML — never judge.me's closed API (B6).
  3. JSON-LD first (``AggregateRating`` + ``Review[]``), then the DOM fallback.
  4. Treat a badge of ``0.00`` / ``0`` as ABSENT (client-rendered placeholder), never
     a real zero. NB the measurement's ``0.00`` badge for myperfumes/parfum was a
     CSS-SELECTOR false match (``.jdgm-prev-badge[data-average-rating='0.00']`` inside
     a ``<style>`` block); the DOM reader here parses ``data-average-rating`` only
     from a REAL HTML element, so the true badges (myperfumes 4.79/115, parfum
     4.15/169) are recovered.
  5. Drop review bodies of length ``<= 1`` char (albayanperfumes.com's lone body is
     the single character U+0660 — junk).

This is a NEW, opportunistic, DEFAULT-OFF enrichment (it does NOT repair a
measured-0%-success production path), so per CLAUDE.md rule 1 it ships DARK: the flag
is read PER CALL via ``os.getenv`` (mirroring ``price_service.exact_gate_enabled``),
never cached at import. With the flag OFF every entry point returns ``None`` before
doing anything, and this module is not wired into any existing path, so the rollback
is byte-identical. Every parse error resolves to ``None`` (verify-or-omit); the
module NEVER raises.
"""

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Flag gate — read PER CALL (never cached at import), default OFF.
# ---------------------------------------------------------------------------

def judgeme_reviews_enabled() -> bool:
    """True iff the judge.me server-HTML enrichment is active (default OFF).

    A NEW opportunistic enrichment, not a repair of a measured-0%-success path, so
    it ships DARK and is flipped on Railway during canary. Read PER CALL from
    ``os.getenv`` (copying ``price_service.exact_gate_enabled``) so the flag can be
    flipped without a restart. With the flag OFF every entry point returns ``None``
    before doing anything, so the rollback is byte-identical."""
    return os.getenv("ENABLE_JUDGEME_HTML_REVIEWS", "").strip().lower() in (
        "true", "1", "yes", "on",
    )


# ---------------------------------------------------------------------------
# STRICT multi-marker install detector (rule 1) — never the bare 'judge' substring.
# ---------------------------------------------------------------------------

# Each pattern is a REAL judge.me install signal. ANY one is sufficient (this mirrors
# the M5 measure.py strict detector, which was 24/24 correct with 6/6 substring false
# positives excluded). The bare substring 'judge' is deliberately NOT in this set.
_STRICT_MARKERS = (
    # loader / widget / API CDN host
    re.compile(r"cdn\.judge\.me", re.I),
    re.compile(r"cdnwidget\.judge\.me", re.I),
    re.compile(r"cache\.judge\.me", re.I),
    # a jdgm.<ident>= config assignment (jdgm.CDN_HOST=, jdgm.SHOP_DOMAIN=, ...)
    re.compile(r"jdgm\.[A-Za-z_]+\s*=", re.I),
    # a jdgm- CSS class on a real node (class='...jdgm-widget...', 'jdgm-rev', ...)
    re.compile(r"""class\s*=\s*["'][^"']*\bjdgm-""", re.I),
    # the canonical review-widget mount id
    re.compile(r"""id\s*=\s*["']judgeme_product_reviews""", re.I),
)


def has_judgeme_install(html: Optional[str]) -> bool:
    """True iff the PDP HTML carries a STRICT judge.me install marker (rule 1).

    ANY one of the strict markers is sufficient. The bare substring ``judge`` /
    ``Judge.me`` is NEVER an install signal on its own — a page that only contains
    the substring (web pixel, leftover CSS asset, minified string) returns False."""
    if not html or not isinstance(html, str):
        return False
    return any(rx.search(html) for rx in _STRICT_MARKERS)


# ---------------------------------------------------------------------------
# Aggregate rating — JSON-LD first (rule 3), DOM badge fallback (rule 4).
# ---------------------------------------------------------------------------

_JSONLD_BLOCK_RE = re.compile(
    r"""<script[^>]+type\s*=\s*["']application/ld\+json["'][^>]*>(.*?)</script>""",
    re.I | re.S,
)

# A REAL DOM badge element: an HTML tag (starts with '<') that carries BOTH
# data-average-rating and data-number-of-reviews. Anchoring to a tag (not a bare
# attribute run) is what excludes the CSS ``.jdgm-prev-badge[data-average-rating=
# '0.00']`` selector that lives inside a <style> block (rule 4). Either attribute
# order is tolerated.
_DOM_BADGE_RE = re.compile(
    r"<[a-zA-Z][^>]*\bclass\s*=\s*[\"'][^\"']*"
    r"\b(?:jdgm-prev-badge|jdgm-rev-widg)\b[^\"']*[\"'][^>]*>",
    re.I,
)
_ATTR_AVG_RE = re.compile(r"""data-average-rating\s*=\s*["']([0-9]+(?:\.[0-9]+)?)["']""", re.I)
_ATTR_CNT_RE = re.compile(r"""data-number-of-reviews\s*=\s*["']([0-9]+)["']""", re.I)


def _lenient_json(raw: str) -> Optional[Any]:
    """Parse a JSON-LD block, tolerating a trailing comma before ``}``/``]``."""
    raw = raw.strip()
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:  # noqa: BLE001
        try:
            return json.loads(re.sub(r",\s*([}\]])", r"\1", raw))
        except Exception:  # noqa: BLE001
            return None


def _walk_json(node, out: List[Dict[str, Any]]) -> None:
    """Depth-first, DOCUMENT-ORDER collection of every dict node (so a JSON-LD
    ``Review[]`` is yielded in the order it appears on the page)."""
    if isinstance(node, list):
        for x in node:
            _walk_json(x, out)
    elif isinstance(node, dict):
        out.append(node)
        for v in node.values():
            if isinstance(v, (list, dict)):
                _walk_json(v, out)


def _iter_jsonld_nodes(html: str):
    """Yield every dict node in every JSON-LD block, in document order."""
    for m in _JSONLD_BLOCK_RE.finditer(html):
        data = _lenient_json(m.group(1))
        if data is None:
            continue
        nodes: List[Dict[str, Any]] = []
        _walk_json(data, nodes)
        for node in nodes:
            yield node


def _types_of(node: Dict[str, Any]) -> List[str]:
    t = node.get("@type") or node.get("type")
    types = t if isinstance(t, list) else [t]
    return [str(x).lower() for x in types if x]


def _to_float(v: Any) -> Optional[float]:
    try:
        return float(str(v).strip())
    except (TypeError, ValueError):
        return None


def _to_int(v: Any) -> Optional[int]:
    try:
        return int(float(str(v).strip()))
    except (TypeError, ValueError):
        return None


def _jsonld_aggregate(html: str) -> Optional[Dict[str, Any]]:
    """A JSON-LD ``AggregateRating`` (nested or top-level typed), or None. A 0/absent
    average or count is treated as ABSENT (rule 4)."""
    for node in _iter_jsonld_nodes(html):
        ar = None
        if isinstance(node.get("aggregateRating"), dict):
            ar = node["aggregateRating"]
        elif "aggregaterating" in _types_of(node):
            ar = node
        if not isinstance(ar, dict):
            continue
        avg = _to_float(ar.get("ratingValue"))
        cnt = _to_int(ar.get("reviewCount") or ar.get("ratingCount"))
        if avg and cnt and avg > 0 and cnt > 0:
            return {"average_score": avg, "total_reviews": cnt, "source": "jsonld"}
    return None


def _dom_badge_aggregate(html: str) -> Optional[Dict[str, Any]]:
    """The aggregate from the FIRST real DOM badge whose average AND count are both
    nonzero, or None. The first nonzero badge is the MAIN product (related-product
    carousel badges follow it); a 0.00/0 badge is a client-rendered placeholder and
    is skipped (rule 4)."""
    for m in _DOM_BADGE_RE.finditer(html):
        tag = m.group(0)
        avg_m = _ATTR_AVG_RE.search(tag)
        cnt_m = _ATTR_CNT_RE.search(tag)
        if not avg_m or not cnt_m:
            continue
        avg = _to_float(avg_m.group(1))
        cnt = _to_int(cnt_m.group(1))
        if avg and cnt and avg > 0 and cnt > 0:
            return {"average_score": avg, "total_reviews": cnt, "source": "dom_badge"}
    return None


def extract_judgeme_aggregate(html: Optional[str]) -> Optional[Dict[str, Any]]:
    """The judge.me aggregate rating ``{average_score, total_reviews, source}`` from
    the merchant HTML, or None. JSON-LD ``AggregateRating`` first (rule 3), then the
    DOM badge (rule 4). A 0.00/0 placeholder is ABSENT, never a real zero."""
    if not html or not isinstance(html, str):
        return None
    return _jsonld_aggregate(html) or _dom_badge_aggregate(html)


# ---------------------------------------------------------------------------
# Review bodies — JSON-LD first (rule 3), DOM nodes fallback.
# ---------------------------------------------------------------------------

# Minimum body length that counts as real review text (rule 5). albayan's lone body
# is the single character U+0660, which must be dropped.
_MIN_BODY_CHARS = 2


def _strip_tags(html_fragment: str) -> str:
    """Strip tags and collapse whitespace (a <br> becomes a single space)."""
    txt = re.sub(r"<[^>]+>", " ", html_fragment)
    txt = txt.replace("\xa0", " ")
    return re.sub(r"\s+", " ", txt).strip()


def _jsonld_reviews(html: str) -> List[Dict[str, Any]]:
    """Reviews from JSON-LD ``Review[]`` (author / rating / date / body). Bodies of
    length <= 1 char are dropped (rule 5)."""
    out: List[Dict[str, Any]] = []
    for node in _iter_jsonld_nodes(html):
        if "review" not in _types_of(node):
            continue
        body = node.get("reviewBody") or node.get("description") or ""
        body = str(body).strip()
        if len(body) < _MIN_BODY_CHARS:
            continue
        author = node.get("author")
        if isinstance(author, dict):
            author = author.get("name")
        rating = node.get("reviewRating")
        score = None
        if isinstance(rating, dict):
            score = _to_float(rating.get("ratingValue"))
        out.append({
            "author": (str(author).strip() if author else None),
            "title": (str(node.get("name")).strip() if node.get("name") else None),
            "body": body,
            "score": (int(score) if score is not None and score == int(score) else score),
            "date": node.get("datePublished"),
            "verified_buyer": None,
            "source": "jsonld",
        })
    return out


# A DOM review node opens with class="jdgm-rev " (a space or the closing quote right
# after 'jdgm-rev' — distinguishing it from jdgm-rev-widg / jdgm-rev__*). We split
# the HTML on this boundary so each chunk is one self-contained review node.
_REV_NODE_BOUNDARY_RE = re.compile(r"""<div[^>]*\bclass\s*=\s*["']jdgm-rev(?=[\s"'])""", re.I)
_REV_AUTHOR_RE = re.compile(r"""class\s*=\s*["'][^"']*\bjdgm-rev__author\b[^"']*["'][^>]*>(.*?)</span>""", re.I | re.S)
_REV_TITLE_RE = re.compile(r"""class\s*=\s*["'][^"']*\bjdgm-rev__title\b[^"']*["'][^>]*>(.*?)</b>""", re.I | re.S)
_REV_BODY_RE = re.compile(r"""class\s*=\s*["'][^"']*\bjdgm-rev__body\b[^"']*["'][^>]*>(.*?)</div>""", re.I | re.S)
_REV_SCORE_RE = re.compile(r"""data-score\s*=\s*["']([0-9]+(?:\.[0-9]+)?)["']""", re.I)
_REV_VERIFIED_RE = re.compile(r"""data-verified-buyer\s*=\s*["'](true|false)["']""", re.I)


def _dom_reviews(html: str) -> List[Dict[str, Any]]:
    """Reviews from ``div.jdgm-rev`` DOM nodes (author / title / body / score). Each
    node is parsed as a contiguous chunk between review-node boundaries. Bodies of
    length <= 1 char are dropped (rule 5)."""
    starts = [m.start() for m in _REV_NODE_BOUNDARY_RE.finditer(html)]
    if not starts:
        return []
    bounds = starts + [len(html)]
    out: List[Dict[str, Any]] = []
    for i in range(len(starts)):
        chunk = html[bounds[i]:bounds[i + 1]]
        body_m = _REV_BODY_RE.search(chunk)
        if not body_m:
            continue
        body = _strip_tags(body_m.group(1))
        if len(body) < _MIN_BODY_CHARS:
            continue
        author_m = _REV_AUTHOR_RE.search(chunk)
        title_m = _REV_TITLE_RE.search(chunk)
        score_m = _REV_SCORE_RE.search(chunk)
        verified_m = _REV_VERIFIED_RE.search(chunk)
        score = _to_float(score_m.group(1)) if score_m else None
        out.append({
            "author": (_strip_tags(author_m.group(1)) or None) if author_m else None,
            "title": (_strip_tags(title_m.group(1)) or None) if title_m else None,
            "body": body,
            "score": (int(score) if score is not None and score == int(score) else score),
            "date": None,
            "verified_buyer": (verified_m.group(1).lower() == "true") if verified_m else None,
            "source": "dom",
        })
    return out


def extract_judgeme_reviews(html: Optional[str]) -> List[Dict[str, Any]]:
    """Review bodies from the merchant HTML — JSON-LD ``Review[]`` first (rule 3),
    DOM ``div.jdgm-rev`` nodes as fallback. Bodies of length <= 1 char are dropped
    (rule 5). Returns [] when no usable body is present (the common shell case)."""
    if not html or not isinstance(html, str):
        return []
    reviews = _jsonld_reviews(html)
    if reviews:
        return reviews
    return _dom_reviews(html)


# ---------------------------------------------------------------------------
# Public entry point — HTML in hand, no network.
# ---------------------------------------------------------------------------

def _retailer_of(url: str) -> str:
    if not url:
        return ""
    try:
        return (urlparse(url).netloc or "").replace("www.", "").strip().lower()
    except Exception:  # noqa: BLE001
        return ""


def extract_judgeme_from_html(
    html: Optional[str], url: str = "",
) -> Optional[Dict[str, Any]]:
    """Opportunistic judge.me enrichment from the merchant's OWN PDP HTML, or None.

    Flow: gate on the flag (default OFF -> None); require a STRICT judge.me install
    (rule 1 — never the bare substring); recover the aggregate RATING (primary:
    JSON-LD ``AggregateRating`` first, then the DOM badge, 0.00/0 treated as absent)
    and, secondarily, any server-rendered review BODIES (JSON-LD ``Review[]`` first,
    then ``div.jdgm-rev`` nodes, 1-char junk dropped).

    Returns::

        {
          "source": "judgeme",
          "retailer": "<host>",
          "rating": {"average_score", "total_reviews", "source"} | None,
          "reviews": [ {author, title, body, score, date, verified_buyer, source} ],
          "rating_primary": True,
        }

    Returns None on flag-OFF / no install / when NOTHING usable is recovered (no
    aggregate AND no review body — the 18/24 pure-shell case). NEVER raises, NEVER
    calls judge.me's API, issues NO network request ($0)."""
    if not judgeme_reviews_enabled():
        return None
    if not has_judgeme_install(html):
        return None
    try:
        rating = extract_judgeme_aggregate(html)
        reviews = extract_judgeme_reviews(html)
    except Exception as exc:  # noqa: BLE001 — verify-or-omit; a parse error is a miss
        logger.info("[JUDGEME] parse error, treating as a miss: %s", exc)
        return None
    if rating is None and not reviews:
        # Pure shell (18/24): install present but zero server-side signal.
        return None
    retailer = _retailer_of(url)
    logger.info(
        "[JUDGEME] enrichment @ %s: rating=%s (%s), %d review bodies",
        retailer or "?",
        (rating or {}).get("average_score"),
        (rating or {}).get("source"),
        len(reviews),
    )
    return {
        "source": "judgeme",
        "retailer": retailer,
        "rating": rating,
        "reviews": reviews,
        "rating_primary": True,
    }
