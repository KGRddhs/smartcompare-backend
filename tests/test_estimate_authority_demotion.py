"""S3 L3.2+ — estimate price-authority demotion (Ahmed directive 2026-06-13:
"facts, accuracy... NO estimation. An estimated-price product can never out-rank
a real-priced one on fabricated confidence").

The hole: _compute_raw_scores feeds price.amount into the value/price dimensions
REGARDLESS of source_method, so a GPT-*estimated* cheap price inflates the value
dim and can hand an estimated product a DECISIVE win over a real-priced
competitor — a fabricated number out-ranking real Bahrain data. The band-limited
L3.2 tie-break doesn't catch this when the (fabricated) price gap pushes the
margin outside the tie band.

Demotion rule (fact-preserving, never fabricates the other way): when exactly
one product has a real price (source_method in the trust set) and the other only
an estimate, the ESTIMATED product may win ONLY IF it also leads on the NON-PRICE
evidence (specs / reviews / reliability / popularity). If the estimate's edge is
purely its (fabricated) price, the win defers to the real-priced product, with a
winner_evidence reason. The real-priced product is NEVER demoted — facts win.
"""
import pytest

from app.services import scoring_service
from app.services.scoring_service import ScoringService


@pytest.fixture
def service():
    return ScoringService()


def _elec(name, *, amount, source_method, rating=4.4, review_count=500,
          specs=None, fact_check=None):
    return {
        "name": name,
        "category": "electronics",
        "specs": specs if specs is not None else {
            "ram": "8 GB", "storage": "256 GB", "battery": "4000 mAh",
        },
        "rating": rating,
        "review_count": review_count,
        "price": {"amount": amount, "currency": "BHD", "source_method": source_method},
        "fact_check": fact_check if fact_check is not None else {"specs_verified": 3},
    }


# ---------------------------------------------------------------------------
# Core: an estimate must NOT win on a fabricated price alone (decisive margin)
# ---------------------------------------------------------------------------

def test_estimate_cannot_outrank_real_on_price_alone_decisive(service):
    """Estimated cheap (150 BHD est) vs real pricier (320 BHD local_bhd), IDENTICAL
    specs/rating. The estimate's only edge is its fabricated cheap price. Even at a
    decisive margin, the winner must defer to the REAL-priced product."""
    est_cheap = _elec("EstCheap", amount=150, source_method="estimated")
    real_pricier = _elec("RealPricier", amount=320, source_method="local_bhd")
    result = service.compute_scores([est_cheap, real_pricier])
    assert result["winner_index"] == 1, (
        "an estimated price must never out-rank a real Bahrain price when the "
        "estimate's only advantage is the (fabricated) price"
    )
    ev = " ".join(str(e) for e in (result.get("winner_evidence") or [])).lower()
    assert any(t in ev for t in ("bahrain", "real", "price", "confirmed")), ev


def test_estimate_demotion_is_order_independent(service):
    """Same scenario, products swapped — the real-priced product still wins."""
    real_pricier = _elec("RealPricier", amount=320, source_method="local_bhd")
    est_cheap = _elec("EstCheap", amount=150, source_method="estimated")
    result = service.compute_scores([real_pricier, est_cheap])
    assert result["winner_index"] == 0  # real-priced product is index 0 here


# ---------------------------------------------------------------------------
# Guards: demotion must NOT fabricate a flip when the estimate legitimately leads
# ---------------------------------------------------------------------------

def test_estimate_still_wins_when_it_leads_on_non_price_evidence(service):
    """If the estimated product ALSO leads decisively on real non-price evidence
    (much better specs + rating), it keeps the win — the demotion only strips a
    PURELY-price-driven estimate win, never a genuine spec/review lead."""
    est_strong = _elec(
        "EstStrong", amount=150, source_method="estimated",
        specs={"ram": "16 GB", "storage": "1024 GB", "battery": "6000 mAh",
               "rear_camera": "200 MP", "front_camera": "32 MP"},
        rating=4.9, review_count=8000,
        fact_check={"specs_verified": 5, "price_verified": False,
                    "review_sentiment_consistent": True},
    )
    real_weak = _elec(
        "RealWeak", amount=320, source_method="local_bhd",
        specs={"ram": "4 GB", "storage": "64 GB"},
        rating=3.2, review_count=30,
        fact_check={"specs_verified": 1, "specs_unverified": 4},
    )
    result = service.compute_scores([est_strong, real_weak])
    assert result["winner_index"] == 0, (
        "an estimate that leads on real specs+reviews keeps the win; demotion "
        "only removes a purely-price-driven estimate victory"
    )


def test_both_estimated_no_demotion(service):
    """Both products estimated -> there's no real-priced product to defer to;
    demotion must not fire (the plain argmax/tie-break stands)."""
    p0 = _elec("Est0", amount=150, source_method="estimated")
    p1 = _elec("Est1", amount=320, source_method="estimated")
    result = service.compute_scores([p0, p1])
    # Cheaper estimate wins on argmax; no real price anywhere -> no demotion flip,
    # no price-authority evidence.
    assert result["winner_index"] == 0
    ev = " ".join(str(e) for e in (result.get("winner_evidence") or [])).lower()
    assert "confirmed bahrain price" not in ev


def test_real_priced_winner_unaffected_by_demotion(service):
    """When the real-priced product ALREADY wins, demotion is a no-op (it never
    demotes the real-priced side). converted_usd counts as NOT-real, so the
    local_bhd product is the real one."""
    real_winner = _elec("RealWinner", amount=200, source_method="local_bhd",
                        rating=4.7, review_count=2000)
    est_loser = _elec("EstLoser", amount=600, source_method="converted_usd",
                      rating=4.0, review_count=100)
    result = service.compute_scores([real_winner, est_loser])
    assert result["winner_index"] == 0


def test_converted_usd_is_not_real_price_for_demotion(service):
    """converted_usd is NOT a real local Bahrain price (per _PRICE_TRUST_SET).
    An estimate vs converted_usd is estimate-vs-estimate for demotion purposes —
    neither is real, so no demotion flip."""
    est = _elec("Est", amount=150, source_method="estimated")
    conv = _elec("Conv", amount=320, source_method="converted_usd")
    result = service.compute_scores([est, conv])
    # cheaper one wins on argmax; no demotion (neither is a real BH price)
    assert result["winner_index"] == 0
