"""Tests for audit logging service."""
import pytest
from unittest.mock import patch, MagicMock


class TestAuditService:
    @pytest.mark.asyncio
    async def test_log_audit_event_creates_entry(self):
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_table.insert.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[{"id": "test"}])

        with patch("app.services.audit_service.get_admin_supabase_client", return_value=mock_client):
            from app.services.audit_service import log_audit_event
            await log_audit_event(
                event_type="login_success",
                user_id="user-123",
                ip_address="1.2.3.4",
                endpoint="/api/v1/auth/login",
                details={"email": "test@example.com"}
            )
            mock_client.table.assert_called_with("admin_audit_log")
            insert_call = mock_table.insert.call_args[0][0]
            assert insert_call["event_type"] == "login_success"
            assert insert_call["user_id"] == "user-123"
            assert insert_call["ip_address"] == "1.2.3.4"
            assert insert_call["endpoint"] == "/api/v1/auth/login"

    @pytest.mark.asyncio
    async def test_log_audit_event_handles_error_gracefully(self):
        mock_client = MagicMock()
        mock_client.table.side_effect = Exception("DB error")

        with patch("app.services.audit_service.get_admin_supabase_client", return_value=mock_client):
            from app.services.audit_service import log_audit_event
            # Should not raise — fire-and-forget
            await log_audit_event(event_type="test_event")

    @pytest.mark.asyncio
    async def test_log_audit_event_with_no_optional_fields(self):
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_table.insert.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[{"id": "test"}])

        with patch("app.services.audit_service.get_admin_supabase_client", return_value=mock_client):
            from app.services.audit_service import log_audit_event
            await log_audit_event(event_type="rate_limit_exceeded")
            insert_call = mock_table.insert.call_args[0][0]
            assert insert_call["event_type"] == "rate_limit_exceeded"
            assert insert_call["user_id"] is None
            assert insert_call["ip_address"] is None
            assert insert_call["endpoint"] is None
            assert insert_call["details"] is None

    @pytest.mark.asyncio
    async def test_log_audit_event_includes_timestamp(self):
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_table.insert.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[{"id": "test"}])

        with patch("app.services.audit_service.get_admin_supabase_client", return_value=mock_client):
            from app.services.audit_service import log_audit_event
            await log_audit_event(event_type="admin_access")
            insert_call = mock_table.insert.call_args[0][0]
            assert "created_at" in insert_call
            assert insert_call["created_at"] is not None
