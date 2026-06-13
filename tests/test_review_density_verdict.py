"""S3 L3.3 — review-density (YouTube signal) into the verdict + winner pick.

Plan §L3.3: "L2's YouTube signal (+ Arabic review sources via the usage='review'
path) feeds factual_verdict line-2 evidence + winner confidence — cited, never
as a raw score."

Two surfaces:
  (a) factual_verdict: when the winner has clearly more YouTube review attention
      than the runner-up, that becomes a CITED candidate fact (channel + a
      humanized view count) competing for line1 / used in line2 — never a raw
      score, never the word "estimated".
  (b) winner tie-break: review-density is a SECOND evidence axis for
      apply_winner_evidence_tiebreak. When price authority does NOT discriminate
      (both/neither real price) but one product has markedly more review
      attention inside the tie band, the winner tilts to the higher-attention
      product + a winner_evidence reason. Price authority stays the FIRST axis
      (it's the stronger Bahrain signal); review-density only breaks ties price
      can't.

All consumption is FLAG-GATED on ENABLE_YOUTUBE_SOURCE (mirrors L2's rollback
safety: the 14d cache can carry a youtube_review_signal past a flag flip, so a
rolled-back flag must roll back fully). Flag OFF -> byte-identical to no-YouTube.
"""
import pytest

from app.services import scoring_service
from app.services.scoring_service import ScoringService
from app.services import response_builder
from app.services.response_builder import _build_factual_verdict


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def youtube_on(monkeypatch):
    monkeypatch.setenv("ENABLE_YOUTUBE_SOURCE", "true")
    yield


@pytest.fixture
def youtube_off(monkeypatch):
    monkeypatch.delenv("ENABLE_YOUTUBE_SOURCE", raising=False)
    yield


def _yt_signal(*, total_views, video_count, channel, title="Full Review"):
    """Synthesize the L2 youtube_review_signal shape (no L2 import dependency)."""
    return {
        "review_count_signal": video_count * 50,
        "top_video_title": title,
        "top_channel": channel,
        "video_url": "https://www.youtube.com/watch?v=abc123",
        "total_views": total_views,
        "video_count": video_count,
    }


def _prod(name, *, price_amount=300, source_method="estimated", rating=4.3,
          review_count=300, yt=None, specs=None):
    p = {
        "name": name,
        "category": "electronics",
        "specs": specs if specs is not None else {"ram": "8 GB", "storage": "256 GB"},
        "rating": rating,
        "review_count": review_count,
        "price": {"amount": price_amount, "currency": "BHD",
                  "source_method": source_method},
        "reviews": {},
        "fact_check": {"specs_verified": 2},
    }
    if yt is not None:
        p["reviews"]["youtube_review_signal"] = yt
    return p


# ---------------------------------------------------------------------------
# (a) factual_verdict — review-density as a CITED candidate
# ---------------------------------------------------------------------------

def test_factual_verdict_cites_youtube_density_when_on(youtube_on):
    """Winner (index 0) has 2.4M YouTube views across 12 videos; runner-up has
    almost none. With price/rating tied, the review-density fact should surface
    in the verdict, citing the channel + a humanized count."""
    winner = _prod("Phone A", yt=_yt_signal(total_views=2_400_000, video_count=12,
                                            channel="MKBHD"))
    runner = _prod("Phone B", yt=_yt_signal(total_views=3_000, video_count=1,
                                            channel="SmallChan"))
    # Identical price + rating so neither price nor rating candidate dominates.
    fv = _build_factual_verdict([winner, runner], {}, winner_index=0, dimensions=[])
    blob = (fv["line1"] + " " + fv["line2"]).lower()
    assert "mkbhd" in blob or "2.4m" in blob or "youtube" in blob or "review" in blob, (
        f"factual_verdict should cite the YouTube review-density signal; got {fv}"
    )
    # Never the word "estimated"; never a raw view integer.
    assert "estimated" not in blob
    assert "2400000" not in blob


def test_factual_verdict_no_youtube_when_flag_off(youtube_off):
    """Flag OFF -> the youtube_review_signal on the product must NOT leak into
    the verdict, even if a stale cache attached one."""
    winner = _prod("Phone A", yt=_yt_signal(total_views=2_400_000, video_count=12,
                                            channel="MKBHD"))
    runner = _prod("Phone B", yt=_yt_signal(total_views=3_000, video_count=1,
                                            channel="SmallChan"))
    fv = _build_factual_verdict([winner, runner], {}, winner_index=0, dimensions=[])
    blob = (fv["line1"] + " " + fv["line2"]).lower()
    assert "mkbhd" not in blob and "youtube" not in blob, (
        f"flag OFF must not surface YouTube density; got {fv}"
    )


def test_factual_verdict_no_youtube_density_when_attention_comparable(youtube_on):
    """When BOTH products have similar review attention, density is not a
    discriminating fact -> don't cite it (avoids a meaningless 'more reviews'
    claim). Falls back to the existing price/rating/dim line."""
    winner = _prod("Phone A", yt=_yt_signal(total_views=1_000_000, video_count=8,
                                            channel="Chan1"))
    runner = _prod("Phone B", yt=_yt_signal(total_views=1_050_000, video_count=8,
                                            channel="Chan2"))
    fv = _build_factual_verdict([winner, runner], {}, winner_index=0, dimensions=[])
    blob = (fv["line1"] + " " + fv["line2"]).lower()
    # No channel citation when attention is comparable.
    assert "chan1" not in blob and "chan2" not in blob


# ---------------------------------------------------------------------------
# (b) winner tie-break — review-density as the SECOND evidence axis
# ---------------------------------------------------------------------------

@pytest.fixture
def service():
    return ScoringService()


def test_review_density_breaks_tie_when_price_undiscriminating(service, youtube_on):
    """Both products are estimates (price authority can't discriminate) but
    product_1 has vastly more YouTube review attention. Inside the tie band the
    winner should tilt to product_1 + emit a review-density winner_evidence
    reason."""
    p0 = _prod("Quiet", source_method="estimated",
               yt=_yt_signal(total_views=5_000, video_count=1, channel="Tiny"))
    p1 = _prod("Loud", source_method="estimated",
               yt=_yt_signal(total_views=3_000_000, video_count=15, channel="MKBHD"))
    result = service.compute_scores([p0, p1])
    assert result["winner_index"] == 1, (
        "with price tied/estimated, the markedly-more-reviewed product should win the tie"
    )
    blob = " ".join(str(e) for e in (result.get("winner_evidence") or [])).lower()
    assert any(t in blob for t in ("review", "youtube", "mkbhd", "attention", "coverage")), (
        f"winner_evidence should cite the review-density signal; got {result.get('winner_evidence')}"
    )


def test_price_authority_beats_review_density(service, youtube_on):
    """Price authority is the FIRST axis. If product_0 has the only real BH
    price but product_1 has more YouTube attention, price authority wins the tie
    (real local price > video popularity for a Bahrain buyer)."""
    p0 = _prod("RealPrice", source_method="local_bhd",
               yt=_yt_signal(total_views=10_000, video_count=1, channel="Tiny"))
    p1 = _prod("Popular", source_method="estimated",
               yt=_yt_signal(total_views=3_000_000, video_count=15, channel="MKBHD"))
    result = service.compute_scores([p0, p1])
    assert result["winner_index"] == 0, (
        "real BH price must outrank review-density in the tie-break"
    )


def test_review_density_tiebreak_inert_when_flag_off(service, youtube_off):
    """Flag OFF -> review-density must not influence the winner at all."""
    p0 = _prod("Quiet", source_method="estimated",
               yt=_yt_signal(total_views=5_000, video_count=1, channel="Tiny"))
    p1 = _prod("Loud", source_method="estimated",
               yt=_yt_signal(total_views=3_000_000, video_count=15, channel="MKBHD"))
    result = service.compute_scores([p0, p1])
    # No real price, flag off -> no discriminating evidence -> argmax stands,
    # no review-density evidence.
    blob = " ".join(str(e) for e in (result.get("winner_evidence") or [])).lower()
    assert "review" not in blob and "youtube" not in blob and "mkbhd" not in blob


def test_review_density_evidence_no_backend_internals(service, youtube_on):
    """Review-density winner_evidence stays qualitative — no view-count integers,
    coefficients, or score math leaked."""
    p0 = _prod("Quiet", source_method="estimated",
               yt=_yt_signal(total_views=5_000, video_count=1, channel="Tiny"))
    p1 = _prod("Loud", source_method="estimated",
               yt=_yt_signal(total_views=3_000_000, video_count=15, channel="MKBHD"))
    result = service.compute_scores([p0, p1])
    blob = " ".join(str(e) for e in (result.get("winner_evidence") or [])).lower()
    for forbidden in ("3000000", "tie_band", "argmax", "weight", "coefficient", "%"):
        assert forbidden not in blob, f"leaked backend internal: {forbidden!r}"
