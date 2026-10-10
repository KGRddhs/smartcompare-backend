"""COST-METER (#66, session 74/75) -- the OpenAI list-price table and the
per-request usage ledger.

Stdlib only, no app imports: this is a LEAF so ``api_budget_service`` (the one
chat-completion chokepoint, ``guarded_llm_create``) can record every served
response here without an import cycle, and ``response_builder`` / the admin
routes can read the summary shape from one place.

Price table source: https://openai.com/api/pricing/ -- the rates below are the
figures the owner read on that page on 2026-10-08 (PRICE_TABLE_AS_OF); the URL
was NOT fetched by the code or the tests. USD per 1M tokens, list price.
EXACT keys only (ruling CM7): a dated snapshot or a variant that is not in the
table prices to None -- never 0 -- so an unknown id can never read as free.

The ledger is a ContextVar bound to a fresh list at each compare entry
(``start_openai_ledger``); tasks spawned from the request copy the context at
spawn and hold the SAME list object, so every child append is visible to the
parent. ``record_openai_response`` NEVER raises (the whole body is guarded; a
usage that cannot be read records the call UNPRICED and logs the exception
type name only). ``summarize_openai_ledger``
turns the list into the additive ``metadata.openai`` dict; a ledger with zero
calls is a TRUE 0.0, a ledger whose calls all priced to None is None.
"""
from __future__ import annotations

import logging
from contextvars import ContextVar
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

PRICE_TABLE_AS_OF = "2026-10-08"

_GPT4O_RATES = {"input": 2.50, "cached_input": 1.25, "output": 10.00}
_GPT4O_MINI_RATES = {"input": 0.15, "cached_input": 0.075, "output": 0.60}

# https://openai.com/api/pricing/ as read by the owner on 2026-10-08.
PRICE_USD_PER_1M: Dict[str, Dict[str, float]] = {
    "gpt-4o": dict(_GPT4O_RATES),
    "gpt-4o-2024-08-06": dict(_GPT4O_RATES),
    "gpt-4o-2024-11-20": dict(_GPT4O_RATES),
    "gpt-4o-mini": dict(_GPT4O_MINI_RATES),
    "gpt-4o-mini-2024-07-18": dict(_GPT4O_MINI_RATES),
}

BASIS = "list_price"

_LEDGER: ContextVar[Optional[List[Dict[str, Any]]]] = ContextVar(
    "openai_usage_ledger", default=None
)


def price_row(model: Any) -> Optional[Dict[str, float]]:
    """The USD-per-1M row for an EXACT model id; None for anything else."""
    if not isinstance(model, str):
        return None
    return PRICE_USD_PER_1M.get(model)


def list_price_usd(
    model: Any,
    prompt_tokens: Any,
    completion_tokens: Any,
    cached_tokens: Any = 0,
) -> Optional[float]:
    """List price of one call; None when the model is unpriced or a token count
    is unknown. A None cached count counts as 0 (CM8); cached tokens above the
    prompt count clamp the uncached share to 0."""
    row = price_row(model)
    if row is None or prompt_tokens is None or completion_tokens is None:
        return None
    cached = cached_tokens or 0
    uncached = max(prompt_tokens - cached, 0)
    return (
        uncached * row["input"]
        + cached * row["cached_input"]
        + completion_tokens * row["output"]
    ) / 1e6


def start_openai_ledger() -> List[Dict[str, Any]]:
    """Bind a FRESH ledger list to the current context and return it (never
    reuses an existing one -- the camera route keeps its own list, G5)."""
    ledger: List[Dict[str, Any]] = []
    _LEDGER.set(ledger)
    return ledger


def _tok(value: Any) -> Optional[int]:
    """An int token count, else None (a MagicMock usage records None)."""
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return None


def _cached_tokens(usage: Any) -> Optional[int]:
    """``usage.prompt_tokens_details.cached_tokens`` else
    ``usage.prompt_tokens_cached`` else 0 (mirrors openai_service telemetry);
    a None count is 0."""
    details = getattr(usage, "prompt_tokens_details", None)
    cached = _tok(getattr(details, "cached_tokens", None)) if details is not None else None
    if cached is None:
        cached = _tok(getattr(usage, "prompt_tokens_cached", None))
    return cached if cached is not None else 0


def _unpriced_entry(model: Any) -> Dict[str, Any]:
    """The entry for a served call whose usage could not be read (ruling X6):
    the REQUESTED model id, every token count and the cost None, so the call
    still counts (``unpriced_calls``, ``cost_complete`` False) instead of
    vanishing from the ledger."""
    return {
        "model": "" if model is None else str(model),
        "prompt_tokens": None,
        "completion_tokens": None,
        "cached_tokens": None,
        "cost_usd": None,
    }


def record_openai_response(model: Any, response: Any) -> None:
    """Append one entry for a served chat completion to the bound ledger; a
    no-op when no ledger is bound. Never raises: when reading the usage
    raises after the ledger was obtained, the call is recorded UNPRICED
    (X6) and the skip is logged by exception type name only."""
    ledger = None
    try:
        ledger = _LEDGER.get()
        if ledger is None:
            return
        usage = getattr(response, "usage", None)
        if usage is None:
            prompt = completion = cached = None
        else:
            prompt = _tok(getattr(usage, "prompt_tokens", None))
            completion = _tok(getattr(usage, "completion_tokens", None))
            cached = _cached_tokens(usage)
        ledger.append({
            "model": str(model) if model is not None else "",
            "prompt_tokens": prompt,
            "completion_tokens": completion,
            "cached_tokens": cached,
            "cost_usd": list_price_usd(model, prompt, completion, cached),
        })
    except Exception as exc:  # noqa: BLE001 -- the recorder never raises
        logger.debug(
            "[openai_pricing] usage unreadable (%s); recorded as an unpriced call",
            type(exc).__name__,
        )
        if ledger is not None:
            try:
                ledger.append(_unpriced_entry(model))
            except Exception:  # noqa: BLE001 -- the recorder never raises
                pass


def _sum_costs(values: List[Optional[float]]) -> Optional[float]:
    priced = [v for v in values if v is not None]
    if not priced:
        return None
    return round(sum(priced), 6)


def summarize_openai_ledger(ledger: Optional[List[Dict[str, Any]]]) -> Optional[Dict[str, Any]]:
    """The additive ``metadata.openai`` dict for a ledger; None for None."""
    if ledger is None:
        return None
    calls = len(ledger)
    priced_calls = sum(1 for e in ledger if e.get("cost_usd") is not None)
    by_model: Dict[str, Dict[str, Any]] = {}
    for e in ledger:
        key = str(e.get("model") or "")
        row = by_model.setdefault(key, {
            "calls": 0, "prompt_tokens": 0, "cached_tokens": 0, "completion_tokens": 0,
            "cost_usd": None, "_costs": [],
        })
        row["calls"] += 1
        for field in ("prompt_tokens", "cached_tokens", "completion_tokens"):
            if e.get(field) is not None:
                row[field] += e[field]
        row["_costs"].append(e.get("cost_usd"))
    for row in by_model.values():
        row["cost_usd"] = _sum_costs(row.pop("_costs"))
    if calls == 0:
        cost_usd: Optional[float] = 0.0
    elif priced_calls == 0:
        cost_usd = None
    else:
        cost_usd = _sum_costs([e.get("cost_usd") for e in ledger])
    return {
        "calls": calls,
        "priced_calls": priced_calls,
        "unpriced_calls": calls - priced_calls,
        "prompt_tokens": sum(e["prompt_tokens"] for e in ledger if e.get("prompt_tokens") is not None),
        "cached_tokens": sum(e["cached_tokens"] for e in ledger if e.get("cached_tokens") is not None),
        "completion_tokens": sum(e["completion_tokens"] for e in ledger if e.get("completion_tokens") is not None),
        "cost_usd": cost_usd,
        "cost_complete": priced_calls == calls,
        "by_model": by_model,
        "basis": BASIS,
        "price_table_as_of": PRICE_TABLE_AS_OF,
    }


def _int_of(value: Any) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def merge_openai_summaries(a: Optional[Dict[str, Any]], b: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Merge two summaries (G5: the camera route's vision ledger + the compare's
    own ``metadata.openai``). None-aware: None + x = x; counts and token sums
    add; ``cost_usd`` is the sum of the non-None costs (None only when both
    are None); ``cost_complete`` is a AND b; ``by_model`` merges per key."""
    if a is None:
        return b
    if b is None:
        return a
    by_model: Dict[str, Dict[str, Any]] = {}
    for src in (a.get("by_model") or {}, b.get("by_model") or {}):
        for key, row in src.items():
            tgt = by_model.setdefault(key, {
                "calls": 0, "prompt_tokens": 0, "cached_tokens": 0, "completion_tokens": 0,
                "cost_usd": None,
            })
            for field in ("calls", "prompt_tokens", "cached_tokens", "completion_tokens"):
                tgt[field] += _int_of((row or {}).get(field))
            tgt["cost_usd"] = _sum_costs([tgt["cost_usd"], (row or {}).get("cost_usd")])
    merged: Dict[str, Any] = {}
    for field in ("calls", "priced_calls", "unpriced_calls",
                  "prompt_tokens", "cached_tokens", "completion_tokens"):
        merged[field] = _int_of(a.get(field)) + _int_of(b.get(field))
    merged["cost_usd"] = _sum_costs([a.get("cost_usd"), b.get("cost_usd")])
    merged["cost_complete"] = bool(a.get("cost_complete")) and bool(b.get("cost_complete"))
    merged["by_model"] = by_model
    merged["basis"] = a.get("basis") or b.get("basis") or BASIS
    merged["price_table_as_of"] = a.get("price_table_as_of") or b.get("price_table_as_of") or PRICE_TABLE_AS_OF
    return merged
