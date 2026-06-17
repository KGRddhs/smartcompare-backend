"""Trust validation — cross-check GPT verdict claims against deterministic scores."""
import logging
from typing import Dict, Any, Optional, List

from app.services.scoring_service import CATEGORY_DIMENSIONS, MISSING_SCORE, _extract_hours

logger = logging.getLogger(__name__)


def _check_longevity_consistency(
    scoring_result: Dict[str, Any], products: List[Dict[str, Any]]
) -> Optional[bool]:
    """F4.1 — True/False iff the longevity_score dimension winner AGREES with the
    spec-stated longevity, or None when it can't be evaluated.

    The prod contradiction: p0 won longevity_score (78.7 > 70.5) while p0's spec
    longevity ("5-6 hours") was SHORTER than p1's ("all day"). With the qualitative
    `_extract_hours` map, we compare the spec-stated hours to the dim-score leader
    and flag a disagreement so trust_validation surfaces it (without changing the
    scoring math). Returns None when specs/scores are missing."""
    try:
        scores = scoring_result.get("scores") or {}
        b0 = (scores.get("product_0") or {}).get("breakdown") or {}
        b1 = (scores.get("product_1") or {}).get("breakdown") or {}
        s0 = b0.get("longevity_score")
        s1 = b1.get("longevity_score")
        if not isinstance(s0, (int, float)) or not isinstance(s1, (int, float)):
            return None
        if abs(s0 - s1) < 3.0:
            return None  # essentially tied — no meaningful winner to contradict
        if len(products) < 2:
            return None
        sp0 = (products[0] or {}).get("specs") or {}
        sp1 = (products[1] or {}).get("specs") or {}
        h0 = _extract_hours(sp0.get("longevity") or sp0.get("longevity_hours"))
        h1 = _extract_hours(sp1.get("longevity") or sp1.get("longevity_hours"))
        if h0 is None or h1 is None or abs(h0 - h1) < 0.5:
            return None  # no spec signal / equal hours — nothing to contradict
        score_leader = 0 if s0 > s1 else 1
        spec_leader = 0 if h0 > h1 else 1
        return score_leader == spec_leader
    except Exception:  # noqa: BLE001 — a consistency probe must never break validation
        return None


def validate_verdict(
    verdict: Dict[str, Any],
    scoring_result: Dict[str, Any],
    category: str,
    products: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Cross-validate GPT verdict against deterministic scoring data.

    Returns validation metadata:
        winner_aligned: bool — GPT winner matches scoring winner
        claims_validated: int — dimensions where GPT and scores agree directionally
        claims_softened: int — dimensions where scores are essentially tied (gap < 3)
        claims_flagged: int — dimensions where GPT contradicted scores
        confidence_adjustment: str|None — suggested confidence change
    """
    scores = scoring_result.get("scores", {})
    if not scores or "product_0" not in scores or "product_1" not in scores:
        return {
            "winner_aligned": True,
            "claims_validated": 0,
            "claims_softened": 0,
            "claims_flagged": 0,
            "confidence_adjustment": None,
        }

    # Check winner alignment
    score_winner = scoring_result.get("winner_index", 0)
    verdict_winner = verdict.get("winner_index", 0)
    winner_aligned = score_winner == verdict_winner

    # Check dimension-level alignment
    dims = CATEGORY_DIMENSIONS.get(category, CATEGORY_DIMENSIONS.get("other", []))
    b0 = scores["product_0"].get("breakdown", {})
    b1 = scores["product_1"].get("breakdown", {})

    validated = 0
    softened = 0
    flagged = 0

    verdict_winner = verdict.get("winner_index", 0)

    for dim in dims:
        s0 = b0.get(dim, MISSING_SCORE)
        s1 = b1.get(dim, MISSING_SCORE)
        if s0 is None or s1 is None or s0 == MISSING_SCORE or s1 == MISSING_SCORE:
            continue

        gap = abs(s0 - s1)
        if gap < 3.0:
            # Scores are essentially tied — any strong claim is overclaiming
            softened += 1
        else:
            score_dim_leader = 0 if s0 > s1 else 1
            if score_dim_leader != verdict_winner and gap >= 10.0:
                flagged += 1
            else:
                validated += 1

    # F4.1 — fragrance longevity consistency cross-check (spec-stated longevity
    # vs the longevity_score dim winner). Only meaningful for fragrances and only
    # when product specs are supplied. A contradiction reduces confidence.
    longevity_consistent = None
    if category == "fragrances" and products:
        longevity_consistent = _check_longevity_consistency(scoring_result, products)

    # Confidence adjustment
    confidence_adjustment = None
    if not winner_aligned:
        confidence_adjustment = "low"
    elif flagged > 2:
        confidence_adjustment = "reduced"
    elif longevity_consistent is False and confidence_adjustment is None:
        confidence_adjustment = "reduced"

    result = {
        "winner_aligned": winner_aligned,
        "claims_validated": validated,
        "claims_softened": softened,
        "claims_flagged": flagged,
        "confidence_adjustment": confidence_adjustment,
    }
    if longevity_consistent is not None:
        result["longevity_consistent"] = longevity_consistent
    return result
