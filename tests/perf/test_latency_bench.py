"""
Bundle E latency benchmark — 20 cold queries against Railway preview /stream.

Targets (design § Decision 9):
    P50 first_paint   ≤ 10s
    P95 first_paint   ≤ 14s
    P95 settle_complete ≤ 25s  (hard cap — backend kills SSE)

RED until Phase 2 ships scatter-gather + new SSE event types
(`first_paint`, `settle_update`, `settle_complete`, `confidence_upgrade`).

Cost: 20 cold queries × ~$0.01 ≈ $0.20 per run. Gated by both
`@pytest.mark.bench` AND a `BENCH=1` env var so accidental runs in CI/dev
don't burn credits. Final-gate use is Task 4.5.

Run:
    BENCH=1 python -m pytest tests/perf/test_latency_bench.py -v --timeout=600 -m bench

Runbook + interpretation: docs/runbooks/bundle-e-perf-bench.md (Task 4.5).
"""
from __future__ import annotations

import json
import os
import statistics
import time
from dataclasses import dataclass

import httpx
import pytest

BASE_URL = "https://web-production-58776.up.railway.app"
STREAM_PATH = "/api/v1/text/compare/stream"
STREAM_TIMEOUT = 60.0  # per-query upper bound; hard cap is 25s server-side
N_COLD_QUERIES = 20

# Varied categories ensure no single cache key inflates P50 — design §
# Decision 9 measures cold-cache behaviour. Mix of supplements / luxury /
# electronics / fashion / grocery hits the full scraper fan-out.
COLD_QUERIES: tuple[str, ...] = (
    "Glorious Model O vs Ducky One 2 Mini",          # original failure case
    "iPhone 15 Pro vs Samsung Galaxy S24 Ultra",     # warm electronics
    "Sony WH-1000XM5 vs Bose QC Ultra",              # audio
    "Dyson V15 Detect vs Shark Stratos",             # appliances
    "Nespresso Vertuo vs Breville Bambino",          # kitchen
    "CeraVe SA cleanser vs La Roche-Posay Effaclar", # skincare
    "HealthAid Vitamin D vs Now Foods Vitamin D",    # supplements
    "Louis Vuitton Neverfull vs Hermes Garden",      # luxury (SPA scrapers)
    "Logitech G Pro X Superlight vs Razer Viper",    # gaming peripherals
    "Theragun Pro vs Hyperice Hypervolt 2",          # wellness
    "Patek Philippe Calatrava vs Rolex Datejust",    # luxury watches
    "Tesla Model 3 vs BYD Seal",                     # auto
    "Hellmann's mayo vs Heinz mayo",                 # grocery
    "Olaplex No. 3 vs K18 mask",                     # haircare
    "Chanel No. 5 vs Dior J'adore",                  # fragrance
    "Tropicana orange juice vs Almarai orange juice",# regional grocery
    "Apple Watch Ultra 2 vs Garmin Fenix 7",         # wearables
    "Adidas Ultraboost vs Nike Pegasus",             # fashion footwear
    "MacBook Air M3 vs Dell XPS 13",                 # laptops
    "PS5 Slim vs Xbox Series X",                     # consoles
)


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------

@dataclass(frozen=True)
class StreamTiming:
    query: str
    first_paint_ms: float | None
    settle_complete_ms: float | None
    error: str | None = None

    @property
    def first_paint_s(self) -> float | None:
        return None if self.first_paint_ms is None else self.first_paint_ms / 1000.0

    @property
    def settle_complete_s(self) -> float | None:
        return None if self.settle_complete_ms is None else self.settle_complete_ms / 1000.0


def _parse_sse_event(raw_line: str) -> tuple[str | None, dict | None]:
    """SSE wire format: `event: <name>\\n` then `data: <json>\\n\\n`."""
    if raw_line.startswith("event:"):
        return raw_line[len("event:"):].strip(), None
    if raw_line.startswith("data:"):
        body = raw_line[len("data:"):].strip()
        try:
            return None, json.loads(body)
        except json.JSONDecodeError:
            return None, {"_raw": body}
    return None, None


def measure_stream(query: str) -> StreamTiming:
    """
    Open the SSE stream, capture wall-clock to first_paint + settle_complete.
    Returns timings in milliseconds (None if event never arrived).
    """
    started = time.perf_counter()
    first_paint_ms: float | None = None
    settle_complete_ms: float | None = None
    current_event: str | None = None

    try:
        with httpx.stream(
            "GET",
            f"{BASE_URL}{STREAM_PATH}",
            params={"q": query, "nocache": "true"},
            timeout=STREAM_TIMEOUT,
        ) as response:
            response.raise_for_status()
            for raw in response.iter_lines():
                if not raw:
                    current_event = None
                    continue
                event, _data = _parse_sse_event(raw)
                if event is not None:
                    current_event = event
                    elapsed_ms = (time.perf_counter() - started) * 1000.0
                    if event == "first_paint" and first_paint_ms is None:
                        first_paint_ms = elapsed_ms
                    elif event in ("settle_complete", "complete") and settle_complete_ms is None:
                        # Accept legacy `complete` event per § Decision 8
                        # backward-compat ("existing `complete` event still
                        # fired at settle_complete").
                        settle_complete_ms = elapsed_ms
                # data: lines without preceding event: keep the event open
    except httpx.HTTPError as exc:
        return StreamTiming(query=query, first_paint_ms=None, settle_complete_ms=None, error=str(exc))

    return StreamTiming(
        query=query,
        first_paint_ms=first_paint_ms,
        settle_complete_ms=settle_complete_ms,
    )


def _quantile(samples: list[float], p: float) -> float:
    """Inclusive percentile across a sorted sample list (statistics.quantiles
    needs >1 sample and uses exclusive method — we want the simpler
    inclusive nearest-rank for the small N=20 case)."""
    if not samples:
        raise ValueError("no samples")
    ordered = sorted(samples)
    if len(ordered) == 1:
        return ordered[0]
    # nearest-rank: rank = ceil(p * N), 1-indexed
    rank = max(1, int(round(p * len(ordered))))
    return ordered[min(rank, len(ordered)) - 1]


# ----------------------------------------------------------------------
# Tests — bench-gated
# ----------------------------------------------------------------------

_BENCH_ENABLED = os.environ.get("BENCH") == "1"
_BENCH_REASON = "BENCH=1 not set — perf bench skipped to avoid burning Railway credits."


@pytest.mark.bench
@pytest.mark.skipif(not _BENCH_ENABLED, reason=_BENCH_REASON)
def test_latency_first_paint_p50_p95():
    """
    20 cold queries — assert P50 ≤ 10s AND P95 ≤ 14s on first_paint event.
    Design § Decision 9 latency table (cold-no-luxury 8-12s, cold-luxury
    12-13s) sets the targets.
    """
    timings: list[StreamTiming] = []
    for q in COLD_QUERIES[:N_COLD_QUERIES]:
        timings.append(measure_stream(q))

    # Surface any per-query errors so the report doesn't silently mask them.
    errors = [t for t in timings if t.error is not None]
    assert not errors, (
        f"{len(errors)}/{N_COLD_QUERIES} queries errored mid-stream — "
        f"first 3: {[ (t.query, t.error) for t in errors[:3] ]}"
    )

    first_paints = [t.first_paint_s for t in timings if t.first_paint_s is not None]
    assert len(first_paints) >= int(0.9 * N_COLD_QUERIES), (
        f"first_paint event missing on {N_COLD_QUERIES - len(first_paints)}/{N_COLD_QUERIES} "
        f"queries — backend likely not yet emitting `first_paint` (Phase 2 RED)."
    )

    p50 = statistics.median(first_paints)
    p95 = _quantile(first_paints, 0.95)

    assert p50 <= 10.0, (
        f"P50 first_paint = {p50:.2f}s exceeds 10s budget (§ Decision 9). "
        f"Samples: {[round(s, 2) for s in sorted(first_paints)]}"
    )
    assert p95 <= 14.0, (
        f"P95 first_paint = {p95:.2f}s exceeds 14s budget (§ Decision 9). "
        f"Samples: {[round(s, 2) for s in sorted(first_paints)]}"
    )


@pytest.mark.bench
@pytest.mark.skipif(not _BENCH_ENABLED, reason=_BENCH_REASON)
def test_latency_settle_complete_hard_cap_25s():
    """
    Backend MUST kill the SSE stream at 25s regardless of in-flight work
    (§ Decision 9 hard cap). P95 settle_complete proves the killer is wired.
    """
    timings: list[StreamTiming] = []
    for q in COLD_QUERIES[:N_COLD_QUERIES]:
        timings.append(measure_stream(q))

    settles = [t.settle_complete_s for t in timings if t.settle_complete_s is not None]
    assert len(settles) >= int(0.9 * N_COLD_QUERIES), (
        f"settle_complete event missing on {N_COLD_QUERIES - len(settles)}/{N_COLD_QUERIES} "
        f"queries — backend not yet emitting `settle_complete` (Phase 2 RED) "
        f"OR streams timing out past the 25s cap."
    )

    p95 = _quantile(settles, 0.95)
    assert p95 <= 25.0, (
        f"P95 settle_complete = {p95:.2f}s exceeds 25s hard cap (§ Decision 9). "
        f"Samples: {[round(s, 2) for s in sorted(settles)]}"
    )


@pytest.mark.bench
@pytest.mark.skipif(not _BENCH_ENABLED, reason=_BENCH_REASON)
def test_warm_cache_first_paint_under_3s():
    """
    Design § Success Criteria: "Comparing two iPhones (warm cache, same
    category) hits ≤3s first paint." Run the same query twice — second hit
    must return on warm cache.
    """
    query = "iPhone 15 Pro vs Samsung Galaxy S24 Ultra"
    # Prime the cache (this counts toward cost; mark as nocache=true would
    # defeat the test).
    _ = httpx.get(
        f"{BASE_URL}/api/v1/text/compare",
        params={"q": query, "nocache": "false"},
        timeout=STREAM_TIMEOUT,
    )
    warm = measure_stream(query.replace("vs", "vs"))  # same query, warm cache
    assert warm.first_paint_s is not None, (
        f"Warm-cache run missing first_paint event entirely. Error: {warm.error}"
    )
    assert warm.first_paint_s <= 3.0, (
        f"Warm-cache first_paint = {warm.first_paint_s:.2f}s exceeds 3s budget "
        "(§ Success Criteria). Cache integration regressed or Phase 2 not yet wired."
    )
