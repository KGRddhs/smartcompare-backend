"""Bundle E B-S2.idle — cohort + scoring load smoke.

Runs 5x diverse `/api/v1/text/compare` queries back-to-back against live
Railway, asserts no exceptions raised, and asserts p50 wall time stays
under 8 seconds. The query mix spans 5 cohort-relevant categories
(electronics, supplements, skincare, makeup, fragrances) so the test
exercises the full scoring + pricing + extraction pipelines that the
cohort prompt-block joins onto for authenticated users.

Why these markers
-----------------
This test is double-gated so it does NOT run on default CI:

  1. `@pytest.mark.live_unit` — matches the existing convention for
     tests that call live external services (iHerb, Serper, OpenAI).
     Default suite filter `-m "not live_unit"` excludes it.
  2. `RUN_LOAD=1` env gate via `skipif` — even when running the
     live_unit suite, this test only fires when explicitly opted in.
     Reason: 5x compare calls burn ~$0.05 of OpenAI + Serper credits
     plus 5x ~5-15s wall time. Don't want that on every CI run, and
     don't want a teammate running `pytest -m live_unit` to surprise-
     spend the credit budget.

Run explicitly:
    RUN_LOAD=1 python -m pytest tests/test_cohort_personalization_load.py -v --timeout=180 -m live_unit

Cost: ~$0.05. Wall: ~40-60s end-to-end (5 queries x cold-cache average).
"""
from __future__ import annotations

import os
import statistics
import time

import httpx
import pytest


# Live Railway preview deployment per CLAUDE.md `# Backend` section.
BASE_URL = "https://web-production-58776.up.railway.app"

# Per-request timeout — the compare endpoint has a STREAM_HARD_CAP_SECONDS=25
# server-side guard, but cold-cache rare-pair queries can land near that ceiling.
# Add a generous client-side buffer so we measure server time, not timeout chops.
REQUEST_TIMEOUT_SECONDS = 60.0

# Cohort-relevant category sweep — one query per category. Mix is intentional:
# - electronics: high-volume warm-cache path
# - supplements: iHerb scrape path
# - skincare: mid-volume cohort path
# - makeup: lower-volume category coverage
# - fragrances: luxury Tier 1.5 fallback path
LOAD_QUERIES: list[str] = [
    "iPhone 15 vs Samsung Galaxy S24",
    "NOW Foods Vitamin D3 vs HealthAid Vitamin D3",
    "CeraVe Moisturizing Cream vs Cetaphil Moisturizing Cream",
    "Maybelline Fit Me Foundation vs L'Oreal True Match",
    "Tom Ford Tobacco Vanille vs Creed Aventus",
]

# Per dispatcher spec — p50 must stay under 8s.
P50_WALL_BUDGET_SECONDS = 8.0


@pytest.mark.live_unit
@pytest.mark.skipif(
    os.environ.get("RUN_LOAD") != "1",
    reason="opt-in load smoke — set RUN_LOAD=1 to fire (~$0.05 credit burn)",
)
def test_cohort_scoring_load_smoke_5_queries():
    """5x cohort-relevant compare queries back-to-back.

    Asserts:
      1. Every request returns HTTP 200 + valid JSON (no exceptions).
      2. p50 wall time across the 5 queries stays under 8.0s.

    Does NOT assert response shape contract — that's covered by
    test_bundle_e_integration.py + test_endpoint_shapes_vs_jsx.py.
    This test is purely about load + reliability.
    """
    wall_times: list[float] = []
    failures: list[str] = []

    for i, query in enumerate(LOAD_QUERIES):
        start = time.monotonic()
        try:
            response = httpx.get(
                f"{BASE_URL}/api/v1/text/compare",
                params={"q": query, "nocache": "true"},
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
        except Exception as exc:  # noqa: BLE001 — load smoke catches everything
            wall = time.monotonic() - start
            failures.append(
                f"query[{i}]={query!r} raised {type(exc).__name__}: {exc!r} "
                f"after {wall:.2f}s"
            )
            continue

        wall = time.monotonic() - start
        wall_times.append(wall)

        if response.status_code != 200:
            failures.append(
                f"query[{i}]={query!r} HTTP {response.status_code}: "
                f"{response.text[:200]}"
            )
            continue

        # Parse JSON — catches malformed-body failures too.
        try:
            response.json()
        except Exception as exc:  # noqa: BLE001
            failures.append(
                f"query[{i}]={query!r} JSON parse failed: {type(exc).__name__}: {exc!r}"
            )

    # Assert no exceptions / failed responses.
    assert not failures, (
        f"{len(failures)} of {len(LOAD_QUERIES)} cohort-load queries failed:\n"
        + "\n".join(f"  - {f}" for f in failures)
    )

    # Assert p50 wall budget.
    assert len(wall_times) == len(LOAD_QUERIES), (
        f"recorded {len(wall_times)} timings vs {len(LOAD_QUERIES)} queries — "
        f"shape inconsistency suggests a try/except mismatch in the test loop"
    )
    p50 = statistics.median(wall_times)
    assert p50 < P50_WALL_BUDGET_SECONDS, (
        f"p50 wall time {p50:.2f}s exceeds {P50_WALL_BUDGET_SECONDS}s budget. "
        f"All timings: {[f'{w:.2f}s' for w in wall_times]}. "
        f"This is the canary for scoring + cohort prompt-block + pricing "
        f"pipeline regressions under repeated load."
    )
