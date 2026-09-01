"""Pins scoring's price-trust set as a SUPERSET of the backend's genuine-BH set.

M18 review, finding PO-fact-check-06: `scoring_service._PRICE_TRUST_SET` had
drifted from `price_service._GENUINE_BH_SOURCE_METHODS` — eight genuine stamps
(`page_scrape_jsonld`, `firecrawl_brand_domain`, `woo_store_api`, `salla_api`,
`occ_rest_bhd`, `magento_graphql_bhd`, `rest_json_bhd`, `zyte_render_bhd`) were
missing, so a REAL Bahrain price read out of a real Bahrain PDP took the full
estimate-grade authority penalty (-4.0, harder than `converted_usd`'s -2.0),
rendered the price confidence leg `weak`, and could never be cited in winner
evidence. Every other consumer (7d genuine TTL, `_showable_source_methods`,
`quality_ranker`, the eval genuine-share KPI) already trusted all eight.

Direction of the invariant is deliberate: GENUINE - TRUST must be empty (every
genuine stamp is trusted), but TRUST may legitimately grow beyond GENUINE — the
trust set is a SCORING concept and a future scoring-only member must not turn
`price_service` red.

The literals are duplicated rather than imported into `scoring_service`
(`price_service` already lazy-imports back into `scoring_service`, so a
module-level import in the other direction would make that coupling load-bearing
at import time). This file is the parity pin, mirroring the pattern of
`tests/test_eval_genuine_methods_parity.py`.
"""
import pytest

from app.services.price_service import _GENUINE_BH_SOURCE_METHODS as GENUINE
from app.services.scoring_service import (
    _PRICE_TRUST_SET as TRUST,
    _has_real_price,
    _price_authority_delta,
    build_winner_evidence,
    compute_confidence,
)


def test_every_genuine_bh_method_is_trusted():
    assert GENUINE - TRUST == set(), (
        "scoring _PRICE_TRUST_SET drifted from the backend genuine-BH set.\n"
        f"  genuine but NOT trusted: {sorted(GENUINE - TRUST)}"
    )


def test_page_scrape_jsonld_takes_no_authority_penalty():
    # the stamp of the genuine-price program — a real BHD price out of a real
    # Bahrain PDP's JSON-LD must score as an honest fact, not an estimate.
    assert _price_authority_delta(
        {"price": {"source_method": "page_scrape_jsonld"}}
    ) == 0.0


def test_converted_usd_and_estimated_penalties_unchanged():
    # non-regression pin: only the genuine-BH set moves; the deliberate
    # converted_usd half-penalty and the estimate-grade fall-through stand.
    assert _price_authority_delta({"price": {"source_method": "converted_usd"}}) == -2.0
    assert _price_authority_delta({"price": {"source_method": "estimated"}}) == -4.0
    assert _price_authority_delta({}) == -4.0


def test_sentinel_non_prices_are_not_trusted():
    """`sitemap_no_match` / `validation_rejected` are SENTINELS, not prices —
    they mark a lookup that found nothing. They must stay out of the trust set
    and keep the full estimate-grade penalty, or a failed lookup would score as
    a confirmed Bahrain fact."""
    for method in ("sitemap_no_match", "validation_rejected"):
        assert method not in TRUST
        assert _price_authority_delta({"price": {"source_method": method}}) == -4.0


@pytest.mark.parametrize("method", sorted(GENUINE))
def test_has_real_price_true_for_each_genuine_method(method):
    assert _has_real_price({"price": {"source_method": method}}) is True


def test_price_leg_strong_for_genuine_scrape_without_shopping():
    # reproduces recorded row 6b8122e5: both sides page_scrape_jsonld, genuine
    # BHD, estimated=false — and the price pill rendered weak.
    conf = compute_confidence([
        {"price": {"source_method": "page_scrape_jsonld"}, "shopping_count": 0},
        {"price": {"source_method": "estimated"}, "shopping_count": 0},
    ])
    assert conf["legs"]["price"] == "strong"


def test_winner_evidence_cites_confirmed_bahrain_price():
    products_data = [
        {"brand": "X", "name": "A", "price": {"source_method": "page_scrape_jsonld"}},
        {"brand": "Y", "name": "B", "price": {"source_method": "estimated"}},
    ]
    reasons = build_winner_evidence(products_data, {}, 0, "electronics")
    assert any("confirmed Bahrain price" in r for r in reasons), reasons
