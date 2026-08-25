"""
Unit tests for drug database service.

Tests the Bahrain approved drugs lookup and GPT context formatting.

Tests marked @pytest.mark.live_db require:
- SUPABASE_URL and SUPABASE_SERVICE_KEY env vars pointing to a project
  with the bahrain_approved_drugs table populated.
- LIVE=1. Without it the sanitizer in tests/_env_safety.py replaces SUPABASE_*
  with unusable sentinels and the collection hook skips every live_db item, so
  a bare `-m live_db` run reports `skipped` instead of testing anything.
- Run with: LIVE=1 pytest tests/test_drug_database_service.py -v -m live_db
- Skip live_db tests: pytest tests/test_drug_database_service.py -v -m "not live_db"
"""
import pytest
import asyncio
from unittest.mock import patch, MagicMock


def run_async(coro):
    """Helper to run async functions in sync tests."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _can_connect_to_drug_table():
    """Check if the bahrain_approved_drugs table is accessible."""
    try:
        from app.services.database_service import get_supabase_client
        client = get_supabase_client()
        # Direct query — will raise if table doesn't exist in PostgREST schema cache
        response = client.table("bahrain_approved_drugs").select("id").limit(1).execute()
        return True
    except Exception:
        return False


# Skip live_db tests if table isn't accessible
live_db_available = _can_connect_to_drug_table()
skip_no_db = pytest.mark.skipif(
    not live_db_available,
    reason="bahrain_approved_drugs table not accessible (check SUPABASE_URL/SUPABASE_SERVICE_KEY)"
)


class TestFindMatchingDrugs:
    """Tests for find_matching_drugs() full-text search."""

    @skip_no_db
    @pytest.mark.live_db
    def test_exact_trade_name_match(self):
        """Searching for an exact trade name returns that product."""
        from app.services.drug_database_service import find_matching_drugs

        results = run_async(find_matching_drugs("TIGER BALM SOFT"))
        assert len(results) >= 1
        trade_names = [r["trade_name"].upper() for r in results]
        assert any("TIGER BALM" in tn for tn in trade_names)

    @skip_no_db
    @pytest.mark.live_db
    def test_partial_ingredient_match(self):
        """Searching 'Omega 3' matches products with omega-3 ingredients."""
        from app.services.drug_database_service import find_matching_drugs

        results = run_async(find_matching_drugs("Omega 3"))
        assert len(results) >= 1
        # At least one result should mention omega in trade_name or api_name
        found_omega = any(
            "omega" in (r.get("trade_name", "") + " " + r.get("api_name", "")).lower()
            for r in results
        )
        assert found_omega, f"Expected omega-related product, got: {[r['trade_name'] for r in results]}"

    @skip_no_db
    @pytest.mark.live_db
    def test_vitamin_d_search(self):
        """Searching 'Vitamin D' matches vitamin D products."""
        from app.services.drug_database_service import find_matching_drugs

        results = run_async(find_matching_drugs("Vitamin D"))
        assert len(results) >= 1

    @skip_no_db
    @pytest.mark.live_db
    def test_no_match_returns_empty(self):
        """Searching for a non-drug product returns empty list."""
        from app.services.drug_database_service import find_matching_drugs

        results = run_async(find_matching_drugs("iPhone 15 Pro Max"))
        assert results == []

    @skip_no_db
    @pytest.mark.live_db
    def test_limit_parameter(self):
        """Results are capped at the limit parameter."""
        from app.services.drug_database_service import find_matching_drugs

        results = run_async(find_matching_drugs("vitamin", limit=3))
        assert len(results) <= 3

    @skip_no_db
    @pytest.mark.live_db
    def test_result_fields(self):
        """Each result has the expected fields."""
        from app.services.drug_database_service import find_matching_drugs

        results = run_async(find_matching_drugs("cod liver oil"))
        assert len(results) >= 1
        result = results[0]
        assert "trade_name" in result
        assert "api_name" in result
        assert "form" in result
        assert "pack_size" in result
        assert "applicant_name" in result

    def test_error_returns_empty_list(self):
        """If Supabase fails, returns empty list instead of raising."""
        from app.services.drug_database_service import find_matching_drugs

        with patch("app.services.drug_database_service.get_supabase_client") as mock:
            mock.side_effect = Exception("Connection refused")
            results = run_async(find_matching_drugs("anything"))
            assert results == []


class TestFormatDrugContext:
    """Tests for format_drug_context() prompt formatting."""

    def test_empty_list_returns_empty_string(self):
        """No drugs = no context to inject."""
        from app.services.drug_database_service import format_drug_context

        assert format_drug_context([]) == ""

    def test_single_drug_format(self):
        """Single drug formatted correctly for GPT prompt."""
        from app.services.drug_database_service import format_drug_context

        drugs = [{
            "trade_name": "NORWEGIAN COD LIVER OIL",
            "api_name": "Vitamin A 1250 IU, Vitamin D 135 IU",
            "form": "Soft Gel Capsules",
            "pack_size": "110",
            "applicant_name": "BAHRAIN PHARMACY (MAIN)",
            "manufacturer": "21st Century Healthcare Inc",
            "country": "USA",
        }]

        result = format_drug_context(drugs)
        assert "Official Bahrain Drug Registration Data" in result
        assert "NORWEGIAN COD LIVER OIL" in result
        assert "Vitamin A 1250 IU" in result
        assert "Soft Gel Capsules" in result
        assert "BAHRAIN PHARMACY (MAIN)" in result
        assert "21st Century Healthcare Inc" in result

    def test_multiple_drugs_all_included(self):
        """Multiple drugs all appear in output."""
        from app.services.drug_database_service import format_drug_context

        drugs = [
            {"trade_name": "Product A", "api_name": "Ingredient A"},
            {"trade_name": "Product B", "api_name": "Ingredient B"},
        ]

        result = format_drug_context(drugs)
        assert "Product A" in result
        assert "Product B" in result

    def test_missing_fields_handled(self):
        """Drugs with missing optional fields don't crash."""
        from app.services.drug_database_service import format_drug_context

        drugs = [{"trade_name": "Minimal Drug"}]
        result = format_drug_context(drugs)
        assert "Minimal Drug" in result
