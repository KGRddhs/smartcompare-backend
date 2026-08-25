"""Bundle C integration probe suite (Section C plan tasks C.9.1–C.9.6).

Runs against live Railway backend with ?nocache=true. Marked
`@pytest.mark.integration` so the free suite excludes them; promote to ship
evidence per Section D.6 post-deploy verification.

Run (LIVE=1 required — the marker alone no longer opts in, see
tests/_env_safety.py):
    LIVE=1 python -m pytest tests/test_bundle_c_integration.py -v -m integration --timeout=180

Covers spec §1c + §8d + edges flagged by qa-bundle-c (absorbed from
qa's `tests/test_bundle_c_edge_stubs.py` proposal — kept on this file
to retain Section C ownership).
"""
from __future__ import annotations

import os
import re
import time

import pytest

from tests._bundle_c_helpers import (
    assert_no_forbidden_strings,
    collect_user_visible_strings,
)


BASE_URL = os.getenv(
    "BUNDLE_C_PROBE_URL", "https://web-production-58776.up.railway.app"
)
TIMEOUT = 30.0


@pytest.fixture(scope="module")
def probe_session():
    """Lightweight requests session — initialised once per module."""
    requests = pytest.importorskip("requests")
    s = requests.Session()
    s.headers.update({"Accept": "application/json"})
    return s


# 6-category × `(category, query, min_dims)`
PROBES = [
    ("electronics",  "iPhone 16 vs Galaxy S25",                       4),
    ("skincare",     "CeraVe vs Cetaphil moisturizing cream",         3),
    ("supplements",  "Solgar Vitamin D3 vs NOW Foods Vitamin D3",      3),
    ("fashion",      "Adidas Samba vs Nike Air Force 1",              3),
    ("fragrances",   "Tom Ford Black Orchid vs Dior Sauvage",          3),
    ("grocery",      "Lurpak butter vs President butter",             3),
]


def _fetch(probe_session, query: str, **params) -> dict:
    """Fetch a comparison response — base helper for every integration probe."""
    p = {"q": query, "region": "bahrain", "nocache": "true", **params}
    r = probe_session.get(
        f"{BASE_URL}/api/v1/text/compare", params=p, timeout=TIMEOUT
    )
    assert r.status_code == 200, f"HTTP {r.status_code}: {r.text[:500]}"
    return r.json()


# ---------------------------------------------------------------------------
# C.9.2 — 6-category cold-cache probes — real prices land, pros/cons populated
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.parametrize("category,query,min_dims", PROBES)
def test_cold_cache_probe_real_prices(probe_session, category, query, min_dims):
    """Spec §1c + §8d: real prices land (NOT all estimated). pros/cons populated.
    dimensions[] count ≥ min_dims. factual_verdict populated.
    """
    data = _fetch(probe_session, query, selected_category=category)

    # §1c — Real prices for at least ONE product per probe
    products = data.get("products", []) or []
    estimated_count = sum(
        1 for p in products
        if (p.get("price") or {}).get("source_method") == "estimated"
    )
    assert estimated_count < len(products), (
        f"All products estimated for {category}/{query!r} — Bundle C §1c regression"
    )

    # §1a — pros/cons populated
    for i, p in enumerate(products):
        assert p.get("pros"), (
            f"Empty pros for product[{i}] in {category}/{query!r} — §1a regression"
        )
        assert p.get("cons"), (
            f"Empty cons for product[{i}] in {category}/{query!r} — §1a regression"
        )

    # §6a — dimensions[] count ≥ min per category
    sv2 = data.get("scoring_v2", {}) or {}
    dims = sv2.get("dimensions", []) or []
    assert len(dims) >= min_dims, (
        f"Only {len(dims)} dims for {category}/{query!r} (expected ≥ {min_dims})"
    )

    # §1b — factual_verdict populated
    fv = sv2.get("factual_verdict", {}) or {}
    assert fv.get("line1"), f"factual_verdict.line1 missing for {category}/{query!r}"
    assert fv.get("line2"), f"factual_verdict.line2 missing for {category}/{query!r}"


# ---------------------------------------------------------------------------
# C.9.3 — `other` car-like comparison probe (spec §3f)
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_other_car_like_comparison_geometric_mean_subscale(probe_session):
    """Spec §3f: Toyota+Honda 5000–6000 BHD → other_ultra → 'mid' tier."""
    data = _fetch(
        probe_session,
        "Toyota Corolla 2020 vs Honda Civic 2020",
        selected_category="other",
    )
    products = data.get("products", []) or []
    tiers = [
        ((p.get("scoring_v2") or {}).get("price_tier"))
        for p in products
    ]
    # At least one product must hit the 'mid' bucket of other_ultra
    assert "mid" in tiers, (
        f"Geometric-mean sub-scale not firing — tiers: {tiers}"
    )


# ---------------------------------------------------------------------------
# C.9.4 — value_match captions fire correctly (spec §4d)
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_value_match_caption_fires_when_above_user_budget(probe_session):
    """Spec §4d: user picking 'budget' searching iPhone 16 (luxury) → at least
    one value_match='above_range'."""
    data = _fetch(
        probe_session,
        "iPhone 16 vs Galaxy S25",
        selected_category="electronics",
        **{"preferences[budget]": "budget"},
    )
    products = data.get("products", []) or []
    matches = [
        ((p.get("scoring_v2") or {}).get("value_match"))
        for p in products
    ]
    assert "above_range" in matches, (
        f"value_match not firing for above-budget comparison: {matches}"
    )


# ---------------------------------------------------------------------------
# C.9.5 — No forbidden vocabulary in any probe response (spec § rule)
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.parametrize("category,query,min_dims", PROBES)
def test_no_forbidden_strings_in_user_visible_fields(
    probe_session, category, query, min_dims
):
    """User-visible fields ONLY (NOT internal source_method enum which retains
    'estimated' as a backend enum)."""
    data = _fetch(probe_session, query, selected_category=category)
    for s in collect_user_visible_strings(data):
        assert_no_forbidden_strings(s)


# ---------------------------------------------------------------------------
# C.9.6 — Wall-time inside STREAM_HARD_CAP_SECONDS per probe
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.parametrize("category,query,min_dims", PROBES)
def test_probe_within_stream_hard_cap(probe_session, category, query, min_dims):
    """Each probe completes inside 25s STREAM_HARD_CAP_SECONDS + 1s slack."""
    start = time.monotonic()
    data = _fetch(probe_session, query, selected_category=category)
    elapsed = time.monotonic() - start
    assert elapsed < 26.0, f"{category}/{query!r} took {elapsed:.1f}s — exceeds cap"
    assert data.get("products"), "response missing products"


# ===========================================================================
# Edge stubs absorbed from qa-bundle-c (qa-bundle-c idle-work backlog item 3)
#
# Each one promotes from `@pytest.mark.skip` → real assertion once the matching
# A.x / B.x contract lands. Keep the skip marker until the contract is wired
# so the integration suite stays GREEN during the bundle-in-flight window.
# ===========================================================================


# Edge 1 — Mixed source_method per leg → Price pill hidden (§5c)
@pytest.mark.integration
@pytest.mark.skip(reason="bundle-c — promote once mixed-leg probe identified")
def test_mixed_source_method_hides_price_pill_per_5c(probe_session):
    """Probe TBD — niche luxury fragrance + mainstream supplement likely mix legs.
    Backend assertion: at least one estimated leg + at least one non-estimated.
    Frontend hide-rule covered by ConfidencePills snapshot test (C.6.3).
    """
    data = _fetch(probe_session, "<TBD: mixed-leg query>")
    methods = [(p.get("price") or {}).get("source_method") for p in data["products"]]
    assert "estimated" in methods
    assert any(m != "estimated" for m in methods)


# Edge 2 — Anonymous user → empty applied_shifts → chip hidden (§7a)
@pytest.mark.integration
@pytest.mark.skip(reason="bundle-c — promote when anonymous-user attribution path lands")
def test_anonymous_user_empty_applied_shifts_per_7a(probe_session):
    data = _fetch(
        probe_session,
        "iPhone 16 vs Galaxy S25",
        user_id="00000000-0000-0000-0000-000000000000",
    )
    shifts = (
        (data.get("scoring_v2") or {})
        .get("personalization", {})
        .get("applied_shifts", [])
    )
    assert isinstance(shifts, list)
    assert shifts == []


# Edge 3 — Weird cross-category (iPhone vs CeraVe) (§2e)
@pytest.mark.integration
@pytest.mark.skip(reason="bundle-c — promote when weird-comparison detector ships (A.x)")
def test_weird_cross_category_handling_per_2e(probe_session):
    data = _fetch(probe_session, "iPhone 16 vs CeraVe Moisturizer")
    quality = (
        (data.get("metadata") or {}).get("comparison_quality")
        or (data.get("scoring_v2") or {}).get("comparison_quality")
    )
    assert quality == "weird"
    declaration = (data.get("comparison") or {}).get("winner_declaration", "")
    # No scary copy in the verdict
    assert_no_forbidden_strings(declaration)


# Edge 4 — `other` car-like → geometric-mean other_ultra sub-scale (§3f)
@pytest.mark.integration
@pytest.mark.skip(reason="bundle-c — superseded by test_other_car_like_comparison_geometric_mean_subscale")
def test_other_category_geometric_mean_sub_scale_per_3f(probe_session):
    """Kept as documentation of qa's edge-stub coverage. Superseded by
    test_other_car_like_comparison_geometric_mean_subscale above (live now)."""
    data = _fetch(probe_session, "Toyota Corolla vs Honda Civic 2024")
    assert data.get("category_used", "other") == "other"
    for product in data.get("products", []) or []:
        assert "value_match" in (product.get("scoring_v2") or {})


# Edge 5 — Backend-internals leak guard (project rule + spec §7b)
@pytest.mark.integration
@pytest.mark.skip(reason="bundle-c — promote when applied_shifts response wired (A.x)")
def test_response_does_not_leak_backend_internals(probe_session):
    """Recursive walk: assert NO `coefficient|cap_pct|shift_magnitude|
    scaling_factor|weight|magnitude` keys in user-discoverable response paths.
    """
    banned = re.compile(
        r"^(coefficient|cap_pct|cap_percent|shift_magnitude|scaling_factor|"
        r"formula_weight|magnitude|shift_pct|weight_delta)$",
        re.IGNORECASE,
    )

    def walk(obj, path=""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                assert not banned.match(k), f"banned key at {path}.{k}"
                walk(v, f"{path}.{k}")
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                walk(item, f"{path}[{i}]")

    for q in ("iPhone 16 vs Galaxy S25", "iPhone 16 vs CeraVe Moisturizer"):
        walk(_fetch(probe_session, q))
