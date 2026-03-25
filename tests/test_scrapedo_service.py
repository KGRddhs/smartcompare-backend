"""Tests for Scrape.do service."""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import httpx

from app.services.scrapedo_service import render_page, render_page_with_status, is_available


SAMPLE_HTML = "<html><body>" + "x" * 1000 + "</body></html>"


@pytest.fixture
def mock_env_token():
    with patch.dict("os.environ", {"SCRAPEDO_API_TOKEN": "test-token"}):
        yield


def _make_mock_client(mock_client_cls, mock_client):
    """Wire up AsyncClient context manager mock."""
    mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)


class TestIsAvailable:
    def test_available_with_token(self):
        with patch.dict("os.environ", {"SCRAPEDO_API_TOKEN": "tok"}):
            assert is_available() is True

    def test_unavailable_without_token(self):
        with patch.dict("os.environ", {}, clear=True):
            assert is_available() is False

    def test_unavailable_when_disabled(self):
        with patch.dict("os.environ", {"SCRAPEDO_API_TOKEN": "tok", "ENABLE_SCRAPEDO": "false"}):
            assert is_available() is False

    def test_available_when_explicitly_enabled(self):
        with patch.dict("os.environ", {"SCRAPEDO_API_TOKEN": "tok", "ENABLE_SCRAPEDO": "true"}):
            assert is_available() is True


class TestRenderPage:
    @pytest.mark.asyncio
    async def test_returns_html_on_success(self, mock_env_token):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = SAMPLE_HTML

        with patch("app.services.scrapedo_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            _make_mock_client(mock_client_cls, mock_client)

            result = await render_page("https://example.com/product")
            assert result == SAMPLE_HTML

    @pytest.mark.asyncio
    async def test_passes_correct_params(self, mock_env_token):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = SAMPLE_HTML

        with patch("app.services.scrapedo_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            _make_mock_client(mock_client_cls, mock_client)

            await render_page("https://example.com/product")
            call_kwargs = mock_client.get.call_args
            params = call_kwargs.kwargs.get("params") or call_kwargs[1].get("params")
            assert params["token"] == "test-token"
            assert params["url"] == "https://example.com/product"
            assert params["render"] == "true"

    @pytest.mark.asyncio
    async def test_returns_none_without_token(self):
        with patch.dict("os.environ", {}, clear=True):
            result = await render_page("https://example.com")
            assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_short_html(self, mock_env_token):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "<html></html>"

        with patch("app.services.scrapedo_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            _make_mock_client(mock_client_cls, mock_client)

            result = await render_page("https://example.com/product")
            assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_timeout(self, mock_env_token):
        with patch("app.services.scrapedo_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.side_effect = httpx.TimeoutException("timeout")
            _make_mock_client(mock_client_cls, mock_client)

            result = await render_page("https://example.com/product")
            assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_http_500(self, mock_env_token):
        mock_resp = MagicMock()
        mock_resp.status_code = 500

        with patch("app.services.scrapedo_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            _make_mock_client(mock_client_cls, mock_client)

            result = await render_page("https://example.com/product")
            assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_connection_error(self, mock_env_token):
        with patch("app.services.scrapedo_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.side_effect = httpx.ConnectError("refused")
            _make_mock_client(mock_client_cls, mock_client)

            result = await render_page("https://example.com/product")
            assert result is None


class TestRenderPageWithStatus:
    @pytest.mark.asyncio
    async def test_returns_html_and_200(self, mock_env_token):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = SAMPLE_HTML

        with patch("app.services.scrapedo_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            _make_mock_client(mock_client_cls, mock_client)

            html, status = await render_page_with_status("https://example.com")
            assert html == SAMPLE_HTML
            assert status == 200

    @pytest.mark.asyncio
    async def test_returns_none_and_200_on_no_content(self, mock_env_token):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "<html></html>"

        with patch("app.services.scrapedo_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            _make_mock_client(mock_client_cls, mock_client)

            html, status = await render_page_with_status("https://example.com")
            assert html is None
            assert status == 200

    @pytest.mark.asyncio
    async def test_returns_none_and_429(self, mock_env_token):
        mock_resp = MagicMock()
        mock_resp.status_code = 429

        with patch("app.services.scrapedo_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            _make_mock_client(mock_client_cls, mock_client)

            html, status = await render_page_with_status("https://example.com")
            assert html is None
            assert status == 429

    @pytest.mark.asyncio
    async def test_returns_none_and_0_on_timeout(self, mock_env_token):
        with patch("app.services.scrapedo_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.side_effect = httpx.TimeoutException("timeout")
            _make_mock_client(mock_client_cls, mock_client)

            html, status = await render_page_with_status("https://example.com")
            assert html is None
            assert status == 0

    @pytest.mark.asyncio
    async def test_returns_none_and_0_on_connection_error(self, mock_env_token):
        with patch("app.services.scrapedo_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.side_effect = httpx.ConnectError("refused")
            _make_mock_client(mock_client_cls, mock_client)

            html, status = await render_page_with_status("https://example.com")
            assert html is None
            assert status == 0

    @pytest.mark.asyncio
    async def test_returns_none_and_0_without_token(self):
        with patch.dict("os.environ", {}, clear=True):
            html, status = await render_page_with_status("https://example.com")
            assert html is None
            assert status == 0


class TestScrapedoEdgeCases:
    """Additional edge-case tests."""

    @pytest.mark.asyncio
    async def test_render_page_empty_string_response(self, mock_env_token):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = ""

        with patch("app.services.scrapedo_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            _make_mock_client(mock_client_cls, mock_client)

            result = await render_page("https://example.com/product")
            assert result is None

    @pytest.mark.asyncio
    async def test_render_page_exactly_500_bytes(self, mock_env_token):
        html_500 = "x" * 500
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = html_500

        with patch("app.services.scrapedo_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            _make_mock_client(mock_client_cls, mock_client)

            result = await render_page("https://example.com/product")
            assert result is None

    @pytest.mark.asyncio
    async def test_render_page_501_bytes_succeeds(self, mock_env_token):
        html_501 = "x" * 501
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = html_501

        with patch("app.services.scrapedo_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            _make_mock_client(mock_client_cls, mock_client)

            result = await render_page("https://example.com/product")
            assert result == html_501

    @pytest.mark.asyncio
    async def test_render_page_http_403(self, mock_env_token):
        mock_resp = MagicMock()
        mock_resp.status_code = 403

        with patch("app.services.scrapedo_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            _make_mock_client(mock_client_cls, mock_client)

            result = await render_page("https://example.com/product")
            assert result is None

    @pytest.mark.asyncio
    async def test_render_page_with_status_http_403(self, mock_env_token):
        mock_resp = MagicMock()
        mock_resp.status_code = 403

        with patch("app.services.scrapedo_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            _make_mock_client(mock_client_cls, mock_client)

            html, status = await render_page_with_status("https://example.com")
            assert html is None
            assert status == 403

    @pytest.mark.asyncio
    async def test_render_page_with_status_503(self, mock_env_token):
        mock_resp = MagicMock()
        mock_resp.status_code = 503

        with patch("app.services.scrapedo_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            _make_mock_client(mock_client_cls, mock_client)

            html, status = await render_page_with_status("https://example.com")
            assert html is None
            assert status == 503

    @pytest.mark.asyncio
    async def test_render_page_generic_exception(self, mock_env_token):
        with patch("app.services.scrapedo_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.side_effect = RuntimeError("unexpected")
            _make_mock_client(mock_client_cls, mock_client)

            result = await render_page("https://example.com/product")
            assert result is None

    @pytest.mark.asyncio
    async def test_render_page_with_status_generic_exception(self, mock_env_token):
        with patch("app.services.scrapedo_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.side_effect = RuntimeError("unexpected")
            _make_mock_client(mock_client_cls, mock_client)

            html, status = await render_page_with_status("https://example.com")
            assert html is None
            assert status == 0
