"""Verdict self-critique service (Bundle B B.3 / S2 I3.1).

A single gpt-4o-mini pass that SCORES a shipped verdict on 5 quality axes
(0..10) so the orchestrator can decide whether to regenerate it ONCE:

  bias_score              — does the verdict favour one product WITHOUT
                            scoring evidence? (10 = balanced, 0 = biased)
  vagueness_score         — generic statements that don't reference the
                            specific products at hand (10 = specific)
  hedging_score           — "could be", "might want to", "depending on"
                            (10 = decisive, 0 = fence-sitting)
  missing_citation_score  — claims without source-count / number grounding
                            (10 = well-grounded)
  pain_workflow_align_score — does the verdict honour the cohort's top
                            pain-workflow constraints (10 = aligned)

Any axis < CRITIQUE_THRESHOLD (7) flags `needs_regen=True`; the CALLER
enforces the ONE-regeneration hard cap. This module only scores + flags —
it never re-prompts the verdict itself, and it NEVER blocks the response:
on any error (API failure, malformed JSON, missing axes) `critique_verdict`
returns None and the caller serves the original verdict unchanged.

Design: docs/plans/2026-06-10-bundle-b-intelligence-layer-design.md § 4
        (Lane I3) · migration 030 verdict_critiques.
Flag: ENABLE_SELF_CRITIQUE — default OFF in code (Railway flips at a gate).
Cost: ONE gpt-4o-mini call, ~$0.0002-0.001/verdict (≤$0.002 gate, I3.3).
"""
from __future__ import annotations

import dataclasses
import json
import logging
import os
from typing import Any, Dict, List, Optional

from app.services.database_service import get_admin_supabase_client
from app.services.openai_service import get_client

logger = logging.getLogger(__name__)

# The 5 critique axes — names mirror migration 030 verdict_critiques columns
# EXACTLY so persistence is a direct field map.
CRITIQUE_AXES: tuple[str, ...] = (
    "bias_score",
    "vagueness_score",
    "hedging_score",
    "missing_citation_score",
    "pain_workflow_align_score",
)

# Any axis strictly below this triggers exactly ONE regeneration (caller-
# enforced hard cap). 7/10 is acceptable; 6 is not.
CRITIQUE_THRESHOLD = 7

# gpt-4o-mini — the critique is a cheap scoring pass, never the verdict's
# own high-priority model. Pinned (NOT model_router) so the critic stays a
# fixed, bounded cost regardless of the daily 4o budget.
CRITIC_MODEL = "gpt-4o-mini"

_CRITIQUE_SYSTEM = """You are a strict quality auditor for product-comparison verdicts written for buyers in Bahrain / the GCC. Score the verdict below on 5 axes from 0 to 10 (10 = best). Be a harsh grader — a competent-but-generic verdict should score 6-7, not 9.

Return ONLY valid JSON with these exact integer keys (0..10):
{
    "bias_score": 0,
    "vagueness_score": 0,
    "hedging_score": 0,
    "missing_citation_score": 0,
    "pain_workflow_align_score": 0
}

Axis definitions:
- bias_score: 10 = the winner is justified by the scoring data; 0 = favours one product with no supporting evidence.
- vagueness_score: 10 = every claim names a specific spec / number / attribute of THESE products; 0 = generic filler that could describe anything.
- hedging_score: 10 = decisive, commits to a clear recommendation; 0 = fence-sitting ("it depends", "might", "could be").
- missing_citation_score: 10 = claims are grounded in numbers / source counts; 0 = unsupported assertions.
- pain_workflow_align_score: 10 = leads with the verdict and matches the buyer's stated decision priorities; 0 = ignores them.

Score ONLY the axes. Do NOT rewrite the verdict. Do NOT add commentary."""


def is_self_critique_enabled() -> bool:
    """Read ENABLE_SELF_CRITIQUE each call (default OFF). Cheap env read —
    the critique only runs post-verdict (not a hot inner loop), and reading
    live lets a Railway flip take effect without a redeploy-vs-cache race."""
    return os.environ.get("ENABLE_SELF_CRITIQUE", "false").lower() == "true"


@dataclasses.dataclass
class CritiqueResult:
    """Outcome of one critique pass. `axis_scores` maps each of CRITIQUE_AXES
    to a clamped 0..10 int. `needs_regen` is True iff any axis is below
    CRITIQUE_THRESHOLD. `usage` carries token counts for I3.3 cost tracking."""
    axis_scores: Dict[str, int]
    needs_regen: bool
    low_axes: List[str]
    regen_reason: Optional[str]
    critic_model: str
    usage: Dict[str, int]

    @property
    def tokens_used(self) -> int:
        return int(self.usage.get("prompt_tokens", 0)) + int(
            self.usage.get("completion_tokens", 0)
        )


def _clamp_axis(value: Any) -> Optional[int]:
    """Coerce a model-emitted axis value to an int in [0, 10]. Returns None
    when the value isn't numeric (a missing/garbage axis → un-scoreable)."""
    if isinstance(value, bool):  # bool is an int subclass — reject explicitly
        return None
    if not isinstance(value, (int, float)):
        return None
    return max(0, min(10, int(round(value))))


def _build_critique_user_message(
    comparison: Dict[str, Any],
    product_names: List[str],
    pain_workflow_context: Optional[str],
) -> str:
    """Compose the user message: the verdict prose fields the critic scores,
    plus the optional pain-workflow context for the alignment axis."""
    winner_idx = comparison.get("winner_index")
    verdict_fields = {
        "products": product_names,
        "winner_index": winner_idx,
        "winner_declaration": comparison.get("winner_declaration"),
        "winner_reason": comparison.get("winner_reason"),
        "key_tradeoff": comparison.get("key_tradeoff"),
        "value_context": comparison.get("value_context"),
        "best_for": comparison.get("best_for"),
        "product_0_pros": comparison.get("product_0_pros"),
        "product_0_cons": comparison.get("product_0_cons"),
        "product_1_pros": comparison.get("product_1_pros"),
        "product_1_cons": comparison.get("product_1_cons"),
    }
    parts = ["VERDICT TO SCORE:", json.dumps(verdict_fields, ensure_ascii=False, indent=2)]
    if pain_workflow_context:
        parts.append("")
        parts.append("BUYER DECISION PRIORITIES (for pain_workflow_align_score):")
        parts.append(pain_workflow_context)
    return "\n".join(parts)


async def critique_verdict(
    *,
    comparison: Dict[str, Any],
    product_names: List[str],
    pain_workflow_context: Optional[str] = None,
) -> Optional[CritiqueResult]:
    """Score a verdict on the 5 axes via one gpt-4o-mini pass.

    Returns a CritiqueResult, or None on ANY failure (API error, malformed
    or empty JSON, missing axes) — the caller serves the ORIGINAL verdict
    when None. NEVER raises. The flag check is the CALLER's responsibility
    (so it can skip building the message entirely when OFF), but this
    function is also safe to call unconditionally.
    """
    try:
        client = get_client()
        user_msg = _build_critique_user_message(
            comparison, product_names, pain_workflow_context
        )
        response = await client.chat.completions.create(
            model=CRITIC_MODEL,
            messages=[
                {"role": "system", "content": _CRITIQUE_SYSTEM},
                {"role": "user", "content": user_msg},
            ],
            max_tokens=150,
            temperature=0.0,  # deterministic grading
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        if not content:
            logger.info("[SELF_CRITIQUE] empty response content — serving original")
            return None

        parsed = json.loads(content)

        axis_scores: Dict[str, int] = {}
        for axis in CRITIQUE_AXES:
            clamped = _clamp_axis(parsed.get(axis))
            if clamped is None:
                # A missing/garbage axis means we can't faithfully score —
                # serve the original rather than ship a partial critique.
                logger.info(
                    "[SELF_CRITIQUE] axis %s missing/invalid in critique JSON — "
                    "serving original",
                    axis,
                )
                return None
            axis_scores[axis] = clamped

        low_axes = [a for a in CRITIQUE_AXES if axis_scores[a] < CRITIQUE_THRESHOLD]
        needs_regen = bool(low_axes)
        regen_reason = None
        if needs_regen:
            regen_reason = "; ".join(
                f"{a}={axis_scores[a]}/10" for a in low_axes
            ) + f" (threshold {CRITIQUE_THRESHOLD})"

        usage_obj = getattr(response, "usage", None)
        usage = {
            "prompt_tokens": int(getattr(usage_obj, "prompt_tokens", 0) or 0),
            "completion_tokens": int(getattr(usage_obj, "completion_tokens", 0) or 0),
        }

        return CritiqueResult(
            axis_scores=axis_scores,
            needs_regen=needs_regen,
            low_axes=low_axes,
            regen_reason=regen_reason,
            critic_model=CRITIC_MODEL,
            usage=usage,
        )

    except (json.JSONDecodeError, ValueError) as exc:
        logger.info("[SELF_CRITIQUE] malformed critique JSON (%s) — serving original", exc)
        return None
    except Exception as exc:  # noqa: BLE001 — critique must NEVER block the verdict
        logger.warning("[SELF_CRITIQUE] critique pass failed (%s) — serving original", exc)
        return None


async def persist_critique(
    *,
    comparison_id: Optional[str],
    critique: CritiqueResult,
    regenerated: bool,
) -> None:
    """I3.2 — write one verdict_critiques row (migration 030) via the
    service-role client. Designed to be wrapped in _fire_and_forget by the
    caller; this function NEVER raises (observability write — a DB outage
    must not affect the served verdict).

    `comparison_id` is the FK target (the saved comparisons.id). When None —
    e.g. an anonymous comparison that was never persisted — the write is
    skipped (no FK target, no dangling row).

    migration 030 CHECK invariants honored:
      - all 5 axis scores are 0..10 ints (CritiqueResult guarantees this).
      - regen_reason is NON-NULL whenever regenerated=true.
    """
    if not comparison_id:
        return
    try:
        row = {
            "comparison_id": comparison_id,
            "bias_score": critique.axis_scores.get("bias_score"),
            "vagueness_score": critique.axis_scores.get("vagueness_score"),
            "hedging_score": critique.axis_scores.get("hedging_score"),
            "missing_citation_score": critique.axis_scores.get("missing_citation_score"),
            "pain_workflow_align_score": critique.axis_scores.get("pain_workflow_align_score"),
            "regenerated": regenerated,
            # CHECK vc_regen_reason_when_regenerated: regenerated=true ⇒
            # regen_reason NOT NULL. Fall back to the low-axis summary if the
            # caller regenerated but didn't pass a reason through.
            "regen_reason": (
                critique.regen_reason
                or ("; ".join(critique.low_axes) if critique.low_axes else "regenerated")
            ) if regenerated else critique.regen_reason,
            "critic_model": critique.critic_model,
            "critic_tokens_used": critique.tokens_used,
        }
        client = get_admin_supabase_client()
        client.table("verdict_critiques").insert(row).execute()
    except Exception as exc:  # noqa: BLE001 — observability write, never fatal
        logger.warning("[SELF_CRITIQUE] verdict_critiques persist failed (%s)", exc)


@dataclasses.dataclass
class CritiqueOutcome:
    """Result of the orchestrator-facing critique-and-maybe-regenerate flow.

    `final_comparison` is the verdict the caller should ship (the
    regenerated one if a regeneration fired and succeeded, else the
    original — ALWAYS a valid verdict). `critique` is the CritiqueResult
    (None when the flag is OFF or the critique failed). `regenerated` is
    whether the ONE regeneration actually fired AND succeeded.
    `critique_usage` carries the critique-call token usage for I3.3 cost
    tracking (zeros when no critique ran)."""
    final_comparison: Dict[str, Any]
    critique: Optional[CritiqueResult]
    regenerated: bool
    critique_usage: Dict[str, int]


async def critique_and_maybe_regenerate(
    *,
    comparison: Dict[str, Any],
    product_names: List[str],
    regenerate,
    pain_workflow_context: Optional[str] = None,
) -> CritiqueOutcome:
    """Orchestrator-facing helper (keeps the ssc.py call site ~3 lines).

    Flag-gated by ENABLE_SELF_CRITIQUE (OFF → no-op: returns the original
    verdict, no critique call, zero cost). When ON: score the verdict; if
    any axis is below threshold, call `regenerate(critique)` EXACTLY ONCE
    (hard cap — the regenerated verdict is NOT re-critiqued) and ship its
    result. NEVER raises and NEVER blocks the response:
      - critique failure → original verdict, critique=None, regenerated=False.
      - regeneration callback failure → original verdict, regenerated=False,
        critique preserved (so the low scores are still recorded).

    `regenerate` is an async callable taking the CritiqueResult and
    returning a new verdict dict — the caller supplies the closure that
    re-runs generate_comparison with the critique feedback.
    """
    zero_usage = {"prompt_tokens": 0, "completion_tokens": 0}
    if not is_self_critique_enabled():
        return CritiqueOutcome(
            final_comparison=comparison, critique=None,
            regenerated=False, critique_usage=zero_usage,
        )

    critique = await critique_verdict(
        comparison=comparison,
        product_names=product_names,
        pain_workflow_context=pain_workflow_context,
    )
    if critique is None:
        # Critique failed — serve the original, no regen.
        return CritiqueOutcome(
            final_comparison=comparison, critique=None,
            regenerated=False, critique_usage=zero_usage,
        )

    usage = dict(critique.usage)
    if not critique.needs_regen:
        return CritiqueOutcome(
            final_comparison=comparison, critique=critique,
            regenerated=False, critique_usage=usage,
        )

    # Exactly ONE regeneration. The regenerated verdict is shipped as-is —
    # never re-critiqued (hard cap bounds cost + latency + loop risk).
    try:
        regenerated_comparison = await regenerate(critique)
        if regenerated_comparison and isinstance(regenerated_comparison, dict):
            return CritiqueOutcome(
                final_comparison=regenerated_comparison, critique=critique,
                regenerated=True, critique_usage=usage,
            )
        # Regen returned nothing usable — fall back to original.
        logger.info("[SELF_CRITIQUE] regeneration returned no verdict — serving original")
    except Exception as exc:  # noqa: BLE001 — regen must never block the response
        logger.warning("[SELF_CRITIQUE] regeneration failed (%s) — serving original", exc)

    return CritiqueOutcome(
        final_comparison=comparison, critique=critique,
        regenerated=False, critique_usage=usage,
    )
