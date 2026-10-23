"""LLM-LEDGER-V2 (S81-03, ENABLE_LLM_LEDGER_V2): a provider-neutral LLM cost ledger.

One leaf prices ANY provider through ``price_call``: the OpenAI rows are the
``openai_pricing`` table itself (re-exported, priced by delegation so the float
is bit-identical to the OpenAI ledger's own cost), the Anthropic rows are the
claude-haiku-5-5 and claude-sonnet-5-5 list prices read from the
platform.claude.com pricing page on 2026-10-22 (research digest R1, session 81),
literals with a read date, never fetched. The leaf also normalises every call
into one usage record (``LLM_RECORD_KEYS``), summarises records into the additive
``metadata.llm`` (a SUMMARY only, ruling R-S03-1: the per-call records belong to
S81-22 compare_runs), prices each call ``_track_gpt_cost`` tracks from the bound
ledger entry it came from (claims in a bounded module registry, gate ruling G-1)
and builds the row shape of the off-clock spend table (migration 050).

Imports: the stdlib and ``app.services.openai_pricing`` only (a stdlib leaf).
Every consumer reaches this module through the module attribute
(``from app.services import llm_pricing as _llm_pricing``, ruling BL4), so a
recorder patched on the module sees every call. The flag is read per call by
``llm_ledger_v2_enabled`` and is the first statement of every gated consumer
branch; with it OFF no function here is called and every body is byte-identical.
"""
from __future__ import annotations

import math
import os
import threading
from contextvars import ContextVar
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple

from app.services import openai_pricing as _openai_pricing

FLAG = "ENABLE_LLM_LEDGER_V2"

# --- Anthropic list prices, USD per 1M tokens (R1, read 2026-10-22) ----------
# Cache write 5 minutes = 1.25x input, 1 hour = 2x input, cache read 0.1x input.
# Sonnet's cache read is 0.10 (the critic correction of the bundled 0.20).
ANTHROPIC_PRICE_TABLE_AS_OF = "2026-10-22"
ANTHROPIC_PRICE_USD_PER_1M: Dict[str, Dict[str, float]] = {
    "claude-haiku-5-5": {
        "input": 0.10, "output": 0.50, "cache_read": 0.01,
        "cache_write_5m": 0.125, "cache_write_1h": 0.20,
    },
    "claude-sonnet-5-5": {
        "input": 2.00, "output": 10.00, "cache_read": 0.10,
        "cache_write_5m": 2.50, "cache_write_1h": 4.00,
    },
}

# Long context. A request is measured by its WHOLE prompt (input + cache read +
# cache writes). Haiku above 100,000 prompt tokens (strictly) is priced at the
# higher tier for the whole request, cache reads included (R1, read
# 2026-10-22: 0.50 / 2.50); the tier's cache rates are DERIVED from the R1
# multipliers of the tier input rate (ruling R-S03-4): read 0.1x, 5-minute
# write 1.25x, 1-hour write 2x. No Sonnet long-context tier is modelled: a
# Sonnet request above 200,000 prompt tokens is unpriced (None, gate ruling
# G-2). S81-07's pricing read re-verifies both boundaries and every Anthropic
# row BEFORE the first Anthropic flip; a difference lands as a data PR.
HAIKU_LONG_CONTEXT: Dict[str, Any] = {
    "model": "claude-haiku-5-5",
    "threshold_prompt_tokens": 100000,
    "input": 0.50,
    "output": 2.50,
    "cache_read": 0.05,       # derived 0.1x of the tier input (R1, 2026-10-22)
    "cache_write_5m": 0.625,  # derived 1.25x of the tier input (R1, 2026-10-22)
    "cache_write_1h": 1.00,   # derived 2x of the tier input (R1, 2026-10-22)
}
# The prompt size above which a model's flat row stops applying: the Haiku tier
# row replaces it, any other model is unpriced.
LONG_CONTEXT_THRESHOLD_PROMPT_TOKENS: Dict[str, int] = {
    "claude-haiku-5-5": 100000,
    "claude-sonnet-5-5": 200000,
}
_LONG_CONTEXT_ROWS: Dict[str, Dict[str, Any]] = {"claude-haiku-5-5": HAIKU_LONG_CONTEXT}

# Server web search: 10 USD per 1,000 requests (server_tool_use.web_search_requests);
# the Batch API halves token charges only, never the search fee (R1).
WEB_SEARCH_USD_PER_REQUEST = 0.01
BATCH_TOKEN_MULTIPLIER = 0.5

# --- OpenAI: THE openai_pricing objects (re-exported, never re-typed) --------
OPENAI_PRICE_USD_PER_1M = _openai_pricing.PRICE_USD_PER_1M
OPENAI_PRICE_TABLE_AS_OF = _openai_pricing.PRICE_TABLE_AS_OF

PRICE_TABLE_AS_OF = {"openai": OPENAI_PRICE_TABLE_AS_OF, "anthropic": ANTHROPIC_PRICE_TABLE_AS_OF}
BASIS = "list_price"
SCHEMA_VERSION = 1

# The base _track_gpt_cost / vision literals (the gpt-4o-mini input / output
# rates per 1M tokens), kept as bare floats so the leaf names no model id.
LEGACY_TRACK_RATES_USD_PER_1M = (0.15, 0.60)

# The provider-neutral usage record. prompt_tokens is the normalised TOTAL input
# (OpenAI prompt_tokens; Anthropic input + cache read + cache writes) so every
# existing prompt_tokens reader keeps its meaning; input_tokens is the uncached
# input billed at the base rate.
LLM_RECORD_KEYS = (
    "provider", "model", "role", "input_tokens", "output_tokens", "cache_read_tokens",
    "cache_write_5m_tokens", "cache_write_1h_tokens", "web_search_requests",
    "prompt_tokens", "completion_tokens", "cost_usd", "latency_ms", "stop_reason", "batch",
)
_TOKEN_KEYS = (
    "prompt_tokens", "completion_tokens", "input_tokens", "output_tokens",
    "cache_read_tokens", "cache_write_5m_tokens", "cache_write_1h_tokens",
)

# OpenTelemetry GenAI names for the record keys that have one. Internal only (it
# reaches no response). Ruling R-S03-8: the names are
# unverified against the OpenTelemetry GenAI semantic conventions; S81-22 verifies
# with a read-only documentation fetch.
OTEL_GENAI_ATTRIBUTES = {
    "provider": "gen_ai.provider.name",
    "model": "gen_ai.request.model",
    "prompt_tokens": "gen_ai.usage.input_tokens",
    "completion_tokens": "gen_ai.usage.output_tokens",
    "stop_reason": "gen_ai.response.finish_reasons",
}

# The off-clock spend table (migration 050) and its vocabularies (the S81-04 lanes).
SPEND_LANES = ("live", "escalation", "search", "offclock")
SPEND_MODES = ("sync", "batch")
SPEND_PROVIDERS = ("openai", "anthropic")
SPEND_LEDGER_COLUMNS = (
    "job", "lane", "mode", "provider", "model", "role", "provider_batch_id", "request_count",
    "input_tokens", "output_tokens", "cache_read_tokens", "cache_write_5m_tokens",
    "cache_write_1h_tokens", "web_search_requests", "cost_usd", "cost_complete", "basis",
    "price_table_as_of", "period_start", "period_end",
)
_SPEND_SUM_KEYS = (
    "input_tokens", "output_tokens", "cache_read_tokens", "cache_write_5m_tokens",
    "cache_write_1h_tokens", "web_search_requests",
)

# The per-request ledger of NON-OpenAI calls (ruling R-S03-7: OpenAI calls stay on
# the openai_pricing ledger). Bound by S81-06 beside start_openai_ledger(); until
# then nothing binds it and record_llm_call is a no-op (stated limit L3).
_LLM_LEDGER: ContextVar[Optional[List[Dict[str, Any]]]] = ContextVar("llm_usage_ledger", default=None)

# Claims (gate ruling G-1): which bound ledger entries a tracked call already
# priced. Keyed by the IDENTITY of the bound (openai ledger, llm ledger) lists and
# holding strong references to both, so an id cannot be reused while its entry
# lives; a module registry (not a ContextVar) because the explicit-pair, stream
# and camera compares track their first calls inside asyncio.gather child tasks,
# whose ContextVar sets never reach the builder. Bounded: the oldest entry is
# evicted past _CLAIM_REGISTRY_MAX.
_CLAIM_REGISTRY: Dict[Tuple[int, int], Dict[str, Any]] = {}
_CLAIM_REGISTRY_MAX = 256
_CLAIM_LOCK = threading.Lock()


def llm_ledger_v2_enabled() -> bool:
    """The house idiom, read per call (never cached)."""
    return os.getenv(FLAG, "false").strip().lower() in ("true", "1", "yes", "on")


def provider_of(model: Any) -> Optional[str]:
    """'anthropic' for a claude- id, 'openai' for a gpt- or omni-moderation- id, else None."""
    if not isinstance(model, str):
        return None
    if model.startswith("claude-"):
        return "anthropic"
    if model.startswith("gpt-") or model.startswith("omni-moderation-"):
        return "openai"
    return None


def _count_ok(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def price_call(
    provider: Any,
    model: Any,
    *,
    input_tokens: Any = 0,
    output_tokens: Any = 0,
    cache_read_tokens: Any = 0,
    cache_write_5m_tokens: Any = 0,
    cache_write_1h_tokens: Any = 0,
    web_search_requests: Any = 0,
    batch: bool = False,
) -> Optional[float]:
    """The unrounded list price in USD of one call, or None (never 0) when it
    cannot be priced: a count that is not a non-negative non-bool int, an id
    outside the EXACT rows, an unknown provider, an OpenAI call carrying a cache
    write / web search / batch (no cited OpenAI rate), a Sonnet request above
    200,000 prompt tokens."""
    counts = (input_tokens, output_tokens, cache_read_tokens, cache_write_5m_tokens,
              cache_write_1h_tokens, web_search_requests)
    if not all(_count_ok(n) for n in counts):
        return None
    if provider == "openai":
        if cache_write_5m_tokens or cache_write_1h_tokens or web_search_requests or batch:
            return None
        return _openai_pricing.list_price_usd(
            model, input_tokens + cache_read_tokens, output_tokens, cache_read_tokens,
        )
    if provider != "anthropic" or not isinstance(model, str):
        return None
    row = ANTHROPIC_PRICE_USD_PER_1M.get(model)
    if row is None:
        return None
    prompt_total = input_tokens + cache_read_tokens + cache_write_5m_tokens + cache_write_1h_tokens
    if prompt_total > LONG_CONTEXT_THRESHOLD_PROMPT_TOKENS[model]:
        row = _LONG_CONTEXT_ROWS.get(model)
        if row is None:
            return None
    tokens = (input_tokens * row["input"] + output_tokens * row["output"]
              + cache_read_tokens * row["cache_read"]
              + cache_write_5m_tokens * row["cache_write_5m"]
              + cache_write_1h_tokens * row["cache_write_1h"])
    return (tokens / 1e6) * (BATCH_TOKEN_MULTIPLIER if batch else 1.0) + web_search_requests * WEB_SEARCH_USD_PER_REQUEST


def legacy_track_cost_usd(prompt_tokens: Any, completion_tokens: Any) -> float:
    """EXACTLY the base _track_gpt_cost / vision expression (same operands, same
    operation order), so the float is bit-identical to the base estimate."""
    return (prompt_tokens * 0.15 / 1_000_000) + (completion_tokens * 0.60 / 1_000_000)


def _usage_int(obj: Any, name: str) -> int:
    value = getattr(obj, name, None) if obj is not None else None
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def _usage_cached(usage: Any) -> int:
    """The cached prompt tokens of an OpenAI usage (the openai_pricing rule,
    restated here: prompt_tokens_details.cached_tokens, else
    prompt_tokens_cached, else 0)."""
    details = getattr(usage, "prompt_tokens_details", None)
    cached = getattr(details, "cached_tokens", None) if details is not None else None
    if not (isinstance(cached, int) and not isinstance(cached, bool)):
        cached = getattr(usage, "prompt_tokens_cached", None)
    return cached if isinstance(cached, int) and not isinstance(cached, bool) else 0


def openai_usage_cost_usd(model: Any, usage: Any) -> float:
    """The list price of one OpenAI response's usage on ``model`` (cached
    tokens at the cached rate); the base estimate when the model is unpriced;
    0.0 for a None usage. Always a float (the vision / disambiguation fields)."""
    if usage is None:
        return 0.0
    prompt = _usage_int(usage, "prompt_tokens")
    completion = _usage_int(usage, "completion_tokens")
    cached = _usage_cached(usage)
    priced = price_call("openai", model, input_tokens=max(prompt - cached, 0),
                        cache_read_tokens=min(cached, prompt), output_tokens=completion)
    return priced if priced is not None else legacy_track_cost_usd(prompt, completion)


def current_openai_ledger() -> Optional[List[Dict[str, Any]]]:
    """The bound openai_pricing ledger (the one sanctioned read of its ContextVar)."""
    return _openai_pricing._LEDGER.get()


def current_llm_records() -> Optional[List[Dict[str, Any]]]:
    """The bound non-OpenAI ledger, or None."""
    return _LLM_LEDGER.get()


def _claims_for(openai_ledger: Any, llm_records: Any) -> Dict[str, Any]:
    """The claims entry of the bound pair, created (fresh) when absent or stale."""
    key = (id(openai_ledger), id(llm_records))
    with _CLAIM_LOCK:
        claims = _CLAIM_REGISTRY.get(key)
        if claims is None or claims["ledger"] is not openai_ledger or claims["llm"] is not llm_records:
            claims = {"ledger": openai_ledger, "llm": llm_records, "taken": set()}
            _CLAIM_REGISTRY[key] = claims
            while len(_CLAIM_REGISTRY) > _CLAIM_REGISTRY_MAX:
                _CLAIM_REGISTRY.pop(next(iter(_CLAIM_REGISTRY)))
        return claims


def _taken_for(openai_ledger: Any, llm_records: Any) -> frozenset:
    """A read-only snapshot of the pair's claimed keys (empty when none)."""
    with _CLAIM_LOCK:
        claims = _CLAIM_REGISTRY.get((id(openai_ledger), id(llm_records)))
        if claims is None or claims["ledger"] is not openai_ledger or claims["llm"] is not llm_records:
            return frozenset()
        return frozenset(claims["taken"])


def _finite_cost(value: Any) -> Optional[float]:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if not math.isfinite(value) or value < 0:
        return None
    return float(value)


def tracked_call_cost_usd(usage: Dict[str, Any]) -> Optional[float]:
    """The _track_gpt_cost ON body: the list price of the bound ledger entry this
    tracked call came from, or None (the caller then adds the base estimate).

    The match is the FIRST unclaimed candidate (the OpenAI ledger entries, then
    the llm-ledger records) whose prompt_tokens and completion_tokens equal the
    usage's (the base coercion ``usage.get(k, 0) or 0``); each candidate is
    claimed at most once and the entries are never mutated. Contract (gate
    ruling G-5): a float for a claimed priced candidate, None for no bound
    ledger, no match, or a claimed candidate that is unpriced. A non-dict
    usage raises AttributeError exactly as the base body does."""
    prompt = usage.get("prompt_tokens", 0) or 0
    completion = usage.get("completion_tokens", 0) or 0
    ledger = current_openai_ledger()
    records = current_llm_records()
    if ledger is None and records is None:
        return None
    claims = _claims_for(ledger, records)
    candidates = [(("openai", i), e) for i, e in enumerate(ledger or [])]
    candidates += [(("llm", i), r) for i, r in enumerate(records or [])]
    with _CLAIM_LOCK:
        for key, cand in candidates:
            if key in claims["taken"] or not isinstance(cand, dict):
                continue
            if cand.get("prompt_tokens") == prompt and cand.get("completion_tokens") == completion:
                claims["taken"].add(key)
                return _finite_cost(cand.get("cost_usd"))
    return None


def unclaimed_openai_cost_usd() -> float:
    """The list price of every bound OpenAI-ledger entry no tracked call claimed
    (ruling R-S03-2: the builder adds it to metadata.total_cost under ON);
    unpriced entries add nothing; 0.0 with no bound ledger. Read-only."""
    ledger = current_openai_ledger()
    if not ledger:
        return 0.0
    taken = _taken_for(ledger, current_llm_records())
    total = 0.0
    for i, entry in enumerate(ledger):
        if ("openai", i) in taken or not isinstance(entry, dict):
            continue
        cost = _finite_cost(entry.get("cost_usd"))
        if cost is not None:
            total += cost
    return total


def _blank_record(provider: str, model: Any, role: Any = None, latency_ms: Any = None,
                  stop_reason: Any = None, batch: Any = False) -> Dict[str, Any]:
    record: Dict[str, Any] = {key: None for key in LLM_RECORD_KEYS}
    record.update({
        "provider": provider,
        "model": "" if model is None else str(model),
        "role": role,
        "web_search_requests": 0,
        "latency_ms": latency_ms,
        "stop_reason": stop_reason,
        "batch": bool(batch),
    })
    return record


def openai_entry_record(entry: Dict[str, Any]) -> Dict[str, Any]:
    """An openai_pricing ledger entry as a usage record (role, latency and stop
    reason None: the capture point is guarded_llm_create, stated limit L2)."""
    record = _blank_record("openai", entry.get("model"))
    prompt = entry.get("prompt_tokens")
    completion = entry.get("completion_tokens")
    cached = entry.get("cached_tokens") or 0
    if _count_ok(prompt) and _count_ok(completion) and _count_ok(cached):
        cached = min(cached, prompt)
        record.update({
            "prompt_tokens": prompt,
            "completion_tokens": completion,
            "input_tokens": max(prompt - cached, 0),
            "output_tokens": completion,
            "cache_read_tokens": cached,
            "cache_write_5m_tokens": 0,
            "cache_write_1h_tokens": 0,
        })
        record["cost_usd"] = price_call("openai", record["model"], input_tokens=record["input_tokens"],
                                        cache_read_tokens=cached, output_tokens=completion)
    return record


def _field(obj: Any, name: str) -> Any:
    if isinstance(obj, dict):
        return obj.get(name)
    return getattr(obj, name, None)


def anthropic_usage_record(model: Any, usage: Any, *, role: Any = None, latency_ms: Any = None,
                           stop_reason: Any = None, batch: bool = False) -> Dict[str, Any]:
    """An Anthropic Messages usage (object or dict) as a usage record, for S81-06.

    Reads input_tokens, output_tokens, cache_read_input_tokens,
    cache_creation_input_tokens, the cache_creation breakdown
    (ephemeral_5m_input_tokens / ephemeral_1h_input_tokens) and
    server_tool_use.web_search_requests; a missing value counts 0. Without a
    breakdown every cache write counts as 5-minute (the default TTL, stated
    limit L7); a breakdown summing below cache_creation_input_tokens counts the
    remainder as 5-minute writes (C12). An unreadable usage gives every token
    and the cost None. Never raises."""
    record = _blank_record("anthropic", model, role, latency_ms, stop_reason, batch)
    if usage is None:
        return record
    try:
        values = [(_field(usage, name) or 0) for name in (
            "input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")]
        tool_use = _field(usage, "server_tool_use")
        searches = (_field(tool_use, "web_search_requests") or 0) if tool_use is not None else 0
        values.append(searches)
        if not all(_count_ok(v) for v in values):
            return record
        inp, out, read, creation, searches = values
        breakdown = _field(usage, "cache_creation")
        if breakdown:
            write_5m = _field(breakdown, "ephemeral_5m_input_tokens") or 0
            write_1h = _field(breakdown, "ephemeral_1h_input_tokens") or 0
            if not (_count_ok(write_5m) and _count_ok(write_1h)):
                return record
            if write_5m + write_1h < creation:
                write_5m += creation - (write_5m + write_1h)
        else:
            write_5m, write_1h = creation, 0
    except Exception:  # noqa: BLE001 -- an unreadable usage is an unpriced record
        return record
    record.update({
        "input_tokens": inp,
        "output_tokens": out,
        "cache_read_tokens": read,
        "cache_write_5m_tokens": write_5m,
        "cache_write_1h_tokens": write_1h,
        "web_search_requests": searches,
        "prompt_tokens": inp + read + write_5m + write_1h,
        "completion_tokens": out,
    })
    record["cost_usd"] = price_call(
        "anthropic", model, input_tokens=inp, output_tokens=out, cache_read_tokens=read,
        cache_write_5m_tokens=write_5m, cache_write_1h_tokens=write_1h,
        web_search_requests=searches, batch=batch,
    )
    return record


def start_llm_ledger() -> List[Dict[str, Any]]:
    """Bind a FRESH non-OpenAI ledger for this request and return it (S81-06)."""
    ledger: List[Dict[str, Any]] = []
    _LLM_LEDGER.set(ledger)
    return ledger


def record_llm_call(record: Any) -> None:
    """Append a copy of ``record`` (LLM_RECORD_KEYS only) to the bound llm
    ledger; a no-op when none is bound. Never raises."""
    try:
        ledger = _LLM_LEDGER.get()
        if ledger is None:
            return
        ledger.append({key: record.get(key) for key in LLM_RECORD_KEYS})
    except Exception:  # noqa: BLE001 -- the recorder never raises
        return


def _sum_costs(values: Iterable[Any]) -> Optional[float]:
    priced = [v for v in values if v is not None]
    return round(sum(priced), 6) if priced else None


def summarize_llm_records(records: Any) -> Dict[str, Any]:
    """The metadata.llm summary of a record list (ruling R-S03-1: no per-call
    records; bounded by the number of distinct providers and models). cost_usd
    is 0.0 for zero calls, None when no call is priced, else round(sum, 6);
    token sums skip None."""
    records = [r for r in (records or []) if isinstance(r, dict)]
    calls = len(records)
    priced = sum(1 for r in records if r.get("cost_usd") is not None)
    out: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "calls": calls,
        "priced_calls": priced,
        "unpriced_calls": calls - priced,
    }
    for key in _TOKEN_KEYS + ("web_search_requests",):
        out[key] = sum(r[key] for r in records if _count_ok(r.get(key)))
    if calls == 0:
        out["cost_usd"] = 0.0
    elif priced == 0:
        out["cost_usd"] = None
    else:
        out["cost_usd"] = _sum_costs(r.get("cost_usd") for r in records)
    out["cost_complete"] = priced == calls
    by_provider: Dict[str, Dict[str, Any]] = {}
    by_model: Dict[str, Dict[str, Any]] = {}
    for r in records:
        provider = by_provider.setdefault(str(r.get("provider") or ""), {"calls": 0, "_costs": []})
        provider["calls"] += 1
        provider["_costs"].append(r.get("cost_usd"))
        model = by_model.setdefault(str(r.get("model") or ""), {
            "provider": r.get("provider"), "calls": 0, "prompt_tokens": 0,
            "completion_tokens": 0, "cache_read_tokens": 0, "_costs": [],
        })
        model["calls"] += 1
        for key in ("prompt_tokens", "completion_tokens", "cache_read_tokens"):
            if _count_ok(r.get(key)):
                model[key] += r[key]
        model["_costs"].append(r.get("cost_usd"))
    for entry in list(by_provider.values()) + list(by_model.values()):
        entry["cost_usd"] = _sum_costs(entry.pop("_costs"))
    out["by_provider"] = by_provider
    out["by_model"] = by_model
    out["basis"] = BASIS
    out["price_table_as_of"] = dict(PRICE_TABLE_AS_OF)
    return out


def _int_of(value: Any) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def llm_summary_from_openai(openai_usage: Any) -> Optional[Dict[str, Any]]:
    """A metadata.openai summary (openai_pricing.summarize_openai_ledger) mapped
    1:1 into the metadata.llm shape; None for None."""
    if not isinstance(openai_usage, dict):
        return None
    u = openai_usage
    calls = _int_of(u.get("calls"))
    prompt = _int_of(u.get("prompt_tokens"))
    completion = _int_of(u.get("completion_tokens"))
    cached = _int_of(u.get("cached_tokens"))
    out: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "calls": calls,
        "priced_calls": _int_of(u.get("priced_calls")),
        "unpriced_calls": _int_of(u.get("unpriced_calls")),
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "input_tokens": max(prompt - cached, 0),
        "output_tokens": completion,
        "cache_read_tokens": cached,
        "cache_write_5m_tokens": 0,
        "cache_write_1h_tokens": 0,
        "web_search_requests": 0,
        "cost_usd": u.get("cost_usd"),
        "cost_complete": bool(u.get("cost_complete")),
        "by_provider": {"openai": {"calls": calls, "cost_usd": u.get("cost_usd")}} if calls else {},
        "by_model": {},
        "basis": BASIS,
        "price_table_as_of": dict(PRICE_TABLE_AS_OF),
    }
    models = u.get("by_model")
    for model, row in (models.items() if isinstance(models, dict) else ()):
        row = row if isinstance(row, dict) else {}
        out["by_model"][str(model)] = {
            "provider": "openai",
            "calls": _int_of(row.get("calls")),
            "prompt_tokens": _int_of(row.get("prompt_tokens")),
            "completion_tokens": _int_of(row.get("completion_tokens")),
            "cache_read_tokens": _int_of(row.get("cached_tokens")),
            "cost_usd": row.get("cost_usd"),
        }
    return out


def merge_llm_summaries(a: Optional[Dict[str, Any]], b: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """None-aware merge (the merge_openai_summaries rules): None + x = x; counts
    and token sums add; cost_usd is the sum of the non-None costs (None only
    when both are None); cost_complete is a AND b; by_provider / by_model merge
    per key (ints add, cost_usd as the top level)."""
    if a is None:
        return b
    if b is None:
        return a
    out: Dict[str, Any] = {"schema_version": SCHEMA_VERSION}
    for key in ("calls", "priced_calls", "unpriced_calls") + _TOKEN_KEYS + ("web_search_requests",):
        out[key] = _int_of(a.get(key)) + _int_of(b.get(key))
    out["cost_usd"] = _sum_costs([a.get("cost_usd"), b.get("cost_usd")])
    out["cost_complete"] = bool(a.get("cost_complete")) and bool(b.get("cost_complete"))
    for field in ("by_provider", "by_model"):
        merged: Dict[str, Dict[str, Any]] = {}
        for src in (a.get(field) or {}, b.get(field) or {}):
            for key, row in src.items():
                row = row if isinstance(row, dict) else {}
                target = merged.get(key)
                if target is None:
                    merged[key] = dict(row)
                    continue
                for name, value in row.items():
                    if name == "cost_usd":
                        target["cost_usd"] = _sum_costs([target.get("cost_usd"), value])
                    elif isinstance(value, int) and not isinstance(value, bool):
                        target[name] = _int_of(target.get(name)) + value
        out[field] = merged
    out["basis"] = a.get("basis") or b.get("basis") or BASIS
    out["price_table_as_of"] = a.get("price_table_as_of") or b.get("price_table_as_of") or dict(PRICE_TABLE_AS_OF)
    return out


def build_llm_metadata(openai_usage: Any) -> Optional[Dict[str, Any]]:
    """The builder's one call: the metadata.llm summary for a response that
    carries ``openai_usage``; None when it is None. The OpenAI part is
    summarised from the bound ledger's entries when that ledger summarises to
    exactly ``openai_usage`` (verified), else mapped from ``openai_usage``
    itself; the non-OpenAI records of a bound llm ledger are merged in
    (records whose provider is openai are dropped, R-S03-7, so nothing counts
    twice)."""
    if openai_usage is None:
        return None
    bound = current_openai_ledger()
    if bound is not None and _openai_pricing.summarize_openai_ledger(bound) == openai_usage:
        openai_part = summarize_llm_records([openai_entry_record(e) for e in bound])
    else:
        openai_part = llm_summary_from_openai(openai_usage)
    records = current_llm_records()
    llm_part = None
    if records is not None:
        others = [r for r in records if isinstance(r, dict) and r.get("provider") != "openai"]
        if others:
            llm_part = summarize_llm_records(others)
    return merge_llm_summaries(openai_part, llm_part)


def _text_ok(value: Any, low: int, high: int) -> bool:
    return isinstance(value, str) and low <= len(value) <= high


def spend_ledger_row(
    *,
    job: Any,
    lane: Any,
    mode: Any,
    provider: Any,
    model: Any,
    records: Any,
    role: Any = None,
    provider_batch_id: Any = None,
    period_start: Any = None,
    period_end: Any = None,
) -> Dict[str, Any]:
    """One public.llm_spend_ledger row (keys exactly SPEND_LEDGER_COLUMNS) for a
    batch or cron job's records of ONE provider and model. Raises ValueError on
    any invalid input (the off-clock writers S81-16 / S81-22 are the only
    callers; the live path never calls it)."""
    if not _text_ok(job, 1, 64):
        raise ValueError("spend_ledger_row: job must be a str of 1-64 characters")
    if lane not in SPEND_LANES:
        raise ValueError("spend_ledger_row: unknown lane")
    if mode not in SPEND_MODES:
        raise ValueError("spend_ledger_row: unknown mode")
    if provider not in SPEND_PROVIDERS:
        raise ValueError("spend_ledger_row: unknown provider")
    if not _text_ok(model, 1, 64):
        raise ValueError("spend_ledger_row: model must be a str of 1-64 characters")
    if role is not None and not _text_ok(role, 1, 32):
        raise ValueError("spend_ledger_row: role must be None or a str of 1-32 characters")
    if provider_batch_id is not None and not _text_ok(provider_batch_id, 1, 128):
        raise ValueError("spend_ledger_row: provider_batch_id must be None or a str of 1-128 characters")
    for period in (period_start, period_end):
        if period is not None and not isinstance(period, datetime):
            raise ValueError("spend_ledger_row: a period must be None or a datetime")
    if not isinstance(records, (list, tuple)):
        raise ValueError("spend_ledger_row: records must be a list")
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("spend_ledger_row: every record must be a dict")
        if record.get("provider") != provider or record.get("model") != model:
            raise ValueError("spend_ledger_row: a record's provider or model differs")
        if (mode == "batch") != (record.get("batch") is True):
            raise ValueError("spend_ledger_row: a record's batch flag contradicts the mode")
    row: Dict[str, Any] = {
        "job": job,
        "lane": lane,
        "mode": mode,
        "provider": provider,
        "model": model,
        "role": role,
        "provider_batch_id": provider_batch_id,
        "request_count": len(records),
    }
    for key in _SPEND_SUM_KEYS:
        row[key] = sum(r[key] for r in records if _count_ok(r.get(key)))
    priced = [r.get("cost_usd") for r in records if r.get("cost_usd") is not None]
    row["cost_usd"] = 0.0 if not records else (round(sum(priced), 6) if priced else None)
    row["cost_complete"] = all(r.get("cost_usd") is not None for r in records)
    row["basis"] = BASIS
    row["price_table_as_of"] = PRICE_TABLE_AS_OF[provider]
    row["period_start"] = period_start.isoformat() if period_start is not None else None
    row["period_end"] = period_end.isoformat() if period_end is not None else None
    return row
