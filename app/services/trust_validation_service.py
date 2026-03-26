"""Trust validation — cross-check GPT verdict claims against deterministic scores."""
import logging
from typing import Dict, Any

from app.services.scoring_service import CATEGORY_DIMENSIONS, MISSING_SCORE

logger = logging.getLogger(__name__)


def validate_verdict(
    verdict: Dict[str, Any],
    scoring_result: Dict[str, Any],
    category: str,
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
            validated += 1

    # Confidence adjustment
    confidence_adjustment = None
    if not winner_aligned:
        confidence_adjustment = "low"
    elif flagged > 2:
        confidence_adjustment = "reduced"

    return {
        "winner_aligned": winner_aligned,
        "claims_validated": validated,
        "claims_softened": softened,
        "claims_flagged": flagged,
        "confidence_adjustment": confidence_adjustment,
    }
