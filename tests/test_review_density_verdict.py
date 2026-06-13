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
# (b) winner axis — review-density is a CITED VERDICT signal, NOT a winner-
# determinant (v2 re-architecture, 2026-06-13).
#
# HISTORY: the original L3.3 (pre-pivot, commit d72b18e) made YouTube review-
# density a SECOND winner-tie-break axis that FLIPPED winner_index inside the
# tie band. The "genuine winner from score" v2 pivot (Ahmed: "recommendation
# based on pain, prompt, reviews, preferences, logic") DROPPED every
# winner_index flip — the winner is now the plain argmax of the authority-
# adjusted `overall`. YouTube view-count NEVER enters compute_scores (grep:
# zero refs in scoring_service); it remains a CITED supporting input to the
# factual_verdict + the verdict prompt (surface (a) above + L2's
# _build_youtube_signal_block) — exactly the no-fabrication principle: a
# popularity number must not silently crown a winner. These tests now PIN that
# boundary: density does NOT flip the genuine winner, and build_winner_evidence
# never fabricates a density reason. (Coverage preserved, aligned to v2.)
# ---------------------------------------------------------------------------

@pytest.fixture
def service():
    return ScoringService()


def test_review_density_does_not_flip_genuine_winner(service, youtube_on):
    """v2: both products are identical real signals (estimated price, same
    rating/specs) → compute_scores yields a GENUINE TIE (overall equal). The
    vastly-larger YouTube attention on product_1 must NOT flip the winner — view
    count is a CITED verdict signal, never a score input or a winner-determinant.
    The winner stays the deterministic argmax of the genuine tie (index 0), and
    build_winner_evidence stays EMPTY (no fabricated density reason on a coin-
    flip). This is the inverse of the dropped pre-pivot L3.3 index-flip."""
    p0 = _prod("Quiet", source_method="estimated",
               yt=_yt_signal(total_views=5_000, video_count=1, channel="Tiny"))
    p1 = _prod("Loud", source_method="estimated",
               yt=_yt_signal(total_views=3_000_000, video_count=15, channel="MKBHD"))
    result = service.compute_scores([p0, p1])
    # Genuine tie on the real signals — youtube density did not move `overall`.
    o0 = result["scores"]["product_0"]["overall"]
    o1 = result["scores"]["product_1"]["overall"]
    assert o0 == o1, (
        f"identical real signals must score equal — youtube view-count must NOT "
        f"enter the score; got o0={o0} o1={o1}"
    )
    # Winner is NOT flipped to the higher-attention product by density.
    assert result["winner_index"] != 1, (
        "YouTube review-density must NOT flip the genuine winner to product_1 "
        "(density is citation-only in v2, never a winner-determinant)"
    )
    # No fabricated review-density reason on a genuine coin-flip.
    blob = " ".join(str(e) for e in (result.get("winner_evidence") or [])).lower()
    assert not any(t in blob for t in ("youtube", "mkbhd", "view", "attention")), (
        f"winner_evidence must not fabricate a density reason; got {result.get('winner_evidence')}"
    )


def test_real_price_authority_drives_winner_not_density(service, youtube_on):
    """v2 grounds the winner in REAL signals: product_0 has the only real BH
    price (price-authority bump to its `overall`) while product_1 has far more
    YouTube attention. The genuine winner is product_0 — real local price beats
    video popularity, and density never enters the score to contest it."""
    p0 = _prod("RealPrice", source_method="local_bhd",
               yt=_yt_signal(total_views=10_000, video_count=1, channel="Tiny"))
    p1 = _prod("Popular", source_method="estimated",
               yt=_yt_signal(total_views=3_000_000, video_count=15, channel="MKBHD"))
    result = service.compute_scores([p0, p1])
    assert result["winner_index"] == 0, (
        "real BH price authority must drive the genuine winner over video popularity"
    )


def test_review_density_inert_on_winner_when_flag_off(service, youtube_off):
    """Flag OFF -> review-density must not influence the winner OR emit evidence.
    (Already true in v2 since density never enters the score; pins it explicitly
    so a future density→score wiring can't regress the flag-OFF rollback path.)"""
    p0 = _prod("Quiet", source_method="estimated",
               yt=_yt_signal(total_views=5_000, video_count=1, channel="Tiny"))
    p1 = _prod("Loud", source_method="estimated",
               yt=_yt_signal(total_views=3_000_000, video_count=15, channel="MKBHD"))
    result = service.compute_scores([p0, p1])
    blob = " ".join(str(e) for e in (result.get("winner_evidence") or [])).lower()
    assert "youtube" not in blob and "mkbhd" not in blob and "view" not in blob


def test_winner_evidence_no_backend_internals(service, youtube_on):
    """winner_evidence stays qualitative — no view-count integers, coefficients,
    or score math leaked (no_backend_internals_in_reveals)."""
    p0 = _prod("Quiet", source_method="estimated",
               yt=_yt_signal(total_views=5_000, video_count=1, channel="Tiny"))
    p1 = _prod("Loud", source_method="local_bhd",
               yt=_yt_signal(total_views=3_000_000, video_count=15, channel="MKBHD"))
    result = service.compute_scores([p0, p1])
    blob = " ".join(str(e) for e in (result.get("winner_evidence") or [])).lower()
    for forbidden in ("3000000", "tie_band", "argmax", "weight", "coefficient", "%"):
        assert forbidden not in blob, f"leaked backend internal: {forbidden!r}"
