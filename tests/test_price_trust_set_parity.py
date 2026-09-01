"""M20 #104 (M18 PO-fact-check-06) — every genuine-BH source method must be
trusted by scoring.

`page_scrape_jsonld` is the stamp of the genuine-price program (a real BHD price
read out of a real Bahrain PDP's JSON-LD). Everywhere else in the codebase it is
treated as genuine — `is_price_showable` via `_showable_source_methods`,
`quality_ranker` rank 85, the 7d genuine cache TTL, the genuine-share KPI — but
`scoring_service._PRICE_TRUST_SET` never learned about it. The result is the
exact inversion the `shopify_json` comment was added to prevent: a genuine
Bahrain scrape takes the FULL estimate-grade authority penalty (−4.0), which is
harsher than a `converted_usd` price (−2.0), renders the price leg weak, and is
never cited in winner evidence.

Structured after `tests/test_eval_genuine_methods_parity.py`. The invariant is a
SUBSET, not equality: the trust set is a scoring concept, and a future
scoring-only member must not force a red test in `price_service`.
"""
import pytest

from app.services.price_service import _GENUINE_BH_SOURCE_METHODS as GENUINE
from app.services.scoring_service import (
    _PRICE_TRUST_SET as TRUST,
    _price_authority_delta,
    _has_real_price,
    compute_confidence,
    build_winner_evidence,
)


def test_every_genuine_bh_method_is_trusted():
    assert GENUINE - TRUST == set(), (
        "genuine-BH source methods are scored as estimates:\n"
        f"  in price_service but NOT in scoring_service: {sorted(GENUINE - TRUST)}"
    )


def test_page_scrape_jsonld_takes_no_authority_penalty():
    assert _price_authority_delta(
        {"price": {"source_method": "page_scrape_jsonld"}}
    ) == 0.0


def test_converted_usd_and_estimated_penalties_unchanged():
    """Green from the start — pins the non-regression. An estimate must still
    score as an estimate, and converted_usd keeps its deliberate half penalty."""
    assert _price_authority_delta({"price": {"source_method": "converted_usd"}}) == -2.0
    assert _price_authority_delta({"price": {"source_method": "estimated"}}) == -4.0
    assert _price_authority_delta({}) == -4.0


def test_sentinel_non_prices_are_not_trusted():
    """`sitemap_no_match` / `validation_rejected` are sentinels, not prices, and
    must keep the full estimate-grade penalty."""
    for method in ("sitemap_no_match", "validation_rejected"):
        assert method not in TRUST
        assert _price_authority_delta({"price": {"source_method": method}}) == -4.0


@pytest.mark.parametrize("method", sorted(GENUINE))
def test_has_real_price_true_for_each_genuine_method(method):
    assert _has_real_price({"price": {"source_method": method}}) is True


def test_price_leg_strong_for_genuine_scrape_without_shopping():
    """Reproduces recorded M18 row 6b8122e5 — BOTH sides page_scrape_jsonld,
    estimated=false, genuine BHD 25.19 / 28.2, price leg rendered WEAK."""
    conf = compute_confidence([
        {"price": {"source_method": "page_scrape_jsonld"}, "shopping_count": 0},
        {"price": {"source_method": "estimated"}, "shopping_count": 0},
    ])
    assert conf["legs"]["price"] == "strong"


def test_winner_evidence_cites_confirmed_bahrain_price():
    reasons = build_winner_evidence(
        [
            {"brand": "X", "name": "A", "price": {"source_method": "page_scrape_jsonld"}},
            {"brand": "Y", "name": "B", "price": {"source_method": "estimated"}},
        ],
        {},
        0,
        "electronics",
    )
    assert any("confirmed Bahrain price" in r for r in reasons), reasons
