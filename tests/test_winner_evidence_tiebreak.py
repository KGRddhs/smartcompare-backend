"""S3 L3.2 — Bahrain-availability + price-authority into the winner pick.

The S2 full-200 audit (L3.1) showed the winner axis at .495 — BELOW the
always-pick-product_0 baseline (.655) — because `compute_scores`'
`winner_index = overalls.index(max(overalls))` is a pure argmax with no
tie-break: when the two weighted overalls land in a narrow band (common when
both products carry sparse/MISSING signals), the `.index(max())` call silently
returns product_0. That product_0 bias is noise, not signal.

L3.2 adds an EVIDENCE-WEIGHTED tie-break (NOT a fabricated score): when the
overalls are within a tie band AND exactly one product has a real Bahrain
price (`source_method` in the trust set, i.e. NOT 'estimated'/'converted_usd'),
the winner tilts to the real-data product and a `winner_evidence` reason is
emitted. Hard guards (F2.4 lesson):
  - both products MISSING-only  -> NO fabricated tilt (defer to argmax; the
    orchestrator returns INSUFFICIENT_DATA upstream anyway).
  - decisive margin (> tie band) -> argmax stands untouched (real data already
    drove the score; we never override a genuine signal lead).
  - neither OR both have real prices -> no tilt (no discriminating evidence).

Determinism + order-independence: swapping product_0/product_1 must produce the
mirror winner (no residual first-index bias).
"""
import pytest

from app.services import scoring_service
from app.services.scoring_service import ScoringService, MISSING_SCORE


@pytest.fixture
def service():
    return ScoringService()


def _elec(name, *, price_amount, source_method, specs=None, rating=None,
          review_count=None, fact_check=None):
    """Electronics product with a controllable price.source_method."""
    return {
        "name": name,
        "category": "electronics",
        "specs": specs if specs is not None else {
            "ram": "8 GB", "storage": "256 GB", "battery": "4000 mAh",
            "rear_camera": "48 MP", "front_camera": "12 MP",
        },
        "rating": rating,
        "review_count": review_count,
        "price": {"amount": price_amount, "currency": "BHD",
                  "source_method": source_method},
        "fact_check": fact_check,
    }


# ---------------------------------------------------------------------------
# Core L3.2 contract: tie-band + one real price -> tilt to the real-data side
# ---------------------------------------------------------------------------

def test_tie_band_one_real_price_tilts_to_real_data_product(service):
    """Two near-identical products; product_1 has a real BH price (local_bhd),
    product_0 only an estimate. Within the tie band the winner must tilt to
    product_1 (the real-data side) — NOT default to product_0 via argmax."""
    # Identical specs/rating so the weighted overalls land in the tie band.
    shared = dict(specs={"ram": "8 GB", "storage": "256 GB", "battery": "4000 mAh"},
                  rating=4.4, review_count=500,
                  fact_check={"specs_verified": 3, "specs_likely": 1})
    p0 = _elec("Phone Est", price_amount=300, source_method="estimated", **shared)
    p1 = _elec("Phone Real", price_amount=300, source_method="local_bhd", **shared)

    result = service.compute_scores([p0, p1])

    assert result["winner_index"] == 1, (
        "within the tie band, the real-BH-price product must win the tie-break"
    )
    ev = result.get("winner_evidence")
    assert isinstance(ev, list) and ev, "winner_evidence must be a non-empty list"
    # Qualitative only — no coefficients/caps/percentages leaked.
    blob = " ".join(str(e) for e in ev).lower()
    assert any(tok in blob for tok in ("bahrain", "local", "real", "price", "availab")), \
        "evidence should reference the real-price / availability signal"


def test_tie_break_is_order_independent(service):
    """Swapping the two products must mirror the winner — no product_0 bias."""
    shared = dict(specs={"ram": "8 GB", "storage": "256 GB"}, rating=4.3,
                  review_count=400, fact_check={"specs_verified": 2})
    real = _elec("Real", price_amount=320, source_method="page_scrape", **shared)
    est = _elec("Est", price_amount=320, source_method="estimated", **shared)

    r_real_first = service.compute_scores([real, est])
    r_est_first = service.compute_scores([est, real])

    # real-data product wins in BOTH orderings
    assert r_real_first["winner_index"] == 0
    assert r_est_first["winner_index"] == 1


# ---------------------------------------------------------------------------
# Guards: never fabricate a tilt
# ---------------------------------------------------------------------------

def test_decisive_margin_argmax_stands(service):
    """When one product clearly leads on real signal (big spec + rating gap),
    the existing argmax winner must NOT be overridden even if the LOSER has the
    only real price. Real signal lead always beats the tie-break nudge."""
    strong = _elec(
        "Strong", price_amount=500, source_method="estimated",
        specs={"ram": "16 GB", "storage": "1024 GB", "battery": "6000 mAh",
               "rear_camera": "200 MP", "front_camera": "32 MP"},
        rating=4.9, review_count=5000,
        fact_check={"specs_verified": 5, "price_verified": True,
                    "review_sentiment_consistent": True},
    )
    weak_but_real = _elec(
        "WeakReal", price_amount=500, source_method="local_bhd",
        specs={"ram": "4 GB", "storage": "64 GB"},
        rating=3.1, review_count=20,
        fact_check={"specs_verified": 1, "specs_unverified": 4},
    )
    result = service.compute_scores([strong, weak_but_real])
    assert result["winner_index"] == 0, (
        "a decisive real-signal lead must not be overridden by the price-authority "
        "tie-break (that fires only inside the tie band)"
    )


def test_both_missing_no_fabricated_tilt(service):
    """Both products all-MISSING (no specs, no rating, no real price). The
    tie-break must NOT fabricate a winner_evidence tilt — defer to argmax
    (orchestrator returns INSUFFICIENT_DATA upstream anyway)."""
    p0 = _elec("Blank0", price_amount=None, source_method="estimated",
               specs={}, rating=None, review_count=None)
    p1 = _elec("Blank1", price_amount=None, source_method="estimated",
               specs={}, rating=None, review_count=None)
    result = service.compute_scores([p0, p1])
    # No real price on either side -> no tilt, no fabricated evidence.
    assert not result.get("winner_evidence"), (
        "all-MISSING comparison must not emit a price-authority winner_evidence tilt"
    )


def test_neither_real_price_no_tilt_argmax_preserved(service):
    """When BOTH prices are estimates, there's no discriminating price evidence;
    the winner must equal the plain argmax (no tilt) and no price-authority
    evidence is emitted."""
    shared = dict(specs={"ram": "8 GB", "storage": "256 GB"}, rating=4.2,
                  review_count=300, fact_check={"specs_verified": 2})
    p0 = _elec("Est0", price_amount=300, source_method="estimated", **shared)
    p1 = _elec("Est1", price_amount=300, source_method="converted_usd", **shared)
    result = service.compute_scores([p0, p1])
    # converted_usd is NOT in the trust set -> neither side has real BH price.
    assert not result.get("winner_evidence")


def test_both_real_prices_no_tilt(service):
    """Both products have real BH prices -> price authority doesn't discriminate;
    no tilt (argmax stands), no price-authority evidence."""
    shared = dict(specs={"ram": "8 GB", "storage": "256 GB"}, rating=4.2,
                  review_count=300, fact_check={"specs_verified": 2})
    p0 = _elec("Real0", price_amount=300, source_method="local_bhd", **shared)
    p1 = _elec("Real1", price_amount=305, source_method="page_scrape", **shared)
    result = service.compute_scores([p0, p1])
    assert not result.get("winner_evidence")


def test_winner_evidence_has_no_backend_internals(service):
    """winner_evidence must never leak coefficients / cap percentages / raw
    score math (no_backend_internals_in_reveals)."""
    shared = dict(specs={"ram": "8 GB", "storage": "256 GB"}, rating=4.4,
                  review_count=500, fact_check={"specs_verified": 3})
    p0 = _elec("Est", price_amount=300, source_method="estimated", **shared)
    p1 = _elec("Real", price_amount=300, source_method="local_bhd", **shared)
    result = service.compute_scores([p0, p1])
    blob = " ".join(str(e) for e in (result.get("winner_evidence") or [])).lower()
    # No raw coefficient / cap / percent leakage.
    for forbidden in ("0.6", "0.4", "±", "missing_score", "weight", "coefficient",
                      "tie_band", "argmax", "%"):
        assert forbidden not in blob, f"winner_evidence leaked backend internal: {forbidden!r}"
