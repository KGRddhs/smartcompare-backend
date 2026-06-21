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
]
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")


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
