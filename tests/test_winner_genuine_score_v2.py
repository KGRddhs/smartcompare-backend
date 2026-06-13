"""S3 L3 v2 — GENUINE WINNER FROM SCORE (Ahmed pivot 2026-06-13).

The winner EMERGES from the genuine overall score, NOT a winner_index flip.
v1's A2 / estimate-demotion / tie-break index-overrides are DROPPED. Replaced
by SCORE FACTORS applied to each product's `overall` BEFORE the argmax, so
"facts beat estimates" + the pick are visible + consistent in rings/verdict/
share/eval (frontend already argmaxes scoring_v2.overall_score).

(a) PRICE-AUTHORITY AS A SCORE FACTOR (not a flip):
    - real BH price (_PRICE_TRUST_SET): no penalty (the honest score stands)
    - estimate: a modest PENALTY (the uncertain score is discounted)
    - converted_usd: a smaller penalty (not local data, but not fabricated)
    Magnitude (WINNER_PRICE_AUTHORITY_POINTS, default ~4) sized SMALLER than a
    decisive signal lead — a clearly-better estimated product still wins; only
    genuine close calls tip to the real-priced side.

The winner is then argmax(adjusted overall) — no override anywhere.
"""
import pytest

from app.services import scoring_service
from app.services.scoring_service import ScoringService


@pytest.fixture
def service():
    return ScoringService()


def _elec(name, *, amount, source_method, rating, review_count, specs,
          fact_check=None):
    return {
        "name": name, "category": "electronics",
        "specs": specs, "rating": rating, "review_count": review_count,
        "price": {"amount": amount, "currency": "BHD", "source_method": source_method},
        "fact_check": fact_check if fact_check is not None else {"specs_verified": 4},
    }


# ---------------------------------------------------------------------------
# (a) price-authority is a SCORE factor — discounts the estimate
# ---------------------------------------------------------------------------

def test_estimate_penalty_lowers_that_products_overall(service):
    """Two otherwise-identical products; product_1 estimated → its `overall`
    is penalized relative to product_0 (real). The penalty lives IN the score."""
    shared = dict(rating=4.4, review_count=600,
                  specs={"ram": "8 GB", "storage": "256 GB", "battery": "4500 mAh"},
                  fact_check={"specs_verified": 3})
    p0 = _elec("Real", amount=300, source_method="local_bhd", **shared)
    p1 = _elec("Est", amount=300, source_method="estimated", **shared)
    r = service.compute_scores([p0, p1])
    o0 = r["scores"]["product_0"]["overall"]
    o1 = r["scores"]["product_1"]["overall"]
    assert o0 > o1, "the estimated product's overall must be discounted below the real one"


def test_shopify_json_is_real_price_not_penalized(service):
    """S3 merge (v2×L1) regression: L1's Shopify direct-discovery emits a real,
    currency-verified BHD price as source_method='shopify_json'. v2's price-
    authority MUST treat it as real (0 penalty, == local_bhd), NEVER estimate-
    grade — else a genuine BH Shopify price is penalised, inverting L1's purpose."""
    shared = dict(rating=4.4, review_count=600,
                  specs={"ram": "8 GB", "storage": "256 GB", "battery": "4500 mAh"},
                  fact_check={"specs_verified": 3})
    # shopify_json vs local_bhd, otherwise identical → equal overall (both real).
    o_shopify = service.compute_scores([
        _elec("Shop", amount=300, source_method="shopify_json", **shared),
        _elec("X", amount=300, source_method="local_bhd", **shared),
    ])["scores"]["product_0"]["overall"]
    o_local = service.compute_scores([
        _elec("Loc", amount=300, source_method="local_bhd", **shared),
        _elec("X", amount=300, source_method="local_bhd", **shared),
    ])["scores"]["product_0"]["overall"]
    assert o_shopify == o_local, (
        f"a real BH shopify_json price must score == local_bhd (no penalty); "
        f"got shopify={o_shopify} vs local={o_local}")
    # shopify_json must beat an otherwise-identical estimate (real beats estimate).
    r = service.compute_scores([
        _elec("Shop", amount=300, source_method="shopify_json", **shared),
        _elec("Est", amount=300, source_method="estimated", **shared),
    ])
    assert r["scores"]["product_0"]["overall"] > r["scores"]["product_1"]["overall"], \
        "a real BH shopify_json price must out-score an estimate"


def test_close_call_tips_to_real_price(service):
    """Genuine close call: identical specs (so no normalization-amplified spec
    lead), the real-priced product slightly better rated. Without authority the
    cheaper estimate would edge it on value; the estimate penalty tips this
    genuine near-tie to the real-priced product."""
    p0 = _elec("Est", amount=300, source_method="estimated",
               rating=4.4, review_count=600,
               specs={"ram": "8 GB", "storage": "256 GB", "battery": "4500 mAh"})
    p1 = _elec("Real", amount=300, source_method="local_bhd",
               rating=4.5, review_count=650,
               specs={"ram": "8 GB", "storage": "256 GB", "battery": "4500 mAh"})
    r = service.compute_scores([p0, p1])
    assert r["winner_index"] == 1, "a close call must tip to the real-priced product"


def test_decisively_better_estimate_still_wins(service):
    """An estimated product that is DECISIVELY better on real signal (specs +
    reviews) still wins — the authority penalty is smaller than a real lead.
    Kills the v1 estimate-demotion over-fire."""
    strong_est = _elec(
        "StrongEst", amount=500, source_method="estimated",
        rating=4.9, review_count=8000,
        specs={"ram": "16 GB", "storage": "1024 GB", "battery": "6000 mAh",
               "rear_camera": "200 MP", "front_camera": "32 MP"},
        fact_check={"specs_verified": 5, "review_sentiment_consistent": True},
    )
    weak_real = _elec(
        "WeakReal", amount=500, source_method="local_bhd",
        rating=3.1, review_count=20,
        specs={"ram": "4 GB", "storage": "64 GB"},
        fact_check={"specs_verified": 1, "specs_unverified": 4},
    )
    r = service.compute_scores([strong_est, weak_real])
    assert r["winner_index"] == 0, "a decisively-better estimate must still win"


def test_both_real_no_relative_penalty(service):
    """Both real-priced → the authority factor doesn't discriminate; winner is
    the genuine signal argmax (here product_0 leads on specs)."""
    p0 = _elec("RealStrong", amount=300, source_method="local_bhd",
               rating=4.6, review_count=1500,
               specs={"ram": "12 GB", "storage": "512 GB", "battery": "5000 mAh"})
    p1 = _elec("RealWeak", amount=305, source_method="page_scrape",
               rating=4.3, review_count=800,
               specs={"ram": "8 GB", "storage": "256 GB", "battery": "4000 mAh"})
    r = service.compute_scores([p0, p1])
    assert r["winner_index"] == 0


def test_converted_usd_smaller_penalty_than_estimate(service):
    """converted_usd gets a SMALLER penalty than a raw estimate (it's not local
    data, but it's a real converted figure, not fabricated). So a converted_usd
    product's overall sits between a real and an estimated equivalent."""
    shared = dict(rating=4.4, review_count=600,
                  specs={"ram": "8 GB", "storage": "256 GB"})
    real = service.compute_scores([
        _elec("R", amount=300, source_method="local_bhd", **shared),
        _elec("X", amount=300, source_method="local_bhd", **shared)])["scores"]["product_0"]["overall"]
    conv = service.compute_scores([
        _elec("C", amount=300, source_method="converted_usd", **shared),
        _elec("X", amount=300, source_method="local_bhd", **shared)])["scores"]["product_0"]["overall"]
    est = service.compute_scores([
        _elec("E", amount=300, source_method="estimated", **shared),
        _elec("X", amount=300, source_method="local_bhd", **shared)])["scores"]["product_0"]["overall"]
    assert real >= conv >= est, f"expected real>=converted>=estimated, got {real}/{conv}/{est}"


# ---------------------------------------------------------------------------
# (b) lever 1 — value = value-FOR-MONEY (what-you-get > how-cheap)
# ---------------------------------------------------------------------------

def test_value_for_money_default_coeff_favors_spec():
    """The default value-formula coefficients reward SPEC (what you get) over
    PRICE (how cheap): spec >= 0.70, price <= 0.30 — so a marginally-cheaper
    product with equal specs no longer dominates the value dim."""
    from app.services.scoring_service import VALUE_FORMULA_BY_PRIORITY
    d = VALUE_FORMULA_BY_PRIORITY["_default"]
    assert d["spec"] >= 0.70, f"value-for-money: spec coeff should be >=0.70, got {d['spec']}"
    assert d["price"] <= 0.30, f"value-for-money: price coeff should be <=0.30, got {d['price']}"
    assert abs(d["spec"] + d["price"] - 1.0) < 1e-9, "coeffs must sum to 1.0"


# ---------------------------------------------------------------------------
# Winner is a plain argmax — no flip overrides, no v1 markers
# ---------------------------------------------------------------------------

def test_no_v1_flip_markers_in_result(service):
    """The v1 winner_value_neutralized marker is GONE — the winner is the
    genuine score argmax, nothing to mark."""
    p0 = _elec("A", amount=300, source_method="local_bhd", rating=4.5,
               review_count=900, specs={"ram": "8 GB", "storage": "256 GB"})
    p1 = _elec("B", amount=305, source_method="local_bhd", rating=4.4,
               review_count=800, specs={"ram": "8 GB", "storage": "256 GB"})
    r = service.compute_scores([p0, p1])
    assert "winner_value_neutralized" not in r


def test_winner_index_is_argmax_of_overall(service):
    """Invariant: winner_index == argmax(scores.product_i.overall) ALWAYS —
    the frontend's argmax(scoring_v2.overall_score) then agrees automatically."""
    for seed in [
        (_elec("A", amount=120, source_method="local_bhd", rating=4.7, review_count=2000,
               specs={"ram": "12 GB", "storage": "512 GB"}),
         _elec("B", amount=900, source_method="estimated", rating=4.2, review_count=300,
               specs={"ram": "8 GB", "storage": "256 GB"})),
        (_elec("C", amount=500, source_method="estimated", rating=4.9, review_count=9000,
               specs={"ram": "16 GB", "storage": "1024 GB", "rear_camera": "200 MP"}),
         _elec("D", amount=480, source_method="local_bhd", rating=3.5, review_count=50,
               specs={"ram": "6 GB", "storage": "128 GB"})),
    ]:
        r = service.compute_scores(list(seed))
        o0 = r["scores"]["product_0"]["overall"]
        o1 = r["scores"]["product_1"]["overall"]
        expected = 0 if o0 >= o1 else 1
        assert r["winner_index"] == expected, (
            f"winner_index {r['winner_index']} != argmax of overall ({o0},{o1})"
        )
