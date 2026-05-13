"""
Bundle E Task 2.2 RED — fan_out_price_lookup() runs scrapers concurrently
and cancels still-pending scrapers when a confirmed high-rank price lands.

Plan: docs/plans/2026-05-13-results-quality-overhaul.md (§ Agent A Task 2.2,
      § Test-2.2, § Hard rules line 150)
Design: docs/plans/2026-05-13-results-quality-overhaul-design.md § Decision 8.

Contract under test (inferred from plan task list + design fan-out diagram):

    async def fan_out_price_lookup(
        product: dict,
        scrapers: list[Callable[[dict], Awaitable[dict | None]]] | None = None,
        scraping_mode: str = "hard",
    ) -> dict:
        \"\"\"Fans out all price scrapers concurrently. Cancels in-flight
        scrapers when a confirmed high-rank result lands (rank ≥85 OR 2+
        sources agree within 5%). Returns the selected best candidate
        (via select_best_price from quality_ranker) plus alternates.

        Returns:
          {
            "best": {value, source_method, rank, raw_data},
            "alternates": [{...}, ...],     # non-selected candidates
            "cancelled_count": int,         # how many scrapers were
                                            #   cancelled (for credit tracking)
            "elapsed_seconds": float,
          }
        \"\"\"

Key invariants:
  1. Wall-clock concurrency: total elapsed time < sum of individual scraper
     times. Spec quote (design line 358): "Fan-out (all concurrent)".
  2. Cancellation: when 2 sources agree within 5% OR a single rank≥85
     result lands, still-running scrapers get cancelled. Spec quote
     (design line 403): "When confirmed price lands (rank ≥85 OR 2
     sources agree), still-running scrapers for that product's price
     get cancelled to save credits."
  3. Spec quote (plan line 150): "fan_out_price_lookup MUST cancel
     still-pending scrapers when 2+ sources confirm within 5%."

RED→GREEN trajectory:
  - At HEAD: `app.services.price_service.fan_out_price_lookup` does
    not exist → ImportError at collection → RED.
  - Post-Task-2.2: assertions GREEN.

Note on signature inference: plan + design pin BEHAVIOR (parallelism +
cancellation) but not the exact callable shape. I have inferred a
"caller-provides-list-of-scrapers" injectable shape so the tests can
hand in synthetic scrapers with controlled timing. Agent A may instead
choose a "scrapers are private to the module" shape that calls the real
firecrawl/serper services — in which case this RED file's mocking
strategy needs adjustment via SEND-BACK. The behavioral asserts
(concurrency, cancellation, elapsed time) transfer regardless.
"""

from __future__ import annotations

import asyncio
import time

import pytest

# RED gate — function does not yet exist.
from app.services.price_service import fan_out_price_lookup  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers — synthetic async scrapers with controlled timing
# ---------------------------------------------------------------------------

def _make_scraper(value: float, source_method: str, rank: int, delay: float,
                  cancel_marker: list[str] | None = None,
                  name: str | None = None):
    """Build an async scraper that sleeps `delay` seconds then returns a
    candidate dict. Optionally appends to `cancel_marker` when the
    scraper IS cancelled (asyncio.CancelledError handler)."""
    label = name or source_method

    async def _scraper(_product: dict) -> dict | None:
        try:
            await asyncio.sleep(delay)
            return {
                "value": value,
                "source_method": source_method,
                "rank": rank,
                "raw_data": {"label": label, "delay": delay},
            }
        except asyncio.CancelledError:
            if cancel_marker is not None:
                cancel_marker.append(label)
            raise

    return _scraper


def _product():
    return {
        "brand": "Glorious", "name": "Model O",
        "category": "electronics",
        "price": None,  # to be filled by scrapers
    }


# ---------------------------------------------------------------------------
# Test 1 — Concurrent fan-out (wall-clock < sum of delays)
# ---------------------------------------------------------------------------

class TestConcurrentFanOut:
    """Design line 358: 'Fan-out (all concurrent)'. Total elapsed wall-
    clock time must be ≪ the sum of individual scraper times."""

    @pytest.mark.asyncio
    async def test_three_scrapers_run_in_parallel_not_serial(self):
        """3 scrapers at 0.3s each → serial would take ~0.9s; parallel
        should land in ~0.3s + small overhead. We assert elapsed < 0.6s
        — comfortably below sum (0.9s) while tolerating CI jitter."""
        scrapers = [
            _make_scraper(22.0, "serper_shopping", 75, delay=0.3,
                          name="serper"),
            _make_scraper(22.5, "page_scrape_jsonld", 85, delay=0.3,
                          name="page_scrape"),
            _make_scraper(23.0, "firecrawl_brand_domain", 90, delay=0.3,
                          name="firecrawl"),
        ]
        start = time.monotonic()
        result = await fan_out_price_lookup(_product(), scrapers=scrapers,
                                            scraping_mode="hard")
        elapsed = time.monotonic() - start
        # Serial would take ~0.9s. Parallel should be ~0.3s + overhead.
        # 0.6s is the upper bound — anything above suggests serial execution.
        assert elapsed < 0.6, (
            f"fan-out appears serial: elapsed={elapsed:.3f}s, "
            f"sum-of-delays=0.9s. Should be ~0.3s with concurrency."
        )
        # Sanity: result has a `best` key with a candidate dict.
        assert result is not None and "best" in result

    @pytest.mark.asyncio
    async def test_elapsed_seconds_in_returned_dict(self):
        """The returned dict must include `elapsed_seconds` for credit
        tracking + perf monitoring per design § Decision 8."""
        scrapers = [
            _make_scraper(22.0, "serper_shopping", 75, delay=0.1, name="s"),
        ]
        result = await fan_out_price_lookup(_product(), scrapers=scrapers,
                                            scraping_mode="hard")
        assert "elapsed_seconds" in result
        assert isinstance(result["elapsed_seconds"], (int, float))
        assert result["elapsed_seconds"] >= 0


# ---------------------------------------------------------------------------
# Test 2 — Cancellation on confirmed multi-source agreement
# ---------------------------------------------------------------------------

class TestCancellationOnConfirmed:
    """Design line 403: 'When confirmed price lands (rank ≥85 OR 2 sources
    agree), still-running scrapers for that product's price get cancelled
    to save credits.'"""

    @pytest.mark.asyncio
    async def test_two_agreeing_sources_cancel_late_scraper(self):
        """First 2 scrapers return within 5% within 0.1s. The 3rd
        scraper takes 2s — must be cancelled. Assert cancel_marker
        records that 3rd scraper hit its CancelledError handler."""
        cancelled: list[str] = []
        scrapers = [
            _make_scraper(22.0, "firecrawl_brand_domain", 90, delay=0.05,
                          cancel_marker=cancelled, name="firecrawl"),
            _make_scraper(22.3, "page_scrape_jsonld", 85, delay=0.05,
                          cancel_marker=cancelled, name="page_scrape"),
            _make_scraper(99.0, "scrapedo_rendered", 70, delay=2.0,
                          cancel_marker=cancelled, name="scrapedo_slow"),
        ]
        result = await fan_out_price_lookup(_product(), scrapers=scrapers,
                                            scraping_mode="hard")
        # The slow scraper must have been cancelled.
        assert "scrapedo_slow" in cancelled, (
            f"slow scraper not cancelled despite 2 sources agreeing within 5%. "
            f"cancelled list: {cancelled}"
        )
        # Spec: returned dict reports how many were cancelled.
        assert result.get("cancelled_count", 0) >= 1

    @pytest.mark.asyncio
    async def test_single_high_rank_result_cancels_low_rank_pending(self):
        """A single rank-90 result (firecrawl_brand_domain) lands fast.
        Per design line 403 ('rank ≥85 OR 2 sources agree'), this alone
        is enough to cancel still-pending lower-rank scrapers — saves
        Scrape.do credits."""
        cancelled: list[str] = []
        scrapers = [
            # Fast high-rank winner.
            _make_scraper(22.0, "firecrawl_brand_domain", 90, delay=0.05,
                          cancel_marker=cancelled, name="firecrawl"),
            # Slow low-rank — must be cancelled.
            _make_scraper(99.0, "gpt_training_estimate", 40, delay=2.0,
                          cancel_marker=cancelled, name="gpt_slow"),
        ]
        result = await fan_out_price_lookup(_product(), scrapers=scrapers,
                                            scraping_mode="hard")
        assert "gpt_slow" in cancelled, (
            f"low-rank slow scraper not cancelled despite rank≥85 confirmed "
            f"price. cancelled={cancelled}"
        )

    @pytest.mark.asyncio
    async def test_no_cancellation_when_only_low_rank_results(self):
        """If only low-rank scrapers run (no rank≥85, no 2-source
        agreement), all scrapers must complete — no premature cancel."""
        cancelled: list[str] = []
        scrapers = [
            _make_scraper(22.0, "gpt_organic_extract", 60, delay=0.05,
                          cancel_marker=cancelled, name="gpt_a"),
            _make_scraper(99.0, "gpt_training_estimate", 40, delay=0.15,
                          cancel_marker=cancelled, name="gpt_b"),
        ]
        await fan_out_price_lookup(_product(), scrapers=scrapers,
                                   scraping_mode="hard")
        # Neither met the confirmed threshold (rank≥85, no agreement)
        # so both should complete cleanly.
        assert cancelled == [], (
            f"premature cancellation when no confirmed result: {cancelled}"
        )


# ---------------------------------------------------------------------------
# Test 3 — Returned shape
# ---------------------------------------------------------------------------

class TestReturnedShape:
    """Return dict must always include best, alternates, cancelled_count,
    elapsed_seconds — even when only one scraper completes or all fail."""

    @pytest.mark.asyncio
    async def test_returned_dict_has_required_keys(self):
        scrapers = [
            _make_scraper(22.0, "serper_shopping", 75, delay=0.05, name="s"),
            _make_scraper(22.5, "page_scrape_jsonld", 85, delay=0.05, name="p"),
        ]
        result = await fan_out_price_lookup(_product(), scrapers=scrapers,
                                            scraping_mode="hard")
        required = {"best", "alternates", "cancelled_count", "elapsed_seconds"}
        missing = required - set(result.keys())
        assert not missing, (
            f"fan_out_price_lookup return dict missing keys: {missing}"
        )

    @pytest.mark.asyncio
    async def test_alternates_excludes_the_selected_best(self):
        """If 3 candidates land, `best` is one of them and `alternates`
        is the other 2 (or however many non-selected). Sum total ≤ 3."""
        scrapers = [
            _make_scraper(22.0, "firecrawl_brand_domain", 90, delay=0.05),
            _make_scraper(99.0, "serper_shopping", 75, delay=0.05),
        ]
        result = await fan_out_price_lookup(_product(), scrapers=scrapers,
                                            scraping_mode="hard")
        if result["best"]:
            # Best is one of the scrapers' values; alternates is the rest.
            best_method = result["best"]["source_method"]
            for alt in result["alternates"]:
                assert alt["source_method"] != best_method, (
                    f"alternates list contains the selected best: "
                    f"best={best_method}, alternates={result['alternates']}"
                )

    @pytest.mark.asyncio
    async def test_empty_scrapers_returns_none_best(self):
        """No scrapers → no result. Function must not crash; returns
        best=None so caller can render 'Price unavailable'."""
        result = await fan_out_price_lookup(_product(), scrapers=[],
                                            scraping_mode="hard")
        assert result["best"] is None
        assert result["alternates"] == []
        assert result["cancelled_count"] == 0


# ---------------------------------------------------------------------------
# Verification harness
# ---------------------------------------------------------------------------
# Pre-Task-2.2 run:
#     python -m pytest tests/test_scatter_gather_price.py -v
#     → ImportError on `fan_out_price_lookup` → RED
#
# Post-Task-2.2: 3 test classes, ~8 assertions. Coverage target ≥80%.
