"""S3-reopen T4 — research-verified BH Shopify fragrance sources.

Brief (docs/plans/2026-06-14-bh-sourcing-research.md §1): two verified free-
endpoint wins — en-bh.ajmal.com + alhajisbahrain.com expose Shopify
`/products.json` with genuine BHD prices (the cheapest possible genuine-BHD win,
$0, no render). Decision-F re-verified same-session 2026-06-14:
  - en-bh.ajmal.com  → Shopify, /meta.json currency=BHD ("Oud Nadir 50gms 48.000")
  - alhajisbahrain.com → Shopify, /meta.json currency=BHD ("Meraki Amber 5.000")
(ajmal.com apex is NOT Shopify; the BH store is the en-bh subdomain.)

Added as is_shopify=True bahrain-tier fragrance sources so the cascade hits
their /products.json directly (tier-1 BH free-JSON). Pure registry inspection.
"""

import pytest

from app.services.source_router import (
    SOURCE_REGISTRY,
    get_shopify_sources_for_category,
    score_source,
)


_NEW = ["en-bh.ajmal.com", "alhajisbahrain.com"]


@pytest.mark.parametrize("domain", _NEW)
def test_new_bh_shopify_source_registered_bahrain_tier(domain):
    by_domain = {s.domain: s for s in SOURCE_REGISTRY}
    assert domain in by_domain, f"{domain} not in registry"
    s = by_domain[domain]
    assert s.tier == "bahrain"
    assert s.weight == 3.0
    assert s.is_shopify is True
    assert "fragrances" in s.categories


def test_new_sources_in_fragrances_shopify_set():
    domains = [s.domain for s in get_shopify_sources_for_category("fragrances")]
    for d in _NEW:
        assert d in domains


@pytest.mark.parametrize("domain", _NEW)
def test_new_source_scores_bahrain_weight_for_fragrances(domain):
    assert score_source(f"https://{domain}/products/x", "fragrances") == 3.0
