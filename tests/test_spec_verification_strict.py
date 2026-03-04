"""Tests for stricter spec citation verification."""
import pytest
from app.services.structured_comparison_service import StructuredComparisonService


@pytest.fixture
def service():
    return StructuredComparisonService()


class TestStrictNumericVerification:
    """Numeric spec values must match exactly in cited snippet."""

    def test_exact_number_match_verified(self, service):
        """'4422 mAh' cited from snippet containing '4422' should be verified."""
        specs = {"battery": "4422 mAh", "battery_source": "snippet_1"}
        snippets = ["The phone features a 4422 mAh battery with fast charging"]
        result = service._verify_spec_citations(specs, snippets)
        assert result["battery"] == "verified"

    def test_wrong_number_not_verified(self, service):
        """'4422 mAh' cited from snippet with '5000 mAh' should NOT be verified."""
        specs = {"battery": "4422 mAh", "battery_source": "snippet_1"}
        snippets = ["This device has a 5000 mAh battery for all-day use"]
        result = service._verify_spec_citations(specs, snippets)
        assert result["battery"] != "verified"

    def test_storage_number_must_match(self, service):
        """'128 GB' cited from snippet with only '256 GB' should NOT be verified."""
        specs = {"storage": "128 GB", "storage_source": "snippet_1"}
        snippets = ["Available in 256 GB and 512 GB configurations"]
        result = service._verify_spec_citations(specs, snippets)
        assert result["storage"] != "verified"

    def test_storage_number_exact_match(self, service):
        """'256 GB' cited from snippet with '256' should be verified."""
        specs = {"storage": "256 GB", "storage_source": "snippet_1"}
        snippets = ["The base model comes with 256 GB of storage"]
        result = service._verify_spec_citations(specs, snippets)
        assert result["storage"] == "verified"

    def test_ram_number_must_match(self, service):
        """'8 GB' RAM cited from snippet with '12 GB' should NOT be verified."""
        specs = {"ram": "8 GB", "ram_source": "snippet_1"}
        snippets = ["Powered by 12 GB of RAM and Snapdragon 8 Gen 3"]
        result = service._verify_spec_citations(specs, snippets)
        assert result["ram"] != "verified"

    def test_non_numeric_spec_uses_keyword_match(self, service):
        """Non-numeric specs like 'os' should still use keyword matching."""
        specs = {"os": "Android 14", "os_source": "snippet_1"}
        snippets = ["Ships with Android 14 and One UI 6.1"]
        result = service._verify_spec_citations(specs, snippets)
        assert result["os"] == "verified"

    def test_weight_numeric_match(self, service):
        """Weight '187 g' should match snippet with '187'."""
        specs = {"weight": "187 g", "weight_source": "snippet_1"}
        snippets = ["Weighing in at 187 grams, it's lighter than the Pro model"]
        result = service._verify_spec_citations(specs, snippets)
        assert result["weight"] == "verified"

    def test_training_source_always_unverified(self, service):
        """Specs citing 'training' should always be unverified."""
        specs = {"battery": "4000 mAh", "battery_source": "training"}
        snippets = ["Some snippet text"]
        result = service._verify_spec_citations(specs, snippets)
        assert result["battery"] == "unverified"

    def test_no_source_always_unverified(self, service):
        """Specs with no _source field should be unverified."""
        specs = {"battery": "4000 mAh"}
        snippets = ["Some snippet text"]
        result = service._verify_spec_citations(specs, snippets)
        assert result["battery"] == "unverified"


class TestCrossValidationNumeric:
    """Shopping cross-validation should check exact numeric matches."""

    def test_storage_cross_validated(self, service):
        """Storage '128 GB' should be verified if '128' appears in shopping titles."""
        specs = {"storage": "128 GB"}
        shopping = [{"title": "iPhone 15 128GB Blue", "description": ""}]
        result = service._cross_validate_specs_with_shopping(specs, shopping)
        assert result.get("storage") == "verified"

    def test_wrong_storage_not_cross_validated(self, service):
        """Storage '128 GB' should NOT be verified if only '256' appears in shopping."""
        specs = {"storage": "128 GB"}
        shopping = [{"title": "iPhone 15 Pro 256GB", "description": ""}]
        result = service._cross_validate_specs_with_shopping(specs, shopping)
        assert result.get("storage") != "verified"
