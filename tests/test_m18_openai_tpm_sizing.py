"""#117 (M18 LS-capacity-math-03) — bound the OpenAI 429 retry amplification.

Deferred-OpenAI means nothing here may make a live call: every test mocks the
client. The TPM sizing arithmetic itself is a runbook deliverable
(docs/runbooks/2026-09-02-openai-tpm-launch-sizing.md) — these tests pin the
CODE half: the retry ceiling is explicit, env-configurable, and the verdict
chain's worst-case attempt count is a derivable constant instead of an
implicit SDK default multiplied through a fallback.

Knobs (resolved through model_config — never app/config.py, which requires
seven credentials at import):
  OPENAI_MAX_RETRIES          default 2  == the SDK default (byte-identical)
  OPENAI_FALLBACK_MAX_RETRIES default == OPENAI_MAX_RETRIES (inherit)
"""
from __future__ import annotations

import importlib
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services import model_config


# ---------------------------------------------------------------------------
# Knob resolution (model_config)
# ---------------------------------------------------------------------------


def test_openai_max_retries_default_is_sdk_default_two(monkeypatch):
    monkeypatch.delenv("OPENAI_MAX_RETRIES", raising=False)
    assert model_config.openai_max_retries() == 2


def test_openai_max_retries_env_resolves(monkeypatch):
    monkeypatch.setenv("OPENAI_MAX_RETRIES", "0")
    assert model_config.openai_max_retries() == 0
    monkeypatch.setenv("OPENAI_MAX_RETRIES", "1")
    assert model_config.openai_max_retries() == 1


def test_openai_max_retries_malformed_falls_back(monkeypatch):
    monkeypatch.setenv("OPENAI_MAX_RETRIES", "banana")
    assert model_config.openai_max_retries() == 2
    monkeypatch.setenv("OPENAI_MAX_RETRIES", "-3")
    assert model_config.openai_max_retries() == 0  # clamped, never negative


def test_openai_fallback_retries_inherit_then_override(monkeypatch):
    monkeypatch.delenv("OPENAI_FALLBACK_MAX_RETRIES", raising=False)
    monkeypatch.setenv("OPENAI_MAX_RETRIES", "0")
    assert model_config.openai_fallback_max_retries() == 0  # inherits
    monkeypatch.setenv("OPENAI_FALLBACK_MAX_RETRIES", "1")
    assert model_config.openai_fallback_max_retries() == 1  # explicit override


def test_verdict_chain_max_attempts_is_explicit(monkeypatch):
    """The worst-case upstream attempt count for one verdict is a derivable
    number: (1 + primary retries) + (1 + fallback retries)."""
    monkeypatch.delenv("OPENAI_MAX_RETRIES", raising=False)
    monkeypatch.delenv("OPENAI_FALLBACK_MAX_RETRIES", raising=False)
    # Today's shipped default: 3 primary attempts + 3 fallback attempts = 6.
    assert model_config.verdict_chain_max_attempts() == 6
    # The runbook launch setting: 2 + 1 = 3.
    monkeypatch.setenv("OPENAI_MAX_RETRIES", "1")
    monkeypatch.setenv("OPENAI_FALLBACK_MAX_RETRIES", "0")
    assert model_config.verdict_chain_max_attempts() == 3


# ---------------------------------------------------------------------------
# Client constructions honour the knob
# ---------------------------------------------------------------------------


def _reload_openai_service():
    import app.services.openai_service as osvc

    return importlib.reload(osvc)


@pytest.fixture()
def _restore_openai_service(monkeypatch):
    """Reload openai_service after the test with the env clean so the module
    singleton goes back to the default construction."""
    yield
    import os

    os.environ.pop("OPENAI_MAX_RETRIES", None)
    _reload_openai_service()


def test_module_client_respects_openai_max_retries_env(
    monkeypatch, _restore_openai_service
):
    monkeypatch.setenv("OPENAI_MAX_RETRIES", "0")
    osvc = _reload_openai_service()
    assert osvc.client.max_retries == 0


def test_module_client_default_max_retries_is_two(
    monkeypatch, _restore_openai_service
):
    monkeypatch.delenv("OPENAI_MAX_RETRIES", raising=False)
    osvc = _reload_openai_service()
    assert osvc.client.max_retries == 2


def test_per_project_clients_respect_max_retries(monkeypatch):
    import app.services.openai_service as osvc

    monkeypatch.setenv("OPENAI_MAX_RETRIES", "1")
    saved = dict(osvc._client_cache)
    osvc._client_cache.clear()
    try:
        assert osvc.get_client(True).max_retries == 1
        assert osvc.get_client(False).max_retries == 1
    finally:
        osvc._client_cache.clear()
        osvc._client_cache.update(saved)


def test_extraction_lazy_client_respects_max_retries(monkeypatch):
    from app.services import extraction_service as es

    monkeypatch.setenv("OPENAI_MAX_RETRIES", "0")
    saved = es._client
    es._client = None
    try:
        assert es.get_client().max_retries == 0
    finally:
        es._client = saved


# ---------------------------------------------------------------------------
# The verdict fallback is bounded (no 3x-into-3x storm)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_verdict_fallback_is_retry_bounded(monkeypatch):
    """A 429 on the verdict model falls back ONCE onto the standard model
    through with_options(max_retries=openai_fallback_max_retries()) — the
    fallback must not carry the SDK's own 3 attempts into an
    already-saturated mini TPM budget."""
    monkeypatch.setenv("OPENAI_MAX_RETRIES", "0")
    monkeypatch.setenv("OPENAI_FALLBACK_MAX_RETRIES", "0")
    from app.services import extraction_service as es
    from app.services.model_router_service import model_router

    calls = {"create": 0, "with_options_kwargs": []}

    ok_response = MagicMock()
    ok_response.choices = [MagicMock()]
    ok_response.choices[0].message.content = '{"winner_index": 0}'
    ok_response.usage.prompt_tokens = 10
    ok_response.usage.completion_tokens = 5
    ok_response.usage.total_tokens = 15

    fallback_client = MagicMock()

    async def fb_create(*a, **k):
        calls["create"] += 1
        return ok_response

    fallback_client.chat.completions.create = fb_create

    client = MagicMock()

    async def primary_create(*a, **k):
        calls["create"] += 1
        raise RuntimeError("429 Too Many Requests")

    client.chat.completions.create = primary_create

    def with_options(**kwargs):
        calls["with_options_kwargs"].append(kwargs)
        return fallback_client

    client.with_options = with_options

    monkeypatch.setattr(es, "get_client", lambda: client)
    monkeypatch.setattr(model_router, "get_model", AsyncMock(return_value="gpt-4o"))
    monkeypatch.setattr(model_router, "record_usage", AsyncMock())

    parsed, usage = await es.generate_comparison(
        {"brand": "A", "name": "X"}, {"brand": "B", "name": "Y"}, "bahrain"
    )
    assert parsed.get("winner_index") == 0
    assert "error" not in parsed, f"fallback did not recover: {parsed}"
    # One primary attempt + one fallback attempt — the chain is 2 calls here,
    # and each carries an EXPLICIT max_retries rather than the SDK default.
    assert calls["create"] == 2
    assert calls["with_options_kwargs"] == [{"max_retries": 0}]


def test_runbook_exists_with_modelled_sizing():
    """The doc half of this unit: the TPM sizing arithmetic is written down,
    labelled MODELLED, with the tier verification recorded as a launch gate."""
    from pathlib import Path

    runbook = (
        Path(__file__).resolve().parent.parent
        / "docs"
        / "runbooks"
        / "2026-09-02-openai-tpm-launch-sizing.md"
    )
    assert runbook.exists(), "TPM sizing runbook is missing"
    text = runbook.read_text(encoding="utf-8")
    for needle in (
        "MODELLED",
        "OPENAI_MAX_RETRIES",
        "OPENAI_FALLBACK_MAX_RETRIES",
        "ENABLE_FULL_STREAM_DEADLINE",
        "Tier",
    ):
        assert needle in text, f"runbook is missing required content: {needle}"
