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


class TestNumericVerificationEdgeCases:
    """Edge cases for numeric spec verification."""

    def test_display_size_verified(self, service):
        """Display '6.7 inches' should verify when '6.7' is in snippet."""
        specs = {"display": "6.7 inches OLED", "display_source": "snippet_1"}
        snippets = ["The 6.7-inch Super Retina XDR display is stunning"]
        result = service._verify_spec_citations(specs, snippets)
        assert result["display"] == "likely"  # "6" and "7" are single digits, no sig numbers

    def test_multiple_numbers_all_must_match(self, service):
        """Storage '128 GB + 8 GB RAM' in a single field needs 128 to match."""
        specs = {"storage": "128 GB with 8 GB RAM", "storage_source": "snippet_1"}
        snippets = ["Comes with 128GB storage and 8GB RAM"]
        result = service._verify_spec_citations(specs, snippets)
        assert result["storage"] == "verified"

    def test_multiple_numbers_partial_match_is_likely(self, service):
        """If only some significant numbers match, result is 'likely'."""
        specs = {"storage": "256 GB with 16 GB RAM", "storage_source": "snippet_1"}
        snippets = ["The phone has 256GB of storage with 8GB RAM"]
        result = service._verify_spec_citations(specs, snippets)
        assert result["storage"] == "likely"

    def test_dosage_numeric_match(self, service):
        """Supplement dosage '1000 IU' should match snippet with '1000'."""
        specs = {"dosage": "1000 IU", "dosage_source": "snippet_1"}
        snippets = ["Vitamin D3 1000 IU per softgel for daily supplementation"]
        result = service._verify_spec_citations(specs, snippets)
        assert result["dosage"] == "verified"

    def test_dosage_wrong_number_not_verified(self, service):
        """Dosage '1000 IU' should not verify against snippet with '5000 IU'."""
        specs = {"dosage": "1000 IU", "dosage_source": "snippet_1"}
        snippets = ["High-dose Vitamin D3 5000 IU for deficiency treatment"]
        result = service._verify_spec_citations(specs, snippets)
        assert result["dosage"] != "verified"

    def test_count_numeric_match(self, service):
        """Count '120 softgels' should verify when snippet has '120'."""
        specs = {"count": "120 softgels", "count_source": "snippet_1"}
        snippets = ["Pack of 120 softgels, 4-month supply"]
        result = service._verify_spec_citations(specs, snippets)
        assert result["count"] == "verified"

    def test_small_number_only_uses_keyword_matching(self, service):
        """RAM '8 GB' has only single-digit '8' — falls to keyword matching."""
        specs = {"ram": "8 GB", "ram_source": "snippet_1"}
        snippets = ["The phone has 8GB of RAM for smooth multitasking"]
        result = service._verify_spec_citations(specs, snippets)
        # "8" is 1 digit (not significant), "gb" is 2 chars (too short)
        # No sig numbers and no terms > 2 chars → "likely"
        assert result["ram"] == "likely"

    def test_non_numeric_field_not_affected(self, service):
        """Processor field (not in NUMERIC_SPEC_FIELDS) uses keyword matching."""
        specs = {"processor": "Snapdragon 8 Gen 3", "processor_source": "snippet_1"}
        snippets = ["Powered by Qualcomm Snapdragon 8 Gen 3 chipset"]
        result = service._verify_spec_citations(specs, snippets)
        assert result["processor"] == "verified"

    def test_connectivity_text_field(self, service):
        """Connectivity is a text field and should use keyword matching."""
        specs = {"connectivity": "5G, Wi-Fi 6E, Bluetooth 5.3", "connectivity_source": "snippet_1"}
        snippets = ["Supports 5G connectivity, Wi-Fi 6E, and Bluetooth 5.3"]
        result = service._verify_spec_citations(specs, snippets)
        assert result["connectivity"] == "verified"


class TestCrossValidationEdgeCases:
    """Edge cases for shopping cross-validation."""

    def test_empty_shopping_returns_empty(self, service):
        """Empty shopping list returns empty dict."""
        result = service._cross_validate_specs_with_shopping({"storage": "128GB"}, [])
        assert result == {}

    def test_na_value_skipped(self, service):
        """'N/A' values should be skipped."""
        specs = {"storage": "N/A"}
        shopping = [{"title": "iPhone 15 128GB", "description": ""}]
        result = service._cross_validate_specs_with_shopping(specs, shopping)
        assert "storage" not in result

    def test_non_checkable_field_ignored(self, service):
        """Fields not in checkable list are not cross-validated."""
        specs = {"os": "Android 14"}
        shopping = [{"title": "Samsung Galaxy S24 Android 14", "description": ""}]
        result = service._cross_validate_specs_with_shopping(specs, shopping)
        assert "os" not in result

    def test_processor_text_match_in_shopping(self, service):
        """Processor 'Snapdragon' should be found via text matching (no significant numbers)."""
        specs = {"processor": "Snapdragon 8 Gen 3"}
        shopping = [{"title": "Samsung Galaxy S24 Snapdragon 8 Gen 3 256GB", "description": ""}]
        result = service._cross_validate_specs_with_shopping(specs, shopping)
        assert result.get("processor") == "verified"

    def test_form_text_match(self, service):
        """Form 'softgels' should match via text matching."""
        specs = {"form": "softgels"}
        shopping = [{"title": "Fish Oil 120 Softgels", "description": ""}]
        result = service._cross_validate_specs_with_shopping(specs, shopping)
        assert result.get("form") == "verified"

    def test_description_also_searched(self, service):
        """Cross-validation should check descriptions too, not just titles."""
        specs = {"storage": "128 GB"}
        shopping = [{"title": "iPhone 15", "description": "128GB storage option"}]
        result = service._cross_validate_specs_with_shopping(specs, shopping)
        assert result.get("storage") == "verified"

    def test_multiple_shopping_items_combined(self, service):
        """Numbers can match across multiple shopping items."""
        specs = {"storage": "128 GB"}
        shopping = [
            {"title": "iPhone 15 64GB", "description": ""},
            {"title": "iPhone 15 128GB Blue", "description": ""},
        ]
        result = service._cross_validate_specs_with_shopping(specs, shopping)
        assert result.get("storage") == "verified"
