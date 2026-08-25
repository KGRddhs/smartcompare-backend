"""
Bundle E integration tests — validate the new `scoring_v2` contract end-to-end
against the live Railway preview deploy.

These tests are RED by design until Phase 1 (backend foundations) and Phase 2
(scatter-gather + new SSE events) land. They turn GREEN as backend-opus's
work merges. Final-gate use is at the end of Task 4.1 / 4.6.

Cost: ~$0.01 per test (real OpenAI + Serper). ~$0.04 for the full Bundle E
integration suite. Mark `@pytest.mark.integration` so the default suite
(`pytest -m "not integration"`) skips these.

Run: `LIVE=1 python -m pytest tests/test_bundle_e_integration.py -v --timeout=180 -m integration`
(`LIVE=1` is required — the marker alone no longer opts in, see
tests/_env_safety.py.)
"""
from __future__ import annotations

import re
from typing import Any

import httpx
import pytest

BASE_URL = "https://web-production-58776.up.railway.app"
TIMEOUT = 150.0  # API can take up to 120s on cold queries

# Banned evaluative vocab — design doc § Decision 5 lock + Agent A's
# pre-read entry at QA log [16:17]. `delta_text` MUST NOT contain any of
# these (case-insensitive, whole-word).
BANNED_DELTA_WORDS = (
    "best", "pick", "excellent", "great", "recommend", "winner",
    "worst", "better", "worse", "beats", "smart", "good", "choose",
)
_BANNED_RE = re.compile(
    r"\b(" + "|".join(BANNED_DELTA_WORDS) + r")\b",
    flags=re.IGNORECASE,
)


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------

def fetch_comparison(query: str, *, nocache: bool = True) -> dict[str, Any]:
    """GET /api/v1/text/compare and return the parsed JSON body."""
    response = httpx.get(
        f"{BASE_URL}/api/v1/text/compare",
        params={"q": query, "nocache": "true" if nocache else "false"},
        timeout=TIMEOUT,
    )
    assert response.status_code == 200, (
        f"HTTP {response.status_code}: {response.text[:500]}"
    )
    return response.json()


def find_scoring_v2(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Return the scoring_v2 sub-object from the response. Design § Decision 2
    locks the response shape to `scoring.dimensions[]` + `scoring.overall_score`
    PLUS legacy keys for one release cycle (Bundle F removes legacy). Until the
    final shape is wired we accept either top-level `scoring_v2` or
    `scoring.dimensions[]` — assert helper below routes through this.
    """
    # Preferred final shape: scoring.dimensions[] alongside legacy keys.
    scoring = payload.get("scoring") or {}
    if isinstance(scoring, dict) and "dimensions" in scoring:
        return scoring
    # Fallback during Phase 1 development: explicit `scoring_v2` namespace.
    sv2 = payload.get("scoring_v2")
    if isinstance(sv2, dict) and "dimensions" in sv2:
        return sv2
    # Failure surface for early Phase 1 RED runs.
    raise AssertionError(
        "scoring_v2 contract missing: no `scoring.dimensions[]` or top-level "
        f"`scoring_v2` in response. Keys present: {sorted(payload.keys())}; "
        f"scoring keys: {sorted(scoring.keys()) if isinstance(scoring, dict) else type(scoring).__name__}"
    )


def assert_no_banned_vocab(scoring: dict[str, Any]) -> None:
    """Every `delta_text` must be factual — no superlatives or judgement words."""
    for i, dim in enumerate(scoring.get("dimensions", [])):
        delta = dim.get("delta_text") or ""
        if not delta:
            continue
        match = _BANNED_RE.search(delta)
        assert match is None, (
            f"dimensions[{i}] (`{dim.get('key')}`) delta_text contains banned "
            f"vocab `{match.group(0) if match else ''}`: {delta!r}"
        )


def assert_dimension_complete(dim: dict[str, Any], idx: int) -> None:
    """Per § Decision 2 — no dimension is emitted unless BOTH products have data."""
    for field in ("key", "label", "score_a", "score_b", "delta_text", "confidence", "is_core"):
        assert field in dim, (
            f"dimensions[{idx}] missing required field `{field}`. Keys: {sorted(dim.keys())}"
        )
    # No empty bars — design § Decision 2 lock.
    assert dim["score_a"] not in (0, None), (
        f"dimensions[{idx}] (`{dim['key']}`) score_a is {dim['score_a']!r} — "
        f"design § Decision 2 forbids emitting incomplete-data dimensions."
    )
    assert dim["score_b"] not in (0, None), (
        f"dimensions[{idx}] (`{dim['key']}`) score_b is {dim['score_b']!r} — "
        f"design § Decision 2 forbids emitting incomplete-data dimensions."
    )
    assert dim["confidence"] in ("high", "medium", "low"), (
        f"dimensions[{idx}] confidence `{dim['confidence']!r}` not in "
        f"high/medium/low (§ Decision 2 enum)."
    )


def assert_calibrated_score(score: Any, label: str) -> None:
    """Design § Decision 4 — calibrated scores live in 70-95 range (60-95 absolute floor)."""
    assert isinstance(score, (int, float)), (
        f"{label} must be numeric, got {type(score).__name__}: {score!r}"
    )
    assert 60 <= score <= 95, (
        f"{label}={score} outside calibrated range [60, 95]. "
        f"Per § Decision 4 above-average products land 70-95; floor 60."
    )


# ----------------------------------------------------------------------
# Task 4.1 — original-failure-case e2e
# ----------------------------------------------------------------------

@pytest.mark.integration
def test_original_failure_case_mouse_vs_keyboard():
    """
    The Glorious-vs-Ducky walkthrough that motivated Bundle E.
    Design doc § Section 1 captures the 9-symptom regression table; this
    e2e validates the structural fixes (symptoms #2, #3, #4, #5, #9).
    """
    payload = fetch_comparison("Glorious Model O vs Ducky One 2 Mini")
    scoring = find_scoring_v2(payload)

    # § Decision 2 — overall_score + dimensions[] present.
    overall = scoring.get("overall_score") or {}
    assert "product_a" in overall and "product_b" in overall, (
        f"scoring.overall_score missing product_a/product_b. Got: {overall!r}"
    )
    assert_calibrated_score(overall["product_a"], "overall_score.product_a")
    assert_calibrated_score(overall["product_b"], "overall_score.product_b")

    # § Decision 2 — always 3 core dimensions: price + reviews + value.
    dims = scoring.get("dimensions") or []
    assert isinstance(dims, list) and len(dims) >= 3, (
        f"scoring.dimensions must have ≥3 entries, got {len(dims)}: "
        f"{[d.get('key') for d in dims]}"
    )

    core = [d for d in dims if d.get("is_core")]
    core_keys = {d.get("key") for d in core}
    for required in ("price", "reviews", "value"):
        assert required in core_keys, (
            f"Core dimension `{required}` missing. Core keys: {core_keys}. "
            "§ Decision 2 locks Price + Reviews + Value as always-emitted."
        )

    # § Decision 2 — no dimension with missing-data bar (zero/null on either side).
    for i, dim in enumerate(dims):
        assert_dimension_complete(dim, i)

    # § Decision 5 — no banned vocab in any delta_text.
    assert_no_banned_vocab(scoring)

    # § Decision 7 — overall_confidence apologetic pill removed.
    fact_check = payload.get("fact_check") or {}
    assert "overall_confidence" not in fact_check, (
        f"fact_check.overall_confidence must be dropped per § Decision 7 — "
        f"per-dimension confidence is the only confidence surface. "
        f"Got fact_check keys: {sorted(fact_check.keys())}"
    )


# ----------------------------------------------------------------------
# Task 4.1 — additional category coverage
# ----------------------------------------------------------------------

@pytest.mark.integration
def test_cross_category_skincare_vs_supplement_universal_dims_only():
    """
    When the two products belong to incompatible categories, the response
    must still ship a complete card with the 3 core dimensions, but should
    NOT emit a category-specific contextual dimension (would be apples-to-oranges).
    """
    payload = fetch_comparison("CeraVe moisturizer vs HealthAid vitamin D")
    scoring = find_scoring_v2(payload)
    dims = scoring.get("dimensions") or []

    core_keys = {d["key"] for d in dims if d.get("is_core")}
    for required in ("price", "reviews", "value"):
        assert required in core_keys, (
            f"Cross-category compare missing core `{required}`. Core: {core_keys}"
        )

    # No contextual dimension should be a category-specific spec
    # (e.g. dpi/rgb/spf/dosage) when the categories don't match.
    category_specific = {"dpi", "rgb", "spf", "dosage", "polling_rate", "battery_life"}
    contextual_keys = {d["key"] for d in dims if not d.get("is_core")}
    leaked = contextual_keys & category_specific
    assert not leaked, (
        f"Cross-category response leaked category-specific dims: {leaked}. "
        "§ Decision 2: category-specific dims only emitted when BOTH products have the spec."
    )

    # Every emitted dimension must still be complete.
    for i, dim in enumerate(dims):
        assert_dimension_complete(dim, i)
    assert_no_banned_vocab(scoring)


@pytest.mark.integration
def test_same_category_mouse_vs_mouse_has_category_extras():
    """
    Two products in the same category (mice) — we expect at least one
    contextual dimension on top of the 3 core (DPI, polling rate, etc.)
    per § Decision 2 "category-specific — only when BOTH products have the spec".
    """
    payload = fetch_comparison("Logitech G Pro X Superlight vs Glorious Model O")
    scoring = find_scoring_v2(payload)
    dims = scoring.get("dimensions") or []

    assert len(dims) >= 4, (
        f"Same-category compare should ship ≥4 dimensions (3 core + ≥1 contextual), "
        f"got {len(dims)}: {[d.get('key') for d in dims]}"
    )

    contextual = [d for d in dims if not d.get("is_core")]
    assert len(contextual) >= 1, (
        f"Same-category compare expected ≥1 contextual dim, got 0. "
        f"All keys: {[d.get('key') for d in dims]}"
    )

    for i, dim in enumerate(dims):
        assert_dimension_complete(dim, i)
    assert_no_banned_vocab(scoring)


# ----------------------------------------------------------------------
# Task 4.1 — backward-compat with legacy clients (1 release cycle window)
# ----------------------------------------------------------------------

@pytest.mark.integration
def test_legacy_scoring_keys_still_emitted_for_one_cycle():
    """
    Design § Decision 2 "Backward compatibility": old clients reading
    `price_score`, `spec_score`, etc. keep working — backend continues to
    emit legacy keys ALONGSIDE the new `dimensions[]` for one release cycle.
    Bundle F removes legacy keys; until then this test guards old TestFlight
    builds in the field.
    """
    payload = fetch_comparison("Logitech G Pro X Superlight vs Glorious Model O")
    scoring = payload.get("scoring") or {}
    # Legacy keys may live either on scoring or in `scoring.per_product[*]` —
    # this assertion is intentionally permissive: we accept either shape as
    # long as ONE of the legacy markers survives.
    legacy_markers = ("price_score", "spec_score", "score_breakdown")
    has_legacy = any(
        _walk_for_key(payload, marker) for marker in legacy_markers
    )
    assert has_legacy, (
        f"None of the legacy scoring markers {legacy_markers} found in response. "
        f"Top-level scoring keys: {sorted(scoring.keys()) if isinstance(scoring, dict) else type(scoring).__name__}. "
        "Bundle E must keep emitting legacy keys for one release cycle (§ Decision 2)."
    )


def _walk_for_key(obj: Any, key: str) -> bool:
    """Recursive search — legacy markers can live nested under products[i]."""
    if isinstance(obj, dict):
        if key in obj:
            return True
        return any(_walk_for_key(v, key) for v in obj.values())
    if isinstance(obj, list):
        return any(_walk_for_key(v, key) for v in obj)
    return False


# ----------------------------------------------------------------------
# Task 4.1 — Phase 0 fix non-regression
# ----------------------------------------------------------------------

@pytest.mark.integration
def test_history_schema_filter_still_excludes_v1():
    """
    Migration 020 schema_version gate (Bundle B/C/D) — history list/count/get
    filter on `schema_version=2`. Bundle E must not regress this; a v1 row
    being returned to the client would re-introduce the symptom #8 crash
    even with the new defensive guard in place.

    This test is currently a smoke check (anonymous compare returns no
    history) — full coverage lives in `test_history_routes.py` and
    `test_share_endpoint.py`. Re-enable when bundle-e adds an auth path
    in Task 4.1.
    """
    # Anonymous endpoint smoke — comparisons created without auth do not land
    # in `comparisons` and therefore never surface to history. The contract
    # we guard here is "Bundle E doesn't drop the schema_version filter."
    payload = fetch_comparison("AirPods Pro vs Sony WF-1000XM5")
    # If schema_version is exposed on the response (some routes echo it),
    # it must be 2 — never 1.
    schema_version = payload.get("schema_version")
    if schema_version is not None:
        assert schema_version == 2, (
            f"Response schema_version={schema_version}, expected 2. "
            "Bundle B/C/D Migration 020 contract regressed."
        )
