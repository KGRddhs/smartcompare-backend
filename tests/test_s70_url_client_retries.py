"""Session 70 OAI_OBS item 1 (issue #265, audit A-C11).

``app/services/url_extraction_service.get_client`` builds its lazy
``AsyncOpenAI`` without ``max_retries``, so ``OPENAI_MAX_RETRIES`` (set to 1 on
Railway ``web`` since 2026-09-30) does not reach ``/api/v1/url/*`` page
extraction: the SDK default of 2 applies whatever the env says. Every sibling
construction (``extraction_service.get_client``, ``openai_service``) passes
``max_retries=model_config.openai_max_retries()`` at FIRST construction and
caches the client for the life of the process (R1.1 / R1.2).

BASE = 4bd5a09f (OR14; app/ and tests/ are byte-identical to 94c097cd).
RED at BASE: test_url_client_respects_openai_max_retries_env[1|0] (the client
carries 2), test_url_client_passes_explicit_max_retries_kwarg and
test_url_client_explicit_kwarg_follows_env (the kwarg is absent). PIN (green at
BASE): the unset default of 2 and the cache-once semantics. C3: nothing this
unit creates is imported (the module and the resolver exist at base).

Every test builds the module client from scratch (``_client`` reset through
monkeypatch, which restores the process's cached client afterwards). No network:
constructing ``AsyncOpenAI`` opens no connection.
"""
import httpx
import pytest

import app.services.url_extraction_service as usvc

_DUMMY_KEY = "test-dummy-key"


@pytest.fixture(autouse=True)
def _fresh_url_client(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", _DUMMY_KEY)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_MAX_RETRIES", raising=False)
    monkeypatch.setattr(usvc, "_client", None)
    yield


def _spy_constructor(monkeypatch):
    seen = []

    class _SpyAsyncOpenAI:
        def __init__(self, *args, **kwargs):
            seen.append((args, kwargs))

    monkeypatch.setattr(usvc, "AsyncOpenAI", _SpyAsyncOpenAI)
    return seen


def test_url_client_default_max_retries_is_two():
    """PIN: with OPENAI_MAX_RETRIES unset the client retries twice (the SDK
    default == the knob default), before and after the fix."""
    client = usvc.get_client()
    assert client.max_retries == 2


@pytest.mark.parametrize("env_value,expected", [("1", 1), ("0", 0)])
def test_url_client_respects_openai_max_retries_env(monkeypatch, env_value, expected):
    """RED at base (measured 2 for OPENAI_MAX_RETRIES=1): the url client must
    honour the same retry ceiling as every other AsyncOpenAI construction."""
    monkeypatch.setenv("OPENAI_MAX_RETRIES", env_value)
    client = usvc.get_client()
    assert client.max_retries == expected, (
        f"OPENAI_MAX_RETRIES={env_value} but the /url/* client retries "
        f"{client.max_retries} times"
    )


def test_url_client_passes_explicit_max_retries_kwarg(monkeypatch):
    """RED at base (the kwargs are {api_key, base_url, timeout}): the
    construction passes max_retries=openai_max_retries() explicitly (2 with the
    env unset) and leaves the other three kwargs exactly as they were."""
    seen = _spy_constructor(monkeypatch)
    usvc.get_client()
    assert len(seen) == 1, seen
    args, kwargs = seen[0]
    assert args == ()
    assert kwargs.get("max_retries") == 2, sorted(kwargs)
    assert set(kwargs) == {"api_key", "base_url", "timeout", "max_retries"}, sorted(kwargs)
    # R1.1: the other kwargs are byte-identical to base.
    assert kwargs["api_key"] == _DUMMY_KEY
    assert kwargs["timeout"] == httpx.Timeout(120.0, connect=30.0)
    from app.services.llm_provider import provider_base_url
    assert kwargs["base_url"] == provider_base_url()


def test_url_client_explicit_kwarg_follows_env(monkeypatch):
    """RED at base: the explicit kwarg carries the env value (1 here), read
    through model_config's resolver."""
    monkeypatch.setenv("OPENAI_MAX_RETRIES", "1")
    seen = _spy_constructor(monkeypatch)
    usvc.get_client()
    assert len(seen) == 1, seen
    assert seen[0][1].get("max_retries") == 1, sorted(seen[0][1])


def test_url_client_cached_after_first_construction(monkeypatch):
    """PIN (R1.2): the lazy client is built ONCE and cached for the life of the
    process, like extraction_service._client: an env change after the first
    construction reaches neither a new client nor the cached one."""
    first = usvc.get_client()
    first_retries = first.max_retries
    monkeypatch.setenv("OPENAI_MAX_RETRIES", "0" if first_retries != 0 else "1")
    second = usvc.get_client()
    assert second is first
    assert second.max_retries == first_retries


def test_url_client_constructed_once_across_calls(monkeypatch):
    """PIN (R1.2): no per-call re-read -- three calls, one construction."""
    seen = _spy_constructor(monkeypatch)
    a = usvc.get_client()
    b = usvc.get_client()
    c = usvc.get_client()
    assert a is b is c
    assert len(seen) == 1, seen
