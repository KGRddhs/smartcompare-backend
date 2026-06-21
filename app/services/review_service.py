"""Review Service — all review-related functions extracted from structured_comparison_service.

Functions are standalone (no self).
FIX M5: _clean_review_citations processes review_summary.highlights[].point format.
FIX M6: Removed dead code processing detailed_praises/detailed_complaints (never populated).
"""
import asyncio
import os
import re
import logging
from typing import Optional, List, Dict, Any, Tuple
from urllib.parse import urlparse

from app.services.extraction_service import (
    extract_reviews,
    get_reviews_cache_key,
)
from app.services.serper_service import search_web
from app.services.cache_service import get_cached, set_cached
from app.services.api_budget_service import has_budget, record_usage
# Bundle B S3 L2 — YouTube cited review signal (imported at module scope so
# tests can patch app.services.review_service.fetch_youtube_review_signal).
from app.services.youtube_service import fetch_youtube_review_signal

logger = logging.getLogger(__name__)

# Cache TTL
REVIEWS_CACHE_TTL = 7 * 24 * 60 * 60  # 7 days

# Category-specific review search terms
# L2.10 — added 4 missing entries (supplements/fragrances/haircare/other) so
# every category in CATEGORY_SPEC_SCHEMAS has its own review-search term
# vocabulary. Previously these fell back to the implicit "user reviews pros
# cons rating" string, which yielded weak Serper organic results for
# supplements (no dosage/clinical context) and fragrances (no
# longevity/sillage signal).
CATEGORY_REVIEW_TERMS = {
    "electronics": "user reviews pros cons battery camera performance display",
    "grocery": "user reviews taste quality ingredients value",
    "beauty": "user reviews results skin ingredients effectiveness",
    "makeup": "user reviews shade match coverage finish wear",
    "skincare": "user reviews skin texture irritation results",
    "fashion": "user reviews fit quality comfort sizing",
    "home": "user reviews quality durability assembly value",
    "sports": "user reviews performance comfort durability",
    "supplements": "user reviews dosage effectiveness side effects clinical purity",
    "fragrances": "user reviews longevity sillage projection scent character season",
    "haircare": "user reviews results frizz scalp hair type texture scent",
    "other": "user reviews quality value durability function",
}

GARBAGE_PATTERNS = [
    r"learn more about",
    r"see (full |more )?details",
    r"click (here|to)",
    r"read more",
    r"shop now",
    r"free (shipping|delivery|returns)",
    r"add to (cart|bag|wishlist)",
    r"available (in|at) (stores|select)",
    r"sign up for",
    r"join (our|the) (newsletter|waitlist)",
]

NEGATIVE_INDICATORS = {
    "bad", "poor", "disappointing", "issue", "problem", "broke", "broken",
    "flimsy", "cheap", "overpriced", "uncomfortable", "fragile", "peeling",
    "fading", "cracking", "defect", "flaw", "mediocre", "underwhelming",
    "lacking", "missing", "difficult", "annoying", "frustrating", "worse", "worst",
}

POSITIVE_INDICATORS = {
    "great", "excellent", "premium", "beautiful", "perfect", "love",
    "amazing", "wonderful", "fantastic", "superb", "outstanding", "impressive",
    "comfortable", "luxurious", "elegant", "sturdy", "durable", "quality",
}


def clean_review_content(reviews: dict) -> dict:
    """Remove garbage text, short items, and misclassified sentiments from reviews."""
    for section in ["common_praises", "common_complaints"]:
        items = reviews.get(section, [])
        if not items:
            continue
        cleaned = []
        for item in items:
            text = item.get("text", "") if isinstance(item, dict) else str(item)
            if any(re.search(p, text, re.IGNORECASE) for p in GARBAGE_PATTERNS):
                continue
            if len(text.split()) < 8:
                continue
            if "complaint" in section:
                words = set(text.lower().split())
                has_negative = bool(words & NEGATIVE_INDICATORS)
                has_positive = bool(words & POSITIVE_INDICATORS)
                if has_positive and not has_negative:
                    continue
            cleaned.append(item)
        reviews[section] = cleaned

    # FIX M5: Also clean review_summary.highlights[].point
    review_summary = reviews.get("review_summary", {})
    if isinstance(review_summary, dict):
        highlights = review_summary.get("highlights", [])
        if highlights and isinstance(highlights, list):
            cleaned_highlights = []
            for h in highlights:
                if isinstance(h, dict):
                    point = h.get("point", "")
                    if any(re.search(p, point, re.IGNORECASE) for p in GARBAGE_PATTERNS):
                        continue
                    if len(point.split()) < 4:
                        continue
                    cleaned_highlights.append(h)
                else:
                    cleaned_highlights.append(h)
            review_summary["highlights"] = cleaned_highlights

    return reviews


def _extract_domain(url: str) -> str:
    """Extract clean domain from URL."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.replace("www.", "")
        return domain or ""
    except Exception:
        return ""


def clean_review_citations(reviews: dict, search_results: list) -> dict:
    """Replace [snippet_N] with source domain name in review text fields.

    FIX M5: Now processes review_summary.highlights[].point format (current format).
    FIX M6: Removed dead code for detailed_praises/detailed_complaints (never populated).
    """
    snippet_source_map = {}
    for i, result in enumerate(search_results or []):
        link = result.get("link", "")
        if link:
            snippet_source_map[str(i + 1)] = _extract_domain(link)

    def _attribute(num: str) -> str:
        domain = snippet_source_map.get(num, "")
        return f"Per {domain}: " if domain else ""

    def replace_citation(text: str) -> str:
        def snippet_replacer(match):
            return _attribute(match.group(1))

        # 1) Attributed `[snippet_N]` markers (existing behavior preserved).
        text = re.sub(r'\[snippet_(\d+)\]\s*', snippet_replacer, text)

        # Task C5: 2) bare numeric `[2]`/`[3]` markers leak from the model when
        # it cites by raw index instead of `[snippet_N]`. They render literally
        # in the UI ("Great scent [2] lasts long"). Strip/attribute them with the
        # same source map. Anchored to `\[\d+\]` so it can NEVER touch the just-
        # inserted "Per domain:" text (no brackets) nor inline ratios like 5/5.
        def bare_replacer(match):
            return _attribute(match.group(1))

        text = re.sub(r'\[(\d+)\]\s*', bare_replacer, text)
        return text

    cleaned = dict(reviews)

    # Legacy fields (common_praises, common_complaints)
    for key in ["common_praises", "common_complaints"]:
        if key in cleaned and isinstance(cleaned[key], list):
            cleaned[key] = [replace_citation(str(item)) for item in cleaned[key]]

    # FIX M5 + Task C5: current format — review_summary.consensus + highlights[].point
    review_summary = cleaned.get("review_summary", {})
    if isinstance(review_summary, dict):
        if isinstance(review_summary.get("consensus"), str):
            review_summary["consensus"] = replace_citation(review_summary["consensus"])
        highlights = review_summary.get("highlights", [])
        if highlights and isinstance(highlights, list):
            for h in highlights:
                if isinstance(h, dict) and "point" in h:
                    h["point"] = replace_citation(str(h["point"]))

    # Task C5: review-source editorial quotes (ENABLE_REVIEW_SOURCE_CONSULT path).
    # Each quote carries a `text` field that can leak bare/snippet markers too.
    quotes = cleaned.get("review_source_quotes")
    if isinstance(quotes, list):
        for q in quotes:
            if isinstance(q, dict) and isinstance(q.get("text"), str):
                q["text"] = replace_citation(q["text"])

    return cleaned


# ITEM 1 — surface retailer_quotes from REAL review material (esp. fragrances).
#
# The FE Reviews accordion (ResultsAccordion.tsx) renders
# `reviews.products[i].retailer_quotes` (`{retailer, text, rating?}`) as compact
# per-source lines (AMAZON ★★★★★ "quote"). Fragrances previously emitted only
# review_summary.{consensus,highlights}, so the FE fell back. This builder
# surfaces up to 3 of the SAME organic Serper snippets the review extraction
# already consumed (ZERO extra API calls), attributed to their real source
# domain — category-general (works for fragrances).
#
# HARD CONSTRAINT (CLAUDE.md invariant): ratings are NEVER AI-generated. So this
# never fabricates a per-quote star rating. `rating` is set ONLY when a REAL
# numeric rating for that source exists in the search data (Serper richSnippet
# or a top-level `rating`); otherwise the key is OMITTED (the FE ReviewLine
# renders no stars when rating is absent — verified gracefully handled).

# A highlight quote text must be at least this long to be a meaningful display
# snippet (mirrors fetch_retailer_quotes' 20-char floor).
_MIN_QUOTE_CHARS = 20

# Matches both `[snippet_N]` and bare `[N]` citation markers the review model
# emits in highlights[].point — used to map a highlight back to its organic
# source index. (The same two marker forms clean_review_citations scrubs.)
_CITATION_MARKER_RE = re.compile(r"\[(?:snippet_)?(\d+)\]")


def _snippet_real_rating(result: Dict[str, Any]) -> Optional[float]:
    """A REAL numeric rating for an organic search result, or None.

    Reads a top-level `rating` first, then the Serper richSnippet
    detected_extensions rating (the same shape fetch_retailer_quotes reads).
    NEVER synthesizes — returns None when no real rating is present so the
    caller OMITS the rating key entirely (no fabricated stars)."""
    if not isinstance(result, dict):
        return None
    top_level = result.get("rating")
    if isinstance(top_level, (int, float)):
        return float(top_level)
    rich = result.get("richSnippet") or {}
    top = rich.get("top") if isinstance(rich, dict) else None
    if isinstance(top, dict):
        detected = top.get("detected_extensions") or {}
        rating_val = detected.get("rating") or detected.get("starRating")
        if isinstance(rating_val, (int, float)):
            return float(rating_val)
    return None


def build_retailer_quotes_from_reviews(
    reviews: Optional[Dict[str, Any]],
    search_results: Optional[List[Dict[str, Any]]],
) -> List[Dict[str, Any]]:
    """Up to 3 `{retailer, text, rating?}` quotes from REAL review snippets.

    For each review_summary highlight (in order), parse its `[snippet_N]` /
    bare `[N]` citation, map the index to the organic search result it cites,
    and emit that result's real source domain (`retailer`) + its real snippet
    text (`text`). Deduped by source domain (no duplicate AMAZON lines), capped
    at 3. `rating` is included ONLY when the cited result carries a real numeric
    rating — never fabricated.

    Returns [] when reviews/highlights/search_results are missing, when no
    highlight is source-attributable, or when every cited snippet is too short.
    Pure + zero network — operates on data the pipeline already has.
    """
    if not isinstance(reviews, dict) or not isinstance(search_results, list) or not search_results:
        return []
    review_summary = reviews.get("review_summary")
    if not isinstance(review_summary, dict):
        return []
    highlights = review_summary.get("highlights")
    if not isinstance(highlights, list) or not highlights:
        return []

    # snippet index (1-based) → organic result (same convention as
    # clean_review_citations' snippet_source_map).
    by_index: Dict[int, Dict[str, Any]] = {}
    for i, result in enumerate(search_results):
        if isinstance(result, dict):
            by_index[i + 1] = result

    quotes: List[Dict[str, Any]] = []
    seen_domains = set()
    for h in highlights:
        if len(quotes) >= 3:
            break
        if not isinstance(h, dict):
            continue
        point = h.get("point")
        if not isinstance(point, str):
            continue
        m = _CITATION_MARKER_RE.search(point)
        if not m:
            continue  # uncited claim — cannot attribute a real source, skip
        idx = int(m.group(1))
        result = by_index.get(idx)
        if not isinstance(result, dict):
            continue
        domain = _extract_domain(result.get("link", ""))
        if not domain or domain in seen_domains:
            continue  # dedupe by source domain
        text = (result.get("snippet") or "").strip()
        if len(text) < _MIN_QUOTE_CHARS:
            continue  # too short to be a meaningful display quote
        quote: Dict[str, Any] = {"retailer": domain, "text": text}
        rating = _snippet_real_rating(result)
        if rating is not None:
            quote["rating"] = rating  # REAL rating only — never fabricated
        quotes.append(quote)
        seen_domains.add(domain)

    return quotes


# ============================================
# Phase 5.1 (Faithful-Results Task #6) — review paraphrase
# ============================================
# Per Ahmed's D4 directive: reviews become a SYNTHESIZED praise line —
# NON-verbatim, NO citations, NO source domains, NO [N]/[snippet_N] markers.
# Built from the REAL review sentiment the pipeline already has (zero extra API
# calls). Ratings stay real-only elsewhere (this never fabricates a rating).

# Strips a leading "Per <domain>: " attribution prefix the review model emits on
# each highlight point (e.g. "Per fragrantica.com: ...").
_PER_DOMAIN_PREFIX_RE = re.compile(r"^\s*per\s+[^\s:]+\.[a-z]{2,}[^:]*:\s*", re.I)
# Any leftover domain token (foo.com / foo.bh / foo.co.uk) anywhere in the text.
# Anchored to real TLDs (incl. GCC ccTLDs) so it strips bare retailer domains
# (fragrantica.com, bn.boots.com) WITHOUT eating dot-joined product strings like
# "S24.Ultra" or "12.Pro" (which would shrink a clause below the min-length and
# drop real praise) — SF-3, code review 2026-06-18.
_BARE_DOMAIN_RE = re.compile(
    r"\b[a-z0-9][a-z0-9-]*\.(?:com|net|org|io|co|app|ai|bh|sa|ae|kw|qa|om|uk)(?:\.[a-z]{2})?\b",
    re.I,
)


def _strip_attribution(text: str) -> str:
    """Remove a "Per <domain>:" prefix, any [N]/[snippet_N] markers, and any
    leftover bare domain tokens from a review clause. Returns a clean,
    citation-free, domain-free fragment."""
    if not isinstance(text, str):
        return ""
    t = _PER_DOMAIN_PREFIX_RE.sub("", text)
    t = _CITATION_MARKER_RE.sub("", t)          # [snippet_N] / [N]
    t = re.sub(r"\[\d+\]", "", t)               # any residual bare [N]
    t = _BARE_DOMAIN_RE.sub("", t)              # leftover domains
    t = re.sub(r"\s{2,}", " ", t).strip()
    # Drop dangling leading punctuation left by a stripped domain/marker.
    t = re.sub(r"^[\s,;:.\-–—]+", "", t)
    return t.strip()


def _lower_first(s: str) -> str:
    """Lowercase the first character for mid-sentence weaving, but PRESERVE a
    leading proper noun / brand / acronym (so "Creed Aventus" / "GPS-grade" are
    not mangled to "creed" / "gPS"). Skip lowercasing when:
      - the leading token is an all-caps acronym (s[0:2].isupper(), e.g. "GPS"), OR
      - the lead is a multi-word Title-Case proper noun — first token Title-Case
        AND the next word also capitalized (e.g. "Creed Aventus …", "Tom Ford …").
    A plain capitalized common word ("Amazing scent") still lowercases."""
    if not s:
        return s
    if s[0:2].isupper():  # leading all-caps acronym (GPS, EDP, …)
        return s
    tokens = s.split()
    if len(tokens) >= 2 and tokens[0][:1].isupper():
        # Strip leading punctuation from the second token before the cap check so
        # "Tom (the …)"-style leads aren't misread; require a real capital letter.
        nxt = tokens[1].lstrip("\"'([{")
        if nxt[:1].isupper():
            return s  # multi-word proper noun / brand — keep as-is
    return s[0].lower() + s[1:]


# Participial / relative leads ("known for …", "described as …", a gerund) read
# correctly only after a copula → "Owners say it IS {clause}".
_PRAISE_PARTICIPIAL_LEAD_RE = re.compile(
    r"^\s*(?:known\s+for|described\s+as|praised\s+for|noted\s+for|loved\s+for|"
    r"said\s+to\b|reported\s+to\b|renowned\s+for|celebrated\s+for|\w+ing\b)",
    re.I,
)
# Plain verb leads ("has …", "lasts …", "wears …") read correctly straight after
# the pronoun → "Owners say it {clause}".
_PRAISE_VERB_LEAD_RE = re.compile(
    r"^\s*(?:has|have|had|is|are|was|lasts?|last|projects?|wears?|smells?|opens?|"
    r"sits?|settles?|develops?|performs?|holds?|stays?|fills?|gives?|delivers?|"
    r"feels?|comes?|leans?|reads?)\b",
    re.I,
)


def _frame_praise_clause(woven: str) -> str:
    """Pick a glue that parses for the woven positive clause(s).

    - participial/relative/gerund lead ("known for …", "described as …", "-ing")
      → "Owners say it is {clause}"
    - plain verb lead ("has …", "lasts …", "wears …")
      → "Owners say it {clause}"
    - noun-phrase lead ("rich sillage …") → "Owners consistently highlight {clause}"

    Never glues "highlight" directly onto a verb/relative lead (D1)."""
    if _PRAISE_PARTICIPIAL_LEAD_RE.match(woven):
        return f"Owners say it is {woven}."
    if _PRAISE_VERB_LEAD_RE.match(woven):
        return f"Owners say it {woven}."
    return f"Owners consistently highlight {woven}."


# --- #6 send-back: copy-policy scrub (single source of truth) ---------------
# review_praise is built from REAL snippets, which carry banned EVALUATIVE vocab
# ("best camera", "excellent battery", "beats every rival"). Contract 2 (Ahmed's
# D4) requires the praise to pass the COPY FENCE. We scrub against the SAME
# .copy-policy.json the FE fence uses (ONE source of truth — no invented list)
# AND reframe toward neutral aspect-aggregation (name WHAT owners praise, not the
# superlative). Loaded once, cached; fail-open to a small builtin if the file is
# absent (the worktree always has it, but never crash praise on a missing file).
_COPY_POLICY_REL = ("SmartCompareApp", "src", "i18n", ".copy-policy.json")
_BANNED_VOCAB_PATTERNS: Optional[List["re.Pattern"]] = None


def _load_banned_vocab_patterns() -> List["re.Pattern"]:
    """Compiled banned/scary patterns from .copy-policy.json (cached)."""
    global _BANNED_VOCAB_PATTERNS
    if _BANNED_VOCAB_PATTERNS is not None:
        return _BANNED_VOCAB_PATTERNS
    pats: List[str] = []
    try:
        import json as _json
        # app/services/review_service.py -> repo root is two parents up.
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        path = os.path.join(root, *_COPY_POLICY_REL)
        with open(path, encoding="utf-8") as f:
            cp = _json.load(f)
        pats = [b["pattern"] for b in cp.get("banned_en", []) if isinstance(b, dict) and b.get("pattern")]
        pats += [re.escape(w) for w in cp.get("scary_vocab_en", []) if isinstance(w, str)]
    except Exception as e:  # noqa: BLE001 — never crash praise on a policy-file read
        logger.debug(f"copy-policy load failed, using builtin banned set: {e}")
        pats = [
            r"\bBest Pick\b", r"\bBest Choice\b", r"\bSmart Pick\b", r"\bWinner\b",
            r"\bExcellent\b", r"\bBeats\b", r"\bBest for\b", r"\bWe recommend\b",
        ]
    # Also scrub the bare superlative "best <noun>" form snippets love (the policy
    # lists "Best Pick"/"Best Choice"/"Best for" but a raw "best camera" still
    # reads as an absolute endorsement → strip the leading "best ").
    compiled = [re.compile(p, re.IGNORECASE) for p in pats]
    compiled.append(re.compile(r"\bbest\b", re.IGNORECASE))
    _BANNED_VOCAB_PATTERNS = compiled
    return compiled


def _scrub_banned_vocab(text: str) -> str:
    """Remove banned/scary evaluative vocab (the .copy-policy.json fence) from a
    clause, leaving the neutral aspect behind ("best camera" -> "camera",
    "excellent battery" -> "battery"). Collapses the whitespace/punctuation the
    removal leaves so the result reads cleanly."""
    if not text:
        return ""
    out = text
    for rx in _load_banned_vocab_patterns():
        out = rx.sub("", out)
    out = re.sub(r"\s{2,}", " ", out)
    out = re.sub(r"\s+([,.;:])", r"\1", out)        # space before punctuation
    out = re.sub(r"^[\s,;:.\-–—]+", "", out)         # leading punctuation
    out = re.sub(r"[\s,;:\-–—]+$", "", out)          # trailing junk
    return out.strip()


def _has_banned_vocab(text: str) -> bool:
    """True iff any banned/scary pattern still matches (post-scrub safety check)."""
    return any(rx.search(text) for rx in _load_banned_vocab_patterns())


def build_review_praise(reviews: Optional[Dict[str, Any]]) -> Optional[str]:
    """A SYNTHESIZED 1–2 sentence praise line from real review sentiment, or None.

    Sources (in order of preference), all de-attributed (no domains, no [N]) AND
    copy-policy-scrubbed (neutral aspect-aggregation — name WHAT owners praise,
    NOT the snippet's superlatives; #6 send-back):
      1. POSITIVE highlights' clauses → woven into a synthesizing lead so the
         output is non-verbatim (never a raw highlight copy).
      2. A consensus summary, but ONLY when overall_sentiment is NOT negative —
         we never present a negative consensus as "praise".

    Returns None when there is no CLEAN positive signal (insufficient/negative
    reviews, or every clause collapses to nothing after the banned-vocab scrub)
    — we never fabricate praise and never ship banned vocab.
    """
    if not isinstance(reviews, dict):
        return None
    summary = reviews.get("review_summary")
    if not isinstance(summary, dict):
        return None

    sentiment = (summary.get("overall_sentiment") or "").lower()
    highlights = summary.get("highlights") if isinstance(summary.get("highlights"), list) else []

    def _clean_clause(raw: str) -> Optional[Tuple[str, bool]]:
        """De-attribute + scrub banned vocab. Returns (clause, was_scrubbed) or
        None when nothing usable survives.

        Readability rule (neutral aspect-aggregation): removing a banned word from
        the INTERIOR of a clause usually breaks its grammar ("it beats every
        rival" -> "it every rival"; "an excellent warm scent" -> "an warm scent").
        So a scrubbed clause is KEPT only when the removal was a clean LEADING
        adjective strip that still parses as an aspect phrase (e.g. "best camera"
        -> "camera"); any interior removal -> DROP (prefer a cleaner clause /
        the consensus / None). Clean-as-is clauses are preferred by the caller."""
        de = _strip_attribution(raw).rstrip(" .")
        c = _scrub_banned_vocab(de)
        if len(c) < 8 or _has_banned_vocab(c):
            return None
        was_scrubbed = c != de
        if was_scrubbed:
            # Keep ONLY if the cleaned clause is a SUFFIX of the original (the
            # removed text was a leading run — "best camera ..." -> "camera ...").
            # An interior removal makes c NOT a suffix of de -> drop as broken.
            if not de.lower().rstrip(" .").endswith(c.lower().rstrip(" .")):
                return None
        return c, was_scrubbed

    # 1) Collect POSITIVE clauses, PREFERRING clean-as-is ones over scrubbed ones
    #    (neutral aspect-aggregation reads better than a scrubbed fragment).
    clean_clauses: List[str] = []
    scrubbed_clauses: List[str] = []
    seen = set()
    for h in highlights:
        if not isinstance(h, dict):
            continue
        if (h.get("sentiment") or "").lower() != "positive":
            continue
        res = _clean_clause(str(h.get("point") or ""))
        if not res:
            continue
        clause, was_scrubbed = res
        key = clause.lower()
        if key in seen:
            continue
        seen.add(key)
        (scrubbed_clauses if was_scrubbed else clean_clauses).append(clause)

    # Clean clauses first, then scrubbed ones as fill, capped at 2.
    positive_clauses = (clean_clauses + scrubbed_clauses)[:2]

    if positive_clauses:
        # Weave into a synthesizing lead so the line is NON-verbatim and clearly
        # an aggregate, not a copied quote. The glue is chosen by the FIRST
        # clause's grammatical shape so a verb/relative lead reads correctly
        # ("Owners say it lasts all day" — never "…highlight lasts all day"; D1).
        woven = " and ".join(_lower_first(c) for c in positive_clauses)
        praise = _frame_praise_clause(woven)
        praise = re.sub(r"\s{2,}", " ", praise).replace(" .", ".").strip()
        # Final safety net — never return a line that still trips the fence.
        if _has_banned_vocab(praise):
            return None
        return praise

    # 2) Fall back to a de-attributed + scrubbed consensus, never a negative one.
    if sentiment and sentiment != "negative":
        de_consensus = _strip_attribution(str(summary.get("consensus") or "")).rstrip(" .")
        consensus = _scrub_banned_vocab(de_consensus)
        # Same readability rule as clauses: an INTERIOR removal ("an excellent
        # warm scent" -> "an warm scent") reads broken — keep the consensus only
        # when it is clean-as-is OR a clean leading strip (a suffix of the
        # original). Otherwise drop to None (never ship a broken line).
        scrubbed = consensus != de_consensus
        suffix_ok = de_consensus.lower().endswith(consensus.lower()) if consensus else False
        if scrubbed and not suffix_ok:
            return None
        if len(consensus) >= 12 and not _has_banned_vocab(consensus):
            return consensus

    return None


def format_review_search_results(results: Dict, retailer_ratings: List[Dict]) -> str:
    """Format search results for review extraction."""
    if not results:
        return "No search results available."

    formatted = []

    organic = results.get("organic", [])[:10]
    for i, r in enumerate(organic):
        title = r.get("title", "")
        snippet = r.get("snippet", "")
        link = r.get("link", "")
        domain = ""
        if link:
            try:
                domain = urlparse(link).netloc.replace("www.", "")
            except Exception:
                pass
        prefix = f"[{domain}] " if domain else ""
        formatted.append(f"{i+1}. {prefix}{title}\n   {snippet}")

    if retailer_ratings:
        formatted.append("\n--- Retailer Ratings (from shopping data) ---")
        for r in retailer_ratings:
            count_str = f" ({r['review_count']} reviews)" if r.get("review_count") else ""
            formatted.append(f"- {r['source']}: {r['rating']}/5{count_str}")

    return "\n".join(formatted)


async def get_reviews(
    brand: str,
    name: str,
    variant: Optional[str],
    search_query: str,
    nocache: bool = False,
    category: str = "other",
    retailer_ratings: Optional[List[Dict]] = None,
    search_results: Optional[Dict] = None,
    track_serper_cost_fn=None,
    track_gpt_cost_fn=None,
) -> Dict[str, Any]:
    """Get reviews with caching (L1: Redis, L2: DB)."""
    import asyncio
    cache_key = get_reviews_cache_key(brand, name, variant)

    cached = get_cached(cache_key) if not nocache else None
    if cached:
        logger.info(f"Reviews cache hit: {cache_key}")
        cached["_cached"] = True
        return cached

    # L2: Check DB before API call
    if not nocache:
        from app.services.product_data_service import get_cached_reviews
        db_reviews = await get_cached_reviews(cache_key)
        if db_reviews:
            set_cached(cache_key, db_reviews, REVIEWS_CACHE_TTL)
            db_reviews["_cached"] = True
            db_reviews["_cache_source"] = "db"
            return db_reviews

    review_terms = CATEGORY_REVIEW_TERMS.get(category, "user reviews pros cons rating")
    logger.info(f"Fetching reviews for: {brand} {name} (category: {category})")
    if search_results is None:
        search_results = await search_web(f"{search_query} {review_terms}")
        if track_serper_cost_fn:
            track_serper_cost_fn()

    search_context = format_review_search_results(
        search_results, retailer_ratings or []
    )

    reviews, usage = await extract_reviews(brand, name, variant, search_context, category=category)
    if track_gpt_cost_fn:
        track_gpt_cost_fn(usage)

    if retailer_ratings:
        reviews["source_ratings"] = retailer_ratings

    # F3 (G2): persist the COMPLETED extraction BEFORE the optional consult.
    # The consult can run inside the outer 10s reviews-race wait_for; if that
    # cap fires DURING the consult, this coroutine is cancelled — so the cache
    # write MUST happen first, otherwise the finished extract_reviews result is
    # lost (PYTHON-FASTAPI-J pattern). After this point the extraction is safe
    # regardless of what the consult does.
    extraction_persisted = False
    if reviews and not reviews.get("error"):
        set_cached(cache_key, reviews, REVIEWS_CACHE_TTL)
        from app.services.product_data_service import save_reviews
        asyncio.create_task(save_reviews(cache_key, brand, name, variant, reviews))
        extraction_persisted = True

    # S2 I2.5 — optional review-content consultation from usage="review" GCC
    # sources. Flag-gated (ENABLE_REVIEW_SOURCE_CONSULT, default OFF → no-op),
    # never critical-path: any miss/timeout yields [] and the already-persisted
    # reviews ship as-is. consult_review_sources is itself wait_for-capped
    # (active mode) / synchronous (passive mode).
    try:
        consult = await consult_review_sources(
            brand, name, variant, category, search_results,
            track_serper_cost_fn=track_serper_cost_fn,
        )
        if consult and isinstance(reviews, dict):
            reviews["review_source_quotes"] = consult
            # Re-cache the enriched copy so a subsequent cache hit carries the
            # quotes too (the pre-consult write already protected the baseline).
            if extraction_persisted:
                set_cached(cache_key, reviews, REVIEWS_CACHE_TTL)
    except Exception as e:  # noqa: BLE001 — defensive; consult is best-effort
        logger.warning("[I2.5] consult_review_sources wiring error: %s", e)

    # S3 L2 — YouTube cited review signal. Flag-gated (default OFF → instant
    # None), wait_for-capped inside consult_youtube_source so it can NEVER
    # extend p95. Runs AFTER the extraction is persisted (same F3/G2 ordering
    # as the I2.5 consult) so a cap-cancel mid-consult can't lose finished
    # reviews. Any error is swallowed — YouTube is never critical-path.
    try:
        yt_signal = await consult_youtube_source(brand, name, variant, category)
        if yt_signal and isinstance(reviews, dict):
            reviews["youtube_review_signal"] = yt_signal
            if extraction_persisted:
                set_cached(cache_key, reviews, REVIEWS_CACHE_TTL)
    except Exception as e:  # noqa: BLE001 — defensive; YouTube is best-effort
        logger.warning("[L2] youtube consult wiring error: %s", e)

    reviews["_cached"] = False
    return reviews


# ---------- L2.11: per-retailer review-quote fetcher (Y from design) ----------

# Retailer-specific Serper site-filters. Order is the design priority:
# Amazon (deepest review depth) -> Noon (GCC native) -> X (social/word of mouth).
RETAILER_QUOTE_SITES = [
    ("Amazon", "amazon.com OR amazon.ae"),
    ("Noon", "noon.com"),
    ("X", "x.com OR twitter.com"),
]

# Cache per product 14d — review quote is stable.
_RETAILER_QUOTES_CACHE_TTL = 14 * 24 * 60 * 60


def _quote_cache_key(brand: str, name: str, variant: str | None) -> str:
    parts = [brand or "", name or "", variant or ""]
    return "retailer_quotes:" + "|".join(p.strip().lower() for p in parts)


async def fetch_retailer_quotes(
    brand: str,
    name: str,
    variant: str | None,
    track_serper_cost_fn=None,
) -> list:
    """L2.11 — fetch up to 3 per-retailer review snippets in parallel.

    Returns a list of ``{retailer, rating, text}`` entries (max 3). Each entry
    comes from a single Serper site-filtered organic search. Quote text is the
    first organic snippet of length > 20 chars; rating is extracted from the
    Serper richSnippet when present, otherwise None.

    Caches per product 14 days. ~$0.003 net cost per cache miss (3x Serper).
    """
    cache_key = _quote_cache_key(brand, name, variant)
    cached = get_cached(cache_key)
    if cached and isinstance(cached, dict) and isinstance(cached.get("quotes"), list):
        return cached["quotes"]

    product_query = f"{brand} {name} {variant or ''} review".strip()

    async def _one(retailer: str, site_filter: str):
        # B0-C-2: gate every Serper site-search behind has_budget("serper") so
        # the 2200-credit lifetime quota cannot be drained by retailer-quote
        # traffic (3 calls per product, 6 per compare). fail-open on Redis down
        # is inherited from has_budget(); record_usage on success keeps the
        # counter accurate for subsequent guards.
        if not has_budget("serper"):
            logger.info("[L2.11] retailer quote skipped — serper budget exhausted: %s", retailer)
            return None
        try:
            q = f'{product_query} site:{site_filter}'.strip()
            result = await search_web(q, num_results=5)
            # L5.1 (S3): NO manual record_usage("serper") here — search_web
            # records the budget meter internally on success (serper_service.py:94),
            # so a manual call here would double-count. LATENT hygiene, not an
            # active drain: this fetcher has ZERO production callers (dormant,
            # ledger §5), so the double-meter never reached prod — the fix
            # prevents it from double-counting if any future caller wires it into
            # the hot path. Same bug class F4/G2 fixed in the (also-dormant)
            # fetch_review_source_snippets (9ee695c). NB rating_service.py:296 is a
            # CORRECT single-count: it meters a DIRECT httpx POST (not search_web),
            # so its manual record_usage is the only meter for that call site.
            # track_serper_cost_fn is the separate per-request cost tracker (not
            # the budget meter) so it stays.
            if track_serper_cost_fn:
                track_serper_cost_fn()
        except Exception as e:
            logger.warning("[L2.11] retailer quote fetch failed for %s: %s", retailer, e)
            return None
        organic = (result or {}).get("organic", []) or []
        for item in organic:
            snippet = (item.get("snippet") or "").strip()
            if len(snippet) < 20:
                continue
            rating = None
            rich = item.get("richSnippet") or {}
            top = rich.get("top") if isinstance(rich, dict) else None
            if isinstance(top, dict):
                detected = top.get("detected_extensions") or {}
                rating_val = detected.get("rating") or detected.get("starRating")
                if isinstance(rating_val, (int, float)):
                    rating = float(rating_val)
            return {"retailer": retailer, "rating": rating, "text": snippet}
        return None

    tasks = [_one(r, s) for r, s in RETAILER_QUOTE_SITES]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    quotes = []
    for r in results:
        if isinstance(r, Exception) or r is None:
            continue
        quotes.append(r)
        if len(quotes) >= 3:
            break

    if quotes:
        set_cached(cache_key, {"quotes": quotes}, _RETAILER_QUOTES_CACHE_TTL)
    return quotes


# ---------- S2 I2.5: review-content consultation from usage="review" sources ----------

# Cache per product 14d — editorial review content is stable.
_REVIEW_SOURCE_CACHE_TTL = 14 * 24 * 60 * 60


def _review_source_cache_key(brand: str, name: str, variant: str | None, category: str) -> str:
    parts = [brand or "", name or "", variant or "", category or ""]
    return "review_source_snippets:" + "|".join(p.strip().lower() for p in parts)


async def fetch_review_source_snippets(
    brand: str,
    name: str,
    variant: str | None,
    category: str,
    track_serper_cost_fn=None,
) -> list:
    """S2 I2.5 — consult registry sources flagged usage in ("review","both")
    for editorial review snippets (e.g. the Arabic GCC sources sayidaty.net /
    khaleejtimes.com / gulfnews.com for beauty/fashion).

    ONE Serper `site:`-filtered organic search across the category's review
    sources. Budget-gated (`has_budget("serper")`), cached per product 14d.
    Returns a list of ``{domain, text}`` (max 3) or ``[]`` on miss / no review
    sources / budget-exhausted / timeout — NEVER raises, NEVER critical-path.
    The caller wraps this in asyncio.wait_for so a slow Serper call cannot drag
    the reviews race past its budget.
    """
    from app.services.source_router import get_sources_for_category

    review_sources = get_sources_for_category(category, usage="review")
    if not review_sources:
        return []  # category has no review-content sources — no-op

    cache_key = _review_source_cache_key(brand, name, variant, category)
    cached = get_cached(cache_key)
    if cached and isinstance(cached, dict) and isinstance(cached.get("snippets"), list):
        return cached["snippets"]

    if not has_budget("serper"):
        logger.info("[I2.5] review-source consult skipped — serper budget exhausted")
        return []

    domains = [s.domain for s in review_sources][:5]
    site_filter = " OR ".join(f"site:{d}" for d in domains)
    product_query = f"{brand} {name} {variant or ''} review".strip()
    query = f"{product_query} {site_filter}".strip()

    try:
        # F4 (G2): NO manual record_usage("serper") here — search_web already
        # records the budget meter internally (serper_service.py:94), and only
        # on success. A manual call here double-counted the credit AND counted
        # failed calls. track_serper_cost_fn is the separate per-request cost
        # tracker (not the budget meter) so it stays.
        result = await search_web(query, num_results=6)
        if track_serper_cost_fn:
            track_serper_cost_fn()
    except Exception as e:  # noqa: BLE001
        logger.warning("[I2.5] review-source consult fetch failed: %s", e)
        return []

    organic = (result or {}).get("organic", []) or []
    snippets = []
    for item in organic:
        snippet = (item.get("snippet") or "").strip()
        if len(snippet) < 20:
            continue
        link = item.get("link", "") or ""
        link_domain = urlparse(link).netloc.replace("www.", "").lower()
        snippets.append({"domain": link_domain, "text": snippet})
        if len(snippets) >= 3:
            break

    if snippets:
        set_cached(cache_key, {"snippets": snippets}, _REVIEW_SOURCE_CACHE_TTL)
    return snippets


def review_source_consult_mode() -> Optional[str]:
    """Read ENABLE_REVIEW_SOURCE_CONSULT fresh each call (default OFF).

    Returns "active" | "passive" | None.
    - "active" (EXPLICIT only) → fires the dedicated budget-gated Serper
      site-search. This is the ONLY value that spends a Serper credit, so it is
      deliberately NOT reachable via a generic truthy flip.
    - "passive" OR any other truthy value ("true"/"1"/"on") → reuses the
      already-fetched unified search organic (zero extra Serper). F3 (G2):
      truthy defaults to the SAFE passive mode so a careless `=true` flip can't
      silently start burning Serper credits.
    - unset / "false" / anything else → None (feature OFF).
    Read fresh (not process-cached) so I4 can A/B both modes at G5.
    """
    raw = os.environ.get("ENABLE_REVIEW_SOURCE_CONSULT", "").strip().lower()
    if raw == "active":
        return "active"
    if raw in ("passive", "true", "1", "on"):
        return "passive"
    return None


def passive_review_snippets(
    search_results: Optional[Dict], category: str
) -> list:
    """PASSIVE mode (zero extra Serper): scan the already-fetched unified
    search organic for hits on the category's usage="review" registry domains.
    Returns up to 3 {domain, text} entries, [] on miss."""
    from app.services.source_router import get_sources_for_category

    review_sources = get_sources_for_category(category, usage="review")
    if not review_sources or not search_results:
        return []
    review_domains = {s.domain.lower() for s in review_sources}
    organic = (search_results or {}).get("organic", []) or []
    snippets = []
    for item in organic:
        link = item.get("link", "") or ""
        link_domain = urlparse(link).netloc.replace("www.", "").lower()
        # match registry domain (incl. subdomains)
        matched = any(
            link_domain == d or link_domain.endswith("." + d) for d in review_domains
        )
        if not matched:
            continue
        snippet = (item.get("snippet") or "").strip()
        if len(snippet) < 20:
            continue
        snippets.append({"domain": link_domain, "text": snippet})
        if len(snippets) >= 3:
            break
    return snippets


async def consult_review_sources(
    brand: str,
    name: str,
    variant: str | None,
    category: str,
    search_results: Optional[Dict],
    track_serper_cost_fn=None,
    timeout: float = 4.0,
) -> list:
    """S2 I2.5 mode dispatcher. OFF (default) -> []; passive -> scan existing
    organic (sync, instant); active -> dedicated budget-gated Serper call
    (wait_for-capped). NEVER raises, NEVER critical-path — any error/timeout
    yields []."""
    mode = review_source_consult_mode()
    if mode is None:
        return []
    try:
        if mode == "passive":
            return passive_review_snippets(search_results, category)
        # active
        return await asyncio.wait_for(
            fetch_review_source_snippets(
                brand, name, variant, category,
                track_serper_cost_fn=track_serper_cost_fn,
            ),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        logger.info("[I2.5] review-source consult timed out (mode=%s)", mode)
        return []
    except Exception as e:  # noqa: BLE001
        logger.warning("[I2.5] review-source consult error (mode=%s): %s", mode, e)
        return []


# ---------- S3 L2: YouTube cited review-signal consult ----------

# Inner wait_for cap for the YouTube consult. Sized WELL under the reviews-race
# budget (_PHASE1_TIMEOUTS["reviews"]=10s) so a slow YouTube call drops out long
# before it can pressure p95. This is the p95 guard: YouTube can NEVER extend
# the reviews race — a call slower than this is abandoned as None.
_YOUTUBE_CONSULT_TIMEOUT = 4.0


def youtube_source_enabled() -> bool:
    """Read ENABLE_YOUTUBE_SOURCE fresh each call (default OFF).

    Default OFF in code; flipped in Railway ONLY when QA is green (the lane
    discipline). Read fresh (not process-cached) so a Railway flip / QA A/B
    takes effect without a restart. Accepts the standard truthy set; anything
    else (unset / "false" / "0" / "off" / junk) is OFF.
    """
    return os.environ.get("ENABLE_YOUTUBE_SOURCE", "").strip().lower() in (
        "true", "1", "on", "yes",
    )


async def consult_youtube_source(
    brand: str,
    name: str,
    variant: str | None,
    category: str,
    timeout: float = _YOUTUBE_CONSULT_TIMEOUT,
) -> Optional[Dict[str, Any]]:
    """S3 L2 — fetch a cited YouTube review signal, wait_for-capped.

    OFF (default) → instant None (the API client is never called → zero quota).
    ON → fetch_youtube_review_signal wrapped in asyncio.wait_for(timeout) so a
    slow call is abandoned as None. NEVER raises, NEVER critical-path — any
    timeout / error / miss yields None and the persisted reviews ship unchanged.
    This is the contract that keeps YouTube off the p95 path.
    """
    if not youtube_source_enabled():
        return None
    try:
        return await asyncio.wait_for(
            fetch_youtube_review_signal(brand, name, variant, category),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        logger.info("[L2] youtube consult timed out (>%ss) — dropping signal", timeout)
        return None
    except Exception as e:  # noqa: BLE001 — best-effort; never breaks reviews
        logger.warning("[L2] youtube consult error: %s", e)
        return None
