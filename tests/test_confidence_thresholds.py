"""Bundle C — confidence threshold RED tests (Section C plan, tasks C.6.1 / C.6.2).

Covers spec § 5a — threshold loosening:
  - `rating_strong` drops `verified=True` requirement; new rule: review_count >= 100.
  - `price_strong` drops `method != "estimated"` blocker IF at least one product's
    `source_method` is in trust set OR shopping_count >= 3.
  - `specs_strong` lowers `verified_pct >= 60` to `verified_pct >= 40`
    OR `citation_count >= 8`.
  - Overall threshold unchanged (3 strong = high, 2 = medium, ≤1 = low).

RED until A.7.1 loosens thresholds in `scoring_service.compute_confidence`.
"""
from __future__ import annotations

import pytest


def _compute_confidence(*args, **kwargs):
    """Lazy import of compute_confidence so file collects pre-impl."""
    try:
        from app.services.scoring_service import compute_confidence  # type: ignore
    except ImportError:
        pytest.fail(
            "RED: compute_confidence not exposed from scoring_service — A.7.1 pending"
        )
        raise
    return compute_confidence(*args, **kwargs)


# ---------------------------------------------------------------------------
# C.6.1 — Loosened thresholds (spec § 5a)
# ---------------------------------------------------------------------------


def test_rating_strong_at_review_count_100_even_unverified():
    """Spec § 5a: rating_strong drops verified=True requirement.
    New rule: review_count >= 100. 1200 aggregated reviews IS strong signal
    even when rating_verified is False.
    """
    products = [{"review_count": 120, "rating_verified": False}]
    conf = _compute_confidence(products)
    # legs.reviews must be 'strong' even without verification
    assert conf.get("legs", {}).get("reviews") == "strong"


def test_rating_below_100_is_not_strong():
    """50 reviews even verified → not strong (acceptable or weak)."""
    products = [{"review_count": 50, "rating_verified": True}]
    conf = _compute_confidence(products)
    assert conf.get("legs", {}).get("reviews") in {"acceptable", "weak"}


def test_price_strong_when_one_product_estimated_other_real():
    """Spec § 5a: price_strong accepts shopping_count >= 3 even when one
    product is estimated (real Serper coverage is strong signal)."""
    products = [
        {"price": {"source_method": "page_scrape"}, "shopping_count": 5},
        {"price": {"source_method": "estimated"}, "shopping_count": 0},
    ]
    conf = _compute_confidence(products)
    assert conf.get("legs", {}).get("price") == "strong"


def test_price_strong_when_official_brand_method_present():
    """Spec § 5a: price_strong accepts when any product has source_method
    in trust set, even if other is estimated."""
    products = [
        {"price": {"source_method": "official_brand"}, "shopping_count": 1},
        {"price": {"source_method": "estimated"}, "shopping_count": 0},
    ]
    conf = _compute_confidence(products)
    assert conf.get("legs", {}).get("price") == "strong"


def test_specs_strong_via_citation_count_alone():
    """Spec § 5a: specs_strong fires at citation_count >= 8 OR verified_pct >= 40."""
    products = [{"fact_check": {"citation_count": 9, "verified_pct": 20}}]
    conf = _compute_confidence(products)
    assert conf.get("legs", {}).get("specs") == "strong"


def test_specs_strong_at_verified_pct_40():
    """Spec § 5a: 40% verified is the new strong threshold (was 60%)."""
    products = [{"fact_check": {"verified_pct": 45, "citation_count": 2}}]
    conf = _compute_confidence(products)
    assert conf.get("legs", {}).get("specs") == "strong"


def test_specs_below_thresholds_not_strong():
    """6 citations + 30% verified → not strong (acceptable or weak)."""
    products = [{"fact_check": {"citation_count": 6, "verified_pct": 30}}]
    conf = _compute_confidence(products)
    assert conf.get("legs", {}).get("specs") in {"acceptable", "weak"}


def test_overall_threshold_unchanged_high_when_3_strong():
    """Spec § 5a: overall threshold unchanged — 3 strong legs → high."""
    products = [
        {
            "review_count": 200,
            "rating_verified": False,
            "fact_check": {"verified_pct": 50, "citation_count": 10},
            "price": {"source_method": "page_scrape"},
            "shopping_count": 5,
        },
    ]
    conf = _compute_confidence(products)
    assert conf.get("overall") == "high"


def test_overall_threshold_low_when_zero_or_one_strong():
    """≤1 strong leg → low."""
    products = [
        {
            "review_count": 5,
            "rating_verified": False,
            "fact_check": {"verified_pct": 5, "citation_count": 0},
            "price": {"source_method": "estimated"},
            "shopping_count": 0,
        },
    ]
    conf = _compute_confidence(products)
    assert conf.get("overall") == "low"


# ---------------------------------------------------------------------------
# C.6.2 — 3-leg pill computation (spec § 5b/5d)
# ---------------------------------------------------------------------------


def test_compute_confidence_returns_three_legs_dict():
    """Spec § 5b: response payload has price/reviews/specs legs with strength enum."""
    products = [
        {
            "review_count": 100,
            "rating_verified": False,
            "fact_check": {"verified_pct": 45, "citation_count": 9},
            "price": {"source_method": "page_scrape"},
            "shopping_count": 5,
        },
    ]
    conf = _compute_confidence(products)
    assert "legs" in conf, f"conf missing 'legs' key: {conf!r}"
    assert set(conf["legs"].keys()) == {"price", "reviews", "specs"}
    for leg_name, leg_value in conf["legs"].items():
        assert leg_value in {"strong", "acceptable", "weak"}, (
            f"leg {leg_name} has invalid value {leg_value!r}"
        )


def test_legacy_overall_field_kept_for_backwards_compat():
    """Spec § 5d: legacy `overall: 'low'/'medium'/'high'` field stays for
    backwards-compat. Frontend doesn't render it (3 pills tell the story
    together) but it must still serialize.
    """
    products = [
        {
            "review_count": 5,
            "fact_check": {},
            "price": {"source_method": "estimated"},
            "shopping_count": 0,
        },
    ]
    conf = _compute_confidence(products)
    assert "overall" in conf
    assert conf["overall"] in {"high", "medium", "low"}


# ---------------------------------------------------------------------------
# Issue #109 — wire fact_check verification into the confidence pills
# (ENABLE_CONFIDENCE_FACTCHECK_WIRING, default OFF)
# ---------------------------------------------------------------------------


def _flag_on(monkeypatch):
    monkeypatch.setenv("ENABLE_CONFIDENCE_FACTCHECK_WIRING", "true")


def _flag_off(monkeypatch):
    monkeypatch.delenv("ENABLE_CONFIDENCE_FACTCHECK_WIRING", raising=False)


def test_specs_leg_weak_when_all_fields_unverified(monkeypatch):
    """Flag ON: 11 unverified fields are ZERO citations, not 11 — reproduces
    recorded row 289eb5e9 which rendered specs 'strong' at 0% verified."""
    _flag_on(monkeypatch)
    products = [{
        "shopping_count": 0,
        "fact_check": {"specs_verified": 0, "specs_likely": 0,
                       "specs_unverified": 11, "specs_flagged": 0},
    }]
    conf = _compute_confidence(products)
    assert conf["legs"]["specs"] == "weak"


def test_specs_leg_acceptable_at_four_real_citations(monkeypatch):
    """verified_pct = round(2/11*100) = 18 < 20, but 2+2 = 4 real citations."""
    _flag_on(monkeypatch)
    products = [{
        "shopping_count": 0,
        "fact_check": {"specs_verified": 2, "specs_likely": 2,
                       "specs_unverified": 7, "specs_flagged": 0},
    }]
    conf = _compute_confidence(products)
    assert conf["legs"]["specs"] == "acceptable"


def test_specs_leg_strong_at_eight_real_citations(monkeypatch):
    """Pin: verified work is still rewarded (8 verified => strong)."""
    _flag_on(monkeypatch)
    products = [{
        "shopping_count": 0,
        "fact_check": {"specs_verified": 8, "specs_likely": 0,
                       "specs_unverified": 3, "specs_flagged": 0},
    }]
    conf = _compute_confidence(products)
    assert conf["legs"]["specs"] == "strong"


def test_flagged_fields_do_not_count_as_citations(monkeypatch):
    _flag_on(monkeypatch)
    products = [{
        "shopping_count": 0,
        "fact_check": {"specs_verified": 0, "specs_likely": 0,
                       "specs_unverified": 0, "specs_flagged": 6},
    }]
    conf = _compute_confidence(products)
    assert conf["legs"]["specs"] == "weak"


def test_price_leg_demoted_when_fact_check_contradicts(monkeypatch):
    """Flag ON: a product whose own fact-check recorded price_verified=False
    at >=30% deviation cannot render a STRONG price pill — reproduces
    recorded row 2bf16403 (strong pill at 75.6% deviation)."""
    _flag_on(monkeypatch)
    products = [{
        "price": {"source_method": "page_scrape"},
        "shopping_count": 0,
        "fact_check": {"price_verified": False, "price_deviation_pct": 75.6},
    }]
    conf = _compute_confidence(products)
    assert conf["legs"]["price"] == "acceptable"


def test_price_leg_not_demoted_on_unknown_verdict(monkeypatch):
    """The #106 None verdict is UNKNOWN, not contradiction — requires an
    explicit `is False` identity test, never a falsy test."""
    _flag_on(monkeypatch)
    products = [{
        "price": {"source_method": "page_scrape"},
        "shopping_count": 0,
        "fact_check": {"price_verified": None, "price_deviation_pct": None},
    }]
    conf = _compute_confidence(products)
    assert conf["legs"]["price"] == "strong"


def test_price_leg_not_demoted_on_small_deviation(monkeypatch):
    _flag_on(monkeypatch)
    products = [{
        "price": {"source_method": "page_scrape"},
        "shopping_count": 0,
        "fact_check": {"price_verified": False, "price_deviation_pct": 12.0},
    }]
    conf = _compute_confidence(products)
    assert conf["legs"]["price"] == "strong"


def test_price_leg_not_demoted_when_no_deviation_available(monkeypatch):
    """price_verified False with NO comparable rows is absence of evidence,
    not contradiction — must not demote."""
    _flag_on(monkeypatch)
    products = [{
        "price": {"source_method": "page_scrape"},
        "shopping_count": 0,
        "fact_check": {"price_verified": False, "price_deviation_pct": None},
    }]
    conf = _compute_confidence(products)
    assert conf["legs"]["price"] == "strong"


def test_overall_recomputed_from_demoted_legs(monkeypatch):
    """Reviews strong + specs strong + price demoted => 2 strong => medium."""
    _flag_on(monkeypatch)
    products = [{
        "review_count": 120,
        "price": {"source_method": "page_scrape"},
        "shopping_count": 0,
        "fact_check": {"specs_verified": 8, "specs_likely": 0,
                       "specs_unverified": 3, "specs_flagged": 0,
                       "price_verified": False, "price_deviation_pct": 75.6},
    }]
    conf = _compute_confidence(products)
    assert conf["overall"] == "medium"


@pytest.mark.parametrize("products,expected", [
    (  # inputs of case 1
        [{"shopping_count": 0,
          "fact_check": {"specs_verified": 0, "specs_likely": 0,
                         "specs_unverified": 11, "specs_flagged": 0}}],
        {"legs": {"price": "weak", "reviews": "weak", "specs": "strong"},
         "overall": "low",
         "price": {"source_count": 0, "method": "estimated", "freshness": "live"},
         "rating": {"review_count": 0, "source": None, "verified": False},
         "specs": {"verified_pct": 0, "citation_count": 11}},
    ),
    (  # inputs of case 4
        [{"shopping_count": 0,
          "fact_check": {"specs_verified": 0, "specs_likely": 0,
                         "specs_unverified": 0, "specs_flagged": 6}}],
        {"legs": {"price": "weak", "reviews": "weak", "specs": "acceptable"},
         "overall": "low",
         "price": {"source_count": 0, "method": "estimated", "freshness": "live"},
         "rating": {"review_count": 0, "source": None, "verified": False},
         "specs": {"verified_pct": 0, "citation_count": 6}},
    ),
    (  # inputs of case 5
        [{"price": {"source_method": "page_scrape"}, "shopping_count": 0,
          "fact_check": {"price_verified": False, "price_deviation_pct": 75.6}}],
        {"legs": {"price": "strong", "reviews": "weak", "specs": "weak"},
         "overall": "low",
         "price": {"source_count": 0, "method": "retailer_verified", "freshness": "live"},
         "rating": {"review_count": 0, "source": None, "verified": False},
         "specs": {"verified_pct": 0, "citation_count": 0}},
    ),
    (  # inputs of case 9
        [{"review_count": 120,
          "price": {"source_method": "page_scrape"}, "shopping_count": 0,
          "fact_check": {"specs_verified": 8, "specs_likely": 0,
                         "specs_unverified": 3, "specs_flagged": 0,
                         "price_verified": False, "price_deviation_pct": 75.6}}],
        {"legs": {"price": "strong", "reviews": "strong", "specs": "strong"},
         "overall": "high",
         "price": {"source_count": 0, "method": "retailer_verified", "freshness": "live"},
         "rating": {"review_count": 120, "source": None, "verified": False},
         "specs": {"verified_pct": 73, "citation_count": 11}},
    ),
])
def test_flag_off_byte_identical(monkeypatch, products, expected):
    """REQUIRED flag-OFF identity pin: with the flag unset, compute_confidence
    reproduces the pre-change literal dict for every input (captured at
    f2481b9)."""
    _flag_off(monkeypatch)
    conf = _compute_confidence(products)
    assert conf == expected
