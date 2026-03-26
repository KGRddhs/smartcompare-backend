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
