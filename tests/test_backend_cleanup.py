"""Tests verifying backend cleanup: dead code removed, no import errors.

Run: python -m pytest tests/test_backend_cleanup.py -v
"""
import importlib
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestLegacyRoutesRemoved:
    """Verify legacy routes.py has been deleted and main.py still works."""

    def test_routes_py_does_not_exist(self):
        """Legacy routes.py should be deleted."""
        assert not os.path.exists("app/api/routes.py")

    def test_main_imports_cleanly(self):
        """app.main should import without errors after routes.py removal."""
        # This will fail if main.py still tries to import from routes.py
        mod = importlib.import_module("app.main")
        importlib.reload(mod)

    def test_no_legacy_router_in_app(self):
        """The legacy api_router should not be registered."""
        from app.main import app

        route_paths = [route.path for route in app.routes]
        # Legacy router used /api/v1/compare/quick — modern routes don't have this
        legacy_patterns = ["/api/v1/compare/quick"]
        for pattern in legacy_patterns:
            assert pattern not in route_paths, f"Legacy route {pattern} still registered"

    def test_no_legacy_image_compare_endpoint(self):
        """Legacy POST /api/v1/compare (image upload) should be gone."""
        from app.main import app

        # Collect (path, methods) for all routes
        for route in app.routes:
            if getattr(route, "path", None) == "/api/v1/compare":
                methods = getattr(route, "methods", set())
                # The legacy route was POST /api/v1/compare for image upload
                # The modern text route is GET/POST /api/v1/text/compare
                assert "POST" not in methods or "/text/" in route.path, \
                    "Legacy POST /api/v1/compare (image upload) still registered"

    def test_no_import_of_comparison_service(self):
        """main.py should not import from comparison_service (legacy)."""
        import inspect
        import app.main as main_mod

        source = inspect.getsource(main_mod)
        assert "comparison_service" not in source, \
            "main.py still references comparison_service"

    def test_no_import_of_routes_module(self):
        """main.py should not import from app.api.routes."""
        import inspect
        import app.main as main_mod

        source = inspect.getsource(main_mod)
        assert "from app.api.routes" not in source, \
            "main.py still imports from app.api.routes"


class TestDeadEndpointsRemoved:
    """Verify dead category-specific endpoints removed from text_routes."""

    def _get_router_paths(self):
        from app.api.text_routes import router
        return [route.path for route in router.routes]

    def test_no_electronics_endpoint(self):
        """Category-specific /compare/electronics should not exist."""
        paths = self._get_router_paths()
        for path in paths:
            assert not path.endswith("/compare/electronics"), \
                f"Dead endpoint found: {path}"

    def test_no_grocery_endpoint(self):
        """Category-specific /compare/grocery should not exist."""
        paths = self._get_router_paths()
        for path in paths:
            assert not path.endswith("/compare/grocery"), \
                f"Dead endpoint found: {path}"

    def test_selected_category_param_still_works(self):
        """The main /compare endpoint should still exist."""
        paths = self._get_router_paths()
        assert any(path.endswith("/compare") for path in paths)

    def test_stream_endpoint_still_exists(self):
        """The /compare/stream SSE endpoint should still exist."""
        paths = self._get_router_paths()
        assert any(path.endswith("/compare/stream") for path in paths)

    def test_other_text_routes_intact(self):
        """Non-deleted text routes should still be registered."""
        paths = self._get_router_paths()
        for expected_suffix in ["/compare", "/quick", "/parse", "/cache"]:
            assert any(path.endswith(expected_suffix) for path in paths), \
                f"Expected route ending with {expected_suffix} is missing"


class TestDeadFunctionsRemoved:
    """Verify unused functions removed from openai_service.py."""

    def test_identify_products_still_exists(self):
        """identify_products should NOT be removed — it is used."""
        from app.services.openai_service import identify_products

        assert identify_products is not None

    def test_extract_price_from_search_results_removed(self):
        """Unused extract_price_from_search_results should be deleted."""
        import app.services.openai_service as mod

        assert not hasattr(mod, "extract_price_from_search_results"), \
            "extract_price_from_search_results should be removed"

    def test_estimate_price_fallback_removed(self):
        """Unused estimate_price_fallback should be deleted."""
        import app.services.openai_service as mod

        assert not hasattr(mod, "estimate_price_fallback"), \
            "estimate_price_fallback should be removed"

    def test_generate_comparison_removed_from_openai_service(self):
        """generate_comparison in openai_service should be deleted (extraction_service has its own)."""
        import app.services.openai_service as mod

        assert not hasattr(mod, "generate_comparison"), \
            "generate_comparison should be removed from openai_service"

    def test_generate_comparison_exists_in_extraction_service(self):
        """generate_comparison should still exist in extraction_service."""
        from app.services.extraction_service import generate_comparison

        assert generate_comparison is not None

    def test_utility_functions_preserved(self):
        """Utility functions used by identify_products should remain."""
        from app.services.openai_service import (
            clean_json_response,
            encode_image_bytes_to_base64,
            encode_image_to_base64,
        )

        assert clean_json_response is not None
        assert encode_image_to_base64 is not None
        assert encode_image_bytes_to_base64 is not None

    def test_unused_imports_cleaned(self):
        """os and Optional should no longer be imported (only used by deleted functions)."""
        import inspect
        import app.services.openai_service as mod

        source = inspect.getsource(mod)
        # os was only used by deleted functions; Optional was only in type hints of deleted functions
        assert "import os" not in source, "Unused 'os' import should be cleaned up"
