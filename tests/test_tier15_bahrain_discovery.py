"""F1.2 / F1.3 / F1.4 — Tier 1.5 candidate harvesting (Bahrain-first).

Covers the `_harvest_candidate_urls()` helper extracted from the Tier 1.5
page-scrape escalation in `_get_price`. The helper turns the per-tier Serper
discovery results into an ordered candidate list:

  bahrain (registry) -> official (brand domain) -> authorized -> gcc

Invariants under test:
- F1.2: Bahrain registry candidates are harvested FIRST (ahead of official /
  authorized / gcc), gated by `score_source(link, category) >= 1.5`.
- F1.3: registry-first gate with legacy whitelist fallback — an `ounass.com`
  fashion link passes via the registry; a legacy-only domain still passes via
  the fallback set; `dhgate.com` (counterfeit) fails BOTH and is rejected.
- F1.4: every harvested entry records `route` and `source_weight`.

`_harvest_candidate_urls` returns `List[Tuple[link, domain_label, route,
source_weight]]`; the production call site derives the legacy
`candidate_urls = [(link, label), ...]` shape from the first two fields.
"""

import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

import pytest

from app.services.structured_comparison_service import _harvest_candidate_urls


def _organic(*links):
    return {"organic": [{"link": l} for l in links]}


# ---------- F1.2: Bahrain-first ordering ----------

def test_bahrain_candidates_harvested_first():
    results_by_tier = {
        "bahrain": _organic("https://www.bahrain.sharafdg.com/product/iphone-15"),
        "official": _organic("https://www.apple.com/shop/iphone-15"),
        "authorized": _organic("https://www.amazon.com/dp/IPHONE"),
        "gcc": _organic("https://www.noon.com/uae-en/iphone-15"),
    }
    harvested = _harvest_candidate_urls(
        results_by_tier, official_domain="apple.com", category="electronics"
    )
    links = [h[0] for h in harvested]
    # Bahrain link must come first in the ordered candidate list.
    assert links[0] == "https://www.bahrain.sharafdg.com/product/iphone-15"
    # The bahrain domain appears ahead of the official apple.com candidate.
    bh_idx = next(i for i, h in enumerate(harvested) if "bahrain.sharafdg.com" in h[0])
    off_idx = next(i for i, h in enumerate(harvested) if "apple.com" in h[0])
    assert bh_idx < off_idx


def test_bahrain_candidate_below_threshold_rejected():
    """A bahrain-tier query may surface an off-registry marketplace link.

    Counterfeit invariant #1: a domain that scores < 1.5 for the category is
    rejected even when it shows up in the bahrain discovery results.
    """
    results_by_tier = {
        "bahrain": _organic(
            "https://www.dhgate.com/fake-iphone",          # score 0.5 -> reject
            "https://gcc.luluhypermarket.com/en-bh/iphone-15",     # score 3.0 -> keep
        ),
    }
    harvested = _harvest_candidate_urls(
        results_by_tier, official_domain=None, category="electronics"
    )
    links = [h[0] for h in harvested]
    assert "https://gcc.luluhypermarket.com/en-bh/iphone-15" in links
    assert "https://www.dhgate.com/fake-iphone" not in links


def test_bahrain_category_mismatch_rejected():
    """bahrain.sharafdg.com is electronics-only — under category=supplements it
    scores 0.5 and must NOT enter the pool from the bahrain tier."""
    results_by_tier = {
        "bahrain": _organic("https://www.bahrain.sharafdg.com/protein-powder"),
    }
    harvested = _harvest_candidate_urls(
        results_by_tier, official_domain=None, category="supplements"
    )
    assert harvested == []


# ---------- F1.3: registry-first gate + legacy fallback ----------

def test_authorized_registry_pass_ounass_fashion():
    """ounass.com is gcc-tier fashion in the registry (score 1.5) -> passes
    the authorized gate via the registry path."""
    results_by_tier = {
        "authorized": _organic("https://www.ounass.com/bag-123"),
    }
    harvested = _harvest_candidate_urls(
        results_by_tier, official_domain=None, category="fashion"
    )
    links = [h[0] for h in harvested]
    assert "https://www.ounass.com/bag-123" in links
    # Recorded route is registry (registry-first).
    entry = next(h for h in harvested if "ounass.com" in h[0])
    assert entry[2] == "registry"
    assert entry[3] >= 1.5


def test_authorized_legacy_fallback_pass():
    """A domain in the legacy AUTHORIZED_LUXURY_RETAILERS / OFFICIAL_BRAND_DOMAINS
    set but NOT in the registry still passes via the legacy fallback path."""
    from app.services.structured_comparison_service import AUTHORIZED_LUXURY_RETAILERS

    # Pick a legacy authorized retailer that is NOT in SOURCE_REGISTRY.
    from app.services.source_router import SOURCE_REGISTRY
    registry_domains = {s.domain for s in SOURCE_REGISTRY}
    legacy_only = next(
        (d for d in AUTHORIZED_LUXURY_RETAILERS if d not in registry_domains), None
    )
    assert legacy_only is not None, "expected a legacy-only authorized retailer"

    results_by_tier = {
        "authorized": _organic(f"https://www.{legacy_only}/product/x"),
    }
    harvested = _harvest_candidate_urls(
        results_by_tier, official_domain=None, category="fashion"
    )
    links = [h[0] for h in harvested]
    assert f"https://www.{legacy_only}/product/x" in links
    entry = next(h for h in harvested if legacy_only in h[0])
    assert entry[2] == "legacy_fallback"


def test_counterfeit_domain_fails_both_gates():
    """dhgate.com scores 0.5 (registry) AND is absent from legacy sets ->
    rejected from authorized + gcc harvest. Dispatcher invariant #1."""
    results_by_tier = {
        "authorized": _organic("https://www.dhgate.com/fake-bag"),
        "gcc": _organic("https://www.aliexpress.com/fake-bag"),
    }
    harvested = _harvest_candidate_urls(
        results_by_tier, official_domain=None, category="fashion"
    )
    assert harvested == []


def test_gcc_registry_pass_noon_all_category():
    """noon.com is gcc-tier with empty categories (all) -> score 1.5 ->
    passes the gcc gate via registry for any category."""
    results_by_tier = {
        "gcc": _organic("https://www.noon.com/uae-en/laptop"),
    }
    harvested = _harvest_candidate_urls(
        results_by_tier, official_domain=None, category="electronics"
    )
    links = [h[0] for h in harvested]
    assert "https://www.noon.com/uae-en/laptop" in links


# ---------- F1.4: route + source_weight on every entry ----------

def test_every_entry_has_route_and_weight():
    results_by_tier = {
        "bahrain": _organic("https://gcc.luluhypermarket.com/en-bh/iphone-15"),
        "official": _organic("https://www.apple.com/shop/iphone-15"),
        "gcc": _organic("https://www.noon.com/uae-en/iphone-15"),
    }
    harvested = _harvest_candidate_urls(
        results_by_tier, official_domain="apple.com", category="electronics"
    )
    assert len(harvested) >= 3
    for link, label, route, weight in harvested:
        assert isinstance(link, str) and link
        assert isinstance(label, str) and label
        assert route in ("registry", "legacy_fallback", "official")
        assert isinstance(weight, float)


def test_official_domain_entry_route_official():
    results_by_tier = {
        "official": _organic("https://www.apple.com/shop/iphone-15"),
    }
    harvested = _harvest_candidate_urls(
        results_by_tier, official_domain="apple.com", category="electronics"
    )
    assert len(harvested) == 1
    link, label, route, weight = harvested[0]
    assert route == "official"
    assert label == "apple.com"


def test_official_offdomain_link_rejected():
    """The official-tier harvest keeps the existing same-domain check —
    an off-domain marketplace link returned for `site:apple.com` is dropped."""
    results_by_tier = {
        "official": _organic("https://www.reseller-example.com/iphone"),
    }
    harvested = _harvest_candidate_urls(
        results_by_tier, official_domain="apple.com", category="electronics"
    )
    assert harvested == []


def test_empty_results_yields_empty_list():
    assert _harvest_candidate_urls({}, official_domain=None, category="electronics") == []


# ---------- F1.2: call-site wiring through _get_price ----------

from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def clean_service(monkeypatch):
    """Fresh service with cache + DB writes neutralized (fan_out pattern)."""
    from app.services import structured_comparison_service as scs_mod

    monkeypatch.setattr(scs_mod, "get_cached", lambda *a, **kw: None)
    monkeypatch.setattr(scs_mod, "set_cached", lambda *a, **kw: None)
    monkeypatch.setattr(
        "app.services.product_data_service.get_cached_price",
        AsyncMock(return_value=None),
    )
    service = scs_mod.get_comparison_service()
    service._save_price_to_db = MagicMock()
    return service


@pytest.mark.asyncio
async def test_bahrain_discovery_query_dispatched_first(monkeypatch, clean_service):
    """When Tier 1.5 escalates for a NON-luxury electronics product, the
    first search_web call carries the Bahrain `site:` discovery query (F1.1
    builder) — ahead of official/authorized/gcc discovery."""
    from app.services import structured_comparison_service as scs_mod

    # Force Tier 1 (Serper Shopping) empty so escalation fires.
    monkeypatch.setattr(
        scs_mod, "search_product_prices",
        AsyncMock(return_value={"shopping": [], "organic": []}),
    )
    monkeypatch.setattr(
        scs_mod, "extract_price_from_shopping", lambda *a, **kw: None,
    )
    # No official domain for a generic electronics product.
    monkeypatch.setattr(scs_mod, "get_official_domain", lambda *a, **kw: None)

    # Record the order of search_web queries.
    seen_queries = []

    async def _recording_search_web(query, *a, **kw):
        seen_queries.append(query)
        return {"organic": []}

    monkeypatch.setattr(scs_mod, "search_web", _recording_search_web)
    # Tier 2 fallback stub so _get_price completes without erroring.
    monkeypatch.setattr(
        scs_mod, "extract_price_from_training_data",
        AsyncMock(return_value=(
            {"amount": 50, "currency": "USD", "source_method": "gpt_training_estimate"},
            {},
        )),
    )

    await clean_service._get_price(
        brand="Xiaomi", name="14", variant=None, region="bahrain",
        search_query="Xiaomi 14 price", nocache=True, category="electronics",
    )

    assert seen_queries, "no search_web discovery calls were made — escalation didn't fire"
    # The FIRST discovery query must be the Bahrain site: query.
    first = seen_queries[0]
    assert "site:" in first, f"first discovery query not a site: query: {first!r}"
    assert "site:gcc.luluhypermarket.com" in first or "site:bahrain.sharafdg.com" in first, (
        f"first discovery query is not Bahrain-tier: {first!r}"
    )
    # And it must precede the authorized/gcc retailer queries.
    assert first.startswith("Xiaomi 14")
