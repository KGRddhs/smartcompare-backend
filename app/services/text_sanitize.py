"""Strip internal scoring artifacts from user-facing verdict text (fail-closed).
Confirmed live leaks (fresh nocache 2026-06-21): "leads on the overall score by
4.0 points", "presentation score of 100", "10.7-point higher overall score",
"+18pt longevity". NOT applied to factual_verdict (deterministic + score-safe)."""
import re

_SCORE_PATTERNS = [
    re.compile(r"\b\d+(?:\.\d+)?\s*[-‐-― ]?points?\b", re.I),  # 4.0 points / 10-point / 10.7‑point
    re.compile(r"\bscore of \d+(?:\.\d+)?\b", re.I),
    re.compile(r"\b\d+(?:\.\d+)?\s*/\s*100\b"),
    re.compile(r"\boverall score\b", re.I),
    re.compile(r"\+\s*\d+(?:\.\d+)?\s*pts?\b", re.I),                    # +18pt / +5 pts
    # M18 PO-verdict-text-04 — fact-check INTERNALS that shipped in cons:
    # "Price deviation of 53.9% from expected." / "... from verified sources."
    # (fact_check_service deviation_pct diagnostics echoed by the model).
    re.compile(r"\bdeviation of \d+(?:\.\d+)?\s*%", re.I),
    # "Soleil Neige scores 73.8 overall" — bare scored-number phrasing the
    # 'score of N' pattern missed.
    re.compile(r"\bscores?\s+\d+(?:\.\d+)?\b", re.I),
]
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")


def dedup_brand_name(brand, name) -> str:
    """ONE shared user-facing display-name builder (M18 PO-verdict-text-05 /
    PO-recorded-13). `f"{brand} {name}"` concatenation doubled the brand
    ("TOM FORD TOM FORD OUD WOOD 100 ML") whenever the parser/vision `name`
    already starts with the brand.

    Rules: token-boundary, case-insensitive. When `name` already starts with
    the brand it is returned with ITS OWN casing preserved; any FURTHER leading
    repeats of the brand inside `name` are collapsed to one. "Applesauce" is
    never deduped against brand "Apple". Empty/None inputs degrade to the other
    half ("" when both are empty)."""
    b = (brand or "").strip()
    n = (name or "").strip()
    if not b:
        return n
    if not n:
        return b
    bl = b.lower()

    def _strip_leading_brand(s: str):
        """Remove ONE leading occurrence of the brand (token-boundary,
        case-insensitive); None when `s` does not start with it."""
        sl = s.lower()
        if sl == bl:
            return ""
        if sl.startswith(bl) and len(s) > len(b) and s[len(b)].isspace():
            return s[len(b):].lstrip()
        return None

    rest = _strip_leading_brand(n)
    if rest is None:
        return f"{b} {n}"           # name does not carry the brand — concat
    # Name already starts with the brand: collapse any further leading repeats,
    # keeping the name's own casing for the first occurrence.
    core = rest
    while True:
        nxt = _strip_leading_brand(core)
        if nxt is None:
            break
        core = nxt
    if core == rest:
        return n                    # single occurrence — name is already right
    head = n[:len(b)]               # the name's own casing of the brand
    return f"{head} {core}".strip()


def has_score_internals(text) -> bool:
    if not text or not isinstance(text, str):
        return False
    return any(p.search(text) for p in _SCORE_PATTERNS)


def strip_score_internals(text) -> str:
    """Drop any SENTENCE containing a score artifact. Returns survivors joined,
    or "" if every sentence leaked (caller supplies a qualitative fallback)."""
    if not text or not isinstance(text, str):
        return text or ""
    kept = [s for s in _SENT_SPLIT.split(text.strip()) if s and not has_score_internals(s)]
    return " ".join(kept).strip()


def scrub_review_summary(rs):
    """WS-5 follow-up (dispatcher gate-fix) — fail-closed backstop for a
    review_summary's free GPT text (`consensus` + `highlights[].point`).
    REVIEWS_EXTRACTION_SYSTEM has no score-forbid rule, and while the FE does not
    render review_summary today (Contract 2 → synthesized review_praise), the
    payload is PERSISTED and re-served (Home/History/Share) — so a leaked internal
    score would survive in the stored body. Strips any score-leaking sentence from
    `consensus`; strips `highlights[].point` and DROPS a highlight whose point
    fully leaks. Returns a cleaned shallow copy; a non-dict passes through."""
    if not isinstance(rs, dict):
        return rs
    out = dict(rs)
    consensus = out.get("consensus")
    if isinstance(consensus, str):
        out["consensus"] = strip_score_internals(consensus)
    highlights = out.get("highlights")
    if isinstance(highlights, list):
        cleaned = []
        for h in highlights:
            if isinstance(h, dict) and isinstance(h.get("point"), str):
                stripped = strip_score_internals(h["point"])
                if not stripped:
                    continue  # the whole point was a score artifact — drop it
                h = {**h, "point": stripped}
            cleaned.append(h)
        out["highlights"] = cleaned
    return out
