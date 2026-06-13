"""S3 L3.4 — surface winner_evidence in scoring_v2.

Plan §L3.4: "winner_evidence surfaced in scoring_v2 — qualitative reasons ONLY
(no backend coefficients/caps per no_backend_internals_in_reveals). Pin with
prod fixtures."

The scoring layer (L3.2 price authority + L3.3 review density) already produces
scoring_result["winner_evidence"] — a list of short qualitative strings.
_build_scoring_v2 must thread it through to the response payload the frontend
reads, defaulting to [] when absent, and never leaking score math.
"""
import json
import pytest

from app.services.response_builder import _build_scoring_v2


def _scoring_result(winner_evidence=None, winner_index=0):
    """Minimal scoring_result with a controllable winner_evidence list."""
    sr = {
        "scores": {
            "product_0": {"overall": 72.0, "breakdown": {"performance_score": 80.0}},
            "product_1": {"overall": 68.0, "breakdown": {"performance_score": 70.0}},
        },
        "winner_index": winner_index,
        "win_margin": 4.0,
        "is_cross_tier": False,
    }
    if winner_evidence is not None:
        sr["winner_evidence"] = winner_evidence
    return sr


def _products():
    return [
        {"name": "Phone A", "category": "electronics",
         "price": {"amount": 300, "currency": "BHD", "source_method": "local_bhd"},
         "rating": 4.5, "review_count": 800},
        {"name": "Phone B", "category": "electronics",
         "price": {"amount": 310, "currency": "BHD", "source_method": "estimated"},
         "rating": 4.4, "review_count": 600},
    ]


def test_scoring_v2_surfaces_winner_evidence():
    evidence = ["Phone A has a confirmed Bahrain price while the other relies on "
                "an indicative figure"]
    sr = _scoring_result(winner_evidence=evidence, winner_index=0)
    sv2 = _build_scoring_v2(_products(), sr, "electronics", 0)
    assert sv2.get("winner_evidence") == evidence


def test_scoring_v2_winner_evidence_defaults_empty_list():
    """No winner_evidence on the scoring_result -> scoring_v2 emits []
    (always-list contract so the frontend can iterate safely)."""
    sr = _scoring_result(winner_evidence=None)
    sv2 = _build_scoring_v2(_products(), sr, "electronics", 0)
    assert sv2.get("winner_evidence") == []


def test_scoring_v2_winner_evidence_is_a_list_of_strings():
    sr = _scoring_result(winner_evidence=["reason one", "reason two"])
    sv2 = _build_scoring_v2(_products(), sr, "electronics", 0)
    we = sv2.get("winner_evidence")
    assert isinstance(we, list)
    assert all(isinstance(x, str) for x in we)


def test_scoring_v2_winner_evidence_tolerates_malformed_input():
    """A non-list winner_evidence (defensive — should never happen) must not
    crash the builder; it coerces to []."""
    sr = _scoring_result(winner_evidence="not a list")
    sv2 = _build_scoring_v2(_products(), sr, "electronics", 0)
    assert sv2.get("winner_evidence") == []


def test_scoring_v2_winner_evidence_no_backend_internals():
    """Whatever reasons flow through must stay qualitative — the surfacing layer
    must not inject coefficients/caps/percentages."""
    sr = _scoring_result(winner_evidence=["Phone A has a confirmed Bahrain price"])
    sv2 = _build_scoring_v2(_products(), sr, "electronics", 0)
    blob = json.dumps(sv2.get("winner_evidence")).lower()
    for forbidden in ("weight", "coefficient", "missing_score", "tie_band", "±", "argmax"):
        assert forbidden not in blob


def test_end_to_end_compute_scores_to_scoring_v2_carries_evidence():
    """Full chain pin: compute_scores (L3.2 price-authority tie-break) ->
    _build_scoring_v2 (L3.4 surfacing). A tie-band pair where product_1 has the
    only real BH price must produce winner_evidence on the final scoring_v2."""
    from app.services.scoring_service import ScoringService
    p0 = {"name": "Est", "category": "electronics",
          "specs": {"ram": "8 GB", "storage": "256 GB"}, "rating": 4.3,
          "review_count": 400, "fact_check": {"specs_verified": 2},
          "price": {"amount": 300, "currency": "BHD", "source_method": "estimated"}}
    p1 = {"name": "Real", "category": "electronics",
          "specs": {"ram": "8 GB", "storage": "256 GB"}, "rating": 4.3,
          "review_count": 400, "fact_check": {"specs_verified": 2},
          "price": {"amount": 300, "currency": "BHD", "source_method": "local_bhd"}}
    sr = ScoringService().compute_scores([p0, p1])
    # The tie-break must have tilted to the real-price product...
    assert sr["winner_index"] == 1
    # ...and that evidence must survive into scoring_v2.
    sv2 = _build_scoring_v2([p0, p1], sr, "electronics", sr["winner_index"])
    assert sv2.get("winner_evidence"), "winner_evidence must reach scoring_v2 end-to-end"
    assert any("bahrain" in e.lower() or "price" in e.lower()
               for e in sv2["winner_evidence"])
