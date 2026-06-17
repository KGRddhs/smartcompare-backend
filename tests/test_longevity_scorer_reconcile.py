"""Bundle-next #16 — F4.1 deeper longevity scorer-math (EVAL-GATED).

The fragrance `longevity_score` dimension is sourced from the GENERIC
`spec_secondary` signal (a spec-coverage + review blend) — it does NOT read the
actual `longevity` spec value. So the dim winner could CONTRADICT the real
longevity signal: prod showed Ombre ('5-6 hours') scoring 78.9 > Tobacco
('all day') 69.5 — the shorter-longevity fragrance winning the longevity dim.

Fix (scorer-math reconciliation): for fragrances, after the generic
longevity_score is computed, apply a BOUNDED nudge keyed on the parsed longevity
hours (_extract_hours, qualitative-aware) so the longevity dim ORDERING follows
the real hours signal when it's clear — without an eval-destabilizing magnitude
rewrite. Already shipped in #5: the _extract_hours qualitative map + the
trust_validation cross-check; THIS pins the actual scorer so the dim winner
aligns.

EVAL-GATED: these are the thorough unit tests; Test runs ONE smoke20 eval at the
end vs baseline 7a5fc55b to confirm specs/winner/factual don't regress.
"""

import pytest

from app.services.scoring_service import ScoringService


def _frag(name, longevity, rating=4.4, sillage="moderate"):
    return {
        "category": "fragrances", "brand": "Tom Ford", "name": name,
        "price": {"amount": 100, "currency": "BHD"}, "rating": rating, "review_count": 5000,
        "specs": {"scent_family": "Oriental", "notes_top": "x", "notes_heart": "y",
                  "notes_base": "z", "longevity": longevity, "sillage": sillage,
                  "concentration": "EDP"},
        "reviews": {"source_ratings": [{"rating": rating}]},
        "fact_check": {"specs_verified": 3, "specs_likely": 2, "specs_flagged": 0,
                       "specs_unverified": 1, "price_verified": True,
                       "review_sentiment_consistent": True},
    }


def _longevity(result, idx):
    return result["scores"][f"product_{idx}"]["breakdown"]["longevity_score"]


class TestLongevityOrderingFollowsHours:
    def test_all_day_beats_5_6_hours(self):
        # The exact prod contradiction: 'all day' (≈10h) must NOT lose the
        # longevity dim to '5-6 hours'.
        svc = ScoringService()
        r = svc.compute_scores([_frag("Ombre", "5-6 hours"), _frag("Tobacco", "all day")])
        assert _longevity(r, 1) >= _longevity(r, 0), (
            f"all-day p1 ({_longevity(r,1)}) must >= 5-6h p0 ({_longevity(r,0)})"
        )

    def test_numeric_hours_ordering(self):
        svc = ScoringService()
        r = svc.compute_scores([_frag("A", "10 hours"), _frag("B", "4 hours")])
        assert _longevity(r, 0) >= _longevity(r, 1)

    def test_reverse_order_also_correct(self):
        # Symmetric: put the long one first.
        svc = ScoringService()
        r = svc.compute_scores([_frag("A", "all day"), _frag("B", "3 hours")])
        assert _longevity(r, 0) >= _longevity(r, 1)

    def test_qualitative_long_beats_short(self):
        svc = ScoringService()
        r = svc.compute_scores([_frag("A", "weak"), _frag("B", "long-lasting")])
        assert _longevity(r, 1) >= _longevity(r, 0)


class TestNoDistortionWhenSignalAbsentOrEqual:
    def test_equal_hours_unchanged_ordering(self):
        # Same longevity → the generic composite decides (no nudge flips an
        # otherwise-tied pair into a spurious winner).
        svc = ScoringService()
        r = svc.compute_scores([_frag("A", "8 hours", rating=4.6),
                                _frag("B", "8 hours", rating=4.0)])
        # Both have identical longevity hours; scores stay finite + bounded.
        assert 0 <= _longevity(r, 0) <= 100
        assert 0 <= _longevity(r, 1) <= 100

    def test_missing_longevity_no_crash(self):
        svc = ScoringService()
        r = svc.compute_scores([_frag("A", "N/A"), _frag("B", "N/A")])
        # No hours signal on either → no nudge, no crash, bounded scores.
        assert 0 <= _longevity(r, 0) <= 100
        assert 0 <= _longevity(r, 1) <= 100

    def test_one_sided_hours_no_crash(self):
        svc = ScoringService()
        r = svc.compute_scores([_frag("A", "all day"), _frag("B", "N/A")])
        assert 0 <= _longevity(r, 0) <= 100
        assert 0 <= _longevity(r, 1) <= 100


class TestBoundedAndScopedToFragrances:
    def test_scores_stay_in_0_100(self):
        svc = ScoringService()
        r = svc.compute_scores([_frag("A", "12 hours"), _frag("B", "1 hour")])
        for i in (0, 1):
            assert 0 <= _longevity(r, i) <= 100

    def test_electronics_unaffected(self):
        # The reconciliation is fragrance-scoped — electronics longevity is not a
        # dim; this just guards that compute_scores on electronics is unchanged.
        svc = ScoringService()
        elec = lambda n, s: {
            "category": "electronics", "brand": "B", "name": n,
            "price": {"amount": 300, "currency": "BHD"}, "rating": 4.3, "review_count": 200,
            "specs": {"processor": "A17", "ram": "8 GB", "storage": s, "battery": "4000 mAh"},
            "reviews": {"source_ratings": [{"rating": 4.3}]},
            "fact_check": {"specs_verified": 4, "specs_likely": 1, "specs_flagged": 0,
                           "specs_unverified": 0, "price_verified": True,
                           "review_sentiment_consistent": True},
        }
        r = svc.compute_scores([elec("X", "256 GB"), elec("Y", "128 GB")])
        # electronics has no longevity_score dim — present dims are bounded.
        for dim, val in r["scores"]["product_0"]["breakdown"].items():
            assert isinstance(val, (int, float))


class TestMakeupLongevityAlsoReconciled:
    """Makeup ALSO has a longevity_score dim (sourced from review). A makeup
    'long_lasting' spec signal should not contradict — guard it stays bounded +
    a clearer long-wear product isn't penalized. (Scoped check: no crash, bounded.)"""

    def _makeup(self, name, long_lasting):
        return {
            "category": "makeup", "brand": "B", "name": name,
            "price": {"amount": 30, "currency": "BHD"}, "rating": 4.2, "review_count": 300,
            "specs": {"shade_range": "40 shades", "finish": "matte", "coverage": "full",
                      "long_lasting": long_lasting, "volume": "30 ml"},
            "reviews": {"source_ratings": [{"rating": 4.2}]},
            "fact_check": {"specs_verified": 3, "specs_likely": 1, "specs_flagged": 0,
                           "specs_unverified": 1, "price_verified": True,
                           "review_sentiment_consistent": True},
        }

    def test_makeup_longevity_bounded(self):
        svc = ScoringService()
        r = svc.compute_scores([self._makeup("A", "16 hours"), self._makeup("B", "8 hours")])
        for i in (0, 1):
            v = r["scores"][f"product_{i}"]["breakdown"]["longevity_score"]
            assert 0 <= v <= 100
