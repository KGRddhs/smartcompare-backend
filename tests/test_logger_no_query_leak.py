"""B0-C Item 1 — PII protection: raw user queries never land in logger.info/debug/warning.

Security audit MED #3: `Parsing query: {query}` at structured_comparison_service.py:1168
leaked plaintext queries to Railway logs at INFO level. The fix replaces the raw query with
SHA-256(query)[:12] + length, matching the audit_service pattern already used for content blocks.

This test pins the invariant: across the three patched sites
(structured_comparison_service / image_routes / drug_database_service), no log record
emitted during a query-handling code path may contain the raw query substring.
"""
import logging
from unittest.mock import patch, AsyncMock

import pytest


SENTINEL = "ULTRA-SECRET-QUERY-DO-NOT-LEAK iPhone 99 vs Galaxy 99"


class TestRawQueryNeverLeaksToLogs:
    @pytest.mark.asyncio
    async def test_structured_comparison_service_parsing_query_log_is_hashed(self, caplog):
        """compare_from_text logs only query_hash + length when parsing, not raw query."""
        from app.services.structured_comparison_service import StructuredComparisonService

        svc = StructuredComparisonService()

        # Mock parse_product_query to short-circuit OpenAI call; force the
        # `< 2 products` early return so we never burn downstream API budget.
        with patch(
            "app.services.structured_comparison_service.parse_product_query",
            new=AsyncMock(return_value=({"products": []}, {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0})),
        ):
            with caplog.at_level(logging.DEBUG, logger="app.services.structured_comparison_service"):
                result = await svc.compare_from_text(SENTINEL, region="bahrain")

        # Sanity: we hit the parser branch (not vision/explicit_pair).
        assert result.get("success") is False

        # Invariant: raw sentinel never appears in any log record across any logger.
        for rec in caplog.records:
            assert SENTINEL not in rec.getMessage(), (
                f"Raw query leaked to log record {rec.name}/{rec.levelname}: {rec.getMessage()!r}"
            )

        # Positive: at least one record must carry the hash prefix to prove the
        # replacement actually fired (not a no-op skip).
        hash_messages = [r for r in caplog.records if "query_hash=" in r.getMessage() and "length=" in r.getMessage()]
        assert hash_messages, "Expected at least one log record with query_hash=... length=... format"

    def test_drug_database_service_lookup_failure_log_is_hashed(self, caplog):
        """find_matching_drugs swallows DB errors but logs query_hash, not raw query."""
        import asyncio
        from app.services import drug_database_service

        with patch(
            "app.services.drug_database_service.get_supabase_client",
            side_effect=Exception("DB down"),
        ):
            with caplog.at_level(logging.WARNING, logger="app.services.drug_database_service"):
                result = asyncio.get_event_loop().run_until_complete(
                    drug_database_service.find_matching_drugs(SENTINEL)
                ) if False else None  # placeholder; use direct asyncio.run below
                result = asyncio.run(drug_database_service.find_matching_drugs(SENTINEL))

        assert result == []

        for rec in caplog.records:
            assert SENTINEL not in rec.getMessage(), (
                f"Raw query leaked to log record: {rec.getMessage()!r}"
            )

        hash_messages = [r for r in caplog.records if "query_hash=" in r.getMessage()]
        assert hash_messages, "Expected a query_hash=... record on DB failure path"

    def test_image_routes_hashlib_imported_and_hash_format_used(self):
        """Static check: image_routes.py uses query_hash format for auto-compare log."""
        import ast
        import inspect
        from app.api import image_routes

        source = inspect.getsource(image_routes)

        # The audit replacement must be present.
        assert "query_hash = hashlib.sha256(query.encode" in source, (
            "Expected query_hash = hashlib.sha256(...) replacement in image_routes"
        )
        assert "[IMAGE] Auto-comparing: query_hash=" in source, (
            "Expected hashed log format in image_routes auto-compare path"
        )

        # The old leak format must be gone.
        assert "[IMAGE] Auto-comparing: {query}" not in source, (
            "Raw `Auto-comparing: {query}` log line still present — leak not patched"
        )

        # Parse to verify hashlib import.
        tree = ast.parse(source)
        imports = {
            n.name for node in ast.walk(tree) if isinstance(node, ast.Import) for n in node.names
        }
        assert "hashlib" in imports, "hashlib not imported in image_routes"
