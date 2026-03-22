"""
Tests for behavioral profile integration in the comparison flow.
"""
import inspect
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


class TestBehaviorIntegration:
    """Tests for behavioral profile integration in comparison flow."""

    def test_scoring_accepts_behavior_params(self):
        """compute_scores() accepts behavior_profile and session_signals parameters."""
        from app.services.scoring_service import ScoringService
        service = ScoringService()
        sig = inspect.signature(service.compute_scores)
        assert "behavior_profile" in sig.parameters
        assert "session_signals" in sig.parameters

    def test_compare_from_text_accepts_user_id(self):
        """compare_from_text() accepts user_id parameter."""
        from app.services.structured_comparison_service import StructuredComparisonService
        service = StructuredComparisonService()
        sig = inspect.signature(service.compare_from_text)
        assert "user_id" in sig.parameters

    def test_compare_from_text_streaming_accepts_user_id(self):
        """compare_from_text_streaming() accepts user_id parameter."""
        from app.services.structured_comparison_service import StructuredComparisonService
        service = StructuredComparisonService()
        sig = inspect.signature(service.compare_from_text_streaming)
        assert "user_id" in sig.parameters

    def test_scoring_with_behavior_profile_adjusts_weights(self):
        """Scoring with behavior_profile adjusts weights via apply_behavioral_adjustments."""
        from app.services.scoring_service import ScoringService, CATEGORY_WEIGHTS
        service = ScoringService()

        products = [
            {
                "brand": "Apple", "name": "iPhone 15", "category": "electronics",
                "specs": {"ram": "6GB", "storage": "128GB"},
                "price": {"amount": 299, "currency": "BHD", "retailer": "Amazon", "estimated": False},
                "reviews": {"average_rating": 4.5, "total_reviews": 1200},
                "rating": 4.5, "review_count": 1200, "rating_verified": True,
                "rating_source": {"name": "Amazon"}, "fact_check": {},
            },
            {
                "brand": "Samsung", "name": "Galaxy S24", "category": "electronics",
                "specs": {"ram": "8GB", "storage": "128GB"},
                "price": {"amount": 279, "currency": "BHD", "retailer": "Noon", "estimated": False},
                "reviews": {"average_rating": 4.3, "total_reviews": 800},
                "rating": 4.3, "review_count": 800, "rating_verified": True,
                "rating_source": {"name": "Noon"}, "fact_check": {},
            },
        ]

        # Score without behavior profile
        result_without = service.compute_scores(products)
        assert result_without["scoring_method"] == "category_weighted"

        # Score with behavior profile
        behavior_profile = {
            "dimension_sensitivity": {
                "spec_score": 0.6,
                "price_score": 0.3,
                "review_score": 0.1,
            },
        }
        result_with = service.compute_scores(products, behavior_profile=behavior_profile)
        assert result_with["scoring_method"] == "behavioral"

        # Weights should differ
        weights_without = result_without["scores"]["product_0"]["weights_used"]
        weights_with = result_with["scores"]["product_0"]["weights_used"]
        assert weights_without != weights_with

    def test_scoring_with_session_signals(self):
        """Scoring with session_signals adjusts weights."""
        from app.services.scoring_service import ScoringService
        service = ScoringService()

        products = [
            {
                "brand": "Apple", "name": "iPhone 15", "category": "electronics",
                "specs": {"ram": "6GB"}, "price": {"amount": 299, "currency": "BHD", "estimated": False},
                "reviews": {}, "rating": 4.5, "review_count": 1200,
                "rating_verified": True, "rating_source": {"name": "Amazon"}, "fact_check": {},
            },
            {
                "brand": "Samsung", "name": "Galaxy S24", "category": "electronics",
                "specs": {"ram": "8GB"}, "price": {"amount": 279, "currency": "BHD", "estimated": False},
                "reviews": {}, "rating": 4.3, "review_count": 800,
                "rating_verified": True, "rating_source": {"name": "Noon"}, "fact_check": {},
            },
        ]

        session_signals = {
            "tab_dwell_ms": {"specs": 10000, "reviews": 1000, "overview": 2000},
            "first_tab_viewed": "specs",
        }
        result = service.compute_scores(products, session_signals=session_signals)
        assert result["scoring_method"] == "behavioral"

    @pytest.mark.asyncio
    async def test_fetch_behavior_profile(self):
        """_fetch_behavior_profile returns profile from Supabase."""
        from app.services.structured_comparison_service import StructuredComparisonService

        service = StructuredComparisonService()
        mock_profile = {"dimension_sensitivity": {"spec_score": 0.5}}

        with patch('app.services.database_service.get_supabase_client') as mock_sb:
            mock_client = MagicMock()
            mock_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
                data={"behavior_profile": mock_profile}
            )
            mock_sb.return_value = mock_client

            result = await service._fetch_behavior_profile("user-123")
            assert result == mock_profile

    @pytest.mark.asyncio
    async def test_fetch_behavior_profile_handles_error(self):
        """_fetch_behavior_profile returns None on error."""
        from app.services.structured_comparison_service import StructuredComparisonService

        service = StructuredComparisonService()

        with patch('app.services.database_service.get_supabase_client') as mock_sb:
            mock_sb.side_effect = Exception("DB error")
            result = await service._fetch_behavior_profile("user-123")
            assert result is None

    @pytest.mark.asyncio
    async def test_fetch_behavior_profile_returns_none_when_empty(self):
        """_fetch_behavior_profile returns None when profile is empty."""
        from app.services.structured_comparison_service import StructuredComparisonService

        service = StructuredComparisonService()

        with patch('app.services.database_service.get_supabase_client') as mock_sb:
            mock_client = MagicMock()
            mock_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
                data={"behavior_profile": {}}
            )
            mock_sb.return_value = mock_client

            result = await service._fetch_behavior_profile("user-123")
            assert result is None  # empty dict is falsy

    @pytest.mark.asyncio
    async def test_update_behavior_profile_calls_supabase(self):
        """_update_behavior_profile fetches data and updates profile."""
        from app.services.structured_comparison_service import StructuredComparisonService

        service = StructuredComparisonService()

        with patch('app.services.database_service.get_supabase_client') as mock_sb, \
             patch('app.services.behavior_service.get_behavior_service') as mock_bs:

            mock_client = MagicMock()
            # Mock table queries
            mock_comparisons = MagicMock(data=[{"category_used": "electronics", "created_at": "2026-03-22T00:00:00"}])
            mock_feedback = MagicMock(data=[{"useful": True}])
            mock_events = MagicMock(data=[{"event_type": "tab_switch", "metadata": {"to": "specs", "dwell_ms": 5000}}])

            mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = mock_comparisons
            mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_feedback
            mock_sb.return_value = mock_client

            mock_service = MagicMock()
            mock_service.build_behavior_profile = AsyncMock(return_value={"category_affinity": {"electronics": 1.0}})
            mock_bs.return_value = mock_service

            await service._update_behavior_profile("user-123")

            # Verify profile was built
            mock_service.build_behavior_profile.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_behavior_profile_handles_error(self):
        """_update_behavior_profile handles errors gracefully."""
        from app.services.structured_comparison_service import StructuredComparisonService

        service = StructuredComparisonService()

        with patch('app.services.database_service.get_supabase_client') as mock_sb:
            mock_sb.side_effect = Exception("DB error")
            # Should not raise
            await service._update_behavior_profile("user-123")


class TestBehaviorInRoutes:
    """Tests that routes pass user_id to service methods."""

    def test_post_compare_passes_user_id(self):
        """POST /compare passes user_id from authenticated user."""
        from app.api.text_routes import text_compare
        sig = inspect.signature(text_compare)
        # The route accepts 'user' param from Depends
        assert "user" in sig.parameters

    def test_get_compare_passes_user_id(self):
        """GET /compare passes user_id from authenticated user."""
        from app.api.text_routes import text_compare_get
        sig = inspect.signature(text_compare_get)
        assert "user" in sig.parameters

    def test_stream_compare_passes_user_id(self):
        """GET /compare/stream passes user_id from authenticated user."""
        from app.api.text_routes import text_compare_stream
        sig = inspect.signature(text_compare_stream)
        assert "user" in sig.parameters
