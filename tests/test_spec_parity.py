"""Bucket A bug 3 — spec parity regression test against pre-D1 baseline."""
import json
import os
import pytest


BASELINE_PATH = "tests/fixtures/comparison_baseline_d2.json"


@pytest.fixture(scope="module")
def baseline():
    with open(BASELINE_PATH) as f:
        return json.load(f)


def _extract_spec_keys(comparison_dict, product_index):
    """Get the set of non-null spec keys for a product, filtering out
    'N/A' and empty strings (those are 'GPT didn't know' signals)."""
    products = comparison_dict.get("products") or (comparison_dict.get("specs") or {}).get("products", [])
    if len(products) <= product_index:
        return set()
    specs = products[product_index].get("specs") or {}
    valid_keys = set()
    for k, v in specs.items():
        if k.startswith("_"):
            continue  # internal fields like _field_confidence
        if v in (None, "", "N/A"):
            continue
        valid_keys.add(k)
    return valid_keys


def test_baseline_iphone_has_minimum_keys(baseline):
    """Baseline iPhone 17 should have at least 6 spec keys with real values."""
    keys = _extract_spec_keys(baseline, 0)
    assert len(keys) >= 6, f"iPhone baseline too thin: {keys}"


def test_baseline_s25_has_minimum_keys(baseline):
    """Baseline Galaxy S25 Ultra should have at least 6 spec keys with real values."""
    keys = _extract_spec_keys(baseline, 1)
    assert len(keys) >= 6, f"S25 baseline too thin: {keys}"


@pytest.mark.live_unit
def test_post_fix_iphone_vs_s25_has_critical_specs():
    """Post-Bucket-A live bench: both products should have front_camera AND
    water_resistance populated (the bug-3 fix). Skipped unless RUN_LIVE_BENCH=1.

    Run manually after deploying Bucket A:
    RUN_LIVE_BENCH=1 pytest tests/test_spec_parity.py::test_post_fix_iphone_vs_s25_has_critical_specs -v
    """
    if os.environ.get("RUN_LIVE_BENCH") != "1":
        pytest.skip("Set RUN_LIVE_BENCH=1 to run live bench")

    import httpx
    response = httpx.get(
        "https://web-production-58776.up.railway.app/api/v1/text/compare",
        params={"q": "iPhone 17 vs Galaxy S25 Ultra", "region": "bahrain", "nocache": "true"},
        timeout=60,
    )
    assert response.status_code == 200
    data = response.json()

    products = data.get("products") or (data.get("specs") or {}).get("products", [])
    assert len(products) == 2, "Expected 2 products"

    for i, p in enumerate(products):
        specs = p.get("specs") or {}
        front_cam = specs.get("front_camera")
        water = specs.get("water_resistance")
        assert front_cam not in (None, "", "N/A"), \
            f"Product {i} ({p.get('name')}) missing front_camera: {specs}"
        assert water not in (None, "", "N/A"), \
            f"Product {i} ({p.get('name')}) missing water_resistance: {specs}"
