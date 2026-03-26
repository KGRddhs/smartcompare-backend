"""Tests for account deletion endpoint, password strength, and email resend verification."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient


class TestAccountDeletion:

    def test_delete_account_requires_auth(self):
        from app.main import app
        client = TestClient(app)
        response = client.delete("/api/v1/auth/account")
        assert response.status_code in (401, 403)

    @patch("app.api.auth_routes.verify_token")
    @patch("app.api.auth_routes.delete_user_account")
    def test_delete_account_success(self, mock_delete, mock_verify):
        from app.main import app
        client = TestClient(app)
        mock_verify.return_value = {"id": "user-123", "email": "test@test.com"}
        mock_delete.return_value = True
        response = client.delete(
            "/api/v1/auth/account",
            headers={"Authorization": "Bearer valid-token"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        mock_delete.assert_called_once_with("user-123")

    @patch("app.api.auth_routes.verify_token")
    @patch("app.api.auth_routes.delete_user_account")
    @patch("app.middleware.rate_limiter.limiter.enabled", False)
    def test_delete_account_failure(self, mock_delete, mock_verify):
        from app.main import app
        client = TestClient(app)
        mock_verify.return_value = {"id": "user-123", "email": "test@test.com"}
        mock_delete.side_effect = Exception("Deletion failed")
        response = client.delete(
            "/api/v1/auth/account",
            headers={"Authorization": "Bearer valid-token"},
        )
        assert response.status_code == 500

    @patch("app.api.auth_routes.verify_token")
    @patch("app.api.auth_routes.delete_user_account")
    @patch("app.middleware.rate_limiter.limiter.enabled", False)
    def test_delete_account_response_message(self, mock_delete, mock_verify):
        from app.main import app
        client = TestClient(app)
        mock_verify.return_value = {"id": "user-456", "email": "test@test.com"}
        mock_delete.return_value = True
        response = client.delete(
            "/api/v1/auth/account",
            headers={"Authorization": "Bearer valid-token"},
        )
        data = response.json()
        assert "deleted" in data["message"].lower()


class TestPasswordStrength:

    def test_short_password_rejected(self):
        from app.main import app
        client = TestClient(app)
        response = client.post("/api/v1/auth/register", json={
            "email": "test@example.com",
            "password": "short",
        })
        assert response.status_code == 422

    def test_no_uppercase_rejected(self):
        from app.main import app
        client = TestClient(app)
        response = client.post("/api/v1/auth/register", json={
            "email": "test@example.com",
            "password": "alllowercase1",
        })
        assert response.status_code == 422

    def test_no_lowercase_rejected(self):
        from app.main import app
        client = TestClient(app)
        response = client.post("/api/v1/auth/register", json={
            "email": "test@example.com",
            "password": "ALLUPPERCASE1",
        })
        assert response.status_code == 422

    def test_no_number_rejected(self):
        from app.main import app
        client = TestClient(app)
        response = client.post("/api/v1/auth/register", json={
            "email": "test@example.com",
            "password": "NoNumberHere",
        })
        assert response.status_code == 422

    def test_valid_password_accepted(self):
        """Validates the Pydantic model directly."""
        from app.api.auth_routes import RegisterRequest
        req = RegisterRequest(email="test@example.com", password="ValidPass123")
        assert req.password == "ValidPass123"

    def test_change_password_strength_validated(self):
        """ChangePasswordRequest also validates new_password."""
        from app.api.auth_routes import ChangePasswordRequest
        with pytest.raises(Exception):
            ChangePasswordRequest(current_password="old", new_password="weak")

    def test_change_password_valid(self):
        from app.api.auth_routes import ChangePasswordRequest
        req = ChangePasswordRequest(current_password="old", new_password="StrongPass1")
        assert req.new_password == "StrongPass1"

    def test_exactly_10_chars_accepted(self):
        from app.api.auth_routes import RegisterRequest
        req = RegisterRequest(email="test@example.com", password="Abcdefgh1x")
        assert req.password == "Abcdefgh1x"

    def test_9_chars_rejected(self):
        from app.api.auth_routes import RegisterRequest
        with pytest.raises(Exception):
            RegisterRequest(email="test@example.com", password="Abcdefg1x")


class TestResendVerification:

    @patch("app.api.auth_routes.resend_verification_email")
    def test_resend_verification_success(self, mock_resend):
        from app.main import app
        client = TestClient(app)
        mock_resend.return_value = True
        response = client.post("/api/v1/auth/resend-verification", json={
            "email": "test@example.com",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @patch("app.api.auth_routes.resend_verification_email")
    def test_resend_verification_failure_still_returns_success(self, mock_resend):
        """Always return success to prevent email enumeration."""
        from app.main import app
        client = TestClient(app)
        mock_resend.side_effect = Exception("Supabase error")
        response = client.post("/api/v1/auth/resend-verification", json={
            "email": "test@example.com",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_resend_verification_no_auth_required(self):
        """Endpoint should not require auth."""
        from app.main import app
        client = TestClient(app)
        with patch("app.api.auth_routes.resend_verification_email") as mock_resend:
            mock_resend.return_value = True
            response = client.post("/api/v1/auth/resend-verification", json={
                "email": "test@example.com",
            })
            assert response.status_code == 200


class TestCascadeDelete:

    @patch("app.services.database_service.get_supabase_client")
    @pytest.mark.asyncio
    async def test_cascade_delete_calls_all_tables(self, mock_client):
        from app.services.database_service import delete_user_data_cascade

        # Build mock chain
        mock_table = MagicMock()
        mock_delete_chain = MagicMock()
        mock_delete_chain.eq.return_value.execute.return_value = MagicMock(data=[])
        mock_table.delete.return_value = mock_delete_chain

        mock_update_chain = MagicMock()
        mock_update_chain.eq.return_value.execute.return_value = MagicMock(data=[])
        mock_table.update.return_value = mock_update_chain

        mock_client.return_value.table.return_value = mock_table

        result = await delete_user_data_cascade("user-123")
        assert result is True

        # Verify all tables were accessed
        table_calls = [call[0][0] for call in mock_client.return_value.table.call_args_list]
        assert "user_events" in table_calls
        assert "comparison_feedback" in table_calls
        assert "comparisons" in table_calls
        assert "search_logs" in table_calls
        assert "users" in table_calls

    @patch("app.services.database_service.get_supabase_client")
    @pytest.mark.asyncio
    async def test_cascade_delete_raises_on_error(self, mock_client):
        from app.services.database_service import delete_user_data_cascade

        mock_client.return_value.table.side_effect = Exception("DB error")

        with pytest.raises(Exception, match="DB error"):
            await delete_user_data_cascade("user-123")


class TestDeleteUserAccount:

    @patch("app.services.auth_service.get_admin_client")
    @patch("app.services.database_service.delete_user_data_cascade")
    @pytest.mark.asyncio
    async def test_delete_user_account_calls_cascade_then_auth(self, mock_cascade, mock_admin):
        from app.services.auth_service import delete_user_account

        mock_cascade.return_value = True
        mock_admin_client = MagicMock()
        mock_admin.return_value = mock_admin_client

        result = await delete_user_account("user-123")
        assert result is True
        mock_cascade.assert_called_once_with("user-123")
        mock_admin_client.auth.admin.delete_user.assert_called_once_with("user-123")


class TestDatabaseServiceLogging:
    """Verify print() calls have been replaced with logger."""

    def test_no_print_statements_in_database_service(self):
        """database_service.py should use logger, not print()."""
        import inspect
        from app.services import database_service
        source = inspect.getsource(database_service)
        # Count print( calls — should be zero
        # Exclude comments
        lines = source.split("\n")
        print_lines = [
            line.strip() for line in lines
            if "print(" in line and not line.strip().startswith("#")
        ]
        assert len(print_lines) == 0, f"Found print() calls: {print_lines}"

    def test_no_print_statements_in_auth_service(self):
        """auth_service.py should use logger, not print()."""
        import inspect
        from app.services import auth_service
        source = inspect.getsource(auth_service)
        lines = source.split("\n")
        print_lines = [
            line.strip() for line in lines
            if "print(" in line and not line.strip().startswith("#")
        ]
        assert len(print_lines) == 0, f"Found print() calls: {print_lines}"
