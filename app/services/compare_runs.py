"""S81-22 COMPARE-RUNS: one de-identified run row per DELIVERED compare.

Dark behind ENABLE_COMPARE_RUN_LEDGER (default OFF, read per call as the first statement
of record_compare_run, after its docstring): flag OFF reads no state, schedules nothing and
logs nothing. Flag ON, each of the five delivery exits (text POST / GET / stream, camera,
URL) makes ONE plain, never-awaited call that builds the row synchronously (the request
ContextVars are read at the exit) and schedules ONE fire-and-forget service-role insert into
public.compare_runs (migration 048).

A leaf: the standard library plus result_gate, llm_pricing, request_context, async_utils and
db_offload through their module attributes; database_service is imported lazily inside the
insert coroutine. The row never carries a user id, an access token, the typed query, a URL,
the raw device fingerprint, a Sentry id or any personalisation: the device is the S81-05
device_key HMAC, the pair is HMAC-SHA256(the S81-05 pepper, "pair:" + the pair identity text)
for every input type (R-S22-24), and the evidence snapshot is de-identified at write time
and capped at EVIDENCE_MAX_BYTES. Log lines carry constants and exception type names only.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import math
import os
import re
import uuid
from typing import Any, Dict, List, Optional
from urllib.parse import urlsplit

from app.services import llm_pricing as _llm_pricing
from app.services import result_gate as _rg
from app.utils import async_utils as _async_utils
from app.utils import db_offload as _db_offload
from app.utils import request_context as _request_context

logger = logging.getLogger(__name__)

FLAG = "ENABLE_COMPARE_RUN_LEDGER"
TABLE = "compare_runs"
#: "up to 12 months" (S81-12 records it as COMPARE_RUN_RETENTION); the nightly judge prunes with it.
COMPARE_RUN_RETENTION_DAYS = 365
EVIDENCE_MAX_BYTES = 65536
LLM_CALLS_MAX = 32
INPUT_TYPES = ("text", "text_stream", "camera", "url")
QUERY_HMAC_DOMAIN = "pair:"
LABEL_PREFIX = "compare_runs.insert."
LOG_SKIPPED = "[COMPARE_RUNS] insert skipped reason=%s"

#: The closed row (21 keys); the DB defaults fill id, created_at, recompare and judged_at.
RUN_COLUMNS = (
    "comparison_id", "consent_version", "compare_request_id", "device_key", "input_type",
    "category", "product_categories", "refusal_reason", "query_hmac", "kb_product_ids",
    "sources_used", "cache_hits", "llm_calls", "stage_timings", "result_status",
    "identity_confidence", "data_coverage", "winner_supported", "field_status",
    "partial_stage", "evidence",
)

#: One llm call: the mapped names from llm_pricing.OTEL_GENAI_ATTRIBUTES (the one source,
#: R-S22-27) plus the unmapped ledger keys under their ledger names.
_OTEL = _llm_pricing.OTEL_GENAI_ATTRIBUTES
LLM_CALL_FIELDS = (
    _OTEL["provider"], _OTEL["model"], _OTEL["prompt_tokens"], _OTEL["completion_tokens"],
    _OTEL["stop_reason"], "role", "web_search_requests", "cost_usd", "latency_ms", "batch",
)

#: scoring_method values that mean personalisation moved the result (R-S22-53).
PERSONALIZED_SCORING = ("personalized", "behavioral", "cohort", "invitee_quiz")

_TRUTHY = ("true", "1", "yes", "on")
_CATEGORY_RX = re.compile(r"^[a-z_]{1,32}$")
_ENUM_RX = re.compile(r"^[a-z0-9_]{1,40}$")
_HOST_RX = re.compile(r"^[a-z0-9.-]{1,253}$")
_TIMING_RX = re.compile(r"^[a-z0-9_]{1,64}$")
_CURRENCY_RX = re.compile(r"^[A-Z]{3}$")
_MAX_TIMINGS = 32
_MAX_SPEC_ROWS = 40
_MAX_SC_ITEMS = 10
_FIELD_TEXT_MAX = 64


def compare_run_ledger_enabled() -> bool:
    return os.getenv(FLAG, "false").strip().lower() in _TRUTHY


# --- the hash ---------------------------------------------------------------------------

def _query_hmac(text: Any) -> Optional[str]:
    """HMAC-SHA256(pepper, "pair:" + norm(text)); None without a pepper or a text.

    The pepper is read per call and never logged; any encoding problem fails closed (None).
    """
    message = _rg.norm(text)
    if not message:
        return None
    pepper = os.getenv(_request_context.PEPPER_ENV)
    if pepper is None or not pepper.strip():
        return None
    try:
        pepper_bytes = pepper.strip().encode("utf-8")
        payload = (QUERY_HMAC_DOMAIN + message).encode("utf-8")
    except UnicodeError:
        return None
    return hmac.new(pepper_bytes, payload, hashlib.sha256).hexdigest()


def pair_identity_text(result: Any) -> str:
    """The two delivered products' identity texts in body order joined by " vs " (else "")."""
    if not isinstance(result, dict):
        return ""
    prods = [p for p in _rg._raw_products(result)[:2] if isinstance(p, dict)]
    if len(prods) < 2:
        return ""
    return " vs ".join(_rg.identity_text(p.get("brand"), p.get("name")) for p in prods)


# --- small total readers ----------------------------------------------------------------

def _dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _text(value: Any, cap: int) -> Optional[str]:
    return value[:cap] if isinstance(value, str) else None


def _finite(value: Any) -> Optional[float]:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _count(value: Any) -> Optional[int]:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _enum(value: Any, rx: "re.Pattern[str]" = _ENUM_RX) -> Optional[str]:
    return value if isinstance(value, str) and rx.match(value) else None


def _host(url: Any) -> Optional[str]:
    """The host only (lower-case, a leading www. stripped); never the path or the query."""
    if not isinstance(url, str) or not url:
        return None
    try:
        host = (urlsplit(url).hostname or "").lower()
    except ValueError:
        return None
    if host.startswith("www."):
        host = host[4:]
    return host if host and _HOST_RX.match(host) else None


def _products(body: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [p if isinstance(p, dict) else {} for p in _rg._raw_products(body)[:2]]


# --- the row fields ---------------------------------------------------------------------

def _comparison_id(body: Dict[str, Any]) -> Optional[str]:
    raw = body.get("comparison_id")
    if not isinstance(raw, str) or not raw:
        return None
    try:
        return str(uuid.UUID(raw))
    except (ValueError, AttributeError, TypeError):
        return None


def _consent_version() -> Optional[int]:
    value = _request_context.consent_version()
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 999:
        return None
    return value


def _device() -> Optional[str]:
    fp = _request_context.device_fingerprint()
    return _request_context.device_key(fp) if fp is not None else None


def _product_categories(body: Dict[str, Any]) -> Optional[List[Optional[str]]]:
    cats = _rg.stamped_product_categories(body)
    if cats is None:
        return None
    return [c if isinstance(c, str) and _CATEGORY_RX.match(c) else None for c in cats]


def _sources_used(body: Dict[str, Any], prods: List[Dict[str, Any]]) -> Dict[str, Any]:
    marks = _dict(body.get("metadata")).get("kb_hit")
    if not (isinstance(marks, list) and len(marks) == 2 and all(m in ("hit", "miss") for m in marks)):
        marks = None
    return {
        "v": 1,
        "price_method": [_enum(_dict(p.get("price")).get("source_method")) for p in prods],
        "price_host": [_host(_dict(p.get("price")).get("url")) for p in prods],
        "rating_method": [_enum(_dict(p.get("rating_source")).get("extract_method")) for p in prods],
        "kb_hit": list(marks) if marks is not None else None,
    }


def _cache_hits(body: Dict[str, Any], prods: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "v": 1,
        "response": _dict(body.get("metadata")).get("cached") is True,
        "price": [_dict(p.get("price")).get("_cached") is True for p in prods],
    }


def _stage_timings(body: Dict[str, Any], vision_ms: Any, compare_ms: Any) -> Optional[Dict[str, int]]:
    meta = _dict(body.get("metadata"))
    out: Dict[str, int] = {}
    raw = meta.get("stage_timings_ms")
    if isinstance(raw, dict):
        for key in sorted(k for k in raw if isinstance(k, str) and _TIMING_RX.match(k)):
            value = _finite(raw[key])
            if value is not None and value >= 0 and len(out) < _MAX_TIMINGS:
                out[key] = int(value)
    if compare_ms is None:
        compare_ms = meta.get("elapsed_ms")
    for name, raw_value in (("vision_ms", vision_ms), ("compare_ms", compare_ms)):
        value = _finite(raw_value)
        if value is not None and value >= 0:
            out[name] = int(value)
    return out or None


def _call(record: Dict[str, Any]) -> Dict[str, Any]:
    def short(value: Any) -> Optional[str]:
        return value if isinstance(value, str) and len(value) <= _FIELD_TEXT_MAX else None

    stop = short(record.get("stop_reason"))
    return {
        _OTEL["provider"]: short(record.get("provider")),
        _OTEL["model"]: short(record.get("model")),
        _OTEL["prompt_tokens"]: _count(record.get("prompt_tokens")),
        _OTEL["completion_tokens"]: _count(record.get("completion_tokens")),
        _OTEL["stop_reason"]: [stop] if stop is not None else None,
        "role": short(record.get("role")),
        "web_search_requests": _count(record.get("web_search_requests")),
        "cost_usd": _finite(record.get("cost_usd")),
        "latency_ms": _count(record.get("latency_ms")),
        "batch": record.get("batch") is True,
    }


def _llm_calls(extra_records: Any) -> Optional[Dict[str, Any]]:
    """The bound OpenAI ledger (+ the camera's own vision ledger, de-duplicated by entry)
    as records, plus the non-OpenAI llm records (the build_llm_metadata rule)."""
    openai_ledger = _llm_pricing.current_openai_ledger()
    llm_records = _llm_pricing.current_llm_records()
    extra = extra_records if isinstance(extra_records, list) else None
    if openai_ledger is None and llm_records is None and extra is None:
        return None
    seen = set()
    openai_entries: List[Dict[str, Any]] = []
    other: List[Dict[str, Any]] = []
    sources = [openai_ledger or []]
    if extra is not None and extra is not openai_ledger:
        sources.append(extra)
    for source in sources:
        for entry in source:
            if not isinstance(entry, dict) or id(entry) in seen:
                continue
            seen.add(id(entry))
            if "provider" in entry and entry.get("provider") != "openai":
                other.append(entry)
            elif "provider" not in entry:
                openai_entries.append(entry)
    records = [_llm_pricing.openai_entry_record(e) for e in openai_entries] + other
    records += [r for r in (llm_records or []) if isinstance(r, dict) and r.get("provider") != "openai"
                and id(r) not in seen]
    calls = [_call(r) for r in records]
    return {"v": 1, "calls": calls[:LLM_CALLS_MAX], "llm_calls_dropped": max(0, len(calls) - LLM_CALLS_MAX)}


def _field_status(meta: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    fs = meta.get("field_status")
    if isinstance(fs, list) and len(fs) <= 2 and all(isinstance(x, dict) for x in fs):
        return fs
    return None


def _partial_stage(meta: Dict[str, Any]) -> Optional[str]:
    if meta.get("partial") is not True:
        return None
    stage = meta.get("partial_stage")
    return stage if isinstance(stage, str) and stage in _rg.PARTIAL_STAGES else None


# --- the evidence snapshot (de-identified at write time) -------------------------------

def _personalized(body: Dict[str, Any]) -> bool:
    """A personalisation marker on the body: the verdict prose is then dropped (R-S22-53)."""
    if _dict(body.get("metadata")).get("cohort_injected") is True or body.get("personalized") is True:
        return True
    if _dict(body.get("personalization")).get("personalized") is True:
        return True
    method = _dict(body.get("scoring")).get("scoring_method")
    return isinstance(method, str) and method in PERSONALIZED_SCORING


def _spec_rows(specs: Any) -> Dict[str, str]:
    out: Dict[str, str] = {}
    if not isinstance(specs, dict):
        return out
    for key in sorted(k for k in specs if isinstance(k, str) and not k.startswith("_")):
        value = specs[key]
        if isinstance(value, list):
            value = ", ".join(str(x) for x in value)
        if value is None or isinstance(value, dict):
            continue
        out[key[:40]] = str(value)[:160]
        if len(out) >= _MAX_SPEC_ROWS:
            break
    return out


def _snap_product(body: Dict[str, Any], i: int, p: Dict[str, Any]) -> Dict[str, Any]:
    price = _dict(p.get("price"))
    specs = _dict(p.get("specs"))
    rating = p.get("rating")
    currency = price.get("currency")
    size = specs.get("volume") if specs.get("volume") is not None else specs.get("size")
    return {
        "brand": _text(p.get("brand"), 160),
        "name": _text(p.get("name"), 160),
        "variant": _text(p.get("variant"), 80),
        "category": _enum(p.get("category"), _CATEGORY_RX),
        "size": _text(size, 40),
        "concentration": _text(specs.get("concentration"), 40),
        "price": {
            "amount": _finite(price.get("amount")),
            "currency": currency if isinstance(currency, str) and _CURRENCY_RX.match(currency) else None,
            "source_method": _enum(price.get("source_method")),
            "as_of": _text(price.get("as_of"), 40),
            "host": _host(price.get("url")),
            "estimated": price.get("estimated") is True,
            "unavailable": price.get("unavailable") is True,
        },
        "rating": {
            "value": _finite(rating.get("value") if isinstance(rating, dict) else rating),
            "count": _count(p.get("review_count")),
            "source": _enum(_dict(p.get("rating_source")).get("extract_method")),
        },
        "specs": _spec_rows(specs),
        "image": bool(_rg._image_present(body, i)),
    }


def _specs_comparison(body: Dict[str, Any]) -> Optional[Dict[str, List[str]]]:
    raw = _dict(body.get("specs")).get("specs_comparison")
    if not isinstance(raw, dict):
        raw = _dict(body.get("comparison")).get("specs_comparison")
    if not isinstance(raw, dict):
        return None
    out: Dict[str, List[str]] = {}
    for key in sorted(k for k in raw if isinstance(k, str) and _ENUM_RX.match(k)):
        items = raw[key] if isinstance(raw[key], list) else [raw[key]]
        out[key] = [str(x)[:300] for x in items[:_MAX_SC_ITEMS]]
    return out


def _snapshot(body: Dict[str, Any], category: Optional[str], supported: bool) -> Dict[str, Any]:
    winner = _dict(_dict(body.get("overview")).get("winner"))
    index = winner.get("product_index")
    verdict = {
        "product_index": index if isinstance(index, int) and not isinstance(index, bool) else None,
        "name": _text(winner.get("name"), 160),
        "declaration": _text(winner.get("declaration"), 160),
        "reason": _text(winner.get("reason"), 600),
        "key_tradeoff": _text(winner.get("key_tradeoff"), 600),
        "margin": _finite(winner.get("margin")),
        "supported": supported,
    }
    snap: Dict[str, Any] = {"v": 1, "category": category}
    if _personalized(body):
        for key in ("declaration", "reason", "key_tradeoff"):
            verdict[key] = None
        snap["prose_dropped"] = "personalized"
    scoring = _dict(body.get("scoring"))
    scores = _dict(scoring.get("scores"))
    snap.update({
        "products": [_snap_product(body, i, p) for i, p in enumerate(_products(body))],
        "specs_comparison": _specs_comparison(body),
        "verdict": verdict,
        "scores": {
            "overall": [_finite(_dict(scores.get("product_%d" % i)).get("overall")) for i in (0, 1)],
            "scoring_method": _enum(scoring.get("scoring_method"), _CATEGORY_RX),
        },
        "section_status": _rg.section_status(body),
        "truncated": False,
    })
    return snap


def _serialized_size(obj: Any) -> int:
    return len(json.dumps(obj, ensure_ascii=True, sort_keys=True, separators=(",", ":")))


def _fit(snap: Dict[str, Any]) -> Dict[str, Any]:
    """The cut order: the specs (per product + the comparison), then the verdict prose,
    then the minimal form {"v": 1, "truncated": true}."""
    if _serialized_size(snap) <= EVIDENCE_MAX_BYTES:
        return snap
    for product in snap.get("products") or []:
        product["specs"] = None
    snap["specs_comparison"] = None
    snap["truncated"] = True
    if _serialized_size(snap) <= EVIDENCE_MAX_BYTES:
        return snap
    for key in ("reason", "key_tradeoff", "declaration"):
        snap["verdict"][key] = None
    if _serialized_size(snap) <= EVIDENCE_MAX_BYTES:
        return snap
    return {"v": 1, "truncated": True}


# --- the builder and the recorder ---------------------------------------------------------

def build_run_row(result: Any, input_type: Any, *, vision_ms: Any = None, compare_ms: Any = None,
                  extra_records: Any = None) -> Optional[Dict[str, Any]]:
    """PURE: the closed RUN_COLUMNS row for a success body, else None (no I/O)."""
    if input_type not in INPUT_TYPES or not isinstance(result, dict) or result.get("success") is not True:
        return None
    body = result
    prods = _products(body)
    assessment = _rg.assess_result(body, product_categories=_rg.stamped_product_categories(body))
    supported = assessment["status"] == _rg.STATUS_SUPPORTED
    used = _rg._category_used(body)
    category = used if isinstance(used, str) and _CATEGORY_RX.match(used) else None
    meta = _dict(body.get("metadata"))
    row = {
        "comparison_id": _comparison_id(body),
        "consent_version": _consent_version(),
        "compare_request_id": _request_context.compare_request_id(),
        "device_key": _device(),
        "input_type": input_type,
        "category": category,
        "product_categories": _product_categories(body),
        "refusal_reason": None,
        "query_hmac": _query_hmac(pair_identity_text(body)),
        "kb_product_ids": None,
        "sources_used": _sources_used(body, prods),
        "cache_hits": _cache_hits(body, prods),
        "llm_calls": _llm_calls(extra_records),
        "stage_timings": _stage_timings(body, vision_ms, compare_ms),
        "result_status": assessment["status"],
        "identity_confidence": assessment["identity_confidence"],
        "data_coverage": int(assessment["data_coverage"]),
        "winner_supported": supported,
        "field_status": _field_status(meta),
        "partial_stage": _partial_stage(meta),
        "evidence": _fit(_snapshot(body, category, supported)),
    }
    return {key: row[key] for key in RUN_COLUMNS}


async def _insert(row: Dict[str, Any]) -> None:
    try:
        from app.services import database_service as _db

        client = _db.get_admin_supabase_client()
        await _db_offload.run_db(lambda: client.table(TABLE).insert(row).execute())
    except Exception as exc:  # noqa: BLE001 - one WARNING here, never a second done-callback line
        logger.warning(LOG_SKIPPED, type(exc).__name__)


def record_compare_run(result: Any, input_type: Any, *, vision_ms: Any = None,
                       compare_ms: Any = None, extra_records: Any = None) -> None:
    """Schedule ONE fire-and-forget insert of the run row for a delivered body.

    The flag is the first statement; never raises, never awaits, returns None.
    """
    if not compare_run_ledger_enabled():
        return
    try:
        if not isinstance(result, dict) or result.get("success") is not True:
            return
        row = build_run_row(result, input_type, vision_ms=vision_ms, compare_ms=compare_ms,
                            extra_records=extra_records)
        if row is None:
            return
        _async_utils.fire_and_forget(_insert(row), label=LABEL_PREFIX + str(input_type))
    except Exception as exc:  # noqa: BLE001 - the response is never touched
        logger.warning(LOG_SKIPPED, type(exc).__name__)
