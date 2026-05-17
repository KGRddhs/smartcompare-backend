"""D2 per-category spec-parity regression — runs against pre-D2 baseline
(offline, always) and post-D2 live bench (gated by RUN_LIVE_BENCH=1).

Catches category-specific regressions that a single-electronics test
would miss: fragrances notes extraction, supplements drug_context,
fashion minimal-schema validation paths, etc.
"""
import json
import os
import pytest


CATEGORIES = ["electronics", "supplements", "skincare", "fragrances", "fashion"]

QUERIES = {
    "electronics": "iPhone 17 vs Galaxy S25 Ultra",
    "supplements": "Centrum Adults vs One A Day Men",
    "skincare":    "Garnier Micellar Water vs Bioderma Sensibio",
    "fragrances":  "Tom Ford Tobacco Vanille vs Dior Sauvage",
    "fashion":     "Nike Air Force 1 vs Adidas Stan Smith",
}

CRITICAL_FIELDS = {
    "electronics": ["front_camera", "rear_camera", "processor", "ram", "battery", "water_resistance"],
    "supplements": ["count", "dosage", "form"],
    "skincare":    ["volume_ml", "ingredients"],
    "fragrances":  ["concentration", "longevity", "sillage"],
    "fashion":     ["material", "origin"],
}


def _baseline_path(category: str) -> str:
    return f"tests/fixtures/comparison_baseline_d2_post_bucket_a__{category}.json"


def _extract_specs(comparison: dict, product_index: int) -> dict:
    prods = comparison.get("products") or (comparison.get("specs") or {}).get("products", [])
    if len(prods) <= product_index:
        return {}
    return prods[product_index].get("specs") or {}


def _present(value) -> bool:
    return value not in (None, "", "N/A")


@pytest.mark.parametrize("category", CATEGORIES)
def test_baseline_has_critical_fields(category):
    """Offline check: per-category baseline fixture must have critical
    fields present for BOTH products. If this fails, the baseline was
    captured during a degraded state — re-run the curl in Task 0.1."""
    path = _baseline_path(category)
    assert os.path.exists(path), f"Baseline fixture missing: {path}"

    with open(path) as f:
        baseline = json.load(f)

    fields = CRITICAL_FIELDS[category]
    for product_index in (0, 1):
        specs = _extract_specs(baseline, product_index)
        assert specs, f"{category} product {product_index}: no specs in baseline"
        missing = [f for f in fields if not _present(specs.get(f))]
        # Tolerate up to 1 missing field per product in baseline (some real
        # products genuinely lack certain specs). More than 1 → baseline is
        # too thin to be useful for regression detection.
        assert len(missing) <= 1, (
            f"{category} product {product_index} ({(baseline.get('products') or [{}])[product_index].get('name', '?')}) "
            f"missing too many critical fields in baseline: {missing}. "
            f"Re-capture baseline."
        )


@pytest.mark.live_unit
@pytest.mark.parametrize("category", CATEGORIES)
def test_post_d2_per_category_critical_fields_intact(category):
    """Live bench: post-D2 deploy must not regress critical-fields presence
    vs the baseline. Skipped unless RUN_LIVE_BENCH=1.

    Strategy: for each baseline field that WAS present, the post-D2 response
    must ALSO have it present (D2 must not drop fields). Fields absent in
    baseline are tolerated post-D2 too.

    Run after deploying D2:
        RUN_LIVE_BENCH=1 pytest tests/test_d2_spec_parity_per_category.py -v
    """
    if os.environ.get("RUN_LIVE_BENCH") != "1":
        pytest.skip("Set RUN_LIVE_BENCH=1 to run live bench")

    import httpx

    # Load baseline
    with open(_baseline_path(category)) as f:
        baseline = json.load(f)

    # Live bench
    query = QUERIES[category]
    response = httpx.get(
        "https://web-production-58776.up.railway.app/api/v1/text/compare",
        params={"q": query, "region": "bahrain", "nocache": "true"},
        timeout=90,
    )
    assert response.status_code == 200, f"{category} live bench HTTP {response.status_code}"
    live = response.json()

    fields = CRITICAL_FIELDS[category]
    for product_index in (0, 1):
        baseline_specs = _extract_specs(baseline, product_index)
        live_specs = _extract_specs(live, product_index)
        baseline_name = (baseline.get("products") or [{}, {}])[product_index].get("name", "?")
        live_name = (live.get("products") or [{}, {}])[product_index].get("name", "?")

        # For each critical field that WAS present in baseline, it must
        # ALSO be present in live (post-D2). D2 can ADD fields; it cannot
        # REMOVE them.
        regressed = []
        for f in fields:
            if _present(baseline_specs.get(f)) and not _present(live_specs.get(f)):
                regressed.append(f)

        assert not regressed, (
            f"{category} product {product_index} regressed critical fields: {regressed}\n"
            f"  baseline ({baseline_name}): {{f: baseline_specs.get(f) for f in regressed}}\n"
            f"  live ({live_name}): {{f: live_specs.get(f) for f in regressed}}"
        )


@pytest.mark.live_unit
@pytest.mark.parametrize("category", CATEGORIES)
def test_post_d2_per_category_wall_time_under_25s(category):
    """Live bench wall-time: each category's cold compare must complete
    under 25s post-D2. Skipped unless RUN_LIVE_BENCH=1.

    25s is the hard ceiling (matches STREAM_HARD_CAP_SECONDS). D2's target
    is ≤15s p50, so individual benches at 20-25s indicate a slow query
    but not a blocker. Use the consolidated bench in Task 3.3 for p50/p95
    aggregate assertions.
    """
    if os.environ.get("RUN_LIVE_BENCH") != "1":
        pytest.skip("Set RUN_LIVE_BENCH=1 to run live bench")

    import httpx
    import time

    query = QUERIES[category]
    start = time.perf_counter()
    response = httpx.get(
        "https://web-production-58776.up.railway.app/api/v1/text/compare",
        params={"q": query, "region": "bahrain", "nocache": "true"},
        timeout=30,
    )
    elapsed = time.perf_counter() - start

    assert response.status_code == 200, f"{category} HTTP {response.status_code}"
    assert elapsed < 25.0, (
        f"{category} cold bench took {elapsed:.1f}s (limit 25s). "
        f"Query: {query!r}"
    )
