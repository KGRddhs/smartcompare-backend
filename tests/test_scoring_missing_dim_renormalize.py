"""M20 #101 — stop letting a MISSING signal outscore a measured bad one.

`MISSING_SCORE = 50` is injected into the `overall` roll-up for any dimension a
product has no data for, while a genuinely measured 2.0-star rating normalizes
to 40.0 via `_normalize_review`. The arithmetic consequence is that NO DATA
BEATS BAD DATA: an unrated product outranks an otherwise-identical 2.0-star
product (measured offline on `fragrances`: 51.8 vs 52.5, winner 1).

The fix (issue #101, "Implementation notes" — exclude-and-renormalize, NOT a
clamp): when a dimension's source signal is missing for at least one but not
all products, that dimension is dropped from EVERY product's `overall` and the
remaining weights are renormalized to sum to 1.0. Neither side is rewarded or
punished for the gap. Gated behind `ENABLE_MISSING_DIM_RENORM` (default OFF).

Missingness is read from the EXPLICIT per-dim `_<dim>_missing` flags (surfaced
as `missing_data`), NEVER `== MISSING_SCORE` value-equality — a 2.5-star rating
normalizes to exactly 50.0 and a 0.5 reliability/popularity raw does too. See
tests/test_missing_score_collision_v2.py for that collision.
"""
import json
import os

import pytest

from app.services.scoring_service import (
    ScoringService,
    CATEGORY_DIMENSIONS,
    MISSING_SCORE,
)

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_GOLDEN = os.path.join(
    _REPO_ROOT, "tests", "fixtures", "missing_dim_renorm_flag_off_golden.json"
)

_SPECS = {"longevity": "8 hours", "volume": "100 ml"}


@pytest.fixture
def service():
    return ScoringService()


@pytest.fixture
def renorm_on(monkeypatch):
    """Flag reader is LIVE (env read per call), so setenv is enough — there is
    no module-level cache to reset (unlike `_BUNDLE_C_SCORING_FLAG`)."""
    monkeypatch.setenv("ENABLE_MISSING_DIM_RENORM", "true")
    yield


@pytest.fixture
def renorm_off(monkeypatch):
    monkeypatch.delenv("ENABLE_MISSING_DIM_RENORM", raising=False)
    yield


def _prod(name, *, rating, review_count, fact_check=True, specs=_SPECS,
          price=300, category="fragrances"):
    """Mirrors the `_prod()` shape in tests/test_missing_score_collision_v2.py,
    retargeted at `fragrances` (the category the issue reproduced on)."""
    product = {
        "brand": "House", "name": name, "category": category,
        "specs": dict(specs) if specs is not None else {},
        "rating": rating, "review_count": review_count,
    }
    product["price"] = (
        {"amount": price, "currency": "BHD", "source_method": "local_bhd"}
        if price is not None else {"amount": None, "currency": "BHD"}
    )
    if fact_check:
        product["fact_check"] = {"specs_verified": 3}
    return product


# --- fixture builders -------------------------------------------------------
# Verified offline against dd4c849; the one-sided-dim counts are asserted in
# test_effective_weights_sum_to_one so a drift in the underlying signal map
# fails loudly rather than silently weakening these tests.

def _measured_vs_unrated(rating=2.0):
    """Identical specs, price and fact_check. A has a measured (bad) rating,
    B has none. 3 one-sided dims: longevity / projection / presentation."""
    return [
        _prod("Measured", rating=rating, review_count=300),
        _prod("Unrated", rating=None, review_count=None),
    ]


def _one_excluded_dim():
    """Identical ratings; only B lacks `fact_check` -> reliability one-sided.
    Exactly 1 one-sided dim: versatility_score."""
    return [
        _prod("WithFacts", rating=4.0, review_count=300),
        _prod("NoFacts", rating=4.0, review_count=300, fact_check=False),
    ]


def _both_sided_missing():
    """Neither product has a rating -> the review/popularity/spec_secondary
    gaps are BOTH-sided, so nothing is one-sided and nothing is excluded."""
    return [
        _prod("A", rating=None, review_count=None),
        _prod("B", rating=None, review_count=None),
    ]


def _all_dims_one_sided():
    """A carries every signal, B carries none -> all 6 dims one-sided, so the
    effective-weight total collapses to 0 (the divide-by-zero edge case)."""
    return [
        _prod("Full", rating=4.0, review_count=300,
              specs={"longevity": "10 hours", "volume": "50 ml"}),
        _prod("Empty", rating=None, review_count=None, fact_check=False,
              specs=None, price=None),
    ]


def _one_sided_dims(result, category="fragrances"):
    """Derive the one-sided set from `missing_data` INDEPENDENTLY of the new
    `excluded_dims` key, so tests 3/4 are not circular."""
    dims = CATEGORY_DIMENSIONS[category]
    per_product = [
        set(result["scores"][f"product_{i}"]["missing_data"] or [])
        for i in range(len(result["scores"]))
    ]
    return [
        d for d in dims
        if 0 < sum(1 for md in per_product if d in md) < len(per_product)
    ]


def _expected_renormalized_overall(result, product_key, excluded):
    """Re-derive `overall` by dropping `excluded` from `weights_used`,
    renormalizing the remainder to 1.0 and re-weighting `breakdown`."""
    entry = result["scores"][product_key]
    weights = {k: v for k, v in entry["weights_used"].items() if k not in excluded}
    total = sum(weights.values())
    assert total > 0, "fixture must leave at least one dim in play"
    raw = sum(
        entry["breakdown"].get(dim, MISSING_SCORE) * w / total
        for dim, w in weights.items()
    )
    return round(max(0, min(100, raw)), 1)


# --- 1. the headline inversion ---------------------------------------------

def test_no_rating_does_not_beat_two_star_rating(service, renorm_on):
    """A 2.0-star product must not be outranked by a product with NO rating.

    NOTE on the assertion strength: the issue text predicts a strict `>`, but
    exclude-and-renormalize (the approach the issue's own Implementation notes
    mandate over clamping) removes exactly the dims that differentiate these
    two OTHERWISE-IDENTICAL products, so the correct post-fix result is an
    exact TIE on `overall` with the measured product taking the argmax. `>=`
    plus `winner_index == 0` is the strongest claim exclusion can support here;
    a strict `>` would only be reachable by rewarding measured data, which is
    the mirror-image of the bug. Both halves are RED today (51.8 vs 52.5,
    winner 1).
    """
    result = service.compute_scores(_measured_vs_unrated(rating=2.0))
    measured = result["scores"]["product_0"]["overall"]
    unrated = result["scores"]["product_1"]["overall"]
    assert measured >= unrated, (
        f"unrated product outscored a measured 2.0-star one: {unrated} > {measured}"
    )
    assert result["winner_index"] == 0


def test_one_star_does_not_beat_no_rating(service, renorm_on):
    """Same fixture at 1.0 stars — pins that the fix is EXCLUSION, not a
    partial clamp of the sentinel toward the dampened band floor (a clamp only
    shrinks the inversion; a 1.0-star product would still lose to a void)."""
    result = service.compute_scores(_measured_vs_unrated(rating=1.0))
    measured = result["scores"]["product_0"]["overall"]
    unrated = result["scores"]["product_1"]["overall"]
    assert measured >= unrated, (
        f"unrated product outscored a measured 1.0-star one: {unrated} > {measured}"
    )
    assert result["winner_index"] == 0


# --- 3. the roll-up arithmetic ---------------------------------------------

def test_one_sided_missing_dim_excluded_from_both_overalls(service, renorm_on):
    result = service.compute_scores(_measured_vs_unrated())
    excluded = _one_sided_dims(result)
    assert excluded, "fixture must produce at least one one-sided dim"
    for key in ("product_0", "product_1"):
        assert result["scores"][key]["overall"] == pytest.approx(
            _expected_renormalized_overall(result, key, excluded), abs=0.06
        ), f"{key} overall still includes the one-sided dims {excluded}"


# --- 4. renormalization invariant ------------------------------------------

@pytest.mark.parametrize("builder,expected_excluded", [
    (_one_excluded_dim, 1),
    (_measured_vs_unrated, 3),
])
def test_effective_weights_sum_to_one(service, renorm_on, builder, expected_excluded):
    result = service.compute_scores(builder())
    excluded = _one_sided_dims(result)
    assert len(excluded) == expected_excluded, (
        f"fixture drifted: expected {expected_excluded} one-sided dims, got {excluded}"
    )
    reported = result["scores"]["product_0"].get("excluded_dims")
    assert sorted(reported or []) == sorted(excluded), (
        f"excluded_dims {reported} disagrees with the missing_data-derived set {excluded}"
    )
    weights = result["scores"]["product_0"]["weights_used"]
    total = sum(w for d, w in weights.items() if d not in excluded)
    assert total > 0
    effective = {d: w / total for d, w in weights.items() if d not in excluded}
    assert sum(effective.values()) == pytest.approx(1.0, abs=1e-6)


# --- 5-7. guards ------------------------------------------------------------

def test_both_sided_missing_unchanged(service, monkeypatch):
    """A dim missing on BOTH sides is not one-sided — today's behavior holds."""
    monkeypatch.delenv("ENABLE_MISSING_DIM_RENORM", raising=False)
    baseline = service.compute_scores(_both_sided_missing())
    monkeypatch.setenv("ENABLE_MISSING_DIM_RENORM", "true")
    flagged = service.compute_scores(_both_sided_missing())
    for key in ("product_0", "product_1"):
        assert flagged["scores"][key]["overall"] == baseline["scores"][key]["overall"]
    assert flagged["scores"]["product_0"].get("excluded_dims") is None


def test_all_dims_one_sided_missing_does_not_divide_by_zero(service, monkeypatch):
    """Every dim one-sided -> effective total is 0. Fall back to the legacy
    un-renormalized sum rather than dividing by zero."""
    monkeypatch.delenv("ENABLE_MISSING_DIM_RENORM", raising=False)
    legacy = service.compute_scores(_all_dims_one_sided())
    monkeypatch.setenv("ENABLE_MISSING_DIM_RENORM", "true")
    flagged = service.compute_scores(_all_dims_one_sided())
    for key in ("product_0", "product_1"):
        assert flagged["scores"][key]["overall"] == legacy["scores"][key]["overall"]


def test_two_point_five_star_is_not_treated_as_missing(service, renorm_on):
    """rating 2.5 normalizes to EXACTLY 50.0 (== MISSING_SCORE). The new code
    must read `_<dim>_missing`, never value-equality, so `projection_score`
    (the `review` signal dim for fragrances) is NOT excluded here."""
    result = service.compute_scores([
        _prod("Middling", rating=2.5, review_count=300),
        _prod("Good", rating=4.0, review_count=300),
    ])
    assert result["scores"]["product_0"]["breakdown"]["projection_score"] == 50.0
    for key in ("product_0", "product_1"):
        assert "projection_score" not in (
            result["scores"][key].get("excluded_dims") or []
        ), "a genuine 50.0 was mistaken for the MISSING sentinel"


# --- 8. payload shape -------------------------------------------------------

def test_excluded_dims_key_present_and_shaped_like_missing_data(service, renorm_on):
    """`excluded_dims` mirrors `missing_data`'s shape exactly (list, or None
    when empty) so consumers can branch identically."""
    one_sided = service.compute_scores(_measured_vs_unrated())
    entry = one_sided["scores"]["product_0"]
    assert isinstance(entry["excluded_dims"], list) and entry["excluded_dims"]
    assert all(isinstance(d, str) for d in entry["excluded_dims"])

    nothing_excluded = service.compute_scores(_both_sided_missing())
    assert nothing_excluded["scores"]["product_0"]["excluded_dims"] is None


# --- 9. flag-OFF golden -----------------------------------------------------

def _golden_products(category):
    """MUST mirror tests/fixtures/_gen_missing_dim_renorm_flag_off_golden.py."""
    common_specs = {
        "ram": "8GB", "storage": "256GB", "longevity": "8 hours",
        "volume": "100 ml", "material": "cotton", "protein": "20 g",
    }
    return [
        {
            "brand": "Alpha", "name": "One", "category": category,
            "specs": dict(common_specs),
            "price": {"amount": 300, "currency": "BHD", "source_method": "local_bhd"},
            "rating": 2.0, "review_count": 300,
            "fact_check": {"specs_verified": 3},
        },
        {
            "brand": "Beta", "name": "Two", "category": category,
            "specs": dict(common_specs),
            "price": {"amount": 300, "currency": "BHD", "source_method": "local_bhd"},
            "rating": None, "review_count": None,
        },
    ]


@pytest.mark.parametrize("category", sorted(CATEGORY_DIMENSIONS))
def test_flag_off_matches_recorded_golden(service, renorm_off, category):
    """Flag OFF -> byte-for-byte the dd4c849 (== review base 593ec1e) output.
    This is the mandatory stand-in for scripts/verify_flag_byte_identity.py,
    which covers the price-EXTRACTION path only and does not apply here."""
    with open(_GOLDEN, encoding="utf-8") as fh:
        golden = json.load(fh)
    result = service.compute_scores(_golden_products(category))
    captured = {
        "winner_index": result["winner_index"],
        "win_margin": result["win_margin"],
        "scores": result["scores"],
    }
    assert json.loads(json.dumps(captured, sort_keys=True)) == golden[category]
