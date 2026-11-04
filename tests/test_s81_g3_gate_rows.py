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
