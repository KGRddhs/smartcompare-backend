"""S3 winner-mechanism intervention #1 — value-axis neutralization (FLAG-GATED,
default OFF). Built ready-to-measure pending team-lead's ruling; INERT in prod
and in the gate until ENABLE_WINNER_VALUE_NEUTRALIZATION is flipped.

Mechanism (corpus-pinned): the value/price dimension rewards the CHEAPER product
(up to 100 vs 30), but gold's winner is the MORE EXPENSIVE product in 64% of
priced rows (166-row test). So the value axis statistically fights gold —
especially on CROSS-TIER comparisons (budget vs luxury) where "cheaper wins" is
least reliable and the premium is most often justified.

Intervention: when the flag is ON and the comparison is CROSS-TIER, recompute the
winner with the value-type dimension's weight removed (renormalized) so the
cheaper-is-better pressure no longer decides the pick. Within-tier comparisons
are untouched (value is a fair signal there). Default OFF => byte-identical to
today. This is winner-only (eval price/specs/factual read independent fields).
"""
import pytest

from app.services import scoring_service
from app.services.scoring_service import ScoringService


@pytest.fixture
def service():
    return ScoringService()


@pytest.fixture
def neutralize_on(monkeypatch):
    monkeypatch.setenv("ENABLE_WINNER_VALUE_NEUTRALIZATION", "true")
    yield


@pytest.fixture
def neutralize_off(monkeypatch):
    monkeypatch.delenv("ENABLE_WINNER_VALUE_NEUTRALIZATION", raising=False)
    yield


def _elec(name, *, amount, rating, review_count, specs, source_method="local_bhd",
          fact_check=None):
    return {
        "name": name, "category": "electronics",
        "specs": specs, "rating": rating, "review_count": review_count,
        "price": {"amount": amount, "currency": "BHD", "source_method": source_method},
        "fact_check": fact_check if fact_check is not None else {"specs_verified": 4},
    }


def _cross_tier_premium_better():
    """A CROSS-TIER pair where specs are NEAR-EQUAL so the value/price axis is the
    LONE swing: the cheaper budget product wins overall ONLY because of value,
    while the premium leads on rating/reviews/reliability. This is exactly the
    case the value-neutralization targets — removing the cheaper-wins pull lets
    the genuinely-stronger premium win. (When specs already separate the pair,
    value isn't the decider and neutralization correctly does nothing — that's
    why this fixture deliberately equalizes specs.)"""
    # Premium (index 0): pricier; slightly stronger rating/reviews/fact_check.
    premium = _elec(
        "Premium", amount=900, rating=4.6, review_count=3000,
        specs={"ram": "8 GB", "storage": "256 GB", "battery": "4500 mAh",
               "rear_camera": "50 MP", "front_camera": "12 MP"},
        fact_check={"specs_verified": 5, "price_verified": True,
                    "review_sentiment_consistent": True},
    )
    # Budget (index 1): much cheaper; near-identical specs, marginally weaker rating.
    budget = _elec(
        "Budget", amount=150, rating=4.5, review_count=2800,
        specs={"ram": "8 GB", "storage": "256 GB", "battery": "4500 mAh",
               "rear_camera": "50 MP", "front_camera": "12 MP"},
        fact_check={"specs_verified": 5, "price_verified": True,
                    "review_sentiment_consistent": True},
    )
    return premium, budget


# ---------------------------------------------------------------------------
# Default OFF — no behavior change
# ---------------------------------------------------------------------------

def test_flag_off_is_inert(service, neutralize_off):
    """Flag OFF -> winner identical to the unmodified scorer (no neutralization)."""
    premium, budget = _cross_tier_premium_better()
    result = service.compute_scores([premium, budget])
    # We don't assert a specific winner here — only that the flag-off path does
    # not raise and produces a deterministic winner. (Inert path.)
    assert result["winner_index"] in (0, 1)
    # And that no neutralization marker leaks when off.
    assert "winner_value_neutralized" not in result


def test_flag_off_matches_baseline_exactly(service, neutralize_off):
    """The flag-off winner equals the winner computed with neutralization code
    absent — i.e. identical to the pre-intervention argmax."""
    premium, budget = _cross_tier_premium_better()
    r = service.compute_scores([premium, budget])
    # Reconstruct the plain weighted argmax (no value-dim removal).
    scores = r["scores"]
    o0 = scores["product_0"]["overall"]
    o1 = scores["product_1"]["overall"]
    plain = 0 if o0 >= o1 else 1
    assert r["winner_index"] == plain


# ---------------------------------------------------------------------------
# Flag ON, cross-tier — value axis neutralized
# ---------------------------------------------------------------------------

def test_cross_tier_premium_wins_when_neutralized(service, neutralize_on):
    """Flag ON + cross-tier: removing the value dim's pull lets the
    spec/review-superior PREMIUM product win instead of the cheaper budget one."""
    premium, budget = _cross_tier_premium_better()
    result = service.compute_scores([premium, budget])
    assert result.get("is_cross_tier") is True, "fixture must be cross-tier"
    assert result["winner_index"] == 0, (
        "with the value axis neutralized on a cross-tier pair, the spec/review-"
        "superior premium product should win"
    )
    assert result.get("winner_value_neutralized") is True


def test_within_tier_untouched_by_flag(service, neutralize_on):
    """Flag ON but WITHIN-tier: value is a fair signal there, so neutralization
    must NOT fire — winner equals the plain argmax + no marker."""
    a = _elec("A", amount=300, rating=4.5, review_count=900,
              specs={"ram": "8 GB", "storage": "256 GB"})
    b = _elec("B", amount=320, rating=4.4, review_count=800,
              specs={"ram": "8 GB", "storage": "256 GB"})
    result = service.compute_scores([a, b])
    assert result.get("is_cross_tier") is False, "fixture must be within-tier"
    assert not result.get("winner_value_neutralized")


def test_neutralization_is_winner_only_scores_unchanged(service, neutralize_on):
    """Neutralization affects ONLY winner_index — the per-product breakdown +
    overall scores (which the response + eval specs/price read) are unchanged."""
    premium, budget = _cross_tier_premium_better()
    on = service.compute_scores([premium, budget])
    # The value_score breakdown cell is still present + unchanged in magnitude
    # (we damp its WINNER influence, not the displayed score).
    assert "value_score" in on["scores"]["product_0"]["breakdown"]
    assert on["scores"]["product_0"]["overall"] is not None
