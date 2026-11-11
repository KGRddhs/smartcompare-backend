"""S81-G5 D22 NIGHTLY-LEARNING: the nightly, DB-only learning job.

Flag ``ENABLE_LEARNING_JOB`` (default OFF) is read per call, as the FIRST
statement of ``main``, through ``kb_seed_common.run_mode``: unset, blank,
garbage, false, 0, no, off or dry = OFF (one INFO line, exit 0, before argparse,
before any client, before the KB leaf, no file); the house truthy set (true,
1, yes, on) = DRY RUN (every read and the report, no write); the exact word
``apply`` = WRITE (one upsert of the closed ``learning.*`` metric list into
the KB coverage table per (day, metric), every row from the leaf's
``build_coverage_row``). ``--dry-run`` downgrades apply to dry. Knobs, read per
call through ``kb_seed_common.int_knob``: LEARNING_WINDOW_DAYS (7, 1..30),
LEARNING_MIN_CASES (3, 1..100), LEARNING_MIN_DEVICES (2, 1..10),
LEARNING_MAX_ROWS (5000 per table, 100..50000) and
LEARNING_EXEMPLARS_PER_CATEGORY (5, 3..5).

DB only: the service-role client reads the window ending at the previous UTC
midnight of comparison_feedback, verdict_critiques, user_events, search_logs,
the KB gap queue and the KB feedback table (paged, ordered on id, capped), then
the joined comparisons by id (PostgREST JSON paths only, never the query text
nor the whole stored response) and the KB specs of the reported KB products for
grounding. No LLM, no search provider, no Redis, no other network. Only the
standard library and ``scripts.kb_seed_common`` are imported at module top; the
leaf comes through ``common.kb_leaf()``.

De-identification: every exemplar candidate, eval candidate and grounding entry
passes a structural screen (a uuid shape, a 64-hex run, an at sign, the Bahrain
dialling prefix, an 8-digit run; unanchored, so a shape inside a longer token
counts) BEFORE the per-category cut; a failing one is dropped and counted.
Only product names, field / category / source names, verdict text and counts
reach the report; the log carries counts and names only. Actors (user ids,
device keys) never leave the process.

Stated limits: (L1) the judge is absent, so every KB correction proposal carries
judge_state pending and NOTHING is applied; (L2) user_id is a PROXY for a device
outside the KB feedback table; (L3) identity_wrong has only the KB feedback
identity input, which nothing writes yet, and the client sends no per-axis
correctness field until CL3 / SF1; (L4) the report file is ephemeral on Railway:
the log is the durable copy and carries names and counts, never the exemplar
verdict text. Nothing is written to the repository data folder.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import logging
import math
import re
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

import scripts.kb_seed_common as common

logger = logging.getLogger("cron_learning")

PREFIX = "[LEARNING]"
FLAG = "ENABLE_LEARNING_JOB"
REPORT_SCHEMA = "learning-report/1"
KB_COVERAGE_TABLE = "kb_coverage_daily"
KB_FEEDBACK_TABLE = "kb_feedback"
COMPARISON_FEEDBACK_TABLE = "comparison_feedback"
COMPARISONS_TABLE = "comparisons"
USER_EVENTS_TABLE = "user_events"
SEARCH_LOGS_TABLE = "search_logs"
VERDICT_CRITIQUES_TABLE = "verdict_critiques"
READ_TABLES = (COMPARISON_FEEDBACK_TABLE, COMPARISONS_TABLE, USER_EVENTS_TABLE, SEARCH_LOGS_TABLE,
               VERDICT_CRITIQUES_TABLE, common.KB_GAPS_TABLE, KB_FEEDBACK_TABLE, common.KB_SPECS_TABLE)
FEEDBACK_COLUMNS = "id,user_id,comparison_id,useful,winner_correct,price_correct,specs_correct,created_at"
COMPARISON_COLUMNS = ("id,user_id,product_names,category:full_response->>category_used,"
                      "wi:full_response->>winner_index,"
                      "m0:full_response->overview->products->0->price->>source_method,"
                      "m1:full_response->overview->products->1->price->>source_method,"
                      "a0:full_response->overview->products->0->price->>amount,"
                      "a1:full_response->overview->products->1->price->>amount,"
                      "c0:full_response->overview->products->0->price->>currency,"
                      "c1:full_response->overview->products->1->price->>currency,"
                      "cwi:full_response->comparison->>winner_index,"
                      "wr:full_response->comparison->>winner_reason,"
                      "kt:full_response->comparison->>key_tradeoff,"
                      "vc:full_response->comparison->value_context")
EVENT_COLUMNS = "id,user_id,event_type,comparison_id,created_at"
SEARCH_COLUMNS = "id,user_id,success,is_synthetic,created_at"
CRITIQUE_COLUMNS = "id,comparison_id,bias_score,missing_citation_score,created_at"
GAP_COLUMNS = "id,field,state,demand_count,last_seen"
KB_FEEDBACK_COLUMNS = "id,compare_request_id,product_id,field,verdict,device_key,created_at"
SPEC_COLUMNS = "product_id,field,source_url,cited"
BUCKETS = ("identity_wrong", "price_wrong", "spec_missing", "spec_wrong", "verdict_unsupported", "verdict_wrong")
CATEGORIES = ("electronics", "grocery", "supplements", "makeup", "skincare", "haircare", "fragrances",
              "fashion", "other")
D05_FIELDS = ("identity", "image", "price", "size", "concentration", "specs", "rating", "review_count")
SOURCE_METHODS = ("local_bhd", "converted_usd", "page_scrape", "page_scrape_rendered", "firecrawl",
                  "scrapedo_rendered", "estimated")
SOURCES_EXTRA = ("mixed", "unknown", "specs", "verdict", "critic", "kb", "kb_gap")
ACTIONS = ("recheck_source", "drop_source_for_field", "needs_operator", "no_action")
ABANDON_EVENTS = ("result_abandon", "compare_cancelled", "scan_failed")
CONFIRM_EVENTS = ("save", "share_completed", "screenshot")
GAP_OPEN_STATES = ("open", "queued", "needs_operator")
HINT_PREFIX = "pdp_"
CRITIQUE_THRESHOLD = 7  # the retired self-critique pass's threshold (S81-22b); PIN P5 holds the literal
MISSING_TABLE_CODES = ("42P01", "PGRST205")
IN_CHUNK = 100

_ORDER_COLUMN = "id"
_UNKNOWN = "unknown"
_OTHER_FIELD = "other"
_JUDGE_PENDING = "pending"
_GROUNDING_MAX = 3
_FIELD_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_ISO3_RE = re.compile(r"^[A-Z]{3}$")
#: the structural de-identification shapes (unanchored; built so the source carries no literal shape)
_UNCLEAN_RES = (
    re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.IGNORECASE),
    re.compile(r"[0-9a-fA-F]{64}"),
    re.compile(re.escape(chr(64))),
    re.compile(re.escape("+" + "97" + "3")),
    re.compile(r"[0-9]{8}"),
)
_BUCKET_INPUTS = {
    "identity_wrong": (KB_FEEDBACK_TABLE,),
    "price_wrong": (COMPARISON_FEEDBACK_TABLE, KB_FEEDBACK_TABLE),
    "spec_missing": (common.KB_GAPS_TABLE,),
    "spec_wrong": (COMPARISON_FEEDBACK_TABLE, KB_FEEDBACK_TABLE),
    "verdict_unsupported": (VERDICT_CRITIQUES_TABLE,),
    "verdict_wrong": (COMPARISON_FEEDBACK_TABLE,),
}
_PER_AXIS_NOTE = "no client sends the per-axis correctness field until CL3 / SF1"
_BUCKET_NOTES = {
    "identity_wrong": "no writer at base; SF1 / CL3 add the identity signals",
    "price_wrong": _PER_AXIS_NOTE,
    "spec_missing": "open kb gaps without a pdp_ hint; kb gaps carry no actor",
    "spec_wrong": _PER_AXIS_NOTE,
    "verdict_unsupported": "only while the self-critique pass has run",
    "verdict_wrong": _PER_AXIS_NOTE,
}


# ---------------------------------------------------------------------------
# flag and knobs (read per call, never memoised)
# ---------------------------------------------------------------------------

def learning_mode() -> str:
    return common.run_mode(FLAG)


def window_days() -> int:
    return common.int_knob("LEARNING_WINDOW_DAYS", 7, 1, 30)


def min_cases() -> int:
    return common.int_knob("LEARNING_MIN_CASES", 3, 1, 100)


def min_devices() -> int:
    return common.int_knob("LEARNING_MIN_DEVICES", 2, 1, 10)


def max_rows() -> int:
    return common.int_knob("LEARNING_MAX_ROWS", 5000, 100, 50000)


def exemplars_per_category() -> int:
    return common.int_knob("LEARNING_EXEMPLARS_PER_CATEGORY", 5, 3, 5)


# ---------------------------------------------------------------------------
# small pure helpers
# ---------------------------------------------------------------------------

def _clean(text: Any) -> bool:
    """False when a string carries any de-identification shape (a non-string is clean)."""
    if not isinstance(text, str):
        return True
    return not any(rx.search(text) for rx in _UNCLEAN_RES)


#: D22d (L15): C0 / C1 control characters -> \xNN, U+2028 / U+2029 -> \uNNNN;
#: a backslash is NOT doubled. Built once; applied by :func:`_render`.
_RENDER_ESCAPES: Dict[int, str] = {
    **{code: "\\x%02x" % code for code in range(0x00, 0x20)},
    **{code: "\\x%02x" % code for code in range(0x7F, 0xA0)},
    0x2028: "\\u2028",
    0x2029: "\\u2029",
}


def _render(text: Any) -> Any:
    """D22d: a product name made safe for a log line or a markdown cell (the
    control characters escaped); a name without one is returned unchanged."""
    if not isinstance(text, str):
        return text
    return text.translate(_RENDER_ESCAPES)


def _all_clean(values: Iterable[Any]) -> bool:
    return all(_clean(v) for v in values)


def _field_name(raw: Any) -> str:
    if isinstance(raw, str) and _FIELD_RE.match(raw) and _clean(raw):
        return raw
    return _OTHER_FIELD


def _index01(raw: Any) -> Optional[int]:
    if isinstance(raw, bool) or raw is None:
        return None
    try:
        value = int(str(raw).strip())
    except (TypeError, ValueError):
        return None
    return value if value in (0, 1) else None


def _int_score(raw: Any) -> Optional[int]:
    if isinstance(raw, bool) or not isinstance(raw, int):
        return None
    return raw


def _amount(raw: Any) -> Optional[float]:
    if raw is None or isinstance(raw, bool):
        return None
    try:
        value = float(str(raw).strip())
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def _category(cmp_row: Optional[Dict[str, Any]]) -> str:
    if not cmp_row:
        return _UNKNOWN
    raw = cmp_row.get("category")
    if isinstance(raw, str):
        value = raw.strip().lower()
        if value in CATEGORIES:
            return value
    return _UNKNOWN


def _price_source(cmp_row: Optional[Dict[str, Any]]) -> str:
    if not cmp_row:
        return _UNKNOWN
    m0, m1 = cmp_row.get("m0"), cmp_row.get("m1")
    if m0 in SOURCE_METHODS and m1 in SOURCE_METHODS:
        return m0 if m0 == m1 else "mixed"
    return _UNKNOWN


def _actor(tag: str, raw: Any) -> Optional[Tuple[str, str]]:
    if isinstance(raw, str) and raw:
        return (tag, raw)
    return None


def _pair_names(cmp_row: Dict[str, Any]) -> Optional[Tuple[str, str]]:
    names = cmp_row.get("product_names")
    if not isinstance(names, (list, tuple)) or len(names) < 2:
        return None
    n0, n1 = names[0], names[1]
    if not (isinstance(n0, str) and isinstance(n1, str) and n0 and n1):
        return None
    return (n0, n1)


def _value_context(raw: Any) -> Optional[Dict[str, str]]:
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except ValueError:
            return None
    if not isinstance(raw, dict):
        return None
    v0, v1 = raw.get("product_0"), raw.get("product_1")
    if not (isinstance(v0, str) and isinstance(v1, str)):
        return None
    return {"product_0": v0, "product_1": v1}


def _set_version(day: date, items: List[Dict[str, Any]]) -> str:
    blob = json.dumps(items, sort_keys=True, ensure_ascii=True).encode("ascii")
    digest = base64.b32encode(hashlib.sha256(blob).digest()).decode("ascii").lower()[:16]
    return "%s.%s" % (day.isoformat(), digest)


# ---------------------------------------------------------------------------
# reads (paged, ordered on id, capped; one table's failure is isolated)
# ---------------------------------------------------------------------------

def _page(client: Any, table: str, columns: str, filters: List[Tuple[str, Tuple[Any, ...]]],
          start: int, end: int) -> List[Dict[str, Any]]:
    query = client.table(table).select(columns)
    for name, args in filters:
        query = getattr(query, name)(*args)
    resp = query.order(_ORDER_COLUMN).range(start, end).execute()
    rows = getattr(resp, "data", None)
    if not isinstance(rows, list):
        raise TypeError("page is not a list")
    return rows


def _read_window(client: Any, table: str, columns: str, column: str, start_iso: str, end_iso: str,
                 cap: int, extra: Tuple[Tuple[str, Tuple[Any, ...]], ...] = ()) -> Tuple[List[Dict[str, Any]], str]:
    filters = list(extra) + [("gte", (column, start_iso)), ("lt", (column, end_iso))]
    rows: List[Dict[str, Any]] = []
    offset = 0
    while True:
        last = min(offset + common.PAGE_SIZE, cap) - 1
        page = _page(client, table, columns, filters, offset, last)
        rows.extend(page)
        if len(rows) >= cap:
            return rows[:cap], "capped"
        if len(page) < last - offset + 1:
            return rows, "ok"
        offset = last + 1


def _read_by(client: Any, table: str, columns: str, column: str, values: Iterable[str],
             cap: int) -> Tuple[List[Dict[str, Any]], str]:
    wanted = sorted(set(values))
    rows: List[Dict[str, Any]] = []
    for i in range(0, len(wanted), IN_CHUNK):
        chunk = wanted[i:i + IN_CHUNK]
        # D22d (L14): id-ordered pages of PAGE_SIZE per chunk until a short page,
        # never past the cap (was ONE range(0, 799) per chunk, silently cut).
        offset = 0
        while True:
            size = min(common.PAGE_SIZE, cap - len(rows))
            page = _page(client, table, columns, [("in_", (column, chunk))], offset, offset + size - 1)
            rows.extend(page)
            if len(rows) >= cap:
                return rows[:cap], "capped"
            if len(page) < size:
                break
            offset += size
    return rows, "ok"


class _Tables:
    """The per-table read state: rows, status (ok / absent / error / capped) and the error type."""

    def __init__(self) -> None:
        self.state: Dict[str, Dict[str, Any]] = {t: {"rows": 0, "status": "ok", "error": None}
                                                  for t in READ_TABLES}

    def read(self, table: str, fn: Any) -> List[Dict[str, Any]]:
        try:
            rows, status = fn()
        except Exception as exc:  # noqa: BLE001 - one table's failure never ends the run
            code = getattr(exc, "code", None)
            status = "absent" if str(code) in MISSING_TABLE_CODES else "error"
            logger.warning("%s table=%s read failed (%s)", PREFIX, table, type(exc).__name__)
            self.state[table] = {"rows": 0, "status": status, "error": type(exc).__name__}
            return []
        self.state[table] = {"rows": len(rows), "status": status, "error": None}
        return [r for r in rows if isinstance(r, dict)]

    def failed(self, table: str) -> bool:
        return self.state[table]["status"] in ("absent", "error")

    def capped(self, table: str) -> bool:
        return self.state[table]["status"] == "capped"


# ---------------------------------------------------------------------------
# cases, clusters, proposals
# ---------------------------------------------------------------------------

class _Cases:
    """One case per (bucket, case id); every report mapping to a case adds its actor (GC-2)."""

    def __init__(self) -> None:
        self.by_bucket: Dict[str, Dict[Tuple[Any, ...], Dict[str, Any]]] = {b: {} for b in BUCKETS}

    def add(self, bucket: str, case_id: Tuple[Any, ...], category: str, source: str, field: str,
            actor: Optional[Tuple[str, str]], demand: int = 0, product: Optional[str] = None) -> None:
        entry = self.by_bucket[bucket].setdefault(
            case_id, {"key": (category, source, field), "actors": set(), "demand": 0, "product": product})
        if actor is not None:
            entry["actors"].add(actor)
        entry["demand"] = max(entry["demand"], demand)

    def bucket_actors(self, bucket: str) -> Set[Tuple[str, str]]:
        out: Set[Tuple[str, str]] = set()
        for entry in self.by_bucket[bucket].values():
            out |= entry["actors"]
        return out

    def all_actors(self) -> Set[Tuple[str, str]]:
        out: Set[Tuple[str, str]] = set()
        for bucket in BUCKETS:
            out |= self.bucket_actors(bucket)
        return out


def _clusters(cases: _Cases, need_cases: int, need_actors: int) -> List[Dict[str, Any]]:
    grouped: Dict[Tuple[str, str, str, str], Dict[str, Any]] = {}
    for bucket in BUCKETS:
        for entry in cases.by_bucket[bucket].values():
            category, source, field = entry["key"]
            key = (bucket, category, source, field)
            agg = grouped.setdefault(key, {"cases": 0, "actors": set(), "demand": 0, "products": set()})
            agg["cases"] += 1
            agg["actors"] |= entry["actors"]
            agg["demand"] += entry["demand"]
            if entry["product"]:
                agg["products"].add(entry["product"])
    out = []
    for key in sorted(grouped):
        agg = grouped[key]
        actors = len(agg["actors"])
        out.append({
            "bucket": key[0], "category": key[1], "source": key[2], "field": key[3],
            "cases": agg["cases"], "actors": actors, "demand": agg["demand"],
            "systematic": agg["cases"] >= need_cases and actors >= need_actors,
            "_products": sorted(agg["products"]),
        })
    return out


def _action(bucket: str, source: str, grounding: List[Dict[str, str]]) -> str:
    if bucket == "price_wrong":
        if source == "estimated":
            return "drop_source_for_field"
        if source in SOURCE_METHODS:
            return "recheck_source"
        return "needs_operator"
    if bucket == "spec_wrong":
        return "recheck_source" if grounding else "needs_operator"
    if bucket in ("identity_wrong", "spec_missing"):
        return "needs_operator"
    return "no_action"


def _grounding(cluster: Dict[str, Any], specs: List[Dict[str, Any]], dropped: List[int]) -> List[Dict[str, str]]:
    if cluster["bucket"] != "spec_wrong" or cluster["source"] != "kb":
        return []
    products = set(cluster["_products"])
    found = set()
    for row in specs:
        if row.get("cited") is not True or row.get("field") != cluster["field"]:
            continue
        product, url = row.get("product_id"), row.get("source_url")
        if product not in products or not isinstance(url, str) or not url:
            continue
        if not _all_clean((product, url)):
            dropped[0] += 1
            continue
        found.add((product, cluster["field"], url))
    return [{"product_id": p, "field": f, "source_url": u} for p, f, u in sorted(found)[:_GROUNDING_MAX]]


# ---------------------------------------------------------------------------
# exemplar and eval candidates (screened BEFORE the per-category cut, GC-3)
# ---------------------------------------------------------------------------

def _confirmed(feedback: List[Dict[str, Any]], comparisons: Dict[str, Dict[str, Any]]) -> List[Tuple[Dict[str, Any], Dict[str, Any]]]:
    """(feedback row, comparison row) for useful + winner_correct correct, once per comparison."""
    out, seen = [], set()
    for row in feedback:
        if row.get("useful") is not True or row.get("winner_correct") != "correct":
            continue
        cid = row.get("comparison_id")
        cmp_row = comparisons.get(cid) if isinstance(cid, str) else None
        if cmp_row is None or cid in seen:
            continue
        seen.add(cid)
        out.append((row, cmp_row))
    return out


def _exemplars(confirmed: List[Tuple[Dict[str, Any], Dict[str, Any]]], day: date, per_category: int,
               dropped: List[int]) -> Dict[str, Dict[str, Any]]:
    by_category: Dict[str, Dict[Tuple[str, str], Dict[str, Any]]] = {}
    for _row, cmp_row in confirmed:
        names = _pair_names(cmp_row)
        winner = _index01(cmp_row.get("cwi"))
        reason = cmp_row.get("wr")
        context = _value_context(cmp_row.get("vc"))
        if names is None or winner is None or context is None or not (isinstance(reason, str) and reason.strip()):
            continue
        tradeoff = cmp_row.get("kt") if isinstance(cmp_row.get("kt"), str) else ""
        candidate = {"product_names": [names[0], names[1]], "winner_index": winner, "winner_reason": reason,
                     "key_tradeoff": tradeoff, "value_context": context}
        if not _all_clean((names[0], names[1], reason, tradeoff, context["product_0"], context["product_1"])):
            dropped[0] += 1
            continue
        by_category.setdefault(_category(cmp_row), {}).setdefault(names, candidate)
    out: Dict[str, Dict[str, Any]] = {}
    for category in sorted(by_category):
        items = [by_category[category][k] for k in sorted(by_category[category])][:per_category]
        out[category] = {"version": _set_version(day, items), "count": len(items), "exemplars": items}
    return out


def _confirmed_price(cmp_row: Dict[str, Any], amount_key: str, currency_key: str) -> Optional[Dict[str, Any]]:
    amount = _amount(cmp_row.get(amount_key))
    currency = cmp_row.get(currency_key)
    if amount is None or not (isinstance(currency, str) and _ISO3_RE.match(currency)):
        return None
    return {"amount": amount, "currency": currency}


def _eval_candidates(confirmed: List[Tuple[Dict[str, Any], Dict[str, Any]]], dropped: List[int]) -> List[Dict[str, Any]]:
    found: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    for row, cmp_row in confirmed:
        names = _pair_names(cmp_row)
        winner = _index01(cmp_row.get("wi"))
        if names is None or winner is None:
            continue
        prices: Dict[str, Optional[Dict[str, Any]]] = {"product_0": None, "product_1": None}
        if row.get("price_correct") == "correct":
            prices = {"product_0": _confirmed_price(cmp_row, "a0", "c0"),
                      "product_1": _confirmed_price(cmp_row, "a1", "c1")}
        strings = [names[0], names[1]] + [p["currency"] for p in prices.values() if p]
        if not _all_clean(strings):
            dropped[0] += 1
            continue
        category = _category(cmp_row)
        found.setdefault((category, names[0], names[1]), {
            "category": category, "product_names": [names[0], names[1]],
            "confirmed_winner_index": winner, "confirmed_prices": prices})
    return [found[k] for k in sorted(found)]


# ---------------------------------------------------------------------------
# the run
# ---------------------------------------------------------------------------

def _gather(client: Any, kb_category: str, start_iso: str, end_iso: str, cap: int) -> Dict[str, Any]:
    tables = _Tables()

    def windowed(table: str, columns: str, column: str, extra: Tuple[Tuple[str, Tuple[Any, ...]], ...] = ()):
        return tables.read(table, lambda: _read_window(client, table, columns, column, start_iso, end_iso,
                                                       cap, extra))

    feedback = windowed(COMPARISON_FEEDBACK_TABLE, FEEDBACK_COLUMNS, "created_at")
    critiques = windowed(VERDICT_CRITIQUES_TABLE, CRITIQUE_COLUMNS, "created_at")
    events = windowed(USER_EVENTS_TABLE, EVENT_COLUMNS, "created_at",
                      (("in_", ("event_type", list(ABANDON_EVENTS + CONFIRM_EVENTS))),))
    searches = windowed(SEARCH_LOGS_TABLE, SEARCH_COLUMNS, "created_at")
    gaps = windowed(common.KB_GAPS_TABLE, GAP_COLUMNS, "last_seen")
    kb_feedback = windowed(KB_FEEDBACK_TABLE, KB_FEEDBACK_COLUMNS, "created_at")

    cmp_ids = [r.get("comparison_id") for r in feedback + critiques]
    cmp_ids = [c for c in cmp_ids if isinstance(c, str) and c]
    comparisons: Dict[str, Dict[str, Any]] = {}
    if cmp_ids:
        rows = tables.read(COMPARISONS_TABLE,
                           lambda: _read_by(client, COMPARISONS_TABLE, COMPARISON_COLUMNS, "id", cmp_ids, cap))
        comparisons = {r["id"]: r for r in rows if isinstance(r.get("id"), str)}

    cases = _Cases()
    for row in feedback:
        cid = row.get("comparison_id")
        cmp_row = comparisons.get(cid) if isinstance(cid, str) else None
        case_id = ("cf", cid) if isinstance(cid, str) and cid else ("cf-row", str(row.get("id")))
        category = _category(cmp_row)
        actor = _actor("u", row.get("user_id"))
        if row.get("price_correct") == "wrong":
            cases.add("price_wrong", case_id, category, _price_source(cmp_row), "price", actor)
        if row.get("specs_correct") == "wrong":
            cases.add("spec_wrong", case_id, category, "specs", "specs", actor)
        if row.get("winner_correct") == "wrong":
            cases.add("verdict_wrong", case_id, category, "verdict", "verdict", actor)
    for row in critiques:
        scores = [_int_score(row.get("missing_citation_score")), _int_score(row.get("bias_score"))]
        if not any(s is not None and s < CRITIQUE_THRESHOLD for s in scores):
            continue
        cid = row.get("comparison_id")
        cmp_row = comparisons.get(cid) if isinstance(cid, str) else None
        case_id = ("vc", cid) if isinstance(cid, str) and cid else ("vc-row", str(row.get("id")))
        actor = _actor("u", cmp_row.get("user_id")) if cmp_row else None
        cases.add("verdict_unsupported", case_id, _category(cmp_row), "critic", "verdict", actor)
    spec_products: Set[str] = set()
    dropped_fields = 0
    for row in kb_feedback:
        if row.get("verdict") != "wrong":
            continue
        raw_field = row.get("field")
        product = row.get("product_id") if isinstance(row.get("product_id"), str) else None
        case_id = ("kf", str(row.get("compare_request_id")), str(product), str(raw_field))
        actor = _actor("d", row.get("device_key"))
        if raw_field == "price":
            cases.add("price_wrong", case_id, kb_category, "kb", "price", actor)
        elif raw_field == "identity":
            cases.add("identity_wrong", case_id, kb_category, "kb", "identity", actor)
        else:
            if isinstance(raw_field, str) and not _clean(raw_field):
                dropped_fields += 1  # D22d: an unclean field-name row counts once (it maps to other)
            cases.add("spec_wrong", case_id, kb_category, "kb", _field_name(raw_field), actor, product=product)
            if product:
                spec_products.add(product)
    for row in gaps:
        field = row.get("field")
        if row.get("state") not in GAP_OPEN_STATES or not isinstance(field, str) or field.startswith(HINT_PREFIX):
            continue
        demand = row.get("demand_count")
        demand = demand if isinstance(demand, int) and not isinstance(demand, bool) and demand > 0 else 0
        cases.add("spec_missing", ("kg", str(row.get("id"))), kb_category, "kb_gap", _field_name(field), None,
                  demand=demand)

    specs: List[Dict[str, Any]] = []
    if spec_products:
        specs = tables.read(common.KB_SPECS_TABLE,
                            lambda: _read_by(client, common.KB_SPECS_TABLE, SPEC_COLUMNS, "product_id",
                                             spec_products, cap))

    abandon_users: Set[str] = set()
    confirm_users: Set[str] = set()
    abandon = confirm = 0
    for row in events:
        kind, user = row.get("event_type"), row.get("user_id")
        if kind in ABANDON_EVENTS:
            abandon += 1
            if isinstance(user, str) and user:
                abandon_users.add(user)
        elif kind in CONFIRM_EVENTS:
            confirm += 1
            if isinstance(user, str) and user:
                confirm_users.add(user)
    searches_total = searches_failed = 0
    for row in searches:
        if row.get("is_synthetic") is True:
            continue
        searches_total += 1
        if row.get("success") is False:
            searches_failed += 1

    return {"tables": tables, "cases": cases, "feedback": feedback, "comparisons": comparisons, "specs": specs,
            "context": {"events_abandon": abandon, "events_confirm": confirm,
                        "searches_failed": searches_failed, "searches_total": searches_total},
            "abandon_users": len(abandon_users), "confirm_users": len(confirm_users),
            "dropped_fields": dropped_fields}


def _metrics(cases: _Cases, clusters: List[Dict[str, Any]], proposals: List[Dict[str, Any]],
             exemplars: Dict[str, Dict[str, Any]], evals: List[Dict[str, Any]], gathered: Dict[str, Any],
             dropped: int) -> List[List[Any]]:
    out: List[List[Any]] = []
    for bucket in BUCKETS:
        out.append(["learning.cases." + bucket, len(cases.by_bucket[bucket]), len(cases.bucket_actors(bucket))])
    systematic = sum(1 for c in clusters if c["systematic"])
    candidates = sum(block["count"] for block in exemplars.values())
    actors = len(cases.all_actors())
    ctx = gathered["context"]
    out += [
        ["learning.clusters.total", len(clusters), len(clusters)],
        ["learning.clusters.systematic", systematic, systematic],
        ["learning.proposals", len(proposals), len(proposals)],
        ["learning.exemplar_candidates", candidates, len(exemplars)],
        ["learning.eval_candidates", len(evals), len(evals)],
        ["learning.actors", actors, actors],
        ["learning.events.abandon", ctx["events_abandon"], gathered["abandon_users"]],
        ["learning.events.confirm", ctx["events_confirm"], gathered["confirm_users"]],
        ["learning.searches.failed", ctx["searches_failed"], ctx["searches_total"]],
        ["learning.dropped.deidentify", dropped, dropped],
    ]
    tables: _Tables = gathered["tables"]
    for table in READ_TABLES:
        if tables.failed(table):
            out.append(["learning.skipped." + table, 1, 0])
    for table in READ_TABLES:
        if tables.capped(table):
            rows = tables.state[table]["rows"]
            out.append(["learning.capped." + table, rows, rows])
    return out


def _write_md(path: Optional[str], report: Dict[str, Any]) -> None:
    if not path:
        return
    lines = ["# Learning report " + report["day"], "", "Window: %s to %s (%d days); judge_state %s." % (
        report["window_start"], report["window_end"], report["window_days"], report["judge_state"]), "",
        "| metric | value | n |", "|---|---|---|"]
    lines += ["| %s | %s | %d |" % (name, value, n) for name, value, n in report["metrics"]]
    lines += ["", "| bucket | category | source | field | cases | actors | systematic |", "|---|---|---|---|---|---|---|"]
    lines += ["| %s | %s | %s | %s | %d | %d | %d |" % (c["bucket"], c["category"], c["source"], c["field"],
                                                         c["cases"], c["actors"], 1 if c["systematic"] else 0)
              for c in report["clusters"]]
    lines += ["", "| bucket | category | source | field | action | grounding |", "|---|---|---|---|---|---|"]
    lines += ["| %s | %s | %s | %s | %s | %d |" % (p["bucket"], p["category"], p["source"], p["field"],
                                                    p["proposed_action"], len(p["grounding"]))
              for p in report["proposals"]]
    lines += ["", "Exemplar candidates (names only; the verdict text is in the JSON report):"]
    for category, block in sorted(report["exemplar_candidates"].items()):
        for item in block["exemplars"]:
            lines.append("- %s %s: %s || %s" % (category, block["version"], _render(item["product_names"][0]),
                                               _render(item["product_names"][1])))
    with open(path, "w", encoding="ascii", errors="backslashreplace", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")


def main(argv: Optional[List[str]] = None, client: Any = None) -> int:
    mode = learning_mode()
    if mode == common.MODE_OFF:
        logger.info("%s mode=off %s not set; skipping run", PREFIX, FLAG)
        return 0
    parser = argparse.ArgumentParser(prog="cron_learning")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--report", default=None)
    parser.add_argument("--report-md", default=None)
    parser.add_argument("--day", default=None)
    args = parser.parse_args(argv)
    mode = common.cli_mode(mode, args.dry_run)
    try:
        day = (datetime.strptime(args.day, "%Y-%m-%d").date() if args.day
               else (common._now() - timedelta(days=1)).date())
    except ValueError:
        logger.warning("%s bad --day; skipping run", PREFIX)
        return 0
    if client is None:
        try:
            client = common._admin_client()
            if client is None:
                raise LookupError("no client")
        except Exception as exc:  # noqa: BLE001 - a run that cannot read has nothing to report
            logger.error("%s no service-role client (%s)", PREFIX, type(exc).__name__)
            return 1
    days, need_cases, need_actors = window_days(), min_cases(), min_devices()
    cap, per_category = max_rows(), exemplars_per_category()
    end = datetime.combine(day + timedelta(days=1), time(0, 0), tzinfo=timezone.utc)
    start = end - timedelta(days=days)
    logger.info("%s mode=%s day=%s window_days=%d", PREFIX, mode, day.isoformat(), days)
    kb = common.kb_leaf()
    gathered = _gather(client, kb.KB_CATEGORY, start.isoformat(), end.isoformat(), cap)
    tables: _Tables = gathered["tables"]
    for table in READ_TABLES:
        st = tables.state[table]
        logger.info("%s table=%s status=%s rows=%d", PREFIX, table, st["status"], st["rows"])

    cases: _Cases = gathered["cases"]
    dropped = [gathered["dropped_fields"]]  # D22d: the unclean field-name rows
    clusters = _clusters(cases, need_cases, need_actors)
    proposals = []
    for c in clusters:
        if not c["systematic"]:
            continue
        grounding = _grounding(c, gathered["specs"], dropped)
        proposals.append({"bucket": c["bucket"], "category": c["category"], "source": c["source"],
                          "field": c["field"], "cases": c["cases"], "distinct_actors": c["actors"],
                          "judge_state": _JUDGE_PENDING, "grounding": grounding,
                          "proposed_action": _action(c["bucket"], c["source"], grounding)})
    for c in clusters:
        c.pop("_products", None)
        logger.info("%s cluster bucket=%s category=%s source=%s field=%s cases=%d actors=%d systematic=%d",
                    PREFIX, c["bucket"], c["category"], c["source"], c["field"], c["cases"], c["actors"],
                    1 if c["systematic"] else 0)
    for p in proposals:
        logger.info("%s proposal bucket=%s category=%s source=%s field=%s action=%s grounding=%d", PREFIX,
                    p["bucket"], p["category"], p["source"], p["field"], p["proposed_action"], len(p["grounding"]))

    confirmed = _confirmed(gathered["feedback"], gathered["comparisons"])
    exemplars = _exemplars(confirmed, day, per_category, dropped)
    evals = _eval_candidates(confirmed, dropped)
    for category, block in exemplars.items():
        logger.info("%s exemplar_set category=%s version=%s count=%d", PREFIX, category, block["version"],
                    block["count"])
        for item in block["exemplars"]:
            logger.info("%s exemplar category=%s version=%s names=%s || %s", PREFIX, category, block["version"],
                        _render(item["product_names"][0]), _render(item["product_names"][1]))
    for item in evals:
        priced = 1 if any(item["confirmed_prices"].values()) else 0
        logger.info("%s eval_case category=%s winner=%d prices=%d names=%s || %s", PREFIX, item["category"],
                    item["confirmed_winner_index"], priced, _render(item["product_names"][0]),
                    _render(item["product_names"][1]))

    metrics = _metrics(cases, clusters, proposals, exemplars, evals, gathered, dropped[0])
    rows: List[Dict[str, Any]] = []
    not_built = 0
    for name, value, n in metrics:
        logger.info("%s metric=%s value=%s n=%d", PREFIX, name, value, n)
        row = kb.build_coverage_row(day=day, metric=name, value=value, n=n)
        if row is None:
            not_built += 1
            continue
        rows.append(row)

    report = {
        "schema": REPORT_SCHEMA, "day": day.isoformat(), "mode": mode, "window_days": days,
        "window_start": start.isoformat(), "window_end": end.isoformat(),
        "thresholds": {"min_cases": need_cases, "min_devices": need_actors, "max_rows": cap,
                       "exemplars_per_category": per_category},
        "judge_state": _JUDGE_PENDING,
        "actor_basis": {COMPARISON_FEEDBACK_TABLE: "user_id (proxy for device)",
                        VERDICT_CRITIQUES_TABLE: "comparisons.user_id (proxy)",
                        KB_FEEDBACK_TABLE: "device_key", common.KB_GAPS_TABLE: "none"},
        "tables": {t: dict(tables.state[t]) for t in READ_TABLES},
        "buckets": {b: {"cases": len(cases.by_bucket[b]), "actors": len(cases.bucket_actors(b)),
                        "inputs": list(_BUCKET_INPUTS[b]), "note": _BUCKET_NOTES[b]} for b in BUCKETS},
        "clusters": clusters,
        "proposals": proposals,
        "exemplar_candidates": exemplars,
        "eval_candidates": evals,
        "context": dict(gathered["context"]),
        "dropped_deidentify": dropped[0],
        "metrics": metrics,
    }
    try:
        common.write_report(args.report, report)
        _write_md(args.report_md, report)
    except Exception as exc:  # noqa: BLE001 - the log copy stands
        logger.warning("%s report write failed (%s)", PREFIX, type(exc).__name__)
    if mode == common.MODE_APPLY and rows:
        try:
            client.table(KB_COVERAGE_TABLE).upsert(rows, on_conflict="day,metric").execute()
        except Exception as exc:  # noqa: BLE001 - one WARNING, exit 0
            logger.warning("%s upsert failed (%s)", PREFIX, type(exc).__name__)
    logger.info("%s totals rows=%d not_built=%d clusters=%d systematic=%d mode=%s", PREFIX, len(rows),
                not_built, len(clusters), sum(1 for c in clusters if c["systematic"]), mode)
    return 0


run = main

if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(level=logging.INFO)
    raise SystemExit(main())
