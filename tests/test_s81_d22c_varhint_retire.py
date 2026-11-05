"""D22c VARHINT-RETIRE RED rows (spec S81-G7, unit D22c part (2) section 5, as amended by
RULINGS_S81_G7 R-G7-6): price_service._VARHINT_LEARNED_PATH, _varhint_append_learned, its
one call and data/variant_hint_learned.json are deleted (dead code, unflagged, R-A1); the
B3b test suppression (the no_learned_write fixture) goes with it (E1, GREEN's); the Redis
verdict cache stays the only store. The corpus gate OVERALL SHA256 is measured equal at
base and at HEAD (not a pytest row).

Every RED row fails at base on an AssertionError only (the symbols are read with hasattr
and asserted). The PIN row runs with the B3b preconditions set (the exact gate, the axes
and the hint flag ON, the warm context) and a recorder on every LLM call and every open().

Hygiene: pure ASCII, LF; bounded runner only; netguard on; the OpenAI disambiguator and
Redis are in-memory fakes; never a live LLM.
"""
from __future__ import annotations

import app.main  # noqa: F401,I001  (FIRST: the dotenv guard)

import asyncio
import builtins
from pathlib import Path

import pytest

from app.services import cache_service
from app.services import openai_service
from app.services import price_service as ps

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "variant_hint_learned.json"
B3B_TEST = ROOT / "tests" / "test_variant_llm_hint_b3b.py"
PRICE_SERVICE = ROOT / "app" / "services" / "price_service.py"
QUERY = "Obscure Niche House Ambrox"
TITLE = "Obscure Niche House Ambrox Pour Femme Eau de Parfum 100ml"
AXIS = "gender"


@pytest.fixture
def hint_on(monkeypatch):
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "true")
    monkeypatch.setenv("ENABLE_VARIANT_DESCRIPTOR_AXES", "true")
    monkeypatch.setenv("ENABLE_VARIANT_LLM_HINT", "true")
    monkeypatch.setenv("WARMER_CONTEXT", "1")
    monkeypatch.setenv("VARHINT_MAX_CALLS_PER_RUN", "5")
    ps._reset_varhint_run_state()
    yield
    ps._reset_varhint_run_state()


@pytest.fixture
def fake_redis(monkeypatch):
    store = {}

    def _get(key):
        return store.get(key)

    def _set(key, value, ex=None):
        store[key] = value
        return True
    monkeypatch.setattr(cache_service, "_redis_get", _get, raising=True)
    monkeypatch.setattr(cache_service, "_redis_set", _set, raising=True)
    return store


def _llm(monkeypatch, distinct, confidence):
    calls = []

    async def _fake(category, query, candidate_title, axis):
        calls.append((category, query, candidate_title, axis))
        return {"distinct_product": distinct, "confidence": confidence, "cost": 0.0}
    monkeypatch.setattr(openai_service, "disambiguate_variant_line", _fake)
    return calls


def _mode(args, kwargs):
    return str(kwargs.get("mode", args[0] if args else "r"))


def _consult_recording_opens():
    """Run one consult with builtins.open replaced by a recorder. Every open of a data/ path
    is recorded with its mode; a read of the curated reference passes through, while any
    write-mode open under data/ and any open of the learned file are refused (OSError), so
    the committed data files are never written."""
    opened = []
    real_open = builtins.open

    def _rec_open(file, *args, **kwargs):
        text = str(file).replace("\\", "/")
        mode = _mode(args, kwargs)
        if "/data/" in text:
            opened.append((text.rsplit("/", 1)[-1], mode))
            if text.endswith("variant_hint_learned.json") or any(c in mode for c in "wax+"):
                raise OSError("d22c probe: data file write refused")
        return real_open(file, *args, **kwargs)
    builtins.open = _rec_open
    try:
        verdict = asyncio.run(ps._consult_variant_llm_hint("fragrances", QUERY, TITLE, AXIS))
    finally:
        builtins.open = real_open
    return verdict, opened


# ---------------------------------------------------------------------------
# RED rows
# ---------------------------------------------------------------------------

def test_v1_dead_symbols_gone():
    """V1: the learned-file write path no longer exists in price_service."""
    assert not hasattr(ps, "_varhint_append_learned"), "price_service._varhint_append_learned still exists"
    assert not hasattr(ps, "_VARHINT_LEARNED_PATH"), "price_service._VARHINT_LEARNED_PATH still exists"


def test_v2_data_file_gone():
    """V2: data/variant_hint_learned.json is deleted."""
    assert not DATA_FILE.exists(), "data/variant_hint_learned.json still exists"


def test_v3_no_suppression_left():
    """V3: the B3b suite no longer suppresses the write; price_service names no learned file."""
    b3b = B3B_TEST.read_text(encoding="utf-8")
    assert "no_learned_write" not in b3b, "tests/test_variant_llm_hint_b3b.py still carries no_learned_write"
    assert "_varhint_append_learned" not in b3b, "tests/test_variant_llm_hint_b3b.py still names the writer"
    assert "variant_hint_learned" not in PRICE_SERVICE.read_text(encoding="utf-8"), \
        "price_service.py still names variant_hint_learned"


def test_v4_on_path_writes_no_file(hint_on, fake_redis, monkeypatch):
    """V4: the hint flag ON, a high-confidence distinct answer: the verdict is cached in Redis
    and returned; the learned file is never opened and no data/ path is opened for writing."""
    calls = _llm(monkeypatch, True, "high")
    verdict, opened = _consult_recording_opens()
    assert verdict == "distinct", verdict
    assert len(calls) == 1, calls
    assert list(fake_redis.values()) == ["distinct"], fake_redis
    assert [o for o in opened if o[0] == "variant_hint_learned.json"] == [], opened
    assert [o for o in opened if any(c in o[1] for c in "wax+")] == [], opened


# ---------------------------------------------------------------------------
# PIN rows
# ---------------------------------------------------------------------------

def test_p5_consult_behaviour_kept(hint_on, fake_redis, monkeypatch):
    """P5 (PIN): a cache hit returns the cached verdict with no LLM call; the per-run cap
    returns unknown with no call; low confidence -> unknown, nothing cached."""
    key = ps._varhint_verdict_key(QUERY, TITLE, AXIS)
    fake_redis[key] = "same"
    calls = _llm(monkeypatch, True, "high")
    assert asyncio.run(ps._consult_variant_llm_hint("fragrances", QUERY, TITLE, AXIS)) == "same"
    assert calls == [], calls
    fake_redis.clear()
    monkeypatch.setattr(ps, "_varhint_calls_this_run", ps._varhint_max_calls_per_run())
    assert asyncio.run(ps._consult_variant_llm_hint("fragrances", QUERY, TITLE, AXIS)) == "unknown"
    assert calls == [] and fake_redis == {}, (calls, fake_redis)
    ps._reset_varhint_run_state()
    low = _llm(monkeypatch, True, "low")
    assert asyncio.run(ps._consult_variant_llm_hint("fragrances", QUERY, TITLE, AXIS)) == "unknown"
    assert len(low) == 1 and fake_redis == {}, (low, fake_redis)
