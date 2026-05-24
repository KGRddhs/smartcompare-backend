"""Tests for legal endpoints."""
from fastapi.testclient import TestClient


class TestLegalRoutes:

    def test_privacy_policy_returns_200(self):
        from app.main import app
        client = TestClient(app)
        response = client.get("/api/v1/legal/privacy")
        assert response.status_code == 200
        data = response.json()
        assert "title" in data
        assert "content" in data
        assert "last_updated" in data
        assert data["title"] == "Privacy Policy"
        assert len(data["content"]) > 100

    def test_terms_of_service_returns_200(self):
        from app.main import app
        client = TestClient(app)
        response = client.get("/api/v1/legal/terms")
        assert response.status_code == 200
        data = response.json()
        assert "title" in data
        assert "content" in data
        assert "last_updated" in data
        assert data["title"] == "Terms of Service"
        assert len(data["content"]) > 100

    def test_legal_endpoints_no_auth_required(self):
        from app.main import app
        client = TestClient(app)
        # No Authorization header
        r1 = client.get("/api/v1/legal/privacy")
        r2 = client.get("/api/v1/legal/terms")
        assert r1.status_code == 200
        assert r2.status_code == 200

    def test_privacy_content_mentions_data(self):
        """Privacy policy should mention data collection."""
        from app.main import app
        client = TestClient(app)
        response = client.get("/api/v1/legal/privacy")
        content = response.json()["content"].lower()
        assert "data" in content
        assert "collect" in content

    def test_terms_content_mentions_use(self):
        """Terms should mention acceptable use."""
        from app.main import app
        client = TestClient(app)
        response = client.get("/api/v1/legal/terms")
        content = response.json()["content"].lower()
        assert "use" in content

    def test_last_updated_is_date_format(self):
        from app.main import app
        client = TestClient(app)
        response = client.get("/api/v1/legal/privacy")
        last_updated = response.json()["last_updated"]
        # Should be YYYY-MM-DD format
        parts = last_updated.split("-")
        assert len(parts) == 3
        assert len(parts[0]) == 4  # year

    def test_read_legal_file_missing_file(self):
        """_read_legal_file should return fallback for missing files."""
        from app.api.legal_routes import _read_legal_file
        result = _read_legal_file("nonexistent.md")
        assert result == "Content not available."

    def test_privacy_policy_returns_200_with_markdown_body(self):
        """Bundle D Task 1.B.1 acceptance — frontend calls /privacy_policy not /privacy."""
        from app.main import app
        client = TestClient(app)
        response = client.get("/api/v1/legal/privacy_policy")
        assert response.status_code == 200
        body = response.json()
        assert "content" in body
        assert "Qaren" in body["content"]

    def test_terms_of_service_returns_200_with_markdown_body(self):
        """Bundle D Task 1.B.1 acceptance — frontend calls /terms_of_service not /terms."""
        from app.main import app
        client = TestClient(app)
        response = client.get("/api/v1/legal/terms_of_service")
        assert response.status_code == 200
        body = response.json()
        assert "content" in body
        assert "Qaren" in body["content"]

    def test_legal_content_no_smartcompare_brand_residue(self):
        """Bundle D Task 1.B.7 (R22) acceptance — Qaren-only branding, no SmartCompare leak."""
        from app.main import app
        client = TestClient(app)
        for path in ("/api/v1/legal/privacy_policy", "/api/v1/legal/terms_of_service"):
            response = client.get(path)
            assert response.status_code == 200
            body = response.json()["content"]
            assert "SmartCompare" not in body
            assert "smartcompare.app" not in body

    def test_terms_referral_section_matches_migration_023_policy(self):
        """Bundle D — § 12 referral copy must match the actual cap (3 lifetime per
        device per Migration 023 + Bundle B/C/D), NOT the legacy 3-per-week +
        15-per-month + 30-day-expiry numbers from the pre-Bundle-A draft.
        Catches Native/Ops-flagged drift between code (`referral_service.LIFETIME_CAP=3`,
        `BONUS_EXPIRY_DAYS=7`) and legal docs.
        """
        from app.main import app
        client = TestClient(app)
        response = client.get("/api/v1/legal/terms_of_service")
        assert response.status_code == 200
        body = response.json()["content"]
        # Forbidden stale numbers
        assert "3 shares per week" not in body
        assert "Maximum 15 referral" not in body
        assert "15 referral comparisons per month" not in body
        assert "expire 30 days" not in body
        # Required current numbers
        assert "3 successful invites per device" in body
        assert "7 days" in body
