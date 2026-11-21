"""INC-SH1 SHOPIFY-NAMED-LIVE-READ: the frozen RED rows (P1-P5 pins, R1-R16).

With ``ENABLE_SHOPIFY_NAMED_LIVE_READ`` ON (default OFF, read per call) the
Shopify catalog read, the currency probe and the product-feed fetch name
themselves with the agent of the nightly reader, let the library follow no
redirect, ask the persisted robots record before every request (no record, no
read) and stop reading a host for the rest of the compare after a 429, 403, 503
or a challenge page, with no retry.

RED rows fail at base on an AssertionError only: every new symbol is reached
through ``_need`` (getattr plus an assertion), never imported at module top.
PIN rows P1-P5 are green at base and run with the full configuration (the
switch unset or in an OFF spelling, the live-robots, UCP and feed flags ON, a
disallow record in the memo) with call-order recorders compared with base
literals.

Every transport is faked: ``curl_cffi.requests.get`` (a kwargs recorder that
follows a redirect only when the caller asks the library to), the cache seams,
the per-domain slot, the SSRF validator and the memo seams of live_robots; the
robots emitter is patched to raise. Synthetic ``*.test`` hosts only; pure ASCII.
"""
from __future__ import annotations

import ast
import asyncio
import contextvars
import copy
import json
import logging
import socket
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urljoin

import pytest

SWITCH = "ENABLE_SHOPIFY_NAMED_LIVE_READ"
D14 = "ENABLE_LIVE_ROBOTS_REGISTRY"
UCP = "ENABLE_UCP_JSON_PRICE"
PDP = "ENABLE_SHOPIFY_PDP_JSON"
ANCHOR = "ENABLE_WALL_SIGNATURE_ANCHOR"
SCOPE_VAR = "shopify_named_read_ended"
KNOBS = {
    "MERCHANT_REGISTRY_MEMO_SECONDS": "600",
    "MERCHANT_REGISTRY_READ_TIMEOUT_SECONDS": "5",
    "MERCHANT_REGISTRY_MAX_STALE_SECONDS": "3600",
}
CLEARED_ENV = (
    SWITCH, D14, UCP, PDP, ANCHOR, "ENABLE_LIVE_ROBOTS_HEALTH_FLUSH",
    "ENABLE_PRICE_PATH_REDIS_OFFLOOP", "ENABLE_OFFLOOP_DNS_RESOLVE",
    "ENABLE_NOT_A_PDP_FILTER", "ENABLE_MERCHANT_REGISTRY_DB",
    "ENABLE_PRICE_PARSE_OFFLOAD", "ENABLE_PAGE_SCRAPE",
) + tuple(KNOBS)
OFF_SPELLINGS = [None, "false", "  FALSE ", "0", "off", "no", "garbage", ""]
OFF_IDS = ["unset", "false", "padded", "zero", "off", "no", "garbage", "empty"]
ON_SPELLINGS = ["true", "1", "yes", "on", " TRUE ", chr(9) + "On" + chr(10), "Yes", "  1  ", "ON"]
D14_STATES = [None, "true"]
D14_IDS = ["d14_off", "d14_on"]

PS_LOG = "app.services.price_service"
SPS_LOG = "app.services.shopify_pdp_service"
LR_LOG = "app.services.live_robots"
LOGGERS = (PS_LOG, SPS_LOG, LR_LOG)

HOST_A = "shop-a.test"
HOST_B = "shop-b.test"
HOST_C = "shop-c.test"
CAT_A = "https://" + HOST_A + "/products.json?limit=250"
META_A = "https://" + HOST_A + "/meta.json"
CAT_B = "https://" + HOST_B + "/products.json?limit=250"
META_B = "https://" + HOST_B + "/meta.json"
CAT_C = "https://" + HOST_C + "/products.json?limit=250"
FEED_A = "https://" + HOST_A + "/products/synthetic-oud.json"
FEED_A_WWW = "https://www." + HOST_A + "/products/synthetic-oud.json"
OTHER_A = "https://" + HOST_A + "/products/synthetic-amber.json"
BLOCKED_A = "https://" + HOST_A + "/products/blocked.json"
FEED_C_WWW = "https://www." + HOST_C + "/products/synthetic-oud.json"
PDP_A = "https://" + HOST_A + "/products/synthetic-oud?ref=synthetic"
ROBOTS_A = "https://" + HOST_A + "/robots.txt"
KEY_A = "shopify_catalog:" + HOST_A
NOW = datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc)
T0 = 1000.0

CAT_DATA = {"products": [{"id": 1, "title": "Synthetic Oud Eau de Parfum 100ml", "variants": []}]}
CAT_TEXT = json.dumps(CAT_DATA)
CAT_OK = dict(CAT_DATA, _store_currency="BHD")
META_BHD = json.dumps({"currency": "bhd"})
FEED_TEXT = json.dumps({"product": {"id": 7, "title": "Synthetic Oud", "variants": []}})
WALLED_HTML = "<html><head><title>Just a moment...</title></head><body>cf_chl_opt</body></html>"
PLAIN_HTML = "<html><head><title>Synthetic store</title></head><body><p>Welcome</p></body></html>"
JSON_WITH_LT = json.dumps({"products": [{"body_html": "<title>Just a moment</title> cf_chl_opt"}]})
NEG = {"_shopify_neg": True}
JSON_TYPE = {"content-type": "application/json"}
HTML_TYPE = {"content-type": "text/html"}

BASE_KW = {"allow_redirects": True, "impersonate": "chrome", "timeout": 5}
FEED_BASE_KW = {"allow_redirects": False, "impersonate": "chrome", "timeout": 12}
DENY_RULES = {"qarenbot": [["disallow", "/"]], "star": [["disallow", "/"]]}
PATH_BLOCK = [["allow", "/"], ["disallow", "/products/blocked"]]
PATH_RULES = {"qarenbot": PATH_BLOCK, "star": PATH_BLOCK}
LIVE_SKIP = "[SHOPIFY_LIVE] skip host=%s reason=%s"
LIVE_ENDED = "[SHOPIFY_LIVE] host ended host=%s reason=%s status=%s"
D14_SKIP = "[LIVE_ROBOTS] skip source=shopify host=%s reason=%s"


# ---------------------------------------------------------------------------
# harness
# ---------------------------------------------------------------------------

def _need(mod, name):
    obj = getattr(mod, name, None)
    assert obj is not None, "%s.%s is missing (INC-SH1 not implemented)" % (mod.__name__, name)
    return obj


def _set(mp, name, value):
    if value is None:
        mp.delenv(name, raising=False)
    else:
        mp.setenv(name, value)


def _run(make):
    """Run one coroutine in a FRESH context (no scope leaks between rows)."""
    return contextvars.Context().run(asyncio.run, make())


def _scope_values(ctx=None):
    ctx = contextvars.copy_context() if ctx is None else ctx
    return [ctx[var] for var in ctx if getattr(var, "name", None) == SCOPE_VAR]


def _named_headers():
    from app.services import robots_eval

    return {"User-Agent": robots_eval.QARENBOT_UA, "Accept": "*/*"}


def _named_kw(timeout):
    return {"allow_redirects": False, "headers": _named_headers(), "timeout": timeout}


def _retry_line(host):
    return "[UCP_JSON] 503 for " + host + " " + chr(0x2014) + " retrying once"


def _iso(moment):
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def _robots(origin, rules=None, with_origin=True):
    rules = rules or {}
    rec = {
        "state": "allow",
        "status": 200,
        "fetched_at": _iso(NOW - timedelta(hours=1)),
        "next_reread": _iso(NOW + timedelta(hours=23)),
        "crawl_delay": None,
        "source": "robots_txt",
        "probed": "/",
        "rules": {"qarenbot": rules.get("qarenbot", [["allow", "/"]]),
                  "star": rules.get("star", [["allow", "/"]])},
    }
    if with_origin:
        rec["origin"] = origin
    return rec


def _row(host, *, status="live", rules=None, origin=None, with_origin=True, challenge=None):
    robots = _robots(origin or ("https://" + host), rules, with_origin)
    return {"host": host, "status": status, "deny": False, "robots": robots,
            "challenge": challenge}


def _seed(mp, lr, rows, cold=False):
    """The memo as live_robots holds it after one good load (or a cold memo)."""
    from app.services import deny_hosts

    state = {"rows": None, "loaded_at": None, "good_at": None, "warned_at": None}
    if not cold:
        view = {}
        for raw in rows:
            host = deny_hosts.normalize_host(raw["host"])
            item = {key: copy.deepcopy(raw.get(key))
                    for key in ("host", "status", "deny", "robots", "challenge")}
            item["host"] = host
            view[host] = item
        state.update(rows=view, loaded_at=T0, good_at=T0)
    mp.setattr(lr, "_STATE", state)
    mp.setattr(lr, "_REFRESH", None)


class _Resp:
    def __init__(self, status, text="", headers=None):
        self.status_code = status
        self.text = text
        self.headers = dict(headers or {})
        self.encoding = "utf-8"

    @property
    def content(self):
        return self.text.encode("utf-8")

    def json(self):
        try:
            return json.loads(self.text)
        except ValueError:
            pass
        raise ValueError("synthetic not json")


class SyntheticTransportError(Exception):
    """A transport failure raised by the fake library."""


def _redirect(location, status=302):
    return _Resp(status, "", {"Location": location})


def _norm_kw(kwargs):
    out = {}
    for key in sorted(kwargs):
        value = kwargs[key]
        out[key] = dict(value) if isinstance(value, dict) else value
    return out


class _Transport:
    """The curl_cffi.requests.get recorder. A scripted entry is a response, an
    exception or a FIFO list (the last item sticks). With allow_redirects=True a
    3xx with a Location is followed here, one recorded 'follow' per hop, as the
    library would; with allow_redirects=False the 3xx is handed back."""

    def __init__(self):
        self.calls = []
        self.script = {}
        self._lock = threading.Lock()

    def _next(self, url):
        entry = self.script.get(url)
        if entry is None:
            return _Resp(404, "not found")
        if isinstance(entry, list):
            return entry.pop(0) if len(entry) > 1 else entry[0]
        return entry

    def __call__(self, url, **kwargs):
        with self._lock:
            self.calls.append(["get", url, _norm_kw(kwargs)])
            resp = self._next(url)
        hops = 0
        while (not isinstance(resp, BaseException) and kwargs.get("allow_redirects")
               and 300 <= resp.status_code < 400 and resp.headers.get("Location") and hops < 5):
            url = urljoin(url, resp.headers["Location"])
            with self._lock:
                self.calls.append(["follow", url, {}])
                resp = self._next(url)
            hops += 1
        if isinstance(resp, BaseException):
            raise resp
        return resp


class _Cache:
    def __init__(self):
        self.hit = None
        self.reads = []
        self.writes = []

    def get(self, key, *args, **kwargs):
        self.reads.append(key)
        return copy.deepcopy(self.hit)

    def set(self, key, value, ttl=None, *args, **kwargs):
        self.writes.append([key, copy.deepcopy(value), ttl])
        return True


class _LogRec(logging.Handler):
    def __init__(self):
        super().__init__(level=logging.INFO)
        self.rows = []

    def emit(self, record):
        try:
            msg = record.getMessage()
        except Exception:  # noqa: BLE001
            msg = str(record.msg)
        self.rows.append((record.name, record.levelno, msg))

    def of(self, name, level=logging.INFO):
        return [r[2] for r in self.rows if r[0] == name and r[1] >= level]

    def live(self):
        return [r[2] for r in self.rows if r[2].startswith("[SHOPIFY_LIVE]")]


class _Harness:
    pass


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    import app.main  # noqa: F401  (FIRST: the dotenv-override hazard)

    for name in CLEARED_ENV:
        monkeypatch.delenv(name, raising=False)
    for name, value in KNOBS.items():
        monkeypatch.setenv(name, value)
    yield


@pytest.fixture
def h(monkeypatch):
    import curl_cffi.requests as curl_requests

    from app.services import live_robots as lr
    from app.services import price_service as ps
    from app.services import robots_registry as rr
    from app.services import shopify_pdp_service as sps
    from app.utils import url_validator

    box = _Harness()
    box.mp, box.lr, box.ps, box.rr, box.sps = monkeypatch, lr, ps, rr, sps
    box.transport = _Transport()
    monkeypatch.setattr(curl_requests, "get", box.transport)
    box.cache = _Cache()
    monkeypatch.setattr(ps, "get_cached", box.cache.get)
    monkeypatch.setattr(ps, "set_cached", box.cache.set)
    box.slots, box.validated, box.mono, box.admin, box.memo_reads, box.emitter = [], [], [], [], [], []

    async def _slot(domain):
        box.slots.append(domain)

    async def _validate(url):
        box.validated.append(url)
        return True

    def _mono():
        box.mono.append(1)
        return T0

    def _admin(*args, **kwargs):
        box.admin.append(1)
        return None

    real_row_for_host = lr.row_for_host

    def _row_for_host(host):
        box.memo_reads.append(host)
        return real_row_for_host(host)

    async def _emitter(*args, **kwargs):
        box.emitter.append(list(args))
        raise AssertionError("the robots emitter was reached")

    monkeypatch.setattr(sps, "_await_domain_slot", _slot)
    monkeypatch.setattr(url_validator, "_validate_url_offloop_or_sync", _validate)
    monkeypatch.setattr(lr, "_monotonic", _mono)
    monkeypatch.setattr(lr, "_now", lambda: NOW)
    monkeypatch.setattr(lr, "_admin_client", _admin)
    monkeypatch.setattr(lr, "row_for_host", _row_for_host)
    box.real_default_fetch = rr.default_fetch
    monkeypatch.setattr(rr, "default_fetch", _emitter)
    _seed(monkeypatch, lr, [], cold=True)
    box.logs = _LogRec()
    saved = []
    for name in LOGGERS:
        lg = logging.getLogger(name)
        saved.append((lg, lg.level))
        lg.setLevel(logging.INFO)
        lg.addHandler(box.logs)
    try:
        yield box
    finally:
        for lg, level in saved:
            lg.removeHandler(box.logs)
            lg.setLevel(level)


def _reset(h):
    h.transport.calls.clear()
    h.transport.script = {}
    h.cache.reads.clear()
    h.cache.writes.clear()
    h.cache.hit = None
    h.logs.rows.clear()
    for name in ("slots", "validated", "mono", "admin", "memo_reads", "emitter"):
        getattr(h, name).clear()


def _off_config(h, spelling, d14, rows, cold=False):
    """The FULL configuration with the switch OFF (B1)."""
    _set(h.mp, SWITCH, spelling)
    _set(h.mp, D14, d14)
    h.mp.setenv(UCP, "true")
    h.mp.setenv(PDP, "true")
    h.mp.setenv("ENABLE_PAGE_SCRAPE", "true")
    _seed(h.mp, h.lr, rows, cold=cold)


def _on_config(h, d14, rows, cold=False):
    _off_config(h, "true", d14, rows, cold=cold)


def _feed(h, url=FEED_A, domain=HOST_A):
    return h.sps._fetch_feed_body(url, domain, log_tag="UCP_JSON")


def _counts(h):
    got = h.lr._ATTEMPTS_CTX.get()
    return dict(got) if isinstance(got, dict) else got


# ---------------------------------------------------------------------------
# PIN rows (green at base)
# ---------------------------------------------------------------------------

def _catalog_scenarios():
    neg = [[KEY_A, NEG, 1800]]
    one = [["get", CAT_A, BASE_KW]]
    return [
        ("ok_200", {CAT_A: _Resp(200, CAT_TEXT, JSON_TYPE), META_A: _Resp(200, META_BHD)},
         [["get", CAT_A, BASE_KW], ["get", META_A, BASE_KW]], [], [[KEY_A, CAT_OK, 21600]], CAT_OK),
        ("http_429", {CAT_A: _Resp(429, "slow down")}, one,
         ["[PRICE] Shopify catalog HTTP 429 for " + HOST_A], neg, None),
        ("http_403", {CAT_A: _Resp(403, "no")}, one,
         ["[PRICE] Shopify catalog HTTP 403 for " + HOST_A], neg, None),
        ("http_503", {CAT_A: _Resp(503, "busy")}, one,
         ["[PRICE] Shopify catalog HTTP 503 for " + HOST_A], neg, None),
        ("challenge_header", {CAT_A: _Resp(403, WALLED_HTML, dict(HTML_TYPE, **{"cf-mitigated": "challenge"}))},
         one, ["[PRICE] Shopify catalog HTTP 403 for " + HOST_A], neg, None),
        ("walled_200", {CAT_A: _Resp(200, WALLED_HTML, HTML_TYPE)}, one, [], neg, None),
        ("timeout", {CAT_A: TimeoutError("synthetic timeout")}, one,
         ["[PRICE] Shopify catalog fetch failed for " + HOST_A + ": synthetic timeout"], neg, None),
    ]


@pytest.mark.parametrize("d14", D14_STATES, ids=D14_IDS)
@pytest.mark.parametrize("spelling", OFF_SPELLINGS, ids=OFF_IDS)
def test_p1_catalog_off_identity(h, spelling, d14):
    _off_config(h, spelling, d14, [_row(HOST_A, rules=DENY_RULES)])
    for name, script, calls, lines, writes, ret in _catalog_scenarios():
        _reset(h)
        h.transport.script = script
        got = _run(lambda: h.ps._fetch_shopify_catalog(HOST_A))
        assert h.transport.calls == calls, (name, h.transport.calls)
        assert h.logs.of(PS_LOG) == lines, (name, h.logs.rows)
        assert h.logs.of(SPS_LOG) == [] and h.logs.of(LR_LOG) == [], (name, h.logs.rows)
        assert h.cache.reads == [KEY_A], name
        assert h.cache.writes == writes, (name, h.cache.writes)
        assert got == ret, name
        assert h.memo_reads == [] and h.mono == [] and h.admin == [], name
    for hit, ret in ((copy.deepcopy(CAT_DATA), CAT_DATA), (dict(NEG), None)):
        _reset(h)
        h.cache.hit = hit
        got = _run(lambda: h.ps._fetch_shopify_catalog("www." + HOST_A.upper()))
        assert got == ret and h.transport.calls == [] and h.cache.writes == []
        assert h.cache.reads == [KEY_A] and h.memo_reads == [] and h.mono == []


def _currency_scenarios():
    one = [["get", META_A, BASE_KW]]
    return [
        ("ok_200", {META_A: _Resp(200, json.dumps({"currency": "usd"}))}, [], "USD"),
        ("no_currency", {META_A: _Resp(200, json.dumps({"name": "synthetic"}))}, [], None),
        ("http_429", {META_A: _Resp(429, "slow down")}, [], None),
        ("http_403", {META_A: _Resp(403, "no")}, [], None),
        ("http_503", {META_A: _Resp(503, "busy")}, [], None),
        ("challenge_header", {META_A: _Resp(403, WALLED_HTML, dict(HTML_TYPE, **{"cf-mitigated": "challenge"}))},
         [], None),
        ("walled_200", {META_A: _Resp(200, WALLED_HTML, HTML_TYPE)},
         ["[PRICE] Shopify currency probe failed for " + HOST_A + ": synthetic not json"], None),
        ("timeout", {META_A: TimeoutError("synthetic timeout")},
         ["[PRICE] Shopify currency probe failed for " + HOST_A + ": synthetic timeout"], None),
    ], one


@pytest.mark.parametrize("d14", D14_STATES, ids=D14_IDS)
@pytest.mark.parametrize("spelling", OFF_SPELLINGS, ids=OFF_IDS)
def test_p2_currency_off_identity(h, spelling, d14):
    _off_config(h, spelling, d14, [_row(HOST_A, rules=DENY_RULES)])
    scenarios, one = _currency_scenarios()
    for name, script, lines, ret in scenarios:
        _reset(h)
        h.transport.script = script
        got = _run(lambda: h.ps._fetch_shopify_currency(HOST_A))
        assert h.transport.calls == one, (name, h.transport.calls)
        assert h.logs.of(PS_LOG) == lines, (name, h.logs.rows)
        assert h.logs.of(LR_LOG) == [], name
        assert got == ret, name
        assert h.cache.reads == [] and h.cache.writes == [], name
        assert h.memo_reads == [] and h.mono == [] and h.admin == [], name


@pytest.mark.parametrize("spelling", OFF_SPELLINGS, ids=OFF_IDS)
def test_p3_feed_off_identity(h, spelling):
    deny_a = _row(HOST_A, rules=DENY_RULES)
    deny_b = _row(HOST_B, rules=DENY_RULES)
    two = [["get", FEED_A, FEED_BASE_KW], ["get", FEED_A, FEED_BASE_KW]]
    cases = [
        ("d14_off_503_then_200", None, [deny_a],
         {FEED_A: [_Resp(503, "busy"), _Resp(200, FEED_TEXT)]}, two, [_retry_line(HOST_A)], [], None,
         FEED_TEXT),
        ("d14_off_hop_not_gated", None, [_row(HOST_A, rules=PATH_RULES), deny_b],
         {FEED_A: _redirect("/products/blocked.json"), BLOCKED_A: _Resp(200, FEED_TEXT)},
         [["get", FEED_A, FEED_BASE_KW], ["get", BLOCKED_A, FEED_BASE_KW]], [], [], None, FEED_TEXT),
        ("d14_on_disallow", "true", [deny_a], {FEED_A: _Resp(200, FEED_TEXT)}, [], [],
         [D14_SKIP % (HOST_A, "robots")], {("shopify", HOST_A, "robots_skip"): 1}, None),
        ("d14_on_allow_503_then_200", "true", [_row(HOST_A), deny_b],
         {FEED_A: [_Resp(503, "busy"), _Resp(200, FEED_TEXT)]}, two, [_retry_line(HOST_A)], [],
         {("shopify", HOST_A, "fail"): 1, ("shopify", HOST_A, "ok"): 1}, FEED_TEXT),
        ("d14_on_hop_gated", "true", [_row(HOST_A, rules=PATH_RULES), deny_b],
         {FEED_A: _redirect("/products/blocked.json"), BLOCKED_A: _Resp(200, FEED_TEXT)},
         [["get", FEED_A, FEED_BASE_KW]], [], [D14_SKIP % (HOST_A, "robots")],
         {("shopify", HOST_A, "robots_skip"): 1}, None),
    ]
    for name, d14, rows, script, calls, sps_lines, lr_lines, counts, ret in cases:
        _off_config(h, spelling, d14, rows)
        _reset(h)
        h.transport.script = script

        async def flow(d14=d14):
            if d14:
                h.lr.bind_attempts()
            body = await _feed(h)
            return body, _counts(h)

        body, got_counts = _run(flow)
        assert h.transport.calls == calls, (name, h.transport.calls)
        assert h.logs.of(SPS_LOG) == sps_lines, (name, h.logs.rows)
        assert h.logs.of(LR_LOG) == lr_lines, (name, h.logs.rows)
        assert h.logs.live() == [], name
        assert got_counts == counts, (name, got_counts)
        assert body == ret, name
        assert h.slots == [HOST_A] * len(calls), (name, h.slots)


@pytest.mark.parametrize("d14", D14_STATES, ids=D14_IDS)
@pytest.mark.parametrize("spelling", OFF_SPELLINGS, ids=OFF_IDS)
def test_p4_bind_off_writes_nothing(h, spelling, d14):
    from app.services.structured_comparison_service import StructuredComparisonService

    _off_config(h, spelling, d14, [_row(HOST_A, rules=DENY_RULES)])
    svc = StructuredComparisonService.__new__(StructuredComparisonService)
    ctx = contextvars.Context()
    ctx.run(svc._init_provider_attempts)
    names = sorted(getattr(var, "name", "") for var in ctx)
    assert SCOPE_VAR not in names, names
    assert names == (["live_robots_attempts", "provider_attempts"] if d14 else ["provider_attempts"])
    assert svc._provider_attempts == []
    assert h.memo_reads == [] and h.mono == []


@pytest.mark.parametrize("d14", D14_STATES, ids=D14_IDS)
@pytest.mark.parametrize("spelling", OFF_SPELLINGS + ["true"], ids=OFF_IDS + ["on"])
def test_p5_u7_prefix_kept(h, spelling, d14):
    _off_config(h, spelling, d14, [_row(HOST_A), _row(HOST_B, rules=DENY_RULES)])
    _reset(h)
    h.transport.script = {PDP_A: SyntheticTransportError("synthetic transport failure")}
    got = _run(lambda: h.ps.curl_fetch_html_same_site(PDP_A, HOST_A))
    assert got is None
    assert h.transport.calls == [["get", PDP_A, {"allow_redirects": False, "impersonate": "chrome",
                                                 "timeout": 5}]], h.transport.calls
    warnings = [r[2] for r in h.logs.rows if r[0] == PS_LOG and r[1] == logging.WARNING]
    assert len(warnings) == 1, h.logs.rows
    assert warnings[0].startswith("[PRICE] curl_fetch_html_same_site failed for "), warnings


# ---------------------------------------------------------------------------
# RED rows (AssertionError at base)
# ---------------------------------------------------------------------------

def _function(tree, name):
    hits = [n for n in tree.body
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name]
    assert len(hits) == 1, "%s: %d module-level definitions (INC-SH1 not implemented)" % (name, len(hits))
    return hits[0]


def test_r1_reader_idiom(h):
    reader = _need(h.ps, "shopify_named_live_read_enabled")
    for value in ON_SPELLINGS:
        h.mp.setenv(SWITCH, value)
        assert reader() is True, repr(value)
    for value in OFF_SPELLINGS + ["tru", "enabled", "y", "2", "onn"]:
        _set(h.mp, SWITCH, value)
        assert reader() is False, repr(value)
    tree = ast.parse(Path(h.ps.__file__).read_text(encoding="utf-8"))
    fn = _function(tree, "shopify_named_live_read_enabled")
    body = [n for n in fn.body if not (isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant)
                                       and isinstance(n.value.value, str))]
    first = ast.unparse(body[0])
    idiom = ("os.getenv('ENABLE_SHOPIFY_NAMED_LIVE_READ', 'false').strip().lower() in "
             "('true', '1', 'yes', 'on')")
    assert idiom in first, first


@pytest.mark.parametrize("d14", D14_STATES, ids=D14_IDS)
def test_r2_catalog_named_agent(h, d14):
    _on_config(h, d14, [_row(HOST_A), _row(HOST_B)])
    named = _named_headers()
    _reset(h)
    h.transport.script = {ROBOTS_A: _Resp(200, "User-agent: *")}
    _run(lambda: h.real_default_fetch(ROBOTS_A))
    emitted = h.transport.calls[-1][2].get("headers")
    _reset(h)
    h.transport.script = {CAT_A: _Resp(200, CAT_TEXT, JSON_TYPE), META_A: _Resp(200, META_BHD)}
    got = _run(lambda: h.ps._fetch_shopify_catalog(HOST_A))
    calls = h.transport.calls
    assert [c[1] for c in calls] == [CAT_A, META_A], calls
    for call in calls:
        assert "impersonate" not in call[2], call
        assert call[2] == _named_kw(5), call
        assert call[2]["headers"] == emitted == named, (call, emitted)
    assert got == CAT_OK
    assert h.cache.writes == [[KEY_A, CAT_OK, 21600]]
    assert h.logs.live() == []
    assert _need(h.sps, "NAMED_READ_HEADERS") == named
    _reset(h)
    h.cache.hit = copy.deepcopy(CAT_DATA)
    assert _run(lambda: h.ps._fetch_shopify_catalog(HOST_A)) == CAT_DATA
    assert h.transport.calls == [] and h.memo_reads == []


@pytest.mark.parametrize("d14", D14_STATES, ids=D14_IDS)
def test_r3_currency_named_agent(h, d14):
    _on_config(h, d14, [_row(HOST_A)])
    _reset(h)
    h.transport.script = {META_A: _Resp(200, json.dumps({"currency": "usd"}))}
    got = _run(lambda: h.ps._fetch_shopify_currency(HOST_A))
    assert h.transport.calls == [["get", META_A, _named_kw(5)]], h.transport.calls
    assert got == "USD"


@pytest.mark.parametrize("d14", D14_STATES, ids=D14_IDS)
def test_r4_feed_named_agent(h, d14):
    _on_config(h, d14, [_row(HOST_A)])
    _reset(h)
    real = h.sps._curl_get
    seam = []

    def _seam(url, timeout):
        seam.append(url)
        return real(url, timeout)

    h.mp.setattr(h.sps, "_curl_get", _seam)
    h.transport.script = {FEED_A: _Resp(200, FEED_TEXT)}

    async def flow():
        if d14:
            h.lr.bind_attempts()
        body = await _feed(h)
        return body, _counts(h)

    body, counts = _run(flow)
    assert h.transport.calls == [["get", FEED_A, _named_kw(12)]], h.transport.calls
    assert seam == []
    assert body == FEED_TEXT
    assert h.slots == [HOST_A] and h.validated == [FEED_A]
    if d14:
        assert counts == {("shopify", HOST_A, "ok"): 1}, counts


R5_STATES = ["disallow", "no_row", "no_origin", "www_origin", "cold", "blocked", "parked"]
R5_REASON = {"disallow": "robots", "no_row": "no_row", "no_origin": "no_record",
             "www_origin": "origin", "cold": "no_row", "blocked": "not_live", "parked": "robots"}


def _r5_rows(state):
    parked = {"vendor": "cloudflare", "parked_until": _iso(NOW + timedelta(days=1))}
    return {
        "disallow": ([_row(HOST_A, rules=DENY_RULES)], False),
        "no_row": ([_row(HOST_B)], False),
        "no_origin": ([_row(HOST_A, with_origin=False)], False),
        "www_origin": ([_row(HOST_A, origin="https://www." + HOST_A)], False),
        "cold": ([], True),
        "blocked": ([_row(HOST_A, status="blocked")], False),
        "parked": ([_row(HOST_A, challenge=parked)], False),
    }[state]


def _three(h):
    return (("catalog", lambda: h.ps._fetch_shopify_catalog(HOST_A)),
            ("currency", lambda: h.ps._fetch_shopify_currency(HOST_A)),
            ("feed", lambda: _feed(h)))


@pytest.mark.parametrize("state", R5_STATES)
def test_r5_gate_d14_off(h, state):
    rows, cold = _r5_rows(state)
    _on_config(h, None, rows, cold=cold)
    skip = LIVE_SKIP % (HOST_A, R5_REASON[state])
    for label, make in _three(h):
        _reset(h)
        got = _run(make)
        assert h.transport.calls == [], (label, h.transport.calls)
        assert got is None, label
        assert h.cache.writes == [], (label, h.cache.writes)
        assert h.logs.live() == [skip], (label, h.logs.rows)
        assert h.slots == [], label


def test_r6_gate_d14_on(h):
    _on_config(h, "true", [_row(HOST_A, rules=DENY_RULES)])
    for label, make in _three(h):
        _reset(h)

        async def flow(make=make):
            h.lr.bind_attempts()
            got = await make()
            return got, _counts(h)

        got, counts = _run(flow)
        assert h.transport.calls == [], (label, h.transport.calls)
        assert got is None, label
        assert counts == {("shopify", HOST_A, "robots_skip"): 1}, (label, counts)
        assert h.logs.of(LR_LOG) == [D14_SKIP % (HOST_A, "robots")], (label, h.logs.rows)
        assert h.cache.writes == [], label


@pytest.mark.parametrize("d14", D14_STATES, ids=D14_IDS)
@pytest.mark.parametrize("state", ["disallow", "no_row", "cold", "parked"])
def test_r7_gate_no_robots_fetch(h, state, d14):
    admit = _need(h.ps, "shopify_named_read_admit")
    rows, cold = _r5_rows(state)
    _on_config(h, d14, rows, cold=cold)
    lookups = []

    def _gai(*args, **kwargs):
        lookups.append(args[0] if args else None)
        raise OSError("no name lookup is expected in this row")

    h.mp.setattr(socket, "getaddrinfo", _gai)
    _reset(h)

    async def flow():
        if d14:
            h.lr.bind_attempts()
        verdicts = [admit(CAT_A), admit(META_A), admit(FEED_A)]
        await h.ps._fetch_shopify_catalog(HOST_A)
        await h.ps._fetch_shopify_currency(HOST_A)
        await _feed(h)
        return verdicts

    verdicts = _run(flow)
    assert verdicts == [False, False, False]
    assert h.emitter == [] and lookups == []
    assert h.transport.calls == []
    assert [u for u in h.validated if "robots.txt" in u] == []


R8_KINDS = ["throttled_429", "refused_403", "throttled_503", "challenge_header", "challenge_walled_200"]


def _r8_response(kind):
    return {
        "throttled_429": (_Resp(429, "slow down"), "throttled", 429),
        "refused_403": (_Resp(403, "no"), "refused", 403),
        "throttled_503": (_Resp(503, "busy"), "throttled", 503),
        "challenge_header": (_Resp(403, "", {"cf-mitigated": "challenge"}), "challenge", 403),
        "challenge_walled_200": (_Resp(200, WALLED_HTML, HTML_TYPE), "challenge", 200),
    }[kind]


@pytest.mark.parametrize("d14", D14_STATES, ids=D14_IDS)
@pytest.mark.parametrize("kind", R8_KINDS)
def test_r8_refusal_ends_host(h, kind, d14):
    bind = _need(h.ps, "bind_shopify_named_read_scope")
    resp, reason, status = _r8_response(kind)
    _on_config(h, d14, [_row(HOST_A), _row(HOST_B)])
    _reset(h)
    h.transport.script = {CAT_A: resp, CAT_B: _Resp(200, CAT_TEXT, JSON_TYPE), META_B: _Resp(200, META_BHD)}

    async def flow():
        if d14:
            h.lr.bind_attempts()
        bind()
        first = await h.ps._fetch_shopify_catalog(HOST_A)
        sent_first = len(h.transport.calls)
        again = await h.ps._fetch_shopify_catalog(HOST_A)
        cur = await h.ps._fetch_shopify_currency(HOST_A)
        feed = await _feed(h, FEED_A_WWW, HOST_A)
        sent_later = len(h.transport.calls) - sent_first
        other = await h.ps._fetch_shopify_catalog(HOST_B)
        return first, sent_first, again, cur, feed, sent_later, other

    first, sent_first, again, cur, feed, sent_later, other = _run(flow)
    assert sent_first == 1, h.transport.calls
    assert sent_later == 0, h.transport.calls
    assert (first, again, cur, feed) == (None, None, None, None)
    assert [c[1] for c in h.transport.calls] == [CAT_A, CAT_B, META_B], h.transport.calls
    assert other == CAT_OK
    ended = [m for m in h.logs.live() if m.startswith("[SHOPIFY_LIVE] host ended ")]
    assert ended == [LIVE_ENDED % (HOST_A, reason, status)], h.logs.rows
    skips = [m for m in h.logs.live() if m.startswith("[SHOPIFY_LIVE] skip ")]
    assert skips == [LIVE_SKIP % (HOST_A, "ended")] * 3, h.logs.rows


def test_r8_refusal_ends_host_www_direction(h):
    bind = _need(h.ps, "bind_shopify_named_read_scope")
    admit = _need(h.ps, "shopify_named_read_admit")
    _on_config(h, None, [_row(HOST_A), _row(HOST_C, origin="https://www." + HOST_C)])
    _reset(h)
    h.transport.script = {FEED_C_WWW: _Resp(429, "slow down")}

    async def flow():
        bind()
        body = await _feed(h, FEED_C_WWW, HOST_C)
        return body, admit(CAT_C), admit(FEED_C_WWW), admit(CAT_A)

    body, cat_c, feed_c, cat_a = _run(flow)
    assert [c[1] for c in h.transport.calls] == [FEED_C_WWW], h.transport.calls
    assert body is None
    assert (cat_c, feed_c, cat_a) == (False, False, True)
    ended = [m for m in h.logs.live() if m.startswith("[SHOPIFY_LIVE] host ended ")]
    assert ended == [LIVE_ENDED % (HOST_C, "throttled", 429)], h.logs.rows
    skips = [m for m in h.logs.live() if m.startswith("[SHOPIFY_LIVE] skip ")]
    assert skips == [LIVE_SKIP % (HOST_C, "ended")] * 2, h.logs.rows


def test_r9_no_retry(h):
    _on_config(h, None, [_row(HOST_A)])
    _reset(h)
    h.transport.script = {FEED_A: [_Resp(503, "busy"), _Resp(200, FEED_TEXT)]}
    body = _run(lambda: _feed(h))
    assert len(h.transport.calls) == 1, h.transport.calls
    assert body is None
    assert _retry_line(HOST_A) not in h.logs.of(SPS_LOG), h.logs.rows
    assert "[UCP_JSON] HTTP 503 for " + HOST_A in h.logs.of(SPS_LOG), h.logs.rows
    bind = _need(h.ps, "bind_shopify_named_read_scope")
    _reset(h)
    h.transport.script = {FEED_A: [_Resp(503, "busy"), _Resp(200, FEED_TEXT)]}

    async def flow():
        bind()
        return await _feed(h)

    assert _run(flow) is None
    assert h.transport.calls == [["get", FEED_A, _named_kw(12)]], h.transport.calls
    assert h.logs.live() == [LIVE_ENDED % (HOST_A, "throttled", 503)], h.logs.rows


R10_KINDS = ["http_404", "http_500", "timeout"]


@pytest.mark.parametrize("kind", R10_KINDS)
def test_r10_non_ending(h, kind):
    def make():
        return {"http_404": _Resp(404, "missing"), "http_500": _Resp(500, "oops"),
                "timeout": TimeoutError("synthetic timeout")}[kind]

    cat_line = {"http_404": "[PRICE] Shopify catalog HTTP 404 for " + HOST_A,
                "http_500": "[PRICE] Shopify catalog HTTP 500 for " + HOST_A,
                "timeout": "[PRICE] Shopify catalog fetch failed for " + HOST_A + ": synthetic timeout"}[kind]
    feed_line = {"http_404": "[UCP_JSON] HTTP 404 for " + HOST_A,
                 "http_500": "[UCP_JSON] HTTP 500 for " + HOST_A,
                 "timeout": "[SHOPIFY_JS] fetch failed for " + HOST_A + ": synthetic timeout"}[kind]
    _on_config(h, None, [_row(HOST_A)])
    _reset(h)
    h.transport.script = {CAT_A: make()}
    assert _run(lambda: h.ps._fetch_shopify_catalog(HOST_A)) is None
    assert h.transport.calls == [["get", CAT_A, _named_kw(5)]], h.transport.calls
    bind = _need(h.ps, "bind_shopify_named_read_scope")
    admit = _need(h.ps, "shopify_named_read_admit")
    _reset(h)
    h.transport.script = {CAT_A: make(), FEED_A: make()}

    async def flow():
        bind()
        first = await h.ps._fetch_shopify_catalog(HOST_A)
        open_after = admit(CAT_A)
        second = await h.ps._fetch_shopify_catalog(HOST_A)
        feed = await _feed(h)
        return first, open_after, second, feed, admit(FEED_A)

    first, open_after, second, feed, open_feed = _run(flow)
    assert (first, second, feed) == (None, None, None)
    assert open_after is True and open_feed is True
    assert h.transport.calls == [["get", CAT_A, _named_kw(5)], ["get", CAT_A, _named_kw(5)],
                                 ["get", FEED_A, _named_kw(12)]], h.transport.calls
    assert h.logs.of(PS_LOG) == [cat_line, cat_line], h.logs.rows
    assert h.logs.of(SPS_LOG) == [feed_line], h.logs.rows
    assert h.cache.writes == [[KEY_A, NEG, 1800], [KEY_A, NEG, 1800]]
    assert h.logs.live() == [], h.logs.rows


R11_TABLE = [
    ("json", 200, JSON_TYPE, CAT_TEXT),
    ("json_with_lt", 200, JSON_TYPE, JSON_WITH_LT),
    ("json_with_lt_no_type", 200, {}, JSON_WITH_LT),
    ("walled_html_403", 403, HTML_TYPE, WALLED_HTML),
    ("cf_mitigated_200", 200, {"cf-mitigated": "challenge"}, ""),
    ("cf_mitigated_mixed_case_403", 403, {"Cf-Mitigated": " Challenge "}, "{}"),
    ("normal_html_200", 200, HTML_TYPE, PLAIN_HTML),
    ("normal_html_403", 403, HTML_TYPE, PLAIN_HTML),
    ("walled_no_type_200", 200, {}, WALLED_HTML),
]


@pytest.mark.parametrize("anchor", [None, "true"], ids=["anchor_off", "anchor_on"])
def test_r11_challenge_parity(h, anchor):
    refusal = _need(h.ps, "shopify_named_read_refusal")
    _set(h.mp, ANCHOR, anchor)
    seen = set()
    for name, status, headers, body in R11_TABLE:
        nightly = h.rr._challenge(status, dict(headers), body) is not None
        ours = refusal(status, dict(headers), body) == "challenge"
        assert ours == nightly, (name, ours, nightly)
        seen.add(nightly)
    assert seen == {True, False}


def test_r11_refusal_status_table(h):
    refusal = _need(h.ps, "shopify_named_read_refusal")
    table = [(429, "throttled"), (503, "throttled"), (403, "refused"), (200, None), (404, None),
             (500, None), (301, None), (302, None), (401, None), (None, None)]
    for status, expected in table:
        assert refusal(status, dict(JSON_TYPE), "{}") == expected, status


def test_r12_request_scope(h):
    bind = _need(h.ps, "bind_shopify_named_read_scope")
    observe = _need(h.ps, "shopify_named_read_observe")
    admit = _need(h.ps, "shopify_named_read_admit")
    _on_config(h, None, [_row(HOST_A), _row(HOST_B)])
    _reset(h)

    def snap():
        return [(type(v).__name__, sorted(v)) for v in _scope_values()]

    async def flow():
        bind()
        first = snap()

        async def ender():
            observe(CAT_A, _Resp(429, "slow down"))

        async def reader():
            return admit(CAT_A), admit(CAT_B)

        await asyncio.gather(asyncio.create_task(ender()))
        shared = await asyncio.create_task(reader())
        after = snap()
        bind()
        fresh = snap()
        return first, shared, after, fresh, admit(CAT_A)

    first, shared, after, fresh, again = _run(flow)
    assert first == [("set", [])], first
    assert shared == (False, True), shared
    assert len(after) == 1 and HOST_A in after[0][1], after
    assert fresh == [("set", [])], fresh
    assert again is True

    async def unbound():
        observe(CAT_A, _Resp(429, "slow down"))
        return admit(CAT_A), _scope_values()

    ok, values = _run(unbound)
    assert ok is True and values == []


@pytest.mark.parametrize("d14", D14_STATES, ids=D14_IDS)
def test_r13_bind_wired(h, d14):
    from app.services.structured_comparison_service import StructuredComparisonService

    _on_config(h, d14, [_row(HOST_A)])
    svc = StructuredComparisonService.__new__(StructuredComparisonService)
    ctx = contextvars.Context()
    ctx.run(svc._init_provider_attempts)
    values = _scope_values(ctx)
    assert len(values) == 1, "no %s bound by _init_provider_attempts" % SCOPE_VAR
    assert isinstance(values[0], set) and not values[0], values
    values[0].add(HOST_A)
    ctx.run(svc._init_provider_attempts)
    again = _scope_values(ctx)
    assert len(again) == 1 and isinstance(again[0], set) and not again[0], again


def test_r14_redirects_on(h):
    _on_config(h, None, [_row(HOST_A)])
    moved = "https://" + HOST_A + "/collections/all"
    _reset(h)
    h.transport.script = {CAT_A: _redirect(moved, 301), moved: _Resp(200, CAT_TEXT, JSON_TYPE),
                          META_A: _Resp(200, META_BHD)}
    got = _run(lambda: h.ps._fetch_shopify_catalog(HOST_A))
    assert h.transport.calls == [["get", CAT_A, _named_kw(5)]], h.transport.calls
    assert got is None
    assert h.cache.writes == [[KEY_A, NEG, 1800]]
    assert h.logs.of(PS_LOG) == ["[PRICE] Shopify catalog HTTP 301 for " + HOST_A], h.logs.rows
    meta_moved = "https://" + HOST_A + "/meta-moved.json"
    _reset(h)
    h.transport.script = {META_A: _redirect(meta_moved), meta_moved: _Resp(200, json.dumps({"currency": "usd"}))}
    assert _run(lambda: h.ps._fetch_shopify_currency(HOST_A)) is None
    assert h.transport.calls == [["get", META_A, _named_kw(5)]], h.transport.calls
    _reset(h)
    h.transport.script = {FEED_A: _redirect("/products/synthetic-amber.json"), OTHER_A: _Resp(200, FEED_TEXT)}
    assert _run(lambda: _feed(h)) == FEED_TEXT
    hops = [["get", FEED_A, _named_kw(12)], ["get", OTHER_A, _named_kw(12)]]
    assert h.transport.calls == hops, h.transport.calls
    assert h.validated == [FEED_A, OTHER_A]
    _seed(h.mp, h.lr, [_row(HOST_A, rules=PATH_RULES)])
    _reset(h)
    h.transport.script = {FEED_A: _redirect("/products/blocked.json"), BLOCKED_A: _Resp(200, FEED_TEXT)}
    assert _run(lambda: _feed(h)) is None
    assert h.transport.calls == [["get", FEED_A, _named_kw(12)]], h.transport.calls
    assert h.logs.live() == [LIVE_SKIP % (HOST_A, "robots")], h.logs.rows


PS_NEW = ("shopify_named_live_read_enabled", "shopify_named_read_admit", "shopify_named_read_refusal",
          "shopify_named_read_observe", "bind_shopify_named_read_scope")
LOG_METHODS = ("debug", "info", "warning", "error", "exception", "critical")
TEMPLATES = (LIVE_SKIP, LIVE_ENDED)


def _log_calls(node):
    return [sub for sub in ast.walk(node)
            if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute)
            and sub.func.attr in LOG_METHODS and isinstance(sub.func.value, ast.Name)
            and sub.func.value.id == "logger"]


def test_r15_new_log_hygiene(h):
    ps_text = Path(h.ps.__file__).read_text(encoding="utf-8")
    sps_text = Path(h.sps.__file__).read_text(encoding="utf-8")
    ps_tree, sps_tree = ast.parse(ps_text), ast.parse(sps_text)
    for name in PS_NEW:
        _function(ps_tree, name)
    _function(sps_tree, "_named_curl_get")
    formats = []
    for tree in (ps_tree, sps_tree):
        for fn in [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]:
            caught = {hd.name for hd in ast.walk(fn) if isinstance(hd, ast.ExceptHandler) and hd.name}
            for call in _log_calls(fn):
                src = ast.unparse(call)
                if "SHOPIFY_LIVE" not in src:
                    continue
                first = call.args[0] if call.args else None
                fmt = first.value if isinstance(first, ast.Constant) and isinstance(first.value, str) else None
                assert fmt is not None and fmt.startswith("[SHOPIFY_LIVE] "), src
                assert call.func.attr in ("debug", "info"), src
                assert fmt.count("%s") == len(call.args) - 1, src
                assert "%" not in fmt.replace("%s", ""), src
                assert not call.keywords, src
                for arg in call.args[1:]:
                    assert not isinstance(arg, ast.JoinedStr), src
                    if isinstance(arg, ast.Name):
                        assert "url" not in arg.id.lower(), src
                    used = {n.id for n in ast.walk(arg) if isinstance(n, ast.Name)}
                    if used & caught:
                        text = ast.unparse(arg)
                        assert text.startswith("type(") and text.endswith(").__name__"), src
                formats.append(fmt)
    assert set(formats) == set(TEMPLATES), sorted(set(formats))
    assert "robots_registry" not in ps_text and "robots_registry" not in sps_text


@pytest.mark.parametrize("spelling", [None, "true"], ids=["off", "on"])
def test_r16_u7_host_and_type(h, spelling):
    _off_config(h, spelling, None, [_row(HOST_A)])
    _reset(h)
    h.transport.script = {PDP_A: SyntheticTransportError("synthetic transport failure")}
    assert _run(lambda: h.ps.curl_fetch_html_same_site(PDP_A, HOST_A)) is None
    warnings = [r[2] for r in h.logs.rows if r[0] == PS_LOG and r[1] == logging.WARNING]
    assert len(warnings) == 1, h.logs.rows
    msg = warnings[0]
    assert msg == "[PRICE] curl_fetch_html_same_site failed for " + HOST_A + ": SyntheticTransportError", msg
    for needle in ("https://", "/products/", "ref=", "synthetic transport failure"):
        assert needle not in msg, (needle, msg)
