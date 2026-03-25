"""Tests for Firecrawl service."""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import httpx

from app.services.firecrawl_service import scrape_page, scrape_page_with_status, is_available


SAMPLE_HTML = "<html><body>" + "x" * 1000 + "</body></html>"


@pytest.fixture
def mock_env_key():
    with patch.dict("os.environ", {"FIRECRAWL_API_KEY": "test-key"}):
        yield


def _make_mock_client(mock_client_cls, mock_client):
    """Wire up AsyncClient context manager mock."""
    mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)


class TestIsAvailable:
    def test_available_with_key(self):
        with patch.dict("os.environ", {"FIRECRAWL_API_KEY": "key"}):
            assert is_available() is True

    def test_unavailable_without_key(self):
        with patch.dict("os.environ", {}, clear=True):
            assert is_available() is False

    def test_unavailable_when_disabled(self):
        with patch.dict("os.environ", {"FIRECRAWL_API_KEY": "key", "ENABLE_FIRECRAWL": "false"}):
            assert is_available() is False

    def test_available_when_explicitly_enabled(self):
        with patch.dict("os.environ", {"FIRECRAWL_API_KEY": "key", "ENABLE_FIRECRAWL": "true"}):
            assert is_available() is True


class TestScrapePage:
    @pytest.mark.asyncio
    async def test_returns_html_on_success(self, mock_env_key):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"success": True, "data": {"html": SAMPLE_HTML}}

        with patch("app.services.firecrawl_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_resp
            _make_mock_client(mock_client_cls, mock_client)

            result = await scrape_page("https://example.com/product")
            assert result == SAMPLE_HTML

    @pytest.mark.asyncio
    async def test_sends_correct_payload(self, mock_env_key):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"success": True, "data": {"html": SAMPLE_HTML}}

        with patch("app.services.firecrawl_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_resp
            _make_mock_client(mock_client_cls, mock_client)

            await scrape_page("https://example.com/product")
            call_kwargs = mock_client.post.call_args
            payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
            assert payload["url"] == "https://example.com/product"
            assert payload["formats"] == ["html"]
            assert "waitFor" in payload

    @pytest.mark.asyncio
    async def test_returns_none_without_key(self):
        with patch.dict("os.environ", {}, clear=True):
            result = await scrape_page("https://example.com")
            assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_api_error(self, mock_env_key):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"success": False, "error": "blocked"}

        with patch("app.services.firecrawl_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_resp
            _make_mock_client(mock_client_cls, mock_client)

            result = await scrape_page("https://example.com/product")
            assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_timeout(self, mock_env_key):
        with patch("app.services.firecrawl_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.TimeoutException("timeout")
            _make_mock_client(mock_client_cls, mock_client)

            result = await scrape_page("https://example.com/product")
            assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_short_html(self, mock_env_key):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"success": True, "data": {"html": "<html></html>"}}

        with patch("app.services.firecrawl_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_resp
            _make_mock_client(mock_client_cls, mock_client)

            result = await scrape_page("https://example.com/product")
            assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_http_500(self, mock_env_key):
        mock_resp = MagicMock()
        mock_resp.status_code = 500

        with patch("app.services.firecrawl_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_resp
            _make_mock_client(mock_client_cls, mock_client)

            result = await scrape_page("https://example.com/product")
            assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_connection_error(self, mock_env_key):
        with patch("app.services.firecrawl_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.ConnectError("refused")
            _make_mock_client(mock_client_cls, mock_client)

            result = await scrape_page("https://example.com/product")
            assert result is None


class TestScrapePageWithStatus:
    @pytest.mark.asyncio
    async def test_returns_html_and_200(self, mock_env_key):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"success": True, "data": {"html": SAMPLE_HTML}}

        with patch("app.services.firecrawl_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_resp
            _make_mock_client(mock_client_cls, mock_client)

            html, status = await scrape_page_with_status("https://example.com")
            assert html == SAMPLE_HTML
            assert status == 200

    @pytest.mark.asyncio
    async def test_returns_none_and_200_on_no_content(self, mock_env_key):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"success": True, "data": {"html": "<html></html>"}}

        with patch("app.services.firecrawl_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_resp
            _make_mock_client(mock_client_cls, mock_client)

            html, status = await scrape_page_with_status("https://example.com")
            assert html is None
            assert status == 200

    @pytest.mark.asyncio
    async def test_returns_none_and_429(self, mock_env_key):
        mock_resp = MagicMock()
        mock_resp.status_code = 429

        with patch("app.services.firecrawl_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_resp
            _make_mock_client(mock_client_cls, mock_client)

            html, status = await scrape_page_with_status("https://example.com")
            assert html is None
            assert status == 429

    @pytest.mark.asyncio
    async def test_returns_none_and_503(self, mock_env_key):
        mock_resp = MagicMock()
        mock_resp.status_code = 503

        with patch("app.services.firecrawl_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_resp
            _make_mock_client(mock_client_cls, mock_client)

            html, status = await scrape_page_with_status("https://example.com")
            assert html is None
            assert status == 503

    @pytest.mark.asyncio
    async def test_returns_none_and_0_on_timeout(self, mock_env_key):
        with patch("app.services.firecrawl_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.TimeoutException("timeout")
            _make_mock_client(mock_client_cls, mock_client)

            html, status = await scrape_page_with_status("https://example.com")
            assert html is None
            assert status == 0

    @pytest.mark.asyncio
    async def test_returns_none_and_0_on_connection_error(self, mock_env_key):
        with patch("app.services.firecrawl_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.ConnectError("refused")
            _make_mock_client(mock_client_cls, mock_client)

            html, status = await scrape_page_with_status("https://example.com")
            assert html is None
            assert status == 0

    @pytest.mark.asyncio
    async def test_returns_none_and_0_without_key(self):
        with patch.dict("os.environ", {}, clear=True):
            html, status = await scrape_page_with_status("https://example.com")
            assert html is None
            assert status == 0


class TestFirecrawlEdgeCases:
    """Additional edge-case tests."""

    @pytest.mark.asyncio
    async def test_scrape_page_missing_data_key(self, mock_env_key):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"success": True}  # no "data" key

        with patch("app.services.firecrawl_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_resp
            _make_mock_client(mock_client_cls, mock_client)

            result = await scrape_page("https://example.com/product")
            assert result is None

    @pytest.mark.asyncio
    async def test_scrape_page_empty_html_string(self, mock_env_key):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"success": True, "data": {"html": ""}}

        with patch("app.services.firecrawl_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_resp
            _make_mock_client(mock_client_cls, mock_client)

            result = await scrape_page("https://example.com/product")
            assert result is None

    @pytest.mark.asyncio
    async def test_scrape_page_exactly_500_bytes(self, mock_env_key):
        # Exactly 500 bytes is NOT > 500, so should return None
        html_500 = "x" * 500
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"success": True, "data": {"html": html_500}}

        with patch("app.services.firecrawl_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_resp
            _make_mock_client(mock_client_cls, mock_client)

            result = await scrape_page("https://example.com/product")
            assert result is None

    @pytest.mark.asyncio
    async def test_scrape_page_501_bytes_succeeds(self, mock_env_key):
        html_501 = "x" * 501
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"success": True, "data": {"html": html_501}}

        with patch("app.services.firecrawl_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_resp
            _make_mock_client(mock_client_cls, mock_client)

            result = await scrape_page("https://example.com/product")
            assert result == html_501

    @pytest.mark.asyncio
    async def test_scrape_page_malformed_json_response(self, mock_env_key):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.side_effect = ValueError("Invalid JSON")

        with patch("app.services.firecrawl_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_resp
            _make_mock_client(mock_client_cls, mock_client)

            result = await scrape_page("https://example.com/product")
            assert result is None

    @pytest.mark.asyncio
    async def test_scrape_page_with_status_malformed_json(self, mock_env_key):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.side_effect = ValueError("Invalid JSON")

        with patch("app.services.firecrawl_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_resp
            _make_mock_client(mock_client_cls, mock_client)

            html, status = await scrape_page_with_status("https://example.com")
            assert html is None
            # ValueError caught by generic except → status 0
            assert status == 0

    @pytest.mark.asyncio
    async def test_scrape_page_success_false_no_error_field(self, mock_env_key):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"success": False}  # no "error" key

        with patch("app.services.firecrawl_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_resp
            _make_mock_client(mock_client_cls, mock_client)

            result = await scrape_page("https://example.com/product")
            assert result is None

    @pytest.mark.asyncio
    async def test_scrape_page_http_403(self, mock_env_key):
        mock_resp = MagicMock()
        mock_resp.status_code = 403

        with patch("app.services.firecrawl_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_resp
            _make_mock_client(mock_client_cls, mock_client)

            result = await scrape_page("https://example.com/product")
            assert result is None
