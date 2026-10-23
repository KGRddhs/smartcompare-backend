"""S81-03 LLM-LEDGER-V2 (ENABLE_LLM_LEDGER_V2, lane B) -- RED file.

Spec: .qa-s80/S81-03_UNIT_SPEC.md of the unit worktree, as amended by the
adversarial review (.qa-s80/S81-03_SPEC_REVIEW.md) and the binding rulings
RULINGS_S81_03.md (session-81 state folder; rulings win, then the review, then
the spec):
  R-S03-1 metadata.llm is the SUMMARY only (no per-call records, no
          records_truncated); the admin read selects full_response->metadata->llm;
  R-S03-2 tracked calls are priced from their ledger entry; under ON the builder
          ADDS the list price of every bound OpenAI-ledger entry no tracked call
          claimed to metadata.total_cost;
  R-S03-3 migration 050 REVOKE ALL ... FROM PUBLIC, anon, authenticated,
          service_role; then GRANT SELECT, INSERT to service_role;
  R-S03-4 the Haiku over-100K tier prices cache tokens at the derived 0.1x /
          1.25x / 2x of the tier input rate; Sonnet long context is unpriced;
  R-S03-5 the four ON consumer bodies fall back to the base value with ONE
          WARNING `[LLM-LEDGER] <site> failed type=<TypeName> -- base value`;
          a non-dict usage raises exactly as at base; D7;
  R-S03-6 the share strip is unflagged; FY25 UNIT_ENV carries the flag (E1);
  R-S03-7 build_llm_metadata drops llm-ledger records whose provider is openai;
  R-S03-8 OTEL map comment; BL2 K3 = the test_model_config.py:135 regex;
  BL3 E5b / D5b; BL4 module-attribute access; BL5 H1 = 050 once + the 039 rule.

Every RED row fails at base on an AssertionError only: a missing module or
symbol is read through find_spec / getattr and asserted. Every PIN row is green
at base and runs with the full configuration (B1 rule): the flag set to a falsy
value or deleted, the unit's state primed when the leaf exists (an llm ledger
bound with one record, a tracked claim left behind) and recorders installed on
every function of app.services.llm_pricing (so a not-gated mutant is killed by a
non-zero count). ContextVar hygiene (C8): sync rows run in a copied context and
bind ledgers explicitly; async rows run in their own task context.

Hermetic: fake OpenAI clients, fake Supabase, stubbed egress (the
tests.test_cost_meter_s74 helpers), the conftest netguard. Pure ASCII, LF. No
credential-shaped literal; the K1 hash literal is built by concatenation.
"""
from __future__ import annotations

import ast
import asyncio
import contextvars
import copy
import functools
import hashlib
import importlib
import importlib.util
import inspect
import json
import logging
import math
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api import image_routes
from app.api.auth_routes import get_optional_user
from app.main import app
from app.middleware.rate_limiter import limiter
from app.services import api_budget_service as abs_mod
from app.services import content_safety_service
from app.services import openai_pricing as op
from app.services import openai_service as oai
from app.services import structured_comparison_service as scs_mod
from app.services import usage_service
from app.services.model_router_service import ModelRouterService
from app.services.response_builder import build_comparison_response
from tests._retro_r_mig_sql import MIGRATIONS_DIR, ROLLBACK_DIR, code_only, comment_lines, norm, read
from tests.test_cost_meter_s74 import (
    ADMIN_KEY,
    JPEG,
    SUMMARY,
    _LLM_JSON,
    _Query,
    _Safety,
    _day,
    _done,
    _no_egress,
    _no_supabase,
    _pin_default_models,
    _response,
    _stamp,
    _usage,
    _usage_client,
)
from tests.test_openai_breaker import _FanOutCounters, _all, _arm_prod_search_config, _run_compare, _run_stream
from tests.test_response_builder_phase1_none_guard import _minimal_product_data, _minimal_scoring

REPO = Path(__file__).resolve().parents[1]
APP_DIR = REPO / "app"
LEAF = "app.services.llm_pricing"
LEAF_FILE = APP_DIR / "services" / "llm_pricing.py"
FLAG = "ENABLE_LLM_LEDGER_V2"
OFF_VALUES = (None, "", "false", "0", "off", "no", " FALSE ")
ON_VALUES = ("true", " TRUE ", "1", "yes", "On")
UNIT_ENV = (
    FLAG,
    "ENABLE_VISION_IDENTITY_V2",
    "VISION_TIMEOUT_SECONDS",
    "ENABLE_LLM_PREFLIGHT_BREAKER",
    "ENABLE_PAID_ROUTE_METERING",
    "ENABLE_CAMERA_FAILURE_ENVELOPE",
    "ENABLE_ANON_USAGE_GATE",
    "ENABLE_COMPARE_AUTH_REQUIRED",
    "ENABLE_STRICT_OPTIONAL_AUTH",
    "ENABLE_SYNC_DB_OFFLOAD",
    "ENABLE_SELF_CRITIQUE",
    "ENABLE_RESULT_STATUS_METADATA",
    "DAILY_4O_CAP",
    "OPENAI_MODEL_VERDICT",
    "OPENAI_MODEL_STANDARD",
    "OPENAI_MODEL_VISION",
    "OPENAI_MODEL_CRITIC",
)
WARN_PREFIX = "[LLM-LEDGER]"

# R-S03-1: the summary-only metadata.llm (spec 2.5 minus records / records_truncated).
SUMMARY_KEYS = frozenset({
    "schema_version", "calls", "priced_calls", "unpriced_calls",
    "prompt_tokens", "completion_tokens", "input_tokens", "output_tokens",
    "cache_read_tokens", "cache_write_5m_tokens", "cache_write_1h_tokens",
    "web_search_requests", "cost_usd", "cost_complete", "by_provider", "by_model",
    "basis", "price_table_as_of",
})
RECORD_KEYS = (
    "provider", "model", "role", "input_tokens", "output_tokens", "cache_read_tokens",
    "cache_write_5m_tokens", "cache_write_1h_tokens", "web_search_requests",
    "prompt_tokens", "completion_tokens", "cost_usd", "latency_ms", "stop_reason", "batch",
)
OTEL = {
    "provider": "gen_ai.provider.name",
    "model": "gen_ai.request.model",
    "prompt_tokens": "gen_ai.usage.input_tokens",
    "completion_tokens": "gen_ai.usage.output_tokens",
    "stop_reason": "gen_ai.response.finish_reasons",
}
PRICE_AS_OF = {"openai": "2026-10-08", "anthropic": "2026-10-22"}
SPEND_COLUMNS = (
    "job", "lane", "mode", "provider", "model", "role", "provider_batch_id", "request_count",
    "input_tokens", "output_tokens", "cache_read_tokens", "cache_write_5m_tokens",
    "cache_write_1h_tokens", "web_search_requests", "cost_usd", "cost_complete", "basis",
    "price_table_as_of", "period_start", "period_end",
)

# The RED gate's measured fixture: recorded at base 95cf6f86 by the RED agent
# with the CALL-INDEX distinct-usage client (explicit pair, flag unset). Historical
# since fix round 2 (its per-model sums followed the dispatch order of the
# compare's concurrent legs, RULINGS_FIX2_S81_03); A17 still maps it as a static
# summary.
B5_OPENAI = {
    "basis": "list_price",
    "by_model": {
        "gpt-4o": {"cached_tokens": 0, "calls": 3, "completion_tokens": 690, "cost_usd": 0.015675,
                   "prompt_tokens": 3510},
        "gpt-4o-mini": {"cached_tokens": 0, "calls": 8, "completion_tokens": 1708, "cost_usd": 0.002317,
                        "prompt_tokens": 8612},
    },
    "cached_tokens": 0, "calls": 11, "completion_tokens": 2398, "cost_complete": True,
    "cost_usd": 0.017992, "price_table_as_of": "2026-10-08", "priced_calls": 11,
    "prompt_tokens": 12122, "unpriced_calls": 0,
}
B5_TOTAL_COST = 0.016634
B5_SERPER_CALLS = 8
B5_GPT_CALLS = 9
# F2-1: recorded at base 84c861f6 (the PR's base) with the content-keyed fake
# (_fake_usage_tokens), flag unset: identical on the REST full path and the
# stream complete payload, under every _perturbed pattern, and equal to HEAD
# with the flag OFF (fix round 2).
B5_BASE_OPENAI = {
    "basis": "list_price",
    "by_model": {
        "gpt-4o": {"cached_tokens": 0, "calls": 3, "completion_tokens": 699, "cost_usd": 0.016745,
                   "prompt_tokens": 3902},
        "gpt-4o-mini": {"cached_tokens": 0, "calls": 8, "completion_tokens": 1688, "cost_usd": 0.002819,
                        "prompt_tokens": 12043},
    },
    "cached_tokens": 0, "calls": 11, "completion_tokens": 2387, "cost_complete": True,
    "cost_usd": 0.019564, "price_table_as_of": "2026-10-08", "priced_calls": 11,
    "prompt_tokens": 15945, "unpriced_calls": 0,
}
B5_BASE_TOTAL_COST = 0.017175

# K1 / K2 (spec 1.8): split so the added-line sweep's 8-digit rule cannot misfire.
K1_GUARDED_AST_SHA = "8fa87b616" + "45971d65a41d38cf70938f38d441d0b0a0d91a055b16d74b1b3a63d"
K2_OPENAI_PRICING_LF_SHA = "0406b617bd91b2a1ea5a5bac" + "d37fd48e28e106ed99991bfec9087d144ec14094"

# The base literal of OPENAI_COST_NOTE (admin_routes.py:133-139 at 95cf6f86).
OPENAI_COST_NOTE_BASE = (
    "List price over persisted comparisons only; excludes Link-mode compares "
    "(never persisted today, issue #340), failed compares and calls cancelled "
    "by the hard cap or retried by the SDK. OpenAI applies its free daily "
    "allowance on its side (organisation data sharing ON since 2026-10-08, "
    "decision D3 = C), so this figure is not a bill."
)
# tests/test_model_config.py:135 (BL2).
STRAY_MODEL_RX = re.compile(r'["\'](gpt-[0-9a-zA-Z.\-]+|omni-moderation-[a-z]+)["\']')


class _LeafBoom(RuntimeError):
    """The fault-injection exception (R-S03-5); its message must never be logged."""


BOOM_TEXT = "s03-boom-detail-never-logged"


# ---------------------------------------------------------------------------
# environment, leaf access, recorders
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _unit_env(monkeypatch):
    for name in UNIT_ENV:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(limiter, "enabled", False)
    yield


def _set_flag(monkeypatch, value):
    if value is None:
        monkeypatch.delenv(FLAG, raising=False)
    else:
        monkeypatch.setenv(FLAG, value)


def _leaf():
    if importlib.util.find_spec(LEAF) is None:
        return None
    return importlib.import_module(LEAF)


def _need_leaf():
    mod = _leaf()
    assert mod is not None, "app/services/llm_pricing.py is missing (S81-03 change 1)"
    return mod


def _need(name):
    mod = _need_leaf()
    value = getattr(mod, name, None)
    assert value is not None, f"llm_pricing.{name} is missing"
    return value


def _counting(calls, name, fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        calls[name] += 1
        return fn(*args, **kwargs)
    return wrapper


def _leaf_recorders(monkeypatch):
    """Wrap every function DEFINED in llm_pricing except the flag reader with a
    counter (module attribute, BL4: every consumer reaches the leaf through the
    module, so the wrapper sees every call). {} at base (no module)."""
    mod = _leaf()
    calls = {}
    if mod is None:
        return calls
    for name, fn in list(vars(mod).items()):
        if name == "llm_ledger_v2_enabled" or not inspect.isfunction(fn):
            continue
        if getattr(fn, "__module__", None) != mod.__name__:
            continue
        calls[name] = 0
        monkeypatch.setattr(mod, name, _counting(calls, name, fn))
    return calls


def _called(calls):
    return {k: v for k, v in calls.items() if v}


def _ledger_warnings(caplog):
    return [r for r in caplog.records if r.getMessage().startswith(WARN_PREFIX)]


def _assert_one_fallback_warning(caplog, where):
    found = _ledger_warnings(caplog)
    assert len(found) == 1, (
        f"{where}: exactly ONE '{WARN_PREFIX} <site> failed type=... -- base value' WARNING "
        f"expected (R-S03-5), got {[r.getMessage() for r in found]}"
    )
    rec = found[0]
    msg = rec.getMessage()
    assert rec.levelno == logging.WARNING, f"{where}: level {rec.levelname}"
    assert "failed type=_LeafBoom" in msg and "base value" in msg, f"{where}: {msg!r}"
    for r in caplog.records:
        assert BOOM_TEXT not in r.getMessage(), f"{where}: the exception text was logged: {r.getMessage()!r}"


def _boom(*_a, **_k):
    raise _LeafBoom(BOOM_TEXT)


def _isolated(fn, *args):
    """C8: run a sync row in a COPY of the current context (ledger binds and
    claims never leak to later tests)."""
    return contextvars.copy_context().run(fn, *args)


def _resp(prompt, completion, cached=0, model="gpt-4o-mini"):
    return _response(model, "{}", _usage(prompt, completion, cached))


def _bind_entries(entries):
    """Bind a FRESH OpenAI ledger in the current context holding one recorded
    entry per (model, prompt, completion[, cached]) tuple."""
    ledger = op.start_openai_ledger()
    for e in entries:
        model, prompt, completion = e[0], e[1], e[2]
        cached = e[3] if len(e) > 3 else 0
        op.record_openai_response(model, _resp(prompt, completion, cached, model))
    return ledger


def _base_estimate(p, c):
    return (p * 0.15 / 1_000_000) + (c * 0.60 / 1_000_000)


def _haiku_record(**usage):
    rec = _need("anthropic_usage_record")
    return rec("claude-haiku-5-5", dict(usage))


def _prime_leaf_state(monkeypatch, final_flag):
    """B1 rule: with the leaf present, leave the unit's request state primed in
    the CURRENT context (an llm ledger bound with one Haiku record, a claim left
    behind by one ON tracked call), then set the flag to ``final_flag``."""
    mod = _leaf()
    if mod is not None:
        start = getattr(mod, "start_llm_ledger", None)
        record = getattr(mod, "record_llm_call", None)
        arec = getattr(mod, "anthropic_usage_record", None)
        if callable(start):
            start()
        if callable(record) and callable(arec):
            record(arec("claude-haiku-5-5", {"input_tokens": 10, "output_tokens": 2}))
        monkeypatch.setenv(FLAG, "true")
        _bind_entries([("gpt-4o", 1000, 200)])
        scs_mod.get_comparison_service()._track_gpt_cost({"prompt_tokens": 1000, "completion_tokens": 200})
    _set_flag(monkeypatch, final_flag)


# F2-1 (RULINGS_FIX2_S81_03): the distinct-usage fake keys every usage by the
# requested MODEL and a CONTENT signature of the request, never by call index.
# Until fix round 2 it answered call n with prompt 1000 + 17n / completion
# 200 + 3n, so the per-model sums B5 / I6 pinned followed the asyncio dispatch
# order of the compare's concurrent legs (PR #369 went red on the GitHub
# runner at 21b37039: gpt-4o completion 684 instead of 690).
FAKE_COMPLETION_TOKENS = {"gpt-4o-mini": 211, "gpt-4o": 233}
FAKE_COMPLETION_TOKENS_OTHER = 197
FAKE_PRODUCT_MARKERS = ("Acme", "Globex")
# Test-only knob (never set in CI): a _perturbed pattern ("skew_a", "skew_b",
# "hash<seed>") that holds every dispatch of every distinct-usage client, so a
# whole-file run proves the rows order-independent (F2-2).
FAKE_PERTURB_ENV = "S03_FAKE_DISPATCH_PERTURB"


def _fake_usage_signature(model, messages):
    """The content one usage is keyed on: the requested model, the first
    sentence of the system message and which compare products the request
    names. The whole message text is not order-stable: the verdict prompt
    serialises each product dict's keys in the order that product's races
    finished (measured under a perturbed dispatch order in fix round 2)."""
    msgs = [m for m in (messages or []) if isinstance(m, dict)]
    system = next((m.get("content") for m in msgs
                   if m.get("role") == "system" and isinstance(m.get("content"), str)), "")
    first_sentence = re.split(r"[.\n]", system, maxsplit=1)[0]
    blob = "\n".join(str(m.get("content")) for m in msgs)
    named = ",".join(marker for marker in FAKE_PRODUCT_MARKERS if marker in blob)
    return f"{model}|{first_sentence}|{named}"


def _fake_usage_tokens(model, messages):
    """(prompt, completion) of one request: prompt = 1000 + a sha256 of the
    signature mod 997 (11 distinct values over the 11 calls of a compare,
    measured), completion = a per-model constant; no call index, no clock."""
    digest = hashlib.sha256(_fake_usage_signature(model, messages).encode("utf-8")).hexdigest()
    prompt = 1000 + int(digest[:12], 16) % 997
    return prompt, FAKE_COMPLETION_TOKENS.get(model, FAKE_COMPLETION_TOKENS_OTHER)


def _distinct_client():
    """Every chat completion carries a usage keyed by the requested model and
    the request's content (_fake_usage_tokens; the same request always gets the
    same counts, distinct requests get distinct counts) and echoes the requested
    model. FAKE_PERTURB_ENV, when set, holds every dispatch (_perturbed)."""
    client = MagicMock()

    async def _create(**kwargs):
        prompt, completion = _fake_usage_tokens(kwargs.get("model"), kwargs.get("messages"))
        usage = SimpleNamespace(prompt_tokens=prompt, completion_tokens=completion,
                                total_tokens=prompt + completion,
                                prompt_tokens_details=SimpleNamespace(cached_tokens=0))
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=_LLM_JSON), finish_reason="stop")],
            usage=usage, model=kwargs.get("model"))

    client.chat.completions.create = AsyncMock(side_effect=_create)
    flagged = MagicMock()
    flagged.flagged = False
    moderation = MagicMock()
    moderation.results = [flagged]
    client.moderations.create = AsyncMock(return_value=moderation)
    return _perturbed(client, os.environ.get(FAKE_PERTURB_ENV, "").strip())


def _e2e_spies(monkeypatch, sink):
    """Record every tracked delta, the Serper and Tier-1.5 cost adds, and the
    bound OpenAI ledger at build time (the scs-namespace builder binding)."""
    cls = scs_mod.StructuredComparisonService
    real_s, real_a, real_g = cls._track_serper_cost, cls._track_cost_amount, cls._track_gpt_cost
    sink.update({"serper": 0, "amounts": [], "tracked": [], "ledgers": []})

    def s(self):
        sink["serper"] += 1
        return real_s(self)

    def a(self, amount):
        sink["amounts"].append(amount)
        return real_a(self, amount)

    def g(self, usage):
        before = self.total_cost
        out = real_g(self, usage)
        sink["tracked"].append((dict(usage), self.total_cost - before))
        return out

    monkeypatch.setattr(cls, "_track_serper_cost", s)
    monkeypatch.setattr(cls, "_track_cost_amount", a)
    monkeypatch.setattr(cls, "_track_gpt_cost", g)
    real_b = scs_mod.build_comparison_response

    def b(*args, **kwargs):
        sink["ledgers"].append([dict(e) for e in (op._LEDGER.get() or [])])
        return real_b(*args, **kwargs)

    monkeypatch.setattr(scs_mod, "build_comparison_response", b)


async def _rest(monkeypatch, client=None):
    _pin_default_models(monkeypatch)
    _arm_prod_search_config(monkeypatch)
    fan = _FanOutCounters()
    client = client or _distinct_client()
    with _all(*fan.patches(client), *_no_supabase(), *_no_egress()):
        result = await _run_compare()
    assert isinstance(result, dict) and result.get("success") is True and "metadata" in result, (
        f"harness: the REST compare did not build: {str(result)[:200]}"
    )
    return result, client


async def _stream(monkeypatch, client=None):
    _pin_default_models(monkeypatch)
    _arm_prod_search_config(monkeypatch)
    fan = _FanOutCounters()
    client = client or _distinct_client()
    with _all(*fan.patches(client), *_no_supabase(), *_no_egress()):
        events = await _run_stream()
    complete = [d for e, d in events if e == "complete"]
    assert complete, f"harness: no complete event: {[e for e, _ in events]}"
    return complete[-1], client


def _builder(**overrides):
    kw = dict(
        query="B0 P0 vs B1 P1", product_data=_minimal_product_data(),
        scoring_result=_minimal_scoring(), comparison=None, region="bahrain",
        api_calls=4, elapsed_seconds=1.5, total_cost=0.001, gpt_calls=2,
    )
    kw.update(overrides)
    return build_comparison_response(**kw)


# ===========================================================================
# A -- the leaf (llm_pricing)
# ===========================================================================
def test_a1_leaf_exists_and_imports_only_stdlib_and_openai_pricing():
    """RED (A1): the leaf exists; every import is stdlib or
    app.services.openai_pricing; the only `_LEDGER` read in app/ outside
    openai_pricing.py is in llm_pricing.current_openai_ledger."""
    assert importlib.util.find_spec(LEAF) is not None, "app/services/llm_pricing.py is missing"
    tree = ast.parse(LEAF_FILE.read_text(encoding="utf-8"))
    stdlib = set(sys.stdlib_module_names) | {"__future__"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                assert top in stdlib or alias.name == "app.services.openai_pricing", alias.name
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if mod == "app.services":
                assert [a.name for a in node.names] == ["openai_pricing"], ast.dump(node)
            else:
                assert mod.split(".")[0] in stdlib or mod == "app.services.openai_pricing", mod
                assert not any(a.name == "_LEDGER" for a in node.names), "never import the private ContextVar"
    readers = []
    for path in sorted(APP_DIR.rglob("*.py")):
        if path.name == "openai_pricing.py":
            continue
        src = path.read_text(encoding="utf-8")
        if "_LEDGER" not in src:
            continue
        t = ast.parse(src)
        total = sum(1 for n in ast.walk(t) if isinstance(n, ast.Attribute) and n.attr == "_LEDGER")
        inside = 0
        for fn in ast.walk(t):
            if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)) and fn.name == "current_openai_ledger":
                inside += sum(1 for n in ast.walk(fn) if isinstance(n, ast.Attribute) and n.attr == "_LEDGER")
        if total:
            readers.append((path.name, total, inside))
    assert len(readers) == 1 and readers[0][0] == "llm_pricing.py" and readers[0][1] == readers[0][2] >= 1, (
        f"the one sanctioned `_LEDGER` read is llm_pricing.current_openai_ledger: {readers}"
    )


@pytest.mark.parametrize("value,expected", [(v, False) for v in OFF_VALUES + ("garbage",)]
                         + [(v, True) for v in ON_VALUES])
def test_a2_flag_reader_idiom(monkeypatch, value, expected):
    """RED (A2): the house idiom os.getenv(FLAG, "false").strip().lower() in
    (true, 1, yes, on), read per call."""
    reader = _need("llm_ledger_v2_enabled")
    _set_flag(monkeypatch, value)
    assert reader() is expected, (value, reader())


def test_a2b_flag_read_per_call(monkeypatch):
    """RED (A2): toggled twice in one test, the reader follows each change."""
    reader = _need("llm_ledger_v2_enabled")
    for value, expected in (("true", True), ("false", False), ("on", True), (None, False)):
        _set_flag(monkeypatch, value)
        assert reader() is expected, value


def test_a3_anthropic_rows_exact_keys_rates_and_as_of():
    """RED (A3): the two EXACT rows, the ten rates, the 1.25x / 2x write
    multipliers, ANTHROPIC_PRICE_TABLE_AS_OF and the provider dict."""
    rows = _need("ANTHROPIC_PRICE_USD_PER_1M")
    assert set(rows) == {"claude-haiku-5-5", "claude-sonnet-5-5"}, sorted(rows)
    assert rows["claude-haiku-5-5"] == {"input": 0.10, "output": 0.50, "cache_read": 0.01,
                                        "cache_write_5m": 0.125, "cache_write_1h": 0.20}
    assert rows["claude-sonnet-5-5"] == {"input": 2.00, "output": 10.00, "cache_read": 0.10,
                                         "cache_write_5m": 2.50, "cache_write_1h": 4.00}
    for row in rows.values():
        assert row["cache_write_5m"] == pytest.approx(1.25 * row["input"])
        assert row["cache_write_1h"] == pytest.approx(2.0 * row["input"])
    assert _need("ANTHROPIC_PRICE_TABLE_AS_OF") == "2026-10-22"
    assert _need("PRICE_TABLE_AS_OF") == PRICE_AS_OF
    assert _need("BASIS") == "list_price"
    assert _need("WEB_SEARCH_USD_PER_REQUEST") == 0.01
    assert _need("BATCH_TOKEN_MULTIPLIER") == 0.5


def test_a4_openai_rows_reexported_same_object_and_legacy_rates():
    """RED (A4): the OpenAI rows are THE openai_pricing object; the legacy track
    rates equal the gpt-4o-mini input / output rates (0.15 / 0.60)."""
    assert _need("OPENAI_PRICE_USD_PER_1M") is op.PRICE_USD_PER_1M
    assert _need("OPENAI_PRICE_TABLE_AS_OF") == op.PRICE_TABLE_AS_OF
    legacy = _need("LEGACY_TRACK_RATES_USD_PER_1M")
    mini = op.PRICE_USD_PER_1M["gpt-4o-mini"]
    assert tuple(legacy) == (0.15, 0.60) == (mini["input"], mini["output"])


def _price(provider, model, **kw):
    return _need("price_call")(provider, model, **kw)


def test_a5_haiku_price_with_every_cache_field():
    """RED (A5): (1000*0.10 + 200*0.50 + 5000*0.01 + 2000*0.125 + 1000*0.20)/1e6 = 0.0007."""
    got = _price("anthropic", "claude-haiku-5-5", input_tokens=1000, output_tokens=200,
                 cache_read_tokens=5000, cache_write_5m_tokens=2000, cache_write_1h_tokens=1000)
    assert got == pytest.approx(0.0007, abs=1e-12)


def test_a6_sonnet_price_and_cache_read_is_010():
    """RED (A6): (1000*2 + 200*10 + 5000*0.10)/1e6 = 0.0045 (cache read 0.10, the critic correction)."""
    got = _price("anthropic", "claude-sonnet-5-5", input_tokens=1000, output_tokens=200,
                 cache_read_tokens=5000)
    assert got == pytest.approx(0.0045, abs=1e-12)


def test_a7_web_search_is_001_each():
    """RED (A7): $0.01 per server web search request."""
    assert _price("anthropic", "claude-haiku-5-5", web_search_requests=3) == pytest.approx(0.03, abs=1e-12)
    assert _price("anthropic", "claude-sonnet-5-5", web_search_requests=1) == pytest.approx(0.01, abs=1e-12)


def test_a8_batch_halves_tokens_not_search():
    """RED (A8): Batch 50 % on tokens only: (100 + 100)/1e6 * 0.5 = 0.0001; + 1 search = 0.0101."""
    assert _price("anthropic", "claude-haiku-5-5", input_tokens=1000, output_tokens=200,
                  batch=True) == pytest.approx(0.0001, abs=1e-12)
    assert _price("anthropic", "claude-haiku-5-5", input_tokens=1000, output_tokens=200,
                  web_search_requests=1, batch=True) == pytest.approx(0.0101, abs=1e-12)


def test_a9_haiku_long_context_tier_with_derived_cache_rates():
    """RED (A9 as amended by R-S03-4): above 100K prompt tokens (strictly; the
    count includes cache reads and writes) the WHOLE Haiku request is priced at
    0.50 / 2.50 with cache read 0.05, 5m write 0.625, 1h write 1.00 (the derived
    0.1x / 1.25x / 2x of the tier input); Sonnet long context is unpriced."""
    h = "claude-haiku-5-5"
    assert _price("anthropic", h, input_tokens=150000, output_tokens=1000) == pytest.approx(0.0775, abs=1e-12)
    assert _price("anthropic", h, input_tokens=100000, output_tokens=1000) == pytest.approx(0.0105, abs=1e-12)
    assert _price("anthropic", h, input_tokens=100001, output_tokens=1000) == pytest.approx(0.0525005, abs=1e-12)
    # 60000*0.50 + 50000*0.05 + 1000*2.50 = 35000 -> 0.035 (R-S03-4; the spec's None is withdrawn)
    assert _price("anthropic", h, input_tokens=60000, cache_read_tokens=50000,
                  output_tokens=1000) == pytest.approx(0.035, abs=1e-12)
    # 50000*0.50 + 40000*0.625 + 20000*1.00 = 70000 -> 0.07
    assert _price("anthropic", h, input_tokens=50000, cache_write_5m_tokens=40000,
                  cache_write_1h_tokens=20000) == pytest.approx(0.07, abs=1e-12)
    # the threshold counts cache reads: 50000 + 50001 = 100001 > 100K -> 0.02750005
    assert _price("anthropic", h, input_tokens=50000, cache_read_tokens=50001) == pytest.approx(0.02750005, abs=1e-12)
    s = "claude-sonnet-5-5"
    assert _price("anthropic", s, input_tokens=100000, output_tokens=1000) == pytest.approx(0.21, abs=1e-12)
    assert _price("anthropic", s, input_tokens=250000, output_tokens=1000) is None, (
        "R-S03-4: no Sonnet long-context tier is modelled; such a request is unpriced"
    )
    src = LEAF_FILE.read_text(encoding="utf-8")
    assert "derived" in src and "R1" in src and "2026-10-22" in src, (
        "R-S03-4: the derived tier constants carry the R1 citation, the read date and the word derived"
    )


@pytest.mark.parametrize("args,kwargs", [
    (("anthropic", "claude-haiku-5-5-20261001"), {"input_tokens": 10}),
    (("anthropic", "claude-opus-5-5"), {"input_tokens": 10}),
    (("anthropic", ""), {"input_tokens": 10}),
    (("anthropic", None), {"input_tokens": 10}),
    (("anthropic", 123), {"input_tokens": 10}),
    (("mistral", "claude-haiku-5-5"), {"input_tokens": 10}),
    (("anthropic", "claude-haiku-5-5"), {"input_tokens": True}),
    (("anthropic", "claude-haiku-5-5"), {"input_tokens": 1.5}),
    (("anthropic", "claude-haiku-5-5"), {"output_tokens": -1}),
    (("anthropic", "claude-haiku-5-5"), {"output_tokens": None}),
    (("anthropic", "claude-haiku-5-5"), {"web_search_requests": True}),
    (("openai", "gpt-5"), {"input_tokens": 10}),
])
def test_a10_unknown_ids_and_bad_counts_price_to_none(args, kwargs):
    """RED (A10): an id outside the EXACT rows, an unknown provider or a count
    that is not a non-negative non-bool int prices to None, never 0."""
    assert _price(*args, **kwargs) is None


A11_TUPLES = ((800, 200, 100), (999, 1, 1001), (1001, 333, 77), (12345, 678, 910), (1187, 0, 233))


def test_a11_openai_price_delegates_bit_identically():
    """RED (A11, kills M13 as redefined by C7): price_call('openai', ...) ==
    openai_pricing.list_price_usd (==, not approx) on five tuples, at least one of
    which differs in the last bit under the term-wise order u*in/1e6 +
    c*cin/1e6 + o*out/1e6; None with a cache write, a web search or batch."""
    for model in ("gpt-4o", "gpt-4o-mini"):
        for u, c, o in A11_TUPLES:
            got = _price("openai", model, input_tokens=u, cache_read_tokens=c, output_tokens=o)
            want = op.list_price_usd(model, u + c, o, c)
            assert got == want, (model, (u, c, o), got, want)
    assert _price("openai", "gpt-4o", input_tokens=10, cache_write_5m_tokens=1) is None
    assert _price("openai", "gpt-4o", input_tokens=10, cache_write_1h_tokens=1) is None
    assert _price("openai", "gpt-4o", input_tokens=10, web_search_requests=1) is None
    assert _price("openai", "gpt-4o", input_tokens=10, batch=True) is None


@pytest.mark.parametrize("model,expected", [
    ("claude-haiku-5-5", "anthropic"), ("claude-sonnet-5-5", "anthropic"),
    ("gpt-4o", "openai"), ("gpt-4o-mini", "openai"), ("gpt-5", "openai"),
    ("omni-moderation-latest", "openai"),
    ("o3", None), ("", None), (None, None), (7, None),
])
def test_a12_provider_of(model, expected):
    """RED (A12)."""
    assert _need("provider_of")(model) == expected


def test_a13_record_keys_and_otel_map():
    """RED (A13 + R-S03-8): the 15 record keys in order; the 5 OpenTelemetry
    GenAI names; the map carries the 'unverified' comment naming S81-22."""
    assert tuple(_need("LLM_RECORD_KEYS")) == RECORD_KEYS
    assert dict(_need("OTEL_GENAI_ATTRIBUTES")) == OTEL
    src = LEAF_FILE.read_text(encoding="utf-8").lower()
    assert "unverified against the opentelemetry genai semantic conventions" in src
    assert "s81-22" in src


def _a14_usage(form, breakdown=(1000, 500), creation=1500):
    data = {
        "input_tokens": 300, "output_tokens": 50, "cache_read_input_tokens": 4000,
        "cache_creation_input_tokens": creation,
        "server_tool_use": {"web_search_requests": 2},
    }
    if breakdown is not None:
        data["cache_creation"] = {"ephemeral_5m_input_tokens": breakdown[0],
                                  "ephemeral_1h_input_tokens": breakdown[1]}
    if form == "dict":
        return data
    obj = SimpleNamespace(**{k: v for k, v in data.items() if k not in ("server_tool_use", "cache_creation")})
    obj.server_tool_use = SimpleNamespace(**data["server_tool_use"])
    if breakdown is not None:
        obj.cache_creation = SimpleNamespace(**data["cache_creation"])
    return obj


@pytest.mark.parametrize("form", ["dict", "object"])
@pytest.mark.parametrize("case,breakdown,cw5m,cw1h", [
    ("breakdown", (1000, 500), 1000, 500),
    ("no_breakdown", None, 1500, 0),
    ("short_breakdown", (800, 500), 1000, 500),  # C12: the 200 remainder counts as 5-minute writes
])
def test_a14_anthropic_usage_normalisation(form, case, breakdown, cw5m, cw1h):
    """RED (A14 + C12): prompt_tokens = input + cache_read + cache writes;
    completion = output; cost == price_call over the same tokens; a breakdown
    summing below cache_creation_input_tokens counts the remainder as 5m."""
    record = _need("anthropic_usage_record")("claude-haiku-5-5", _a14_usage(form, breakdown))
    assert tuple(record) == RECORD_KEYS, tuple(record)
    assert record["provider"] == "anthropic" and record["model"] == "claude-haiku-5-5"
    assert record["input_tokens"] == 300 and record["output_tokens"] == 50
    assert record["cache_read_tokens"] == 4000
    assert (record["cache_write_5m_tokens"], record["cache_write_1h_tokens"]) == (cw5m, cw1h), case
    assert record["web_search_requests"] == 2
    assert record["prompt_tokens"] == 300 + 4000 + cw5m + cw1h == 5800
    assert record["completion_tokens"] == 50
    want = _price("anthropic", "claude-haiku-5-5", input_tokens=300, output_tokens=50,
                  cache_read_tokens=4000, cache_write_5m_tokens=cw5m, cache_write_1h_tokens=cw1h,
                  web_search_requests=2)
    assert record["cost_usd"] == want
    assert record["batch"] is False and record["role"] is None


@pytest.mark.parametrize("garbage", [None, {"input_tokens": "lots", "output_tokens": 5}])
def test_a14b_unreadable_anthropic_usage_is_unpriced(garbage):
    """RED (A14): an unreadable usage gives every token None and cost None, never raises."""
    record = _need("anthropic_usage_record")("claude-haiku-5-5", garbage)
    assert tuple(record) == RECORD_KEYS
    for key in ("input_tokens", "output_tokens", "cache_read_tokens", "cache_write_5m_tokens",
                "cache_write_1h_tokens", "prompt_tokens", "completion_tokens", "cost_usd"):
        assert record[key] is None, (key, record[key])


def test_a15_openai_entry_record():
    """RED (A15): a recorded gpt-4o entry 1000 / 200 / cached 300 -> input 700,
    cache_read 300, prompt 1000, output 200, cost == the entry's cost_usd (==);
    the unpriced entry shape -> None tokens and cost."""
    to_record = _need("openai_entry_record")

    def body():
        ledger = _bind_entries([("gpt-4o", 1000, 200, 300)])
        rec = to_record(ledger[0])
        assert tuple(rec) == RECORD_KEYS
        assert rec["provider"] == "openai" and rec["model"] == "gpt-4o"
        assert (rec["input_tokens"], rec["cache_read_tokens"], rec["prompt_tokens"]) == (700, 300, 1000)
        assert (rec["output_tokens"], rec["completion_tokens"]) == (200, 200)
        assert (rec["cache_write_5m_tokens"], rec["cache_write_1h_tokens"], rec["web_search_requests"]) == (0, 0, 0)
        assert rec["cost_usd"] == ledger[0]["cost_usd"]
        assert rec["role"] is None and rec["latency_ms"] is None and rec["stop_reason"] is None
        assert rec["batch"] is False
        unpriced = to_record({"model": "gpt-4o", "prompt_tokens": None, "completion_tokens": None,
                              "cached_tokens": None, "cost_usd": None})
        assert unpriced["prompt_tokens"] is None and unpriced["input_tokens"] is None
        assert unpriced["cost_usd"] is None

    _isolated(body)


def _records_for_a16():
    arec = _need("anthropic_usage_record")
    priced = arec("claude-haiku-5-5", {"input_tokens": 1000, "output_tokens": 200})
    unpriced = arec("claude-opus-5-5", {"input_tokens": 300, "output_tokens": 30})
    return priced, unpriced


def test_a16_summary_cost_semantics_summary_only():
    """RED (A16 as amended by R-S03-1): the summary carries exactly the summary
    keys (no records, no records_truncated); zero records -> cost 0.0 complete
    True; all unpriced -> None False; mixed -> round(sum priced, 6) False; token
    sums skip None; by_provider / by_model per key."""
    summarize = _need("summarize_llm_records")
    priced, unpriced = _records_for_a16()
    empty = summarize([])
    assert set(empty) == SUMMARY_KEYS, sorted(set(empty) ^ SUMMARY_KEYS)
    assert (empty["calls"], empty["cost_usd"], empty["cost_complete"]) == (0, 0.0, True)
    assert empty["by_provider"] == {} and empty["by_model"] == {}
    assert empty["schema_version"] == 1 and empty["basis"] == "list_price"
    assert empty["price_table_as_of"] == PRICE_AS_OF
    none = summarize([unpriced, dict(unpriced)])
    assert (none["calls"], none["priced_calls"], none["unpriced_calls"]) == (2, 0, 2)
    assert none["cost_usd"] is None and none["cost_complete"] is False
    holey = dict(priced, prompt_tokens=None, cost_usd=None)
    mixed = summarize([priced, unpriced, holey])
    assert mixed["cost_usd"] == round(priced["cost_usd"], 6) == 0.0002
    assert mixed["cost_complete"] is False
    assert mixed["prompt_tokens"] == 1000 + 300
    assert mixed["completion_tokens"] == 200 + 30 + 200
    assert mixed["by_provider"] == {"anthropic": {"calls": 3, "cost_usd": 0.0002}}
    assert mixed["by_model"]["claude-opus-5-5"]["cost_usd"] is None
    assert mixed["by_model"]["claude-haiku-5-5"]["calls"] == 2
    assert mixed["by_model"]["claude-haiku-5-5"]["provider"] == "anthropic"
    assert "records" not in mixed and "records_truncated" not in mixed


def test_a17_summary_is_bounded_by_distinct_models_not_calls():
    """RED (R-S03-1 replaces the records cap): 70 records summarise to the same
    small object (no per-call detail); llm_summary_from_openai maps a
    metadata.openai summary 1:1 into the summary shape."""
    summarize = _need("summarize_llm_records")
    priced, _ = _records_for_a16()
    big = summarize([dict(priced) for _ in range(70)])
    assert set(big) == SUMMARY_KEYS
    assert big["calls"] == 70 and big["cost_usd"] == round(70 * priced["cost_usd"], 6)
    assert len(json.dumps(big)) < 2048, len(json.dumps(big))
    mapped = _need("llm_summary_from_openai")(copy.deepcopy(B5_OPENAI))
    assert set(mapped) == SUMMARY_KEYS
    for key in ("calls", "priced_calls", "unpriced_calls", "prompt_tokens", "completion_tokens",
                "cost_usd", "cost_complete"):
        assert mapped[key] == B5_OPENAI[key], key
    assert mapped["cache_read_tokens"] == B5_OPENAI["cached_tokens"]
    assert mapped["by_provider"] == {"openai": {"calls": 11, "cost_usd": 0.017992}}
    for model, row in B5_OPENAI["by_model"].items():
        assert mapped["by_model"][model]["calls"] == row["calls"]
        assert mapped["by_model"][model]["cost_usd"] == row["cost_usd"]
        assert mapped["by_model"][model]["provider"] == "openai"
    assert _need("llm_summary_from_openai")(None) is None


def test_a18_merge_llm_summaries():
    """RED (A18): None-aware; counts and token sums add; cost None only when
    both None; complete AND; per-key by_provider / by_model; summary keys only."""
    summarize = _need("summarize_llm_records")
    merge = _need("merge_llm_summaries")
    priced, unpriced = _records_for_a16()
    a = summarize([priced])
    b = summarize([unpriced])
    assert merge(None, a) == a and merge(a, None) == a and merge(None, None) is None
    m = merge(a, b)
    assert set(m) == SUMMARY_KEYS
    assert m["calls"] == 2 and m["priced_calls"] == 1 and m["unpriced_calls"] == 1
    assert m["cost_usd"] == a["cost_usd"] and m["cost_complete"] is False
    assert m["prompt_tokens"] == a["prompt_tokens"] + b["prompt_tokens"]
    assert m["by_provider"]["anthropic"]["calls"] == 2
    assert set(m["by_model"]) == {"claude-haiku-5-5", "claude-opus-5-5"}
    both_none = merge(b, summarize([unpriced]))
    assert both_none["cost_usd"] is None
    aa = merge(a, summarize([priced]))
    assert aa["cost_usd"] == round(2 * priced["cost_usd"], 6) and aa["cost_complete"] is True
    assert aa["by_model"]["claude-haiku-5-5"]["calls"] == 2


def test_a19_record_llm_call_no_op_unbound_and_appends_bound():
    """RED (A19): unbound -> None, no raise, current_llm_records() None; bound ->
    a copy restricted to LLM_RECORD_KEYS is appended (the caller's dict intact)."""
    record_call = _need("record_llm_call")
    current = _need("current_llm_records")
    start = _need("start_llm_ledger")
    ledger_var = getattr(_need_leaf(), "_LLM_LEDGER", None)

    def body():
        if isinstance(ledger_var, contextvars.ContextVar):
            ledger_var.set(None)
        rec = dict(_haiku_record(input_tokens=10, output_tokens=2), extra="dropped")
        snapshot = copy.deepcopy(rec)
        assert record_call(rec) is None
        assert current() is None
        bound = start()
        assert current() is bound
        record_call(rec)
        assert len(bound) == 1 and tuple(bound[0]) == RECORD_KEYS
        assert bound[0] is not rec and rec == snapshot

    _isolated(body)


def _spend_records(batch=True, n=2):
    arec = _need("anthropic_usage_record")
    return [arec("claude-haiku-5-5", {"input_tokens": 1000, "output_tokens": 200,
                                      "cache_read_input_tokens": 100}, batch=batch) for _ in range(n)]


def test_a20_spend_ledger_row_shape():
    """RED (A20): the migration-050 row: keys == SPEND_LEDGER_COLUMNS; sums;
    request_count; cost round 6; complete; basis; the provider's as-of date;
    isoformat periods; zero records -> 0.0 complete."""
    row_of = _need("spend_ledger_row")
    assert tuple(_need("SPEND_LEDGER_COLUMNS")) == SPEND_COLUMNS
    start = datetime(2026, 10, 22, 1, 0, tzinfo=timezone.utc)
    end = start + timedelta(hours=1)
    recs = _spend_records()
    row = row_of(job="kb_seed", lane="offclock", mode="batch", provider="anthropic",
                 model="claude-haiku-5-5", records=recs, role="seed",
                 provider_batch_id="msgbatch_s03_1", period_start=start, period_end=end)
    assert set(row) == set(SPEND_COLUMNS) and len(row) == len(SPEND_COLUMNS)
    assert row["request_count"] == 2
    assert (row["input_tokens"], row["output_tokens"], row["cache_read_tokens"]) == (2000, 400, 200)
    assert row["cost_usd"] == round(sum(r["cost_usd"] for r in recs), 6)
    assert row["cost_complete"] is True and row["basis"] == "list_price"
    assert row["price_table_as_of"] == "2026-10-22"
    assert row["period_start"] == start.isoformat() and row["period_end"] == end.isoformat()
    zero = row_of(job="kb_seed", lane="offclock", mode="sync", provider="anthropic",
                  model="claude-haiku-5-5", records=[])
    assert zero["request_count"] == 0 and zero["cost_usd"] == 0.0 and zero["cost_complete"] is True
    unpriced = _need("anthropic_usage_record")("claude-haiku-5-5", None)
    bad = row_of(job="kb_seed", lane="offclock", mode="sync", provider="anthropic",
                 model="claude-haiku-5-5", records=[unpriced])
    assert bad["cost_usd"] is None and bad["cost_complete"] is False


@pytest.mark.parametrize("override", [
    {"job": ""}, {"job": "x" * 65}, {"lane": "nightly"}, {"mode": "stream"},
    {"provider": "mistral"}, {"model": ""}, {"model": "claude-sonnet-5-5"},
    {"role": ""}, {"provider_batch_id": "x" * 129}, {"mode": "sync"},
    {"records": "openai"}, {"period_start": "2026-10-22"}, {"period_end": 123},
])
def test_a20b_spend_ledger_row_validation(override):
    """RED (A20 + C10): each invalid input raises ValueError (one row each); a
    str period is a ValueError, not an AttributeError."""
    row_of = _need("spend_ledger_row")
    kwargs = dict(job="kb_seed", lane="offclock", mode="batch", provider="anthropic",
                  model="claude-haiku-5-5", records=_spend_records())
    if override.get("records") == "openai":
        kwargs["records"] = [_need("openai_entry_record")(
            {"model": "gpt-4o", "prompt_tokens": 10, "completion_tokens": 2, "cached_tokens": 0,
             "cost_usd": op.list_price_usd("gpt-4o", 10, 2, 0)})]
    else:
        kwargs.update(override)
    with pytest.raises(ValueError):
        row_of(**kwargs)


# ===========================================================================
# B -- metadata.llm through the builder (RB)
# ===========================================================================
def _assert_llm_mirrors_openai(llm, openai, where):
    assert isinstance(llm, dict), f"{where}: metadata.llm absent"
    assert set(llm) == SUMMARY_KEYS, f"{where}: keys {sorted(set(llm) ^ SUMMARY_KEYS)} (R-S03-1 summary only)"
    for key in ("calls", "priced_calls", "unpriced_calls", "prompt_tokens", "completion_tokens",
                "cost_usd", "cost_complete"):
        assert llm[key] == openai[key], (where, key, llm[key], openai[key])
    assert llm["cache_read_tokens"] == openai["cached_tokens"]
    assert llm["by_provider"] == {"openai": {"calls": openai["calls"], "cost_usd": openai["cost_usd"]}}
    assert set(llm["by_model"]) == set(openai["by_model"])
    for model, row in openai["by_model"].items():
        assert llm["by_model"][model]["calls"] == row["calls"]
        assert llm["by_model"][model]["cost_usd"] == row["cost_usd"]
        assert llm["by_model"][model]["provider"] == "openai"
    assert llm["price_table_as_of"] == PRICE_AS_OF
    assert llm["schema_version"] == 1 and llm["basis"] == "list_price"
    assert len(json.dumps(llm)) < 2048, f"{where}: about 1 KB, bounded by the model count"


@pytest.mark.asyncio
async def test_b1_rest_compare_carries_metadata_llm(monkeypatch):
    """RED (B1, RB; BL4 recorder row): ON, the REST compare's metadata.llm is the
    summary of the 11 dispatches, equal field for field to metadata.openai, and
    the module-attribute recorder sees build_llm_metadata called."""
    _set_flag(monkeypatch, "true")
    calls = _leaf_recorders(monkeypatch)
    result, client = await _rest(monkeypatch)
    meta = result["metadata"]
    assert client.chat.completions.create.await_count == 11
    assert "llm" in meta, f"metadata.llm absent under ON; keys={sorted(meta)}"
    _assert_llm_mirrors_openai(meta["llm"], meta["openai"], "rest")
    assert meta["llm"]["calls"] == 11
    assert calls.get("build_llm_metadata", 0) >= 1, f"BL4: the builder must reach the leaf by module attribute: {calls}"


@pytest.mark.asyncio
async def test_b2_stream_complete_carries_metadata_llm(monkeypatch):
    """RED (B2): the stream complete payload carries the same summary."""
    _set_flag(monkeypatch, "true")
    complete, client = await _stream(monkeypatch)
    meta = complete["metadata"]
    assert "llm" in meta, f"metadata.llm absent on the stream complete; keys={sorted(meta)}"
    _assert_llm_mirrors_openai(meta["llm"], meta["openai"], "stream")
    assert meta["llm"]["calls"] == client.chat.completions.create.await_count


async def _cm17_partial(monkeypatch, *, llm_record=False):
    """The cm17 hard-cap partial: the impl binds the ledger (and, when asked, an
    llm ledger with one Haiku record), dispatches ONE gpt-4o-mini 1000/200 call
    (untracked) and hangs past a 0.2 s cap."""
    from tests.test_compare_timeout_graceful import _fake_product

    _pin_default_models(monkeypatch)
    monkeypatch.setattr(scs_mod, "STREAM_HARD_CAP_SECONDS", 0.2)
    client = _usage_client()
    mod = _leaf()

    async def _impl(self, *args, **kwargs):
        self._openai_ledger = op.start_openai_ledger()
        if llm_record:
            mod.start_llm_ledger()
            mod.record_llm_call(mod.anthropic_usage_record(
                "claude-haiku-5-5", {"input_tokens": 300, "output_tokens": 50}))
        await abs_mod.guarded_llm_create(client, model="gpt-4o-mini", messages=[])
        self._partial_build_ctx = {
            "query": "Acme Widget vs Globex Gadget", "region": "bahrain",
            "from_cache": False, "user_preferences": None,
            "category_used": "fragrances", "category_switched": False,
            "original_category": None,
        }
        self._partial_product_data = [_fake_product("Acme Widget"), _fake_product("Globex Gadget")]
        self._partial_scoring_result = None
        self._partial_product_names = None
        self._partial_comparison = None
        await asyncio.sleep(60)

    svc = scs_mod.get_comparison_service()
    with patch.object(svc, "_compare_from_text_impl", _impl.__get__(svc)):
        result = await svc.compare_from_text("Acme Widget vs Globex Gadget", region="bahrain")
    assert result.get("success") is True and result["metadata"].get("partial") is True, "harness: no partial"
    return result


@pytest.mark.asyncio
async def test_b3_hard_cap_partial_carries_metadata_llm_and_the_unclaimed_add(monkeypatch):
    """RED (B3 + R-S03-2): ON, the partial's metadata.llm counts the one call
    (0.00027) and metadata.total_cost carries that UNCLAIMED call's list price
    (the partial's service total is 0.0: the dispatch is untracked)."""
    _set_flag(monkeypatch, "true")
    _need_leaf()
    result = await _cm17_partial(monkeypatch)
    meta = result["metadata"]
    llm = meta.get("llm")
    assert isinstance(llm, dict) and set(llm) == SUMMARY_KEYS, f"metadata.llm {llm!r}"
    assert llm["calls"] == 1 and llm["cost_usd"] == pytest.approx(0.00027, abs=1e-9)
    assert meta["total_cost"] == pytest.approx(0.00027, abs=1e-9), (
        f"R-S03-2: the unclaimed list price joins metadata.total_cost on the partial path: {meta['total_cost']}"
    )


@pytest.mark.parametrize("flag", OFF_VALUES)
@pytest.mark.asyncio
async def test_b4_flag_off_no_metadata_llm_full_config_rest(monkeypatch, flag):
    """PIN (B4, B1 rule): OFF with the unit's state primed and recorders on
    every leaf function: no metadata.llm, zero leaf calls (kills M1 / M3 and the
    flag-read-not-first mutants at RB / TG / MR / OV)."""
    _prime_leaf_state(monkeypatch, flag)
    calls = _leaf_recorders(monkeypatch)
    result, _ = await _rest(monkeypatch)
    assert "llm" not in result["metadata"], f"flag {flag!r}: metadata.llm leaked OFF"
    assert not _called(calls), f"flag {flag!r}: leaf functions called OFF: {_called(calls)}"


@pytest.mark.parametrize("flag", (None, "false", " FALSE "))
@pytest.mark.asyncio
async def test_b4s_flag_off_no_metadata_llm_full_config_stream(monkeypatch, flag):
    """PIN (B4, stream twin)."""
    _prime_leaf_state(monkeypatch, flag)
    calls = _leaf_recorders(monkeypatch)
    complete, _ = await _stream(monkeypatch)
    assert "llm" not in complete["metadata"], f"flag {flag!r}: metadata.llm leaked OFF"
    assert not _called(calls), f"flag {flag!r}: leaf functions called OFF: {_called(calls)}"


@pytest.mark.parametrize("path", ["rest", "stream"])
@pytest.mark.asyncio
async def test_b5_flag_off_metadata_openai_and_total_cost_equal_base_recording(monkeypatch, path):
    """PIN (B5, the OFF literal R-S03-2 names): flag "false", the distinct client:
    metadata.openai, metadata.total_cost (the base mini estimate), serper_calls
    and gpt_calls equal the literals recorded at base with the same
    content-keyed fake (F2-1: B5_BASE_*, recorded at 84c861f6; the RED gate's
    call-index fixture 0.016634 / 0.017992 at 95cf6f86 is the historical
    figure)."""
    _prime_leaf_state(monkeypatch, "false")
    calls = _leaf_recorders(monkeypatch)
    if path == "rest":
        result, _ = await _rest(monkeypatch)
        meta = result["metadata"]
    else:
        complete, _ = await _stream(monkeypatch)
        meta = complete["metadata"]
    assert meta["openai"] == B5_BASE_OPENAI
    assert meta["total_cost"] == B5_BASE_TOTAL_COST, meta["total_cost"]
    assert meta["serper_calls"] == B5_SERPER_CALLS and meta["gpt_calls"] == B5_GPT_CALLS
    assert "llm" not in meta
    assert not _called(calls), _called(calls)


def test_b6_caller_metadata_override_wins(monkeypatch):
    """PIN (B6, kills M4): ON, a caller metadata={"llm": ...} wins."""
    _set_flag(monkeypatch, "true")

    def body():
        summary = op.summarize_openai_ledger(_bind_entries([("gpt-4o", 1000, 200)]))
        result = _builder(openai_usage=summary, metadata={"llm": {"x": 1}})
        assert result["metadata"]["llm"] == {"x": 1}

    _isolated(body)


def test_b7_builder_without_openai_usage_writes_no_llm(monkeypatch):
    """PIN (B7): ON, no openai_usage and no bound ledger -> no metadata.llm and
    metadata.total_cost == round(total_cost, 6)."""
    _set_flag(monkeypatch, "true")

    def body():
        op._LEDGER.set(None)
        result = _builder(total_cost=0.0123456789)
        assert "llm" not in result["metadata"]
        assert result["metadata"]["total_cost"] == round(0.0123456789, 6)

    _isolated(body)


def test_b8_unverified_ledger_takes_the_handed_summary(monkeypatch):
    """RED (B8, kills M5): ON, a bound ledger of 2 entries but a handed
    openai_usage of 3 calls -> metadata.llm counts 3 at the summary's cost."""
    _set_flag(monkeypatch, "true")
    _need_leaf()

    def body():
        _bind_entries([("gpt-4o-mini", 1000, 200), ("gpt-4o-mini", 1000, 200)])
        handed = {"calls": 3, "priced_calls": 3, "unpriced_calls": 0, "prompt_tokens": 3000,
                  "cached_tokens": 0, "completion_tokens": 600, "cost_usd": 0.00081,
                  "cost_complete": True,
                  "by_model": {"gpt-4o-mini": {"calls": 3, "prompt_tokens": 3000, "cached_tokens": 0,
                                               "completion_tokens": 600, "cost_usd": 0.00081}},
                  "basis": "list_price", "price_table_as_of": "2026-10-08"}
        llm = _builder(openai_usage=handed)["metadata"].get("llm")
        assert isinstance(llm, dict), "metadata.llm absent"
        assert llm["calls"] == 3 and llm["cost_usd"] == 0.00081
        assert llm["by_provider"] == {"openai": {"calls": 3, "cost_usd": 0.00081}}

    _isolated(body)


@pytest.mark.asyncio
async def test_b9_llm_ledger_records_join_metadata_llm(monkeypatch):
    """RED (B9): ON, the cm17 partial with an llm ledger holding one Haiku
    record: metadata.llm counts 2 calls, anthropic 1 at its list price;
    metadata.openai still counts the OpenAI call only."""
    _set_flag(monkeypatch, "true")
    _need("start_llm_ledger")
    result = await _cm17_partial(monkeypatch, llm_record=True)
    meta = result["metadata"]
    llm = meta.get("llm")
    assert isinstance(llm, dict) and llm["calls"] == 2, llm
    haiku = _price("anthropic", "claude-haiku-5-5", input_tokens=300, output_tokens=50)
    assert llm["by_provider"]["anthropic"]["calls"] == 1
    assert llm["by_provider"]["anthropic"]["cost_usd"] == round(haiku, 6)
    assert llm["by_provider"]["openai"]["calls"] == 1
    assert meta["openai"]["calls"] == 1


def test_b10_openai_records_on_the_llm_ledger_are_dropped(monkeypatch):
    """RED (R-S03-7): the llm ledger is non-OpenAI only; build_llm_metadata drops
    a record whose provider is openai, so nothing double-counts."""
    _set_flag(monkeypatch, "true")
    build = _need("build_llm_metadata")
    mod = _need_leaf()

    def body():
        ledger = _bind_entries([("gpt-4o-mini", 1000, 200)])
        mod.start_llm_ledger()
        mod.record_llm_call(mod.anthropic_usage_record("claude-haiku-5-5", {"input_tokens": 300,
                                                                            "output_tokens": 50}))
        mod.record_llm_call(mod.openai_entry_record(dict(ledger[0])))
        llm = build(op.summarize_openai_ledger(ledger))
        assert llm["calls"] == 2, f"an openai record on the llm ledger must be dropped: {llm['calls']}"
        assert llm["by_provider"]["openai"]["calls"] == 1
        assert llm["by_provider"]["anthropic"]["calls"] == 1

    _isolated(body)


@pytest.mark.asyncio
async def test_b11_builder_fault_delivers_base_body_with_one_warning(monkeypatch, caplog):
    """RED (R-S03-5, RB site): ON, build_llm_metadata raises -> the REST compare
    still delivers, no metadata.llm, metadata.openai intact, exactly one
    '[LLM-LEDGER] ... failed type=_LeafBoom -- base value' WARNING."""
    caplog.set_level(logging.WARNING)
    _set_flag(monkeypatch, "true")
    mod = _need_leaf()
    _need("build_llm_metadata")
    monkeypatch.setattr(mod, "build_llm_metadata", _boom)
    result, client = await _rest(monkeypatch)
    meta = result["metadata"]
    assert "llm" not in meta
    assert meta["openai"]["calls"] == client.chat.completions.create.await_count
    _assert_one_fallback_warning(caplog, "RB")


# ===========================================================================
# C / J / U -- _track_gpt_cost (TG) and the unclaimed add (R-S03-2)
# ===========================================================================
def _svc():
    return scs_mod.get_comparison_service()


def test_c1_track_prices_the_matched_ledger_entry(monkeypatch):
    """RED (C1; BL4 recorder row): ON, a bound gpt-4o 1187 / 233 entry: the tracked
    delta is its list price 0.0052975 (base: the mini estimate 0.00031785)."""
    _set_flag(monkeypatch, "true")
    _need("tracked_call_cost_usd")
    calls = _leaf_recorders(monkeypatch)

    def body():
        _bind_entries([("gpt-4o", 1187, 233)])
        svc = _svc()
        a, g = svc.api_calls, svc.gpt_calls
        svc._track_gpt_cost({"prompt_tokens": 1187, "completion_tokens": 233})
        assert svc.total_cost == pytest.approx(0.0052975, abs=1e-12), svc.total_cost
        assert (svc.api_calls, svc.gpt_calls) == (a + 1, g + 1)

    _isolated(body)
    assert calls.get("tracked_call_cost_usd", 0) == 1, calls


def test_c2_each_entry_claimed_once(monkeypatch):
    """RED (C2, kills M14): two entries with equal tokens (mini then 4o): the
    first call adds the mini price, the second the 4o price, a third the base."""
    _set_flag(monkeypatch, "true")
    _need_leaf()

    def body():
        _bind_entries([("gpt-4o-mini", 1000, 200), ("gpt-4o", 1000, 200)])
        svc = _svc()
        deltas = []
        for _ in range(3):
            before = svc.total_cost
            svc._track_gpt_cost({"prompt_tokens": 1000, "completion_tokens": 200})
            deltas.append(svc.total_cost - before)
        assert deltas == [pytest.approx(0.00027, abs=1e-12), pytest.approx(0.0045, abs=1e-12),
                          pytest.approx(_base_estimate(1000, 200), abs=1e-12)], deltas

    _isolated(body)


C3_TUPLES = ((1234, 567), (1187, 233), (1000, 200), (999, 1001), (12345, 678))


@pytest.mark.parametrize("flag", [None, "false", "true"])
def test_c3_no_bound_ledger_is_bit_identical_base(monkeypatch, flag):
    """PIN (C3, kills M40 as redefined: (p*0.15 + c*0.60)/1e6 differs on
    1234 / 567): no bound ledger -> the delta is the base expression (==)."""
    _set_flag(monkeypatch, flag)

    def body():
        op._LEDGER.set(None)
        mod = _leaf()
        if mod is not None and isinstance(getattr(mod, "_LLM_LEDGER", None), contextvars.ContextVar):
            mod._LLM_LEDGER.set(None)
        for p, c in C3_TUPLES:
            svc = _svc()
            svc._track_gpt_cost({"prompt_tokens": p, "completion_tokens": c})
            assert svc.total_cost == (p * 0.15 / 1_000_000) + (c * 0.60 / 1_000_000), (p, c)

    _isolated(body)


def test_c4_unmatched_usage_is_base_estimate(monkeypatch):
    """PIN (C4): ON, a bound entry with other tokens -> the base expression (==)."""
    _set_flag(monkeypatch, "true")

    def body():
        _bind_entries([("gpt-4o", 1000, 200)])
        svc = _svc()
        svc._track_gpt_cost({"prompt_tokens": 1234, "completion_tokens": 567})
        assert svc.total_cost == _base_estimate(1234, 567)

    _isolated(body)


def test_c5_unpriced_match_is_base_estimate_never_none(monkeypatch):
    """PIN (C5, kills M15): ON, a matching gpt-5 entry (unpriced) -> the base
    expression, a float."""
    _set_flag(monkeypatch, "true")

    def body():
        _bind_entries([("gpt-5", 1234, 567)])
        svc = _svc()
        svc._track_gpt_cost({"prompt_tokens": 1234, "completion_tokens": 567})
        assert isinstance(svc.total_cost, float)
        assert svc.total_cost == _base_estimate(1234, 567)

    _isolated(body)


@pytest.mark.parametrize("flag", ["false", None, " FALSE "])
def test_c6_flag_off_adds_base_estimate_with_ledger_bound(monkeypatch, flag):
    """PIN (C6, kills M16 / M40 / the TG flag-read-not-first mutant): OFF with a
    matching gpt-4o entry bound and the state primed -> the base mini estimate
    (==); zero leaf calls."""

    def body():
        _prime_leaf_state(monkeypatch, flag)
        calls = _leaf_recorders(monkeypatch)
        _bind_entries([("gpt-4o", 1234, 567)])
        svc = _svc()
        svc._track_gpt_cost({"prompt_tokens": 1234, "completion_tokens": 567})
        assert svc.total_cost == _base_estimate(1234, 567)
        assert not _called(calls), _called(calls)

    _isolated(body)


@pytest.mark.asyncio
async def test_c7_e2e_tracked_deltas_follow_the_ledger(monkeypatch):
    """RED (C7): ON, the REST compare: every tracked delta equals the list price
    of a DISTINCT ledger entry with equal tokens; the gpt-4o verdict delta is
    (p*2.5 + c*10)/1e6."""
    _set_flag(monkeypatch, "true")
    _need_leaf()
    sink = {}
    _e2e_spies(monkeypatch, sink)
    await _rest(monkeypatch)
    ledger = sink["ledgers"][-1]
    assert len(sink["tracked"]) == 9 and len(ledger) == 11, (len(sink["tracked"]), len(ledger))
    taken = set()
    for usage, delta in sink["tracked"]:
        p, c = usage.get("prompt_tokens"), usage.get("completion_tokens")
        hit = next((i for i, e in enumerate(ledger) if i not in taken
                    and e["prompt_tokens"] == p and e["completion_tokens"] == c), None)
        assert hit is not None, (p, c)
        taken.add(hit)
        assert delta == pytest.approx(ledger[hit]["cost_usd"], abs=1e-12), (
            f"tracked {p}/{c} on {ledger[hit]['model']}: delta {delta} != list price {ledger[hit]['cost_usd']}"
        )
    verdicts = [(u, d) for u, d in sink["tracked"]
                if any(e["model"] == "gpt-4o" and e["prompt_tokens"] == u["prompt_tokens"] for e in ledger)]
    assert verdicts, "harness: no tracked gpt-4o call"
    for usage, delta in verdicts:
        want = (usage["prompt_tokens"] * 2.5 + usage["completion_tokens"] * 10) / 1e6
        assert delta == pytest.approx(want, abs=1e-12)


def test_c8_claims_reset_on_a_new_openai_ledger(monkeypatch):
    """RED (C8): one service, two start_openai_ledger() binds: the second
    ledger's identical-token entry is claimed, not blocked by the first claim."""
    _set_flag(monkeypatch, "true")
    _need_leaf()

    def body():
        svc = _svc()
        _bind_entries([("gpt-4o", 1000, 200)])
        svc._track_gpt_cost({"prompt_tokens": 1000, "completion_tokens": 200})
        first = svc.total_cost
        _bind_entries([("gpt-4o", 1000, 200)])
        svc._track_gpt_cost({"prompt_tokens": 1000, "completion_tokens": 200})
        assert first == pytest.approx(0.0045, abs=1e-12)
        assert svc.total_cost - first == pytest.approx(0.0045, abs=1e-12)

    _isolated(body)


def test_c8b_claims_reset_when_the_llm_ledger_changes(monkeypatch):
    """RED (C11): the same OpenAI ledger, a re-bound llm ledger holding an
    identical Haiku record: the new record is claimed (not a stale claim)."""
    _set_flag(monkeypatch, "true")
    mod = _need_leaf()

    def body():
        _bind_entries([])
        haiku = mod.anthropic_usage_record("claude-haiku-5-5", {"input_tokens": 300, "output_tokens": 50,
                                                                "cache_read_input_tokens": 4000,
                                                                "cache_creation_input_tokens": 1500})
        svc = _svc()
        usage = {"prompt_tokens": haiku["prompt_tokens"], "completion_tokens": haiku["completion_tokens"]}
        mod.start_llm_ledger()
        mod.record_llm_call(haiku)
        svc._track_gpt_cost(dict(usage))
        first = svc.total_cost
        mod.start_llm_ledger()
        mod.record_llm_call(haiku)
        svc._track_gpt_cost(dict(usage))
        assert first == pytest.approx(haiku["cost_usd"], abs=1e-12)
        assert svc.total_cost - first == pytest.approx(haiku["cost_usd"], abs=1e-12)

    _isolated(body)


@pytest.mark.parametrize("bad", [None, [], "usage"])
@pytest.mark.parametrize("flag", [None, "true"])
def test_c9_non_dict_usage_raises_exactly_as_base(monkeypatch, flag, bad):
    """PIN (C9 / R-S03-5): a non-dict usage raises AttributeError in both flag
    states (ON is never more tolerant than base); total_cost unchanged."""
    _set_flag(monkeypatch, flag)

    def body():
        _bind_entries([("gpt-4o", 1000, 200)])
        svc = _svc()
        with pytest.raises(AttributeError):
            svc._track_gpt_cost(bad)
        assert svc.total_cost == 0.0

    _isolated(body)


def test_c10_claims_never_mutate_ledger_entries(monkeypatch):
    """PIN (old C9, kills M18): after tracking, the bound entries equal their
    pre-call copies and summarise unchanged."""
    _set_flag(monkeypatch, "true")

    def body():
        ledger = _bind_entries([("gpt-4o-mini", 1000, 200), ("gpt-4o", 1187, 233)])
        before = copy.deepcopy(ledger)
        summary = op.summarize_openai_ledger(ledger)
        svc = _svc()
        svc._track_gpt_cost({"prompt_tokens": 1187, "completion_tokens": 233})
        svc._track_gpt_cost({"prompt_tokens": 1000, "completion_tokens": 200})
        assert ledger == before
        assert op.summarize_openai_ledger(ledger) == summary

    _isolated(body)


def test_c11_track_fault_adds_base_estimate_with_one_warning(monkeypatch, caplog):
    """RED (R-S03-5, TG site): ON, tracked_call_cost_usd raises -> the base
    estimate is added (==), counters +1, exactly one fallback WARNING."""
    caplog.set_level(logging.WARNING)
    _set_flag(monkeypatch, "true")
    mod = _need_leaf()
    _need("tracked_call_cost_usd")
    monkeypatch.setattr(mod, "tracked_call_cost_usd", _boom)

    def body():
        _bind_entries([("gpt-4o", 1234, 567)])
        svc = _svc()
        svc._track_gpt_cost({"prompt_tokens": 1234, "completion_tokens": 567})
        assert svc.total_cost == _base_estimate(1234, 567)
        assert (svc.api_calls, svc.gpt_calls) == (1, 1)

    _isolated(body)
    _assert_one_fallback_warning(caplog, "TG")


def test_j1_track_matches_an_llm_record(monkeypatch):
    """RED (J1): ON, an llm-ledger Haiku record (prompt 5800 / completion 50)
    is claimed by the tracked usage with those counts: the delta is its price."""
    _set_flag(monkeypatch, "true")
    mod = _need_leaf()

    def body():
        _bind_entries([])
        rec = mod.anthropic_usage_record("claude-haiku-5-5", _a14_usage("dict"))
        mod.start_llm_ledger()
        mod.record_llm_call(rec)
        svc = _svc()
        svc._track_gpt_cost({"prompt_tokens": 5800, "completion_tokens": 50})
        assert rec["prompt_tokens"] == 5800 and rec["completion_tokens"] == 50
        assert svc.total_cost == pytest.approx(rec["cost_usd"], abs=1e-12)

    _isolated(body)


def _assert_total_follows_ledger(meta, sink, where):
    ledger = sink["ledgers"][-1]
    expected = sum(e["cost_usd"] for e in ledger) + 0.001 * sink["serper"] + sum(sink["amounts"])
    assert meta["total_cost"] == pytest.approx(expected, abs=1.5e-6), (
        f"{where}: metadata.total_cost {meta['total_cost']} != every ledger entry at list "
        f"({sum(e['cost_usd'] for e in ledger)}) + Serper + Tier 1.5 = {expected} (R-S03-2)"
    )
    assert isinstance(meta["total_cost"], float)


@pytest.mark.asyncio
async def test_u1_rest_total_cost_carries_tracked_and_unclaimed_list_prices(monkeypatch):
    """RED (R-S03-2): ON, the REST compare whose ledger holds 2 UNTRACKED gpt-4o
    calls: metadata.total_cost = every ledger entry's list price (tracked ones
    priced per model + the unclaimed ones at list) + Serper + Tier 1.5. Base:
    0.016634 (the mini estimate, B5)."""
    _set_flag(monkeypatch, "true")
    _need_leaf()
    sink = {}
    _e2e_spies(monkeypatch, sink)
    result, _ = await _rest(monkeypatch)
    assert len(sink["tracked"]) < len(sink["ledgers"][-1]), "harness: no untracked entry"
    _assert_total_follows_ledger(result["metadata"], sink, "rest")


@pytest.mark.asyncio
async def test_u2_stream_total_cost_carries_tracked_and_unclaimed_list_prices(monkeypatch):
    """RED (R-S03-2, stream complete twin of U1)."""
    _set_flag(monkeypatch, "true")
    _need_leaf()
    sink = {}
    _e2e_spies(monkeypatch, sink)
    complete, _ = await _stream(monkeypatch)
    _assert_total_follows_ledger(complete["metadata"], sink, "stream")


def test_u3_builder_adds_only_unclaimed_entries(monkeypatch):
    """RED (R-S03-2, unit): ON, a gpt-4o entry claimed by a tracked call and a
    gpt-4o-mini 500 / 100 entry nobody claimed: the builder adds 0.000135 to the
    service total (0.0045), never the claimed 0.0045 a second time."""
    _set_flag(monkeypatch, "true")
    _need_leaf()

    def body():
        ledger = _bind_entries([("gpt-4o", 1000, 200), ("gpt-4o-mini", 500, 100)])
        svc = _svc()
        svc._track_gpt_cost({"prompt_tokens": 1000, "completion_tokens": 200})
        result = _builder(total_cost=svc.total_cost, openai_usage=op.summarize_openai_ledger(ledger))
        assert result["metadata"]["total_cost"] == round(0.0045 + 0.000135, 6), result["metadata"]["total_cost"]

    _isolated(body)


@pytest.mark.parametrize("flag", OFF_VALUES)
def test_u4_flag_off_builder_total_cost_is_base(monkeypatch, flag):
    """PIN (R-S03-2 OFF half; kills the unclaimed add computed with the flag
    OFF): OFF, an unclaimed bound entry -> metadata.total_cost ==
    round(total_cost, 6); zero leaf calls."""

    def body():
        _prime_leaf_state(monkeypatch, flag)
        calls = _leaf_recorders(monkeypatch)
        ledger = _bind_entries([("gpt-4o", 1000, 200)])
        result = _builder(total_cost=0.0123456789, openai_usage=op.summarize_openai_ledger(ledger))
        assert result["metadata"]["total_cost"] == round(0.0123456789, 6)
        assert "llm" not in result["metadata"]
        assert not _called(calls), _called(calls)

    _isolated(body)


def test_u5_unpriced_unclaimed_entry_adds_nothing(monkeypatch):
    """PIN (R-S03-2): ON, an unclaimed UNPRICED entry (gpt-5) adds nothing:
    metadata.total_cost == round(total_cost, 6), a float."""
    _set_flag(monkeypatch, "true")

    def body():
        ledger = _bind_entries([("gpt-5", 1000, 200)])
        result = _builder(total_cost=0.0123456789, openai_usage=op.summarize_openai_ledger(ledger))
        assert result["metadata"]["total_cost"] == round(0.0123456789, 6)
        assert isinstance(result["metadata"]["total_cost"], float)

    _isolated(body)


# ===========================================================================
# D -- the openai_service cost sites (OV1 / OV2 / OD)
# ===========================================================================
VISION_JSON = (
    '[{"brand": "Acme", "name": "Widget", "size_or_count": null, '
    '"visible_price": null, "confidence": "high"}, '
    '{"brand": "Globex", "name": "Gadget", "size_or_count": null, '
    '"visible_price": null, "confidence": "high"}]'
)
IMAGES = [{"bytes": JPEG, "mime_type": "image/jpeg"}, {"bytes": JPEG + b"\x01", "mime_type": "image/jpeg"}]


def _vision_client(prompt=500, completion=100, cached=0, content=VISION_JSON, usage="set"):
    client = MagicMock()

    async def _create(**kwargs):
        u = _usage(prompt, completion, cached) if usage == "set" else None
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=content, refusal=None),
                                     finish_reason="stop")],
            usage=u, model=kwargs.get("model"))

    client.chat.completions.create = AsyncMock(side_effect=_create)
    return client


def _identify(monkeypatch, client):
    monkeypatch.setattr(oai, "client", client)
    return asyncio.run(oai.identify_products(list(IMAGES)))


def test_d1_v1_vision_cost_priced_by_model(monkeypatch):
    """RED (D1; BL4 recorder row): ON, OPENAI_MODEL_VISION=gpt-4o, 500 / 100 ->
    (500*2.5 + 100*10)/1e6 = 0.00225 (base: the mini 0.000135)."""
    _set_flag(monkeypatch, "true")
    monkeypatch.setenv("OPENAI_MODEL_VISION", "gpt-4o")
    _need_leaf()
    calls = _leaf_recorders(monkeypatch)
    out = _identify(monkeypatch, _vision_client())
    assert out["cost"] == 0.00225, out["cost"]
    assert calls.get("openai_usage_cost_usd", 0) == 1, calls


def test_d2_v1_vision_cost_prices_cached_tokens(monkeypatch):
    """RED (D2, kills M19): ON, mini, 500 / 100 / cached 200 -> (300*0.15 +
    200*0.075 + 100*0.60)/1e6 = 0.00012."""
    _set_flag(monkeypatch, "true")
    monkeypatch.setenv("OPENAI_MODEL_VISION", "gpt-4o-mini")
    out = _identify(monkeypatch, _vision_client(cached=200))
    assert out["cost"] == 0.00012, out["cost"]


@pytest.mark.parametrize("flag", ["false", None])
def test_d3_v1_flag_off_full_config_base_cost(monkeypatch, flag):
    """PIN (D3, kills M20a): OFF, gpt-4o, 500 / 100 -> the base mini formula
    0.000135; zero leaf calls."""
    def body():
        _prime_leaf_state(monkeypatch, flag)
        monkeypatch.setenv("OPENAI_MODEL_VISION", "gpt-4o")
        calls = _leaf_recorders(monkeypatch)
        out = _identify(monkeypatch, _vision_client())
        assert out["cost"] == 0.000135, out["cost"]
        assert not _called(calls), _called(calls)

    _isolated(body)


def test_d4_v1_unpriced_model_falls_back_to_base(monkeypatch):
    """PIN (D4): ON, OPENAI_MODEL_VISION=gpt-5 -> the base estimate 0.000135 (a float)."""
    _set_flag(monkeypatch, "true")
    monkeypatch.setenv("OPENAI_MODEL_VISION", "gpt-5")
    out = _identify(monkeypatch, _vision_client())
    assert out["cost"] == 0.000135 and isinstance(out["cost"], float)


V2_REPLY = json.dumps({"products": [
    {"image_index": 0, "brand": "Acme", "name": "Widget", "category": "fragrances",
     "product_type": "perfume bottle", "size_or_count": None, "visible_price": None,
     "distinguishing_features": [], "is_product": True, "confidence": "high"},
    {"image_index": 1, "brand": "Globex", "name": "Gadget", "category": "fragrances",
     "product_type": "perfume bottle", "size_or_count": None, "visible_price": None,
     "distinguishing_features": [], "is_product": True, "confidence": "high"},
]})


def test_d5_v2_vision_cost_priced_by_model(monkeypatch):
    """RED (D5): ON + ENABLE_VISION_IDENTITY_V2, gpt-4o, 100 / 15 ->
    round((100*2.5 + 15*10)/1e6, 6) = 0.0004 (base: 2.4e-05)."""
    _set_flag(monkeypatch, "true")
    monkeypatch.setenv("ENABLE_VISION_IDENTITY_V2", "true")
    monkeypatch.setenv("VISION_TIMEOUT_SECONDS", "7.5")
    monkeypatch.setenv("OPENAI_MODEL_VISION", "gpt-4o")
    out = _identify(monkeypatch, _vision_client(prompt=100, completion=15, content=V2_REPLY))
    assert out["cost"] == 0.0004, out["cost"]


def test_d5b_v2_flag_off_full_config_base_cost(monkeypatch):
    """PIN (D5b, BL3, kills M20b): flag "false", V2 on, gpt-4o, 100 / 15 -> the
    base mini formula 2.4e-05; zero leaf calls."""
    def body():
        _prime_leaf_state(monkeypatch, "false")
        monkeypatch.setenv("ENABLE_VISION_IDENTITY_V2", "true")
        monkeypatch.setenv("VISION_TIMEOUT_SECONDS", "7.5")
        monkeypatch.setenv("OPENAI_MODEL_VISION", "gpt-4o")
        calls = _leaf_recorders(monkeypatch)
        out = _identify(monkeypatch, _vision_client(prompt=100, completion=15, content=V2_REPLY))
        assert out["cost"] == 2.4e-05, out["cost"]
        assert not _called(calls), _called(calls)

    _isolated(body)


def _disambiguate(monkeypatch, prompt=300, completion=20):
    client = _vision_client(prompt=prompt, completion=completion,
                            content='{"distinct_product": "true", "confidence": "high"}')
    monkeypatch.setattr(oai, "get_client", lambda *a, **k: client)
    return asyncio.run(oai.disambiguate_variant_line("fragrances", "Acme Widget EDP",
                                                     "Acme Widget EDT", "formula"))


def test_d6_disambiguation_cost_priced_by_model(monkeypatch):
    """RED (D6): ON, OPENAI_MODEL_STANDARD=gpt-4o, 300 / 20 -> 0.00095 (base 5.7e-05)."""
    _set_flag(monkeypatch, "true")
    monkeypatch.setenv("OPENAI_MODEL_STANDARD", "gpt-4o")
    out = _disambiguate(monkeypatch)
    assert out["distinct_product"] is True
    assert out["cost"] == 0.00095, out["cost"]


def test_d6b_disambiguation_flag_off_base_cost(monkeypatch):
    """PIN (D6b, kills M20c): flag "false", the same env -> 5.7e-05; zero leaf calls."""
    def body():
        _prime_leaf_state(monkeypatch, "false")
        monkeypatch.setenv("OPENAI_MODEL_STANDARD", "gpt-4o")
        calls = _leaf_recorders(monkeypatch)
        out = _disambiguate(monkeypatch)
        assert out["cost"] == 5.7e-05, out["cost"]
        assert not _called(calls), _called(calls)

    _isolated(body)


class _CreditLedger:
    def __init__(self):
        self.consumes, self.refunds, self.anon_refunds = [], [], []

    def consume(self, user_id, access_token="", *_a, **_kw):
        self.consumes.append(user_id)

        async def _r():
            return {"allowed": True, "reason": None, "tier": "free", "consumed": True,
                    "consumed_keys": {"daily": "usage:daily:" + str(user_id)},
                    "remaining": {"daily": 2, "monthly": 9, "lifetime_free": 2}}
        return _r()

    def refund(self, user_id, consumed_keys=None, *_a, **_kw):
        self.refunds.append(user_id)
        return _done()

    def anon_refund(self, device_fp, consumed_keys=None, *_a, **_kw):
        self.anon_refunds.append(device_fp)
        return _done()


@pytest.mark.parametrize("flag", [None, "true"])
def test_d7_vision_usage_none_keeps_the_base_500_and_both_refunds(monkeypatch, flag):
    """PIN (D7, C1 / R-S03-5; L9 deleted): a V1 vision reply WITHOUT usage still
    raises AttributeError in identify_products and the camera route serves the
    base 500 'Image analysis failed. Please try again.' with the reserved refund
    (signed-in) and the anon refund (anonymous), in both flag states."""
    _set_flag(monkeypatch, flag)
    monkeypatch.setenv("OPENAI_MODEL_VISION", "gpt-4o-mini")
    monkeypatch.setenv("ENABLE_PAID_ROUTE_METERING", "true")
    client = _vision_client(usage=None)
    monkeypatch.setattr(oai, "client", client)
    with pytest.raises(AttributeError):
        asyncio.run(oai.identify_products(list(IMAGES)))
    led = _CreditLedger()
    for mod in (usage_service, image_routes):
        monkeypatch.setattr(mod, "consume_comparison_credit", led.consume, raising=False)
        monkeypatch.setattr(mod, "refund_comparison_credit", led.refund, raising=False)
    monkeypatch.setattr(image_routes, "refund_anon_comparison_credit", led.anon_refund)
    files = [("images", (f"p{i}.jpg", JPEG, "image/jpeg")) for i in range(2)]
    user = {"id": "s03-d7-user", "email": "s03@example.test", "access_token": "s03-d7-token"}
    app.dependency_overrides[get_optional_user] = lambda: user
    try:
        resp = TestClient(app, raise_server_exceptions=False).post("/api/v1/image/identify", files=files)
    finally:
        app.dependency_overrides.pop(get_optional_user, None)
    assert resp.status_code == 500, resp.text[:300]
    assert "Image analysis failed. Please try again." in resp.text
    assert led.refunds == [user["id"]], led.refunds

    monkeypatch.setenv("ENABLE_ANON_USAGE_GATE", "true")

    async def _anon_allowed(device_fp):
        return {"allowed": True, "reason": None, "tier": "anonymous", "consumed": True,
                "consumed_keys": {"daily": "anon:daily:x"}, "remaining": {"daily": 2}}

    monkeypatch.setattr(image_routes, "check_anon_usage_allowed", _anon_allowed)
    app.dependency_overrides[get_optional_user] = lambda: None
    try:
        resp = TestClient(app, raise_server_exceptions=False).post(
            "/api/v1/image/identify", files=files, headers={"X-Device-Fingerprint": "a" * 64})
    finally:
        app.dependency_overrides.pop(get_optional_user, None)
    assert resp.status_code == 500, resp.text[:300]
    assert "Image analysis failed. Please try again." in resp.text
    assert led.anon_refunds == ["a" * 64], led.anon_refunds


# ===========================================================================
# E -- ModelRouterService (MR)
# ===========================================================================
def _router(used=0):
    svc = ModelRouterService()
    reads = AsyncMock(return_value=used)
    incs = AsyncMock(return_value=None)
    svc._get_4o_usage_today = reads
    svc._increment_4o_usage = incs
    return svc, reads, incs


def _has_provider_kw():
    params = inspect.signature(ModelRouterService.record_usage).parameters
    return "provider" in params and params["provider"].default is None


def test_e1_record_usage_accepts_provider_keyword():
    """RED (E1): record_usage(model, tokens_used, provider=None)."""
    assert _has_provider_kw(), inspect.signature(ModelRouterService.record_usage)


@pytest.mark.asyncio
async def test_e2_record_usage_skips_non_openai_provider(monkeypatch):
    """RED (E2, kills M21 / M23): ON, provider='anthropic' -> 0 increments;
    provider='openai' -> 1."""
    _set_flag(monkeypatch, "true")
    assert _has_provider_kw(), "record_usage has no provider keyword"
    svc, _, incs = _router()
    await svc.record_usage("gpt-4o", 100, provider="anthropic")
    assert incs.await_count == 0
    await svc.record_usage("gpt-4o", 100, provider="openai")
    assert incs.await_count == 1


@pytest.mark.asyncio
async def test_e3_record_usage_skips_claude_verdict_id(monkeypatch):
    """RED (E3): ON, OPENAI_MODEL_VERDICT=claude-sonnet-5-5 -> no 4o-cap increment."""
    _set_flag(monkeypatch, "true")
    monkeypatch.setenv("OPENAI_MODEL_VERDICT", "claude-sonnet-5-5")
    svc, _, incs = _router()
    await svc.record_usage("claude-sonnet-5-5", 100)
    assert incs.await_count == 0, "a call served by another provider never charges the OpenAI 4o cap"


@pytest.mark.parametrize("flag", ["false", None])
@pytest.mark.asyncio
async def test_e4_flag_off_claude_verdict_id_counts_as_base(monkeypatch, flag):
    """PIN (E4): OFF, the same env -> 1 increment; zero leaf calls."""
    _prime_leaf_state(monkeypatch, flag)
    monkeypatch.setenv("OPENAI_MODEL_VERDICT", "claude-sonnet-5-5")
    calls = _leaf_recorders(monkeypatch)
    svc, _, incs = _router()
    await svc.record_usage("claude-sonnet-5-5", 100)
    assert incs.await_count == 1
    assert not _called(calls), _called(calls)


@pytest.mark.asyncio
async def test_e5_get_model_claude_verdict_skips_the_counter(monkeypatch):
    """RED (E5; BL4 recorder row): ON, a claude verdict id is returned without
    reading the 4o counter."""
    _set_flag(monkeypatch, "true")
    monkeypatch.setenv("OPENAI_MODEL_VERDICT", "claude-sonnet-5-5")
    _need_leaf()
    calls = _leaf_recorders(monkeypatch)
    svc, reads, _ = _router()
    assert await svc.get_model(priority="high") == "claude-sonnet-5-5"
    assert reads.await_count == 0, "ON: a claude verdict id must not read the OpenAI 4o counter"
    assert calls.get("provider_of", 0) >= 1, calls


@pytest.mark.parametrize("flag", ["false", None, " FALSE "])
@pytest.mark.asyncio
async def test_e5b_flag_off_claude_verdict_reads_the_counter_once(monkeypatch, flag):
    """PIN (E5b, BL3, kills M22b get_model not gated): OFF, a claude verdict id
    reads the counter exactly once and routes as base; zero leaf calls."""
    _prime_leaf_state(monkeypatch, flag)
    monkeypatch.setenv("OPENAI_MODEL_VERDICT", "claude-sonnet-5-5")
    calls = _leaf_recorders(monkeypatch)
    svc, reads, _ = _router()
    assert await svc.get_model(priority="high") == "claude-sonnet-5-5"
    assert reads.await_count == 1
    assert not _called(calls), _called(calls)


@pytest.mark.parametrize("flag", [None, "false", "true"])
@pytest.mark.asyncio
async def test_e6_get_model_openai_cap_unchanged_both_states(monkeypatch, flag):
    """PIN (E6): the default gpt-4o verdict at 900K of 1M -> the standard model,
    the counter read once, in both states."""
    _set_flag(monkeypatch, flag)
    svc, reads, _ = _router(used=900_000)
    assert await svc.get_model(priority="high") == "gpt-4o-mini"
    assert reads.await_count == 1


@pytest.mark.parametrize("flag", [None, "true"])
@pytest.mark.asyncio
async def test_e7_openai_verdict_still_counts_both_states(monkeypatch, flag):
    """PIN (kills M23, the inverted gate): record_usage('gpt-4o', 100) with the
    default verdict id increments once in both states."""
    _set_flag(monkeypatch, flag)
    svc, _, incs = _router()
    await svc.record_usage("gpt-4o", 100)
    assert incs.await_count == 1


@pytest.mark.asyncio
async def test_e8_router_fault_falls_back_to_base_with_one_warning(monkeypatch, caplog):
    """RED (R-S03-5, MR site): ON, provider_of raises -> get_model reads the
    counter and routes as base; record_usage counts as base; one fallback
    WARNING per call."""
    caplog.set_level(logging.WARNING)
    _set_flag(monkeypatch, "true")
    monkeypatch.setenv("OPENAI_MODEL_VERDICT", "claude-sonnet-5-5")
    mod = _need_leaf()
    _need("provider_of")
    monkeypatch.setattr(mod, "provider_of", _boom)
    svc, reads, incs = _router()
    assert await svc.get_model(priority="high") == "claude-sonnet-5-5"
    assert reads.await_count == 1
    _assert_one_fallback_warning(caplog, "MR get_model")
    caplog.clear()
    await svc.record_usage("claude-sonnet-5-5", 100)
    assert incs.await_count == 1
    _assert_one_fallback_warning(caplog, "MR record_usage")


# ===========================================================================
# F -- the public share strip (S, unflagged)
# ===========================================================================
def _shared(meta_extra):
    meta = {"query": "Acme Widget vs Globex Gadget", "total_cost": 0.01}
    meta.update(meta_extra)
    return {
        "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "query": "Acme Widget vs Globex Gadget",
        "product_names": ["Acme Widget", "Globex Gadget"],
        "input_type": "text",
        "full_response": {"success": True, "products": [{"brand": "Acme", "name": "Widget"}],
                          "metadata": meta},
        "created_at": "2026-10-22T10:00:00Z",
    }


def _view(handed):
    with patch("app.api.share_routes.get_shared_comparison", new_callable=AsyncMock, return_value=handed):
        resp = TestClient(app).get("/api/v1/share/abc12xyzABC12xyzABCD")
    assert resp.status_code == 200, resp.text[:300]
    return resp.json()["comparison"]["full_response"]


LLM_ROW = {"calls": 2, "cost_usd": 0.004, "cost_complete": True,
           "by_provider": {"anthropic": {"calls": 2, "cost_usd": 0.004}}}


@pytest.mark.parametrize("flag", [None, "true"])
def test_f1_public_share_strips_metadata_llm_and_openai(monkeypatch, flag):
    """RED (F1, kills M24 / M25): unflagged (both states): neither key reaches
    the public view; total_cost and query kept; the handed dict keeps both."""
    _set_flag(monkeypatch, flag)
    stored = _shared({"openai": {"calls": 2, "cost_usd": 0.004}, "llm": copy.deepcopy(LLM_ROW)})
    handed = copy.deepcopy(stored)
    meta = _view(handed)["metadata"]
    assert "openai" not in meta and "llm" not in meta, sorted(meta)
    assert meta["total_cost"] == 0.01 and meta["query"] == "Acme Widget vs Globex Gadget"
    assert handed == stored, "the strip must copy, never mutate the stored dict"


@pytest.mark.parametrize("flag", [None, "true"])
def test_f2_public_share_strips_llm_only_row(monkeypatch, flag):
    """RED (F2): a row carrying metadata.llm only."""
    _set_flag(monkeypatch, flag)
    stored = _shared({"llm": copy.deepcopy(LLM_ROW)})
    full = _view(copy.deepcopy(stored))
    assert "llm" not in full["metadata"]
    assert full["metadata"] == {k: v for k, v in stored["full_response"]["metadata"].items() if k != "llm"}
    assert full["products"] == stored["full_response"]["products"]


def test_f3_public_share_row_without_either_key_unchanged():
    """PIN (F3): a row with neither key passes through exactly as stored."""
    stored = _shared({})
    assert _view(copy.deepcopy(stored)) == stored["full_response"]


def test_f4_owner_history_view_keeps_metadata_llm(monkeypatch):
    """PIN (F4, cm18 shape): the owner view keeps metadata.llm."""
    from app.api.auth_routes import get_current_user

    owner = {"id": "user-s03-f4", "email": "owner@example.test"}
    stored = dict(_shared({"llm": copy.deepcopy(LLM_ROW)}), user_id=owner["id"])
    app.dependency_overrides[get_current_user] = lambda: owner
    try:
        with patch("app.api.history_routes.get_comparison_by_id", new_callable=AsyncMock,
                   return_value=copy.deepcopy(stored)):
            resp = TestClient(app).get("/api/v1/comparisons/a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
    assert resp.status_code == 200, resp.text[:300]
    assert resp.json()["comparison"]["full_response"]["metadata"].get("llm") == LLM_ROW


# ===========================================================================
# G -- /admin/costs, /admin/costs/api, costs.html (AD / CH)
# ===========================================================================
OPENAI_SEL = "id,created_at,full_response->metadata->openai"
LLM_SEL = "id,created_at,full_response->metadata->llm"
BLOB_SEL = "id,created_at,full_response"


def _arow(rid, created_at, openai=None, llm=None, legacy=None):
    meta = {}
    if legacy is not None:
        meta["total_cost"] = legacy
    if openai is not None:
        meta["openai"] = openai
    if llm is not None:
        meta["llm"] = llm
    return {"id": rid, "created_at": created_at, "full_response": {"metadata": meta}}


def _g_rows():
    """A today (0.004, two providers), B legacy (two days ago), C partial 0.0012,
    D 0.0 complete, E corrupt (a bool cost): llm cost 0.0052, rows 5, with_cost
    3, partial 1, without 2 (B and E), complete False."""
    return [
        _arow("row-a", _stamp(0), openai={"cost_usd": 0.001, "cost_complete": True, "calls": 1},
              llm={"cost_usd": 0.004, "cost_complete": True, "calls": 2, "prompt_tokens": 2000,
                   "completion_tokens": 400, "cache_read_tokens": 100, "web_search_requests": 1,
                   "by_provider": {"openai": {"calls": 1, "cost_usd": 0.001},
                                   "anthropic": {"calls": 1, "cost_usd": 0.003}},
                   "by_model": {"gpt-4o-mini": {"provider": "openai", "calls": 1, "cost_usd": 0.001},
                                "claude-haiku-5-5": {"provider": "anthropic", "calls": 1,
                                                     "cost_usd": 0.003}}}),
        _arow("row-b", _stamp(2), legacy=0.01),
        _arow("row-c", _stamp(1), openai={"cost_usd": 0.0012, "cost_complete": False, "calls": 3},
              llm={"cost_usd": 0.0012, "cost_complete": False, "calls": 3, "prompt_tokens": 3000,
                   "completion_tokens": 600,
                   "by_provider": {"openai": {"calls": 3, "cost_usd": 0.0012}},
                   "by_model": {"gpt-4o-mini": {"provider": "openai", "calls": 3, "cost_usd": 0.0012}}}),
        _arow("row-d", _stamp(1), openai={"cost_usd": 0.0, "cost_complete": True, "calls": 0},
              llm={"cost_usd": 0.0, "cost_complete": True, "calls": 0, "by_provider": {},
                   "by_model": {}}),
        _arow("row-e", _stamp(1), llm={"cost_usd": True, "calls": "x"}),
    ]


class _TwoPathSupabase:
    """Answers BOTH JSON paths by key (`->openai` -> key openai, `->llm` -> key
    llm), the blob select, and the count query; records every select string;
    raises on the selects named by ``raise_on``."""

    def __init__(self, rows, raise_on=()):
        self.rows = rows
        self.raise_on = tuple(raise_on)
        self.queries = []

    def table(self, name):
        fake = self
        return SimpleNamespace(select=lambda *a, **k: _Query(fake, a, k))

    @property
    def selects(self):
        return ["".join(str(a) for a in q.select_args).replace(" ", "") for q in self.queries]

    def _execute(self, q):
        self.queries.append(q)
        sel = "".join(str(a) for a in q.select_args).replace(" ", "")
        if q.select_kwargs.get("count"):
            return SimpleNamespace(data=[], count=len(self.rows))
        if sel in self.raise_on:
            raise _LeafBoom(BOOM_TEXT)
        idx = (q.range_args[0] // 1000) if q.range_args is not None else 0
        rows = self.rows if idx == 0 else []
        out = []
        for r in rows:
            meta = r["full_response"]["metadata"]
            if sel == OPENAI_SEL:
                out.append({"id": r["id"], "created_at": r["created_at"], "openai": meta.get("openai")})
            elif sel == LLM_SEL:
                out.append({"id": r["id"], "created_at": r["created_at"], "llm": meta.get("llm")})
            else:
                out.append(copy.deepcopy(r))
        return SimpleNamespace(data=out, count=None)


def _costs(fake, path, *, other=None):
    """/costs reads get_supabase_client, /costs/api get_admin_supabase_client
    (C4): the endpoint's own factory answers with ``fake``, the other factory
    with ``other`` (a recorder that must stay untouched)."""
    other = other if other is not None else _TwoPathSupabase([])
    own_admin = path.startswith("/api/v1/admin/costs/api")
    patches = [
        patch("app.api.admin_routes.get_usage_summary", return_value=copy.deepcopy(SUMMARY)),
        patch("app.api.admin_routes.get_tier15_hit_rate", return_value={}),
        patch("app.api.admin_routes.get_tier15_source_hits", return_value={}),
        patch("app.api.admin_routes.get_burn_status", return_value={
            "used": 0, "limit": 2200, "threshold": 1760, "fraction": 0.0, "over_threshold": False}),
        patch("app.api.admin_routes.get_supabase_client", return_value=other if own_admin else fake),
        patch("app.api.admin_routes.get_admin_supabase_client", return_value=fake if own_admin else other),
    ]
    with _all(*patches):
        resp = TestClient(app).get(path, headers={"X-Admin-Key": ADMIN_KEY})
    assert resp.status_code == 200, resp.text[:300]
    return resp.json()


def _assert_g1_aggregate(llm, note, source, as_of):
    assert llm["cost_usd"] == 0.0052, llm.get("cost_usd")
    assert (llm["rows"], llm["rows_with_cost"], llm["rows_partial"], llm["rows_without_cost"]) == (5, 3, 1, 2)
    assert llm["cost_complete"] is False
    assert llm["today_usd"] == 0.004
    assert llm["by_day"][_day(0)] == 0.004 and llm["by_day"][_day(1)] == 0.0012
    assert llm["truncated"] is False
    assert llm["calls"] == 5
    assert llm["prompt_tokens"] == 5000 and llm["completion_tokens"] == 1000
    assert llm["cache_read_tokens"] == 100 and llm["web_search_requests"] == 1
    assert llm["by_provider"] == {"openai": {"calls": 4, "cost_usd": 0.0022},
                                  "anthropic": {"calls": 1, "cost_usd": 0.003}}, llm["by_provider"]
    assert llm["by_model"] == {"gpt-4o-mini": {"calls": 4, "cost_usd": 0.0022},
                               "claude-haiku-5-5": {"calls": 1, "cost_usd": 0.003}}, llm["by_model"]
    assert llm["basis"] == "list_price" and llm["price_table_as_of"] == as_of
    assert llm["note"] == note and llm["source"] == source == "comparisons.full_response.metadata.llm"


@pytest.fixture
def admin_on(monkeypatch):
    monkeypatch.setenv("ADMIN_API_KEY", ADMIN_KEY)
    yield


def test_g1_admin_costs_sums_metadata_llm(monkeypatch, admin_on):
    """RED (G1, AD; C3 / C4 / R-S03-1): ON, /costs carries summary['llm'] summed
    over the persisted metadata.llm rows through its own select string on the
    endpoint's own client."""
    _set_flag(monkeypatch, "true")
    from app.api import admin_routes

    note = getattr(admin_routes, "LLM_COST_NOTE", None)
    assert isinstance(note, str), "admin_routes.LLM_COST_NOTE is missing"
    fake, other = _TwoPathSupabase(_g_rows()), _TwoPathSupabase([])
    body = _costs(fake, "/api/v1/admin/costs", other=other)
    assert "llm" in body, f"summary['llm'] absent under ON; keys={sorted(body)}"
    _assert_g1_aggregate(body["llm"], note, getattr(admin_routes, "LLM_COST_SOURCE", None),
                         _need("PRICE_TABLE_AS_OF"))
    assert LLM_SEL in fake.selects, fake.selects
    assert fake.selects.count(OPENAI_SEL) == 1, fake.selects
    assert other.queries == [], "C4: the llm read must reuse the endpoint's own client"
    assert body["openai"]["cost_usd"] == 0.0022


def test_g2_admin_costs_api_carries_llm_block(monkeypatch, admin_on):
    """RED (G2): ON, /costs/api?days=30 carries body['llm'] (the G1 aggregate)."""
    _set_flag(monkeypatch, "true")
    from app.api import admin_routes

    fake, other = _TwoPathSupabase(_g_rows()), _TwoPathSupabase([])
    body = _costs(fake, "/api/v1/admin/costs/api?days=30", other=other)
    assert "llm" in body, f"body['llm'] absent under ON; keys={sorted(body)}"
    _assert_g1_aggregate(body["llm"], getattr(admin_routes, "LLM_COST_NOTE", None),
                         getattr(admin_routes, "LLM_COST_SOURCE", None), _need("PRICE_TABLE_AS_OF"))
    assert LLM_SEL in fake.selects and other.queries == []


@pytest.mark.parametrize("flag", OFF_VALUES)
def test_g3_flag_off_admin_queries_and_keys_are_base(monkeypatch, admin_on, flag):
    """PIN (G3, kills M26 / M28 and the admin flag-read-not-first mutant): OFF,
    rows carrying metadata.llm: the issued selects are exactly the base list;
    no llm key; zero leaf calls."""
    def run():
        _prime_leaf_state(monkeypatch, flag)
        calls = _leaf_recorders(monkeypatch)
        fake = _TwoPathSupabase(_g_rows())
        body = _costs(fake, "/api/v1/admin/costs")
        assert fake.selects == [OPENAI_SEL, "id"], fake.selects
        assert "llm" not in body
        fake2 = _TwoPathSupabase(_g_rows())
        body2 = _costs(fake2, "/api/v1/admin/costs/api?days=30")
        assert fake2.selects == [OPENAI_SEL], fake2.selects
        assert "llm" not in body2
        assert not _called(calls), _called(calls)

    _isolated(run)


def _drop_volatile(body):
    body = copy.deepcopy(body)
    body.pop("llm", None)
    return body


def test_g4_on_openai_block_identical_to_off(monkeypatch, admin_on):
    """PIN (G4): /costs and /costs/api minus llm are equal between the flag states."""
    out = {}
    for flag in ("false", "true"):
        _set_flag(monkeypatch, flag)
        out[flag] = (_drop_volatile(_costs(_TwoPathSupabase(_g_rows()), "/api/v1/admin/costs")),
                     _drop_volatile(_costs(_TwoPathSupabase(_g_rows()), "/api/v1/admin/costs/api?days=30")))
    assert out["true"] == out["false"]


def test_g5_llm_read_failure_is_unknown_not_zero(monkeypatch, admin_on, caplog):
    """RED (G5, kills M27): ON, the llm JSON path and the blob select raise:
    llm.cost_usd None, rows 0, cost_complete None; the openai block intact; the
    WARNING carries the exception TYPE only."""
    caplog.set_level(logging.WARNING)
    _set_flag(monkeypatch, "true")
    fake = _TwoPathSupabase(_g_rows(), raise_on=(LLM_SEL, BLOB_SEL))
    body = _costs(fake, "/api/v1/admin/costs")
    assert "llm" in body, sorted(body)
    llm = body["llm"]
    assert llm["cost_usd"] is None and llm["rows"] == 0 and llm["cost_complete"] is None
    assert body["openai"]["cost_usd"] == 0.0022 and body["openai"]["rows"] == 5
    msgs = [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING]
    assert any("_LeafBoom" in m and "llm" in m.lower() for m in msgs), msgs
    assert not any(BOOM_TEXT in m for m in msgs), msgs


@pytest.mark.parametrize("flag", [None, "true"])
@pytest.mark.parametrize("path", ["/api/v1/admin/costs", "/api/v1/admin/costs/api"])
def test_g6_admin_key_guard_unchanged(monkeypatch, admin_on, flag, path):
    """PIN (G6): no key -> 403; a wrong key -> 403; both states."""
    _set_flag(monkeypatch, flag)
    client = TestClient(app)
    assert client.get(path).status_code == 403
    assert client.get(path, headers={"X-Admin-Key": "wrong-" + ADMIN_KEY}).status_code == 403


COSTS_HTML = APP_DIR / "static" / "admin" / "costs.html"


def test_g7_costs_html_renders_llm_block_safely():
    """RED (G7 + C6, kills M29): an inert llmKpis container (no grid class, or
    display:none until filled); renderLlmKpis guarded by an api.llm check,
    rendering through fmtUsd and the note; called from load(); the added
    bytes are ASCII (24 non-ASCII bytes at base); cm12's forbidden phrases
    absent."""
    raw = COSTS_HTML.read_bytes()
    html = raw.decode("utf-8")
    tag = re.search(r'<div[^>]*\bid="llmKpis"[^>]*>', html)
    assert tag, 'the container <div id="llmKpis"> is missing'
    t = tag.group(0)
    assert 'class="grid"' not in t or re.search(r"display\s*:\s*none", t), (
        f"C6: the empty container must be inert (no grid class, or display:none): {t}"
    )
    start = html.find("function renderLlmKpis(")
    assert start >= 0, "function renderLlmKpis(api) is missing"
    nxt = [i for i in (html.find("function ", start + 9), html.find("</script>", start)) if i > start]
    body = html[start:min(nxt)] if nxt else html[start:]
    assert re.search(r"if\s*\(.*api\.llm", body), "the render must be guarded by an api.llm check"
    assert "fmtUsd(api.llm.cost_usd" in body
    assert re.search(r'\$\{\s*api\.llm\.note\s*\|\|\s*""\s*\}', body)
    load_at = html.find("async function load()")
    assert load_at >= 0
    load_src = html[load_at:html.find("</script>", load_at)]
    assert re.search(r"renderLlmKpis\(\s*api\s*\)\s*;", load_src), "load() must call renderLlmKpis(api)"
    assert sum(1 for b in raw if b > 127) == 24, "only ASCII may be added to costs.html"
    low = html.lower()
    for bad in ("paid-tier spillover", "total_cost > $0", "billed comparisons", "openai_paid_usd"):
        assert bad not in low


def test_g8_llm_cost_note_text():
    """RED (G8): LLM_COST_NOTE is ASCII and names list price, persisted
    comparisons only, not a bill, llm_spend_ledger and SDK retries;
    OPENAI_COST_NOTE byte-equal to its base literal."""
    from app.api import admin_routes

    assert admin_routes.OPENAI_COST_NOTE == OPENAI_COST_NOTE_BASE
    note = getattr(admin_routes, "LLM_COST_NOTE", None)
    assert isinstance(note, str), "admin_routes.LLM_COST_NOTE is missing"
    assert note.isascii()
    low = note.lower()
    for needle in ("list price", "persisted comparisons only", "not a bill", "llm_spend_ledger",
                   "retried by the sdk"):
        assert needle in low, needle


# ===========================================================================
# H -- migration 050 (BL1 / BL5 / R-S03-3)
# ===========================================================================
MIG_050 = MIGRATIONS_DIR / "050_llm_spend_ledger.sql"
RB_050 = ROLLBACK_DIR / "050_llm_spend_ledger.sql"
TABLE = "public.llm_spend_ledger"


def _require(path):
    assert path.is_file(), f"{path.name} does not exist"
    return read(path)


def _stmts(sql):
    text = code_only(sql)
    text = re.sub(r"'(?:[^']|'')*'", "''", text)
    return [norm(s) for s in text.split(";") if s.strip()]


def _split_top(text):
    out, depth, cur = [], 0, []
    for ch in text:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            out.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    if "".join(cur).strip():
        out.append("".join(cur))
    return [c.strip() for c in out]


def _compact(text):
    return re.sub(r"\s+", "", text.lower())


def test_h1_050_and_rollback_exist_once_and_039_stays_reserved():
    """RED (H1 as amended by BL5): exactly one 050 forward and one rollback;
    039 stays reserved; nothing about 045-049 (PLAN_S81 F4 owns them)."""
    assert sorted(p.name for p in MIGRATIONS_DIR.glob("050_*.sql")) == ["050_llm_spend_ledger.sql"]
    assert sorted(p.name for p in ROLLBACK_DIR.glob("050_*.sql")) == ["050_llm_spend_ledger.sql"]
    assert not list(MIGRATIONS_DIR.glob("039_*")), "039 is reserved"


def test_h2_050_one_transaction_creates_exactly_the_table():
    """RED (H2): one BEGIN / COMMIT; one CREATE TABLE IF NOT EXISTS
    public.llm_spend_ledger whose columns are id, created_at + the leaf's
    SPEND_LEDGER_COLUMNS; the lane / mode / provider / basis CHECK lists;
    cost_usd a nullable numeric(14, 6)."""
    sql = _require(MIG_050)
    stmts = _stmts(sql)
    assert stmts and stmts[0] == "begin" and stmts[-1] == "commit", stmts[:1] + stmts[-1:]
    assert stmts.count("begin") == 1 and stmts.count("commit") == 1
    creates = [s for s in stmts if s.startswith("create table")]
    assert len(creates) == 1 and creates[0].startswith(f"create table if not exists {TABLE} ("), creates
    text = code_only(sql)
    m = re.search(r"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+public\.llm_spend_ledger\s*\(", text, re.I)
    assert m, "CREATE TABLE IF NOT EXISTS public.llm_spend_ledger ( not found"
    depth, i = 1, m.end()
    while depth and i < len(text):
        depth += {"(": 1, ")": -1}.get(text[i], 0)
        i += 1
    cols = {}
    for item in _split_top(text[m.end():i - 1]):
        name = item.split()[0].strip('"').lower()
        cols[name] = item
    assert set(cols) == {"id", "created_at"} | set(_need("SPEND_LEDGER_COLUMNS")), sorted(cols)
    assert "check(lanein('live','escalation','search','offclock'))" in _compact(cols["lane"])
    assert "check(modein('sync','batch'))" in _compact(cols["mode"])
    assert "check(providerin('openai','anthropic'))" in _compact(cols["provider"])
    assert "check(basis='list_price')" in _compact(cols["basis"])
    cost = _compact(cols["cost_usd"])
    assert cost.startswith("cost_usdnumeric(14,6)") and "notnull" not in cost, cols["cost_usd"]
    assert "primarykey" in _compact(cols["id"]) and "gen_random_uuid()" in _compact(cols["id"])


def test_h3_050_is_service_role_only_and_append_only_by_grant():
    """RED (H3 as amended by BL1 / R-S03-3, kills M30 / M30b / M31): RLS on, no
    policy; REVOKE ALL ON TABLE ... FROM PUBLIC, anon, authenticated,
    service_role BEFORE exactly one GRANT SELECT, INSERT to service_role; no
    UPDATE / DELETE / TRUNCATE grant; nothing else touched."""
    stmts = _stmts(_require(MIG_050))
    assert f"alter table {TABLE} enable row level security" in stmts, stmts
    revoke = f"revoke all on table {TABLE} from public, anon, authenticated, service_role"
    assert revoke in stmts, f"BL1: the service_role default grant must be revoked too: {stmts}"
    grants = [s for s in stmts if s.startswith("grant ")]
    assert len(grants) == 1, grants
    assert re.fullmatch(rf"grant select, insert on (table )?{re.escape(TABLE)} to service_role", grants[0]), grants
    assert stmts.index(revoke) < stmts.index(grants[0]), "the REVOKE must precede the GRANT"
    allowed = (
        re.compile(r"begin|commit"),
        re.compile(rf"create table if not exists {re.escape(TABLE)} \(.*\)"),
        re.compile(rf"alter table {re.escape(TABLE)} enable row level security"),
        re.compile(rf"revoke all on table {re.escape(TABLE)} from .+"),
        re.compile(rf"grant select, insert on (table )?{re.escape(TABLE)} to service_role"),
        re.compile(rf"comment on table {re.escape(TABLE)} is ''"),
        re.compile(rf"comment on column {re.escape(TABLE)}\.[a-z_0-9]+ is ''"),
    )
    stray = [s for s in stmts if not any(rx.fullmatch(s) for rx in allowed)]
    assert not stray, stray
    for s in stmts:
        for bad in ("policy", "function", "trigger", "create index", "drop ", "truncate"):
            assert bad not in s, s


def test_h4_050_outside_the_043_fence():
    """RED (H4, kills M32): the 043 deletion fence sees no user / personal
    column in the new table and reports no gap; the scan is not vacuous."""
    from tests import test_migration_043_delete_user_cascade as t043

    sql = _require(MIG_050)
    assert "llm_spend_ledger" in sql
    files = t043.real_forward_files()
    assert any(name == "050_llm_spend_ledger.sql" for name, _ in files)
    tables = t043.fence_user_tables(files)
    assert "llm_spend_ledger" not in tables, tables.get("llm_spend_ledger")
    assert not t043.fence_report(files)["table_gaps"]


def test_h5_050_header_and_rollback():
    """RED (H5): the header says it changes nothing in production, apply any
    time, no flag, the postcheck grid and the rollback path; the rollback drops
    only the table and says destructive."""
    comments = comment_lines(_require(MIG_050))
    low = comments.lower()
    assert "changes nothing in production" in low
    assert "any time" in low
    assert "rollback/050_llm_spend_ledger.sql" in comments
    assert "has_table_privilege" in low and "relrowsecurity" in low
    assert "flag" in low
    rb = _require(RB_050)
    assert _stmts(rb) == ["begin", f"drop table if exists {TABLE}", "commit"], _stmts(rb)
    assert "destructive" in comment_lines(rb).lower()


# ===========================================================================
# I -- the camera merge (IR)
# ===========================================================================
COMPARE_LLM = {
    "schema_version": 1, "calls": 3, "priced_calls": 3, "unpriced_calls": 0,
    "prompt_tokens": 3000, "completion_tokens": 600, "input_tokens": 3000, "output_tokens": 600,
    "cache_read_tokens": 0, "cache_write_5m_tokens": 0, "cache_write_1h_tokens": 0,
    "web_search_requests": 0, "cost_usd": 0.00081, "cost_complete": True,
    "by_provider": {"openai": {"calls": 3, "cost_usd": 0.00081}},
    "by_model": {"gpt-4o-mini": {"provider": "openai", "calls": 3, "prompt_tokens": 3000,
                                 "completion_tokens": 600, "cache_read_tokens": 0, "cost_usd": 0.00081}},
    "basis": "list_price", "price_table_as_of": dict(PRICE_AS_OF),
}
COMPARE_OPENAI = {
    "calls": 3, "priced_calls": 3, "unpriced_calls": 0, "prompt_tokens": 3000, "cached_tokens": 0,
    "completion_tokens": 600, "cost_usd": 0.00081, "cost_complete": True,
    "by_model": {"gpt-4o-mini": {"calls": 3, "prompt_tokens": 3000, "cached_tokens": 0,
                                 "completion_tokens": 600, "cost_usd": 0.00081}},
    "basis": "list_price", "price_table_as_of": "2026-10-08",
}


def _camera(monkeypatch, *, compare_llm=None, vision_model="gpt-4o-mini"):
    """cm15b-shaped: two images, the REAL identify_products dispatches once (500
    / 100 on ``vision_model``); the compare is faked and returns metadata
    (total_cost 0.01, metadata.openai, and metadata.llm when given)."""
    monkeypatch.setenv("OPENAI_MODEL_VISION", vision_model)
    fake = _usage_client(content=VISION_JSON, prompt=500, completion=100)
    monkeypatch.setattr(oai, "client", fake)
    monkeypatch.setattr(content_safety_service, "get_content_safety_service", lambda: _Safety())
    metadata = {"total_cost": 0.01, "query": "Acme Widget vs Globex Gadget",
                "openai": copy.deepcopy(COMPARE_OPENAI)}
    if compare_llm is not None:
        metadata["llm"] = copy.deepcopy(compare_llm)
    compare_result = {"success": True,
                      "products": [{"brand": "Acme", "name": "Widget"}, {"brand": "Globex", "name": "Gadget"}],
                      "metadata": metadata}

    async def _fake_compare(self, *a, **k):
        return copy.deepcopy(compare_result)

    monkeypatch.setattr(image_routes.StructuredComparisonService, "compare_from_text", _fake_compare)
    monkeypatch.setattr(image_routes, "log_search", lambda **kw: _done())
    monkeypatch.setattr(image_routes, "save_comparison_and_track_cohort", lambda **kw: _done())
    files = [("images", (f"p{i}.jpg", JPEG, "image/jpeg")) for i in range(2)]
    resp = TestClient(app, raise_server_exceptions=False).post("/api/v1/image/identify", files=files)
    assert resp.status_code == 200, f"harness: {resp.status_code} {resp.text[:300]}"
    body = resp.json()
    assert body.get("action") == "comparison", f"harness: {body!r}"[:300]
    return body["metadata"], fake


def test_i1_camera_merges_vision_into_metadata_llm(monkeypatch):
    """RED (I1, kills M33): ON, the compare's metadata.llm (3 calls, 0.00081) +
    the vision call (gpt-4o-mini 500 / 100 = 0.000135) -> one merged summary:
    calls 4, cost 0.000945, complete True, openai 4 calls."""
    _set_flag(monkeypatch, "true")
    meta, fake = _camera(monkeypatch, compare_llm=COMPARE_LLM)
    assert fake.chat.completions.create.await_count == 1
    llm = meta.get("llm")
    assert isinstance(llm, dict), f"metadata.llm absent: {sorted(meta)}"
    assert set(llm) == SUMMARY_KEYS, sorted(set(llm) ^ SUMMARY_KEYS)
    assert llm["calls"] == 4 and llm["priced_calls"] == 4
    assert llm["cost_usd"] == pytest.approx(0.000945, abs=1e-9) and llm["cost_complete"] is True
    assert llm["prompt_tokens"] == 3500 and llm["completion_tokens"] == 700
    assert llm["by_provider"]["openai"]["calls"] == 4
    assert llm["by_model"]["gpt-4o-mini"]["calls"] == 4
    assert meta["openai"]["calls"] == 4


@pytest.mark.parametrize("flag", ["false", None])
def test_i2_camera_flag_off_no_metadata_llm(monkeypatch, flag):
    """PIN (I2, kills M34 and the IR flag-read-not-first mutant): OFF, the fake
    compare returns no llm (as the builder would): no metadata.llm, the merged
    metadata.openai as cm15b, zero leaf calls."""
    def body():
        _prime_leaf_state(monkeypatch, flag)
        calls = _leaf_recorders(monkeypatch)
        meta, _ = _camera(monkeypatch)
        assert "llm" not in meta
        assert meta["openai"]["calls"] == 4
        assert meta["openai"]["cost_usd"] == pytest.approx(0.000945, abs=1e-9)
        assert meta["vision_cost"] == pytest.approx(0.000135, abs=1e-9)
        assert not _called(calls), _called(calls)

    _isolated(body)


def test_i3_camera_vision_cost_follows_the_vision_model(monkeypatch):
    """RED (I3): ON, OPENAI_MODEL_VISION=gpt-4o, 500 / 100: vision_cost 0.00225
    and metadata.total_cost round(0.01 + 0.00225, 6)."""
    _set_flag(monkeypatch, "true")
    meta, _ = _camera(monkeypatch, compare_llm=COMPARE_LLM, vision_model="gpt-4o")
    assert meta["vision_cost"] == 0.00225, meta["vision_cost"]
    assert meta["total_cost"] == round(0.01 + 0.00225, 6)


def test_i4_camera_merge_fault_delivers_with_one_warning(monkeypatch, caplog):
    """RED (R-S03-5, IR site): ON, merge_llm_summaries raises -> the camera
    compare still delivers with the merged metadata.openai and vision_cost, and
    exactly one fallback WARNING."""
    caplog.set_level(logging.WARNING)
    _set_flag(monkeypatch, "true")
    mod = _need_leaf()
    _need("merge_llm_summaries")
    monkeypatch.setattr(mod, "merge_llm_summaries", _boom)
    meta, _ = _camera(monkeypatch, compare_llm=COMPARE_LLM)
    assert meta["openai"]["calls"] == 4
    assert meta["vision_cost"] == pytest.approx(0.000135, abs=1e-9)
    _assert_one_fallback_warning(caplog, "IR")


# ===========================================================================
# K / L / BL4 -- static pins
# ===========================================================================
def test_k1_guarded_llm_create_untouched():
    """PIN (K1): sha256 of ast.dump(guarded_llm_create) on CPython 3.12 (S81-04
    re-records it deliberately, R-S03-10)."""
    src = (APP_DIR / "services" / "api_budget_service.py").read_text(encoding="utf-8")
    nodes = [n for n in ast.walk(ast.parse(src))
             if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == "guarded_llm_create"]
    assert len(nodes) == 1
    digest = hashlib.sha256(ast.dump(nodes[0], include_attributes=False).encode("utf-8")).hexdigest()
    assert digest == K1_GUARDED_AST_SHA, digest


def test_k2_openai_pricing_untouched():
    """PIN (K2): sha256 of the LF-normalised openai_pricing.py text."""
    text = (APP_DIR / "services" / "openai_pricing.py").read_bytes().replace(b"\r\n", b"\n")
    assert hashlib.sha256(text).hexdigest() == K2_OPENAI_PRICING_LF_SHA


def test_k3_leaf_has_no_url_or_stray_model_literal():
    """RED (K3 as amended by BL2): no non-docstring string literal in
    llm_pricing.py holds http:// or https:// (T7b); no match of the
    tests/test_model_config.py:135 regex on a non-comment line."""
    assert LEAF_FILE.is_file(), "app/services/llm_pricing.py is missing"
    src = LEAF_FILE.read_text(encoding="utf-8")
    tree = ast.parse(src)
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = getattr(node, "body", [])
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                docstrings.add(id(body[0].value))
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docstrings:
            assert "http://" not in node.value and "https://" not in node.value, node.value
    for lineno, line in enumerate(src.splitlines(), 1):
        if line.lstrip().startswith("#"):
            continue
        assert not STRAY_MODEL_RX.search(line), f"llm_pricing.py:{lineno}: {line.strip()}"


def test_l1_fy25_unit_env_carries_the_flag():
    """RED (R-S03-6 / E1): tests/test_s75_fanout_identity.py UNIT_ENV names
    ENABLE_LLM_LEDGER_V2, so a developer .env carrying the flag cannot move the
    nine FY25 digests."""
    src = (REPO / "tests" / "test_s75_fanout_identity.py").read_text(encoding="utf-8")
    value = None
    for node in ast.parse(src).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "UNIT_ENV"
                                                for t in node.targets):
            value = ast.literal_eval(node.value)
    assert value is not None, "UNIT_ENV not found"
    assert FLAG in value, value


CONSUMERS = (
    "app/services/response_builder.py",
    "app/services/structured_comparison_service.py",
    "app/services/openai_service.py",
    "app/services/model_router_service.py",
    "app/api/image_routes.py",
    "app/api/admin_routes.py",
)


@pytest.mark.parametrize("rel", CONSUMERS)
def test_bl4_consumers_reach_the_leaf_by_module_attribute(rel):
    """RED (BL4): every consumer imports the MODULE (`from app.services import
    llm_pricing as _llm_pricing`) and calls `_llm_pricing.<fn>(...)`; none
    from-imports a function (a recorder on the module then sees every call)."""
    tree = ast.parse((REPO / rel).read_text(encoding="utf-8"))
    aliases = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            assert node.module != "app.services.llm_pricing", f"{rel}: from-import of a leaf function"
            if node.module == "app.services":
                aliases |= {a.asname or a.name for a in node.names if a.name == "llm_pricing"}
        elif isinstance(node, ast.Import):
            aliases |= {a.asname for a in node.names if a.name == "app.services.llm_pricing" and a.asname}
    assert aliases, f"{rel}: no module import of app.services.llm_pricing"
    used = [n for n in ast.walk(tree) if isinstance(n, ast.Attribute)
            and isinstance(n.value, ast.Name) and n.value.id in aliases]
    assert used, f"{rel}: the module alias is never used"


# ===========================================================================
# U6 -- the unclaimed add's own fault row (RED-gate ruling G-3; the one row
# GREEN appends; every row above is byte-identical to the RED-gate file)
# ===========================================================================
def test_u6_unclaimed_add_fault_keeps_the_base_total_with_one_warning(monkeypatch, caplog):
    """PIN (G-3, U6): ON, the named leaf function of the unclaimed add,
    unclaimed_openai_cost_usd (reached by module attribute), raises -> the
    builder still delivers, metadata.total_cost is the base value
    round(total_cost, 6) although an unclaimed priced gpt-4o entry is bound
    (the add would be 0.0045), metadata.llm is still written, and exactly ONE
    '[LLM-LEDGER] ... failed type=_LeafBoom -- base value' WARNING, never the
    exception text. Green at base (no leaf: the base builder, no add)."""
    caplog.set_level(logging.WARNING)
    _set_flag(monkeypatch, "true")
    mod = _leaf()
    if mod is not None:
        assert callable(getattr(mod, "unclaimed_openai_cost_usd", None)), (
            "G-3: the unclaimed add is the named leaf function unclaimed_openai_cost_usd"
        )
        monkeypatch.setattr(mod, "unclaimed_openai_cost_usd", _boom)

    def body():
        ledger = _bind_entries([("gpt-4o", 1000, 200)])
        try:
            result = _builder(total_cost=0.0123456, openai_usage=op.summarize_openai_ledger(ledger))
        except _LeafBoom as exc:
            raise AssertionError("G-3: a raising unclaimed add must fall back to the base value") from exc
        assert result["metadata"]["total_cost"] == round(0.0123456, 6), result["metadata"]["total_cost"]
        if mod is not None:
            assert isinstance(result["metadata"].get("llm"), dict), "metadata.llm does not depend on the add"

    _isolated(body)
    if mod is not None:
        _assert_one_fallback_warning(caplog, "RB unclaimed")


# ===========================================================================
# F1 -- the rebase-round pin rows (RULINGS_FIX1_S81_03 F1-1 / F1-2 / F1-3;
# appended after U6; every row above stays byte-identical)
# ===========================================================================
def test_a9b_sonnet_long_context_boundary_is_200000_prompt_tokens():
    """PIN (A9b, F1-1, gate G-2; kills G2 = the Sonnet boundary 200,000 ->
    100,000): a Sonnet request is flat-priced up to and including 200,000
    prompt tokens and unpriced above it, the count being the WHOLE prompt
    (input + cache read + cache writes): 150000*2 + 1000*10 = 310000 -> 0.31,
    200000*2 + 1000*10 = 410000 -> 0.41, 200,001 -> None, 199,999 input + 2
    cache read -> None."""
    s = "claude-sonnet-5-5"
    assert _price("anthropic", s, input_tokens=150000, output_tokens=1000) == pytest.approx(0.31, abs=1e-12)
    assert _price("anthropic", s, input_tokens=200000, output_tokens=1000) == pytest.approx(0.41, abs=1e-12)
    assert _price("anthropic", s, input_tokens=200001, output_tokens=1000) is None, (
        "G-2: a Sonnet request above 200,000 prompt tokens is unpriced"
    )
    assert _price("anthropic", s, input_tokens=199999, cache_read_tokens=2) is None, (
        "G-2: the boundary counts the whole prompt (199,999 input + 2 cache read = 200,001)"
    )


def _camera_unsuccessful(monkeypatch):
    """I5 harness: the cm15b camera shape (two images, the REAL
    identify_products dispatching once, 500 / 100 on gpt-4o-mini) with a faked
    UNSUCCESSFUL compare result carrying no metadata at all (the shape of the
    orchestrator's failure dicts: success False, a code, a top-level
    total_cost); metering and the failure envelope stay OFF (UNIT_ENV), so the
    route serves the result as action "comparison"."""
    monkeypatch.setenv("OPENAI_MODEL_VISION", "gpt-4o-mini")
    fake = _usage_client(content=VISION_JSON, prompt=500, completion=100)
    monkeypatch.setattr(oai, "client", fake)
    monkeypatch.setattr(content_safety_service, "get_content_safety_service", lambda: _Safety())
    compare_result = {"success": False, "code": "TIMEOUT", "error": "s03 synthetic timeout",
                      "total_cost": 0.01}

    async def _fake_compare(self, *a, **k):
        return copy.deepcopy(compare_result)

    monkeypatch.setattr(image_routes.StructuredComparisonService, "compare_from_text", _fake_compare)
    monkeypatch.setattr(image_routes, "log_search", lambda **kw: _done())
    monkeypatch.setattr(image_routes, "save_comparison_and_track_cohort", lambda **kw: _done())
    files = [("images", (f"p{i}.jpg", JPEG, "image/jpeg")) for i in range(2)]
    resp = TestClient(app, raise_server_exceptions=False).post("/api/v1/image/identify", files=files)
    assert resp.status_code == 200, f"harness: {resp.status_code} {resp.text[:300]}"
    body = resp.json()
    assert body.get("action") == "comparison" and body.get("success") is False, f"harness: {body!r}"[:300]
    return body["metadata"], fake


def test_i5_camera_unsuccessful_compare_without_llm_gets_the_vision_summary(monkeypatch):
    """PIN (I5, F1-2; kills MIc = the camera IR condition's `or` -> `and`):
    ON, an UNSUCCESSFUL compare result carrying no metadata.llm plus the one
    recorded vision call (gpt-4o-mini 500 / 100 = 0.000135) -> metadata.llm is
    the vision summary alone (calls 1, cost 0.000135, the G-4 key set)."""
    _set_flag(monkeypatch, "true")
    _need_leaf()
    meta, fake = _camera_unsuccessful(monkeypatch)
    assert fake.chat.completions.create.await_count == 1
    llm = meta.get("llm")
    assert isinstance(llm, dict), f"F1-2: metadata.llm absent with one recorded vision call: {sorted(meta)}"
    assert set(llm) == SUMMARY_KEYS, sorted(set(llm) ^ SUMMARY_KEYS)
    assert llm["calls"] == 1 and llm["priced_calls"] == 1
    assert llm["cost_usd"] == pytest.approx(0.000135, abs=1e-9) and llm["cost_complete"] is True
    assert llm["prompt_tokens"] == 500 and llm["completion_tokens"] == 100
    assert llm["by_provider"]["openai"]["calls"] == 1
    assert meta["openai"]["calls"] == 1


def _camera_real_compare(monkeypatch, flag):
    """I6 harness (the correctness adversary's probe PD): the REAL
    /image/identify route, the REAL compare (the fan-out harness with the
    distinct-usage client), the REAL identify_products (500 / 100 on
    gpt-4o-mini); the content-safety stub delegates every method it does not
    define to the real service."""
    _set_flag(monkeypatch, flag)
    _pin_default_models(monkeypatch)
    _arm_prod_search_config(monkeypatch)
    monkeypatch.setattr(oai, "client", _vision_client(prompt=500, completion=100, content=VISION_JSON))
    real_safety = content_safety_service.get_content_safety_service()

    class _DelegatingSafety(_Safety):
        def __getattr__(self, name):
            return getattr(real_safety, name)

    monkeypatch.setattr(content_safety_service, "get_content_safety_service", lambda: _DelegatingSafety())
    monkeypatch.setattr(image_routes, "log_search", lambda **kw: _done())
    monkeypatch.setattr(image_routes, "save_comparison_and_track_cohort", lambda **kw: _done())
    sink = {}
    _e2e_spies(monkeypatch, sink)
    fan = _FanOutCounters()
    files = [("images", (f"p{i}.jpg", JPEG, "image/jpeg")) for i in range(2)]
    with _all(*fan.patches(_distinct_client()), *_no_supabase(), *_no_egress()):
        resp = TestClient(app, raise_server_exceptions=False).post("/api/v1/image/identify", files=files)
    assert resp.status_code == 200, f"harness: {resp.status_code} {resp.text[:300]}"
    body = resp.json()
    assert body.get("action") == "comparison" and body.get("success") is True, f"harness: {body!r}"[:300]
    return body["metadata"], sink


def test_i6_camera_real_compare_total_cost_and_llm_mirror_openai(monkeypatch):
    """PIN (I6, F1-3; coverage, correctness MIN-9): ON, the camera route with a
    REAL compare: metadata.total_cost = every compare-ledger entry at list
    price + 8 x 0.001 Serper + 0.006 Tier 1.5 + the 0.000135 vision call =
    0.033699 with the content-keyed fake (F2-1, recorded at HEAD in fix round
    2; the call-index fake's 0.032127 is the historical figure) (no double
    count of the vision call, no unclaimed add from the vision ledger);
    metadata.llm mirrors metadata.openai (12 calls / 0.019699; historical
    0.018127) in the G-4 key set."""
    _need_leaf()
    meta, sink = _camera_real_compare(monkeypatch, "true")
    ledger = sink["ledgers"][-1]
    compare_list = sum(e["cost_usd"] for e in ledger)
    assert len(ledger) == 11 and sink["serper"] == 8, (len(ledger), sink["serper"])
    assert sum(sink["amounts"]) == pytest.approx(0.006, abs=1e-12)
    assert meta["vision_cost"] == pytest.approx(0.000135, abs=1e-12)
    expected = compare_list + 0.001 * sink["serper"] + sum(sink["amounts"]) + meta["vision_cost"]
    assert meta["total_cost"] == pytest.approx(expected, abs=1.5e-6), (meta["total_cost"], expected)
    assert meta["total_cost"] == 0.033699, meta["total_cost"]
    _assert_llm_mirrors_openai(meta["llm"], meta["openai"], "camera real compare")
    assert meta["llm"]["calls"] == meta["openai"]["calls"] == 12
    assert meta["openai"]["cost_usd"] == pytest.approx(0.019699, abs=1e-6)


@pytest.mark.parametrize("flag", [None, "false"])
def test_i6_off_camera_real_compare_total_cost_is_base(monkeypatch, flag):
    """PIN (I6 OFF half, B1 rule: the unit state primed, recorders on every
    leaf function): OFF, the same camera route with a REAL compare ships the
    base total 0.01731 (the B5 REST base 0.017175 + the 0.000135 vision call;
    F2-1: recorded at base 84c861f6 with the same content-keyed fake and equal
    at HEAD; the call-index fake's 0.016769 is the historical figure), no
    metadata.llm, metadata.openai 12 calls, zero leaf calls."""
    def body():
        _prime_leaf_state(monkeypatch, flag)
        calls = _leaf_recorders(monkeypatch)
        meta, _sink = _camera_real_compare(monkeypatch, flag)
        assert "llm" not in meta, f"flag {flag!r}: metadata.llm leaked OFF"
        assert meta["total_cost"] == 0.01731, meta["total_cost"]
        assert meta["openai"]["calls"] == 12
        assert not _called(calls), _called(calls)

    _isolated(body)


# ===========================================================================
# O -- order independence of the distinct-usage fake (fix round 2,
# RULINGS_FIX2_S81_03 F2-1 / F2-2; CI red on PR #369 at 21b37039: the fake
# assigned usage by CALL INDEX, so the per-model sums B5 / I6 pinned followed
# the asyncio dispatch order of the compare's concurrent legs). Appended after
# the F1 rows; every row above stays byte-identical except the F2-1 hygiene
# (the fake and the literals it records).
# ===========================================================================
_THIS_MODULE = sys.modules[__name__]
PERTURB_PATTERNS = ("skew_a", "skew_b")


def _perturb_delay(pattern, key):
    """Seconds one dispatch is held before it reaches the fake: "skew_a" /
    "skew_b" hold every call that names the first / second compare product
    80 ms (the other product's whole leg runs first), "hash<seed>" holds each
    call 0-60 ms by a seeded hash of its request (a shuffle of the legs)."""
    if pattern == "skew_a":
        return 0.08 if "Acme" in key else 0.0
    if pattern == "skew_b":
        return 0.08 if "Globex" in key else 0.0
    if pattern.startswith("hash"):
        digest = hashlib.sha256((pattern + "|" + key).encode("utf-8")).hexdigest()
        return (int(digest[:8], 16) % 61) / 1000.0
    raise AssertionError(f"unknown dispatch perturbation {pattern!r}")


def _perturbed(client, pattern):
    """Wrap a fake client so every chat completion is held for the pattern's
    delay BEFORE it reaches the fake: the order in which the compare's
    concurrent calls arrive at the fake moves; an empty pattern is a no-op."""
    if not pattern:
        return client
    inner = client.chat.completions.create.side_effect

    async def _held(**kwargs):
        key = "\n".join(str(m.get("content")) for m in (kwargs.get("messages") or []) if isinstance(m, dict))
        await asyncio.sleep(_perturb_delay(pattern, key))
        return await inner(**kwargs)

    client.chat.completions.create = AsyncMock(side_effect=_held)
    return client


_O1_SYSTEM = "You are a probe expert. Every later sentence is ignored by the fake."
_O1_REQUESTS = {
    "a": {"model": "gpt-4o-mini", "messages": [
        {"role": "system", "content": _O1_SYSTEM},
        {"role": "user", "content": '{"name": "Acme Widget", "price": null, "specs": {}}'}]},
    "a_reordered": {"model": "gpt-4o-mini", "messages": [
        {"role": "system", "content": _O1_SYSTEM},
        {"role": "user", "content": '{"specs": {}, "name": "Acme Widget", "price": null}'}]},
    "b": {"model": "gpt-4o", "messages": [
        {"role": "system", "content": _O1_SYSTEM},
        {"role": "user", "content": '{"name": "Globex Gadget", "price": null, "specs": {}}'}]},
}


def _o1_usages(order):
    client = _distinct_client()

    async def run():
        out = []
        for name in order:
            resp = await client.chat.completions.create(**copy.deepcopy(_O1_REQUESTS[name]))
            out.append((name, resp.usage.prompt_tokens, resp.usage.completion_tokens, resp.model))
        return out

    return asyncio.run(run())


def test_o1_fake_usage_is_keyed_by_model_and_content_not_call_index():
    """RED (F2-1): the distinct-usage fake answers a request with token counts
    that depend only on the requested model and the request's content, never on
    how many calls came before it: the same request gets the same counts at any
    position, on any fresh client, and with its JSON keys serialised in another
    order (the compare's verdict prompt dumps each product's dict keys in the
    order that product's races finished, measured in fix round 2); two requests
    naming different products on different models get different counts."""
    seen = {}
    for name, prompt, completion, model in (_o1_usages(["a", "b", "a", "a_reordered", "b"])
                                            + _o1_usages(["b", "a_reordered", "b", "a", "a"])):
        seen.setdefault("a" if name == "a_reordered" else name, set()).add((prompt, completion, model))
    assert len(seen["a"]) == 1, f"F2-1: one request, several usages {sorted(seen['a'])} (call-index usage)"
    assert len(seen["b"]) == 1, f"F2-1: one request, several usages {sorted(seen['b'])} (call-index usage)"
    (pa, ca, ma), = seen["a"]
    (pb, cb, mb), = seen["b"]
    assert (ma, mb) == ("gpt-4o-mini", "gpt-4o")
    assert pa != pb and ca != cb, (pa, ca, pb, cb)


def _order_view(meta):
    view = {key: meta.get(key) for key in ("openai", "total_cost", "serper_calls", "gpt_calls")}
    if "llm" in meta:
        view["llm"] = meta["llm"]
    return view


@pytest.mark.parametrize("pattern", PERTURB_PATTERNS)
@pytest.mark.parametrize("flag", ["false", "true"])
@pytest.mark.parametrize("path", ["rest", "stream"])
@pytest.mark.asyncio
async def test_o2_compare_cost_figures_do_not_follow_the_dispatch_order(monkeypatch, path, flag, pattern):
    """RED (F2-2, the CI-red reproduction): the REST compare and the stream
    complete payload carry the same metadata.openai, metadata.total_cost,
    serper_calls, gpt_calls (and, ON, metadata.llm) when the compare's
    concurrent LLM legs reach the fake in a perturbed order as when they do not.
    At 21b37039 a skew moved gpt-4o's completion sum 690 -> 678 and
    metadata.openai.cost_usd 0.017992 -> 0.017719 (the GitHub runner's 684 /
    0.017855 is the same class)."""
    _set_flag(monkeypatch, flag)
    run = _rest if path == "rest" else _stream
    plain, plain_client = await run(monkeypatch, _distinct_client())
    held, held_client = await run(monkeypatch, _perturbed(_distinct_client(), pattern))
    assert plain_client.chat.completions.create.await_count == 11
    assert held_client.chat.completions.create.await_count == 11
    assert _order_view(held["metadata"]) == _order_view(plain["metadata"]), (
        f"F2-2: the {path} cost figures followed the dispatch order ({pattern}, flag {flag!r})"
    )


@pytest.mark.parametrize("pattern", PERTURB_PATTERNS)
@pytest.mark.parametrize("flag", [None, "true"])
def test_o3_camera_real_compare_cost_figures_do_not_follow_the_dispatch_order(monkeypatch, flag, pattern):
    """RED (F2-2, the I6 shape): the camera route with a REAL compare carries
    the same metadata.openai, metadata.total_cost (and, ON, metadata.llm) when
    the compare's legs reach the fake in a perturbed order. At 21b37039 a skew
    moved the I6 ON total 0.032127 -> 0.031854 (the runner's 0.03199 is the
    same class)."""
    plain, _ = _camera_real_compare(monkeypatch, flag)
    real_factory = _distinct_client
    monkeypatch.setattr(_THIS_MODULE, "_distinct_client", lambda: _perturbed(real_factory(), pattern))
    held, _ = _camera_real_compare(monkeypatch, flag)
    assert _order_view(held) == _order_view(plain), (
        f"F2-2: the camera cost figures followed the dispatch order ({pattern}, flag {flag!r})"
    )
