"""OpenAI-compatible provider indirection (2026-08-17).

The load-bearing invariant: with OPENAI_BASE_URL unset, every client is
constructed exactly as before, so this is a prod no-op until it is configured.
"""
import importlib
import os

import pytest

from app.services.llm_provider import provider_base_url, describe_provider


# ------------------------------------------------------------ default no-op

def test_unset_is_none(monkeypatch):
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    assert provider_base_url() is None
    assert describe_provider() == "openai"


@pytest.mark.parametrize("blank", ["", "   ", "\t", "\n"])
def test_blank_is_none(monkeypatch, blank):
    monkeypatch.setenv("OPENAI_BASE_URL", blank)
    assert provider_base_url() is None


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
    assert provider_base_url() is None
    assert describe_provider() == "openai"


def test_read_fresh_every_call(monkeypatch):
    """No module-level cache — a Railway change takes effect on the next client
    construction, with no redeploy."""
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    assert provider_base_url() is None
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


def test_factories_pass_none_when_unset(monkeypatch):
    """Default path — base_url=None is exactly what the SDK gets today."""
    import app.services.extraction_service as esvc
    seen = []

    class _Spy:
        def __init__(self, *a, **kw):
            seen.append(kw.get("base_url", "MISSING"))

    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.setattr(esvc, "AsyncOpenAI", _Spy)
    monkeypatch.setattr(esvc, "_client", None, raising=False)
    esvc.get_client()
    assert seen == [None]
