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
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_BLOCKLIST_PATH = Path(__file__).resolve().parent.parent / "data" / "content_blocklist.json"


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
        haystack = query.lower()
        for cat, pattern in self._compiled.items():
            m = pattern.search(haystack)
            if m:
                return SafetyResult(allowed=False, reason=cat, blocklist_match=m.group(1))
        return SafetyResult(allowed=True)

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
        try:
            # Inline import — keeps module importable without OPENAI_API_KEY at process boot.
            from app.services.openai_service import get_client
            client = get_client()
            resp = await client.moderations.create(model="omni-moderation-latest", input=text)
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
