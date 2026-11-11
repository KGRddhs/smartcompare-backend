"""D14 LIVE-ROBOTS + attempt hooks RED rows (spec S81-G3, unit D14 section 5, as
amended by RULINGS_S81_G3 R-G3-1..R-G3-18; L3 widened per R-G3-5, P2 per R-G3-9,
L11 per R-G3-15).

RED rows L1..L11 fail at base on an AssertionError only: the new module
``app.services.live_robots`` is reached through ``_lr()`` (find_spec + an
assertion), never imported at module top. PIN rows P1..P3 are green at base:
they run with the FULL configuration (the sub-flag ON, the memo knobs set, a
DISALLOW row offered by a client recorder installed through a getattr-safe
patch that is a no-op at base, a Redis recorder, a pool recorder) and compare
each fetcher's transport call sequence with the golden recorded at base
(tests/fixtures/s81_d14_flag_off_golden.json; re-record with
``python -m tests.test_s81_d14_live_robots <out.json>`` at the base sha only).

Contract assumptions this file fixes (stated in the RED report): the memo clock
is ``live_robots._monotonic()`` (seconds), the verdict clock ``live_robots._now()``
(an aware datetime); ``_admin_client`` / ``_redis_client`` may be used either as
a callable returning the client or as the client itself (the fakes are both);
the per-compare aggregator is the dict bound on ``live_robots._ATTEMPTS_CTX``
keyed ``(source, host, outcome)`` -> int; the URL-mode fetcher label is
``url_extraction`` for both the base and the V2 path.

Hygiene: pure ASCII, LF; bounded runner only; the netguard is on (every transport
is faked); synthetic hosts only; no key-shaped literal.
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
from pathlib import Path
from types import SimpleNamespace as NS

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
            raise OSError("d14 recorder: network blocked")
        return _real_gai(host, *args, **kwargs)

    socket.getaddrinfo = _gai
    os.environ["OPENAI_API_KEY"] = "sk" + "-test-dummy"

os.environ.setdefault("OPENAI_API_KEY", "sk" + "-test-dummy")

import pytest  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "tests" / "fixtures" / "s81_d14_flag_off_golden.json"
LR = "app.services.live_robots"
FLAG = "ENABLE_LIVE_ROBOTS_REGISTRY"
HEALTH = "ENABLE_LIVE_ROBOTS_HEALTH_FLUSH"
KNOBS = {
    "MERCHANT_REGISTRY_MEMO_SECONDS": "600",
    "MERCHANT_REGISTRY_READ_TIMEOUT_SECONDS": "5",
    "MERCHANT_REGISTRY_MAX_STALE_SECONDS": "3600",
    "LIVE_ROBOTS_HEALTH_TTL_DAYS": "8",
}
# Every flag whose state could move a fetcher or the faked compare (cleared per test).
CLEARED_ENV = (
    FLAG, HEALTH, "ENABLE_PRICE_PARSE_OFFLOAD", "ENABLE_OFFLOOP_DNS_RESOLVE",
    "ENABLE_PRICE_PATH_REDIS_OFFLOOP", "ENABLE_MERCHANT_REGISTRY_DB", "ENABLE_JSONLD_RATING",
    "ENABLE_IMAGE_PIPELINE_V2", "ENABLE_DATA_GUARDS_V2", "ENABLE_URL_MODE_V2",
    "ENABLE_KB_INGEST", "ENABLE_FIELD_STATUS_METADATA",
    "ENABLE_PARSE_PRESPLIT", "ENABLE_PARSE_BUDGET", "PARSE_TIMEOUT_SECONDS",
    "ENABLE_UNIFIED_SEARCH_BOUND", "UNIFIED_SEARCH_TIMEOUT_SECONDS",
    "ENABLE_PHASE2_RESIDUAL_GUARD", "PHASE2_MIN_RESIDUAL_SECONDS", "DEBUG_STAGE_TIMINGS",
    "ENABLE_FULL_STREAM_DEADLINE", "ENABLE_RESULT_STATUS_METADATA", "ENABLE_LLM_LEDGER_V2",
    "ENABLE_LLM_SPEND_BREAKER", "ENABLE_ANTHROPIC_TEXT", "ENABLE_ANTHROPIC_VISION",
    "ENABLE_ANTHROPIC_VERDICT", "ENABLE_ANTHROPIC_CRITIC", "ENABLE_ANTHROPIC_MODERATION",
    "ENABLE_SONNET_ESCALATION", "ENABLE_OPENAI_PRE_V3", "ENABLE_FRAGRANCE_ONLY_GATE",
) + tuple(KNOBS)
OFF_SPELLINGS = [None, "false", " 0 ", "OFF"]

HOST_A = "store-a.example.com"
HOST_B = "store-b.example.com"
HOST_SUB = "shop." + HOST_A
URL_A = "https://" + HOST_A + "/p/nimbus-noir?ref=" + "abc"
JS_A = "https://" + HOST_A + "/products/nimbus-noir.js"
PRODUCT = "Acme Nimbus Noir Eau de Parfum 100ml"
NOW = datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc)
T0 = 1000.0
VOLATILE = frozenset({"elapsed_ms", "elapsed_seconds", "timestamp", "generated_at",
                      "created_at", "started_at", "cached_at", "fetched_at", "at",
                      "stage_timings_ms", "orchestrator_timings_ms", "request_id"})


# ---------------------------------------------------------------------------
# harness
# ---------------------------------------------------------------------------

def _present(name):
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def _lr():
    assert _present(LR), "app/services/live_robots.py does not exist (D14 not implemented)"
    return importlib.import_module(LR)


def _attr(mod, name):
    assert hasattr(mod, name), "%s.%s is missing (D14 not implemented)" % (mod.__name__, name)
    return getattr(mod, name)


def _patch_if_present(mp, attr, value):
    """The getattr-safe patch: a no-op at base (no module), a setattr at HEAD."""
    if _present(LR):
        mp.setattr(importlib.import_module(LR), attr, value, raising=False)


class _Patcher:
    """monkeypatch's API outside pytest (the base recorder)."""

    def __init__(self):
        self._undo = []

    def setattr(self, obj, name, value, raising=True):
        self._undo.append(("attr", obj, name, getattr(obj, name, _MISSING)))
        setattr(obj, name, value)

    def setitem(self, mapping, key, value):
        self._undo.append(("item", mapping, key, mapping.get(key, _MISSING)))
        mapping[key] = value

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
            elif kind == "item":
                if value is _MISSING:
                    obj.pop(name, None)
                else:
                    obj[name] = value
            else:
                if value is _MISSING:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value


_MISSING = object()


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    import app.main  # noqa: F401  (FIRST: the dotenv-override hazard)
    from app.services import jsonld_widen

    for name in CLEARED_ENV:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(jsonld_widen, "ROBOTS_ENTRY_LOOKUP", jsonld_widen.ROBOTS_ENTRY_LOOKUP)
    if _present(LR):
        importlib.reload(importlib.import_module(LR))  # a fresh memo per test
    yield


def _set_flag(mp, name, value):
    if value is None:
        mp.delenv(name, raising=False)
    else:
        mp.setenv(name, value)


def _iso(moment):
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def _record(origin, *, state="allow", qarenbot=None, star=None, fetched=None, reread=None,
            truncated=False):
    rec = {
        "state": state,
        "status": 200,
        "fetched_at": _iso(fetched or NOW - timedelta(hours=1)),
        "next_reread": _iso(reread or NOW + timedelta(hours=23)),
        "crawl_delay": None,
        "origin": origin,
        "source": "robots_txt",
        "rules": {"qarenbot": [["allow", "/"]] if qarenbot is None else qarenbot,
                  "star": [["allow", "/"]] if star is None else star},
        "probed": "/",
    }
    if truncated:
        rec["rules_truncated"] = True
    return rec


def _row(host, *, status="live", deny=False, robots=None, challenge=None, allow=True):
    if robots is None:
        robots = _record("https://" + host) if allow else _record(
            "https://" + host, qarenbot=[["disallow", "/"]], star=[["disallow", "/"]])
    return {"host": host, "status": status, "deny": deny, "robots": robots,
            "challenge": challenge}


class _Chain:
    def __init__(self, client, table):
        self._client = client
        self.calls = [["table", [table], {}]]

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)

        def _method(*args, **kwargs):
            self.calls.append([name, list(args), dict(kwargs)])
            return self
        return _method

    def execute(self):
        self._client.executions.append({"calls": self.calls, "thread": threading.get_ident()})
        if self._client.raise_exc is not None:
            raise self._client.raise_exc
        start = 0
        for name, args, _kw in self.calls:
            if name == "range" and args:
                start = args[0]
        data = [dict(r) for r in self._client.rows] if start == 0 else []
        return NS(data=data, count=None)


class _FakeClient:
    """A service-role client recorder: table / select / in_ / order / range /
    execute (+ the executing thread). Callable: returns itself."""

    def __init__(self, rows=(), raise_exc=None):
        self.rows = list(rows)
        self.raise_exc = raise_exc
        self.executions = []
        self.tables = []

    def __call__(self, *a, **k):
        return self

    def table(self, name):
        self.tables.append(name)
        return _Chain(self, name)


class _FlushBoom(Exception):
    pass


class _FakePipe:
    def __init__(self, redis):
        self._redis = redis

    def hincrby(self, key, field, increment=1):
        self._redis.calls.append(["hincrby", key, field, increment])
        return self

    def expire(self, key, seconds):
        self._redis.calls.append(["expire", key, seconds])
        return self

    def exec(self):
        self._redis.calls.append(["exec"])
        if self._redis.raise_exc is not None:
            raise self._redis.raise_exc
        return []


class _FakeRedis:
    def __init__(self, raise_exc=None):
        self.calls = []
        self.raise_exc = raise_exc

    def __call__(self, *a, **k):
        return self

    def pipeline(self, *a, **k):
        self.calls.append(["pipeline"])
        return _FakePipe(self)

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)

        def _any(*args, **kwargs):
            self.calls.append([name] + list(args))
            return None
        return _any


def _seed(lr, rows):
    """Seed the memo through the flag-free loader (R-G3-5)."""
    loader = _attr(lr, "load_records_sync")
    return loader(_FakeClient(rows))


def _clock(mp, lr, mono=T0):
    box = {"mono": mono}
    mp.setattr(lr, "_monotonic", lambda: box["mono"], raising=False)
    mp.setattr(lr, "_now", lambda: NOW, raising=False)
    return box


def _counts(lr):
    ctx = _attr(lr, "_ATTEMPTS_CTX")
    got = ctx.get()
    assert isinstance(got, dict), "no per-compare aggregator bound: %r" % (got,)
    return dict(got)


# ---------------------------------------------------------------------------
# the fake transports (one recorder list per run)
# ---------------------------------------------------------------------------

class _Resp:
    def __init__(self, status, text="", headers=None, json_data=None):
        self.status_code = status
        self.text = text
        self.headers = headers or {}
        self._json = json_data

    def json(self):
        return self._json


class _HResp:
    def __init__(self, status, text="", location=None):
        self.status_code = status
        self.text = text
        self.headers = {}
        self.is_redirect = location is not None
        self.next_request = NS(url=location) if location is not None else None

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("http status %d" % self.status_code)


def _norm_kw(kwargs):
    out = {}
    for key in sorted(kwargs):
        value = kwargs[key]
        if key == "headers" and isinstance(value, dict):
            value = _norm_headers(value)
        elif key == "data" and isinstance(value, str):
            value = value
        elif not isinstance(value, (str, int, float, bool, type(None), list, dict)):
            value = repr(type(value).__name__)
        out[key] = value
    return out


def _norm_headers(headers):
    return {str(k): ("<redacted>" if "key" in str(k).lower() else v)
            for k, v in sorted(headers.items())}


def _install_transport(mp, rec, responses, hresponses=None):
    """Every live transport the D14 hooks guard, faked. ``rec`` gets one entry per
    network call in call order; ``responses`` / ``hresponses`` are consumed FIFO."""
    import curl_cffi.requests as curl_requests

    from app.services import algolia_service, shopify_pdp_service, url_extraction_service
    from app.services import woocommerce_service
    from app.utils import url_validator

    lock = threading.Lock()

    def _next(queue, default):
        with lock:
            return queue.pop(0) if queue else default

    def _get(url, **kwargs):
        with lock:
            rec.append(["curl.get", url, _norm_kw(kwargs)])
        return _next(responses, _Resp(404))

    def _post(url, **kwargs):
        with lock:
            rec.append(["curl.post", url, _norm_kw(kwargs)])
        return _next(responses, _Resp(404))

    def _shopify_get(url, timeout):
        with lock:
            rec.append(["shopify._curl_get", url, timeout])
        return _next(responses, _Resp(404))

    def _woo_get(url, params, headers):
        with lock:
            rec.append(["woo._do_get", url, dict(params), _norm_headers(headers)])
        return _next(responses, _Resp(404))

    hqueue = hresponses if hresponses is not None else []

    class _FakeAsyncClient:
        def __init__(self, **kwargs):
            kw = dict(kwargs)
            if "transport" in kw:
                kw["transport"] = ("_TRANSPORT" if kw["transport"] is url_extraction_service._TRANSPORT
                                   else type(kw["transport"]).__name__)
            rec.append(["httpx.client", _norm_kw(kw)])

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def get(self, url, headers=None, **kwargs):
            rec.append(["httpx.get", url, _norm_headers(headers or {}), _norm_kw(kwargs)])
            return _next(hqueue, _HResp(404))

    async def _valid(url):
        return True

    async def _slot(domain):
        return None

    async def _offloop_none(fn, *args, **kwargs):
        return None

    mp.setattr(curl_requests, "get", _get)
    mp.setattr(curl_requests, "post", _post)
    mp.setattr(shopify_pdp_service, "_curl_get", _shopify_get)
    mp.setattr(shopify_pdp_service, "_await_domain_slot", _slot)
    mp.setattr(woocommerce_service, "_do_get", _woo_get)
    mp.setattr(url_extraction_service.httpx, "AsyncClient", _FakeAsyncClient)
    mp.setattr(url_validator, "_validate_url_offloop_or_sync", _valid)
    mp.setattr(algolia_service, "is_circuit_closed", lambda *a, **k: True)
    mp.setattr(algolia_service, "run_redis_offloop", _offloop_none)
    mp.setattr(algolia_service, "record_failure", lambda *a, **k: None)
    mp.setattr(algolia_service, "record_success", lambda *a, **k: None)


def _explicit_store():
    return {"app_id": "testappid", "api_key": "test" + "-" + "algolia" + "-" + "k",
            "index": "test_index", "currency": "BHD", "genuine": True}


async def _call_fetcher(name, mp):
    from app.services import algolia_service, price_service, shopify_pdp_service
    from app.services import url_extraction_service, woocommerce_service

    if name == "curl":
        return await price_service.curl_fetch_html(URL_A)
    if name in ("same_site", "same_site_hop"):
        return await price_service.curl_fetch_html_same_site(URL_A, HOST_A)
    if name == "shopify":
        return await shopify_pdp_service._fetch_once(JS_A, HOST_A)
    if name == "woo":
        return await woocommerce_service.fetch_woocommerce_store_api_price(
            HOST_A, PRODUCT, "BHD", resolved_category="fragrances")
    if name == "algolia_harvest":
        return await algolia_service.fetch_algolia_price(HOST_A, PRODUCT, "fragrances")
    if name == "algolia_explicit":
        mp.setitem(algolia_service.ALGOLIA_EXPLICIT_STORES, HOST_A, _explicit_store())
        return await algolia_service._fetch_explicit_store_price(
            HOST_A, PRODUCT, resolved_category="fragrances")
    if name == "url_base":
        return await url_extraction_service.extract_from_url(URL_A)
    if name in ("url_v2", "url_v2_hop"):
        return await url_extraction_service.extract_from_url(URL_A, url_mode_v2=True)
    raise AssertionError("unknown fetcher " + name)


def _responses(name):
    """(curl-family responses, httpx responses) of each golden scenario."""
    if name == "curl":
        return [_Resp(200, "<html>a</html>")], []
    if name == "same_site":
        return [_Resp(301, headers={"Location": "/p/nimbus-noir-2"}), _Resp(200, "<html>b</html>")], []
    if name == "same_site_hop":
        return [_Resp(301, headers={"Location": "https://" + HOST_SUB + "/p/x"}),
                _Resp(200, "<html>c</html>")], []
    if name == "shopify":
        return [_Resp(200, '{"id": 1}')], []
    if name == "woo":
        return [_Resp(200, json_data=[]), _Resp(200, json_data=[])], []
    if name in ("algolia_harvest", "algolia_explicit"):
        return [_Resp(404)], []
    if name in ("url_base", "url_v2"):
        return [], [_HResp(404)]
    if name == "url_v2_hop":
        return [], [_HResp(301, location="https://" + HOST_B + "/p/other"), _HResp(200, "<html/>")]
    raise AssertionError(name)


GOLDEN_FETCHERS = ("curl", "same_site", "shopify", "woo", "algolia_harvest",
                   "algolia_explicit", "url_base", "url_v2")
LABELS = {"curl": "curl", "same_site": "curl_same_site", "same_site_hop": "curl_same_site",
          "shopify": "shopify", "woo": "woo", "algolia_harvest": "algolia",
          "algolia_explicit": "algolia", "url_base": "url_extraction", "url_v2": "url_extraction",
          "url_v2_hop": "url_extraction"}


def _plain(value):
    return json.loads(json.dumps(value, default=repr, sort_keys=True))


def _run_fetcher(mp, name, *, before=None):
    """One fetcher on the faked transports; returns (calls, plain return value)."""
    rec = []
    responses, hresponses = _responses(name)
    _install_transport(mp, rec, responses, hresponses)

    async def _go():
        if before is not None:
            before()
        out = await _call_fetcher(name, mp)
        await asyncio.sleep(0.05)  # let any (mutant) scheduled refresh run
        return out

    out = asyncio.run(_go())
    return _plain(rec), _plain(out)


# ---------------------------------------------------------------------------
# the faked compare (the FY25 driver of tests/test_s75_fanout_identity.py, copied)
# ---------------------------------------------------------------------------

QUERY = "iPhone 15 vs Galaxy S24"
LLM_PARSED = {"products": [
    {"brand": "Apple", "name": "iPhone 15", "variant": None, "category": "electronics",
     "search_query": "Apple iPhone 15"},
    {"brand": "Samsung", "name": "Galaxy S24", "variant": None, "category": "electronics",
     "search_query": "Samsung Galaxy S24"}], "comparison_type": "value"}
USAGE = {"prompt_tokens": 100, "completion_tokens": 50}


def _install_compare(mp, svc, state):
    import app.services.structured_comparison_service as scs
    from app.services import content_safety_service as _cs
    from app.services import price_service
    from app.services import scoring_service as _ss

    async def _parse(query):
        return json.loads(json.dumps(LLM_PARSED)), dict(USAGE)

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

    async def _price(*a, **k):
        host = HOST_A if "iphone" in (repr(a) + repr(k)).lower() else HOST_B
        url = "https://" + host + "/p/item"
        scs._record_provider_attempt(provider="curl", url=url, retailer_domain=host, status=200,
                                     cost=0, outcome="ok", html_kb=1, detected_cf=False,
                                     elapsed_ms=1)
        if state["fetch"]:
            await price_service.curl_fetch_html(url)
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
        return _cs.SafetyResult(allowed=True)

    mp.setattr(_cs.ContentSafetyService, "moderate_output", _moderate)
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


async def _compare(mp, kind, *, fetch=True, settle=0.0, until=None):
    """One faked compare; returns (payload, provider attempts, transport calls)."""
    import app.services.structured_comparison_service as scs

    rec = []
    _install_transport(mp, rec, [_Resp(200, "<html>p</html>") for _ in range(4)])
    mp.setattr(scs, "STREAM_HARD_CAP_SECONDS", 30.0)
    state = {"fetch": fetch}
    svc = scs.StructuredComparisonService()
    _install_compare(mp, svc, state)
    if kind == "rest":
        payload = await asyncio.wait_for(
            svc.compare_from_text(QUERY, region="bahrain", nocache=True), 60)
    else:
        payload = []

        async def _drain():
            async for event in svc.compare_from_text_streaming(QUERY, region="bahrain",
                                                               nocache=True):
                payload.append(list(event))
        await asyncio.wait_for(_drain(), 60)
    deadline = time.monotonic() + settle
    while time.monotonic() < deadline:
        if until is not None and until():
            break
        await asyncio.sleep(0.02)
    attempts = sorted((_plain(a) for a in getattr(svc, "_provider_attempts", []) or []),
                      key=lambda a: json.dumps(a, sort_keys=True))
    return payload, attempts, sorted(_plain(rec), key=lambda r: json.dumps(r, sort_keys=True))


def _compare_digests(mp, kind):
    payload, attempts, calls = asyncio.run(_compare(mp, kind))
    return {"payload": _digest(payload), "provider_attempts": _digest(attempts),
            "transport": _digest(calls)}


def _pool_recorder(mp, calls):
    from app.utils import redis_offloop

    async def _pool(fn, *args, durable=False):
        calls.append(["pool", durable])
        return await asyncio.to_thread(fn, *args)

    mp.setattr(redis_offloop, "run_redis_offloop_pool", _pool)
    _patch_if_present(mp, "run_redis_offloop_pool", _pool)


def _full_config(mp, *, client_rows=None, redis=None, pool_calls=None):
    """The FULL D14 configuration (B1): knobs set, the health sub-flag ON, a client
    recorder offering DISALLOW rows, a Redis recorder, a pool recorder."""
    for name, value in KNOBS.items():
        mp.setenv(name, value)
    mp.setenv(HEALTH, "true")
    client = _FakeClient(client_rows if client_rows is not None else [
        _row(HOST_A, allow=False), _row(HOST_B, allow=False), _row(HOST_SUB, allow=False)])
    redis = redis if redis is not None else _FakeRedis()
    _patch_if_present(mp, "_admin_client", client)
    _patch_if_present(mp, "_redis_client", redis)
    _pool_recorder(mp, pool_calls if pool_calls is not None else [])
    return client, redis


def _golden():
    assert GOLDEN.exists(), "the D14 golden is missing: " + str(GOLDEN)
    return json.loads(GOLDEN.read_text(encoding="ascii"))


# ---------------------------------------------------------------------------
# L1 readers
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("reader,name", [("live_robots_enabled", FLAG),
                                         ("health_flush_enabled", HEALTH)])
def test_L1_readers(monkeypatch, reader, name):
    lr = _lr()
    fn = _attr(lr, reader)
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
# L2 verdict table + L2b parity with the G2 gate
# ---------------------------------------------------------------------------

def _deny_url():
    from app.services import deny_hosts
    return "https://" + deny_hosts.DENY_HOSTS[0] + "/p/x"


def _cases():
    a = "https://" + HOST_A + "/p/item?x=1"
    origin = "https://" + HOST_A
    allow = _row(HOST_A)
    return [
        ("allow", a, allow, None),
        ("denied_url", _deny_url(), allow, "denied"),
        ("denied_row", a, dict(allow, deny=True), "denied"),
        ("no_row", a, None, "no_row"),
        ("not_live_blocked", a, dict(allow, status="blocked"), "not_live"),
        ("not_live_candidate", a, dict(allow, status="candidate"), "not_live"),
        ("no_record_empty", a, dict(allow, robots={}), "no_record"),
        ("no_record_no_origin", a, dict(allow, robots={k: v for k, v in _record(origin).items()
                                                       if k != "origin"}), "no_record"),
        ("origin_www", "https://www." + HOST_A + "/p/item", allow, "origin"),
        ("origin_http", "http://" + HOST_A + "/p/item", allow, "origin"),
        ("robots_disallow_state", a, dict(allow, robots=_record(origin, state="disallow")), "robots"),
        ("robots_unreadable", a, dict(allow, robots=_record(origin, state="unreadable")), "robots"),
        ("robots_star_disallows", a, dict(allow, robots=_record(
            origin, qarenbot=[["allow", "/"]], star=[["disallow", "/p/"]])), "robots"),
        ("robots_qarenbot_disallows", a, dict(allow, robots=_record(
            origin, qarenbot=[["disallow", "/p/"]], star=[["allow", "/"]])), "robots"),
        ("robots_expired", a, dict(allow, robots=_record(
            origin, fetched=NOW - timedelta(days=4), reread=NOW - timedelta(days=2))), "robots"),
        ("robots_truncated", a, dict(allow, robots=_record(origin, truncated=True)), "robots"),
        ("robots_challenge_parked", a, dict(allow, challenge={
            "vendor": "x", "parked_until": _iso(NOW + timedelta(days=1))}), "robots"),
        ("bad_url_non_str", None, allow, "bad_url"),
        ("bad_url_ftp", "ftp://" + HOST_A + "/p", allow, "bad_url"),
        ("bad_url_no_host", "https:///p/item", allow, "bad_url"),
    ]


CASES = _cases()


@pytest.mark.parametrize("case", CASES, ids=[c[0] for c in CASES])
def test_L2_verdict_table(case):
    lr = _lr()
    _name, url, row, want = case
    assert tuple(_attr(lr, "VERDICT_REASONS")) == (
        "bad_url", "denied", "no_row", "not_live", "no_record", "origin", "robots")
    got = _attr(lr, "url_verdict")(url, copy.deepcopy(row), NOW)
    assert got == want, (case[0], got)


@pytest.mark.parametrize("case", CASES, ids=[c[0] for c in CASES])
def test_L2b_parity_with_g2_gate(case):
    lr = _lr()
    from scripts import kb_seed_common

    _name, url, row, _want = case
    got = _attr(lr, "url_verdict")(url, copy.deepcopy(row), NOW)
    assert got == kb_seed_common.url_gate(copy.deepcopy(row), url, NOW, require_tos=False), case[0]


# ---------------------------------------------------------------------------
# L3 the memo (widened per R-G3-5)
# ---------------------------------------------------------------------------

def test_L3_refresh_reads_once_off_loop(monkeypatch):
    lr = _lr()
    from app.services import merchant_registry

    monkeypatch.setenv(FLAG, "true")
    for name, value in KNOBS.items():
        monkeypatch.setenv(name, value)
    _clock(monkeypatch, lr)
    client = _FakeClient([_row(HOST_A)])
    monkeypatch.setattr(lr, "_admin_client", client, raising=False)
    loop_thread = threading.get_ident()

    async def _go():
        first = [lr.gate(URL_A, "curl") for _ in range(3)]  # cold: skip, ONE refresh
        deadline = time.monotonic() + 3.0
        while not client.executions and time.monotonic() < deadline:
            await asyncio.sleep(0.01)
        await asyncio.sleep(0.1)
        second = lr.gate(URL_A, "curl")
        return first, second

    first, second = asyncio.run(_go())
    assert first == [False, False, False], first
    assert second is True, "a loaded ALLOW record must allow"
    assert len(client.executions) == 1, "exactly ONE select per memo window: %r" % (
        len(client.executions),)
    calls = client.executions[0]["calls"]
    assert calls[0] == ["table", [merchant_registry.KB_MERCHANTS_TABLE], {}], calls
    selects = [c for c in calls if c[0] == "select"]
    assert len(selects) == 1, calls
    cols = {c.strip() for c in str(selects[0][1][0]).split(",")}
    assert cols == {"host", "status", "deny", "robots", "challenge"}, cols
    ins = [c for c in calls if c[0] == "in_"]
    assert len(ins) == 1 and ins[0][1][0] == "status" and list(ins[0][1][1]) == ["live", "blocked"], ins
    ranges = [c for c in calls if c[0] == "range"]
    assert ranges and ranges[0][1][:2] == [0, 499], ranges
    assert client.executions[0]["thread"] != loop_thread, "the select must run off the loop thread"


def test_L3_failing_refresh_keeps_last_good_until_max_stale(monkeypatch):
    lr = _lr()
    monkeypatch.setenv(FLAG, "true")
    for name, value in KNOBS.items():
        monkeypatch.setenv(name, value)
    box = _clock(monkeypatch, lr)
    _seed(lr, [_row(HOST_A)])
    failing = _FakeClient([], raise_exc=RuntimeError("db down"))
    monkeypatch.setattr(lr, "_admin_client", failing, raising=False)

    async def _go():
        box["mono"] = T0 + 601  # refresh due; it fails
        a = lr.gate(URL_A, "curl")
        deadline = time.monotonic() + 3.0
        while not failing.executions and time.monotonic() < deadline:
            await asyncio.sleep(0.01)
        await asyncio.sleep(0.1)
        box["mono"] = T0 + 1800
        b = lr.gate(URL_A, "curl")
        box["mono"] = T0 + 3601 + 600
        c = lr.gate(URL_A, "curl")
        return a, b, c

    a, b, c = asyncio.run(_go())
    assert failing.executions, "a due refresh must be attempted"
    assert (a, b) == (True, True), "a failing refresh keeps the last good load: %r" % ((a, b),)
    assert c is False, "past MAX_STALE every gated fetch is skipped"


def test_L3_records_snapshot_is_age_aware(monkeypatch):
    lr = _lr()
    for name, value in KNOBS.items():
        monkeypatch.setenv(name, value)
    box = _clock(monkeypatch, lr)
    snapshot = _attr(lr, "records_snapshot")
    assert snapshot() is None, "no load yet -> None"
    loaded = _seed(lr, [_row(HOST_A), _row(HOST_B, status="blocked")])
    assert isinstance(loaded, dict) and set(loaded) >= {HOST_A, HOST_B}, loaded
    assert set(loaded[HOST_A]) >= {"host", "status", "deny", "robots", "challenge"}, loaded[HOST_A]
    box["mono"] = T0 + 10
    snap = snapshot()
    assert isinstance(snap, dict) and HOST_A in snap, snap
    box["mono"] = T0 + 601
    assert snapshot() is None, "past MERCHANT_REGISTRY_MEMO_SECONDS the snapshot is None (R-G3-5)"


def test_L3_no_running_loop_decides_from_memo_and_never_raises(monkeypatch):
    lr = _lr()
    monkeypatch.setenv(FLAG, "true")
    for name, value in KNOBS.items():
        monkeypatch.setenv(name, value)
    box = _clock(monkeypatch, lr)
    client = _FakeClient([_row(HOST_A)])
    monkeypatch.setattr(lr, "_admin_client", client, raising=False)
    assert lr.gate(URL_A, "curl") is False, "cold memo, no loop: skip, no raise"
    _seed(lr, [_row(HOST_A)])
    box["mono"] = T0 + 700  # refresh due, but no running loop
    assert lr.gate(URL_A, "curl") is True
    row = lr.row_for_host(HOST_A)
    assert isinstance(row, dict) and row.get("status") == "live", row
    assert client.executions == [], "no loop: no refresh is scheduled or run"


# ---------------------------------------------------------------------------
# L4 skip per fetcher; L5 allow passes byte-identical args; L6 no robots fetch
# ---------------------------------------------------------------------------

SKIP_CASES = {
    "curl": (HOST_A, [_row(HOST_A, allow=False)], None),
    "same_site": (HOST_A, [_row(HOST_A, allow=False)], None),
    "same_site_hop": (HOST_SUB, [_row(HOST_A), _row(HOST_SUB, allow=False)], None),
    "shopify": (HOST_A, [_row(HOST_A, allow=False)], [None, None]),
    "woo": (HOST_A, [_row(HOST_A, allow=False)], None),
    "algolia_harvest": (HOST_A, [_row(HOST_A, allow=False)], None),
    "algolia_explicit": (HOST_A, [_row(HOST_A, allow=False)], None),
    "url_base": (HOST_A, [_row(HOST_A, allow=False)], "base"),
    "url_v2": (HOST_A, [_row(HOST_A, allow=False)], "v2"),
    "url_v2_hop": (HOST_B, [_row(HOST_A), _row(HOST_B, allow=False)], "v2"),
}


@pytest.mark.parametrize("name", sorted(SKIP_CASES))
def test_L4_skip_per_fetcher(monkeypatch, caplog, name):
    lr = _lr()
    monkeypatch.setenv(FLAG, "true")
    for knob, value in KNOBS.items():
        monkeypatch.setenv(knob, value)
    _clock(monkeypatch, lr)
    skip_host, rows, want = SKIP_CASES[name]
    _seed(lr, rows)
    box = {}

    def _bind():
        _attr(lr, "bind_attempts")()
        box["ctx"] = _attr(lr, "_ATTEMPTS_CTX")

    caplog.set_level(logging.INFO)
    rec = []
    responses, hresponses = _responses(name)
    _install_transport(monkeypatch, rec, responses, hresponses)

    async def _go():
        _bind()
        out = await _call_fetcher(name, monkeypatch)
        return out, dict(box["ctx"].get() or {})

    out, counts = asyncio.run(_go())
    skipped_url_prefix = "https://" + skip_host + "/"
    if name.endswith("_hop"):
        assert len(rec) >= 1, "the allowed initial URL is fetched"
        assert not any(skipped_url_prefix in json.dumps(c) for c in rec[1:]), rec
    else:
        assert rec == [], "a skipped fetch never reaches the transport: %r" % (rec,)
    if want is None:
        assert out is None, out
    elif want == "base":
        assert out == {"success": False, "error": "Failed to fetch URL", "url": URL_A}, out
    elif want == "v2":
        assert out.get("success") is False and out.get("code") == "STORE_UNREADABLE", out
        assert out.get("reason") == "robots_skip", out
    else:
        assert list(out) == want, out
    skips = {k: v for k, v in counts.items() if k[2] == "robots_skip"}
    assert skips == {(LABELS[name], skip_host, "robots_skip"): 1}, counts
    assert any("[LIVE_ROBOTS] skip" in r.getMessage() for r in caplog.records), \
        "one [LIVE_ROBOTS] skip INFO line"


@pytest.mark.parametrize("name", GOLDEN_FETCHERS)
def test_L5_allow_passes_byte_identical_args(monkeypatch, name):
    lr = _lr()
    monkeypatch.setenv(FLAG, "true")
    for knob, value in KNOBS.items():
        monkeypatch.setenv(knob, value)
    _clock(monkeypatch, lr)
    _seed(lr, [_row(HOST_A), _row(HOST_B), _row(HOST_SUB)])
    calls, out = _run_fetcher(monkeypatch, name)
    want = _golden()["fetchers"][name]
    assert calls == want["calls"], "flag ON + ALLOW must pass the base transport call: %s" % name
    assert out == want["returned"], name
    assert not any(str(c[1]).endswith("/robots.txt") for c in calls if len(c) > 1), calls


@pytest.mark.parametrize("status,headers,outcome", [
    (200, {}, "ok"), (404, {}, "fail"), (403, {"cf-mitigated": "challenge"}, "challenge")])
def test_L5_outcomes_counted(monkeypatch, status, headers, outcome):
    lr = _lr()
    monkeypatch.setenv(FLAG, "true")
    for knob, value in KNOBS.items():
        monkeypatch.setenv(knob, value)
    _clock(monkeypatch, lr)
    _seed(lr, [_row(HOST_A)])
    rec = []
    _install_transport(monkeypatch, rec, [_Resp(status, "<html/>", headers=headers)])

    async def _go():
        _attr(lr, "bind_attempts")()
        from app.services import price_service
        await price_service.curl_fetch_html(URL_A)
        return _counts(lr)

    counts = asyncio.run(_go())
    assert len(rec) == 1, rec
    assert counts == {("curl", HOST_A, outcome): 1}, counts


def test_L6_gate_never_fetches(monkeypatch):
    lr = _lr()
    monkeypatch.setenv(FLAG, "true")
    for knob, value in KNOBS.items():
        monkeypatch.setenv(knob, value)
    _clock(monkeypatch, lr)
    _seed(lr, [_row(HOST_A)])
    rec = []
    _install_transport(monkeypatch, rec, [])

    async def _go():
        return [lr.gate(URL_A, "curl"), lr.gate("https://" + HOST_B + "/p", "curl")]

    assert asyncio.run(_go()) == [True, False]
    assert rec == [], "gate never fetches (no robots.txt read on the live path): %r" % (rec,)


# ---------------------------------------------------------------------------
# L7 the D08 seam
# ---------------------------------------------------------------------------

def test_L7_seam_answers_the_record_under_the_flag(monkeypatch):
    lr = _lr()
    from app.services import jsonld_widen

    for knob, value in KNOBS.items():
        monkeypatch.setenv(knob, value)
    _clock(monkeypatch, lr)
    _seed(lr, [_row(HOST_A)])
    lookup_calls = []
    real_row = _attr(lr, "row_for_host")

    def _row_rec(host):
        lookup_calls.append(host)
        return real_row(host)

    monkeypatch.setattr(lr, "row_for_host", _row_rec)
    assert jsonld_widen.ROBOTS_ENTRY_LOOKUP is _attr(lr, "robots_entry_lookup"), \
        "importing live_robots wires the D08 seam (R-G1-1)"
    assert jsonld_widen.ROBOTS_ENTRY_LOOKUP(HOST_A) is None, "flag OFF: None for every host"
    assert lookup_calls == [], "flag OFF: no memo read"
    monkeypatch.setenv(FLAG, "true")
    entry = jsonld_widen.ROBOTS_ENTRY_LOOKUP(HOST_A)
    assert isinstance(entry, dict) and set(entry) == {"status", "deny", "robots", "challenge"}, entry
    assert entry["status"] == "live"
    assert jsonld_widen.ROBOTS_ENTRY_LOOKUP("unknown-host.example.com") is None
    price = {"url": URL_A, "_jsonld_facts": {"rating": {"value": 4.5, "count": 12}}}
    got = jsonld_widen.channel1_rating(price, NOW)
    assert isinstance(got, dict) and got.get("value") == 4.5 and got.get("source") == HOST_A, got


# ---------------------------------------------------------------------------
# L8 / L9 the flush (once per compare, through the S77 pool)
# ---------------------------------------------------------------------------

def _flush_setup(monkeypatch, lr, *, health="true", raise_exc=None):
    monkeypatch.setenv(FLAG, "true")
    _set_flag(monkeypatch, HEALTH, health)
    for knob, value in KNOBS.items():
        monkeypatch.setenv(knob, value)
    _clock(monkeypatch, lr)
    _seed(lr, [_row(HOST_A), _row(HOST_B)])
    redis = _FakeRedis(raise_exc=raise_exc)
    monkeypatch.setattr(lr, "_redis_client", redis, raising=False)
    pool = []
    _pool_recorder(monkeypatch, pool)
    return redis, pool


@pytest.mark.parametrize("kind", ["rest", "stream"])
def test_L8_flush_once_per_compare(monkeypatch, kind):
    lr = _lr()
    redis, pool = _flush_setup(monkeypatch, lr)

    def _done():
        return any(c[0] == "exec" for c in redis.calls)

    asyncio.run(_compare(monkeypatch, kind, settle=3.0, until=_done))
    time.sleep(0.2)
    day = NOW.strftime("%Y%m%d")
    key_a, key_b = "kbh:" + day + ":" + HOST_A, "kbh:" + day + ":" + HOST_B
    assert [c for c in redis.calls if c[0] == "pipeline"] == [["pipeline"]], redis.calls
    assert [c for c in redis.calls if c[0] == "exec"] == [["exec"]], redis.calls
    hincr = sorted(tuple(c[1:]) for c in redis.calls if c[0] == "hincrby")
    assert hincr == sorted([(key_a, "curl:ok", 1), (key_b, "curl:ok", 1)]), hincr
    expire = sorted(tuple(c[1:]) for c in redis.calls if c[0] == "expire")
    assert expire == sorted([(key_a, 691200), (key_b, 691200)]), expire
    assert len(pool) == 1, "the ONE job goes through run_redis_offloop_pool: %r" % (pool,)


@pytest.mark.parametrize("variant", ["nothing_attempted", "health_off"])
def test_L8_no_pipeline_without_attempts_or_health(monkeypatch, variant):
    lr = _lr()
    redis, pool = _flush_setup(monkeypatch, lr, health="true" if variant != "health_off" else None)
    payload = asyncio.run(_compare(monkeypatch, "rest", fetch=variant != "nothing_attempted",
                                   settle=0.4))[0]
    assert payload.get("success") is True, payload
    assert redis.calls == [] and pool == [], (redis.calls, pool)
    # the positive control of the same setup: one compare with attempts and the health
    # flag ON flushes (so this row is not vacuous)
    monkeypatch.setenv(HEALTH, "true")
    asyncio.run(_compare(monkeypatch, "rest", settle=3.0,
                         until=lambda: any(c[0] == "exec" for c in redis.calls)))
    assert [c for c in redis.calls if c[0] == "exec"] == [["exec"]], redis.calls


@pytest.mark.parametrize("kind", ["rest", "stream"])
def test_L9_flush_failure_is_one_warning(monkeypatch, caplog, kind):
    lr = _lr()
    redis_ok, _pool = _flush_setup(monkeypatch, lr)
    good = asyncio.run(_compare(monkeypatch, kind, settle=3.0,
                                until=lambda: any(c[0] == "exec" for c in redis_ok.calls)))[0]
    assert any(c[0] == "exec" for c in redis_ok.calls), "control: the flush ran"
    boom = _FakeRedis(raise_exc=_FlushBoom("pipeline down"))
    monkeypatch.setattr(lr, "_redis_client", boom, raising=False)
    caplog.clear()
    caplog.set_level(logging.WARNING)

    def _warned():
        return any("_FlushBoom" in r.getMessage() for r in caplog.records)

    bad = asyncio.run(_compare(monkeypatch, kind, settle=3.0, until=_warned))[0]
    time.sleep(0.2)
    assert _digest(bad) == _digest(good), "a failing flush never changes the response"
    warns = [r for r in caplog.records
             if r.levelno == logging.WARNING and "_FlushBoom" in r.getMessage()]
    assert len(warns) == 1, [r.getMessage() for r in warns]


# ---------------------------------------------------------------------------
# L10 fail-closed; L11 log hygiene
# ---------------------------------------------------------------------------

def test_L10_gate_error_is_a_skip(monkeypatch):
    lr = _lr()
    monkeypatch.setenv(FLAG, "true")
    for knob, value in KNOBS.items():
        monkeypatch.setenv(knob, value)
    _clock(monkeypatch, lr)
    _seed(lr, [_row(HOST_A)])

    def _raise(*_a, **_k):
        raise RuntimeError("verdict exploded")

    monkeypatch.setattr(lr, "url_verdict", _raise)
    rec = []
    _install_transport(monkeypatch, rec, [_Resp(200, "<html/>")])

    async def _go():
        from app.services import price_service
        return lr.gate(URL_A, "curl"), await price_service.curl_fetch_html(URL_A)

    gated, fetched = asyncio.run(_go())
    assert gated is False and fetched is None, (gated, fetched)
    assert rec == [], rec


def test_L11_log_lines_carry_hosts_and_constants_only(monkeypatch, caplog):
    lr = _lr()
    monkeypatch.setenv(FLAG, "true")
    for knob, value in KNOBS.items():
        monkeypatch.setenv(knob, value)
    _clock(monkeypatch, lr)
    _seed(lr, [_row(HOST_A, allow=False)])
    caplog.set_level(logging.DEBUG)
    rec = []
    _install_transport(monkeypatch, rec, [])
    urls = [URL_A, "https://" + HOST_A + "/deep/path/name?q=" + "secretish" + "&x=1",
            "https://" + HOST_B + "/other?id=7"]

    async def _go():
        _attr(lr, "bind_attempts")()
        from app.services import price_service
        for url in urls:
            await price_service.curl_fetch_html(url)

    asyncio.run(_go())
    lines = [r.getMessage() for r in caplog.records if "[LIVE_ROBOTS]" in r.getMessage()]
    assert len(lines) >= 3, lines
    for line in lines:
        assert "://" not in line and "?" not in line and "=" not in line.split("reason=")[0].replace(
            "source=", "").replace("host=", ""), line
        for token in ("/p/", "/deep/", "/other", "ref", "secretish", "id=7"):
            assert token not in line, line
        hosts = re.findall(r"host=(\S+)", line)
        assert hosts and all("/" not in h for h in hosts), line


# ---------------------------------------------------------------------------
# P1..P3 flag-OFF identity (green at base)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("spelling", OFF_SPELLINGS, ids=["unset", "false", "pad0", "OFF"])
@pytest.mark.parametrize("name", GOLDEN_FETCHERS)
def test_P1_flag_off_fetcher_identity(monkeypatch, name, spelling):
    _set_flag(monkeypatch, FLAG, spelling)
    pool = []
    client, redis = _full_config(monkeypatch, pool_calls=pool)
    calls, out = _run_fetcher(monkeypatch, name)
    want = _golden()["fetchers"][name]
    assert calls == want["calls"], "flag OFF moved the %s transport calls" % name
    assert out == want["returned"], name
    assert client.executions == [] and client.tables == [], "flag OFF: no memo read"
    assert redis.calls == [] and pool == [], "flag OFF: no Redis call"


@pytest.mark.parametrize("kind", ["rest", "stream"])
def test_P2_flag_off_compare_identity(monkeypatch, kind):
    pool = []
    client, redis = _full_config(monkeypatch, pool_calls=pool)
    got = _compare_digests(monkeypatch, kind)
    want = _golden()["compare"][kind]
    assert got == want, "flag OFF moved the faked %s compare (FY25 digests / attempts): %r" % (
        kind, sorted(k for k in want if got.get(k) != want.get(k)))
    assert client.executions == [] and redis.calls == [] and pool == []


def test_P3_seam_off_answers_none():
    import app.main  # noqa: F401
    from app.services import jsonld_widen

    if _present(LR):
        importlib.import_module(LR)
    assert jsonld_widen.ROBOTS_ENTRY_LOOKUP("any.example.com") is None
    assert jsonld_widen.ROBOTS_ENTRY_LOOKUP(HOST_A) is None


# ---------------------------------------------------------------------------
# the base recorder
# ---------------------------------------------------------------------------

def _record_golden():  # pragma: no cover - run at the base sha only
    out = {"meta": {"unit": "D14 LIVE-ROBOTS", "recorded_at_base":
                    "744616e37d031923e522e30740b687de76482ee9",
                    "recorded_with": "ENABLE_LIVE_ROBOTS_REGISTRY unset; the FULL configuration "
                    "(the health sub-flag ON, the memo knobs set, the client / Redis / pool "
                    "recorders); every transport faked"},
           "fetchers": {}, "compare": {}}
    for name in GOLDEN_FETCHERS:
        p = _Patcher()
        try:
            for env in CLEARED_ENV:
                p.delenv(env)
            _full_config(p)
            calls, returned = _run_fetcher(p, name)
            out["fetchers"][name] = {"calls": calls, "returned": returned}
        finally:
            p.undo()
    for kind in ("rest", "stream"):
        p = _Patcher()
        try:
            for env in CLEARED_ENV:
                p.delenv(env)
            _full_config(p)
            out["compare"][kind] = _compare_digests(p, kind)
        finally:
            p.undo()
    return out


if __name__ == "__main__":  # pragma: no cover
    import app.main  # noqa: F401,E402

    data = _record_golden()
    with open(sys.argv[1], "w", encoding="ascii", newline="\n") as handle:
        json.dump(data, handle, indent=1, sort_keys=True, ensure_ascii=True)
        handle.write("\n")
    print("wrote", sys.argv[1], len(data["fetchers"]), len(data["compare"]))
