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
        # systematically remove them.
        #
        # Tolerance: allow up to 1 transient regression per product per run.
        # Mirrors the offline baseline_has_critical_fields tolerance — both
        # baselines AND live snapshots are probabilistic (cold-cache Serper
        # variance + GPT non-determinism + smart-fallback eventual consistency
        # from Bucket A's design). Catches systematic quality drops (2+ fields
        # lost) without firing on single-field transients on a cold call.
        regressed = []
        for f in fields:
            if _present(baseline_specs.get(f)) and not _present(live_specs.get(f)):
                regressed.append(f)

        regressed_summary = {f: (baseline_specs.get(f), live_specs.get(f)) for f in regressed}
        assert len(regressed) <= 1, (
            f"{category} product {product_index} systematic regression: {len(regressed)} critical fields lost\n"
            f"  baseline ({baseline_name}) vs live ({live_name}): {regressed_summary}\n"
            f"  Single transient field is tolerated; 2+ indicates a real D2 quality drop."
        )


# Per-category wall-time ceilings (post-D2 deploy, cold-cache).
# Mainstream targets ≤25s (matches STREAM_HARD_CAP_SECONDS).
# Fragrances has a 60s ceiling because Tom Ford + Dior trigger the
# Tier 1.5 luxury scrape cascade (Firecrawl/Scrape.do) which is not a
# D2 concern — luxury scrape latency is owned by D1 (`SCRAPING_MODE`).
# Pre-D2 baseline was 53-77s; D2 doesn't make it worse.
# Fashion + electronics tolerate 30s for cold-cache Serper variance —
# warm/typical wall is 15-18s, but the very first cold call on a
# busy Serper key can stretch.
WALL_TIME_CEILINGS = {
    "electronics": 30.0,
    "supplements": 30.0,
    "skincare":    30.0,
    "fragrances":  60.0,
    "fashion":     30.0,
}


@pytest.mark.live_unit
@pytest.mark.parametrize("category", CATEGORIES)
def test_post_d2_per_category_wall_time_under_ceiling(category):
    """Live bench wall-time: each category's cold compare must complete
    under its per-category ceiling post-D2. Skipped unless RUN_LIVE_BENCH=1.

    Per-category ceilings reflect realistic cold-cache wall time, not the
    D2 stretch target. D2's stretch target is ≤15s p50 (mainstream avg),
    measured via the consolidated 5-category bench in Task 3.3 of the plan.
    This per-category test catches regressions where a single category
    blows past its expected ceiling, not stretch-goal misses.
    """
    if os.environ.get("RUN_LIVE_BENCH") != "1":
        pytest.skip("Set RUN_LIVE_BENCH=1 to run live bench")

    import httpx
    import time

    ceiling = WALL_TIME_CEILINGS[category]
    query = QUERIES[category]
    start = time.perf_counter()
    response = httpx.get(
        "https://web-production-58776.up.railway.app/api/v1/text/compare",
        params={"q": query, "region": "bahrain", "nocache": "true"},
        timeout=ceiling + 10.0,  # httpx must outlast the assertion ceiling
    )
    elapsed = time.perf_counter() - start

    assert response.status_code == 200, f"{category} HTTP {response.status_code}"
    assert elapsed < ceiling, (
        f"{category} cold bench took {elapsed:.1f}s (per-category ceiling {ceiling}s). "
        f"Query: {query!r}"
    )
