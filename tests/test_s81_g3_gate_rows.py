"""S81-G3 GREEN-owned gate rows (GATE_S81_G3 GC-5 / GC-6).

G3-GR1 test_g3_gr1_offer_reobservation_amount_normalised (GC-6): PostgREST returns a
numeric ``amount`` while build_offer_row sends a 3-place string; the re-observation
match normalises both through Decimal, so an inserted (returned) offer is never
re-updated, and an offer the insert did not return is updated exactly once.
Mutant G3-GRM1 (the normalisation dropped) is killed by the ``returned_numeric`` case.

G3-GR2 test_g3_gr2_every_hook_records_outcomes (GC-5): with ENABLE_LIVE_ROBOTS_REGISTRY
ON and an ALLOW record, every hooked fetcher that observes a response counts one
``ok`` and one ``fail`` outcome under its fetcher label (shopify, woo, algolia,
url_extraction); a response object without headers never raises. Mutant G3-GRM2
(the algolia / url_extraction recording dropped) is killed by the algolia and
url_extraction cases.

G3-GR3 test_g3_gr3_no_projection_and_unbind_when_off (RULINGS_FIX1_S81_G3 F1-2):
(a) with ENABLE_KB_INGEST and ENABLE_FIELD_STATUS_METADATA OFF under the full
configuration, a recorder on kb_ingest.build_job / kb_ingest._now /
result_gate.assess_result records ZERO calls across the REST and stream success
exits, and a raising build_job produces no WARNING (spec 2.6 / R-G3-10: no
projection); (b) with ENABLE_LIVE_ROBOTS_REGISTRY + ENABLE_LIVE_ROBOTS_HEALTH_FLUSH
ON, two consecutive compares on one context (bind, records, the finally flush, a
repeated flush) produce exactly ONE pipeline + ONE exec each (flush_attempts
unbinds _ATTEMPTS_CTX). Mutants S17-M3 (the early return of _kb_ingest_tail
removed) and ADV-8 (the unbind dropped) are killed.

G3-GR4 test_g3_gr4_flush_uses_exec_or_execute (F1-3): live_robots._flush_sync
flushes through ``exec`` (the upstash-redis pipeline) or, when absent, ``execute``
(the redis-py pipeline of cache_service's redis:// path); neither shape raises.
Mutant G3-GRM4 (the fallback dropped) is killed by the ``execute`` shape.

Hermetic: every transport is faked at its seam; synthetic hosts only; pure ASCII, LF.
"""
from __future__ import annotations

import asyncio
import copy
import os
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace as NS

os.environ.setdefault("OPENAI_API_KEY", "sk" + "-test-dummy")

import pytest  # noqa: E402

NOW = datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc)
T0 = 1000.0
HOST = "store-a.example.com"
HOST_B = "store-b.example.com"
CLEARED_ENV = (
    "ENABLE_LIVE_ROBOTS_REGISTRY", "ENABLE_LIVE_ROBOTS_HEALTH_FLUSH", "ENABLE_KB_INGEST",
    "ENABLE_FIELD_STATUS_METADATA", "KB_INGEST_GAP_MAX", "ENABLE_OFFLOOP_DNS_RESOLVE",
    "ENABLE_PRICE_PARSE_OFFLOAD", "ENABLE_PRICE_PATH_REDIS_OFFLOOP", "ENABLE_URL_MODE_V2",
    "ENABLE_DATA_GUARDS_V2", "ENABLE_MERCHANT_REGISTRY_DB", "MERCHANT_REGISTRY_MEMO_SECONDS",
    "MERCHANT_REGISTRY_READ_TIMEOUT_SECONDS", "MERCHANT_REGISTRY_MAX_STALE_SECONDS",
    "LIVE_ROBOTS_HEALTH_TTL_DAYS",
)


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    import importlib

    import app.main  # noqa: F401  (FIRST: the dotenv-override hazard)
    from app.services import jsonld_widen

    for name in CLEARED_ENV:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(jsonld_widen, "ROBOTS_ENTRY_LOOKUP", jsonld_widen.ROBOTS_ENTRY_LOOKUP)
    importlib.reload(importlib.import_module("app.services.live_robots"))  # a fresh memo
    yield


def _iso(moment):
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def _view(host):
    rules = [["allow", "/"]]
    return {"host": host, "status": "live", "deny": False, "challenge": None,
            "robots": {"state": "allow", "status": 200,
                       "fetched_at": _iso(NOW - timedelta(hours=1)),
                       "next_reread": _iso(NOW + timedelta(hours=23)),
                       "crawl_delay": None, "origin": "https://" + host,
                       "source": "robots_txt", "rules": {"qarenbot": rules, "star": rules},
                       "probed": "/"}}


# ---------------------------------------------------------------------------
# G3-GR1 the offer re-observation match (GC-6)
# ---------------------------------------------------------------------------

class _Q:
    def __init__(self, client, table):
        self.client, self.table, self.op, self.payload, self.kwargs = client, table, None, None, {}
        self.filters = []

    def upsert(self, rows, **kwargs):
        self.op, self.payload, self.kwargs = "upsert", copy.deepcopy(rows), dict(kwargs)
        return self

    def update(self, payload, **kwargs):
        self.op, self.payload = "update", copy.deepcopy(payload)
        return self

    def select(self, *_a, **_k):
        self.op = self.op or "select"
        return self

    def eq(self, col, value):
        self.filters.append(("eq", col, value))
        return self

    def in_(self, col, values):
        self.filters.append(("in_", col, list(values)))
        return self

    def execute(self):
        return self.client.execute(self)


class _OfferClient:
    """Insert returns, for kb_offers, the sent rows with ``amount`` as PostgREST
    returns it (a JSON number), per ``mode``; every other table echoes its rows."""

    def __init__(self, mode):
        self.mode = mode
        self.ops = []

    def __call__(self, *_a, **_k):
        return self

    def table(self, name):
        return _Q(self, name)

    def execute(self, q):
        self.ops.append({"table": q.table, "op": q.op, "payload": q.payload,
                         "kwargs": q.kwargs, "filters": list(q.filters)})
        if q.op == "upsert":
            rows = q.payload if isinstance(q.payload, list) else [q.payload]
            if q.table != "kb_offers":
                return NS(data=[dict(r) for r in rows])
            if self.mode == "returned_numeric":
                return NS(data=[dict(r, amount=float(r["amount"])) for r in rows])
            if self.mode == "returned_other_amount":
                return NS(data=[dict(r, amount=float(r["amount"]) + 1.0) for r in rows])
            return NS(data=[])
        return NS(data=[])


def _fragrance(host, slug, amount):
    url = "https://" + host + "/products/" + slug
    return {
        "brand": "Acme", "name": "Nimbus " + slug.title() + " Eau de Parfum", "variant": None,
        "category": "fragrances",
        "price": {"amount": amount, "currency": "BHD", "url": url, "retailer": host,
                  "source_method": "page_scrape_jsonld", "estimated": False, "_cached": False,
                  "size": "100ml", "image_url": None, "in_stock": True},
        "image_url": None, "specs": {"concentration": "Eau de Parfum", "volume": "100ml"},
        "rating": None, "review_count": None, "rating_derived": False, "jsonld_rating": None,
    }


@pytest.mark.parametrize("mode,want_updates", [
    ("returned_numeric", 0), ("returned_other_amount", 1), ("not_returned", 1)])
def test_g3_gr1_offer_reobservation_amount_normalised(monkeypatch, mode, want_updates):
    from app.services import kb_ingest, live_robots

    products = [_fragrance(HOST, "noir", 42.5), _fragrance(HOST_B, "dusk", 37.0)]
    result = {"success": True, "category_used": "fragrances",
              "products": copy.deepcopy(products), "metadata": {}}
    client = _OfferClient(mode)
    monkeypatch.setenv("ENABLE_KB_INGEST", "true")
    monkeypatch.setattr(kb_ingest, "_admin_client", client)
    monkeypatch.setattr(live_robots, "records_snapshot", lambda: {HOST: _view(HOST)})
    monkeypatch.setattr(live_robots, "load_records_sync", lambda *_a, **_k: {HOST: _view(HOST)})
    snap = kb_ingest.build_job(result, copy.deepcopy(products),
                               product_categories=["fragrances", "fragrances"],
                               region="bahrain", vision=False, captured_at=NOW)
    assert snap["identity_confidence"] == "high", snap["identity_confidence"]
    kb_ingest.run_job(snap)
    sent = [o for o in client.ops if o["table"] == "kb_offers" and o["op"] == "upsert"]
    assert len(sent) == 1 and len(sent[0]["payload"]) == 1, sent
    assert sent[0]["payload"][0]["amount"] == "42.500", sent[0]["payload"]
    updates = [o for o in client.ops if o["table"] == "kb_offers" and o["op"] == "update"]
    assert len(updates) == want_updates, (mode, updates)


# ---------------------------------------------------------------------------
# G3-GR2 every hooked fetcher records ok / fail (GC-5)
# ---------------------------------------------------------------------------

class _Resp:
    def __init__(self, status, text="", json_data=None, headers=True):
        self.status_code = status
        self.text = text
        self._json = json_data
        if headers:
            self.headers = {}

    def json(self):
        return self._json


class _HResp:
    def __init__(self, status, text=""):
        self.status_code = status
        self.text = text
        self.headers = {}
        self.is_redirect = False
        self.next_request = None


def _arm(monkeypatch):
    from app.services import live_robots

    monkeypatch.setenv("ENABLE_LIVE_ROBOTS_REGISTRY", "true")
    monkeypatch.setattr(live_robots, "_monotonic", lambda: T0)
    monkeypatch.setattr(live_robots, "_now", lambda: NOW)
    live_robots.load_records_sync(_SeedClient([_view(HOST)]))
    return live_robots


class _SeedChain:
    def __init__(self, rows):
        self.rows = rows

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        return lambda *a, **k: self

    def execute(self):
        return NS(data=[dict(r) for r in self.rows])


class _SeedClient:
    def __init__(self, rows):
        self.rows = rows

    def table(self, _name):
        return _SeedChain(self.rows)


async def _valid(_url):
    return True


async def _no_slot(_domain):
    return None


def _shopify(monkeypatch, resp):
    from app.services import shopify_pdp_service
    from app.utils import url_validator

    def _get(_url, _timeout):
        if isinstance(resp, Exception):
            raise resp
        return resp

    monkeypatch.setattr(url_validator, "_validate_url_offloop_or_sync", _valid)
    monkeypatch.setattr(shopify_pdp_service, "_await_domain_slot", _no_slot)
    monkeypatch.setattr(shopify_pdp_service, "_curl_get", _get)
    return shopify_pdp_service._fetch_once("https://" + HOST + "/products/noir.js", HOST)


def _woo(monkeypatch, resp):
    from app.services import woocommerce_service

    monkeypatch.setattr(woocommerce_service, "_do_get", lambda *_a, **_k: resp)
    return woocommerce_service.fetch_woocommerce_store_api_price(
        HOST, "Acme Nimbus Noir Eau de Parfum 100ml", "BHD", resolved_category="fragrances")


def _algolia_explicit(monkeypatch, resp):
    import curl_cffi.requests as curl_requests

    from app.services import algolia_service

    monkeypatch.setitem(algolia_service.ALGOLIA_EXPLICIT_STORES, HOST, {
        "app_id": "testappid", "api_key": "test" + "-" + "k", "index": "test_index",
        "currency": "BHD", "genuine": True})
    monkeypatch.setattr(algolia_service, "record_failure", lambda *a, **k: None)
    monkeypatch.setattr(algolia_service, "record_success", lambda *a, **k: None)
    monkeypatch.setattr(curl_requests, "post", lambda *_a, **_k: resp)
    return algolia_service._fetch_explicit_store_price(
        HOST, "Acme Nimbus Noir Eau de Parfum 100ml", resolved_category="fragrances")


def _algolia_harvest(monkeypatch, resp):
    import curl_cffi.requests as curl_requests

    from app.services import algolia_service

    async def _offloop_none(*_a, **_k):
        return None

    monkeypatch.setattr(algolia_service, "run_redis_offloop", _offloop_none)
    monkeypatch.setattr(curl_requests, "get", lambda *_a, **_k: resp)
    return algolia_service._harvest_config(HOST)


def _url_base(monkeypatch, html):
    from app.services import url_extraction_service as ues

    async def _fetch(_url):
        return html

    monkeypatch.setattr(ues, "fetch_page", _fetch)
    monkeypatch.setattr(ues, "extract_generic_data",
                        lambda *_a, **_k: {"title": "Acme Nimbus Noir", "price": 42.5})
    return ues.extract_from_url("https://" + HOST + "/products/noir")


def _url_v2(monkeypatch, resp):
    from app.services import url_extraction_service as ues
    from app.utils import url_validator

    class _Client:
        def __init__(self, **_k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_exc):
            return False

        async def get(self, _url, headers=None, **_k):
            return resp

    monkeypatch.setattr(url_validator, "_validate_url_offloop_or_sync", _valid)
    monkeypatch.setattr(ues.httpx, "AsyncClient", _Client)
    return ues._fetch_page_v2("https://" + HOST + "/products/noir")


CASES = {
    # name: (label, driver, ok input, fail input)
    "shopify": ("shopify", _shopify, _Resp(200, "{}"), _Resp(404, headers=False)),
    "shopify_raise": ("shopify", _shopify, _Resp(200, "{}"), RuntimeError("transport down")),
    "woo": ("woo", _woo, _Resp(200, json_data=[{"id": 1}]), _Resp(503, headers=False)),
    "algolia_explicit": ("algolia", _algolia_explicit,
                         _Resp(200, json_data={"hits": [{"name": "other"}]}),
                         _Resp(404, headers=False)),
    "algolia_harvest": ("algolia", _algolia_harvest, _Resp(200, "<html></html>"),
                        _Resp(404, headers=False)),
    "url_extraction_base": ("url_extraction", _url_base, "<html><title>t</title></html>", None),
    "url_extraction_v2": ("url_extraction", _url_v2, _HResp(200, "<html/>"), _HResp(404)),
}


@pytest.mark.parametrize("name", sorted(CASES))
def test_g3_gr2_every_hook_records_outcomes(monkeypatch, name):
    label, driver, ok_input, fail_input = CASES[name]
    lr = _arm(monkeypatch)

    async def _go():
        lr.bind_attempts()
        await driver(monkeypatch, ok_input)
        await driver(monkeypatch, fail_input)
        return dict(lr._ATTEMPTS_CTX.get() or {})

    counts = asyncio.run(_go())
    assert counts.get((label, HOST, "ok")) == 1, (name, counts)
    assert counts.get((label, HOST, "fail")) == 1, (name, counts)
    assert not any(k[2] == "robots_skip" for k in counts), (name, counts)


# ---------------------------------------------------------------------------
# G3-GR3 no projection with both flags OFF; flush_attempts unbinds (F1-2)
# ---------------------------------------------------------------------------

def _s17():
    import importlib

    return importlib.import_module("tests.test_s81_s17_kb_ingest")


@pytest.mark.parametrize("kind", ["rest", "stream"])
def test_g3_gr3_no_projection_and_unbind_when_off(monkeypatch, caplog, kind):
    import logging

    from app.services import kb_ingest, result_gate

    s17 = _s17()
    for name in s17.CLEARED_ENV:
        monkeypatch.delenv(name, raising=False)
    s17._full_config(monkeypatch, "true")
    monkeypatch.setenv("ENABLE_KB_INGEST", "false")
    monkeypatch.setenv("ENABLE_FIELD_STATUS_METADATA", " OFF ")
    monkeypatch.setenv("ENABLE_LIVE_ROBOTS_HEALTH_FLUSH", "true")
    monkeypatch.setenv("LIVE_ROBOTS_HEALTH_TTL_DAYS", "8")

    # (a1) recorders that delegate: zero calls at the success exit.
    calls = []
    real_build, real_now, real_assess = (kb_ingest.build_job, kb_ingest._now,
                                         result_gate.assess_result)

    def _build(*a, **k):
        calls.append("build_job")
        return real_build(*a, **k)

    def _now():
        calls.append("_now")
        return real_now()

    def _assess(*a, **k):
        calls.append("assess_result")
        return real_assess(*a, **k)

    monkeypatch.setattr(kb_ingest, "build_job", _build)
    monkeypatch.setattr(kb_ingest, "_now", _now)
    monkeypatch.setattr(result_gate, "assess_result", _assess)
    state = {}
    payload = asyncio.run(s17._compare(monkeypatch, kind, state=state, settle=0.1))
    assert payload, kind
    assert calls == [], (kind, calls)
    assert "kb_ingest" not in state["labels"], state["labels"]

    # (a2) a raising build_job: no WARNING (it is never reached).
    def _raising(*_a, **_k):
        raise RuntimeError("flag OFF: build_job must never run")

    monkeypatch.setattr(kb_ingest, "build_job", _raising)
    caplog.clear()
    caplog.set_level(logging.WARNING)
    asyncio.run(s17._compare(monkeypatch, kind, state={}, settle=0.1))
    warned = [r.getMessage() for r in caplog.records
              if r.levelno >= logging.WARNING and "KB_INGEST" in r.getMessage()]
    assert warned == [], (kind, warned)
    assert calls == [], (kind, calls)

    # (b) main + health ON: ONE pipeline + ONE exec per compare (the unbind).
    from app.services import live_robots
    from app.utils import redis_offloop

    monkeypatch.setenv("ENABLE_LIVE_ROBOTS_REGISTRY", "true")
    monkeypatch.setattr(live_robots, "_now", lambda: NOW)
    log = []

    class _Pipe:
        def __init__(self, n):
            self.n = n

        def hincrby(self, key, field, n):
            log.append(("hincrby", self.n, key, field, n))

        def expire(self, key, ttl):
            log.append(("expire", self.n, key, ttl))

        def exec(self):
            log.append(("exec", self.n))

    class _Redis:
        def pipeline(self):
            n = len([e for e in log if e[0] == "pipeline"])
            log.append(("pipeline", n))
            return _Pipe(n)

    async def _pool(fn, *args, durable=False):
        return await asyncio.to_thread(fn, *args)

    monkeypatch.setattr(live_robots, "_redis_client", lambda: _Redis())
    monkeypatch.setattr(redis_offloop, "run_redis_offloop_pool", _pool)

    async def _two_compares():
        for host in (HOST, HOST_B):
            live_robots.bind_attempts()
            live_robots.record("curl", host, "ok")
            live_robots.record("curl", host, "ok")
            live_robots.flush_attempts()  # the compare's finally
            live_robots.flush_attempts()  # a repeated flush on the same context
            await asyncio.sleep(0.2)

    asyncio.run(_two_compares())
    pipes = [e for e in log if e[0] == "pipeline"]
    execs = [e for e in log if e[0] == "exec"]
    assert len(pipes) == 2 and len(execs) == 2, log
    incr = [e for e in log if e[0] == "hincrby"]
    key = "kbh:20261101:"
    assert [(e[1], e[2], e[3], e[4]) for e in incr] == [
        (0, key + HOST, "curl:ok", 2), (1, key + HOST_B, "curl:ok", 2)], incr


# ---------------------------------------------------------------------------
# G3-GR4 the flush works on both pipeline shapes (F1-3)
# ---------------------------------------------------------------------------

class _ExecPipe:
    """The upstash-redis pipeline shape: ``exec`` only."""

    def __init__(self, log):
        self.log = log

    def hincrby(self, key, field, n):
        self.log.append(("hincrby", key, field, n))

    def expire(self, key, ttl):
        self.log.append(("expire", key, ttl))

    def exec(self):
        self.log.append(("flush", "exec"))
        return []


class _ExecutePipe:
    """The redis-py pipeline shape: ``execute`` only (no ``exec``)."""

    def __init__(self, log):
        self.log = log

    def hincrby(self, key, field, n):
        self.log.append(("hincrby", key, field, n))

    def expire(self, key, ttl):
        self.log.append(("expire", key, ttl))

    def execute(self):
        self.log.append(("flush", "execute"))
        return []


@pytest.mark.parametrize("shape", ["exec", "execute"])
def test_g3_gr4_flush_uses_exec_or_execute(monkeypatch, shape):
    from app.services import live_robots

    log = []
    pipe_cls = _ExecPipe if shape == "exec" else _ExecutePipe

    class _Client:
        def pipeline(self):
            log.append(("pipeline",))
            return pipe_cls(log)

    monkeypatch.setattr(live_robots, "_redis_client", lambda: _Client())
    counts = {("curl", HOST, "ok"): 3, ("woo", HOST, "fail"): 1}
    raised = None
    try:
        live_robots._flush_sync(counts, "20261101", 8 * 86400)
    except Exception as exc:  # noqa: BLE001 - the row reports it as an assertion
        raised = type(exc).__name__
    assert raised is None, (shape, raised)
    assert log.count(("pipeline",)) == 1, log
    assert [e for e in log if e[0] == "flush"] == [("flush", shape)], log
    key = "kbh:20261101:" + HOST
    assert ("hincrby", key, "curl:ok", 3) in log and ("hincrby", key, "woo:fail", 1) in log, log
    assert [e for e in log if e[0] == "expire"] == [("expire", key, 8 * 86400)], log
