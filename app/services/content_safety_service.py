"""Content moderation pipeline.

Four layers, all returning a uniform `SafetyResult`:

- L1 — query pre-filter (keyword/regex on raw user query, $0)
- L2 — shopping-result filter (drops unsafe items before GPT extraction, $0)
- L3 — output moderation (OpenAI omni-moderation-latest on assembled response, $0)
- L4 — vision moderation (same API as L3, wrapped over vision identification output, $0)

Spec ref: docs/superpowers/specs/2026-05-17-bundle-b-two-input-ux-design.md § 5.2.
"""
import json
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_BLOCKLIST_PATH = Path(__file__).resolve().parent.parent / "data" / "content_blocklist.json"

# QA-requested seeded sentinel for end-to-end content-safety verification
# (spec sec 4.11 Q1). Hardcoded — deliberately NOT in content_blocklist.json
# (that file is committed to prod and should not contain test strings).
# Gated by an opt-in env var: production absence keeps prod fail-open semantics
# untouched. When ENABLE_CONTENT_SAFETY_TEST_SEEDS=true (staging / QA only),
# any L1 query or L3 output text containing this exact substring is treated
# as blocked, letting QA reproduce a CONTENT_UNAVAILABLE response without
# writing real offensive content into the audit log.
_TEST_SENTINEL = "CONTENT_SAFETY_TEST_BLOCK_ME_42"
_SENTINEL_REASON = "test_seed"


def _test_seeds_enabled() -> bool:
    """Cheap per-call env check — only fires the sentinel branch when set."""
    return os.environ.get("ENABLE_CONTENT_SAFETY_TEST_SEEDS", "false").lower() == "true"


def blocklist_precision_v2_enabled() -> bool:
    """W4-8 Half B (default OFF): select the ``v2`` blocklist lists. Read per
    call via ``os.getenv`` -- never cached at import or construction."""
    return os.getenv("ENABLE_BLOCKLIST_PRECISION_V2", "false").strip().lower() in (
        "true", "1", "yes", "on",
    )


def _boundary_alternation(escaped_terms: list[str]) -> re.Pattern:
    return re.compile(
        r"(?:^|[\s\W])(" + "|".join(escaped_terms) + r")(?=$|[\s\W])",
        flags=re.IGNORECASE | re.UNICODE,
    )


class _ExemptingPattern:
    """W4-8 Half B (ruling R11), the v2 matcher of one category: a token listed
    in ``v2.exempt`` does not block a text that also contains one of ITS OWN
    qualifiers (whole token, same boundary / escape / lowercase as the matcher);
    every other token of the category still blocks, in v1 list order."""

    def __init__(self, full: re.Pattern, terms: list[str],
                 qualifiers: dict[str, re.Pattern]) -> None:
        self._full = full
        self._terms = terms
        self._qualifiers = qualifiers
        self._reduced: dict[frozenset, Optional[re.Pattern]] = {}
        # Multi-word tokens: the only ones that can span a field boundary.
        self._spanning = [_boundary_alternation([t]) for t in terms
                          if re.search(r"\s", re.sub(r"\\(.)", r"\1", t, flags=re.DOTALL))]

    def search_fields(self, fields: list[str]):
        """Ruling R16c (the L2 title + snippet surface): a qualifier exempts a
        token only when both occur in the SAME field. The tokens are still found
        over the joined surface (v1 identity): one inside a field is exempted
        only by a qualifier in that field, and one that spans a field boundary
        is in no single field, so no qualifier exempts it."""
        joined = " ".join(fields)
        if not any(q.search(f) for f in fields for q in self._qualifiers.values()):
            return self._full.search(joined)
        for field in fields:
            m = self.search(field)
            if m:
                return m
        junction = -1
        for field in fields[:-1]:
            junction += len(field) + 1
            for pattern in self._spanning:
                m = pattern.search(joined)
                while m is not None and m.start(1) < junction:
                    if m.end(1) > junction:
                        return m
                    m = pattern.search(joined, m.start(1) + 1)
        return None

    def search(self, haystack: str):
        exempted = frozenset(t for t, q in self._qualifiers.items() if q.search(haystack))
        if not exempted:
            return self._full.search(haystack)
        if exempted not in self._reduced:
            kept = [t for t in self._terms if t not in exempted]
            self._reduced[exempted] = _boundary_alternation(kept) if kept else None
        pattern = self._reduced[exempted]
        return pattern.search(haystack) if pattern is not None else None


@dataclass(frozen=True)
class SafetyResult:
    allowed: bool
    reason: Optional[str] = None
    blocklist_match: Optional[str] = None


class ContentSafetyService:
    def __init__(self) -> None:
        self._categories: dict[str, dict[str, list[str]]] = {}
        self._compiled: dict[str, re.Pattern] = {}
        self._compiled_v2: dict[str, re.Pattern] = {}
        self._load_blocklist()

    def _patterns(self) -> dict[str, re.Pattern]:
        return self._compiled_v2 if blocklist_precision_v2_enabled() else self._compiled

    def _load_blocklist(self) -> None:
        """Load + compile blocklist ONCE at construction time.

        Raises if the file is missing or malformed — the app MUST NOT start
        without a valid blocklist (security-critical, per spec § 1.1).
        """
        with _BLOCKLIST_PATH.open("r", encoding="utf-8") as fh:
            doc = json.load(fh)
        self._categories = doc.get("categories", {})
        for cat, lists in self._categories.items():
            terms = [re.escape(t.lower()) for t in lists.get("en", []) + lists.get("ar", [])]
            if terms:
                # Boundary lookaround works for both Latin (whitespace/punct) and
                # Arabic (no word-boundary semantics in regex). Anchors on start,
                # end, whitespace, or non-word chars.
                self._compiled[cat] = re.compile(
                    r"(?:^|[\s\W])(" + "|".join(terms) + r")(?=$|[\s\W])",
                    flags=re.IGNORECASE | re.UNICODE,
                )
        # W4-8 Half B: each "v2" list REPLACES its (category, lang) list; every
        # other list is the v1 list. Both compiled here, selected per call.
        # Ruling R11: the v2 lists equal v1; precision comes from v2.exempt.
        overrides = (doc.get("v2") or {}).get("categories", {})
        exempt = (doc.get("v2") or {}).get("exempt", {})
        for cat, lists in self._categories.items():
            merged = dict(lists)
            merged.update(overrides.get(cat, {}))
            terms = [re.escape(t.lower()) for t in merged.get("en", []) + merged.get("ar", [])]
            if terms:
                self._compiled_v2[cat] = re.compile(
                    r"(?:^|[\s\W])(" + "|".join(terms) + r")(?=$|[\s\W])",
                    flags=re.IGNORECASE | re.UNICODE,
                )
                qualifiers = {
                    re.escape(token.lower()): _boundary_alternation(
                        [re.escape(q.lower()) for q in quals])
                    for by_token in exempt.get(cat, {}).values()
                    for token, quals in by_token.items() if quals
                }
                if qualifiers:
                    self._compiled_v2[cat] = _ExemptingPattern(
                        self._compiled_v2[cat], terms, qualifiers)

    def check_query_intent(self, query: str) -> SafetyResult:
        """L1 — pre-flight blocklist check on raw user query."""
        if not query or not query.strip():
            return SafetyResult(allowed=True)
        # QA-only seeded sentinel (spec sec 4.11 Q1). Branch is dead in prod
        # (env var absent → _test_seeds_enabled returns False, no behavior
        # change). Match runs before the regex sweep so QA gets a deterministic
        # blocklist_match value back.
        if _test_seeds_enabled() and _TEST_SENTINEL in query:
            return SafetyResult(allowed=False, reason=_SENTINEL_REASON, blocklist_match=_TEST_SENTINEL)
        haystack = query.lower()
        for cat, pattern in self._patterns().items():
            m = pattern.search(haystack)
            if m:
                return SafetyResult(allowed=False, reason=cat, blocklist_match=m.group(1))
        return SafetyResult(allowed=True)

    def is_text_safe(self, text: str) -> bool:
        """L2 helper — boolean check for a single text blob (title + retailer,
        post-scrape product surface, etc). Used by Tier 1.5 ingestion points
        that don't have a Serper-shaped {title, snippet} item to filter.

        Returns True on empty/whitespace input — empty surface can't carry
        unsafe content, and an over-eager False here would silently drop
        legitimate price candidates with thin metadata.
        """
        if not text or not text.strip():
            return True
        haystack = text.lower()
        for pattern in self._patterns().values():
            if pattern.search(haystack):
                return False
        return True

    def filter_shopping_items(self, items: list[dict]) -> list[dict]:
        """L2 — drop unsafe shopping items before they reach GPT extraction.

        Item-level filter; drops are noisy on normal traffic so they are NOT
        audit-logged (only L1/L3/L4 hit admin_audit_log). Aggregate drop
        count is emitted as INFO.
        """
        if not items:
            return []
        safe: list[dict] = []
        dropped = 0
        patterns = self._patterns()
        for item in items:
            haystack = f"{item.get('title', '')} {item.get('snippet', '')}".lower()
            blocked = False
            for pattern in patterns.values():
                if isinstance(pattern, _ExemptingPattern):
                    # v2 only (ruling R16c): the exemption is decided per field.
                    hit = pattern.search_fields([f"{item.get('title', '')}".lower(),
                                                 f"{item.get('snippet', '')}".lower()])
                else:
                    hit = pattern.search(haystack)
                if hit:
                    blocked = True
                    break
            if blocked:
                dropped += 1
            else:
                safe.append(item)
        if dropped:
            logger.info("[content_safety] L2 dropped %d/%d shopping items", dropped, len(items))
        return safe

    async def moderate_output(self, text: str) -> SafetyResult:
        """L3 — OpenAI omni-moderation-latest on assembled response text.

        Fails OPEN on API exception (timeout, OpenAI outage) — Build
        Principle #4 says never block valid traffic on moderation flakiness.
        """
        if not text or not text.strip():
            return SafetyResult(allowed=True)
        # QA-only seeded sentinel (spec sec 4.11 Q1). Same dead-branch
        # discipline as L1 above — fires only when env var is set, returns
        # a deterministic SafetyResult so QA can assert against `reason`.
        if _test_seeds_enabled() and _TEST_SENTINEL in text:
            return SafetyResult(allowed=False, reason=_SENTINEL_REASON, blocklist_match=_TEST_SENTINEL)
        try:
            # Inline import — keeps module importable without OPENAI_API_KEY at process boot.
            from app.services.model_config import moderation_model
            from app.services.openai_service import get_client
            client = get_client()
            resp = await client.moderations.create(model=moderation_model(), input=text)
            r = resp.results[0]
            if r.flagged:
                scores = r.category_scores.model_dump() if hasattr(r.category_scores, "model_dump") else dict(r.category_scores)
                top = next(
                    (k for k, v in scores.items() if v and v > 0.5),
                    "unspecified",
                )
                return SafetyResult(allowed=False, reason=top)
        except Exception as e:
            logger.warning("[content_safety] L3 moderation API failed (fail-open): %s", e)
        return SafetyResult(allowed=True)

    async def moderate_vision_output(self, extracted: dict) -> SafetyResult:
        """L4 — L3 wrapper over GPT-4o-mini vision identification output.

        `extracted` is the vision_result dict (products list + raw_response).
        Joins product brand+name+size into a single text surface for the
        moderation API to evaluate.
        """
        products = extracted.get("products", []) or []
        text = " ".join(
            f"{p.get('brand', '')} {p.get('name', '')} {p.get('size_or_count', '')}".strip()
            for p in products
        ).strip()
        return await self.moderate_output(text)


_service: Optional[ContentSafetyService] = None


def get_content_safety_service() -> ContentSafetyService:
    """Module-level singleton accessor — mirrors get_comparison_service shape."""
    global _service
    if _service is None:
        _service = ContentSafetyService()
    return _service
