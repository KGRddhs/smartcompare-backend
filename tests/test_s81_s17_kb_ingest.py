"""S81-17 KB-INGEST (+ D05 FIELD-STATUS) RED rows (spec S81-G3, unit S81-17
section 5, as amended by RULINGS_S81_G3: S4 pins the closed 2.2 vocabulary
(R-G3-6), S20 expects ``elapsed_ms=<int>`` (R-G3-7), gaps at identity high OR
medium and cards / offers / images / reviews at high only (R-G3-8), the hook
positions of R-G3-10, the offer / image / review rules of R-G3-11).

RED rows S1..S21 fail at base on an AssertionError only: ``app.services.kb_ingest``
and ``app.services.live_robots`` are reached through ``_ki()`` / ``_lr()``
(find_spec + an assertion), never imported at module top. PIN rows P1 / P2 are
green at base with the FULL configuration (``KB_INGEST_GAP_MAX`` set,
``ENABLE_SYNC_DB_OFFLOAD`` both ways, a raising ``_admin_client`` installed through
a getattr-safe patch that is a no-op at base, the ``_fire_and_forget`` label
recorder and the ``asyncio.to_thread`` recorder) against
tests/fixtures/s81_s17_flag_off_golden.json, recorded at base with the FY25
normalisation of tests/test_s75_fanout_identity.py (copied here, never
imported; re-record with ``python -m tests.test_s81_s17_kb_ingest <out.json>`` at
the base sha only).

The compare rows drive the REAL entries over the FY25 faked pipeline; the job
rows call ``kb_ingest.build_job`` (the documented pure projection) and
``kb_ingest.run_job`` with an in-memory service-role client recorder (table /
upsert / insert / select / in_ / eq / update / execute + the executing thread)
and the D14 records seeded through ``live_robots.records_snapshot`` (R-G3-5).
Contract assumptions this file fixes (stated in the RED report): ``captured_at``
is an aware datetime; ``field_status`` called without a vision argument reads
identity source ``parse``.

Hygiene: pure ASCII, LF; bounded runner only; netguard on (every leaf faked);
synthetic identities and hosts only; no key-shaped literal.
"""
from __future__ import annotations

import asyncio
import copy
import hashlib
import importlib
import importlib.util
import json
import logging
import os
import re
import sys
import threading
import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

if __name__ == "__main__":  # pragma: no cover - the base recorder runs outside pytest
    import socket

    import dotenv
    import dotenv.main

    dotenv.load_dotenv = lambda *a, **k: False  # never read a developer .env
    dotenv.main.load_dotenv = lambda *a, **k: False
    for _name in ("REDIS_URL", "UPSTASH_REDIS_URL", "UPSTASH_REDIS_TOKEN",
                  "UPSTASH_REDIS_REST_URL", "SUPABASE_URL", "SUPABASE_SERVICE_KEY",
                  "SUPABASE_ANON_KEY", "SENTRY_DSN"):
        os.environ.pop(_name, None)
    _LOCAL = ("127.0.0.1", "::1", "localhost", "", None)
    _real_gai = socket.getaddrinfo

    def _gai(host, *args, **kwargs):
        if host not in _LOCAL:
            raise OSError("s17 recorder: network blocked")
        return _real_gai(host, *args, **kwargs)

    socket.getaddrinfo = _gai
    os.environ["OPENAI_API_KEY"] = "sk" + "-test-dummy"

os.environ.setdefault("OPENAI_API_KEY", "sk" + "-test-dummy")

import pytest  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "tests" / "fixtures" / "s81_s17_flag_off_golden.json"
KI = "app.services.kb_ingest"
LR = "app.services.live_robots"
INGEST = "ENABLE_KB_INGEST"
EXPOSE = "ENABLE_FIELD_STATUS_METADATA"
CLEARED_ENV = (
    INGEST, EXPOSE, "KB_INGEST_GAP_MAX", "ENABLE_SYNC_DB_OFFLOAD",
    "ENABLE_LIVE_ROBOTS_REGISTRY", "ENABLE_LIVE_ROBOTS_HEALTH_FLUSH",
    "ENABLE_PARSE_PRESPLIT", "ENABLE_PARSE_BUDGET", "PARSE_TIMEOUT_SECONDS",
    "ENABLE_UNIFIED_SEARCH_BOUND", "UNIFIED_SEARCH_TIMEOUT_SECONDS",
    "ENABLE_PHASE2_RESIDUAL_GUARD", "PHASE2_MIN_RESIDUAL_SECONDS", "DEBUG_STAGE_TIMINGS",
    "ENABLE_FULL_STREAM_DEADLINE", "ENABLE_RESULT_STATUS_METADATA", "ENABLE_LLM_LEDGER_V2",
    "ENABLE_LLM_SPEND_BREAKER", "ENABLE_ANTHROPIC_TEXT", "ENABLE_ANTHROPIC_VISION",
    "ENABLE_ANTHROPIC_VERDICT", "ENABLE_ANTHROPIC_CRITIC", "ENABLE_ANTHROPIC_MODERATION",
    "ENABLE_SONNET_ESCALATION", "ENABLE_OPENAI_PRE_V3", "ENABLE_FRAGRANCE_ONLY_GATE",
    "ENABLE_JSONLD_RATING", "ENABLE_IMAGE_PIPELINE_V2", "ENABLE_DATA_GUARDS_V2",
    "ENABLE_PREVERDICT_DISCONNECT_ABORT",
    "ENABLE_RESULT_GATE",  # S81-20 E14: an exported result gate refuses these rows' thin compare bodies
)
OFF_SPELLINGS = [None, "false", " 0 ", "OFF"]
NOW = datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc)
NOW_Z = "2026-11-01T12:00:00Z"
HOST_A = "store-a.example.com"
HOST_B = "store-b.example.com"
HOST_Z = "store-z.example.com"
VOLATILE = frozenset({"elapsed_ms", "elapsed_seconds", "timestamp", "generated_at",
                      "created_at", "started_at", "cached_at", "fetched_at", "at",
                      "stage_timings_ms", "orchestrator_timings_ms", "request_id"})
D05_FIELDS = ("identity", "image", "price", "size", "concentration", "specs", "rating",
              "review_count")
KB_WRITE_TABLES = {"kb_products", "kb_variants", "kb_offers", "kb_images", "kb_reviews",
                   "kb_gaps"}
KB_NEVER_TABLES = {"kb_feedback", "kb_specs", "kb_merchants", "kb_coverage_daily"}
# R-G3-6: the closed 2.2 vocabulary (a new value is a RED change).
VOCAB_STATES = {f: {"known", "unknown"} for f in D05_FIELDS}
VOCAB_STATES["price"] = {"fresh", "stale", "unknown"}
VOCAB_SOURCES = {
    "identity": {"vision", "parse"}, "image": {"retailer_page", "search"},
    "size": {"listing", "specs"}, "concentration": {"specs"}, "specs": {"search"},
    "rating": {"retailer_jsonld", "provider"}, "review_count": {"retailer_jsonld", "provider"},
}
VOCAB_REASONS = {
    "identity": {"placeholder_identity", "no_product_id"}, "image": {"no_image"},
    "price": {"no_price", "estimated", "served_from_cache", "unmarked"},
    "size": {"no_size", "model_knowledge"},
    "concentration": {"no_concentration", "model_knowledge"},
    "specs": {"no_specs", "model_knowledge"}, "rating": {"no_rating", "derived_rating"},
    "review_count": {"no_review_count"},
}
_HOST_RE = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+$")
_ISO_Z = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")


# ---------------------------------------------------------------------------
# harness
# ---------------------------------------------------------------------------

def _present(name):
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def _ki():
    assert _present(KI), "app/services/kb_ingest.py does not exist (S81-17 not implemented)"
    return importlib.import_module(KI)


def _lr():
    assert _present(LR), "app/services/live_robots.py does not exist (D14 not implemented)"
    return importlib.import_module(LR)


def _attr(mod, name):
    assert hasattr(mod, name), "%s.%s is missing (S81-17 not implemented)" % (mod.__name__, name)
    return getattr(mod, name)


_MISSING = object()


class _Patcher:
    """monkeypatch's API outside pytest (the base recorder)."""

    def __init__(self):
        self._undo = []

    def setattr(self, obj, name, value, raising=True):
        self._undo.append(("attr", obj, name, getattr(obj, name, _MISSING)))
        setattr(obj, name, value)

    def setenv(self, name, value):
        self._undo.append(("env", None, name, os.environ.get(name, _MISSING)))
        os.environ[name] = value

    def delenv(self, name, raising=True):
        self._undo.append(("env", None, name, os.environ.get(name, _MISSING)))
        os.environ.pop(name, None)

    def undo(self):
        while self._undo:
            kind, obj, name, value = self._undo.pop()
            if kind == "attr":
                if value is _MISSING:
                    delattr(obj, name)
                else:
                    setattr(obj, name, value)
            elif value is _MISSING:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    import app.main  # noqa: F401  (FIRST: the dotenv-override hazard)

    for name in CLEARED_ENV:
        monkeypatch.delenv(name, raising=False)
    yield


def _set_flag(mp, name, value):
    if value is None:
        mp.delenv(name, raising=False)
    else:
        mp.setenv(name, value)


def _iso(moment):
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def _record(origin, *, state="allow", disallow=False, expired=False):
    rules = [["disallow", "/"]] if disallow else [["allow", "/"]]
    return {
        "state": state, "status": 200,
        "fetched_at": _iso(NOW - timedelta(days=4) if expired else NOW - timedelta(hours=1)),
        "next_reread": _iso(NOW - timedelta(days=2) if expired else NOW + timedelta(hours=23)),
        "crawl_delay": None, "origin": origin, "source": "robots_txt",
        "rules": {"qarenbot": rules, "star": rules}, "probed": "/",
    }


def _view(host, *, status="live", disallow=False, expired=False):
    return {"host": host, "status": status, "deny": False,
            "robots": _record("https://" + host, disallow=disallow, expired=expired),
            "challenge": None}


def _records(**over):
    recs = {HOST_A: _view(HOST_A), HOST_B: _view(HOST_B)}
    for host, view in over.items():
        recs[host] = view
    return recs


def _deny_host():
    from app.services import deny_hosts
    return deny_hosts.DENY_HOSTS[0]


def _product(i=0, **over):
    if i == 0:
        brand, name, host, slug = "Acme", "Nimbus Noir Eau de Parfum", HOST_A, "nimbus-noir"
    else:
        brand, name, host, slug = "Zephyra", "Velvet Dusk Eau de Toilette", HOST_B, "velvet-dusk"
    url = "https://" + host + "/products/" + slug + "?ref=" + "cmp"
    image = "https://" + host + "/img/" + slug + ".jpg"
    product = {
        "brand": brand, "name": name, "full_name": brand + " " + name, "variant": None,
        "category": "fragrances",
        "price": {"amount": 42.5 if i == 0 else 37.0, "currency": "BHD", "url": url,
                  "retailer": host, "source_method": "page_scrape_jsonld", "estimated": False,
                  "_cached": False, "size": "100ml", "image_url": image, "in_stock": True,
                  "_jsonld_facts": {"sku": "SKU-" + slug, "rating": {"value": 4.6, "count": 31}}},
        "image_url": image,
        "specs": {"concentration": "Eau de Parfum" if i == 0 else "Eau de Toilette",
                  "volume": "100ml", "top_notes": "bergamot", "_field_confidence": {}},
        "rating": 4.6, "review_count": 31, "rating_verified": False, "rating_derived": False,
        "rating_source": {"name": host + " (product page)", "url": url},
        "jsonld_rating": {"value": 4.6, "count": 31, "source": host, "url": url,
                          "extract_method": "jsonld_aggregate_rating"},
        "reviews": {"highlights": ["good"], "summary": "ok"},
    }
    for key, value in over.items():
        product[key] = value
    return product


def _with_price(product, **over):
    product = copy.deepcopy(product)
    product["price"].update(over)
    return product


def _result(product_data):
    body_products = []
    for p in product_data:
        q = {k: copy.deepcopy(v) for k, v in p.items() if not k.startswith("_")}
        body_products.append(q)
    return {"success": True, "category_used": "fragrances", "products": body_products,
            "metadata": {}}


def _pid(product):
    from app.services import kb_service
    return kb_service.kb_product_id(product["brand"], product["name"], product.get("variant"))


# --- the service-role client recorder (stateful insert-ignore semantics) ----------------

_CONFLICT = {
    "kb_products": ("id",), "kb_variants": ("id",),
    "kb_offers": ("variant_id", "merchant_id", "market", "observed_currency", "amount",
                  "list_vs_sale"),
    "kb_images": ("product_id", "url"), "kb_reviews": ("product_id", "source_url"),
    "kb_gaps": ("product_key", "field"),
}


class _Query:
    def __init__(self, client, table):
        self.client = client
        self.table = table
        self.op = None
        self.payload = None
        self.kwargs = {}
        self.filters = []
        self.columns = None

    def _set(self, op, payload=None, **kwargs):
        self.op, self.payload, self.kwargs = op, copy.deepcopy(payload), dict(kwargs)
        return self

    def upsert(self, rows, **kwargs):
        return self._set("upsert", rows, **kwargs)

    def insert(self, rows, **kwargs):
        return self._set("insert", rows, **kwargs)

    def update(self, payload, **kwargs):
        return self._set("update", payload, **kwargs)

    def delete(self, **kwargs):
        return self._set("delete", None, **kwargs)

    def select(self, columns="*", **kwargs):
        if self.op is None:
            self.op = "select"
        self.columns = columns
        return self

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)

        def _filter(*args, **kwargs):
            self.filters.append([name, list(args), dict(kwargs)])
            return self
        return _filter

    def execute(self):
        return self.client._execute(self)


class _Resp:
    def __init__(self, data):
        self.data = data
        self.count = None


class _KbClient:
    def __init__(self, *, cas_empty=False):
        self.ops = []
        self.store = {t: {} for t in _CONFLICT}
        self.cas_empty = cas_empty
        self.lock = threading.Lock()

    def __call__(self, *a, **k):
        return self

    def table(self, name):
        return _Query(self, name)

    def _key(self, table, row):
        return tuple(str(row.get(c)) for c in _CONFLICT.get(table, ("id",)))

    def _execute(self, q):
        with self.lock:
            entry = {"table": q.table, "op": q.op, "payload": q.payload, "kwargs": q.kwargs,
                     "filters": q.filters, "columns": q.columns,
                     "thread": threading.get_ident()}
            self.ops.append(entry)
            store = self.store.setdefault(q.table, {})
            if q.op in ("upsert", "insert"):
                rows = q.payload if isinstance(q.payload, list) else [q.payload]
                out = []
                for row in rows:
                    key = self._key(q.table, row)
                    if q.kwargs.get("ignore_duplicates") is True:
                        if key in store:
                            continue
                    store[key] = dict(row)
                    out.append(dict(row))
                entry["returned"] = out
                return _Resp(out)
            if q.op == "select":
                rows = list(store.values())
                for name, args, _kw in q.filters:
                    if name == "in_" and len(args) == 2:
                        rows = [r for r in rows if r.get(args[0]) in list(args[1])]
                    elif name == "eq" and len(args) == 2:
                        rows = [r for r in rows if r.get(args[0]) == args[1]]
                return _Resp([dict(r) for r in rows])
            if q.op == "update":
                if q.table == "kb_gaps" and self.cas_empty:
                    return _Resp([])
                rows = list(store.values())
                for name, args, _kw in q.filters:
                    if name == "eq" and len(args) == 2:
                        rows = [r for r in rows if str(r.get(args[0])) == str(args[1])]
                for r in rows:
                    r.update(q.payload or {})
                return _Resp([dict(r) for r in rows])
            return _Resp([])

    def writes(self, table=None):
        return [o for o in self.ops if o["op"] in ("upsert", "insert", "update", "delete")
                and (table is None or o["table"] == table)]

    def rows(self, table):
        out = []
        for o in self.ops:
            if o["table"] == table and o["op"] in ("upsert", "insert"):
                out.extend(o["payload"] if isinstance(o["payload"], list) else [o["payload"]])
        return out


def _run_job(mp, product_data, *, region="bahrain", vision=False, records=None, client=None,
             cats=("fragrances", "fragrances"), result=None):
    ki, lr = _ki(), _lr()
    mp.setenv(INGEST, "true")
    mp.setattr(ki, "_now", lambda: NOW, raising=False)
    client = client if client is not None else _KbClient()
    mp.setattr(ki, "_admin_client", client, raising=False)
    recs = records if records is not None else _records()
    mp.setattr(lr, "records_snapshot", lambda: copy.deepcopy(recs), raising=False)
    mp.setattr(lr, "load_records_sync", lambda *_a, **_k: copy.deepcopy(recs), raising=False)
    snap = _attr(ki, "build_job")(
        result if result is not None else _result(product_data), copy.deepcopy(product_data),
        product_categories=list(cats), region=region, vision=vision, captured_at=NOW)
    _attr(ki, "run_job")(snap)
    return client


def _field_status(product_data, result=None):
    ki = _ki()
    return _attr(ki, "field_status")(copy.deepcopy(product_data),
                                     result if result is not None else _result(product_data),
                                     captured_at=NOW)


def _check_vocab(fs):
    assert isinstance(fs, list) and len(fs) == 2, fs
    for entry in fs:
        assert isinstance(entry, dict) and set(entry) == set(D05_FIELDS), entry
        for field in D05_FIELDS:
            item = entry[field]
            want_keys = {"state", "source", "reason"} | ({"as_of", "rung"} if field == "price" else set())
            assert isinstance(item, dict) and set(item) == want_keys, (field, item)
            state, source, reason = item["state"], item["source"], item["reason"]
            assert state in VOCAB_STATES[field], (field, state)
            if field == "price":
                assert source is None or (isinstance(source, str) and _HOST_RE.match(source)), source
                assert item["as_of"] is None or (isinstance(item["as_of"], str)
                                                 and _ISO_Z.match(item["as_of"])), item
                assert item["rung"] in (None, "page_evidence", "platform_api"), item
            else:
                assert source is None or source in VOCAB_SOURCES[field], (field, source)
            if state in ("known", "fresh"):
                assert reason is None, (field, item)
                if field != "price":
                    assert source in VOCAB_SOURCES[field], (field, item)
            else:
                assert reason in VOCAB_REASONS[field], (field, item)


# ---------------------------------------------------------------------------
# the faked compare (the FY25 driver of tests/test_s75_fanout_identity.py, copied)
# ---------------------------------------------------------------------------

QUERY = "iPhone 15 vs Galaxy S24"
VISION = [{"brand": "Apple", "name": "iPhone 15"}, {"brand": "Samsung", "name": "Galaxy S24"}]
LLM_PARSED = {"products": [
    {"brand": "Apple", "name": "iPhone 15", "variant": None, "category": "electronics",
     "search_query": "Apple iPhone 15"},
    {"brand": "Samsung", "name": "Galaxy S24", "variant": None, "category": "electronics",
     "search_query": "Samsung Galaxy S24"}], "comparison_type": "value"}
USAGE = {"prompt_tokens": 100, "completion_tokens": 50}


def _install(mp, svc, state):
    import app.services.structured_comparison_service as scs
    from app.services import content_safety_service as _cs
    from app.services import scoring_service as _ss

    async def _parse(query):
        out = json.loads(json.dumps(LLM_PARSED))
        if state.get("parse_fail"):
            out["products"] = out["products"][:1]  # one product: the parse-failure exit
        return out, dict(USAGE)

    async def _gen(*_a, **_k):
        return ({"winner_index": 0, "winner_declaration": "iPhone wins",
                 "winner_reason": "battery", "verdict": "v", "pros": {}, "cons": {}},
                {"prompt_tokens": 7, "completion_tokens": 3})

    async def _cat_llm(*_a, **_k):
        return "electronics"

    async def _search(query, num_results=10, **kwargs):
        return {"organic": [{"title": "T " + query[:20], "link": "https://example.com/a",
                             "snippet": "spec sheet battery 4000 mAh"}]}

    async def _specs(*_a, **_k):
        return {"battery_mah": 4000, "storage_gb": 128, "display_size_in": 6.1}

    async def _price(*_a, **_k):
        return {"amount": 120.0, "currency": "BHD", "estimated": False,
                "source_method": "local_bhd", "retailer": "Best Buy",
                "url": "https://www.bestbuy.com/site/x/1.p", "title": "x", "in_stock": True}

    async def _reviews(*_a, **_k):
        return {"highlights": ["good"], "summary": "ok"}

    async def _rating(*_a, **_k):
        return {"rating": 4.5, "review_count": 10, "rating_verified": True,
                "rating_source": {"name": "example", "url": "https://example.com/r"}}

    async def _empty(*_a, **_k):
        return {}

    async def _none(*_a, **_k):
        return None

    async def _moderate(_self, _text):
        state["events"].append(["moderate"])
        return _cs.SafetyResult(allowed=state["moderation_allowed"])

    real_ff = scs._fire_and_forget

    def _ff(coro, label):
        state["events"].append(["ff", label])
        state["labels"].append(label)
        return real_ff(coro, label)

    mp.setattr(_cs.ContentSafetyService, "moderate_output", _moderate)
    mp.setattr(scs, "_fire_and_forget", _ff)
    async def _blocked_log(*_a, **_k):
        state["events"].append(["log_content_blocked"])  # no Supabase write (hermetic)

    from app.services import audit_service as _audit

    mp.setattr(_audit, "log_content_blocked", _blocked_log)
    mp.setattr(scs, "parse_product_query", _parse)
    mp.setattr(scs, "generate_comparison", _gen)
    mp.setattr(scs, "reconcile_pair_fairness", lambda *a, **k: None)
    mp.setattr(scs, "classify_category_llm", _cat_llm)
    mp.setattr(scs, "get_scoring_service", lambda: _ss.ScoringService())
    mp.setattr(scs, "search_web", _search)
    mp.setattr(scs, "tier2_fill_non_negotiables", _empty)
    mp.setattr(scs, "tier3_synthesize_non_negotiables", _empty)
    mp.setattr(scs, "collect_retailer_ratings", lambda *a, **k: [])
    mp.setattr(scs, "get_product_image_url", _none)
    svc._get_specs = _specs
    svc._get_price = _price
    svc._get_reviews = _reviews
    svc._get_verified_rating = _rating
    svc._smart_fallback_extract = _empty
    if state["slow"]:
        async def _slow_fetch(product_info, *args, partial_slot=None, **kwargs):
            if partial_slot is not None and isinstance(svc._early_specs_buffer, list):
                svc._early_specs_buffer[partial_slot] = {
                    "brand": "", "name": product_info["name"],
                    "full_name": product_info["name"], "category": "electronics",
                    "specs": {"display": "6.1 in"}, "price": None}
            await asyncio.sleep(30)
        svc._fetch_product_data = _slow_fetch


async def _compare(mp, kind, *, query=QUERY, vision=None, moderation_allowed=True, slow=False,
                   cap=30.0, settle=0.0, until=None, state=None, parse_fail=False):
    import app.services.structured_comparison_service as scs

    state = state if state is not None else {}
    state.setdefault("events", [])
    state.setdefault("labels", [])
    state["moderation_allowed"] = moderation_allowed
    state["slow"] = slow
    state["parse_fail"] = parse_fail
    mp.setattr(scs, "STREAM_HARD_CAP_SECONDS", cap)
    svc = scs.StructuredComparisonService()
    _install(mp, svc, state)
    kwargs = {"vision_products": copy.deepcopy(vision)} if vision else {}
    if kind == "rest":
        payload = await asyncio.wait_for(
            svc.compare_from_text(query, region="bahrain", nocache=True, **kwargs), 60)
        state["events"].append(["return"])
    else:
        payload = []

        async def _drain():
            async for event in svc.compare_from_text_streaming(query, region="bahrain",
                                                               nocache=True):
                state["events"].append(["yield", event[0]])
                payload.append(list(event))
        await asyncio.wait_for(_drain(), 60)
    deadline = time.monotonic() + settle
    while time.monotonic() < deadline:
        if until is not None and until():
            break
        await asyncio.sleep(0.02)
    return payload


def _normalize(obj):
    if isinstance(obj, dict):
        return {str(k): _normalize(v) for k, v in obj.items() if k not in VOLATILE}
    if isinstance(obj, (list, tuple)):
        return [_normalize(v) for v in obj]
    if isinstance(obj, float):
        return repr(obj)
    return obj


def _digest(snapshot):
    blob = json.dumps(_normalize(snapshot), sort_keys=True, default=repr, ensure_ascii=True)
    return hashlib.sha256(blob.encode("ascii")).hexdigest()


SCENARIOS = {
    "rest_full": ("rest", {}),
    "stream_full": ("stream", {}),
    "camera_full": ("rest", {"vision": VISION}),
}
LITERALS = {
    "rest_refusal": ("rest", {"moderation_allowed": False}),
    "stream_refusal": ("stream", {"moderation_allowed": False}),
    "rest_parse_fail": ("rest", {"parse_fail": True}),
}


def _strip_fs(payload):
    """The payload with metadata.field_status removed (every event of a stream)."""
    def _one(body):
        body = copy.deepcopy(body)
        if isinstance(body, dict) and isinstance(body.get("metadata"), dict):
            body["metadata"].pop("field_status", None)
        return body
    if isinstance(payload, list):
        return [[e[0], _one(e[1])] for e in payload]
    return _one(payload)


def _bodies(payload):
    if isinstance(payload, list):
        return [e[1] for e in payload if isinstance(e[1], dict)]
    return [payload]


def _has_fs(payload):
    return any(isinstance(b.get("metadata"), dict) and "field_status" in b["metadata"]
               for b in _bodies(payload))


def _golden():
    assert GOLDEN.exists(), "the S81-17 golden is missing: " + str(GOLDEN)
    return json.loads(GOLDEN.read_text(encoding="ascii"))


def _job_recorder(mp, *, block=None, raise_exc=None):
    """kb_ingest.run_job replaced by a recorder (the thread it ran on, the snap)."""
    ki = _ki()
    calls = []

    def _job(snap):
        calls.append({"thread": threading.get_ident(), "snap": snap, "done": False})
        if block is not None:
            block.wait(5.0)
        calls[-1]["done"] = True
        if raise_exc is not None:
            raise raise_exc

    mp.setattr(ki, "run_job", _job)
    return calls


# ---------------------------------------------------------------------------
# S1 readers
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("reader,name", [("kb_ingest_enabled", INGEST),
                                         ("field_status_metadata_enabled", EXPOSE)])
def test_S1_readers(monkeypatch, reader, name):
    ki = _ki()
    fn = _attr(ki, reader)
    for value in (None, "", "false", "0", " OFF ", "garbage"):
        _set_flag(monkeypatch, name, value)
        assert fn() is False, (reader, value)
    for value in ("true", " TRUE ", "1", "yes", "on"):
        _set_flag(monkeypatch, name, value)
        assert fn() is True, (reader, value)
    monkeypatch.setenv(name, "true")
    assert fn() is True
    monkeypatch.setenv(name, "false")
    assert fn() is False, "%s must be re-read per call" % reader


# ---------------------------------------------------------------------------
# S2 / S3 field_status (pure)
# ---------------------------------------------------------------------------

def test_S2_field_status_full_product():
    fs = _field_status([_product(0), _product(1)])
    _check_vocab(fs)
    first = fs[0]
    for field in D05_FIELDS:
        want = "fresh" if field == "price" else "known"
        assert first[field]["state"] == want and first[field]["reason"] is None, (field, first[field])
    assert first["identity"]["source"] == "parse"
    assert first["image"]["source"] == "retailer_page"
    assert first["price"] == {"state": "fresh", "source": HOST_A, "reason": None,
                              "as_of": NOW_Z, "rung": "page_evidence"}, first["price"]
    assert first["size"]["source"] == "listing"
    assert first["concentration"]["source"] == "specs"
    assert first["specs"]["source"] == "search"
    assert first["rating"]["source"] == "retailer_jsonld"
    assert first["review_count"]["source"] == "retailer_jsonld"
    assert fs[1]["price"]["source"] == HOST_B


def _miss_cases():
    p = _product(0)
    no_size_specs = dict(p["specs"])
    no_size_specs.pop("volume")
    tier3_conc = dict(p["specs"], _field_confidence={"concentration": "tier3_synthesis"})
    tier3_all = dict(p["specs"], _field_confidence={k: "tier3_synthesis" for k in
                                                    ("concentration", "volume", "top_notes")})
    no_mark = _with_price(p)
    no_mark["price"].pop("_cached")
    return [
        ("placeholder_identity", _product(0, brand="", name="Unknown Product"), "identity",
         {"state": "unknown", "reason": "placeholder_identity"}),
        ("no_image", dict(_with_price(p, image_url=None), image_url=None), "image",
         {"state": "unknown", "reason": "no_image"}),
        ("estimated", _with_price(p, estimated=True, source_method="estimated"), "price",
         {"state": "unknown", "reason": "estimated", "as_of": None, "rung": None}),
        ("served_from_cache", _with_price(p, _cached=True), "price",
         {"state": "stale", "reason": "served_from_cache", "as_of": None}),
        ("unmarked", no_mark, "price", {"state": "stale", "reason": "unmarked", "as_of": None}),
        ("no_size", dict(_with_price(p, size=None), specs=no_size_specs), "size",
         {"state": "unknown", "reason": "no_size"}),
        ("tier3_concentration", dict(p, specs=tier3_conc), "concentration",
         {"state": "unknown", "reason": "model_knowledge"}),
        ("only_tier3_specs", dict(p, specs=tier3_all), "specs",
         {"state": "unknown", "reason": "model_knowledge"}),
        ("derived_rating", dict(p, rating_derived=True, jsonld_rating=None), "rating",
         {"state": "unknown", "reason": "derived_rating"}),
        ("no_review_count", dict(p, review_count=None), "review_count",
         {"state": "unknown", "reason": "no_review_count"}),
        ("platform_rung", _with_price(p, source_method="shopify_json"), "price",
         {"state": "fresh", "rung": "platform_api"}),
        ("converted_usd_rung", _with_price(p, source_method="converted_usd"), "price",
         {"state": "fresh", "rung": None}),
    ]


MISS_CASES = _miss_cases()


@pytest.mark.parametrize("case", MISS_CASES, ids=[c[0] for c in MISS_CASES])
def test_S3_field_status_misses(case):
    _name, product, field, want = case
    fs = _field_status([product, _product(1)])
    _check_vocab(fs)
    got = fs[0][field]
    for key, value in want.items():
        assert got.get(key) == value, (case[0], got)


# ---------------------------------------------------------------------------
# S4 / S5 exposure; S6 no key off the success exits
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("kind", ["rest", "stream"])
def test_S4_exposure_rest_and_stream(monkeypatch, kind):
    _ki()
    off = asyncio.run(_compare(monkeypatch, kind))
    monkeypatch.setenv(EXPOSE, "true")
    on = asyncio.run(_compare(monkeypatch, kind))
    if kind == "rest":
        assert on.get("success") is True, on
        fs = (on.get("metadata") or {}).get("field_status")
        _check_vocab(fs)
    else:
        for name in ("settle_complete", "complete"):
            body = [e[1] for e in on if e[0] == name]
            assert body, name
            _check_vocab((body[0].get("metadata") or {}).get("field_status"))
    assert _digest(_strip_fs(on)) == _digest(off), "every other key equals the flag-OFF run"


def test_S5_exposure_camera(monkeypatch):
    _ki()
    monkeypatch.setenv(EXPOSE, "true")
    on = asyncio.run(_compare(monkeypatch, "rest", vision=VISION))
    fs = (on.get("metadata") or {}).get("field_status")
    _check_vocab(fs)
    assert [e["identity"]["source"] for e in fs] == ["vision", "vision"], fs


NEGATIVE = {
    "rest_refusal": ("rest", {"moderation_allowed": False}),
    "stream_refusal": ("stream", {"moderation_allowed": False}),
    "rest_parse_fail": ("rest", {"parse_fail": True}),
    "rest_timeout_partial": ("rest", {"slow": True, "cap": 0.5}),
}


@pytest.mark.parametrize("name", sorted(NEGATIVE))
def test_S6_no_key_off_the_success_exits(monkeypatch, name):
    _ki()
    _job_recorder(monkeypatch)
    monkeypatch.setenv(EXPOSE, "true")
    monkeypatch.setenv(INGEST, "true")
    control = {}
    good = asyncio.run(_compare(monkeypatch, NEGATIVE[name][0], state=control))
    assert _has_fs(good) and "kb_ingest" in control["labels"], "control: the success exit stamps"
    state = {}
    kind, kwargs = NEGATIVE[name]
    payload = asyncio.run(_compare(monkeypatch, kind, state=state, settle=0.2, **kwargs))
    assert not _has_fs(payload), "no field_status off the success exits: %s" % name
    assert "kb_ingest" not in state["labels"], "no kb_ingest job off the success exits: %s" % name


# ---------------------------------------------------------------------------
# S7 one job per compare; S8 never awaited; S9 job failure
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("kind", ["rest", "stream"])
def test_S7_one_job_per_compare_after_moderation(monkeypatch, kind):
    _ki()
    monkeypatch.setenv(INGEST, "true")
    calls = _job_recorder(monkeypatch)
    state = {}
    loop_thread = threading.get_ident()
    asyncio.run(_compare(monkeypatch, kind, state=state, settle=2.0, until=lambda: bool(calls)))
    assert state["labels"].count("kb_ingest") == 1, state["labels"]
    events = state["events"]
    i_mod = events.index(["moderate"])
    i_job = events.index(["ff", "kb_ingest"])
    end = ["return"] if kind == "rest" else ["yield", "settle_complete"]
    i_end = events.index(end)
    assert i_mod < i_job < i_end, events
    assert len(calls) == 1 and calls[0]["thread"] != loop_thread, \
        "run_job runs once, through asyncio.to_thread (a worker thread)"


@pytest.mark.parametrize("kind", ["rest", "stream"])
def test_S8_job_never_awaited(monkeypatch, kind):
    _ki()
    monkeypatch.setenv(INGEST, "true")
    gate = threading.Event()
    calls = _job_recorder(monkeypatch, block=gate)
    state = {}

    async def _go():
        try:
            payload = await asyncio.wait_for(_compare(monkeypatch, kind, state=state), 10)
            finished_at_return = [c["done"] for c in calls]
            deadline = time.monotonic() + 2.0
            while not calls and time.monotonic() < deadline:
                await asyncio.sleep(0.02)
            return payload, finished_at_return
        finally:
            gate.set()

    payload, finished = asyncio.run(_go())
    if kind == "rest":
        assert payload.get("success") is True
    else:
        assert any(e[0] == "complete" for e in payload)
    assert calls, "a kb_ingest job was started"
    assert True not in finished, "the response left while the job was still blocked"


@pytest.mark.parametrize("kind", ["rest", "stream"])
def test_S9_job_failure_never_reaches_the_caller(monkeypatch, caplog, kind):
    _ki()
    monkeypatch.setenv(INGEST, "true")
    calls = _job_recorder(monkeypatch)
    good = asyncio.run(_compare(monkeypatch, kind, settle=2.0, until=lambda: bool(calls)))
    assert calls, "control: a job ran"

    class _JobBoom(Exception):
        pass

    _job_recorder(monkeypatch, raise_exc=_JobBoom("kb down"))
    caplog.clear()
    caplog.set_level(logging.WARNING)

    def _warned():
        return any("kb_ingest" in r.getMessage() and r.levelno == logging.WARNING
                   for r in caplog.records)

    bad = asyncio.run(_compare(monkeypatch, kind, settle=3.0, until=_warned))
    assert _digest(bad) == _digest(good), "a failing job never changes the response"
    warns = [r for r in caplog.records if r.levelno == logging.WARNING
             and "kb_ingest" in r.getMessage() and "_JobBoom" in r.getMessage()]
    assert len(warns) == 1, [r.getMessage() for r in caplog.records]


# ---------------------------------------------------------------------------
# S10..S20 the job (build_job + run_job, the client recorder)
# ---------------------------------------------------------------------------

def _pair(**over0):
    return [_product(0, review_count=None, **over0), _product(1)]


def test_S10_builder_only_writes(monkeypatch):
    from app.services import kb_service

    client = _run_job(monkeypatch, _pair())
    tables = {o["table"] for o in client.ops}
    assert tables, "the job wrote nothing"
    assert tables <= KB_WRITE_TABLES and not (tables & KB_NEVER_TABLES), tables
    for o in client.ops:
        if o["op"] in ("upsert", "insert"):
            assert o["op"] == "upsert" and o["kwargs"].get("ignore_duplicates") is True, o
            rows = o["payload"] if isinstance(o["payload"], list) else [o["payload"]]
            for row in rows:
                assert set(row) == set(kb_service.KB_BUILDER_KEYS[o["table"]]), (o["table"], row)


@pytest.mark.parametrize("level", ["high", "medium", "low", "unresolved"])
def test_S11_confidence_gates(monkeypatch, level):
    if level == "high":
        data = _pair()
    elif level == "medium":
        data = [_product(0, review_count=None), _product(1, brand="")]
    elif level == "low":
        data = [_product(0), copy.deepcopy(_product(0))]
    else:
        data = [_product(0, brand="", name="Unknown Product"), _product(1)]
    client = _run_job(monkeypatch, data)
    written = {o["table"] for o in client.writes()}
    if level == "high":
        assert written >= KB_WRITE_TABLES, written
    elif level == "medium":
        assert written == {"kb_gaps"}, written
        assert {r["product_key"] for r in client.rows("kb_gaps")} == {_pid(data[0])}
    else:
        assert client.ops == [], "no write at all at %s identity: %r" % (level, client.ops)


def _offer_cases():
    deny = _deny_host()
    p = _product(0)
    origin_url = "https://www." + HOST_A + "/products/nimbus-noir"
    return [
        ("converted_usd", _with_price(p, source_method="converted_usd"), {}, "bahrain"),
        ("estimated", _with_price(p, estimated=True, source_method="estimated"), {}, "bahrain"),
        ("render_tier", _with_price(p, source_method="scrapedo_rendered"), {}, "bahrain"),
        ("non_registry_host", _with_price(p, url="https://" + HOST_Z + "/products/nimbus-noir"),
         {}, "bahrain"),
        ("row_blocked", p, {HOST_A: _view(HOST_A, status="blocked")}, "bahrain"),
        ("robots_disallow", p, {HOST_A: _view(HOST_A, disallow=True)}, "bahrain"),
        ("expired_record", p, {HOST_A: _view(HOST_A, expired=True)}, "bahrain"),
        ("origin_mismatch", _with_price(p, url=origin_url), {}, "bahrain"),
        ("deny_host", _with_price(p, url="https://" + deny + "/products/nimbus-noir"),
         {deny: _view(deny)}, "bahrain"),
        ("region_not_bahrain", p, {}, "uae"),
    ]


OFFER_CASES = _offer_cases()


@pytest.mark.parametrize("case", OFFER_CASES, ids=[c[0] for c in OFFER_CASES])
def test_S12_offer_refusals(monkeypatch, case):
    _name, p0, recs, region = case
    p1 = _with_price(_product(1), url="https://" + HOST_Z + "/products/velvet-dusk")
    client = _run_job(monkeypatch, [p0, p1], records=_records(**recs), region=region)
    assert client.ops, "control: the high-identity job wrote its cards"
    assert client.rows("kb_offers") == [], (case[0], client.rows("kb_offers"))


def test_S12_offer_allowed(monkeypatch):
    from app.services import kb_service

    p0 = _product(0)
    p1 = _with_price(_product(1), url="https://" + HOST_Z + "/products/velvet-dusk")
    client = _run_job(monkeypatch, [p0, p1])
    rows = client.rows("kb_offers")
    assert len(rows) == 1, rows
    row = rows[0]
    ts = kb_service._ts_iso(NOW)
    assert row["variant_id"] == _pid(p0) + "|100", row
    assert row["merchant_id"] == HOST_A and row["market"] == "BH", row
    assert row["observed_currency"] == "BHD" and row["evidence_rung"] == "page_evidence", row
    assert row["canonical_url"] == "https://" + HOST_A + "/products/nimbus-noir", row
    assert Decimal(row["amount"]) == Decimal("42.5"), row
    assert row["captured_at"] == row["first_seen"] == row["last_seen"] == ts, row


def test_S13_re_observation_is_one_update(monkeypatch):
    from app.services import kb_service

    p0 = _product(0)
    p1 = _with_price(_product(1), url="https://" + HOST_Z + "/products/velvet-dusk")
    client = _KbClient()
    _run_job(monkeypatch, [p0, p1], client=client)
    client.ops.clear()
    _run_job(monkeypatch, [p0, p1], client=client)
    offer_ins = [o for o in client.ops if o["table"] == "kb_offers" and o["op"] == "upsert"]
    assert offer_ins and all(o["returned"] == [] for o in offer_ins), offer_ins
    updates = [o for o in client.ops if o["table"] == "kb_offers" and o["op"] == "update"]
    assert len(updates) == 1, updates
    upd = updates[0]
    assert set(upd["payload"]) == set(kb_service.KB_OFFER_UPSERT_SET), upd["payload"]
    eq_cols = {f[1][0] for f in upd["filters"] if f[0] == "eq"}
    assert eq_cols == set(kb_service.KB_OFFER_OBSERVATION_KEY), upd["filters"]


def _image_cases():
    deny = _deny_host()
    return [
        ("deny_host_image", "https://" + deny + "/img/n.jpg", {}),
        ("http_image", "http://" + HOST_A + "/img/n.jpg", {}),
        ("disallow_host", "https://" + HOST_A + "/img/nimbus-noir.jpg",
         {HOST_A: _view(HOST_A, disallow=True)}),
    ]


IMAGE_CASES = _image_cases()


def test_S14_image_allowed(monkeypatch):
    p1 = _product(1, image_url=None)
    p1["price"]["image_url"] = None
    client = _run_job(monkeypatch, [_product(0), p1])
    rows = client.rows("kb_images")
    assert len(rows) == 1, rows
    row = rows[0]
    assert row["source"] == "retailer_jsonld" and row["provenance_host"] == HOST_A, row
    assert row["url"] == "https://" + HOST_A + "/img/nimbus-noir.jpg" and row["product_id"] == _pid(
        _product(0)), row


@pytest.mark.parametrize("case", IMAGE_CASES, ids=[c[0] for c in IMAGE_CASES])
def test_S14_image_refusals(monkeypatch, case):
    _name, image, recs = case
    p0 = _with_price(_product(0, image_url=image), image_url=image)
    p1 = _product(1, image_url=None)
    p1["price"]["image_url"] = None
    client = _run_job(monkeypatch, [p0, p1], records=_records(**recs))
    assert client.ops, "control: the job wrote"
    assert client.rows("kb_images") == [], (case[0], client.rows("kb_images"))


@pytest.mark.parametrize("variant", ["jsonld", "provider"])
def test_S15_reviews_channel1_only(monkeypatch, variant):
    p0 = _product(0) if variant == "jsonld" else _product(0, jsonld_rating=None)
    p1 = _product(1, jsonld_rating=None)
    client = _run_job(monkeypatch, [p0, p1])
    rows = client.rows("kb_reviews")
    if variant == "provider":
        assert client.ops and rows == [], rows
        return
    assert len(rows) == 1, rows
    row = rows[0]
    assert row["source"] == "retailer_jsonld" and row["source_url"] == p0["jsonld_rating"]["url"], row
    assert Decimal(str(row["aggregate_rating"])) == Decimal("4.6") and row["review_count"] == 31, row


def test_S16_no_specs_and_misses_become_gaps(monkeypatch):
    specs = dict(_product(0)["specs"], _field_confidence={"concentration": "tier3_synthesis"})
    p0 = _product(0, specs=specs, _spec_confidence={"concentration": "verified",
                                                    "top_notes": "verified"})
    client = _run_job(monkeypatch, [p0, _product(1)])
    assert not [o for o in client.ops if o["table"] == "kb_specs"], "no kb_specs from the live path"
    fields = {(r["product_key"], r["field"]) for r in client.rows("kb_gaps")}
    assert (_pid(p0), "concentration") in fields, fields


def _gap_rows(client):
    return client.rows("kb_gaps")


def _assert_gap_hygiene(client):
    for r in _gap_rows(client):
        assert not str(r["field"]).startswith("pdp_"), r
        assert r["field"] in D05_FIELDS and r["field"] != "identity", r
    for o in client.ops:
        if o["table"] == "kb_gaps" and o["op"] == "update":
            assert set(o["payload"]) == {"demand_count", "last_seen"}, o["payload"]


def test_S17_gap_rows_per_unknown_field(monkeypatch):
    p0 = _with_price(_product(0, image_url=None, review_count=None), image_url=None)
    client = _run_job(monkeypatch, [p0, _product(1)])
    rows = _gap_rows(client)
    assert {r["field"] for r in rows} == {"image", "review_count"}, rows
    for r in rows:
        assert r["product_key"] == _pid(p0) and r["demand_count"] == 1, r
        assert r["state"] == "open" and r["source_hint"] == HOST_A, r
    _assert_gap_hygiene(client)


def test_S17_gap_needs_operator_on_blocked_host(monkeypatch):
    p0 = _product(0, review_count=None)
    client = _run_job(monkeypatch, [p0, _product(1)],
                      records=_records(**{HOST_A: _view(HOST_A, status="blocked")}))
    rows = [r for r in _gap_rows(client) if r["product_key"] == _pid(p0)]
    assert rows and all(r["state"] == "needs_operator" for r in rows), rows
    _assert_gap_hygiene(client)


@pytest.mark.parametrize("cas_empty", [False, True], ids=["cas_wins", "cas_lost"])
def test_S17_existing_gap_compare_and_set(monkeypatch, caplog, cas_empty):
    from app.services import kb_service

    p0 = _product(0, review_count=None)
    pid = _pid(p0)
    client = _KbClient(cas_empty=cas_empty)
    client.store["kb_gaps"][(pid, "review_count")] = {
        "product_key": pid, "field": "review_count", "demand_count": 4, "state": "open",
        "source_hint": HOST_A, "first_seen": kb_service._ts_iso(NOW - timedelta(days=3)),
        "last_seen": kb_service._ts_iso(NOW - timedelta(days=3))}
    caplog.set_level(logging.INFO)
    _run_job(monkeypatch, [p0, _product(1)], client=client)
    selects = [o for o in client.ops if o["table"] == "kb_gaps" and o["op"] == "select"]
    assert len(selects) == 1, selects
    updates = [o for o in client.ops if o["table"] == "kb_gaps" and o["op"] == "update"]
    assert len(updates) == 1, "one CAS update per existing row, never retried: %r" % (updates,)
    upd = updates[0]
    assert upd["payload"] == {"demand_count": 5, "last_seen": kb_service._ts_iso(NOW)}, upd
    eqs = {f[1][0]: f[1][1] for f in upd["filters"] if f[0] == "eq"}
    assert eqs == {"product_key": pid, "field": "review_count", "demand_count": 4}, eqs
    _assert_gap_hygiene(client)
    line = [r.getMessage() for r in caplog.records if r.getMessage().startswith("[KB_INGEST] job ")]
    assert len(line) == 1, line
    lost = int(re.search(r"gap_cas_lost=(\d+)", line[0]).group(1))
    assert lost == (1 if cas_empty else 0), line[0]


def test_S17_gap_max_bounds_the_rows(monkeypatch):
    monkeypatch.setenv("KB_INGEST_GAP_MAX", "1")
    p0 = _with_price(_product(0, image_url=None, review_count=None), image_url=None, size=None)
    p0["specs"] = {"top_notes": "bergamot", "_field_confidence": {}}
    client = _run_job(monkeypatch, [p0, _product(1, review_count=None)])
    assert 1 <= len(_gap_rows(client)) <= 1, _gap_rows(client)
    _assert_gap_hygiene(client)


def test_S18_idempotent(monkeypatch):
    client = _KbClient()
    data = _pair()
    _run_job(monkeypatch, data, client=client)
    first_rows = {t: len(s) for t, s in client.store.items()}
    client.ops.clear()
    _run_job(monkeypatch, data, client=client)
    inserts = [o for o in client.ops if o["op"] in ("upsert", "insert")]
    assert inserts and all(o["returned"] == [] for o in inserts), \
        "the second job inserts nothing new: %r" % ([(o["table"], o["returned"]) for o in inserts],)
    assert {t: len(s) for t, s in client.store.items()} == first_rows
    assert any(o["op"] == "update" for o in client.ops), "the second job only updates"


def test_S19_job_calls_no_llm_serper_or_fetcher(monkeypatch):
    import curl_cffi.requests as curl_requests

    from app.services import api_budget_service, price_service, serper_service

    hits = []

    def _boom(name):
        def _f(*_a, **_k):
            hits.append(name)
            raise AssertionError("the ingest job called " + name)
        return _f

    monkeypatch.setattr(api_budget_service, "guarded_llm_create", _boom("guarded_llm_create"))
    monkeypatch.setattr(serper_service, "search_web", _boom("search_web"))
    monkeypatch.setattr(price_service, "curl_fetch_html", _boom("curl_fetch_html"))
    monkeypatch.setattr(price_service, "curl_fetch_html_same_site", _boom("same_site"))
    monkeypatch.setattr(curl_requests, "get", _boom("curl.get"))
    monkeypatch.setattr(curl_requests, "post", _boom("curl.post"))
    client = _run_job(monkeypatch, _pair())
    assert client.ops, "control: the job wrote"
    assert hits == [], hits


def test_S20_one_ints_only_log_line(monkeypatch, caplog):
    caplog.set_level(logging.DEBUG)
    _run_job(monkeypatch, _pair())
    lines = [r for r in caplog.records if r.getMessage().startswith("[KB_INGEST] job ")]
    assert len(lines) == 1, [r.getMessage() for r in caplog.records]
    assert lines[0].levelno == logging.INFO
    tokens = lines[0].getMessage()[len("[KB_INGEST] job "):].split()
    pairs = dict(t.split("=", 1) for t in tokens)
    assert all(re.fullmatch(r"\d+", v) for v in pairs.values()), pairs
    assert set(pairs) >= {"products", "variants", "offers", "offer_updates", "images", "reviews",
                          "gaps", "gap_increments", "gap_cas_lost", "not_built",
                          "elapsed_ms"}, pairs
    for r in caplog.records:
        msg = r.getMessage()
        if "[KB_INGEST]" in msg:
            for token in ("Acme", "Nimbus", "Zephyra", HOST_A, "http", "fragrances|"):
                assert token not in msg, msg


# ---------------------------------------------------------------------------
# S21 ingest ON does not move the body
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", sorted(SCENARIOS))
def test_S21_ingest_does_not_change_the_body(monkeypatch, name):
    _ki()
    monkeypatch.setenv(INGEST, "true")
    calls = _job_recorder(monkeypatch)
    kind, kwargs = SCENARIOS[name]
    payload = asyncio.run(_compare(monkeypatch, kind, settle=2.0, until=lambda: bool(calls),
                                   **kwargs))
    assert len(calls) == 1, "one kb_ingest job per compare"
    assert _digest(payload) == _golden()["digests"][name], name


# ---------------------------------------------------------------------------
# P1 / P2 flag-OFF identity (green at base)
# ---------------------------------------------------------------------------

def _full_config(mp, offload):
    mp.setenv("KB_INGEST_GAP_MAX", "16")
    _set_flag(mp, "ENABLE_SYNC_DB_OFFLOAD", offload)

    def _raising_client(*_a, **_k):
        raise AssertionError("flag OFF: the service-role client must never be built")

    if _present(KI):
        mp.setattr(importlib.import_module(KI), "_admin_client", _raising_client, raising=False)
    seen = []
    real = asyncio.to_thread

    async def _tt(func, *args, **kwargs):
        seen.append("%s.%s" % (getattr(func, "__module__", ""), getattr(func, "__name__", "")))
        return await real(func, *args, **kwargs)

    mp.setattr(asyncio, "to_thread", _tt)
    return seen


@pytest.mark.parametrize("offload", [None, "true"], ids=["offload_off", "offload_on"])
@pytest.mark.parametrize("spelling", OFF_SPELLINGS, ids=["unset", "false", "pad0", "OFF"])
def test_P1_flag_off_identity(monkeypatch, spelling, offload):
    _set_flag(monkeypatch, INGEST, spelling)
    _set_flag(monkeypatch, EXPOSE, spelling)
    seen = _full_config(monkeypatch, offload)
    want = _golden()["digests"]
    for name, (kind, kwargs) in SCENARIOS.items():
        state = {}
        payload = asyncio.run(_compare(monkeypatch, kind, state=state, settle=0.1, **kwargs))
        assert _digest(payload) == want[name], "flag OFF moved %s" % name
        assert "kb_ingest" not in state["labels"], state["labels"]
    assert not [s for s in seen if "kb_ingest" in s], seen


@pytest.mark.parametrize("name", sorted(LITERALS))
def test_P2_exits_untouched_off(monkeypatch, name):
    _full_config(monkeypatch, "true")
    kind, kwargs = LITERALS[name]
    payload = asyncio.run(_compare(monkeypatch, kind, **kwargs))
    assert _normalize(payload) == _golden()["literals"][name], name


# ---------------------------------------------------------------------------
# the base recorder
# ---------------------------------------------------------------------------

def _record_golden():  # pragma: no cover - run at the base sha only
    out = {"meta": {"unit": "S81-17 KB-INGEST", "recorded_at_base":
                    "744616e37d031923e522e30740b687de76482ee9",
                    "recorded_with": "ENABLE_KB_INGEST / ENABLE_FIELD_STATUS_METADATA unset; "
                    "the FY25 faked pipeline (tests/test_s75_fanout_identity.py, copied), "
                    "its normalisation (the clock fields dropped)"},
           "digests": {}, "literals": {}}
    for name, (kind, kwargs) in SCENARIOS.items():
        p = _Patcher()
        try:
            for env in CLEARED_ENV:
                p.delenv(env)
            out["digests"][name] = _digest(asyncio.run(_compare(p, kind, **kwargs)))
        finally:
            p.undo()
    for name, (kind, kwargs) in LITERALS.items():
        p = _Patcher()
        try:
            for env in CLEARED_ENV:
                p.delenv(env)
            out["literals"][name] = _normalize(asyncio.run(_compare(p, kind, **kwargs)))
        finally:
            p.undo()
    return out


if __name__ == "__main__":  # pragma: no cover
    import app.main  # noqa: F401,E402

    data = _record_golden()
    with open(sys.argv[1], "w", encoding="ascii", newline="\n") as handle:
        json.dump(data, handle, indent=1, sort_keys=True, ensure_ascii=True)
        handle.write("\n")
    print("wrote", sys.argv[1], len(data["digests"]), len(data["literals"]))
