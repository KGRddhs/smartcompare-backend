"""S3 winner-mechanism Option A1 — normalization dampening (team-lead APPROVED
as DEFAULT, 2026-06-13).

Mechanism (corpus-pinned): `_normalize_dimension` mapped the relative position
with `30 + ratio*70`, so the product with even a SLIGHTLY higher raw spec number
got 100 and the other got 30 — a 70-point gap manufactured from noise. A1 narrows
the spread to `45 + ratio*40` (range 45–85) so a tiny raw-spec edge stops
manufacturing a landslide. This compresses BOTH the user-visible dimension bars
AND the winner/overall contribution (the FULL version, shipped DEFAULT per
team-lead's "more coherent" steer).

Fallback (flag `DISABLE_DIM_NORM_DAMPENING`, default OFF): when flipped, reverts
`_normalize_dimension` to the legacy 30–100 spread entirely (display + winner) —
the escape hatch in case Ahmed wants the dramatic bars kept. Noted but NOT the
default. (A true winner-only split — dampened winner math + legacy display bars
— needs a larger compute_scores refactor to compute two breakdowns; offered
on request, not built here to keep A1's blast radius minimal.)

Safety: winner_pass/price/specs/factual eval axes can't regress (winner reads
overall; eval price/specs read overview.products) — A1 only re-scales the dim
bars + their weighted contribution.
"""
import pytest

from app.services import scoring_service
from app.services.scoring_service import ScoringService, MISSING_SCORE


@pytest.fixture
def service():
    return ScoringService()


def _raw(spec_raw, *, missing=False):
    d = {"spec_raw": spec_raw}
    if missing:
        d["_spec_missing"] = True
    return d


# ---------------------------------------------------------------------------
# A1 default — dampened spread 45..85
# ---------------------------------------------------------------------------

def test_winner_gets_85_not_100(service):
    """The relative winner on a dimension now tops out at ~85, not 100."""
    raw = [_raw(10.0), _raw(5.0)]  # idx0 higher
    s0 = service._normalize_dimension(raw, 0, "spec_raw", higher_better=True)
    assert s0 == pytest.approx(85.0, abs=0.1), f"winner should cap at 85, got {s0}"


def test_loser_gets_45_not_30(service):
    """The relative loser floors at ~45, not 30 — the gap is compressed."""
    raw = [_raw(10.0), _raw(5.0)]
    s1 = service._normalize_dimension(raw, 1, "spec_raw", higher_better=True)
    assert s1 == pytest.approx(45.0, abs=0.1), f"loser should floor at 45, got {s1}"


def test_gap_is_40_not_70(service):
    """The manufactured winner-loser gap is now 40 points, not 70."""
    raw = [_raw(10.0), _raw(5.0)]
    s0 = service._normalize_dimension(raw, 0, "spec_raw", higher_better=True)
    s1 = service._normalize_dimension(raw, 1, "spec_raw", higher_better=True)
    assert abs(s0 - s1) == pytest.approx(40.0, abs=0.2)


def test_midpoint_value_is_mid_band(service):
    """A product exactly halfway between min and max lands mid-band (~65)."""
    raw = [_raw(10.0), _raw(0.0), _raw(5.0)]  # idx2 is the midpoint
    s2 = service._normalize_dimension(raw, 2, "spec_raw", higher_better=True)
    assert s2 == pytest.approx(65.0, abs=0.5)


def test_genuine_tie_returns_band_midpoint(service):
    """The genuine non-missing tie (both sides equal non-zero raw) returns the
    NEW band midpoint (65), not the legacy 70."""
    raw = [_raw(5.0), _raw(5.0)]
    s0 = service._normalize_dimension(raw, 0, "spec_raw", higher_better=True)
    assert s0 == pytest.approx(65.0, abs=0.1)


def test_missing_still_returns_missing_score(service):
    """A1 must NOT disturb the MISSING propagation — both-missing still
    MISSING_SCORE (the B0-A phantom-tie guard is preserved)."""
    raw = [_raw(0.0, missing=True), _raw(0.0, missing=True)]
    s0 = service._normalize_dimension(raw, 0, "spec_raw", higher_better=True)
    assert s0 == MISSING_SCORE


def test_no_signal_zero_returns_missing_score(service):
    """max==min==0 (no signal extracted) still propagates MISSING_SCORE."""
    raw = [_raw(0.0), _raw(0.0)]
    s0 = service._normalize_dimension(raw, 0, "spec_raw", higher_better=True)
    assert s0 == MISSING_SCORE


# ---------------------------------------------------------------------------
# Fallback flag — winner-only dampening (display keeps legacy 30..100)
# ---------------------------------------------------------------------------

def test_fallback_flag_reverts_to_legacy_spread(service, monkeypatch):
    """With DISABLE_DIM_NORM_DAMPENING on, _normalize_dimension reverts to the
    legacy 30..100 spread (escape hatch for keeping the dramatic bars)."""
    monkeypatch.setenv("DISABLE_DIM_NORM_DAMPENING", "true")
    raw = [_raw(10.0), _raw(5.0)]
    s0 = service._normalize_dimension(raw, 0, "spec_raw", higher_better=True)
    s1 = service._normalize_dimension(raw, 1, "spec_raw", higher_better=True)
    # Legacy spread: winner 100, loser 30.
    assert s0 == pytest.approx(100.0, abs=0.1)
    assert s1 == pytest.approx(30.0, abs=0.1)
    # Legacy genuine-tie returns 70.
    raw_tie = [_raw(5.0), _raw(5.0)]
    assert service._normalize_dimension(raw_tie, 0, "spec_raw", higher_better=True) == pytest.approx(70.0, abs=0.1)
