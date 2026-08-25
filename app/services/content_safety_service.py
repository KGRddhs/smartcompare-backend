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


@dataclass(frozen=True)
class SafetyResult:
    allowed: bool
    reason: Optional[str] = None
    blocklist_match: Optional[str] = None


class ContentSafetyService:
    def __init__(self) -> None:
        self._categories: dict[str, dict[str, list[str]]] = {}
        self._compiled: dict[str, re.Pattern] = {}
        self._load_blocklist()

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
        for cat, pattern in self._compiled.items():
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
        for pattern in self._compiled.values():
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
        for item in items:
            haystack = f"{item.get('title', '')} {item.get('snippet', '')}".lower()
            blocked = False
            for pattern in self._compiled.values():
                if pattern.search(haystack):
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
