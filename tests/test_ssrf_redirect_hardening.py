"""SSRF hardening (scraping audit 2026-07-08).

Two fetch paths followed redirects without re-validating each hop, so a
public URL that 30x-redirects to a private/loopback/link-local/cloud-metadata
address (169.254.169.254) would be fetched — an exfiltrating SSRF:
  1. url_extraction_service.fetch_page (public /url/* routes) — now follows
     redirects MANUALLY, bounded, re-validating every hop with validate_external_url.
  2. price_service.fetch_page_price — now routes through curl_fetch_html_same_site
     (validates the initial URL + every hop, pinned to the source host) instead of
     the unvalidated curl_fetch_html.
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock

import app.services.url_extraction_service as ues


class _Resp:
    def __init__(self, is_redirect=False, next_url=None, text="", status=200):
        self.is_redirect = is_redirect
        self.next_request = MagicMock(url=next_url) if next_url else None
        self.text = text
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class _Client:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def __call__(self, **kwargs):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def get(self, url, headers=None):
        self.calls.append(url)
        return self._responses.pop(0)


def _patch(monkeypatch, client, validator):
    monkeypatch.setattr(ues.httpx, "AsyncClient", client)
    monkeypatch.setattr("app.utils.url_validator.validate_external_url", validator)


# --- 1. fetch_page: redirect to internal is BLOCKED (never fetched) ---
def test_fetch_page_blocks_redirect_to_metadata(monkeypatch):
    client = _Client([_Resp(is_redirect=True, next_url="http://169.254.169.254/latest/meta-data/")])
    _patch(monkeypatch, client, lambda u: "169.254" not in u and "127.0.0" not in u)
    result = asyncio.run(ues.fetch_page("https://attacker.example/p"))
    assert result is None
    # the internal target must NEVER be fetched
    assert not any("169.254.169.254" in c for c in client.calls)


def test_fetch_page_blocks_private_initial_url(monkeypatch):
    client = _Client([_Resp(text="secret")])
    _patch(monkeypatch, client, lambda u: "127.0.0.1" not in u and "169.254" not in u)
    result = asyncio.run(ues.fetch_page("http://127.0.0.1/admin"))
    assert result is None
    assert client.calls == []  # never even attempted


def test_fetch_page_follows_valid_redirect(monkeypatch):
    client = _Client([
        _Resp(is_redirect=True, next_url="https://store.example/final"),
        _Resp(text="<html>ok</html>"),
    ])
    _patch(monkeypatch, client, lambda u: True)  # all public
    result = asyncio.run(ues.fetch_page("https://store.example/p"))
    assert result == "<html>ok</html>"
    assert client.calls == ["https://store.example/p", "https://store.example/final"]


def test_fetch_page_caps_redirect_chain(monkeypatch):
    # an endless public redirect loop terminates (bounded), returns None
    client = _Client([_Resp(is_redirect=True, next_url=f"https://x.example/{i}") for i in range(10)])
    _patch(monkeypatch, client, lambda u: True)
    result = asyncio.run(ues.fetch_page("https://x.example/start"))
    assert result is None
    assert len(client.calls) <= 6  # bounded (~5 hops)


# --- 2. fetch_page_price routes through the VALIDATED same-site helper ---
def test_fetch_page_price_uses_validated_fetch(monkeypatch):
    import app.services.price_service as ps
    monkeypatch.setattr(ps, "ENABLE_PAGE_SCRAPE", True)
    same_site = AsyncMock(return_value=None)
    unvalidated = AsyncMock(return_value="<html>should-not-be-called</html>")
    monkeypatch.setattr(ps, "curl_fetch_html_same_site", same_site)
    monkeypatch.setattr(ps, "curl_fetch_html", unvalidated)
    asyncio.run(ps.fetch_page_price("https://alibaksh.com/product/x", "Lattafa Khamrah", "BHD"))
    same_site.assert_awaited_once()
    # the unvalidated fetch must NOT be used on this path anymore
    unvalidated.assert_not_awaited()
    # called with (url, domain)
    args = same_site.await_args.args
    assert args[0] == "https://alibaksh.com/product/x"
    assert args[1] == "alibaksh.com"
