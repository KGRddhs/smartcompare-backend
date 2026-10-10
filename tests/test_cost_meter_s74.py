"""COST-METER (#66, punch list G12 / UI-8) -- RED pins, session 75.

Spec: docs/investigations/2026-10-08-session-74-state/specs/COST_METER_SPEC.md
section 4.1 (nodes cm01-cm12) as amended by FABLE_RULINGS_COST_METER.md CM1-CM12
(cm13/cm14 end-to-end from CM4; the camera, recorder-log and share pins from
CM9/CM10/CM11). Every docstring names its spec row and ruling; every expected
cost value was re-derived in Python 3.12.9 on the pinned venv (the arithmetic
is written in the docstring that uses it).

Truth at main 4c0f3c99 (anchor 49883e84 + 3 lines in admin_routes.py):
``/api/v1/admin/costs`` selects a non-existent ``comparisons.metadata`` column
(admin_routes.py:133) so the OpenAI figure reads 0 for every month; the
pipeline records no model id or token count anywhere (``guarded_llm_create``,
api_budget_service.py:952-1025, reads nothing from ``response.usage``); the
``metadata.total_cost`` it does write prices every model at gpt-4o-mini rates.

Design under test (spec section 2): a stdlib-only leaf
``app/services/openai_pricing.py`` (EXACT-key price table, ``price_row``,
``list_price_usd``, a per-request ContextVar ledger ``start_openai_ledger`` /
``record_openai_response`` / ``summarize_openai_ledger``), recorded at BOTH
dispatch branches of ``guarded_llm_create``, summarised into the additive
``metadata.openai`` key by ``build_comparison_response(openai_usage=...)``,
and read back by the two admin endpoints through a paged JSON-path select.

Mutants the GREEN mutation check must kill (spec 4.3 + CM4), named on the
nodes that kill them:
  M1 delete the recorder call on the flag-OFF branch        -> cm03
  M2 delete the recorder call on the flag-ON branch         -> cm04
  M3 unknown-model cost 0.0 instead of None                 -> cm02, cm06
  M4 dashboard cost_usd defaults to 0 instead of None       -> cm09, cm11
  M5 delete start_openai_ledger() at the compare_from_text entry  -> cm13
  M6 delete start_openai_ledger() at the streaming entry          -> cm14
  M7 _build_partial_response without openai_usage=           -> cm17 (G9)
  M13 the camera route overwriting instead of merging        -> cm15b (G5)

Post-adversary fix round (rulings X1-X11), the adversary mutant shapes each
node is RED on:
  MA  merge_openai_summaries cost_complete `and` -> `or`     -> cm15c (X11)
  A1  the recorder keys on response.model                    -> cm19 (X8)
  A6  the paged read de-duplicates by created_at             -> cm10c (X9)
  A7  the owner history view strips metadata.openai          -> cm18 (X5)
  A9  fmtUsd sends only undefined to n/a (null -> $0)        -> cm12 (X3)
  A14 the share strip mutates the stored dict in place       -> cm16 (X4)
  A19 the count query executes inline on the loop           -> cm10e (X7)
  and on the GREEN bytes: cm12 (X1, the page renders api.note), cm08 / cm09 /
  cm11 (X2, partial independent of cost; cost_complete always present),
  cm05b (X6, an unreadable usage records an UNPRICED entry).

Hermetic: fake Supabase builders, fake OpenAI clients, counting provider stubs,
no socket. Pure ASCII, LF. No credential-shaped literal anywhere.
"""
from __future__ import annotations

import asyncio
import contextvars
import copy
import functools
import importlib
import logging
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api import image_routes
from app.main import app
from app.middleware.rate_limiter import limiter
from app.services import api_budget_service as abs_mod
from app.services import content_safety_service
from app.services import openai_service as oai
from app.services import price_service as price_mod
from app.services import structured_comparison_service as scs_mod
from app.services.response_builder import build_comparison_response
from tests.test_openai_breaker import (
    _FanOutCounters,
    _all,
    _arm_prod_search_config,
    _run_compare,
    _run_stream,
)
from tests.test_response_builder_phase1_none_guard import (
    _minimal_product_data,
    _minimal_scoring,
)

ADMIN_KEY = "test-admin-key"
PRICING_MODULE = "app.services.openai_pricing"
PAGE = 1000
JPEG = b"\xff\xd8" + b"\x00" * 64

# CM7 -- the EXACT keys and USD-per-1M rates the owner read on 2026-10-08.
GPT4O_RATES = {"input": 2.50, "cached_input": 1.25, "output": 10.00}
MINI_RATES = {"input": 0.15, "cached_input": 0.075, "output": 0.60}
EXACT_KEYS = {
    "gpt-4o": GPT4O_RATES,
    "gpt-4o-2024-08-06": GPT4O_RATES,
    "gpt-4o-2024-11-20": GPT4O_RATES,
    "gpt-4o-mini": MINI_RATES,
    "gpt-4o-mini-2024-07-18": MINI_RATES,
}
# CM7 negatives: priced by nothing, None never 0.
UNPRICED_IDS = (
    "gpt-4o-2024-05-13",
    "gpt-4o-realtime-preview",
    "gpt-4o-audio-preview",
    "gpt-4o-mini-tts",
    "gpt-4o-mini-audio-preview",
    "gpt-5",
    "gpt-5-mini",
    "gpt-4.1",
    "",
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _pricing():
    """Import the leaf lazily so each node reports ITS OWN reason (ImportError
    on cm01-cm06, the pinned-defect assertion on cm08-cm12), never a
    collection error for the whole file."""
    return importlib.import_module(PRICING_MODULE)


def _done(value=None):
    """A finished coroutine for fire_and_forget stand-ins."""

    async def _c():
        return value

    return _c()


def _usage(prompt=1000, completion=200, cached=0):
    return SimpleNamespace(
        prompt_tokens=prompt,
        completion_tokens=completion,
        total_tokens=(prompt or 0) + (completion or 0),
        prompt_tokens_details=SimpleNamespace(cached_tokens=cached),
    )


def _response(model, content="{}", usage=None):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content), finish_reason="stop")],
        usage=_usage() if usage is None else usage,
        model=model,
    )


def _client_returning(response):
    client = MagicMock()
    client.chat.completions.create = AsyncMock(return_value=response)
    return client


# One JSON body every chat call in a compare can swallow: the specs filter keeps
# the meta keys brand/model (extraction_service.extract_specs), and the verdict
# parser reads winner_index / pros / cons with .get defaults.
_LLM_JSON = (
    '{"brand": "Acme", "model": "Widget", "winner_index": 0, '
    '"winner_declaration": "Acme Widget wins", '
    '"verdict": "Acme Widget is better overall.", "reason": "More data.", '
    '"product_0_pros": ["a"], "product_0_cons": ["b"], '
    '"product_1_pros": ["c"], "product_1_cons": ["d"], '
    '"key_differences": [], "tradeoffs": []}'
)


def _usage_client(content=_LLM_JSON, prompt=1000, completion=200):
    """A fake AsyncOpenAI whose every chat completion carries usage and echoes
    the REQUESTED model id; moderations.create answers 'not flagged'."""
    client = MagicMock()

    async def _create(**kwargs):
        return _response(kwargs.get("model"), content, _usage(prompt, completion, 0))

    client.chat.completions.create = AsyncMock(side_effect=_create)
    flagged = MagicMock()
    flagged.flagged = False
    moderation = MagicMock()
    moderation.results = [flagged]
    client.moderations.create = AsyncMock(return_value=moderation)
    return client


def _pin_default_models(monkeypatch):
    """Model ids are env-overridable per call (model_config); pin the defaults
    so the price lookups are deterministic whatever the shell carries."""
    monkeypatch.setenv("OPENAI_MODEL_VERDICT", "gpt-4o")
    monkeypatch.setenv("OPENAI_MODEL_STANDARD", "gpt-4o-mini")
    monkeypatch.setenv("OPENAI_MODEL_VISION", "gpt-4o-mini")
    monkeypatch.setenv("OPENAI_MODEL_CRITIC", "gpt-4o-mini")
    monkeypatch.delenv("ENABLE_LLM_PREFLIGHT_BREAKER", raising=False)
    monkeypatch.delenv("ENABLE_SELF_CRITIQUE", raising=False)


# 1000/200/0 tokens per call under CM7: gpt-4o (1000*2.50 + 200*10.00)/1e6 =
# 0.0045; gpt-4o-mini (1000*0.15 + 200*0.60)/1e6 = 0.00027.
_UNIT_COST_1000_200 = {"gpt-4o": 0.0045, "gpt-4o-mini": 0.00027}


# ---------------------------------------------------------------------------
# fake Supabase (the paged admin read, CM2 / CM5)
# ---------------------------------------------------------------------------
_IN_OFFLOAD = contextvars.ContextVar("cm_in_offload", default=False)


def _row(rid, created_at, openai=None, legacy_total_cost=None):
    meta = {}
    if legacy_total_cost is not None:
        meta["total_cost"] = legacy_total_cost
    if openai is not None:
        meta["openai"] = openai
    return {"id": rid, "created_at": created_at, "full_response": {"metadata": meta}}


def _openai_of(row):
    return (((row.get("full_response") or {}).get("metadata")) or {}).get("openai")


class _Query:
    """Chainable stand-in for the postgrest select builder: every filter /
    order / range / limit returns self and is recorded; execute() asks the
    fake client for the page."""

    def __init__(self, fake, select_args, select_kwargs):
        self._fake = fake
        self.select_args = select_args
        self.select_kwargs = select_kwargs
        self.order_calls = []
        self.range_args = None
        self.limit_arg = None
        self.filters = []
        self.in_offload = None

    def _f(self, _method, *a, **k):
        # X10 (E10): the filter METHOD name is recorded with its args, so
        # `.gte("created_at", ...)` is told apart from `.gt` / `.eq`.
        self.filters.append((_method,) + tuple(a))
        return self

    gte = functools.partialmethod(_f, "gte")
    lte = functools.partialmethod(_f, "lte")
    gt = functools.partialmethod(_f, "gt")
    lt = functools.partialmethod(_f, "lt")
    eq = functools.partialmethod(_f, "eq")
    neq = functools.partialmethod(_f, "neq")

    def order(self, *a, **k):
        self.order_calls.append((a, k))
        return self

    def range(self, lo, hi):
        self.range_args = (int(lo), int(hi))
        return self

    def limit(self, n):
        self.limit_arg = int(n)
        return self

    def execute(self):
        return self._fake._execute(self)


class _Table:
    def __init__(self, fake):
        self._fake = fake

    def select(self, *a, **k):
        return _Query(self._fake, a, k)


class _FakeSupabase:
    """``pages``: lists of blob-shaped rows. A select carrying the JSON path
    (``->``) is answered in the JSON-path shape PostgREST returns for
    ``full_response->metadata->openai`` (key ``openai``, null when the path is
    absent); any other select is answered in the blob shape. ``count="exact"``
    selects answer the count query. Page i is whatever ``range`` starts at
    i*1000 (a limit-only chain reads page 0)."""

    def __init__(self, pages, count=None, json_path_error=None):
        self.pages = [list(p) for p in pages]
        self.count = sum(len(p) for p in pages) if count is None else count
        self.json_path_error = json_path_error
        self.queries = []

    def table(self, name):
        self.last_table = name
        return _Table(self)

    @property
    def page_queries(self):
        return [q for q in self.queries if not q.select_kwargs.get("count")]

    @property
    def range_args(self):
        return [q.range_args for q in self.page_queries if q.range_args is not None]

    def _execute(self, q):
        q.in_offload = _IN_OFFLOAD.get()
        self.queries.append(q)
        if q.select_kwargs.get("count"):
            return SimpleNamespace(data=[], count=self.count)
        sel = " ".join(str(a) for a in q.select_args)
        json_path = "->" in sel
        if json_path and self.json_path_error is not None:
            raise self.json_path_error
        idx = (q.range_args[0] // PAGE) if q.range_args is not None else 0
        rows = self.pages[idx] if idx < len(self.pages) else []
        if json_path:
            data = [{"id": r["id"], "created_at": r["created_at"], "openai": _openai_of(r)} for r in rows]
        else:
            data = [copy.deepcopy(r) for r in rows]
        return SimpleNamespace(data=data, count=None)


def _stamp(days_ago=0):
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()


def _day(days_ago=0):
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).strftime("%Y-%m-%d")


def _rows_abcd():
    """CM1 fixture, OFF the rounding boundary: A 0.004 (today), B legacy
    (total_cost only, two days ago), C 0.0012 partial (yesterday), D 0.0
    complete (yesterday). Sum 0.004 + 0.0012 + 0.0 = 0.0052;
    round(0.0052 / 3, 6) = 0.001733; round(30.00 + 0.0052, 2) = 30.01
    (the spec's 0.005 fixture gave round(30.005, 2) == 30.0 -- review F1)."""
    return [
        _row("row-a", _stamp(0), openai={"cost_usd": 0.004, "cost_complete": True, "calls": 2,
                                          "basis": "list_price"}),
        _row("row-b", _stamp(2), legacy_total_cost=0.01),
        _row("row-c", _stamp(1), openai={"cost_usd": 0.0012, "cost_complete": False, "calls": 3}),
        _row("row-d", _stamp(1), openai={"cost_usd": 0.0, "cost_complete": True, "calls": 0}),
    ]


def _row_e():
    """X2 fixture row E: an ALL-unpriced compare (every call on an id outside
    the price table): cost_usd None, cost_complete False, 3 calls on gpt-5.
    It is BOTH rows_without_cost and rows_partial (the window's figure is
    then a lower bound and the endpoint says cost_complete False)."""
    return _row("row-e", _stamp(1), openai={
        "cost_usd": None, "cost_complete": False, "calls": 3,
        "by_model": {"gpt-5": {"calls": 3, "cost_usd": None}},
    })


def _rows_abcde():
    """CM1's A/B/C/D plus X2's row E: cost_usd 0.0052 (E adds no cost); rows
    5; rows_with_cost 3; rows_partial 2 (C and E); rows_without_cost 2 (B and
    E); calls 2 + 3 + 0 + 3 = 8."""
    return _rows_abcd() + [_row_e()]


def _bulk_page(prefix, n, cost=0.001):
    return [
        _row(f"{prefix}-{i}", _stamp(1), openai={"cost_usd": cost, "cost_complete": True, "calls": 1})
        for i in range(n)
    ]


def _seq_rows(prefix, n, base, start=0, cost=0.001):
    """Rows with DISTINCT created_at values (base + start + i microseconds):
    unlike _bulk_page (one _stamp(1) per row, which collides at the Windows
    clock resolution), a de-dup keyed on created_at cannot pass by accident."""
    return [
        _row(f"{prefix}-{i}", (base + timedelta(microseconds=start + i)).isoformat(),
             openai={"cost_usd": cost, "cost_complete": True, "calls": 1})
        for i in range(n)
    ]


SUMMARY = {"providers": {}, "circuit_breakers": {}}


def _admin_patches(fake, *, admin_too=False):
    """The Redis-backed helpers the two cost endpoints call, stubbed; the
    Supabase getter replaced by ``fake``. CM3: ``api_costs`` keeps
    ``get_supabase_client`` -- cm08-cm10 patch THAT name only. costs_api
    (cm11) uses the admin getter today, so it patches both."""
    patches = [
        patch("app.api.admin_routes.get_usage_summary", return_value=copy.deepcopy(SUMMARY)),
        patch("app.api.admin_routes.get_tier15_hit_rate", return_value={}),
        patch("app.api.admin_routes.get_tier15_source_hits", return_value={}),
        patch("app.api.admin_routes.get_burn_status", return_value={
            "used": 0, "limit": 2200, "threshold": 1760, "fraction": 0.0, "over_threshold": False,
        }),
        patch("app.api.admin_routes.get_supabase_client", return_value=fake),
    ]
    if admin_too:
        patches.append(patch("app.api.admin_routes.get_admin_supabase_client", return_value=fake))
    return patches


def _get_costs(fake, path="/api/v1/admin/costs", admin_too=False):
    with _all(*_admin_patches(fake, admin_too=admin_too)):
        resp = TestClient(app).get(path, headers={"X-Admin-Key": ADMIN_KEY})
    return resp


@pytest.fixture
def admin_env(monkeypatch):
    """Admin key present; the 30/minute limiter off (this file plus the
    neighbouring dashboard tests share one in-process bucket)."""
    monkeypatch.setenv("ADMIN_API_KEY", ADMIN_KEY)
    monkeypatch.setattr(limiter, "enabled", False)
    monkeypatch.delenv("ENABLE_SYNC_DB_OFFLOAD", raising=False)
    yield


# ===========================================================================
class TestCostMeterS74:
    # -------------------------------------------------------------- cm01
    def test_cm01_price_table_rates_as_of_2026_10_08(self):
        """Spec 4.1 cm01 + CM7. EXACT keys only: gpt-4o, gpt-4o-2024-08-06,
        gpt-4o-2024-11-20 = 2.50 / 1.25 / 10.00; gpt-4o-mini,
        gpt-4o-mini-2024-07-18 = 0.15 / 0.075 / 0.60 USD per 1M. Every other
        id (the 2024-05-13 snapshot, realtime/audio/tts, gpt-5 family, gpt-4.1)
        is None, never 0. The module cites the price URL and the read date.
        RED: ImportError (no app.services.openai_pricing)."""
        p = _pricing()
        assert p.PRICE_TABLE_AS_OF == "2026-10-08"
        for model, rates in EXACT_KEYS.items():
            assert p.PRICE_USD_PER_1M[model] == rates, model
            row = p.price_row(model)
            assert row is not None, model
            assert row["input"] == rates["input"]
            assert row["cached_input"] == rates["cached_input"]
            assert row["output"] == rates["output"]
        assert p.price_row("gpt-4o-2024-11-20")["input"] == 2.50
        assert p.price_row("gpt-4o-mini-2024-07-18")["output"] == 0.60
        assert set(p.PRICE_USD_PER_1M) == set(EXACT_KEYS), "EXACT keys only (CM7)"
        for model in UNPRICED_IDS:
            assert p.price_row(model) is None, f"{model!r} must be unpriced (None), never 0"
        assert p.price_row(None) is None
        source = Path(p.__file__).read_text(encoding="utf-8")
        assert "openai.com/api/pricing" in source, "module comment must cite the price URL"
        assert "2026-10-08" in source, "module comment must carry the read date"

    # -------------------------------------------------------------- cm02
    def test_cm02_list_price_uses_cached_and_uncached_input(self):
        """Spec 4.1 cm02 + CM7. gpt-4o 1000 prompt / 400 cached / 200 completion:
        uncached = 1000 - 400 = 600; (600*2.50 + 400*1.25 + 200*10.00)/1e6 =
        (1500 + 500 + 2000)/1e6 = 0.004. gpt-4o-mini, same tokens:
        (600*0.15 + 400*0.075 + 200*0.60)/1e6 = (90 + 30 + 120)/1e6 = 0.00024.
        cached > prompt clamps uncached to 0: gpt-4o 100/400/0 ->
        (0*2.50 + 400*1.25 + 0)/1e6 = 0.0005. Unknown model -> None (M3);
        a None token count -> None. RED: ImportError."""
        p = _pricing()
        assert p.list_price_usd("gpt-4o", 1000, 200, 400) == pytest.approx(0.004, rel=1e-9)
        assert p.list_price_usd("gpt-4o-mini", 1000, 200, 400) == pytest.approx(0.00024, rel=1e-9)
        assert p.list_price_usd("gpt-4o-2024-11-20", 1000, 200, 400) == pytest.approx(0.004, rel=1e-9)
        assert p.list_price_usd("gpt-4o", 100, 0, 400) == pytest.approx(0.0005, rel=1e-9)
        unknown = p.list_price_usd("gpt-5", 1000, 200, 400)
        assert unknown is None, f"unknown model must price to None, not {unknown!r} (mutant M3)"
        assert p.list_price_usd("gpt-4o-2024-05-13", 1000, 200, 0) is None
        assert p.list_price_usd("gpt-4o", None, 200, 0) is None
        assert p.list_price_usd("gpt-4o", 1000, None, 0) is None
        assert p.list_price_usd("gpt-4o", 0, 0, 0) == 0.0

    # -------------------------------------------------------------- cm03
    @pytest.mark.asyncio
    async def test_cm03_chokepoint_records_model_and_usage(self, monkeypatch):
        """Spec 4.1 cm03 (flag OFF branch, api_budget_service.py:978). One
        dispatch through guarded_llm_create with usage 1000/200 and 400 cached
        tokens records ONE ledger entry {model gpt-4o, prompt 1000, completion
        200, cached 400, cost_usd 0.004} ((600*2.50 + 400*1.25 + 200*10)/1e6);
        the create was still awaited once with store=False (U3c kept).
        Kills mutant M1. RED: ImportError (start_openai_ledger)."""
        monkeypatch.delenv("ENABLE_LLM_PREFLIGHT_BREAKER", raising=False)
        p = _pricing()
        ledger = p.start_openai_ledger()
        assert ledger == []
        client = _client_returning(_response("gpt-4o", "{}", _usage(1000, 200, 400)))

        out = await abs_mod.guarded_llm_create(client, model="gpt-4o", messages=[])

        assert out is client.chat.completions.create.return_value
        assert client.chat.completions.create.await_count == 1
        assert client.chat.completions.create.await_args.kwargs["store"] is False
        assert len(ledger) == 1, f"flag-OFF dispatch recorded {len(ledger)} entries (mutant M1)"
        entry = ledger[0]
        assert entry["model"] == "gpt-4o"
        assert entry["prompt_tokens"] == 1000
        assert entry["completion_tokens"] == 200
        assert entry["cached_tokens"] == 400
        assert entry["cost_usd"] == pytest.approx(0.004, rel=1e-9)
        # The same list object the ContextVar holds (spec 2.1: child tasks append
        # into the parent's list).
        assert p._LEDGER.get() is ledger

    # -------------------------------------------------------------- cm04
    @pytest.mark.asyncio
    async def test_cm04_chokepoint_records_on_breaker_branch(self, monkeypatch):
        """Spec 4.1 cm04 (flag ON branch, api_budget_service.py:985). With the
        preflight breaker enabled and the snapshot patched CLOSED/0 (admitted,
        outcome does not matter: no Redis write), the same dispatch records the
        same single entry. Kills mutant M2. RED: ImportError."""
        monkeypatch.setenv("ENABLE_LLM_PREFLIGHT_BREAKER", "true")
        p = _pricing()
        ledger = p.start_openai_ledger()
        client = _client_returning(_response("gpt-4o-mini", "{}", _usage(1000, 200, 400)))

        with patch.object(abs_mod, "_openai_breaker_snapshot", return_value=(abs_mod.CB_CLOSED, 0.0, 0)):
            out = await abs_mod.guarded_llm_create(client, model="gpt-4o-mini", messages=[])

        assert out is client.chat.completions.create.return_value
        assert client.chat.completions.create.await_count == 1
        assert client.chat.completions.create.await_args.kwargs["store"] is False
        assert len(ledger) == 1, f"flag-ON dispatch recorded {len(ledger)} entries (mutant M2)"
        entry = ledger[0]
        assert entry["model"] == "gpt-4o-mini"
        assert entry["prompt_tokens"] == 1000
        assert entry["completion_tokens"] == 200
        assert entry["cached_tokens"] == 400
        # (600*0.15 + 400*0.075 + 200*0.60)/1e6 = 0.00024
        assert entry["cost_usd"] == pytest.approx(0.00024, rel=1e-9)

    # -------------------------------------------------------------- cm05
    @pytest.mark.asyncio
    async def test_cm05_recorder_never_raises_and_noops_without_ledger(self, monkeypatch):
        """Spec 4.1 cm05 + CM8. (a) ContextVar None: the dispatch records
        nothing and returns the response. (b) A MagicMock usage (the #89
        fixture class) records prompt/completion None and cost None; the
        summary says priced_calls 0, cost_usd None, cost_complete False.
        (c) A raising create leaves the ledger empty. (d) CM8: a None
        cached_tokens counts as 0 -> a PRICED entry: gpt-4o 1000/200/None ->
        (1000*2.50 + 200*10.00)/1e6 = 0.0045, cached 0. RED: ImportError."""
        monkeypatch.delenv("ENABLE_LLM_PREFLIGHT_BREAKER", raising=False)
        p = _pricing()

        # (a) no ledger bound
        p._LEDGER.set(None)
        client = _client_returning(_response("gpt-4o", "{}", _usage(1000, 200, 400)))
        out = await abs_mod.guarded_llm_create(client, model="gpt-4o", messages=[])
        assert out is client.chat.completions.create.return_value
        assert p._LEDGER.get() is None
        assert p.summarize_openai_ledger(None) is None

        # (b) MagicMock usage -> unpriced entry
        ledger = p.start_openai_ledger()
        mock_resp = MagicMock()
        mock_resp.usage = MagicMock()
        client = _client_returning(mock_resp)
        await abs_mod.guarded_llm_create(client, model="gpt-4o", messages=[])
        assert len(ledger) == 1
        assert ledger[0]["model"] == "gpt-4o"
        assert ledger[0]["prompt_tokens"] is None
        assert ledger[0]["completion_tokens"] is None
        assert ledger[0]["cached_tokens"] in (None, 0)
        assert ledger[0]["cost_usd"] is None
        summary = p.summarize_openai_ledger(ledger)
        assert summary["calls"] == 1
        assert summary["priced_calls"] == 0
        assert summary["unpriced_calls"] == 1
        assert summary["cost_usd"] is None
        assert summary["cost_complete"] is False

        # (c) a raising create records nothing
        ledger = p.start_openai_ledger()
        client = MagicMock()
        client.chat.completions.create = AsyncMock(side_effect=RuntimeError("boom"))
        with pytest.raises(RuntimeError):
            await abs_mod.guarded_llm_create(client, model="gpt-4o", messages=[])
        assert ledger == []

        # (d) CM8: None cached_tokens counts as 0, entry is priced
        ledger = p.start_openai_ledger()
        usage = SimpleNamespace(prompt_tokens=1000, completion_tokens=200, total_tokens=1200,
                                prompt_tokens_details=SimpleNamespace(cached_tokens=None))
        client = _client_returning(_response("gpt-4o", "{}", usage))
        await abs_mod.guarded_llm_create(client, model="gpt-4o", messages=[])
        assert len(ledger) == 1, "a None cached count must not drop the call (CM8 / review F10)"
        assert ledger[0]["cached_tokens"] == 0
        assert ledger[0]["prompt_tokens"] == 1000
        assert ledger[0]["cost_usd"] == pytest.approx(0.0045, rel=1e-9)

        # (e) usage None -> tokens None, cost None, call still counted
        ledger = p.start_openai_ledger()
        client = _client_returning(SimpleNamespace(choices=[], usage=None, model="gpt-4o"))
        await abs_mod.guarded_llm_create(client, model="gpt-4o", messages=[])
        assert len(ledger) == 1
        assert ledger[0]["prompt_tokens"] is None
        assert ledger[0]["cost_usd"] is None

    # -------------------------------------------------------------- cm05b
    def test_cm05b_recorder_logs_exception_type_name_only(self, caplog):
        """CM10 (review F12). A usage object whose attribute access raises
        makes the never-raising recorder log the exception TYPE NAME only --
        no str(e), no response text (U8d / log_scrub posture). RED:
        ImportError.

        X6 (E6, design adopted): the call is NOT dropped -- the recorder
        appends an UNPRICED entry {requested model, tokens None, cost None},
        so a malformed response counts as a call with cost_complete False.
        X10 (E10): the ledger is bound with a token and reset afterwards (no
        ledger leaks into the pytest main-thread context). RED on the GREEN
        bytes: the call vanished (len(ledger) == 0)."""
        p = _pricing()
        secret = "resp-body-" + "do-not-log-" + "cm05b"

        class _Explosive:
            def __getattr__(self, name):
                raise ValueError(secret)

        ledger = []
        token = p._LEDGER.set(ledger)
        try:
            caplog.set_level(logging.DEBUG)
            p.record_openai_response("gpt-4o", SimpleNamespace(usage=_Explosive(), choices=[]))
        finally:
            p._LEDGER.reset(token)
        assert p._LEDGER.get() is not ledger, "harness: the ledger must not outlive the node (X10)"
        texts = [r.getMessage() for r in caplog.records]
        assert any("ValueError" in t for t in texts), (
            f"the recorder must log the exception type name; got {texts!r}"
        )
        assert secret not in caplog.text, "the recorder logged the exception text"
        assert len(ledger) == 1 and ledger[0]["cost_usd"] is None and ledger[0]["model"] == "gpt-4o", (
            f"an unreadable usage must record ONE unpriced call, not drop it (X6); ledger={ledger!r}"
        )
        assert ledger[0]["prompt_tokens"] is None
        assert ledger[0]["completion_tokens"] is None
        assert ledger[0]["cached_tokens"] is None
        summary = p.summarize_openai_ledger(ledger)
        assert summary["calls"] == 1
        assert summary["unpriced_calls"] == 1
        assert summary["cost_usd"] is None
        assert summary["cost_complete"] is False

    # -------------------------------------------------------------- cm06
    @pytest.mark.asyncio
    async def test_cm06_summary_null_vs_zero(self, monkeypatch):
        """Spec 4.1 cm06 + CM7. Empty ledger -> calls 0, cost_usd 0.0 (a TRUE
        zero: fully cached compare), cost_complete True; summarize(None) is
        None; mixed priced (gpt-4o 1000/200/400 = 0.004) + unknown-model
        (gpt-5, cost None) entries -> cost_usd 0.004 (the priced sum, rounded
        to 6 dp), cost_complete False, by_model keyed by BOTH ids, token sums
        over both. Kills mutant M3. RED: ImportError."""
        monkeypatch.delenv("ENABLE_LLM_PREFLIGHT_BREAKER", raising=False)
        p = _pricing()
        empty = p.summarize_openai_ledger([])
        assert empty["calls"] == 0
        assert empty["priced_calls"] == 0
        assert empty["unpriced_calls"] == 0
        assert empty["cost_usd"] == 0.0
        assert empty["cost_complete"] is True
        assert empty["basis"] == "list_price"
        assert empty["price_table_as_of"] == "2026-10-08"
        assert empty["by_model"] == {}
        assert p.summarize_openai_ledger(None) is None

        ledger = p.start_openai_ledger()
        await abs_mod.guarded_llm_create(
            _client_returning(_response("gpt-4o", "{}", _usage(1000, 200, 400))),
            model="gpt-4o", messages=[])
        await abs_mod.guarded_llm_create(
            _client_returning(_response("gpt-5", "{}", _usage(1000, 200, 400))),
            model="gpt-5", messages=[])
        assert len(ledger) == 2
        assert ledger[1]["cost_usd"] is None, "unknown model must record cost None (mutant M3)"
        mixed = p.summarize_openai_ledger(ledger)
        assert mixed["calls"] == 2
        assert mixed["priced_calls"] == 1
        assert mixed["unpriced_calls"] == 1
        assert mixed["cost_usd"] == 0.004
        assert mixed["cost_complete"] is False
        assert set(mixed["by_model"]) == {"gpt-4o", "gpt-5"}
        assert mixed["by_model"]["gpt-4o"]["calls"] == 1
        assert mixed["by_model"]["gpt-4o"]["cost_usd"] == 0.004
        assert mixed["by_model"]["gpt-5"]["calls"] == 1
        assert mixed["by_model"]["gpt-5"]["cost_usd"] is None
        assert mixed["prompt_tokens"] == 2000
        assert mixed["cached_tokens"] == 800
        assert mixed["completion_tokens"] == 400

    # -------------------------------------------------------------- cm07
    def test_cm07_response_builder_writes_metadata_openai(self):
        """Spec 4.1 cm07. build_comparison_response(openai_usage=...) writes
        metadata.openai verbatim; without the kwarg the key is ABSENT;
        metadata.total_cost stays round(total_cost, 6); a metadata={"openai":
        ...} override wins (the override merge, response_builder.py:2117).
        RED: TypeError unexpected keyword 'openai_usage'."""
        usage = {"calls": 3, "priced_calls": 3, "unpriced_calls": 0, "cost_usd": 0.0123,
                 "cost_complete": True, "basis": "list_price", "price_table_as_of": "2026-10-08",
                 "by_model": {"gpt-4o": {"calls": 1, "cost_usd": 0.01}}}
        def common():
            return dict(
                query="B0 P0 vs B1 P1", product_data=_minimal_product_data(),
                scoring_result=_minimal_scoring(), comparison=None, region="bahrain",
                api_calls=4, elapsed_seconds=1.5, total_cost=0.0123456789, gpt_calls=2,
            )

        result = build_comparison_response(openai_usage=copy.deepcopy(usage), **common())
        assert result["metadata"]["openai"] == usage
        assert result["metadata"]["total_cost"] == round(0.0123456789, 6)

        without = build_comparison_response(**common())
        assert "openai" not in without["metadata"], "absent-unless-present (model_downgraded precedent)"
        assert without["metadata"]["total_cost"] == round(0.0123456789, 6)

        override = build_comparison_response(
            openai_usage=copy.deepcopy(usage), metadata={"openai": {"calls": 9}}, **common())
        assert override["metadata"]["openai"] == {"calls": 9}, "a caller override must win"

    # -------------------------------------------------------------- cm08
    def test_cm08_admin_costs_sums_metadata_openai_and_counts_rows(self, admin_env):
        """Spec 4.1 cm08 as amended by CM1 (fixture off the rounding boundary),
        CM3 (get_supabase_client patched), CM5 (JSON-path select answered with
        key ``openai``), CM6 (truthful note). Rows A 0.004 (today), B legacy,
        C 0.0012 partial, D 0.0 complete: cost_usd 0.0052; rows 4;
        rows_with_cost 3; rows_partial 1; rows_without_cost 1;
        cost_complete False (a lower bound); today_usd 0.004;
        avg_cost_per_comparison round(0.0052/3, 6) = 0.001733;
        estimated_monthly_total round(30 + 0.0052, 2) = 30.01. RED at main:
        cost_usd 0.0 (the non-existent `metadata` column) and the keys missing.

        X2 (E2 = F2): fixture row E (an ALL-unpriced compare: cost None,
        cost_complete False, 3 calls on gpt-5) is BOTH rows_without_cost and
        rows_partial: rows 5, rows_with_cost 3, rows_partial 2 (C and E),
        rows_without_cost 2 (B and E), calls 2 + 3 + 0 + 3 = 8, cost_usd still
        0.0052, cost_complete False. RED on the GREEN bytes: rows_partial 1
        (partial was counted only inside the has-a-cost branch)."""
        fake = _FakeSupabase([_rows_abcde()], count=5)
        resp = _get_costs(fake)
        assert resp.status_code == 200
        data = resp.json()
        openai = data["openai"]
        assert openai["cost_usd"] == 0.0052, f"cost_usd {openai.get('cost_usd')!r} != 0.0052"
        assert openai["rows"] == 5
        assert openai["rows_with_cost"] == 3
        assert openai["rows_partial"] == 2, (
            f"rows_partial {openai.get('rows_partial')!r} != 2: an all-unpriced row (cost None, "
            f"cost_complete False) is partial too (X2)"
        )
        assert openai["rows_without_cost"] == 2
        assert openai["cost_complete"] is False
        assert openai["by_model"]["gpt-5"] == {"calls": 3, "cost_usd": None}
        assert openai["today_usd"] == 0.004
        assert openai["by_day"][_day(0)] == 0.004
        assert openai["by_day"][_day(1)] == 0.0012
        assert openai["truncated"] is False
        assert openai["basis"] == "list_price"
        assert openai["price_table_as_of"] == "2026-10-08"
        assert openai["source"] == "comparisons.full_response.metadata.openai"
        assert openai["calls"] == 8
        note = openai["note"].lower()
        assert "free daily" in note
        assert "persisted comparisons only" in note, "CM6: the note must say what the figure covers"
        assert "list price" in note
        assert data["comparisons_this_month"] == 5
        assert data["avg_cost_per_comparison"] == 0.001733
        assert data["estimated_monthly_total"] == 30.01
        assert data["fixed_costs_monthly"] == 30.00
        # CM5: the paged read asks PostgREST for the JSON path, not the blob.
        first = fake.page_queries[0]
        sel = "".join(str(a) for a in first.select_args).replace(" ", "")
        assert sel == "id,created_at,full_response->metadata->openai", (
            f"first select must be the JSON path (CM5), got {first.select_args!r}"
        )

    # -------------------------------------------------------------- cm09
    def test_cm09_admin_costs_null_when_nothing_recorded(self, admin_env):
        """Spec 4.1 cm09. Legacy-only rows -> cost_usd None,
        avg_cost_per_comparison None, estimated_monthly_total None,
        rows_without_cost 2; no client -> cost_usd None; Supabase raising ->
        200 and cost_usd None. Never 0 for unknown. Kills mutant M4.
        RED at main: 0 instead of null.

        X2 (Q3): the endpoint ALWAYS carries cost_complete -- None (unknown)
        whenever no row recorded a cost: legacy-only rows, no client, a
        raising Supabase, and a window whose only row is an ALL-unpriced
        compare (rows_partial 1 but rows_with_cost 0: unknown wins over
        partial). RED on the GREEN bytes: the key is absent."""

        def _complete_of(payload):
            assert "cost_complete" in payload["openai"], (
                f"cost_complete must always be present (X2); openai keys={sorted(payload['openai'])}"
            )
            return payload["openai"]["cost_complete"]

        legacy = [_row("l1", _stamp(1), legacy_total_cost=0.01),
                  _row("l2", _stamp(1), legacy_total_cost=0.015)]
        data = _get_costs(_FakeSupabase([legacy], count=2)).json()
        assert data["openai"]["cost_usd"] is None, (
            f"legacy-only rows must read null, got {data['openai'].get('cost_usd')!r} (mutant M4)"
        )
        assert data["openai"]["rows"] == 2
        assert data["openai"]["rows_with_cost"] == 0
        assert data["openai"]["rows_without_cost"] == 2
        assert data["openai"]["today_usd"] is None
        assert data["avg_cost_per_comparison"] is None
        assert data["estimated_monthly_total"] is None
        assert data["comparisons_this_month"] == 2
        assert _complete_of(data) is None

        data = _get_costs(None).json()
        assert data["openai"]["cost_usd"] is None
        assert data["openai"]["rows"] == 0
        assert data["avg_cost_per_comparison"] is None
        assert data["estimated_monthly_total"] is None
        assert _complete_of(data) is None

        raising = MagicMock()
        raising.table.side_effect = Exception("Supabase down")
        resp = _get_costs(raising)
        assert resp.status_code == 200
        data = resp.json()
        assert data["openai"]["cost_usd"] is None
        assert data["avg_cost_per_comparison"] is None
        assert data["estimated_monthly_total"] is None
        assert _complete_of(data) is None

        data = _get_costs(_FakeSupabase([[_row_e()]], count=1)).json()
        assert data["openai"]["cost_usd"] is None
        assert data["openai"]["rows_with_cost"] == 0
        assert data["openai"]["rows_partial"] == 1
        assert data["openai"]["rows_without_cost"] == 1
        assert data["openai"]["calls"] == 3
        assert _complete_of(data) is None, "no recorded cost: unknown (None) wins over partial (X2)"

    # -------------------------------------------------------------- cm10
    def test_cm10_admin_costs_truncated_flag_and_range_contract(self, admin_env):
        """Spec 4.1 cm10 + CM2. Ten full pages: page i is
        .range(i*1000, i*1000 + 999) (inclusive ends, postgrest
        base_request_builder.range), ordered by created_at ASCENDING then id;
        after the 10th full page truncated True, rows 10000, cost_usd
        10000 * 0.001 = 10.0; comparisons_this_month comes from the count
        query (12345 here, so the two are told apart). RED at main: no range
        calls, `truncated` missing."""
        fake = _FakeSupabase([_bulk_page(f"p{i}", PAGE) for i in range(10)], count=12345)
        data = _get_costs(fake).json()
        assert fake.range_args == [(i * PAGE, i * PAGE + PAGE - 1) for i in range(10)], (
            f"range args {fake.range_args!r}"
        )
        openai = data["openai"]
        assert openai["truncated"] is True
        assert openai["rows"] == 10000
        assert openai["rows_with_cost"] == 10000
        assert openai["cost_usd"] == 10.0
        assert data["comparisons_this_month"] == 12345
        first = fake.page_queries[0]
        assert first.order_calls, "the paged read must order its rows (CM2)"
        (cols, kw) = first.order_calls[0]
        assert cols[0] == "created_at" and not kw.get("desc", False), (
            f"first order must be created_at ascending, got {first.order_calls!r}"
        )
        assert any(c[0][0] == "id" for c in first.order_calls), (
            f"a secondary order by id is required (CM2), got {first.order_calls!r}"
        )
        # X10 (E10): the window filter is `.gte("created_at", since)` -- the
        # fake records the filter METHOD name, so `.gt` / `.eq` would not pass.
        assert ("gte", "created_at") in [tuple(f[:2]) for f in first.filters], (
            f"the paged read must filter created_at with .gte, got {first.filters!r}"
        )

    def test_cm10b_admin_costs_1001_row_page_counts_as_full(self, admin_env):
        """CM2: a page counts as full when len(page) >= 1000. A 1001-row first
        page must NOT stop the loop: range (0,999) then (1000,1999); rows
        1001 + 3 = 1004; truncated False. RED at main: no range calls."""
        fake = _FakeSupabase([_bulk_page("big", PAGE + 1), _bulk_page("tail", 3)], count=1004)
        data = _get_costs(fake).json()
        assert fake.range_args == [(0, 999), (1000, 1999)], fake.range_args
        assert data["openai"]["rows"] == 1004
        assert data["openai"]["truncated"] is False
        assert data["openai"]["cost_usd"] == round(1004 * 0.001, 6)
        # X2: every row recorded a complete cost -> cost_complete True (the
        # third branch of the always-present key; RED on the GREEN bytes).
        assert data["openai"].get("cost_complete", "absent") is True

    def test_cm10c_admin_costs_dedupes_page_boundary_repeat_by_id(self, admin_env):
        """CM2 (review F8): a row that moves across the page boundary under a
        concurrent insert reappears on the next page; rows are de-duplicated
        by id so it is counted ONCE: 1000 + (3 - 1 repeat) = 1002 rows,
        cost 1002 * 0.001 = 1.002. RED at main: keys missing.

        The X9 variant runs FIRST so a created_at-keyed de-dup (mutant A6)
        fails on the targeted twin row on every platform (the second case's
        _bulk_page timestamps collide only at a coarse clock resolution)."""
        # X9 (E8b): the de-dup key is the id, never created_at. Every row has
        # a DISTINCT created_at (_seq_rows); page 1 carries page 0's last row
        # again (same id: dropped) AND a twin with a DIFFERENT id and the SAME
        # created_at (a different comparison: counted). 1000 + 1 + 2 = 1003
        # rows, cost 1003 * 0.001 = 1.003. RED on mutant A6 (de-dup by
        # created_at drops the twin: 1002).
        base = datetime.now(timezone.utc) - timedelta(days=1)
        page0 = _seq_rows("s", PAGE, base)
        last = page0[-1]
        twin = _row("s-twin", last["created_at"],
                    openai={"cost_usd": 0.001, "cost_complete": True, "calls": 1})
        page1 = [copy.deepcopy(last), twin] + _seq_rows("s-tail", 2, base, start=PAGE)
        assert len({r["created_at"] for r in page0 + page1}) == PAGE + 2, "harness: created_at must be distinct"
        fake = _FakeSupabase([page0, page1], count=1003)
        data = _get_costs(fake).json()
        assert data["openai"]["rows"] == 1003, (
            f"rows {data['openai'].get('rows')!r} != 1003: a different id with the same created_at "
            f"is a different comparison (de-dup by id, X9)"
        )
        assert data["openai"]["rows_with_cost"] == 1003
        assert data["openai"]["cost_usd"] == 1.003

        page0 = _bulk_page("r", PAGE)
        page1 = [copy.deepcopy(page0[-1])] + _bulk_page("next", 2)
        fake = _FakeSupabase([page0, page1], count=1002)
        data = _get_costs(fake).json()
        assert data["openai"]["rows"] == 1002, f"double-counted the boundary row: {data['openai'].get('rows')!r}"
        assert data["openai"]["rows_with_cost"] == 1002
        assert data["openai"]["cost_usd"] == 1.002

    def test_cm10d_admin_costs_falls_back_to_blob_select_logging_type_only(self, admin_env, caplog):
        """CM5: when the JSON-path select raises (PostgREST rejecting the
        path), the read falls back to the blob shape (full_response) and
        logs the fallback with the exception TYPE NAME only. Same A/B/C/D
        aggregate as cm08: cost_usd 0.0052, rows 4. RED at main: cost_usd 0."""
        secret = "pgrst-detail-" + "must-not-be-logged-" + "cm10d"
        fake = _FakeSupabase([_rows_abcd()], count=4, json_path_error=RuntimeError(secret))
        caplog.set_level(logging.DEBUG)
        data = _get_costs(fake).json()
        openai = data["openai"]
        assert openai["cost_usd"] == 0.0052, f"blob fallback did not run: {openai.get('cost_usd')!r}"
        assert openai["rows"] == 4
        assert openai["rows_with_cost"] == 3
        shapes = ["json" if "->" in "".join(map(str, q.select_args)) else "blob" for q in fake.page_queries]
        assert "json" in shapes and "blob" in shapes, f"expected JSON-path probe then blob fallback, got {shapes}"
        assert shapes.index("json") < shapes.index("blob")
        assert any("RuntimeError" in r.getMessage() for r in caplog.records), (
            "the fallback must be logged with the exception type name"
        )
        assert secret not in caplog.text, "the fallback log carried the exception text"

    def test_cm10e_admin_costs_paged_read_runs_through_db_offload(self, admin_env, monkeypatch):
        """CM5 (review F5): the paged read goes through the existing db offload
        helper (app/utils/db_offload.run_db) so that with
        ENABLE_SYNC_DB_OFFLOAD=true every page's .execute() runs in
        asyncio.to_thread, never blocking the event loop inside the async
        handler. Pinned by marking the to_thread context and reading the mark
        inside the fake execute. RED at main: executed inline on the loop."""
        monkeypatch.setenv("ENABLE_SYNC_DB_OFFLOAD", "true")
        real_to_thread = asyncio.to_thread

        async def _marked(func, *a, **k):
            token = _IN_OFFLOAD.set(True)
            try:
                return await real_to_thread(func, *a, **k)
            finally:
                _IN_OFFLOAD.reset(token)

        fake = _FakeSupabase([_bulk_page("o", PAGE), _bulk_page("o2", 5)], count=1005)
        with patch("asyncio.to_thread", new=_marked):
            data = _get_costs(fake).json()
        assert data["openai"]["rows"] == 1005
        pages = fake.page_queries
        assert pages, "harness: no paged read happened"
        assert all(q.in_offload for q in pages), (
            f"{sum(1 for q in pages if not q.in_offload)} of {len(pages)} page reads executed on the event loop"
        )
        # X7 (E7 / G4): the count query's .execute() runs in the offload too.
        counts = [q for q in fake.queries if q.select_kwargs.get("count")]
        assert counts, "harness: no count query happened"
        assert data["comparisons_this_month"] == 1005
        assert all(q.in_offload for q in counts), (
            "the count query executed on the event loop (G4 / X7, mutant A19)"
        )

    # -------------------------------------------------------------- cm11
    def test_cm11_costs_api_list_usd_and_daily_burn(self, admin_env):
        """Spec 4.1 cm11 + CM1 + CM12 (openai_paid_usd RENAMED openai_list_usd,
        no alias). /costs/api?days=30 with rows A/B/C/D: openai_list_usd
        round(0.0052, 4) = 0.0052; comparisons_with_cost 3 (recorded, a true
        0.0 counts); avg_cost_per_request_usd round(0.0052/3, 6) = 0.001733;
        daily_burn carries only recorded costs (today 0.004, yesterday
        0.0012, nothing for the legacy row's day); rows_without_cost 1;
        rows_partial 1; "openai_paid_usd" absent. Legacy-only rows ->
        openai_list_usd None, avg None (mutant M4). RED at main: key missing.

        X2 mirrored on /costs/api: rows A-E -> rows 5, rows_without_cost 2,
        rows_partial 2, cost_complete False (always present); legacy-only,
        no client and a raising Supabase -> cost_complete None. RED on the
        GREEN bytes: rows_partial 1 and cost_complete absent."""
        path = "/api/v1/admin/costs/api?days=30"
        fake = _FakeSupabase([_rows_abcde()], count=5)
        resp = _get_costs(fake, path=path, admin_too=True)
        assert resp.status_code == 200
        body = resp.json()
        assert "openai_list_usd" in body, f"openai_list_usd missing (CM12); keys={sorted(body)}"
        assert "openai_paid_usd" not in body, "the old name asserts a billing fact the data cannot carry (CM12)"
        assert body["openai_list_usd"] == 0.0052
        assert body["comparisons_with_cost"] == 3
        assert body["avg_cost_per_request_usd"] == 0.001733
        assert body["rows"] == 5
        assert body["rows_without_cost"] == 2
        assert body["rows_partial"] == 2, f"rows_partial {body.get('rows_partial')!r} != 2 (X2)"
        assert body.get("cost_complete", "absent") is False, (
            f"cost_complete must be present and False with partial rows (X2); got {body.get('cost_complete', 'absent')!r}"
        )
        assert body["truncated"] is False
        assert body["basis"] == "list_price"
        assert body["price_table_as_of"] == "2026-10-08"
        assert body["window_days"] == 30
        assert "scrapers" in body
        note = body["note"].lower()
        assert "free daily" in note and "persisted comparisons only" in note
        burn = {d["day"]: d["usd"] for d in body["daily_burn"]}
        assert burn.get(_day(0)) == 0.004
        assert burn.get(_day(1)) == 0.0012
        assert burn.get(_day(2), 0.0) == 0.0, f"the legacy row leaked into daily_burn: {burn}"
        assert sum(burn.values()) == pytest.approx(0.0052, abs=1e-9)

        legacy = [_row("l1", _stamp(1), legacy_total_cost=0.0086),
                  _row("l2", _stamp(0), legacy_total_cost=0.0019)]
        body = _get_costs(_FakeSupabase([legacy], count=2),
                          path="/api/v1/admin/costs/api?days=30", admin_too=True).json()
        assert body["openai_list_usd"] is None, f"legacy-only must read null, got {body.get('openai_list_usd')!r}"
        assert body["avg_cost_per_request_usd"] is None
        assert body["comparisons_with_cost"] == 0
        assert body["rows_without_cost"] == 2
        assert body["daily_burn"] == [] or all(d["usd"] == 0.0 for d in body["daily_burn"])
        assert body.get("cost_complete", "absent") is None, "legacy-only: cost_complete None (X2)"

        body = _get_costs(None, path=path, admin_too=True).json()
        assert body["openai_list_usd"] is None
        assert body["rows"] == 0
        assert body.get("cost_complete", "absent") is None, "no client: cost_complete None (X2)"

        raising = MagicMock()
        raising.table.side_effect = Exception("Supabase down")
        resp = _get_costs(raising, path=path, admin_too=True)
        assert resp.status_code == 200
        body = resp.json()
        assert body["openai_list_usd"] is None
        assert body["avg_cost_per_request_usd"] is None
        assert body.get("cost_complete", "absent") is None, "raising Supabase: cost_complete None (X2)"

    # -------------------------------------------------------------- cm12
    def test_cm12_costs_html_labels_and_null_render(self):
        """Spec 4.1 cm12 + CM6 + CM12 (review F9). app/static/admin/costs.html
        reads openai_list_usd (never openai_paid_usd) through a
        ``function fmtUsd`` that renders null as the literal "n/a"; the labels
        say list price and name the free daily allowance as OpenAI's; the
        false labels ("paid-tier spillover", "total_cost > $0", "BILLED
        COMPARISONS") are gone. RED at main: label text.

        X3 (E3): the fmtUsd null branch itself is pinned by regex (mutant A9,
        `v === undefined ? "n/a"`, renders null as $0.0000 in a browser).
        X1 (E1 / G7): the OPENAI LIST-PRICE SPEND card renders the endpoint's
        note, ``${api.note || ""}``. The page is static, so the template
        reference is pinned and the backend OPENAI_COST_NOTE (what /costs/api
        sends as ``note``) is substituted for it before the phrase checks:
        "persisted comparisons only", "not a bill", "free daily allowance",
        "list price" and X12's "retried by the sdk". RED on the GREEN bytes:
        the page never renders api.note."""
        from app.api.admin_routes import OPENAI_COST_NOTE

        html_path = Path(image_routes.__file__).resolve().parents[2] / "app" / "static" / "admin" / "costs.html"
        html = html_path.read_text(encoding="utf-8")

        fmt = re.search(r"function fmtUsd\(\s*(\w+)[^)]*\)\s*\{([^}]*)\}", html)
        assert fmt, "null-safe formatter fmtUsd required (review F9)"
        arg, body = re.escape(fmt.group(1)), fmt.group(2)
        null_branch = re.search(arg + r' == null \? "n/a"', body) or (
            re.search(arg + r" === null", body) and re.search(arg + r" === undefined", body)
        )
        assert null_branch, (
            f"fmtUsd must send null (not only undefined) to n/a (X3, mutant A9); body={body.strip()!r}"
        )

        note_ref = re.search(r'\$\{\s*api\.note\s*\|\|\s*""\s*\}', html)
        assert note_ref, "costs.html must render the endpoint's note: ${api.note || \"\"} (X1 / G7)"
        rendered = html[:note_ref.start()] + OPENAI_COST_NOTE + html[note_ref.end():]
        lower = rendered.lower()
        assert "persisted comparisons only" in lower, "X1: the rendered note names what the figure covers"
        assert "not a bill" in lower, "X1: the rendered note says the figure is not a bill"
        assert "retried by the sdk" in lower, "X12: the note names SDK retries among the exclusions"
        assert "openai_list_usd" in html, "costs.html must read openai_list_usd (CM12)"
        assert "openai_paid_usd" not in html, "costs.html still reads openai_paid_usd"
        assert "paid-tier spillover" not in html
        assert "total_cost > $0" not in html
        assert "billed comparisons" not in lower
        assert "recorded cost" in lower, "the KPI label must say COMPARISONS WITH A RECORDED COST"
        assert "free daily allowance" in lower
        assert "list price" in lower
        assert "function fmtUsd" in html, "null-safe formatter fmtUsd required (review F9)"
        assert '"n/a"' in html or "'n/a'" in html, "fmtUsd must render null as n/a"
        assert re.search(r"fmtUsd\([^)]*openai_list_usd", html), (
            "openai_list_usd must render through fmtUsd"
        )

    # -------------------------------------------------------------- cm13
    @pytest.mark.asyncio
    async def test_cm13_compare_from_text_end_to_end_records_metadata_openai(self, monkeypatch):
        """CM4 (review F4), the non-streaming entry. A hermetic explicit-pair
        compare with a fake client whose EVERY chat completion carries usage
        1000/200/0 builds a response whose metadata.openai has
        calls == create.await_count, cost_usd > 0 (gpt-4o 0.0045 and
        gpt-4o-mini 0.00027 per call under CM7, summed over the requested
        ids), cost_complete True, by_model keyed by the REQUESTED ids.
        Kills mutant M5 (start_openai_ledger() deleted at the
        compare_from_text entry). RED at main: metadata.openai absent."""
        _pin_default_models(monkeypatch)
        _arm_prod_search_config(monkeypatch)
        fan = _FanOutCounters()
        client = _usage_client()
        with _all(*fan.patches(client), *_no_supabase(), *_no_egress()):
            result = await _run_compare()
        _assert_e2e_openai(result, client, "compare_from_text")

    # -------------------------------------------------------------- cm14
    @pytest.mark.asyncio
    async def test_cm14_compare_from_text_streaming_end_to_end_records_metadata_openai(self, monkeypatch):
        """CM4 (review F4), the SSE entry the app drives. Same harness as cm13
        through compare_from_text_streaming; the ``complete`` event's payload
        carries metadata.openai with calls == create.await_count, cost_usd >
        0, cost_complete True, by_model keyed by the requested ids. Kills
        mutant M6 (start_openai_ledger() deleted at the streaming entry).
        RED at main: metadata.openai absent."""
        _pin_default_models(monkeypatch)
        _arm_prod_search_config(monkeypatch)
        fan = _FanOutCounters()
        client = _usage_client()
        with _all(*fan.patches(client), *_no_supabase(), *_no_egress()):
            events = await _run_stream()
        complete = [d for e, d in events if e == "complete"]
        assert complete, (
            "harness: no complete event; events="
            f"{[(e, (d.get('code') if isinstance(d, dict) else None)) for e, d in events]}"
        )
        _assert_e2e_openai(complete[-1], client, "compare_from_text_streaming")

    # -------------------------------------------------------------- cm15
    def test_cm15_camera_identify_call_is_recorded_into_metadata_openai(self, monkeypatch):
        """CM9 (review F11). POST /api/v1/image/identify with two images: the
        REAL identify_products dispatches once through guarded_llm_create on
        the vision model (gpt-4o-mini, 500 prompt / 100 completion ->
        (500*0.15 + 100*0.60)/1e6 = 0.000135); the compare is faked (so its
        own ledger is empty) and the route re-summarises the vision entry into
        result.metadata.openai: calls 1, by_model {gpt-4o-mini}, cost_usd
        0.000135, cost_complete True. RED at main: metadata.openai absent."""
        _pin_default_models(monkeypatch)
        monkeypatch.setattr(limiter, "enabled", False)
        for flag in ("ENABLE_COMPARE_AUTH_REQUIRED", "ENABLE_ANON_USAGE_GATE",
                     "ENABLE_PAID_ROUTE_METERING", "ENABLE_STRICT_OPTIONAL_AUTH"):
            monkeypatch.delenv(flag, raising=False)
        vision_json = (
            '[{"brand": "Acme", "name": "Widget", "size_or_count": null, '
            '"visible_price": null, "confidence": "high"}, '
            '{"brand": "Globex", "name": "Gadget", "size_or_count": null, '
            '"visible_price": null, "confidence": "high"}]'
        )
        fake = _usage_client(content=vision_json, prompt=500, completion=100)
        monkeypatch.setattr(oai, "client", fake)
        monkeypatch.setattr(content_safety_service, "get_content_safety_service", lambda: _Safety())
        compare_result = {
            "success": True,
            "products": [{"brand": "Acme", "name": "Widget"}, {"brand": "Globex", "name": "Gadget"}],
            "metadata": {"total_cost": 0.01, "query": "Acme Widget vs Globex Gadget"},
        }

        async def _fake_compare(self, *a, **k):
            return copy.deepcopy(compare_result)

        monkeypatch.setattr(image_routes.StructuredComparisonService, "compare_from_text", _fake_compare)
        monkeypatch.setattr(image_routes, "log_search", lambda **kw: _done())
        monkeypatch.setattr(image_routes, "save_comparison_and_track_cohort", lambda **kw: _done())

        files = [("images", (f"p{i}.jpg", JPEG, "image/jpeg")) for i in range(2)]
        resp = TestClient(app, raise_server_exceptions=False).post("/api/v1/image/identify", files=files)
        assert resp.status_code == 200, f"harness: {resp.status_code} {resp.text[:300]}"
        body = resp.json()
        assert body.get("action") == "comparison", f"harness: the route did not reach the compare: {body!r}"
        assert fake.chat.completions.create.await_count == 1
        meta = body["metadata"]
        assert meta["vision_cost"] == pytest.approx(0.000135, abs=1e-9)
        assert "openai" in meta, f"camera identify call not recorded (CM9); metadata keys={sorted(meta)}"
        openai = meta["openai"]
        assert openai["calls"] == 1
        assert set(openai["by_model"]) == {"gpt-4o-mini"}
        assert openai["cost_usd"] == pytest.approx(0.000135, abs=1e-6)
        assert openai["cost_complete"] is True
        assert openai["prompt_tokens"] == 500
        assert openai["completion_tokens"] == 100

    # -------------------------------------------------------------- cm15b
    def test_cm15b_camera_route_merges_vision_and_compare_summaries(self, monkeypatch):
        """G5 (the camera merge design). The vision identify call (gpt-4o-mini
        500/100 -> 0.000135) is recorded on the route's OWN ledger; the fake
        compare returns its own metadata.openai (calls 2, cost 0.00054, prompt
        2000, completion 400, by_model {gpt-4o-mini: 2 calls}); the route ships
        the MERGED summary through merge_openai_summaries: calls 3, cost_usd
        0.000135 + 0.00054 = 0.000675, by_model {gpt-4o-mini: {calls 3, cost
        0.000675}}, prompt 2500, completion 500, cost_complete True. Kills
        mutant M13 both ways (the route overwriting with the compare summary
        gives calls 2; with the vision summary calls 1). RED: key absent."""
        compare_openai = {
            "calls": 2, "priced_calls": 2, "unpriced_calls": 0,
            "prompt_tokens": 2000, "cached_tokens": 0, "completion_tokens": 400,
            "cost_usd": 0.00054, "cost_complete": True,
            "by_model": {"gpt-4o-mini": {"calls": 2, "prompt_tokens": 2000, "cached_tokens": 0,
                                         "completion_tokens": 400, "cost_usd": 0.00054}},
            "basis": "list_price", "price_table_as_of": "2026-10-08",
        }
        body, fake = _camera_identify(monkeypatch, compare_openai=compare_openai)
        assert fake.chat.completions.create.await_count == 1
        meta = body["metadata"]
        assert "openai" in meta, f"camera route carries no metadata.openai; keys={sorted(meta)}"
        openai = meta["openai"]
        assert openai["calls"] == 3, (
            f"calls {openai['calls']} != 3: the route must MERGE the vision and compare summaries (mutant M13)"
        )
        assert openai["priced_calls"] == 3
        assert openai["unpriced_calls"] == 0
        assert openai["cost_usd"] == pytest.approx(0.000675, abs=1e-9)
        assert set(openai["by_model"]) == {"gpt-4o-mini"}
        assert openai["by_model"]["gpt-4o-mini"]["calls"] == 3
        assert openai["by_model"]["gpt-4o-mini"]["cost_usd"] == pytest.approx(0.000675, abs=1e-9)
        assert openai["prompt_tokens"] == 2500
        assert openai["completion_tokens"] == 500
        assert openai["cached_tokens"] == 0
        assert openai["cost_complete"] is True
        assert openai["basis"] == "list_price"
        assert openai["price_table_as_of"] == "2026-10-08"
        # The compare's own figures still ship inside the merged key (one key, additive).
        assert meta["vision_cost"] == pytest.approx(0.000135, abs=1e-9)

    # -------------------------------------------------------------- cm15c
    def test_cm15c_camera_merge_keeps_a_partial_compare_partial(self, monkeypatch):
        """X11 (F1). The compare returns a PARTIAL summary (priced 1, unpriced
        1, cost 0.00027, cost_complete False; by_model {gpt-4o-mini: 1 call
        0.00027, gpt-5: 1 call None}); the vision call is complete and runs
        on the dated mini snapshot gpt-4o-mini-2024-07-18 (an EXACT key at
        the mini rates, CM7: 500/100 -> 0.000135), so the merged by_model
        carries THREE keys (the merge sums per key; here each key comes from
        one side, cm15b pins the same-key sum: gpt-4o-mini 1 + 2 calls). The
        merged camera summary is partial: cost_complete
        False (a AND b), calls 3, priced 2, unpriced 1, cost_usd 0.00027 +
        0.000135 = 0.000405 (6 dp). RED on mutant MA (`and` -> `or` reads
        the merged row as complete)."""
        compare_openai = {
            "calls": 2, "priced_calls": 1, "unpriced_calls": 1,
            "prompt_tokens": 2000, "cached_tokens": 0, "completion_tokens": 400,
            "cost_usd": 0.00027, "cost_complete": False,
            "by_model": {
                "gpt-4o-mini": {"calls": 1, "prompt_tokens": 1000, "cached_tokens": 0,
                                "completion_tokens": 200, "cost_usd": 0.00027},
                "gpt-5": {"calls": 1, "prompt_tokens": 1000, "cached_tokens": 0,
                          "completion_tokens": 200, "cost_usd": None},
            },
            "basis": "list_price", "price_table_as_of": "2026-10-08",
        }
        snapshot = "gpt-4o-mini-2024-07-18"
        body, fake = _camera_identify(monkeypatch, compare_openai=compare_openai, vision_model=snapshot)
        assert fake.chat.completions.create.await_count == 1
        assert fake.chat.completions.create.await_args.kwargs.get("model") == snapshot, "harness: vision model"
        openai = body["metadata"]["openai"]
        assert openai["cost_complete"] is False, (
            "a partial compare must keep the merged camera summary partial (X11, mutant MA)"
        )
        assert openai["calls"] == 3
        assert openai["priced_calls"] == 2
        assert openai["unpriced_calls"] == 1
        assert openai["cost_usd"] == pytest.approx(0.000405, abs=1e-9)
        assert openai["cost_usd"] == round(openai["cost_usd"], 6)
        assert openai["prompt_tokens"] == 2500
        assert openai["completion_tokens"] == 500
        assert set(openai["by_model"]) == {snapshot, "gpt-4o-mini", "gpt-5"}, (
            f"by_model must carry THREE keys (X11): {sorted(openai['by_model'])}"
        )
        vision = openai["by_model"][snapshot]
        assert vision["calls"] == 1
        assert vision["cost_usd"] == pytest.approx(0.000135, abs=1e-9)
        assert vision["prompt_tokens"] == 500
        assert vision["completion_tokens"] == 100
        mini = openai["by_model"]["gpt-4o-mini"]
        assert mini["calls"] == 1
        assert mini["cost_usd"] == pytest.approx(0.00027, abs=1e-9)
        assert mini["prompt_tokens"] == 1000
        assert mini["completion_tokens"] == 200
        assert openai["by_model"]["gpt-5"]["calls"] == 1
        assert openai["by_model"]["gpt-5"]["cost_usd"] is None

    # -------------------------------------------------------------- cm16
    def test_cm16_public_share_view_strips_metadata_openai(self):
        """CM11 (review F14). GET /api/v1/share/{token} (no auth) serves the
        stored full_response WITHOUT metadata.openai; the rest of metadata
        (total_cost ships today) is kept. RED at main: the key passes through.
        X4 (E4): the strip COPIES -- the dict handed to the route by
        get_shared_comparison still carries metadata.openai after the request
        (RED on mutant A14, an in-place pop)."""
        shared = {
            "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            "query": "Acme Widget vs Globex Gadget",
            "product_names": ["Acme Widget", "Globex Gadget"],
            "input_type": "text",
            "full_response": {
                "success": True,
                "products": [{"brand": "Acme", "name": "Widget"}],
                "metadata": {
                    "query": "Acme Widget vs Globex Gadget",
                    "total_cost": 0.01,
                    "openai": {"calls": 4, "cost_usd": 0.0052, "cost_complete": True,
                               "by_model": {"gpt-4o": {"calls": 1}}},
                },
            },
            "created_at": "2026-10-09T10:00:00Z",
        }
        handed = copy.deepcopy(shared)
        with patch("app.api.share_routes.get_shared_comparison", new_callable=AsyncMock,
                   return_value=handed):
            resp = TestClient(app).get("/api/v1/share/abc12xyzABC12xyzABCD")
        assert resp.status_code == 200, resp.text[:300]
        full = resp.json()["comparison"]["full_response"]
        meta = full["metadata"]
        assert "openai" not in meta, f"the public share view leaks metadata.openai: {sorted(meta)}"
        assert meta["total_cost"] == 0.01
        assert meta["query"] == "Acme Widget vs Globex Gadget"
        assert full["products"] == [{"brand": "Acme", "name": "Widget"}]
        assert "openai" in handed["full_response"]["metadata"], (
            "the share strip mutated the stored dict instead of copying it (X4, mutant A14)"
        )
        assert handed["full_response"]["metadata"]["openai"] == shared["full_response"]["metadata"]["openai"]

    # -------------------------------------------------------------- cm17
    @pytest.mark.asyncio
    async def test_cm17_hard_cap_partial_carries_metadata_openai(self, monkeypatch):
        """G9 M7 (CM4's third mutant), the hard-cap partial path. The inner
        impl is stubbed (the tests/test_compare_timeout_graceful.py shape): it
        binds the request ledger, dispatches ONE fake chat completion through
        guarded_llm_create (gpt-4o-mini 1000/200/0 -> 0.00027), seeds the
        partial stash with two usable products and hangs past a 0.2 s
        STREAM_HARD_CAP_SECONDS, so the wrapper's TimeoutError handler builds
        the partial through _build_partial_response. That partial's
        metadata.openai carries the call: calls 1, by_model {gpt-4o-mini},
        cost_usd 0.00027, cost_complete True, next to metadata.partial True.
        Kills mutant M7 (_build_partial_response without openai_usage=).
        RED: ImportError / key absent."""
        from tests.test_compare_timeout_graceful import _fake_product

        _pin_default_models(monkeypatch)
        p = _pricing()
        monkeypatch.setattr(scs_mod, "STREAM_HARD_CAP_SECONDS", 0.2)
        client = _usage_client()

        async def _impl(self, *args, **kwargs):
            self._openai_ledger = p.start_openai_ledger()
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

        assert result.get("success") is True and result["metadata"].get("partial") is True, (
            f"harness: the hard cap did not build a partial: code={result.get('code')!r} keys={sorted(result)[:12]}"
        )
        assert client.chat.completions.create.await_count == 1
        meta = result["metadata"]
        assert "openai" in meta, (
            f"the hard-cap partial carries no metadata.openai (mutant M7); keys={sorted(meta)}"
        )
        openai = meta["openai"]
        assert openai["calls"] == 1
        assert openai["priced_calls"] == 1
        assert set(openai["by_model"]) == {"gpt-4o-mini"}
        assert openai["cost_usd"] == pytest.approx(0.00027, abs=1e-9)
        assert openai["cost_complete"] is True
        assert openai["prompt_tokens"] == 1000
        assert openai["completion_tokens"] == 200
        assert "total_cost" in meta

    # -------------------------------------------------------------- cm18
    def test_cm18_owner_history_view_keeps_metadata_openai(self, monkeypatch):
        """X5 (E5, CM11's second clause). The authenticated OWNER view
        GET /api/v1/comparisons/{id} serves the stored full_response WITH
        metadata.openai and total_cost (only the public share view strips it).
        The history read is patched the way tests/test_history_routes.py does
        (get_comparison_by_id + a get_current_user override). RED on mutant
        A7 (the owner view strips metadata.openai)."""
        from app.api.auth_routes import get_current_user

        monkeypatch.setattr(limiter, "enabled", False)
        owner = {"id": "user-cm18", "email": "owner@example.com"}
        openai = {"calls": 4, "priced_calls": 4, "unpriced_calls": 0, "cost_usd": 0.0052,
                  "cost_complete": True, "by_model": {"gpt-4o": {"calls": 1, "cost_usd": 0.0045}},
                  "basis": "list_price", "price_table_as_of": "2026-10-08"}
        stored = {
            "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            "query": "Acme Widget vs Globex Gadget",
            "product_names": ["Acme Widget", "Globex Gadget"],
            "input_type": "text",
            "user_id": owner["id"],
            "full_response": {
                "success": True,
                "products": [{"brand": "Acme", "name": "Widget"}],
                "metadata": {"query": "Acme Widget vs Globex Gadget", "total_cost": 0.01,
                             "openai": copy.deepcopy(openai)},
            },
            "created_at": "2026-10-09T10:00:00Z",
        }
        app.dependency_overrides[get_current_user] = lambda: owner
        try:
            with patch("app.api.history_routes.get_comparison_by_id", new_callable=AsyncMock,
                       return_value=copy.deepcopy(stored)):
                resp = TestClient(app).get("/api/v1/comparisons/a1b2c3d4-e5f6-7890-abcd-ef1234567890")
        finally:
            app.dependency_overrides.pop(get_current_user, None)
        assert resp.status_code == 200, resp.text[:300]
        meta = resp.json()["comparison"]["full_response"]["metadata"]
        assert meta.get("openai") == openai, (
            f"the owner view must keep metadata.openai (CM11 / X5, mutant A7); metadata keys={sorted(meta)}"
        )
        assert meta["total_cost"] == 0.01

    # -------------------------------------------------------------- cm19
    @pytest.mark.asyncio
    async def test_cm19_ledger_keys_on_the_requested_model_not_the_served_snapshot(self, monkeypatch):
        """X8 (E8a, spec A4). The served response names a DIFFERENT, still
        priced snapshot (response.model gpt-4o-2024-08-06) than the requested
        gpt-4o: the ledger entry's model and the summary's by_model key are
        the REQUESTED id (what the price table and the env override name);
        the cost is (1000*2.50 + 200*10.00)/1e6 = 0.0045 either way. RED on
        mutant A1 (the recorder keys on response.model)."""
        monkeypatch.delenv("ENABLE_LLM_PREFLIGHT_BREAKER", raising=False)
        p = _pricing()
        ledger = []
        token = p._LEDGER.set(ledger)
        try:
            client = _client_returning(_response("gpt-4o-2024-08-06", "{}", _usage(1000, 200, 0)))
            await abs_mod.guarded_llm_create(client, model="gpt-4o", messages=[])
        finally:
            p._LEDGER.reset(token)
        assert client.chat.completions.create.await_count == 1
        assert len(ledger) == 1
        assert ledger[0]["model"] == "gpt-4o", (
            f"the entry must carry the REQUESTED id, not the served snapshot (X8, mutant A1): {ledger[0]['model']!r}"
        )
        assert ledger[0]["cost_usd"] == pytest.approx(0.0045, rel=1e-9)
        summary = p.summarize_openai_ledger(ledger)
        assert set(summary["by_model"]) == {"gpt-4o"}, f"by_model {sorted(summary['by_model'])}"
        assert summary["cost_usd"] == 0.0045


# ---------------------------------------------------------------------------
# cm13 / cm14 / cm15 helpers (kept below the class so the nodes read top-down)
# ---------------------------------------------------------------------------
class _Safety:
    async def moderate_vision_output(self, _extracted):
        return content_safety_service.SafetyResult(allowed=True)


def _camera_identify(monkeypatch, *, compare_openai=None, vision_model=None):
    """cm15b harness: POST /api/v1/image/identify with two images; the REAL
    identify_products dispatches once on the vision model (gpt-4o-mini
    500/100 -> 0.000135, or ``vision_model`` when given: cm15c) and the
    compare is faked, returning ``compare_openai`` as its own metadata.openai
    when given. Returns (body, fake_client)."""
    _pin_default_models(monkeypatch)
    if vision_model is not None:
        monkeypatch.setenv("OPENAI_MODEL_VISION", vision_model)
    monkeypatch.setattr(limiter, "enabled", False)
    for flag in ("ENABLE_COMPARE_AUTH_REQUIRED", "ENABLE_ANON_USAGE_GATE",
                 "ENABLE_PAID_ROUTE_METERING", "ENABLE_STRICT_OPTIONAL_AUTH"):
        monkeypatch.delenv(flag, raising=False)
    vision_json = (
        '[{"brand": "Acme", "name": "Widget", "size_or_count": null, '
        '"visible_price": null, "confidence": "high"}, '
        '{"brand": "Globex", "name": "Gadget", "size_or_count": null, '
        '"visible_price": null, "confidence": "high"}]'
    )
    fake = _usage_client(content=vision_json, prompt=500, completion=100)
    monkeypatch.setattr(oai, "client", fake)
    monkeypatch.setattr(content_safety_service, "get_content_safety_service", lambda: _Safety())
    metadata = {"total_cost": 0.01, "query": "Acme Widget vs Globex Gadget"}
    if compare_openai is not None:
        metadata["openai"] = copy.deepcopy(compare_openai)
    compare_result = {
        "success": True,
        "products": [{"brand": "Acme", "name": "Widget"}, {"brand": "Globex", "name": "Gadget"}],
        "metadata": metadata,
    }

    async def _fake_compare(self, *a, **k):
        return copy.deepcopy(compare_result)

    monkeypatch.setattr(image_routes.StructuredComparisonService, "compare_from_text", _fake_compare)
    monkeypatch.setattr(image_routes, "log_search", lambda **kw: _done())
    monkeypatch.setattr(image_routes, "save_comparison_and_track_cohort", lambda **kw: _done())

    files = [("images", (f"p{i}.jpg", JPEG, "image/jpeg")) for i in range(2)]
    resp = TestClient(app, raise_server_exceptions=False).post("/api/v1/image/identify", files=files)
    assert resp.status_code == 200, f"harness: {resp.status_code} {resp.text[:300]}"
    body = resp.json()
    assert body.get("action") == "comparison", f"harness: the route did not reach the compare: {body!r}"
    return body, fake


def _no_supabase():
    """No Supabase client is ever built in the compare (profile / history);
    same stub shape as tests/test_retro_w1_3.py."""
    from app.services import database_service as db_mod
    from app.services import product_data_service as pds_mod

    def _refuse(*args, **kwargs):
        raise RuntimeError("zero-network: supabase stubbed in test_cost_meter_s74")

    return (
        patch.object(pds_mod, "get_admin_supabase_client", side_effect=_refuse),
        patch.object(db_mod, "get_admin_supabase_client", side_effect=_refuse),
    )


def _no_egress():
    """G3 (the netguard ratchet): the egress the cm13/cm14 harness reaches is
    the Shopify direct-discovery catalog fetch
    (``price_service._fetch_shopify_catalog`` -> curl_cffi GET
    ``https://<bh store>/products.json``) and, once that misses, the Algolia
    tier-2 catalog query (``algolia_service._algolia_query`` /
    ``_algolia_query_explicit`` -> curl_cffi POST ``<app>-dsn.algolia.net``);
    answer each with the empty shape the real fetcher returns on a miss so the
    two nodes make ZERO network attempts and the CI ratchet needs no new
    baseline row."""
    from curl_cffi import requests as curl_requests

    from app.services import algolia_service as algolia_mod

    async def _no_catalog(*args, **kwargs):
        return None

    async def _no_hits(*args, **kwargs):
        return []

    async def _no_explicit(*args, **kwargs):
        return None

    def _no_curl(self, *args, **kwargs):
        # The backstop under every later adapter rung (unbxd, woo, salla, occ,
        # magento, rest_json, noon ...): the SAME transport-error shape the
        # netguard's own block raises, which every adapter already swallows
        # into "no price"; the guard then has nothing to count.
        raise curl_requests.RequestsError("test_cost_meter_s74: curl_cffi egress stubbed (G3)")

    return (
        patch.object(price_mod, "_fetch_shopify_catalog", side_effect=_no_catalog),
        patch.object(algolia_mod, "_algolia_query", side_effect=_no_hits),
        patch.object(algolia_mod, "_algolia_query_explicit", side_effect=_no_explicit),
        patch.object(curl_requests.Session, "request", _no_curl),
        patch.object(curl_requests.AsyncSession, "request", _no_curl),
    )


def _assert_e2e_openai(result, client, entry):
    create = client.chat.completions.create
    assert isinstance(result, dict) and result.get("success") is True and "metadata" in result, (
        f"harness ({entry}): the compare did not reach a build: code={result.get('code')!r} "
        f"error={str(result.get('error'))[:120]!r} keys={sorted(result)[:14]}"
    )
    assert create.await_count > 0, f"harness ({entry}): the fake client was never dispatched"
    meta = result["metadata"]
    assert "openai" in meta, (
        f"{entry}: metadata.openai absent after {create.await_count} dispatches "
        f"(mutant M5/M6 or the ledger never started); metadata keys={sorted(meta)}"
    )
    openai = meta["openai"]
    requested = [c.kwargs.get("model") for c in create.await_args_list]
    assert openai["calls"] == create.await_count, (
        f"{entry}: calls {openai['calls']} != dispatches {create.await_count}"
    )
    assert set(openai["by_model"]) == set(requested), (
        f"{entry}: by_model {sorted(openai['by_model'])} != requested {sorted(set(requested))}"
    )
    for model in set(requested):
        assert openai["by_model"][model]["calls"] == requested.count(model)
    expected = round(sum(_UNIT_COST_1000_200[m] for m in requested), 6)
    assert openai["cost_usd"] is not None and openai["cost_usd"] > 0
    assert openai["cost_usd"] == pytest.approx(expected, abs=1.5e-6), (
        f"{entry}: cost_usd {openai['cost_usd']} != {expected} over {requested}"
    )
    assert openai["cost_complete"] is True
    assert openai["priced_calls"] == create.await_count
    assert openai["unpriced_calls"] == 0
    assert openai["prompt_tokens"] == 1000 * create.await_count
    assert openai["completion_tokens"] == 200 * create.await_count
    assert openai["basis"] == "list_price"
    assert openai["price_table_as_of"] == "2026-10-08"
    # total_cost is untouched by the unit (spec 0: byte-identical semantics).
    assert "total_cost" in meta
