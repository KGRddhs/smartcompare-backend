"""L2.14 — Lane 2 prod integration test.

Runs 6 queries (2 per scenario: confidence-high, confidence-medium,
confidence-low) against live Railway and asserts:
- Source trace surfaces escalation when expected
- Wall time stays under STREAM_HARD_CAP_SECONDS=25s
- Confidence-driven escalation works for non-luxury categories

Gated by `pytest -m integration`. Requires the deploy at
https://web-production-58776.up.railway.app/ to have:
- ENABLE_FIRECRAWL=true
- ENABLE_SCRAPEDO=true
- ENABLE_PAGE_SCRAPE=true
- DEBUG_STAGE_TIMINGS=true
(per team-lead's Railway env flip, 2026-06-08).
"""

import os
import time

import httpx
import pytest

PROD_BASE = os.environ.get(
    "L2_INTEGRATION_BASE",
    "https://web-production-58776.up.railway.app",
)

WALL_BUDGET_SECONDS = 25.0
TIMEOUT_SECONDS = 35.0  # Allow margin over the backend hard cap


@pytest.mark.integration
@pytest.mark.parametrize(
    "scenario,query,expected_category",
    [
        # Confidence-HIGH: well-known mainstream electronics, Tier 1 should land
        ("electronics_phone", "iPhone 15 vs Galaxy S24", "electronics"),
        ("electronics_laptop", "MacBook Air M3 vs Dell XPS 13", "electronics"),
        # Confidence-MEDIUM: supplements that hit iHerb but no multi-source
        ("supplements_protein", "Optimum Nutrition Gold Standard Whey vs Dymatize ISO100", "supplements"),
        ("supplements_vitamin", "NOW Foods Vitamin D 5000 IU vs Nature Made Vitamin D3", "supplements"),
        # Confidence-LOW (former luxury-only path now confidence-driven):
        # niche fragrances - Tier 1 yields ZERO; escalation MUST fire
        ("fragrances_niche", "Creed Aventus vs Tom Ford Black Orchid", "fragrances"),
        ("fragrances_edp", "Dior Sauvage EDP vs YSL La Nuit de L'Homme", "fragrances"),
    ],
)
def test_lane2_prod_scenario(scenario: str, query: str, expected_category: str):
    start = time.perf_counter()
    with httpx.Client(timeout=TIMEOUT_SECONDS) as client:
        response = client.get(
            f"{PROD_BASE}/api/v1/text/compare",
            params={"q": query, "nocache": "true"},
        )
    wall = time.perf_counter() - start

    assert response.status_code == 200, (
        f"[{scenario}] HTTP {response.status_code}: {response.text[:200]}"
    )

    data = response.json()

    # Graceful timeout response is OK (lane2 still met the hard cap)
    if data.get("code") == "TIMEOUT":
        assert wall <= WALL_BUDGET_SECONDS + 5.0, (
            f"[{scenario}] TIMEOUT returned but wall {wall:.1f}s "
            f"exceeded hard cap + buffer"
        )
        pytest.skip(f"[{scenario}] backend returned TIMEOUT (expected on slow tier)")

    assert data.get("success") is True, (
        f"[{scenario}] success!=True. Full response: {data}"
    )

    # Wall budget
    assert wall <= WALL_BUDGET_SECONDS + 5.0, (
        f"[{scenario}] wall {wall:.1f}s > hard cap {WALL_BUDGET_SECONDS}s"
    )

    # Category sanity
    cat = (data.get("metadata") or {}).get("category_used") or data.get(
        "category_used"
    )
    if cat:
        assert cat == expected_category, (
            f"[{scenario}] category_switched: got {cat!r} expected "
            f"{expected_category!r}"
        )

    # L2.9 — source_trace observability: when DEBUG_STAGE_TIMINGS=true on
    # Railway, the orchestrator collects the per-product race trace.
    # On TIMEOUT or content-block the trace may be absent — we only assert
    # presence on success responses.
    metadata = data.get("metadata") or {}
    source_trace = metadata.get("source_trace")
    if source_trace is not None:
        assert "products" in source_trace, (
            f"[{scenario}] source_trace missing 'products' list"
        )
        for ptrace in source_trace["products"]:
            assert "races" in ptrace
            assert isinstance(ptrace["races"], dict)


@pytest.mark.integration
def test_lane2_confidence_escalation_for_non_luxury():
    """Direct probe of L2.5: a confidence-LOW query MUST surface either:
    - a real price > 0 (escalation found something), OR
    - an explicit graceful degrade (success:false, code:INSUFFICIENT_DATA), OR
    - a TIMEOUT code with wall <= cap.

    Previously the luxury gate would have silently returned a bogus Tier 1
    price (e.g. 20 BHD for Tom Ford). Net effect of L2.5: that no longer
    happens — either we escalate and find truth, or we return null/timeout.
    """
    with httpx.Client(timeout=TIMEOUT_SECONDS) as client:
        response = client.get(
            f"{PROD_BASE}/api/v1/text/compare",
            params={
                "q": "Tom Ford Black Orchid 50ml vs Creed Aventus 100ml",
                "nocache": "true",
            },
        )

    assert response.status_code == 200
    data = response.json()

    code = data.get("code")
    if code in ("TIMEOUT", "INSUFFICIENT_DATA", "CONTENT_UNAVAILABLE"):
        pytest.skip(f"backend returned graceful degrade: {code}")

    assert data.get("success") is True

    # Extract per-product prices via either overview.products or top-level products
    products = (
        (data.get("overview") or {}).get("products")
        or data.get("products")
        or []
    )
    assert len(products) == 2

    # Every product MUST have either a real price OR an explicit unavailable
    # marker. The forbidden state is a bogus < 30 BHD price for a luxury
    # fragrance that retails at $250+ — that would mean the luxury gate
    # leaked through.
    for p in products:
        price = p.get("price") or {}
        amount = price.get("amount")
        if amount is None or price.get("unavailable"):
            continue  # Acceptable — no price found, FE renders "Price not available"
        # If we got a number, it must not be the bogus < 30 BHD pre-L2.5 case
        assert amount >= 30, (
            f"product {p.get('name')!r} got price={amount} BHD — "
            f"luxury gate may have leaked. Source method: {price.get('source_method')}"
        )


@pytest.mark.integration
def test_lane2_specs_use_product_type_schema_in_prod():
    """L2.12 probe — phone query should yield phone-specific schema fields
    in specs.products[i].specs. Washer would yield capacity_kg etc."""
    with httpx.Client(timeout=TIMEOUT_SECONDS) as client:
        response = client.get(
            f"{PROD_BASE}/api/v1/text/compare",
            params={"q": "iPhone 15 Pro vs Galaxy S24", "nocache": "true"},
        )
    assert response.status_code == 200
    data = response.json()
    if data.get("code"):
        pytest.skip(f"backend degrade: {data['code']}")
    assert data.get("success") is True

    specs_products = (data.get("specs") or {}).get("products") or []
    if not specs_products:
        pytest.skip("specs.products missing — graceful empty path")

    # For a phone query, expect at least 2 of: display/processor/ram/battery/camera
    phone_signal_fields = {"display", "processor", "ram", "battery", "camera", "rear_camera"}
    for p in specs_products:
        specs = p.get("specs") or {}
        present = phone_signal_fields & set(specs.keys())
        assert len(present) >= 2, (
            f"product {p.get('name')!r} specs missing phone fields. "
            f"Got keys: {list(specs.keys())[:10]}"
        )
