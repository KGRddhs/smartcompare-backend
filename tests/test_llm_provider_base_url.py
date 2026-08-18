"""OpenAI-compatible provider indirection (2026-08-17).

The load-bearing invariant: with OPENAI_BASE_URL unset, every client is
constructed exactly as before, so this is a prod no-op until it is configured.
"""
import importlib
import os

import pytest

from app.services.llm_provider import (
    provider_base_url,
    describe_provider,
    is_custom_provider,
    STOCK_OPENAI_BASE_URL,
)


# ------------------------------------------------------------ default no-op

def test_unset_is_stock_openai(monkeypatch):
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    assert provider_base_url() == STOCK_OPENAI_BASE_URL
    assert is_custom_provider() is False
    assert describe_provider() == "openai"


@pytest.mark.parametrize("blank", ["", "   ", "\t", "\n"])
def test_blank_is_stock_openai(monkeypatch, blank):
    monkeypatch.setenv("OPENAI_BASE_URL", blank)
    assert provider_base_url() == STOCK_OPENAI_BASE_URL
    assert is_custom_provider() is False


# --------------------------------------------------------------- happy path

@pytest.mark.parametrize("url", [
    "https://api.groq.com/openai/v1",
    "http://localhost:4000",
    "https://gateway.ai.cloudflare.com/v1/acct/app/openai",
])
def test_valid_url_passes_through(monkeypatch, url):
    monkeypatch.setenv("OPENAI_BASE_URL", url)
    assert provider_base_url() == url
    assert describe_provider() == f"openai-compatible@{url}"


def test_surrounding_whitespace_is_stripped(monkeypatch):
    monkeypatch.setenv("OPENAI_BASE_URL", "  https://example.test/v1  ")
    assert provider_base_url() == "https://example.test/v1"


# ------------------------------------------------------------- fail-safe

@pytest.mark.parametrize("bad", [
    "api.groq.com/openai/v1",   # no scheme
    "ftp://example.test",
    "gopher://x",
    "not a url at all",
    "//protocol-relative",
])
def test_malformed_falls_back_to_stock_openai(monkeypatch, bad, caplog):
    """A malformed value must NOT silently point the app at a bogus host."""
    monkeypatch.setenv("OPENAI_BASE_URL", bad)
    assert provider_base_url() == STOCK_OPENAI_BASE_URL
    assert is_custom_provider() is False
    assert describe_provider() == "openai"


def test_read_fresh_every_call(monkeypatch):
    """No module-level cache — a Railway change takes effect on the next client
    construction, with no redeploy."""
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    assert provider_base_url() == STOCK_OPENAI_BASE_URL
    monkeypatch.setenv("OPENAI_BASE_URL", "https://a.test/v1")
    assert provider_base_url() == "https://a.test/v1"
    monkeypatch.setenv("OPENAI_BASE_URL", "https://b.test/v1")
    assert provider_base_url() == "https://b.test/v1"


def test_never_leaks_credentials_in_label(monkeypatch):
    monkeypatch.setenv("OPENAI_BASE_URL", "https://gw.test/v1")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-secret-value-do-not-log")
    assert "sk-secret" not in describe_provider()


# ------------------------------------------- the factories actually use it

def test_all_client_factories_pass_base_url(monkeypatch):
    """Every AsyncOpenAI construction in the app must honour the setting —
    a factory that forgets it would silently stay on stock OpenAI."""
    import app.services.openai_service as osvc
    import app.services.extraction_service as esvc
    import app.services.url_extraction_service as usvc

    seen = []

    class _Spy:
        def __init__(self, *a, **kw):
            seen.append(kw.get("base_url", "MISSING"))

    monkeypatch.setenv("OPENAI_BASE_URL", "https://spy.test/v1")
    for mod in (osvc, esvc, usvc):
        monkeypatch.setattr(mod, "AsyncOpenAI", _Spy)
    monkeypatch.setattr(osvc, "_client_cache", {}, raising=False)
    monkeypatch.setattr(esvc, "_client", None, raising=False)
    monkeypatch.setattr(usvc, "_client", None, raising=False)

    osvc.get_client(use_shared_project=True)
    monkeypatch.setattr(osvc, "_client_cache", {}, raising=False)
    osvc.get_client(use_shared_project=False)
    esvc.get_client()
    usvc.get_client()

    assert len(seen) == 4, seen
    assert all(v == "https://spy.test/v1" for v in seen), seen


def test_factories_pass_explicit_stock_url_when_unset(monkeypatch):
    """Default path — an EXPLICIT stock url, so a later malformed env value
    can never be re-read by the SDK behind our back."""
    import app.services.extraction_service as esvc
    seen = []

    class _Spy:
        def __init__(self, *a, **kw):
            seen.append(kw.get("base_url", "MISSING"))

    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.setattr(esvc, "AsyncOpenAI", _Spy)
    monkeypatch.setattr(esvc, "_client", None, raising=False)
    esvc.get_client()
    # explicit stock url, NOT None — None would let the SDK re-read the env var
    assert seen == [STOCK_OPENAI_BASE_URL]


# ---------------------------------------------------------------------------
# REGRESSION (2026-08-17): the fail-safe did not actually fail safe.
#
# openai-python resolves base_url itself when it is passed None:
#     if base_url is None: base_url = os.environ.get("OPENAI_BASE_URL")
#     if base_url is None: base_url = "https://api.openai.com/v1"
#
# So returning None for a MALFORMED value handed the SDK the same bad env var,
# and the client was built against it — the exact outcome the guard existed to
# prevent. The guard must therefore return an EXPLICIT stock URL, never None.
# ---------------------------------------------------------------------------

STOCK = "https://api.openai.com/v1"


@pytest.mark.parametrize("bad", ["not-a-url", "ftp://x", "//protocol-relative", "junk value"])
def test_malformed_value_cannot_reach_the_sdk(monkeypatch, bad):
    """The SDK must end up on stock OpenAI, not on the malformed value."""
    from openai import AsyncOpenAI
    monkeypatch.setenv("OPENAI_BASE_URL", bad)
    client = AsyncOpenAI(api_key="test", base_url=provider_base_url())
    assert str(client.base_url).rstrip("/") == STOCK, str(client.base_url)


def test_unset_resolves_to_stock_openai_through_the_sdk(monkeypatch):
    from openai import AsyncOpenAI
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    client = AsyncOpenAI(api_key="test", base_url=provider_base_url())
    assert str(client.base_url).rstrip("/") == STOCK


def test_valid_value_reaches_the_sdk(monkeypatch):
    from openai import AsyncOpenAI
    monkeypatch.setenv("OPENAI_BASE_URL", "https://gateway.test/v1")
    client = AsyncOpenAI(api_key="test", base_url=provider_base_url())
    assert str(client.base_url).rstrip("/") == "https://gateway.test/v1"
