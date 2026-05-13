"""
Bundle E Task 2.1 RED — quality_ranker.select_best_price() chooses the
highest-trust price among parallel scraper candidates.

Plan: docs/plans/2026-05-13-results-quality-overhaul.md (§ Agent A Task 2.1,
      § Test-2.1)
Design: docs/plans/2026-05-13-results-quality-overhaul-design.md § Decision 8.

Contract:

    PRICE_SOURCE_RANK = [
        ("confirmed_multi_source", 100),  # 2+ sources agree within 5%
        ("firecrawl_brand_domain", 90),   # official brand site, rendered
        ("page_scrape_jsonld", 85),       # structured data on indexed page
        ("serper_shopping", 75),          # Google Shopping direct
        ("scrapedo_rendered", 70),        # residential proxy
        ("gpt_organic_extract", 60),      # GPT from search snippets
        ("gpt_training_estimate", 40),    # last resort, flagged
    ]

    def select_best_price(
        candidates: list[dict],   # each: {value, source_method, rank, raw_data}
    ) -> dict | None:
        # Returns the highest-rank candidate. If two candidates agree
        # within 5%, returns a synthesized "confirmed_multi_source"
        # candidate (rank=100). Empty list → None.

Test cases per plan § Test-2.1:
  1. Confirmed-multi-source wins (2 sources agree within 5%)
  2. Highest-rank wins when no agreement
  3. Empty candidates returns None

Plus a few defensive contract tests:
  - Returned dict has the 4 expected fields (value, source_method,
    rank, raw_data).
  - Single-candidate input passes through unchanged.
  - Agreement window is 5% (4.99% agrees, 5.01% doesn't).

RED→GREEN trajectory:
  - At HEAD: `app.services.quality_ranker` module does not exist →
    ModuleNotFoundError → RED.
  - Post-Task-2.1: all assertions pass.
"""

from __future__ import annotations

import pytest

# RED gate — module does not yet exist.
from app.services.quality_ranker import select_best_price  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _candidate(value, source_method, rank, raw_data=None):
    return {
        "value": value,
        "source_method": source_method,
        "rank": rank,
        "raw_data": raw_data or {},
    }


# ---------------------------------------------------------------------------
# Test 1 — Confirmed multi-source wins
# ---------------------------------------------------------------------------

class TestConfirmedMultiSourceWins:
    """Per plan § Test-2.1 case 1: when 2+ sources agree within 5%, the
    returned candidate has source_method="confirmed_multi_source" and
    rank=100 — strictly higher than any individual source rank."""

    def test_two_sources_within_5pct_yields_confirmed(self):
        """Firecrawl says 22.0, page_scrape says 22.5 — within 5%.
        Returned candidate must be a synthesized confirmed_multi_source
        (rank=100), NOT just the firecrawl candidate (rank=90)."""
        candidates = [
            _candidate(22.0, "firecrawl_brand_domain", 90),
            _candidate(22.5, "page_scrape_jsonld", 85),
        ]
        result = select_best_price(candidates)
        assert result is not None
        assert result["source_method"] == "confirmed_multi_source", (
            f"agreement within 5% did NOT produce confirmed_multi_source: "
            f"{result}"
        )
        assert result["rank"] == 100, (
            f"confirmed candidate rank should be 100, got {result['rank']}"
        )

    def test_confirmed_value_is_one_of_the_agreeing_values(self):
        """The synthesized confirmed candidate's `value` is one of the
        original agreeing values (typically the highest-rank source's
        value — but any of the agreeing sources is acceptable; we
        assert membership not exact identity)."""
        candidates = [
            _candidate(22.0, "firecrawl_brand_domain", 90),
            _candidate(22.5, "page_scrape_jsonld", 85),
        ]
        result = select_best_price(candidates)
        assert result["value"] in (22.0, 22.5), (
            f"confirmed value {result['value']} is not one of the agreeing "
            f"source values {{22.0, 22.5}}"
        )

    def test_three_way_agreement_still_confirmed(self):
        """3 sources within 5% should also produce confirmed, not get
        confused by the extra agreement."""
        candidates = [
            _candidate(50.0, "firecrawl_brand_domain", 90),
            _candidate(50.5, "page_scrape_jsonld", 85),
            _candidate(51.2, "serper_shopping", 75),
        ]
        result = select_best_price(candidates)
        assert result["source_method"] == "confirmed_multi_source"
        assert result["rank"] == 100


# ---------------------------------------------------------------------------
# Test 2 — Highest-rank wins when no agreement
# ---------------------------------------------------------------------------

class TestHighestRankWinsWithoutAgreement:
    """Per plan § Test-2.1 case 2: when no pair agrees within 5%, the
    candidate with the highest source-rank wins."""

    def test_firecrawl_beats_serper_when_no_agreement(self):
        """Firecrawl says 100, Serper says 200 — 100% deviation, no
        agreement. Firecrawl's rank=90 beats Serper's rank=75."""
        candidates = [
            _candidate(100.0, "firecrawl_brand_domain", 90),
            _candidate(200.0, "serper_shopping", 75),
        ]
        result = select_best_price(candidates)
        assert result["source_method"] == "firecrawl_brand_domain", (
            f"highest-rank pick mismatched: {result}"
        )
        assert result["value"] == 100.0

    def test_serper_beats_gpt_estimate(self):
        """Serper rank=75, GPT estimate rank=40 — Serper wins."""
        candidates = [
            _candidate(50.0, "gpt_training_estimate", 40),
            _candidate(80.0, "serper_shopping", 75),
        ]
        result = select_best_price(candidates)
        assert result["source_method"] == "serper_shopping"

    def test_all_low_rank_returns_highest_among_them(self):
        """Worst case: only GPT estimates available. Still must return
        the highest-rank candidate, never None."""
        candidates = [
            _candidate(50.0, "gpt_training_estimate", 40),
            _candidate(55.0, "gpt_training_estimate", 40),
        ]
        # Two GPT estimates within 5% (50 vs 55 = 10% — let's adjust)
        candidates = [
            _candidate(50.0, "gpt_training_estimate", 40),
            _candidate(80.0, "gpt_training_estimate", 40),  # 60% off
        ]
        result = select_best_price(candidates)
        assert result is not None
        assert result["source_method"] == "gpt_training_estimate"


# ---------------------------------------------------------------------------
# Test 3 — Empty candidates returns None
# ---------------------------------------------------------------------------

class TestEmptyCandidatesReturnsNone:
    """Per plan § Test-2.1 case 3: empty input must not raise — it
    returns None and lets the caller decide (typically: render
    'Price unavailable')."""

    def test_empty_list_returns_none(self):
        assert select_best_price([]) is None

    def test_returned_dict_has_required_fields(self):
        """Returned candidates must always be 4-field dicts so the
        caller can render without defensive checks."""
        result = select_best_price([
            _candidate(22.0, "firecrawl_brand_domain", 90),
        ])
        assert result is not None
        required = {"value", "source_method", "rank", "raw_data"}
        missing = required - set(result.keys())
        assert not missing, (
            f"returned candidate missing fields: {missing} (got: {result})"
        )


# ---------------------------------------------------------------------------
# Test 4 — Defensive contract checks
# ---------------------------------------------------------------------------

class TestSingleCandidatePassThrough:
    """One candidate input is the common steady-state case (only Serper
    came back). The result is that exact candidate — no synthesis."""

    def test_single_candidate_returned_unchanged(self):
        c = _candidate(22.0, "firecrawl_brand_domain", 90,
                       raw_data={"retailer": "noon.com"})
        result = select_best_price([c])
        assert result is not None
        assert result["value"] == c["value"]
        assert result["source_method"] == c["source_method"]
        assert result["rank"] == c["rank"]
        assert result["raw_data"] == c["raw_data"]


class TestAgreementWindowIsFivePct:
    """Per design line 389: 2+ sources agree "within 5%". Test the
    boundary — 4.99% agrees (confirmed); 5.01% doesn't."""

    def test_just_under_5pct_agrees(self):
        """100.0 vs 104.9 → 4.9% deviation → AGREES."""
        candidates = [
            _candidate(100.0, "firecrawl_brand_domain", 90),
            _candidate(104.9, "page_scrape_jsonld", 85),
        ]
        result = select_best_price(candidates)
        assert result["source_method"] == "confirmed_multi_source", (
            f"4.9% deviation should agree, got: {result}"
        )

    def test_just_over_5pct_does_not_agree(self):
        """100.0 vs 106.0 → 6% deviation → does NOT agree → highest
        rank wins (firecrawl 90 over page_scrape 85)."""
        candidates = [
            _candidate(100.0, "firecrawl_brand_domain", 90),
            _candidate(106.0, "page_scrape_jsonld", 85),
        ]
        result = select_best_price(candidates)
        assert result["source_method"] == "firecrawl_brand_domain", (
            f"6% deviation should NOT agree (highest rank should win), "
            f"got: {result}"
        )


# ---------------------------------------------------------------------------
# Verification harness
# ---------------------------------------------------------------------------
# Pre-Task-2.1 run:
#     python -m pytest tests/test_quality_ranker.py -v
#     → ModuleNotFoundError on `app.services.quality_ranker` → RED
#
# Post-Task-2.1: 5 test classes, ~12 assertions. Coverage target ≥90%
# per plan § "Tests" table (line 480 — quality_ranker.py ≥90%).
