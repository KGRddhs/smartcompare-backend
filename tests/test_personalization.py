"""Tests for personalization feature — preference validation, API endpoints, prompt injection, edge cases."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from pydantic import ValidationError


# ============================================
# 1. Preference Validation (~17 tests)
# ============================================

class TestPreferenceValidation:
    """Test the UserPreferencesRequest Pydantic model validation."""

    def test_valid_full_preferences(self):
        """All fields provided correctly should pass validation."""
        from app.api.auth_routes import UserPreferencesRequest
        req = UserPreferencesRequest(
            priorities=["price", "quality", "durability"],
            budget="mid",
            lifestyle=["fitness_enthusiast", "vegan"],
            brand_attitude="best_of_both",
        )
        assert req.priorities == ["price", "quality", "durability"]
        assert req.budget == "mid"
        assert req.brand_attitude == "best_of_both"

    def test_valid_single_priority(self):
        """A single priority should be valid (up to 3 allowed)."""
        from app.api.auth_routes import UserPreferencesRequest
        req = UserPreferencesRequest(
            priorities=["price"],
            budget="budget",
            lifestyle=["student"],
            brand_attitude="function_first",
        )
        assert len(req.priorities) == 1

    def test_valid_three_priorities_max(self):
        """Exactly 3 priorities (maximum) should be valid."""
        from app.api.auth_routes import UserPreferencesRequest
        req = UserPreferencesRequest(
            priorities=["price", "quality", "eco_friendly"],
            budget="premium",
            lifestyle=["minimalist"],
            brand_attitude="brand_loyal",
        )
        assert len(req.priorities) == 3

    def test_invalid_more_than_three_priorities(self):
        """More than 3 priorities should be rejected."""
        from app.api.auth_routes import UserPreferencesRequest
        with pytest.raises(ValidationError):
            UserPreferencesRequest(
                priorities=["price", "quality", "durability", "eco_friendly"],
                budget="mid",
                lifestyle=["student"],
                brand_attitude="function_first",
            )

    def test_invalid_empty_priorities(self):
        """Empty priorities list should be rejected (at least 1 required)."""
        from app.api.auth_routes import UserPreferencesRequest
        with pytest.raises(ValidationError):
            UserPreferencesRequest(
                priorities=[],
                budget="mid",
                lifestyle=["student"],
                brand_attitude="function_first",
            )

    def test_invalid_priority_value(self):
        """Unknown priority value should be rejected."""
        from app.api.auth_routes import UserPreferencesRequest
        with pytest.raises(ValidationError):
            UserPreferencesRequest(
                priorities=["price", "unknown_priority"],
                budget="mid",
                lifestyle=["student"],
                brand_attitude="function_first",
            )

    def test_invalid_budget_value(self):
        """Unknown budget value should be rejected."""
        from app.api.auth_routes import UserPreferencesRequest
        with pytest.raises(ValidationError):
            UserPreferencesRequest(
                priorities=["price"],
                budget="ultra_premium",
                lifestyle=["student"],
                brand_attitude="function_first",
            )

    def test_invalid_brand_attitude_value(self):
        """Unknown brand_attitude should be rejected."""
        from app.api.auth_routes import UserPreferencesRequest
        with pytest.raises(ValidationError):
            UserPreferencesRequest(
                priorities=["price"],
                budget="mid",
                lifestyle=["student"],
                brand_attitude="no_brands",
            )

    def test_invalid_lifestyle_value(self):
        """Unknown lifestyle tag should be rejected."""
        from app.api.auth_routes import UserPreferencesRequest
        with pytest.raises(ValidationError):
            UserPreferencesRequest(
                priorities=["price"],
                budget="mid",
                lifestyle=["astronaut"],
                brand_attitude="function_first",
            )

    def test_valid_empty_lifestyle(self):
        """Empty lifestyle list should be valid (lifestyle tags are optional)."""
        from app.api.auth_routes import UserPreferencesRequest
        req = UserPreferencesRequest(
            priorities=["price"],
            budget="mid",
            lifestyle=[],
            brand_attitude="function_first",
        )
        assert req.lifestyle == []

    def test_all_valid_budget_values(self):
        """All three budget values should be accepted."""
        from app.api.auth_routes import UserPreferencesRequest
        for budget in ["budget", "mid", "premium"]:
            req = UserPreferencesRequest(
                priorities=["price"],
                budget=budget,
                lifestyle=[],
                brand_attitude="function_first",
            )
            assert req.budget == budget

    def test_all_valid_brand_attitudes(self):
        """All three brand_attitude values should be accepted."""
        from app.api.auth_routes import UserPreferencesRequest
        for attitude in ["brand_loyal", "function_first", "best_of_both"]:
            req = UserPreferencesRequest(
                priorities=["price"],
                budget="mid",
                lifestyle=[],
                brand_attitude=attitude,
            )
            assert req.brand_attitude == attitude

    def test_all_valid_priority_options(self):
        """All documented priority options should be accepted individually."""
        from app.api.auth_routes import UserPreferencesRequest, VALID_PRIORITIES
        for priority in VALID_PRIORITIES:
            req = UserPreferencesRequest(
                priorities=[priority],
                budget="mid",
                lifestyle=[],
                brand_attitude="function_first",
            )
            assert req.priorities == [priority]

    def test_all_valid_lifestyle_options(self):
        """All documented lifestyle options should be accepted."""
        from app.api.auth_routes import UserPreferencesRequest, VALID_LIFESTYLE
        req = UserPreferencesRequest(
            priorities=["price"],
            budget="mid",
            lifestyle=VALID_LIFESTYLE.copy(),
            brand_attitude="function_first",
        )
        assert len(req.lifestyle) == len(VALID_LIFESTYLE)

    def test_missing_required_budget(self):
        """Missing budget field should raise ValidationError."""
        from app.api.auth_routes import UserPreferencesRequest
        with pytest.raises(ValidationError):
            UserPreferencesRequest(
                priorities=["price"],
                lifestyle=[],
                brand_attitude="function_first",
            )

    def test_missing_required_brand_attitude(self):
        """Missing brand_attitude field should raise ValidationError."""
        from app.api.auth_routes import UserPreferencesRequest
        with pytest.raises(ValidationError):
            UserPreferencesRequest(
                priorities=["price"],
                budget="mid",
                lifestyle=[],
            )

    def test_model_dump_produces_dict(self):
        """model_dump() should produce a clean dict for storage."""
        from app.api.auth_routes import UserPreferencesRequest
        req = UserPreferencesRequest(
            priorities=["price", "quality"],
            budget="mid",
            lifestyle=["vegan"],
            brand_attitude="best_of_both",
        )
        d = req.model_dump()
        expected_set_fields = {
            "priorities": ["price", "quality"],
            "budget": "mid",
            "lifestyle": ["vegan"],
            "brand_attitude": "best_of_both",
        }
        assert expected_set_fields.items() <= d.items()
        # Unset optional fields (notifications, ai_sharing) dump as None, not omitted
        assert all(v is None for k, v in d.items() if k not in expected_set_fields)


# ============================================
# 2. API Endpoint Tests (~8 tests)
# ============================================

class TestPreferenceEndpoints:
    """Test GET/PUT /api/v1/auth/preferences endpoints."""

    @pytest.mark.asyncio
    async def test_get_preferences_returns_data(self):
        """GET /preferences returns saved preferences for authenticated user."""
        from app.api.auth_routes import get_preferences
        mock_result = {
            "success": True,
            "preferences": {
                "priorities": ["price", "quality"],
                "budget": "mid",
                "lifestyle": ["student"],
                "brand_attitude": "function_first",
            },
            "preferences_completed": True,
        }
        with patch("app.api.auth_routes.get_user_preferences", new_callable=AsyncMock,
                   return_value=mock_result):
            result = await get_preferences(
                current_user={"id": "user-1", "email": "test@example.com"}
            )
        assert result["success"] is True
        assert result["preferences"]["budget"] == "mid"

    @pytest.mark.asyncio
    async def test_get_preferences_empty_when_not_set(self):
        """GET /preferences returns empty preferences when not yet saved."""
        from app.api.auth_routes import get_preferences
        mock_result = {
            "success": True,
            "preferences": {},
            "preferences_completed": False,
        }
        with patch("app.api.auth_routes.get_user_preferences", new_callable=AsyncMock,
                   return_value=mock_result):
            result = await get_preferences(
                current_user={"id": "user-1", "email": "test@example.com"}
            )
        assert result["success"] is True
        assert result["preferences"] == {}

    @pytest.mark.asyncio
    async def test_get_preferences_requires_auth(self):
        """GET /preferences requires authentication (uses get_current_user)."""
        from app.api.auth_routes import get_current_user
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(authorization=None)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_get_preferences_raises_404_on_failure(self):
        """GET /preferences raises 404 when service returns failure."""
        from app.api.auth_routes import get_preferences
        from fastapi import HTTPException
        with patch("app.api.auth_routes.get_user_preferences", new_callable=AsyncMock,
                   return_value={"success": False, "error": "User not found"}):
            with pytest.raises(HTTPException) as exc_info:
                await get_preferences(
                    current_user={"id": "nonexistent", "email": "x@x.com"}
                )
            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_save_preferences_success(self):
        """PUT /preferences saves valid preferences."""
        from app.api.auth_routes import save_preferences, UserPreferencesRequest
        mock_user = {"id": "user-1", "email": "test@example.com"}
        with patch("app.api.auth_routes.save_user_preferences", new_callable=AsyncMock,
                   return_value={"success": True, "message": "Preferences saved"}):
            result = await save_preferences(
                body=UserPreferencesRequest(
                    priorities=["price", "quality"],
                    budget="mid",
                    lifestyle=["student"],
                    brand_attitude="function_first",
                ),
                current_user=mock_user,
            )
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_save_preferences_raises_400_on_failure(self):
        """PUT /preferences raises 400 when service returns failure."""
        from app.api.auth_routes import save_preferences, UserPreferencesRequest
        from fastapi import HTTPException
        mock_user = {"id": "user-1", "email": "test@example.com"}
        with patch("app.api.auth_routes.save_user_preferences", new_callable=AsyncMock,
                   return_value={"success": False, "error": "DB error"}):
            with pytest.raises(HTTPException) as exc_info:
                await save_preferences(
                    body=UserPreferencesRequest(
                        priorities=["price"],
                        budget="budget",
                        lifestyle=[],
                        brand_attitude="brand_loyal",
                    ),
                    current_user=mock_user,
                )
            assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_save_preferences_passes_user_id_and_prefs(self):
        """PUT /preferences passes user_id and prefs (now with _sources) to service.

        Session 41 (cohort personalization): the route appends a `_sources` dict
        marking each field as user_stated when no prior preferences exist.
        """
        from app.api.auth_routes import save_preferences, UserPreferencesRequest
        mock_user = {"id": "user-42", "email": "test@example.com"}
        with patch("app.api.auth_routes.get_user_preferences", new_callable=AsyncMock,
                   return_value=None), patch(
                "app.api.auth_routes.save_user_preferences", new_callable=AsyncMock,
                return_value={"success": True}) as mock_svc:
            await save_preferences(
                body=UserPreferencesRequest(
                    priorities=["quality"],
                    budget="premium",
                    lifestyle=["professional"],
                    brand_attitude="best_of_both",
                ),
                current_user=mock_user,
            )
        # New prefs (no prior) → all sources are user_stated
        mock_svc.assert_called_once()
        args = mock_svc.await_args.args
        assert args[0] == "user-42"
        payload = args[1]
        assert payload["priorities"] == ["quality"]
        assert payload["budget"] == "premium"
        assert payload["lifestyle"] == ["professional"]
        assert payload["brand_attitude"] == "best_of_both"
        assert payload["_sources"]["priorities"] == "user_stated"
        assert payload["_sources"]["budget"] == "user_stated"
        assert payload["_sources"]["brand_attitude"] == "user_stated"

    @pytest.mark.asyncio
    async def test_save_preferences_requires_auth(self):
        """PUT /preferences requires authentication."""
        from app.api.auth_routes import get_current_user
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(authorization="NotBearer token")
        assert exc_info.value.status_code == 401


# ============================================
# 3. Auth Service Tests (~6 tests)
# ============================================

class TestPreferenceServiceFunctions:
    """Test auth_service get_user_preferences and save_user_preferences."""

    @pytest.mark.asyncio
    async def test_get_user_preferences_success(self):
        """get_user_preferences returns preferences from users table."""
        from app.services.auth_service import get_user_preferences

        mock_table = MagicMock()
        mock_table.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={
                "preferences": {"priorities": ["price"], "budget": "mid", "lifestyle": [], "brand_attitude": "function_first"},
                "preferences_completed": True,
            }
        )
        mock_admin = MagicMock()
        mock_admin.table.return_value = mock_table

        with patch("app.services.auth_service.get_admin_client", return_value=mock_admin):
            result = await get_user_preferences("user-1")

        assert result["success"] is True
        assert result["preferences"]["priorities"] == ["price"]
        assert result["preferences_completed"] is True

    @pytest.mark.asyncio
    async def test_get_user_preferences_user_not_found(self):
        """get_user_preferences returns failure when user row has no data."""
        from app.services.auth_service import get_user_preferences

        mock_table = MagicMock()
        mock_table.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data=None
        )
        mock_admin = MagicMock()
        mock_admin.table.return_value = mock_table

        with patch("app.services.auth_service.get_admin_client", return_value=mock_admin):
            result = await get_user_preferences("nonexistent")

        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_get_user_preferences_db_error(self):
        """get_user_preferences returns failure on exception."""
        from app.services.auth_service import get_user_preferences

        mock_admin = MagicMock()
        mock_admin.table.return_value.select.return_value.eq.return_value.single.return_value.execute.side_effect = Exception("DB error")

        with patch("app.services.auth_service.get_admin_client", return_value=mock_admin):
            result = await get_user_preferences("user-1")

        assert result["success"] is False
        assert result["error"] == "Failed to load preferences"

    @pytest.mark.asyncio
    async def test_get_user_preferences_empty_preferences(self):
        """get_user_preferences returns empty dict when preferences column is empty."""
        from app.services.auth_service import get_user_preferences

        mock_table = MagicMock()
        mock_table.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"preferences": {}, "preferences_completed": False}
        )
        mock_admin = MagicMock()
        mock_admin.table.return_value = mock_table

        with patch("app.services.auth_service.get_admin_client", return_value=mock_admin):
            result = await get_user_preferences("user-1")

        assert result["success"] is True
        assert result["preferences"] == {}
        assert result["preferences_completed"] is False

    @pytest.mark.asyncio
    async def test_save_user_preferences_success(self):
        """save_user_preferences updates preferences and sets preferences_completed."""
        from app.services.auth_service import save_user_preferences

        mock_table = MagicMock()
        mock_table.update.return_value.eq.return_value.execute.return_value = MagicMock()
        mock_admin = MagicMock()
        mock_admin.table.return_value = mock_table

        prefs = {
            "priorities": ["price", "quality"],
            "budget": "mid",
            "lifestyle": ["student"],
            "brand_attitude": "function_first",
        }

        with patch("app.services.auth_service.get_admin_client", return_value=mock_admin):
            result = await save_user_preferences("user-1", prefs)

        assert result["success"] is True
        update_call = mock_table.update.call_args[0][0]
        assert update_call["preferences"] == prefs
        assert update_call["preferences_completed"] is True

    @pytest.mark.asyncio
    async def test_save_user_preferences_db_error(self):
        """save_user_preferences returns error on exception."""
        from app.services.auth_service import save_user_preferences

        mock_admin = MagicMock()
        mock_admin.table.return_value.update.side_effect = Exception("Connection lost")

        with patch("app.services.auth_service.get_admin_client", return_value=mock_admin):
            result = await save_user_preferences("user-1", {"priorities": ["price"], "budget": "mid", "lifestyle": [], "brand_attitude": "function_first"})

        assert result["success"] is False
        assert result["error"] == "Failed to save preferences"


# ============================================
# 4. Login/Register includes preferences_completed (~4 tests)
# ============================================

class TestAuthResponsePreferencesCompleted:
    """Test that login and register responses include preferences_completed."""

    @pytest.mark.asyncio
    async def test_register_returns_preferences_completed_false(self):
        """Register response should include preferences_completed=false for new users."""
        from app.services.auth_service import register_user

        mock_user = MagicMock()
        mock_user.id = "new-id"
        mock_user.email = "new@test.com"

        mock_session = MagicMock()
        mock_session.access_token = "access-tok"
        mock_session.refresh_token = "refresh-tok"
        mock_session.expires_at = 1234567890

        mock_response = MagicMock()
        mock_response.user = mock_user
        mock_response.session = mock_session

        mock_auth = MagicMock()
        mock_auth.sign_up.return_value = mock_response

        mock_client = MagicMock()
        mock_client.auth = mock_auth

        mock_admin_table = MagicMock()
        mock_admin_table.insert.return_value.execute.return_value = MagicMock()

        mock_admin = MagicMock()
        mock_admin.table.return_value = mock_admin_table

        with patch("app.services.auth_service.get_auth_client", return_value=mock_client), \
             patch("app.services.auth_service.get_admin_client", return_value=mock_admin):
            result = await register_user("new@test.com", "password123")

        assert result["success"] is True
        assert result["user"]["preferences_completed"] is False

    @pytest.mark.asyncio
    async def test_login_returns_preferences_completed_true(self):
        """Login response should include preferences_completed from users table."""
        from app.services.auth_service import login_user

        mock_user = MagicMock()
        mock_user.id = "user-id"
        mock_user.email = "user@test.com"

        mock_session = MagicMock()
        mock_session.access_token = "access-tok"
        mock_session.refresh_token = "refresh-tok"
        mock_session.expires_at = 1234567890

        mock_response = MagicMock()
        mock_response.user = mock_user
        mock_response.session = mock_session

        mock_client = MagicMock()
        mock_client.auth.sign_in_with_password.return_value = mock_response

        mock_admin_table = MagicMock()
        mock_admin_table.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"preferences_completed": True}
        )
        mock_admin = MagicMock()
        mock_admin.table.return_value = mock_admin_table

        with patch("app.services.auth_service.get_auth_client", return_value=mock_client), \
             patch("app.services.auth_service.get_admin_client", return_value=mock_admin):
            result = await login_user("user@test.com", "correct")

        assert result["success"] is True
        assert result["user"]["preferences_completed"] is True

    @pytest.mark.asyncio
    async def test_login_defaults_preferences_completed_false_on_lookup_failure(self):
        """Login should default to preferences_completed=false if DB lookup fails."""
        from app.services.auth_service import login_user

        mock_user = MagicMock()
        mock_user.id = "user-id"
        mock_user.email = "user@test.com"

        mock_session = MagicMock()
        mock_session.access_token = "tok"
        mock_session.refresh_token = "ref"
        mock_session.expires_at = 9999

        mock_response = MagicMock()
        mock_response.user = mock_user
        mock_response.session = mock_session

        mock_client = MagicMock()
        mock_client.auth.sign_in_with_password.return_value = mock_response

        mock_admin = MagicMock()
        mock_admin.table.return_value.select.return_value.eq.return_value.single.return_value.execute.side_effect = Exception("DB down")

        with patch("app.services.auth_service.get_auth_client", return_value=mock_client), \
             patch("app.services.auth_service.get_admin_client", return_value=mock_admin):
            result = await login_user("user@test.com", "password")

        assert result["success"] is True
        assert result["user"]["preferences_completed"] is False

    @pytest.mark.asyncio
    async def test_social_login_returns_preferences_completed(self):
        """Social login response should include preferences_completed."""
        from app.services.auth_service import sign_in_with_social

        mock_user = MagicMock()
        mock_user.id = "social-uid"
        mock_user.email = "social@test.com"

        mock_session = MagicMock()
        mock_session.access_token = "tok"
        mock_session.refresh_token = "ref"
        mock_session.expires_at = 9999

        mock_response = MagicMock()
        mock_response.user = mock_user
        mock_response.session = mock_session

        mock_auth_client = MagicMock()
        mock_auth_client.auth.sign_in_with_id_token.return_value = mock_response

        # User exists, with preferences_completed
        mock_admin = MagicMock()
        mock_admin.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": "social-uid"}]
        )
        mock_admin.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"preferences_completed": True}
        )

        with patch("app.services.auth_service.get_auth_client", return_value=mock_auth_client), \
             patch("app.services.auth_service.get_admin_client", return_value=mock_admin):
            result = await sign_in_with_social("google", "id-token-123")

        assert result["success"] is True
        assert "preferences_completed" in result["user"]


# ============================================
# 5. Prompt Injection Tests (~8 tests)
# ============================================

class TestPromptInjection:
    """Test that preferences are correctly injected into comparison prompts."""

    def test_build_preferences_prompt_full(self):
        """_build_preferences_prompt includes all 4 preference dimensions."""
        from app.services.extraction_service import _build_preferences_prompt
        prefs = {
            "priorities": ["price", "durability"],
            "budget": "budget",
            "lifestyle": ["student", "vegan"],
            "brand_attitude": "function_first",
        }
        prompt = _build_preferences_prompt(prefs)
        assert "price" in prompt
        assert "durability" in prompt
        assert "budget" in prompt.lower()
        assert "student" in prompt
        assert "vegan" in prompt
        assert "function_first" in prompt

    def test_build_preferences_prompt_empty_lifestyle(self):
        """Empty lifestyle should produce 'none specified' in the prompt."""
        from app.services.extraction_service import _build_preferences_prompt
        prefs = {
            "priorities": ["quality"],
            "budget": "premium",
            "lifestyle": [],
            "brand_attitude": "brand_loyal",
        }
        prompt = _build_preferences_prompt(prefs)
        assert "quality" in prompt
        assert "premium" in prompt
        assert "brand_loyal" in prompt
        assert "none specified" in prompt.lower()

    def test_build_preferences_prompt_contains_header(self):
        """Prompt should contain the 'User Preferences' section header."""
        from app.services.extraction_service import _build_preferences_prompt
        prefs = {
            "priorities": ["price"],
            "budget": "mid",
            "lifestyle": [],
            "brand_attitude": "function_first",
        }
        prompt = _build_preferences_prompt(prefs)
        assert "User Preferences" in prompt

    @pytest.mark.asyncio
    async def test_generate_comparison_with_preferences_injects_prompt(self):
        """generate_comparison includes preference section when user_preferences provided."""
        from app.services.extraction_service import generate_comparison

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"winner": "Product A", "verdict": "Best for you", "reasons": []}'

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        prefs = {
            "priorities": ["price", "durability"],
            "budget": "budget",
            "lifestyle": ["student"],
            "brand_attitude": "function_first",
        }

        with patch("app.services.extraction_service.get_client", return_value=mock_client):
            await generate_comparison(
                product1={"name": "Product A", "brand": "BrandA"},
                product2={"name": "Product B", "brand": "BrandB"},
                region="bahrain",
                user_preferences=prefs,
            )

        call_args = mock_client.chat.completions.create.call_args
        prompt_text = call_args[1]["messages"][0]["content"]
        assert "User Preferences" in prompt_text
        assert "price" in prompt_text.lower()
        assert "student" in prompt_text.lower()

    @pytest.mark.asyncio
    async def test_generate_comparison_without_preferences_no_section(self):
        """generate_comparison omits preference section when no user_preferences."""
        from app.services.extraction_service import generate_comparison

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"winner": "Product A", "verdict": "Generic verdict", "reasons": []}'

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch("app.services.extraction_service.get_client", return_value=mock_client):
            await generate_comparison(
                product1={"name": "Product A", "brand": "BrandA"},
                product2={"name": "Product B", "brand": "BrandB"},
                region="bahrain",
            )

        call_args = mock_client.chat.completions.create.call_args
        prompt_text = call_args[1]["messages"][0]["content"]
        assert "User Preferences" not in prompt_text

    @pytest.mark.asyncio
    async def test_generate_comparison_none_preferences_no_section(self):
        """Passing user_preferences=None should not inject preferences section."""
        from app.services.extraction_service import generate_comparison

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"winner": "A", "verdict": "v", "reasons": []}'

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch("app.services.extraction_service.get_client", return_value=mock_client):
            await generate_comparison(
                product1={"name": "A", "brand": "X"},
                product2={"name": "B", "brand": "Y"},
                region="bahrain",
                user_preferences=None,
            )

        call_args = mock_client.chat.completions.create.call_args
        prompt_text = call_args[1]["messages"][0]["content"]
        assert "User Preferences" not in prompt_text

    @pytest.mark.asyncio
    async def test_prompt_includes_all_priorities(self):
        """All selected priorities should appear in the injected prompt."""
        from app.services.extraction_service import generate_comparison

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"winner": "A", "verdict": "v", "reasons": []}'

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        prefs = {
            "priorities": ["eco_friendly", "health_safety", "ease_of_use"],
            "budget": "budget",
            "lifestyle": [],
            "brand_attitude": "best_of_both",
        }

        with patch("app.services.extraction_service.get_client", return_value=mock_client):
            await generate_comparison(
                product1={"name": "A", "brand": "X"},
                product2={"name": "B", "brand": "Y"},
                region="bahrain",
                user_preferences=prefs,
            )

        call_args = mock_client.chat.completions.create.call_args
        prompt_text = call_args[1]["messages"][0]["content"]
        assert "eco_friendly" in prompt_text
        assert "health_safety" in prompt_text
        assert "ease_of_use" in prompt_text

    @pytest.mark.asyncio
    async def test_prompt_includes_lifestyle_tags(self):
        """All lifestyle tags should appear in the injected prompt."""
        from app.services.extraction_service import generate_comparison

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"winner": "A", "verdict": "v", "reasons": []}'

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        prefs = {
            "priorities": ["price"],
            "budget": "mid",
            "lifestyle": ["vegan", "fitness_enthusiast", "parent"],
            "brand_attitude": "function_first",
        }

        with patch("app.services.extraction_service.get_client", return_value=mock_client):
            await generate_comparison(
                product1={"name": "A", "brand": "X"},
                product2={"name": "B", "brand": "Y"},
                region="bahrain",
                user_preferences=prefs,
            )

        call_args = mock_client.chat.completions.create.call_args
        prompt_text = call_args[1]["messages"][0]["content"]
        assert "vegan" in prompt_text
        assert "fitness_enthusiast" in prompt_text
        assert "parent" in prompt_text


# ============================================
# 6. Comparison Service Personalization Metadata (~7 tests)
# ============================================

class TestComparisonServicePersonalization:
    """Test personalized/personalization_factors in comparison service response."""

    @pytest.mark.asyncio
    async def test_personalized_true_with_preferences(self):
        """Response includes personalized=true when user_preferences provided."""
        from app.services.structured_comparison_service import StructuredComparisonService

        service = StructuredComparisonService()
        prefs = {
            "priorities": ["price"],
            "budget": "budget",
            "lifestyle": ["student"],
            "brand_attitude": "function_first",
        }

        with patch("app.services.structured_comparison_service.parse_product_query", new_callable=AsyncMock, return_value=({
            "products": [
                {"brand": "Apple", "name": "iPhone 15", "variant": None},
                {"brand": "Samsung", "name": "Galaxy S24", "variant": None},
            ],
            "category": "electronics",
        }, {"prompt_tokens": 0, "completion_tokens": 0})), patch.object(service, "_fetch_product_data", new_callable=AsyncMock, return_value={
            "name": "iPhone 15", "brand": "Apple", "specs": {}, "price": {"amount": 299},
            "reviews": {}, "rating": {},
        }), patch("app.services.structured_comparison_service.generate_comparison", new_callable=AsyncMock, return_value=({
            "winner": "iPhone 15", "verdict": "Best for you",
        }, {"prompt_tokens": 0, "completion_tokens": 0})):
            result = await service.compare_from_text(
                query="iPhone 15 vs Galaxy S24",
                user_preferences=prefs,
            )

        assert result["personalized"] is True

    @pytest.mark.asyncio
    async def test_personalized_false_without_preferences(self):
        """Response includes personalized=false when no user_preferences."""
        from app.services.structured_comparison_service import StructuredComparisonService

        service = StructuredComparisonService()

        with patch("app.services.structured_comparison_service.parse_product_query", new_callable=AsyncMock, return_value=({
            "products": [
                {"brand": "Apple", "name": "iPhone 15", "variant": None},
                {"brand": "Samsung", "name": "Galaxy S24", "variant": None},
            ],
            "category": "electronics",
        }, {"prompt_tokens": 0, "completion_tokens": 0})), patch.object(service, "_fetch_product_data", new_callable=AsyncMock, return_value={
            "name": "iPhone 15", "brand": "Apple", "specs": {}, "price": {"amount": 299},
            "reviews": {}, "rating": {},
        }), patch("app.services.structured_comparison_service.generate_comparison", new_callable=AsyncMock, return_value=({
            "winner": "iPhone 15", "verdict": "Generic verdict",
        }, {"prompt_tokens": 0, "completion_tokens": 0})):
            result = await service.compare_from_text(
                query="iPhone 15 vs Galaxy S24",
            )

        assert result["personalized"] is False

    @pytest.mark.asyncio
    async def test_personalization_factors_include_priorities(self):
        """Personalization factors should include priority_* entries."""
        from app.services.structured_comparison_service import StructuredComparisonService

        service = StructuredComparisonService()
        prefs = {
            "priorities": ["price", "quality"],
            "budget": "mid",
            "lifestyle": [],
            "brand_attitude": "function_first",
        }

        with patch("app.services.structured_comparison_service.parse_product_query", new_callable=AsyncMock, return_value=({
            "products": [
                {"brand": "A", "name": "P1", "variant": None},
                {"brand": "B", "name": "P2", "variant": None},
            ],
            "category": "electronics",
        }, {"prompt_tokens": 0, "completion_tokens": 0})), patch.object(service, "_fetch_product_data", new_callable=AsyncMock, return_value={
            "name": "P1", "brand": "A", "specs": {}, "price": {"amount": 100},
            "reviews": {}, "rating": {},
        }), patch("app.services.structured_comparison_service.generate_comparison", new_callable=AsyncMock, return_value=({
            "winner": "P1", "verdict": "v",
        }, {"prompt_tokens": 0, "completion_tokens": 0})):
            result = await service.compare_from_text(query="P1 vs P2", user_preferences=prefs)

        factors = result["personalization_factors"]
        assert "priority_price" in factors
        assert "priority_quality" in factors

    @pytest.mark.asyncio
    async def test_personalization_factors_include_budget(self):
        """Personalization factors should include budget_* entry."""
        from app.services.structured_comparison_service import StructuredComparisonService

        service = StructuredComparisonService()
        prefs = {
            "priorities": ["price"],
            "budget": "premium",
            "lifestyle": [],
            "brand_attitude": "function_first",
        }

        with patch("app.services.structured_comparison_service.parse_product_query", new_callable=AsyncMock, return_value=({
            "products": [
                {"brand": "A", "name": "P1", "variant": None},
                {"brand": "B", "name": "P2", "variant": None},
            ],
            "category": "electronics",
        }, {"prompt_tokens": 0, "completion_tokens": 0})), patch.object(service, "_fetch_product_data", new_callable=AsyncMock, return_value={
            "name": "P1", "brand": "A", "specs": {}, "price": {"amount": 100},
            "reviews": {}, "rating": {},
        }), patch("app.services.structured_comparison_service.generate_comparison", new_callable=AsyncMock, return_value=({
            "winner": "P1", "verdict": "v",
        }, {"prompt_tokens": 0, "completion_tokens": 0})):
            result = await service.compare_from_text(query="P1 vs P2", user_preferences=prefs)

        assert "budget_premium" in result["personalization_factors"]

    @pytest.mark.asyncio
    async def test_personalization_factors_include_lifestyle(self):
        """Personalization factors should include lifestyle_* entries."""
        from app.services.structured_comparison_service import StructuredComparisonService

        service = StructuredComparisonService()
        prefs = {
            "priorities": ["price"],
            "budget": "mid",
            "lifestyle": ["vegan", "student"],
            "brand_attitude": "function_first",
        }

        with patch("app.services.structured_comparison_service.parse_product_query", new_callable=AsyncMock, return_value=({
            "products": [
                {"brand": "A", "name": "P1", "variant": None},
                {"brand": "B", "name": "P2", "variant": None},
            ],
            "category": "electronics",
        }, {"prompt_tokens": 0, "completion_tokens": 0})), patch.object(service, "_fetch_product_data", new_callable=AsyncMock, return_value={
            "name": "P1", "brand": "A", "specs": {}, "price": {"amount": 100},
            "reviews": {}, "rating": {},
        }), patch("app.services.structured_comparison_service.generate_comparison", new_callable=AsyncMock, return_value=({
            "winner": "P1", "verdict": "v",
        }, {"prompt_tokens": 0, "completion_tokens": 0})):
            result = await service.compare_from_text(query="P1 vs P2", user_preferences=prefs)

        factors = result["personalization_factors"]
        assert "lifestyle_vegan" in factors
        assert "lifestyle_student" in factors

    @pytest.mark.asyncio
    async def test_personalization_factors_empty_without_prefs(self):
        """Personalization factors should be empty list without preferences."""
        from app.services.structured_comparison_service import StructuredComparisonService

        service = StructuredComparisonService()

        with patch("app.services.structured_comparison_service.parse_product_query", new_callable=AsyncMock, return_value=({
            "products": [
                {"brand": "A", "name": "P1", "variant": None},
                {"brand": "B", "name": "P2", "variant": None},
            ],
            "category": "electronics",
        }, {"prompt_tokens": 0, "completion_tokens": 0})), patch.object(service, "_fetch_product_data", new_callable=AsyncMock, return_value={
            "name": "P1", "brand": "A", "specs": {}, "price": {"amount": 100},
            "reviews": {}, "rating": {},
        }), patch("app.services.structured_comparison_service.generate_comparison", new_callable=AsyncMock, return_value=({
            "winner": "P1", "verdict": "v",
        }, {"prompt_tokens": 0, "completion_tokens": 0})):
            result = await service.compare_from_text(query="P1 vs P2")

        assert result["personalization_factors"] == []

    @pytest.mark.asyncio
    async def test_personalized_false_with_empty_dict(self):
        """Empty preferences dict should result in personalized=false."""
        from app.services.structured_comparison_service import StructuredComparisonService

        service = StructuredComparisonService()

        with patch("app.services.structured_comparison_service.parse_product_query", new_callable=AsyncMock, return_value=({
            "products": [
                {"brand": "A", "name": "P1", "variant": None},
                {"brand": "B", "name": "P2", "variant": None},
            ],
            "category": "electronics",
        }, {"prompt_tokens": 0, "completion_tokens": 0})), patch.object(service, "_fetch_product_data", new_callable=AsyncMock, return_value={
            "name": "P1", "brand": "A", "specs": {}, "price": {"amount": 100},
            "reviews": {}, "rating": {},
        }), patch("app.services.structured_comparison_service.generate_comparison", new_callable=AsyncMock, return_value=({
            "winner": "P1", "verdict": "v",
        }, {"prompt_tokens": 0, "completion_tokens": 0})):
            result = await service.compare_from_text(query="P1 vs P2", user_preferences={})

        assert result["personalized"] is False


# ============================================
# 7. Constants Validation (~2 tests)
# ============================================

class TestValidOptionConstants:
    """Test that valid option constants match the design doc."""

    def test_valid_priorities_has_eight_options(self):
        """Original 8 priority options must still be accepted (Session 41 added 6 more
        for cohort_service.seed_preferences emit values)."""
        from app.api.auth_routes import VALID_PRIORITIES
        original_eight = {"price", "quality", "brand_reputation", "durability",
                          "latest_features", "ease_of_use", "eco_friendly", "health_safety"}
        # The original 8 must still be valid (backwards compat)
        assert original_eight.issubset(set(VALID_PRIORITIES))
        # Cohort-derived enum values were added in Session 41
        cohort_added = {"best_price", "quality_reliability", "trusted_brand",
                        "warranty_support", "design_aesthetics", "value_for_money"}
        assert cohort_added.issubset(set(VALID_PRIORITIES))

    def test_valid_lifestyle_accepts_fe_picker_vocabulary(self):
        """VALID_LIFESTYLE must accept the FE LifestylePicker vocabulary so
        Edit Preferences can save (device bug 2026-07-04 — picks other than
        minimalist/tech_enthusiast 422'd). It stays a SUPERSET of the original
        backend tags for backwards-compat with any prior-seeded rows."""
        from app.api.auth_routes import VALID_LIFESTYLE
        original = {"gamer", "photographer", "fitness_enthusiast", "vegan",
                    "sensitive_skin", "parent", "student", "professional",
                    "outdoor_adventurer", "minimalist", "tech_enthusiast"}
        fe_picker = {"fitness", "budget_conscious", "tech_enthusiast",
                     "eco_conscious", "luxury_lover", "minimalist",
                     "family_focused", "frequent_traveler", "home_cook",
                     "outdoors", "creative"}
        valid = set(VALID_LIFESTYLE)
        assert original.issubset(valid), "lost backwards-compat lifestyle tags"
        assert fe_picker.issubset(valid), "FE LifestylePicker vocab must validate"
