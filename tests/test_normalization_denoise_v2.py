"""S3 L3 v2 — de-noising _normalize_dimension (Ahmed/team-lead 2026-06-13).

Two hatched levers, both deterministic post-data (offline-sweepable, zero Serper):

LEVER 1 — A1 dampening: spread 30+ratio*70 (30–100) → 45+ratio*40 (45–85), tie
  → band midpoint (65). Env DISABLE_DIM_NORM_DAMPENING reverts to legacy.

LEVER 2 — MAGNITUDE-AWARENESS (the real fix): _normalize_dimension mapped
  DIRECTION to the full range and ignored MAGNITUDE — relative min/max on a
  2-product pair gave the higher value the ceiling + the lower the floor by ANY
  margin (a +0.02% product → a 40pt lead). The relative-gap tolerance fixes it:
    gap = |hi − lo| / hi
    gap <= WINNER_DIM_GAP_TOLERANCE  → both ~tied (band midpoint)
    gap >  tolerance                 → lead opens, scaled by the EXCESS gap
                                       (gap−tol)/(1−tol), smoothly (no cliff).
  So a 1.1% battery gap → ~tie; a 20% gap → a real swing.

Default config (sweep-tunable): dampened band 45–85 + gap tolerance ~0.08.
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
# LEVER 2 — magnitude awareness: tiny gap => ~tie, not a landslide
# ---------------------------------------------------------------------------

def test_tiny_relative_gap_is_near_tie(service):
    """A ~1.1% raw gap (4550 vs 4500) → both near the band midpoint (65), NOT a
    40-point swing. This is the core de-noising property."""
    raw = [_raw(4550.0), _raw(4500.0)]
    s0 = service._normalize_dimension(raw, 0, "spec_raw", higher_better=True)
    s1 = service._normalize_dimension(raw, 1, "spec_raw", higher_better=True)
    # Within ~5 points of each other AND both near the midpoint.
    assert abs(s0 - s1) <= 6.0, f"tiny gap should be ~tie, got {s0} vs {s1}"
    assert 60 <= s0 <= 70 and 60 <= s1 <= 70, f"both near midpoint, got {s0}/{s1}"


def test_meaningful_gap_opens_a_real_lead(service):
    """A large gap (12 vs 6 = 50% relative) opens a genuine, clear lead — winner
    well above the loser (>=15pt, distinct from the ~tie zone <=6pt)."""
    raw = [_raw(12.0), _raw(6.0)]
    s0 = service._normalize_dimension(raw, 0, "spec_raw", higher_better=True)
    s1 = service._normalize_dimension(raw, 1, "spec_raw", higher_better=True)
    assert s0 - s1 >= 15.0, f"a 50% gap should open a clear lead, got {s0} vs {s1}"
    # A near-maximal gap (100 vs 1 = 99%) should approach the full band.
    raw_max = [_raw(100.0), _raw(1.0)]
    s0m = service._normalize_dimension(raw_max, 0, "spec_raw", higher_better=True)
    s1m = service._normalize_dimension(raw_max, 1, "spec_raw", higher_better=True)
    assert s0m - s1m >= 35.0, f"a 99% gap should open near-full band, got {s0m} vs {s1m}"


def test_moderate_gap_scales_between(service):
    """A moderate gap sits between tiny and large — monotonic in gap size."""
    tiny = [_raw(101.0), _raw(100.0)]      # 1%
    moderate = [_raw(120.0), _raw(100.0)]  # ~17%
    large = [_raw(200.0), _raw(100.0)]     # 50%
    g_tiny = abs(service._normalize_dimension(tiny, 0, "spec_raw") - service._normalize_dimension(tiny, 1, "spec_raw"))
    g_mod = abs(service._normalize_dimension(moderate, 0, "spec_raw") - service._normalize_dimension(moderate, 1, "spec_raw"))
    g_large = abs(service._normalize_dimension(large, 0, "spec_raw") - service._normalize_dimension(large, 1, "spec_raw"))
    assert g_tiny < g_mod < g_large, f"lead must grow with gap: {g_tiny} < {g_mod} < {g_large}"


# ---------------------------------------------------------------------------
# LEVER 1 — dampened band bounds (when a real lead opens)
# ---------------------------------------------------------------------------

def test_winner_caps_in_dampened_band(service):
    """A decisive winner tops out at ~85 (dampened ceiling), not 100."""
    raw = [_raw(100.0), _raw(1.0)]
    s0 = service._normalize_dimension(raw, 0, "spec_raw", higher_better=True)
    assert s0 <= 85.5, f"dampened ceiling ~85, got {s0}"


def test_loser_floors_in_dampened_band(service):
    """A decisive loser floors at ~45 (dampened floor), not 30."""
    raw = [_raw(100.0), _raw(1.0)]
    s1 = service._normalize_dimension(raw, 1, "spec_raw", higher_better=True)
    assert 44.5 <= s1 <= 46.0, f"dampened floor ~45, got {s1}"


# ---------------------------------------------------------------------------
# Invariants preserved — MISSING propagation untouched
# ---------------------------------------------------------------------------

def test_both_missing_still_missing_score(service):
    raw = [_raw(0.0, missing=True), _raw(0.0, missing=True)]
    assert service._normalize_dimension(raw, 0, "spec_raw") == MISSING_SCORE


def test_no_signal_zero_still_missing_score(service):
    raw = [_raw(0.0), _raw(0.0)]
    assert service._normalize_dimension(raw, 0, "spec_raw") == MISSING_SCORE


def test_genuine_exact_tie_is_midpoint(service):
    """Exactly-equal non-zero values → band midpoint (not MISSING)."""
    raw = [_raw(5.0), _raw(5.0)]
    assert service._normalize_dimension(raw, 0, "spec_raw") == pytest.approx(65.0, abs=0.5)


# ---------------------------------------------------------------------------
# Hatches — sweep knobs work
# ---------------------------------------------------------------------------

def test_gap_tolerance_hatch_widens_tie_zone(service, monkeypatch):
    """Raising WINNER_DIM_GAP_TOLERANCE makes a larger gap still read as ~tie."""
    raw = [_raw(115.0), _raw(100.0)]  # 13% gap
    monkeypatch.setenv("WINNER_DIM_GAP_TOLERANCE", "0.30")  # 30% tolerance
    s0 = service._normalize_dimension(raw, 0, "spec_raw")
    s1 = service._normalize_dimension(raw, 1, "spec_raw")
    assert abs(s0 - s1) <= 6.0, f"13% gap under 30% tolerance should be ~tie, got {s0}/{s1}"


def test_dampening_disable_hatch_restores_legacy_spread(service, monkeypatch):
    """DISABLE_DIM_NORM_DAMPENING reverts to the legacy 30–100 spread + 70 tie
    AND turns off magnitude-awareness (full legacy behavior)."""
    monkeypatch.setenv("DISABLE_DIM_NORM_DAMPENING", "true")
    raw = [_raw(100.0), _raw(1.0)]
    assert service._normalize_dimension(raw, 0, "spec_raw") == pytest.approx(100.0, abs=0.1)
    assert service._normalize_dimension(raw, 1, "spec_raw") == pytest.approx(30.0, abs=0.1)
    raw_tie = [_raw(5.0), _raw(5.0)]
    assert service._normalize_dimension(raw_tie, 0, "spec_raw") == pytest.approx(70.0, abs=0.1)
