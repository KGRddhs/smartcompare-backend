"""Tests for improved price fallback — broader search before Tier 3."""
import pytest
import re

MODEL_VARIANT_PATTERN = re.compile(r'\s+(pro|plus|max|ultra|\d{2,}gb|\d+tb)$', re.IGNORECASE)

class TestModelVariantStripping:
    def test_strips_pro(self):
        assert MODEL_VARIANT_PATTERN.sub('', "iPhone 15 Pro") == "iPhone 15"

    def test_strips_plus(self):
        assert MODEL_VARIANT_PATTERN.sub('', "Galaxy S24 Plus") == "Galaxy S24"

    def test_strips_ultra(self):
        assert MODEL_VARIANT_PATTERN.sub('', "Galaxy S24 Ultra") == "Galaxy S24"

    def test_strips_storage_variant(self):
        assert MODEL_VARIANT_PATTERN.sub('', "Galaxy S24 256GB") == "Galaxy S24"

    def test_preserves_base_name(self):
        assert MODEL_VARIANT_PATTERN.sub('', "iPhone 15") == "iPhone 15"

    def test_preserves_short_numbers(self):
        assert MODEL_VARIANT_PATTERN.sub('', "iPhone 15") == "iPhone 15"

    def test_case_insensitive(self):
        assert MODEL_VARIANT_PATTERN.sub('', "Pixel 8 PRO") == "Pixel 8"

    def test_multiple_passes_chain(self):
        name = "iPhone 15 Pro Max 256GB"
        for _ in range(3):
            name = MODEL_VARIANT_PATTERN.sub('', name).strip()
        assert name == "iPhone 15"

    def test_no_broader_when_unchanged(self):
        original = "Sony WH-1000XM5"
        broader = MODEL_VARIANT_PATTERN.sub('', original).strip()
        assert broader == original


class TestBroaderFallbackImport:
    def test_model_variant_pattern_importable(self):
        from app.services.structured_comparison_service import MODEL_VARIANT_PATTERN
        assert MODEL_VARIANT_PATTERN is not None

    def test_pattern_works_on_import(self):
        from app.services.structured_comparison_service import MODEL_VARIANT_PATTERN
        assert MODEL_VARIANT_PATTERN.sub('', "iPhone 15 Pro") == "iPhone 15"
