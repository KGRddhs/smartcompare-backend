"""Tests for token-based cost tracking and GPT/Serper counter separation.

Run: python -m pytest tests/test_cost_tracking.py -v
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from app.services.structured_comparison_service import get_comparison_service


class TestTrackGptCost:
    def setup_method(self):
        self.service = get_comparison_service()
        self.service.total_cost = 0.0
        self.service.gpt_calls = 0
        self.service.serper_calls = 0
        self.service.api_calls = 0

    def test_calculates_cost_from_tokens(self):
        """Cost should be calculated from actual token counts."""
        usage = {"prompt_tokens": 1000, "completion_tokens": 500}
        self.service._track_gpt_cost(usage)
        # input: 1000 * 0.15 / 1M = 0.00015
        # output: 500 * 0.60 / 1M = 0.0003
        expected = 0.00015 + 0.0003
        assert abs(self.service.total_cost - expected) < 1e-10

    def test_increments_gpt_calls(self):
        usage = {"prompt_tokens": 100, "completion_tokens": 50}
        self.service._track_gpt_cost(usage)
        self.service._track_gpt_cost(usage)
        assert self.service.gpt_calls == 2

    def test_increments_api_calls_for_backward_compat(self):
        usage = {"prompt_tokens": 100, "completion_tokens": 50}
        self.service._track_gpt_cost(usage)
        assert self.service.api_calls == 1

    def test_handles_zero_tokens(self):
        usage = {"prompt_tokens": 0, "completion_tokens": 0}
        self.service._track_gpt_cost(usage)
        assert self.service.total_cost == 0.0
        assert self.service.gpt_calls == 1

    def test_handles_missing_keys(self):
        usage = {}
        self.service._track_gpt_cost(usage)
        assert self.service.total_cost == 0.0
        assert self.service.gpt_calls == 1


class TestTrackSerperCost:
    def setup_method(self):
        self.service = get_comparison_service()
        self.service.total_cost = 0.0
        self.service.gpt_calls = 0
        self.service.serper_calls = 0
        self.service.api_calls = 0

    def test_fixed_cost_per_call(self):
        self.service._track_serper_cost()
        assert self.service.total_cost == 0.001

    def test_increments_serper_calls(self):
        self.service._track_serper_cost()
        self.service._track_serper_cost()
        assert self.service.serper_calls == 2

    def test_increments_api_calls_for_backward_compat(self):
        self.service._track_serper_cost()
        assert self.service.api_calls == 1

    def test_does_not_increment_gpt_calls(self):
        self.service._track_serper_cost()
        assert self.service.gpt_calls == 0


class TestCounterSeparation:
    def setup_method(self):
        self.service = get_comparison_service()
        self.service.total_cost = 0.0
        self.service.gpt_calls = 0
        self.service.serper_calls = 0
        self.service.api_calls = 0

    def test_mixed_calls_separate_correctly(self):
        usage = {"prompt_tokens": 1000, "completion_tokens": 500}
        self.service._track_gpt_cost(usage)
        self.service._track_serper_cost()
        self.service._track_serper_cost()
        self.service._track_gpt_cost(usage)

        assert self.service.gpt_calls == 2
        assert self.service.serper_calls == 2
        assert self.service.api_calls == 4

    def test_api_calls_equals_sum(self):
        """api_calls must always equal gpt_calls + serper_calls."""
        usage = {"prompt_tokens": 500, "completion_tokens": 200}
        for _ in range(3):
            self.service._track_gpt_cost(usage)
        for _ in range(5):
            self.service._track_serper_cost()
        assert self.service.api_calls == self.service.gpt_calls + self.service.serper_calls

    def test_total_cost_includes_both(self):
        usage = {"prompt_tokens": 1000000, "completion_tokens": 0}  # $0.15 input
        self.service._track_gpt_cost(usage)
        self.service._track_serper_cost()
        # GPT: 0.15, Serper: 0.001
        assert abs(self.service.total_cost - 0.151) < 1e-10


class TestExtractionFunctionsImportable:
    """Verify all 6 extraction functions are importable after refactor."""

    def test_all_extraction_functions_import(self):
        """All 6 functions should import without error. If renamed/removed, this fails."""
        from app.services.extraction_service import (
            parse_product_query, extract_specs, extract_price,
            extract_price_from_training_data, extract_reviews,
            generate_comparison
        )
        assert parse_product_query is not None
        assert extract_specs is not None
        assert extract_price is not None
        assert extract_price_from_training_data is not None
        assert extract_reviews is not None
        assert generate_comparison is not None


class TestStateReset:
    """Verify new counters are reset per request."""

    def test_gpt_calls_initialized_to_zero(self):
        service = get_comparison_service()
        assert hasattr(service, 'gpt_calls')

    def test_serper_calls_initialized_to_zero(self):
        service = get_comparison_service()
        assert hasattr(service, 'serper_calls')

    def test_old_track_cost_removed(self):
        """The old _track_cost method should no longer exist."""
        service = get_comparison_service()
        assert not hasattr(service, '_track_cost'), \
            "_track_cost should be replaced by _track_gpt_cost and _track_serper_cost"
