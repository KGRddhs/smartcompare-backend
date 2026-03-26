"""Tests for app version check endpoint."""
import os
from unittest.mock import patch
from fastapi.testclient import TestClient


class TestVersionRoutes:

    def test_version_returns_200(self):
        from app.main import app
        client = TestClient(app)
        response = client.get("/api/v1/app/version")
        assert response.status_code == 200
        data = response.json()
        assert "min_version" in data
        assert "latest_version" in data
        assert "force_update" in data

    def test_version_no_auth_required(self):
        from app.main import app
        client = TestClient(app)
        response = client.get("/api/v1/app/version")
        assert response.status_code == 200

    def test_version_defaults(self):
        """Without env vars, defaults should be returned."""
        from app.api.version_routes import get_version_info
        # Clear env vars if set
        env_overrides = {
            "APP_MIN_VERSION": "",
            "APP_LATEST_VERSION": "",
            "APP_FORCE_UPDATE": "",
        }
        with patch.dict(os.environ, env_overrides, clear=False):
            # Remove the keys entirely
            for key in env_overrides:
                os.environ.pop(key, None)
            info = get_version_info()
        assert info["min_version"] == "1.0.0"
        assert info["latest_version"] == "1.0.0"
        assert info["force_update"] is False

    @patch.dict(os.environ, {
        "APP_MIN_VERSION": "2.0.0",
        "APP_LATEST_VERSION": "2.1.0",
        "APP_FORCE_UPDATE": "true",
    })
    def test_version_reads_from_env(self):
        from app.api.version_routes import get_version_info
        info = get_version_info()
        assert info["min_version"] == "2.0.0"
        assert info["latest_version"] == "2.1.0"
        assert info["force_update"] is True

    @patch.dict(os.environ, {"APP_FORCE_UPDATE": "false"})
    def test_force_update_false(self):
        from app.api.version_routes import get_version_info
        info = get_version_info()
        assert info["force_update"] is False

    @patch.dict(os.environ, {"APP_FORCE_UPDATE": "TRUE"})
    def test_force_update_case_insensitive(self):
        from app.api.version_routes import get_version_info
        info = get_version_info()
        assert info["force_update"] is True

    def test_version_response_includes_store_urls(self):
        from app.api.version_routes import get_version_info
        info = get_version_info()
        assert "update_url_ios" in info
        assert "update_url_android" in info
